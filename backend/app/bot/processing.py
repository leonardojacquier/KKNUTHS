"""Pipeline síncrono de processamento de uploads — o coração do bot.

Sem dependência do SDK do Telegram: recebe bytes, devolve o texto de resposta.
O handler async chama isto via `asyncio.to_thread`, então chamadas lentas (LLM,
banco) não bloqueiam o event loop nem os outros usuários do bot.
"""
from __future__ import annotations

import logging

from app.agent import analyze_hand, analyze_tournament
from app.agent.analyzer import select_key_hands
from app.agent.embeddings import embed_text
from app.agent.llm import coach
from app.analysis import compute_player_stats
from app.config import get_settings
from app.db import get_repository
from app.ingestion import ingest
from app.models.canonical import CanonicalHand
from app.quota import MAX_COACHED_HANDS, check_quota, consume_quota

log = logging.getLogger("processing")

# mãos recentes por usuário (para /treino e /stats sem banco). Cap por usuário.
RECENT_HANDS: dict[int, list[CanonicalHand]] = {}
_RECENT_CAP = 300

# contexto da última análise por usuário — habilita a conversa de follow-up
LAST_ANALYSIS: dict[int, dict] = {}
_HISTORY_CAP = 6

# gráficos de range gerados na última análise (o handler envia e limpa)
# contexto do último upload por usuário: o handler escolhe os botões de
# pós-análise por ele (torneio -> relatório/evolução; mão avulsa -> simular)
LAST_UPLOAD_KIND: dict[int, str] = {}

# metadados da última MÃO analisada — os botões agem sobre ELA ("Simular esta
# mão" tem que simular esta mão; "Range do spot" é o range DESTE spot)
LAST_HAND_META: dict[int, dict] = {}

# (timestamp, charts): gráfico órfão de uma resposta que falhou NÃO pode
# grudar na interação seguinte — fora de contexto destrói a confiança
PENDING_CHARTS: dict[int, tuple[float, list[tuple[bytes, str]]]] = {}
_CHART_TTL = 900.0


def _chart_desc(spec: tuple) -> str:
    if spec and spec[0] == "range" and len(spec) > 2:
        return str(spec[2])
    if spec and spec[0] in ("nash", "nashmode"):
        return f"jam/fold {spec[1]} {spec[2]:g}bb"
    return str(spec[0] if spec else "?")


def _stash_charts(telegram_id: int, specs: list, user_id: str | None = None) -> None:
    """Processa as specs coletadas do coach: notas de caderno vão para o banco;
    gráficos (máx. 4, sem duplicatas) são renderizados para envio pelo handler.
    Render que falha vira AVISO explícito — o texto prometeu o gráfico."""
    import time as _time

    if not specs:
        return
    from app.analysis.range_chart import render_spec

    notes = [s for s in specs if s and s[0] == "note"]
    chart_specs = []
    for s in specs:  # dedupe preservando ordem: mesmo range 2x = 1 gráfico
        if s and s[0] != "note" and s not in chart_specs:
            chart_specs.append(s)

    if notes and user_id:
        repo = get_repository()
        for _, kind, note in notes[:3]:
            repo.save_note(user_id, kind, note)

    if len(chart_specs) > 4:
        log.warning("charts além do teto descartados: %s",
                    [_chart_desc(s) for s in chart_specs[4:]])

    charts = []
    for spec in chart_specs[:4]:
        rendered = render_spec(spec)
        if rendered:
            charts.append(rendered)
        else:
            # prometido no texto e não entregue = incoerência; avisa e loga
            charts.append(
                (b"", f"⚠️ Não consegui montar o gráfico ({_chart_desc(spec)}) "
                      "desta vez — me pede de novo que eu tento na hora."))
            get_repository().log_event(
                telegram_id, None, "chart_failed", {"spec": repr(spec)[:300]})
    if charts:
        PENDING_CHARTS[telegram_id] = (_time.time(), charts)


def pop_charts(telegram_id: int) -> list[tuple[bytes, str]]:
    import time as _time

    ts, charts = PENDING_CHARTS.pop(telegram_id, (0.0, []))
    if _time.time() - ts > _CHART_TTL:
        return []
    return charts


# documentos pendentes (relatório mão a mão etc.): (ts, [(bytes, nome, legenda)])
# mesmo raciocínio do TTL dos gráficos: doc órfão não gruda em resposta futura
PENDING_DOCS: dict[int, tuple[float, list[tuple[bytes, str, str]]]] = {}


def pop_docs(telegram_id: int) -> list[tuple[bytes, str, str]]:
    import time as _time

    ts, docs = PENDING_DOCS.pop(telegram_id, (0.0, []))
    if _time.time() - ts > _CHART_TTL:
        return []
    return docs


# paste de hand history cortado pelo Telegram (limite 4096): guarda a(s)
# parte(s) já recebidas até a continuação chegar
PENDING_PASTE: dict[int, tuple[str, float, int]] = {}
_PASTE_TTL = 900.0
_PASTE_CAP = 400_000  # ~100 partes; acima disso, mantém o final


def stash_paste(telegram_id: int, text: str, parts: int = 1) -> None:
    import time

    PENDING_PASTE[telegram_id] = (text[-_PASTE_CAP:], time.time(), parts)


def take_paste(telegram_id: int) -> tuple[str, int]:
    """Remove e retorna (paste pendente, nº de partes); ('', 0) se não há/expirou."""
    import time

    item = PENDING_PASTE.pop(telegram_id, None)
    if not item:
        return "", 0
    text, ts, parts = item
    if time.time() - ts >= _PASTE_TTL:
        return "", 0
    return text, parts


def remember_hands(telegram_id: int, hands: list[CanonicalHand]) -> None:
    cur = RECENT_HANDS.get(telegram_id, [])
    RECENT_HANDS[telegram_id] = (cur + hands)[-_RECENT_CAP:]


# análises em andamento por usuário: N mensagens simultâneas com 1 análise
# restante não podem TODAS passar no check de cota (a análise demora ~30s)
_INFLIGHT: dict[int, int] = {}
_INFLIGHT_LOCK = None


def _inflight_lock():
    global _INFLIGHT_LOCK
    if _INFLIGHT_LOCK is None:
        import threading

        _INFLIGHT_LOCK = threading.Lock()
    return _INFLIGHT_LOCK


def process_upload(
    content: bytes, fmt: str, telegram_id: int, username: str | None,
    lang: str = "pt", caption: str | None = None
) -> str:
    """Processa um arquivo enviado e retorna a resposta (markdown do Telegram)."""
    repo = get_repository()
    user = repo.get_or_create_user(telegram_id, username) if repo.enabled else None

    # ---- cota (P0): protege o custo de LLM mesmo sem billing ----
    with _inflight_lock():
        quota = check_quota(telegram_id, user, repo)
        inflight = _INFLIGHT.get(telegram_id, 0)
        if quota.degraded:
            return (
                "😅 Deu um engasgo aqui do meu lado — me manda de novo em alguns "
                "minutos? Essa mão não conta na sua cota."
            )
        if not quota.allowed or (quota.remaining >= 0 and inflight >= quota.remaining):
            return (
                "🚦 Suas análises gratuitas deste mês acabaram!\n"
                "Elas renovam no próximo mês — e os planos pagos chegam em breve."
            )
        _INFLIGHT[telegram_id] = inflight + 1
    try:
        return _process_upload_inner(
            content, fmt, telegram_id, username, lang, repo, user, caption
        )
    finally:
        with _inflight_lock():
            _INFLIGHT[telegram_id] = max(0, _INFLIGHT.get(telegram_id, 1) - 1)


def _process_upload_inner(
    content, fmt, telegram_id: int, username: str | None, lang: str, repo, user,
    caption: str | None = None,
) -> str:

    # ---- arquivo bruto no Storage (auditoria/reprocessamento) ----
    raw_path = None
    if repo.enabled and isinstance(content, (bytes, bytearray)):
        raw_path = repo.store_raw_file(telegram_id, bytes(content), fmt)
    elif repo.enabled and isinstance(content, str):
        raw_path = repo.store_raw_file(telegram_id, content.encode(), fmt or "txt")

    # ---- ingestão ----
    result = ingest(content, source_format=fmt)
    if not result.hands and caption and len(caption.strip()) >= 12:
        # print ilegível mas o aluno NARROU a mão junto: a narração é fonte
        # suficiente — "resolva essa bosta": nunca devolver 'não li' quando
        # o próprio aluno escreveu o cenário
        from app.agent.llm import extract_from_hand_text
        from app.ingestion.pipeline import IngestResult

        hand = extract_from_hand_text(caption)
        if hand is not None:
            hand.source_format = "image"
            result = IngestResult(
                [hand], hand.site if hand.site != "unknown" else None,
                "image", confidence=hand.confidence, needs_review=True,
                note="mão montada pela narração do aluno (print ilegível)",
            )
    if not result.hands:
        # registra a falha COM um trecho do conteúdo — permite diagnóstico e
        # correção do parser sem pedir o arquivo de novo
        excerpt = ""
        if fmt in ("image", "png", "jpg", "jpeg", "pdf"):
            # binário no excerpt derrubava o log_event inteiro (NUL byte)
            excerpt = f"<{fmt} binário, {len(content)} bytes>"
        elif isinstance(content, (bytes, bytearray)):
            excerpt = bytes(content[:500]).decode("utf-8", "ignore")
        elif isinstance(content, str):
            excerpt = content[:500]
        repo.log_event(
            telegram_id, username, "upload_failed",
            {"format": fmt, "note": result.note, "excerpt": excerpt,
             "raw_path": raw_path},
        )
        if fmt == "pppoker_replay":
            # o link foi reconhecido mas a mão não veio (CDN fora, chave
            # inválida): cai no caminho que já funciona
            return (
                "🔗 Achei o link, mas não consegui puxar essa mão do replay "
                "agora 😕. Me manda o *print* da tela da mão, ou *descreve* "
                "ela (cartas, posição, o que rolou), que eu analiso na hora. 🃏"
            )
        if "por enquanto analiso" in (result.note or ""):
            # variante reconhecida mas fora do motor (stud/razz/omaha do PHH):
            # nomear o jogo é honesto; "não li" seria mentira
            return (
                f"Li o arquivo — é uma {result.note}. 🃏\n"
                "Manda uma mão de Hold'em (NLHE) que eu analiso na hora!"
            )
        if caption and caption.strip():
            return (
                "O print veio ilegível pra mim e a legenda ainda não fecha a mão. 😕\n"
                "Me manda numa mensagem de texto: suas cartas, posição, stack e o "
                "que cada um fez (ex.: *99 no CO, 50bb, UTG abriu 2x*) — que eu "
                "analiso na hora, sem precisar do print."
            )
        return (
            "Ainda não consegui ler esse arquivo. 😕 Já registrei o formato para "
            "melhorar o suporte!\n\nEnquanto isso, tente:\n"
            "• enviar um *print do replay* da mão (funciona para qualquer sala)\n"
            "• ou *colar o texto de uma mão* aqui na conversa\n"
            "• ou o hand history `.txt` oficial (GGPoker: PokerCraft → download)"
        )
    hands = result.hands
    remember_hands(telegram_id, hands)

    # ---- persistência (no-op sem Supabase) ----
    hand_row_ids: list[str | None] = []
    if user:
        upload_id = repo.save_upload(
            user["id"], raw_path, result.source_format, result.site, result.confidence
        )
        for h in hands:
            hand_row_ids.append(repo.save_hand(user["id"], h, upload_id))

    # ---- análise determinística ----
    is_tournament = hands[0].format.value in ("tournament", "sng") and len(hands) > 1
    LAST_UPLOAD_KIND[telegram_id] = "tournament" if is_tournament else "hand"
    key_hands = None
    if is_tournament:
        structured = analyze_tournament(hands)
        key_hands = select_key_hands(hands, k=MAX_COACHED_HANDS)
    else:
        structured = analyze_hand(hands[0])
        if result.source_format == "image":
            _augment_snapshot(structured, hands[0])
        LAST_HAND_META[telegram_id] = {
            "hand_id": hands[0].hand_id,
            "position": structured.get("position"),
            "stack_bb": structured.get("effective_bb")
            or structured.get("hero_stack_bb"),
        }
    # o que o usuário ESCREVEU junto do envio (legenda da foto/arquivo) é
    # parte da mão: posições, ações e contexto que o print não mostra —
    # antes era descartado ("eu narrei a mão. Ele não considerou?")
    if caption and caption.strip():
        structured["relato_do_usuario"] = caption.strip()[:1500]
        structured["instrucao_relato"] = (
            "O aluno NARROU a mão junto do envio (relato_do_usuario). Use o "
            "relato como fonte para posições/ações/contexto que faltarem na "
            "leitura automática. Pote, sizings e stacks que o aluno citou são "
            "INSUMOS válidos para as ferramentas (pot_odds/ev_call/...) — os "
            "RESULTADOS é que vêm das ferramentas, nunca de cabeça. Se ainda "
            "faltar um dado para a conta, pergunte esse dado; não diga que "
            "não dá para calcular. Se o relato contradisser o que foi lido "
            "da imagem, confie no relato e diga o que ajustou.")

    # ---- stats cumulativas (histórico completo quando há banco) ----
    all_hands = repo.get_all_hands(user["id"]) if user else []
    stats_source = all_hands or RECENT_HANDS.get(telegram_id, hands)
    stats = compute_player_stats(stats_source, player=None)
    # só grava stats calculadas do HISTÓRICO COMPLETO: uma falha transitória do
    # get_all_hands não pode sobrescrever o perfil acumulado com a amostra em
    # memória (ex.: 5000 mãos viram 3)
    if user and all_hands and stats.hands:
        repo.upsert_player_stats(user["id"], stats)
        # ponto na linha do tempo de evolução (/evolucao): net do lote atual
        repo.snapshot_player_stats(user["id"], stats,
                                   net_bb=structured.get("net_bb"))

    # ---- coaching (Claude com tools; fallback determinístico) ----
    from app.agent.llm import set_tool_user

    set_tool_user(user["id"] if user else None)  # habilita search_hands
    chart_specs: list = []
    coaching = coach(structured, stats.__dict__, lang=lang, key_hands=key_hands,
                     collect_charts=chart_specs)
    _stash_charts(telegram_id, chart_specs, user["id"] if user else None)

    # quadro-resumo do campeonato: chega ANTES dos outros gráficos
    board_png: bytes | None = None
    if is_tournament and len(hands) >= 3:
        try:
            from app.analysis.tournament_board import render_tournament_board

            board = render_tournament_board(hands)
            board_png = board[0]
            import time as _time

            _ts, _lst = PENDING_CHARTS.get(telegram_id) or (0.0, [])
            _lst.insert(0, board)
            PENDING_CHARTS[telegram_id] = (_time.time(), _lst)
        except Exception as exc:
            log.warning("quadro do torneio falhou: %s", exc)

    # relatório mão a mão COMPLETO em anexo — quem sobe um torneio recebe o
    # detalhe de TODAS as mãos, não só o resumo (feedback duro do beta/admin:
    # "pedi a análise completa das mãos"). REPORT_AUTO=0 -> só via /relatorio
    if is_tournament and len(hands) >= 8 and get_settings().report_auto:
        try:
            from app.analysis.handreport import (
                _played, build_report_html, per_hand_analysis_llm,
            )

            played = [h for h in hands if _played(h)]
            per_hand = per_hand_analysis_llm(played) if len(played) <= 40 else {}
            html = build_report_html(hands, coaching, board_png,
                                     per_hand_analysis=per_hand)
            fname = f"KKNuths-MaoAMao-{hands[0].tournament_id or 'torneio'}.html"
            import time as _time

            _ts, _docs = PENDING_DOCS.get(telegram_id) or (0.0, [])
            _docs.append((
                html.encode("utf-8"), fname,
                "📋 Relatório mão a mão — o torneio inteiro, mão por mão, com "
                "o Nº da sala em cada uma. Quer abrir alguma? Me manda o Nº "
                "ou as cartas aqui no chat.",
            ))
            PENDING_DOCS[telegram_id] = (_time.time(), _docs)
        except Exception as exc:
            log.warning("relatório mão a mão falhou: %s", exc)

    # ---- base de conhecimento ----
    if user and hand_row_ids and hand_row_ids[0]:
        try:
            embedding = embed_text(coaching)
            repo.save_hand_analysis(hand_row_ids[0], structured, coaching, embedding)
        except Exception as exc:
            log.warning("falha ao gravar análise/embedding: %s", exc)

    # ---- consumo de cota ----
    consume_quota(telegram_id, user, repo)
    quota_after = check_quota(telegram_id, user, repo)

    # ---- evento (visibilidade de dashboard) ----
    repo.log_event(
        telegram_id,
        username,
        "upload",
        {
            "format": result.source_format,
            "site": result.site,
            "hands": len(hands),
            "confidence": result.confidence,
            "is_tournament": is_tournament,
            "quota_remaining": quota_after.remaining,
        },
    )

    # contexto para follow-up ("não gostei da análise" / "e se o vilão só paga com AQ+?")
    # se veio de PRINT, guarda a imagem: o coach pode RELÊ-LA no follow-up.
    # PDF fica de fora: bytes de PDF rotulados como image/jpeg fazem a API
    # rejeitar TODO follow-up daquela análise
    image_b64 = None
    media = "image/jpeg"
    if result.source_format == "image" and isinstance(content, (bytes, bytearray)):
        import base64 as _b64

        if len(content) <= 3_700_000:  # base64 infla 4/3; limite da API ~5MB
            image_b64 = _b64.standard_b64encode(bytes(content)).decode()
            media = "image/png" if fmt in ("png",) else "image/jpeg"
    LAST_ANALYSIS[telegram_id] = {
        "context": {
            "analysis": structured,
            "key_hands": key_hands,
            "coaching_anterior": coaching,
        },
        "history": [],
        "hand_row_id": hand_row_ids[0] if hand_row_ids else None,
        "user_id": user["id"] if user else None,
        "image_b64": image_b64,
        "media": media,
    }

    header = f"📊 *{len(hands)} mão(s)* lidas de {result.site}.\n"
    footer = "\n\n💬 _Discorda ou quer aprofundar? É só responder aqui._"
    if quota_after.remaining >= 0:
        footer += f"\n_Análises restantes no mês: {quota_after.remaining}_"
    return header + "\n" + coaching + footer


def _augment_snapshot(structured: dict, h: CanonicalHand) -> None:
    """PRINT da mesa no meio da mão: não existe história para narrar — existe a
    DECISÃO atual. Sem isto o coach 'analisava' lances que nunca viu (caso
    real: análise saiu 'nada a ver' com a foto enviada)."""
    from app.models.canonical import ActionType

    hero_acted = any(
        a.actor == h.hero and a.type in
        (ActionType.CALL, ActionType.BET, ActionType.RAISE, ActionType.FOLD)
        for st in h.streets for a in st.actions
    )
    if hero_acted and h.final_board:
        return  # mão com linha lida do print: análise normal serve

    n_op = max(1, min((len(h.players) or 2) - 1, 4))
    eq = None
    try:
        from app.analysis.equity import equity_vs_random

        eq = equity_vs_random(h.hero_cards, h.final_board or [], n_op,
                              iterations=1500, seed=7)
    except Exception:
        pass
    structured["modo"] = "FOTO DA MESA — spot ao vivo, NÃO é hand history"
    structured["spot_atual"] = {
        "jogadores_na_mesa": len(h.players),
        "viloes_considerados": n_op,
        "equity_vs_maos_aleatorias": round(eq, 2) if eq is not None else None,
    }
    structured["instrucao_snapshot"] = (
        "Isto é um PRINT da mesa no meio da mão — não há histórico de ações. "
        "PROIBIDO narrar ou supor lances passados e PROIBIDO dar veredito de "
        "mão inteira. Analise a DECISÃO ATUAL do herói com o que se vê: "
        "cartas, stack em bb, pote, preço a pagar se visível, posição se "
        "identificável. Se faltar um dado decisivo (posição, preço, ação dos "
        "vilões), declare a suposição em uma frase e FECHE perguntando o ÚNICO "
        "dado que mais refina a leitura."
    )


def process_followup(telegram_id: int, username: str | None, question: str) -> str | None:
    """Continua a conversa sobre a última análise. None se não há contexto.

    Grava o que importa: cada troca vai para bot_events e, quando há mão
    persistida, o insight (Q+A) entra na base de conhecimento com embedding —
    o /ask encontra depois.
    """
    ctx = LAST_ANALYSIS.get(telegram_id)
    if not ctx:
        # bot reiniciou? recupera a última análise do banco e retoma a conversa
        repo = get_repository()
        if repo.enabled:
            user = repo.get_or_create_user(telegram_id, username)
            latest = repo.get_latest_analysis(user["id"]) if user else None
            if latest and latest.get("summary"):
                canonical = latest.get("canonical") or {}
                ctx = {
                    "context": {
                        "analysis_anterior": latest["summary"],
                        "mao": {
                            "hero_cards": canonical.get("hero_cards"),
                            "final_board": canonical.get("final_board"),
                            "site": canonical.get("site"),
                            "format": canonical.get("format"),
                        },
                    },
                    "history": [],
                    "hand_row_id": latest.get("hand_row_id"),
                    "user_id": user["id"],
                }
                LAST_ANALYSIS[telegram_id] = ctx

    if not ctx:
        # modo coach geral: pergunta aberta de poker, sem mão específica —
        # personaliza com o perfil do jogador quando existe
        repo = get_repository()
        stats = None
        user = None
        if repo.enabled:
            user = repo.get_or_create_user(telegram_id, username)
            stats = repo.get_player_stats(user["id"]) if user else None
        ctx = {
            "context": {
                "modo": "coaching geral — sem mão específica; responda a pergunta "
                "do aluno como coach de poker (estratégia, tilt, bankroll, ranges…)",
                "perfil_do_jogador": stats,
            },
            "history": [],
            "hand_row_id": None,
            "user_id": user["id"] if user else None,
        }
        LAST_ANALYSIS[telegram_id] = ctx

    # memória de coach: as últimas notas do caderno entram no contexto — o
    # coach lembra dos leaks/metas do aluno entre sessões
    if ctx.get("user_id") and "caderno_do_coach" not in ctx["context"]:
        notes = get_repository().get_notes(ctx["user_id"], limit=6)
        if notes:
            ctx["context"]["caderno_do_coach"] = [
                f"[{n['kind']}] {n['note']}" for n in notes
            ]

    # registra a pergunta ANTES de gerar a resposta: se o LLM falhar (ou o
    # processo cair no meio), o rastro fica — caso real: perguntas do beta
    # sumiram do log e o portal ficou cego para parte do uso
    repo = get_repository()
    if repo.enabled:
        repo.log_event(telegram_id, username, "followup", {"q": question[:300]})

    from app.agent.llm import followup, set_tool_user

    set_tool_user(ctx.get("user_id"))  # habilita search_hands na conversa
    chart_specs: list = []
    answer = followup(
        ctx["context"],
        ctx["history"],
        question,
        image_b64=ctx.get("image_b64"),
        media_type=ctx.get("media", "image/jpeg"),
        collect_charts=chart_specs,
    )
    _stash_charts(telegram_id, chart_specs, ctx.get("user_id"))
    if not answer:
        if repo.enabled:
            repo.log_event(telegram_id, username, "followup_failed",
                           {"q": question[:300]})
        return (
            "Opa, me embananei aqui — me pergunta de novo em um instante? 🙏"
        )

    ctx["history"] = (ctx["history"] + [{"q": question, "a": answer}])[-_HISTORY_CAP:]

    if repo.enabled:
        # insight importante -> base de conhecimento (buscável via /ask)
        if ctx.get("hand_row_id"):
            try:
                insight = f"[Follow-up] Pergunta: {question}\nResposta: {answer}"
                embedding = embed_text(insight)
                repo.save_hand_analysis(
                    ctx["hand_row_id"], {"net_bb": None, "spots": None}, insight, embedding
                )
            except Exception as exc:
                log.warning("falha ao gravar insight de follow-up: %s", exc)

    return answer


def report_doc_for_user(telegram_id: int,
                        username: str | None) -> tuple[bytes, str, str] | None:
    """/relatorio: relatório mão a mão do ÚLTIMO torneio do usuário no banco.

    Retorna (bytes, filename, caption) ou None sem material.
    """
    repo = get_repository()
    if not repo.enabled:
        return None
    user = repo.get_or_create_user(telegram_id, username)
    if not user:
        return None
    tourneys = [h for h in repo.get_all_hands(user["id"]) if h.tournament_id]
    if len(tourneys) < 8:
        return None
    latest = max(tourneys, key=lambda h: h.played_at or "")
    hands = sorted((h for h in tourneys
                    if h.tournament_id == latest.tournament_id),
                   key=lambda h: h.played_at or "")
    if len(hands) < 8:
        return None

    from app.analysis.handreport import (
        _played, build_report_html, per_hand_analysis_llm,
    )

    board_png = None
    try:
        from app.analysis.tournament_board import render_tournament_board

        board_png = render_tournament_board(hands)[0]
    except Exception:
        pass
    played = [h for h in hands if _played(h)]
    per_hand = per_hand_analysis_llm(played) if len(played) <= 40 else {}
    html = build_report_html(hands, "", board_png, per_hand_analysis=per_hand)
    repo.log_event(telegram_id, username, "relatorio",
                   {"tournament": latest.tournament_id, "hands": len(hands)})
    return (
        html.encode("utf-8"),
        f"KKNuths-MaoAMao-{latest.tournament_id or 'torneio'}.html",
        "📋 Relatório mão a mão do seu último torneio — cada mão com análise "
        "e a versão 🎈 mais simples. Quer abrir alguma? Me manda o Nº ou as "
        "cartas aqui no chat.",
    )


def simplify_last(telegram_id: int, username: str | None) -> str | None:
    """Botão 🎈: reexplica a última resposta do coach em linguagem de
    iniciante total. None quando não há nada para simplificar."""
    ctx = LAST_ANALYSIS.get(telegram_id)
    if not ctx:
        return None
    text = None
    if ctx.get("history"):
        text = ctx["history"][-1].get("a")
    if not text:
        c = ctx.get("context") or {}
        text = c.get("coaching_anterior") or c.get("analysis_anterior")
    if not text:
        return None

    repo = get_repository()
    if repo.enabled:
        repo.log_event(telegram_id, username, "simplify", {})
    from app.agent.llm import simplify

    simple = simplify(str(text))
    if not simple:
        return "Opa, me embananei aqui — toca o botão de novo em um instante? 🙏"
    # a versão simples vira a última fala: dá para simplificar em cadeia e o
    # follow-up continua do ponto que o aluno de fato leu
    ctx["history"] = (ctx.get("history", []) +
                      [{"q": "(explica mais simples)", "a": simple}])[-_HISTORY_CAP:]
    return simple


def evolution_report(telegram_id: int) -> tuple[bytes | None, str]:
    """Gráfico + leitura da evolução do jogador (para o /evolucao)."""
    repo = get_repository()
    if not repo.enabled:
        return None, "Preciso do banco para montar sua linha do tempo — tente mais tarde."
    user = repo.get_or_create_user(telegram_id, None)
    history = repo.get_stats_history(user["id"]) if user else []
    if len(history) < 2:
        return None, (
            "📈 Sua linha do tempo está começando — cada lote de mãos analisado "
            "vira um ponto no gráfico. Envie mais sessões e me chame de novo!"
        )

    from app.analysis.evolution_chart import evolution_text, render_evolution_png

    png = render_evolution_png(history)
    text = evolution_text(history)

    notes = repo.get_notes(user["id"], limit=4)
    if notes:
        text += "\n\n📒 *Caderno do coach:*"
        for n in reversed(notes):
            text += f"\n• _[{n['kind']}]_ {n['note']}"
    return png, text


def tournament_board_report(telegram_id: int) -> tuple[bytes, str] | None:
    """Quadro-resumo do torneio mais recente do usuário (None sem material)."""
    repo = get_repository()
    hands: list[CanonicalHand] = []
    if repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        all_hands = repo.get_all_hands(user["id"]) if user else []
        tourneys = [h for h in all_hands if h.tournament_id]
        if tourneys:
            latest = max(tourneys, key=lambda h: h.played_at or "")
            hands = [h for h in tourneys
                     if h.tournament_id == latest.tournament_id]
    if not hands:
        hands = [h for h in RECENT_HANDS.get(telegram_id, []) if h.tournament_id]
    if len(hands) < 2:
        return None
    from app.analysis.tournament_board import render_tournament_board

    return render_tournament_board(hands)


def indicator_chart(telegram_id: int, indicator: str) -> bytes | None:
    """Gráfico de UM indicador da evolução (vpip|pfr|3bet|af|bb)."""
    repo = get_repository()
    if not repo.enabled:
        return None
    user = repo.get_or_create_user(telegram_id, None)
    history = repo.get_stats_history(user["id"]) if user else []
    if len(history) < 2:
        return None
    from app.analysis.evolution_chart import render_indicator_png

    return render_indicator_png(history, indicator)


def style_report(telegram_id: int, username: str | None,
                 desired: str | None = None) -> tuple[bytes | None, str] | None:
    """Cartão visual de estilo + texto (e caminho de transição se `desired`)."""
    repo = get_repository()
    stats = None
    if repo.enabled:
        user = repo.get_or_create_user(telegram_id, username)
        hands = repo.get_all_hands(user["id"]) if user else []
        if hands:
            stats = compute_player_stats(hands, player=None)
    if stats is None:
        recent = RECENT_HANDS.get(telegram_id, [])
        stats = compute_player_stats(recent, player=None) if recent else None
    if not stats or stats.hands < 10:
        return None

    from app.analysis.pro_styles import match_pro_style
    from app.analysis.style_chart import render_style_png

    vpip, pfr, tbet, af = stats.vpip, stats.pfr, stats.three_bet, stats.af
    if get_settings().bayes_stats:
        from app.analysis.bayes import bayes_stats

        b = bayes_stats(stats)
        vpip, pfr, tbet = b["vpip"]["mean"], b["pfr"]["mean"], b["three_bet"]["mean"]
        af = b["af"]["mean"]
    m = match_pro_style(vpip, pfr, af, tbet, desired)
    png = render_style_png(vpip, pfr, af, tbet)

    text = (
        f"🏅 *{m['estilo']}*\n{m['descricao']}\n\n"
        f"_2º estilo mais próximo: {m['segundo_estilo_mais_proximo']}_"
    )
    if desired and m.get("transicao_para"):
        text = (
            f"🎯 *Caminho: {m['estilo'].split(' (')[0]} → {m['transicao_para']}*\n\n"
            f"{m['caminho']}\n\n"
            f"Ajustes numéricos: {' · '.join(m['ajustes_numericos'])}\n\n"
            "_Vou acompanhar essa meta nas próximas análises._"
        )
    if stats.hands < 30:
        text += "\n\n⚠️ _Amostra pequena — mande mais mãos para firmar a leitura._"
    return png if not desired else None, text


def spot_range_chart(telegram_id: int) -> tuple[bytes, str] | None:
    """Range do SPOT da última mão analisada (botão 📖): stack curto vira o
    range de shove aproximado de Nash; deep vira o range de open da posição.
    Determinístico — o mesmo número que ancora o veredito do coach."""
    meta = LAST_HAND_META.get(telegram_id)
    if not meta:
        return None
    from app.analysis.pushfold import shove_threshold
    from app.analysis.range_chart import render_spec
    from app.analysis.ranges import OPEN_RANGES

    pos = (meta.get("position") or "").upper()
    stack = meta.get("stack_bb")
    if stack and stack <= 20 and pos not in ("", "BB"):
        pct = shove_threshold(pos, float(stack))
        if pct:
            return render_spec(("range", f"top {round(pct * 100)}%",
                                f"Shove {pos} ~{stack:g}bb (aprox. Nash)"))
    rng = OPEN_RANGES.get(pos)
    if rng:
        return render_spec(("range", rng, f"Range de open — {pos} (deep)"))
    return render_spec(("range", OPEN_RANGES["BTN"],
                        "Range de open — BTN (deep)"))


# domínios de replay de clube conhecidos (link, não arquivo)
_REPLAY_HOSTS = ("replay.pppoker.net", "pppoker.net", "supremapoker.net",
                 "clubgg.com", "wepoker", "pokerbros", "upoker")


def replay_link_info(text: str) -> dict | None:
    """Detecta link de replay de clube na mensagem. Retorna
    {'site', 'share_key'} ou None. Só dispara quando a mensagem É o link
    (não quando cita uma url no meio de uma pergunta longa)."""
    import re as _re

    t = (text or "").strip()
    m = _re.search(r'https?://[^\s]+', t)
    if not m:
        return None
    url = m.group(0)
    host = _re.sub(r'^https?://([^/]+).*', r'\1', url).lower()
    if not any(h in host for h in _REPLAY_HOSTS):
        return None
    if len(t) > len(url) + 40:
        return None
    from app.parsers.pppoker_replay import share_key_from_url

    site = "pppoker" if "pppoker" in host else (
        "suprema" if "suprema" in host else "outro")
    return {"site": site, "url": url,
            "share_key": share_key_from_url(url) if site == "pppoker" else None}


def replay_fallback_text() -> str:
    """Mensagem para replay que não dá para puxar automático (Suprema etc.)."""
    return (
        "🔗 Esse é um *link de replay*. Esse tipo eu ainda não abro sozinho — "
        "mas analiso a mão *agora* de dois jeitos:\n\n"
        "📸 *Print do replay* — foto da tela da mão (cartas + board).\n"
        "✍️ *Ou descreve* — _\"77 no CO, 30bb, limpei, flop A♦7♣9♣...\"_ — "
        "que eu rodo os números na hora. 🃏"
    )


def _extract_metas(text: str) -> list[str]:
    """Extrai as linhas 'META 1: …' / 'META 2: …' do briefing (viram notas
    no caderno; o relatório pós-torneio vai cobrá-las na fase 3)."""
    import re as _re

    return [m.strip() for m in _re.findall(
        r"^META\s*\d\s*:\s*(.+)$", text or "", _re.MULTILINE) if m.strip()][:2]


def prepare_report(telegram_id: int, username: str | None,
                   args_text: str = "") -> str | None:
    """/preparar — briefing pré-torneio a partir dos dados do PRÓPRIO aluno.

    None quando não há mãos (o handler explica) ou o LLM está fora.
    """
    repo = get_repository()
    user = repo.get_or_create_user(telegram_id, username) if repo.enabled else None
    src_hands = (repo.get_all_hands(user["id"]) if user else []) or \
        RECENT_HANDS.get(telegram_id, [])
    if not src_hands:
        return None
    stats = compute_player_stats(src_hands, player=None)
    if not stats or not stats.hands:
        return None

    vpip, pfr, tbet, af = stats.vpip, stats.pfr, stats.three_bet, stats.af
    if get_settings().bayes_stats:
        from app.analysis.bayes import bayes_stats

        b = bayes_stats(stats)
        vpip, pfr, tbet = b["vpip"]["mean"], b["pfr"]["mean"], b["three_bet"]["mean"]
        af = b["af"]["mean"]

    from app.analysis.leaks import detect_leaks
    from app.analysis.mental import detect_mental
    from app.analysis.prep import dicas_para, parse_tournament_profile

    torneio = parse_tournament_profile(args_text)
    dicas = dicas_para(torneio)
    ctx: dict = {
        "torneio_de_hoje": torneio if torneio.get("descricao") else None,
        "dicas_do_formato": dicas or None,
        "perfil": {"maos": stats.hands, "vpip": round(vpip), "pfr": round(pfr),
                   "three_bet": round(tbet), "af": round(af, 2),
                   "estilo": stats.label},
        "leaks": detect_leaks(src_hands[:150]),
        "tilt": detect_mental(src_hands[:300]),
    }
    if user:
        notes = repo.get_notes(user["id"], limit=6)
        if notes:
            ctx["caderno_do_coach"] = [f"[{n['kind']}] {n['note']}" for n in notes]

    from app.agent.llm import prepare_briefing

    briefing = prepare_briefing(ctx)
    if not briefing:
        return None

    # ranges do formato como imagem: turbo/hyper vivem de push/fold (anexa o
    # equilíbrio de shove do SB); estrutura lenta ganha a referência de open
    if torneio.get("formato") in ("turbo", "hyper"):
        _stash_charts(telegram_id, [("nashmode", "SB", 12.0, "freq", 1.5)])
    elif torneio.get("formato") == "regular":
        from app.analysis.ranges import OPEN_RANGES

        _stash_charts(telegram_id, [
            ("range", OPEN_RANGES["BTN"], "Range de open — BTN (deep)")])

    # metas viram notas do caderno — memória entre a preparação e o jogo
    if user:
        from datetime import date

        for meta in _extract_metas(briefing):
            repo.save_note(user["id"], "meta", f"[prep {date.today()}] {meta}")
    if repo.enabled:
        repo.log_event(telegram_id, username, "preparar",
                       {"args": args_text[:120] or None})
    return briefing


def stats_report(telegram_id: int, username: str | None) -> str | None:
    """Perfil atual + benchmark contra o field da ferramenta + caderno."""
    repo = get_repository()
    stats = None
    user = None
    src_hands: list[CanonicalHand] = []
    if repo.enabled:
        user = repo.get_or_create_user(telegram_id, username)
        src_hands = repo.get_all_hands(user["id"]) if user else []
        if src_hands:
            stats = compute_player_stats(src_hands, player=None)
    if stats is None:
        src_hands = RECENT_HANDS.get(telegram_id, [])
        stats = compute_player_stats(src_hands, player=None) if src_hands else None
    if not stats or not stats.hands:
        return None

    # números corrigidos por amostra (shrinkage): com poucas mãos o valor cru
    # mente ("3-bet 100%" com 2 oportunidades) — o corrigido fica ancorado no
    # field e o coach mostra o intervalo enquanto a amostra não crava
    vpip, pfr, tbet, af = stats.vpip, stats.pfr, stats.three_bet, stats.af
    intervalo = ""
    if get_settings().bayes_stats:
        from app.analysis.bayes import bayes_stats

        b = bayes_stats(stats)
        vpip, pfr, tbet = b["vpip"]["mean"], b["pfr"]["mean"], b["three_bet"]["mean"]
        af = b["af"]["mean"]
        soft = [k for k in ("vpip", "pfr", "three_bet") if not b[k]["firm"]]
        if soft:
            k = soft[0]
            nome = {"vpip": "VPIP", "pfr": "PFR", "three_bet": "3-bet"}[k]
            intervalo = (
                f"\n_{nome} ainda entre {b[k]['lo']:.0f} e {b[k]['hi']:.0f}% — "
                "mande mais torneios que eu cravo._"
            )

    msg = (
        f"*Seu perfil* ({stats.hands} mãos)\n"
        f"• VPIP {vpip:.0f}% | PFR {pfr:.0f}% | 3-bet {tbet:.0f}%\n"
        f"• Agressão (AF) {af:g}\n"
        f"• Estilo: *{stats.label}*{intervalo}"
    )

    # com amostra decente, aproxima dos grandes nomes (perfis públicos)
    if stats.hands >= 30:
        from app.analysis.pro_styles import match_pro_style

        m = match_pro_style(vpip, pfr, af, tbet)
        top = m["jogadores_parecidos"][0]
        msg += (
            f"\n\n🏅 *Seu estilo lembra:* {m['estilo']}\n"
            f"Na linha de *{top['nome']}* — {top['por_que']}.\n"
            f"_Veja o cartão visual com /estilo_"
        )

    # você vs o field da ferramenta (só usuários com amostra decente)
    field = repo.get_field_averages() if repo.enabled else []
    others = [f for f in field if f]
    if len(others) >= 2:
        import statistics as st

        med_vpip = st.median(float(f.get("vpip") or 0) for f in others)
        med_pfr = st.median(float(f.get("pfr") or 0) for f in others)
        # o seu número é o corrigido pela amostra; a mediana do field é crua —
        # o rótulo deixa isso explícito para a comparação não enganar
        corr = " (corrigido)" if get_settings().bayes_stats else ""
        msg += (
            f"\n\n*Você vs o field KKNuths* ({len(others)} jogadores)\n"
            f"• VPIP: você {vpip:.0f}%{corr} · field {med_vpip:.0f}%\n"
            f"• PFR: você {pfr:.0f}%{corr} · field {med_pfr:.0f}%"
        )

    if user:
        notes = repo.get_notes(user["id"], limit=3)
        if notes:
            msg += "\n\n📒 *Caderno do coach:*"
            for n in reversed(notes):
                msg += f"\n• _[{n['kind']}]_ {n['note']}"

    # plano de estudo rankeado por dinheiro (leaks com posterior + custo);
    # limita a amostra para não pesar o /stats (equity MC por decisão)
    if get_settings().bayes_stats and stats.hands >= 10:
        from app.analysis.leaks import detect_leaks, leaks_text
        from app.analysis.mental import detect_mental, mental_text

        msg += leaks_text(detect_leaks(src_hands[:150]))
        msg += mental_text(detect_mental(src_hands[:300]))

    msg += "\n\n📈 Veja sua linha do tempo com /evolucao"
    return msg


def build_simulation(telegram_id: int, hand_id: str | None = None) -> dict | None:
    """Monta uma simulação jogável a partir de uma mão real do usuário.

    `hand_id`: simula AQUELA mão (botão 'Simular esta mão' age sobre a mão
    da análise, não sobre outra). Sem hand_id (ou mão sem decisão), escolhe
    a mão com mais pontos de decisão do herói. None sem material.
    """
    from app.agent.analyzer import analyze_hand as _ah
    from app.agent.analyzer import hand_timeline

    hands = list(RECENT_HANDS.get(telegram_id, []))
    repo = get_repository()
    if not hands and repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        if user:
            hands = repo.get_all_hands(user["id"], limit=200)

    best, best_events = None, []
    if hand_id:
        for h in hands:
            if h.hand_id == hand_id and h.hero and h.hero_cards:
                ev = hand_timeline(h)
                if any(e["kind"] == "decision" for e in ev):
                    best, best_events = h, ev
                break
    if best is None:
        for h in hands:
            if not (h.hero and h.hero_cards):
                continue
            ev = hand_timeline(h)
            if sum(1 for e in ev if e["kind"] == "decision") > sum(
                1 for e in best_events if e["kind"] == "decision"
            ):
                best, best_events = h, ev
    if not best or not any(e["kind"] == "decision" for e in best_events):
        return None

    a = _ah(best)
    return {
        "hand_id": best.hand_id,
        "cards": best.hero_cards,
        "position": a["position"],
        "bb": best.stakes.big_blind or 1,
        "net_bb_real": a["net_bb"],
        "events": best_events,
        "pos": 0,
        "results": [],
    }


def sim_advance(sim: dict) -> dict:
    """Avança a simulação: narra ações dos vilões até a próxima decisão do herói.

    Retorna {"narration": str, "decision": evento|None, "done": bool}.
    """
    lines: list[str] = []
    last_street = None
    while sim["pos"] < len(sim["events"]):
        e = sim["events"][sim["pos"]]
        if e["street"] != last_street:
            board = " ".join(e["board"]) if e["board"] else "—"
            lines.append(f"\n🃏 *{e['street'].upper()}*  (board: {board})")
            last_street = e["street"]
        if e["kind"] == "action":
            lines.append(f"  {e['text']}")
            sim["pos"] += 1
            continue
        # decisão do herói: para aqui e espera o botão
        pot_txt = f"pote: {e['pot']:g}"
        call_txt = f" | para pagar: {e['to_call']:g}" if e["to_call"] > 0 else ""
        lines.append(f"\n👉 *Sua vez!*  {pot_txt}{call_txt}")
        return {"narration": "\n".join(lines), "decision": e, "done": False}
    return {"narration": "\n".join(lines), "decision": None, "done": True}


def sim_choose(sim: dict, choice: str) -> None:
    """Registra a escolha do usuário na decisão atual e avança o ponteiro."""
    e = sim["events"][sim["pos"]]
    sim["results"].append(
        {
            "street": e["street"],
            "board": e.get("board") or [],
            "choice": choice,
            "actual": e["actual"] + (" (all-in)" if e.get("all_in") else ""),
            "actual_amount": e.get("amount"),
            "pot": e["pot"],
            "to_call": e["to_call"],
        }
    )
    sim["pos"] += 1


def sim_whatif(sim: dict, telegram_id: int | None = None) -> str | None:
    """Modo "e se": veredito do coach sobre a linha alternativa escolhida.

    None quando o LLM está indisponível (o resumo determinístico já foi enviado).
    Gráficos que o coach pedir no veredito são stashed para o handler enviar —
    sem isto o texto prometia 'gráfico abaixo' e nada chegava.
    """
    from app.agent.llm import evaluate_line

    payload = {
        "hero_cards": sim["cards"],
        "position": sim["position"],
        "big_blind": sim["bb"],
        "resultado_real_bb": sim["net_bb_real"],
        "decisoes": sim["results"],
    }
    chart_specs: list = []
    out = evaluate_line(payload, collect_charts=chart_specs)
    if telegram_id is not None:
        _stash_charts(telegram_id, chart_specs, None)
    return out


def sim_summary(sim: dict) -> str:
    """Comparação final: sua linha vs a linha real, com o preço de cada decisão."""
    from app.analysis.tools import pot_odds

    lines = [
        f"🏁 *Fim da simulação!*  ({' '.join(sim['cards'])} em {sim['position'] or '?'})\n"
    ]
    matches = 0
    for r in sim["results"]:
        same = r["choice"].split()[0] == r["actual"].split()[0]
        matches += int(same)
        icon = "✅" if same else "↔️"
        price = ""
        if r["to_call"] > 0:
            req = pot_odds(r["pot"], r["to_call"])
            price = f" — equity mínima p/ pagar: {req*100:.0f}%"
        lines.append(
            f"{icon} *{r['street']}*: você: {r['choice']} | na mão real: {r['actual']}{price}"
        )
    lines.append(
        f"\nResultado real da mão: {sim['net_bb_real']:+.1f} BB "
        f"(em big blinds)."
    )
    lines.append(
        f"Você repetiu a linha real em {matches}/{len(sim['results'])} decisões."
    )
    lines.append("\n💬 _Quer discutir alguma dessas decisões? É só responder aqui._")
    return "\n".join(lines)


def _pretty_cards(cards: list[str]) -> str:
    sym = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
    return " ".join(c[0] + sym.get(c[1], c[1]) for c in cards if len(c) == 2)


def _walk_hand(h: CanonicalHand) -> tuple[list[str], list[dict]]:
    """Percorre a mão narrando por POSIÇÃO e em BB; devolve (linhas, decisões).

    Cada decisão do herói vem com o índice da narrativa naquele momento +
    street, mesa, pote, preço e a ação real — a matéria-prima do quiz."""
    from app.models.canonical import ActionType, StreetName

    bb = h.stakes.big_blind or 1
    pos = {p.name: (p.position or p.name[:8]) for p in h.players}
    verbs = {"fold": "folda", "check": "dá check", "call": "paga",
             "bet": "aposta", "raise": "aumenta para"}
    lines: list[str] = []
    decisions: list[dict] = []
    pot = 0.0
    order = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN, StreetName.RIVER]

    for sname in order:
        st = h.street(sname)
        if not st:
            continue
        contrib: dict[str, float] = {}
        started = False
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - contrib.get(a.actor, 0.0)
            counts = a.type != ActionType.POST or a.post_type in ("sb", "bb")
            outstanding = max(contrib.values(), default=0.0)

            if a.type != ActionType.POST and not started:
                board = _pretty_cards(st.board) if st.board else ""
                lines.append(f"*{sname.value.upper()}*" + (f"  ({board})" if board else ""))
                started = True

            if a.actor == h.hero and a.type != ActionType.POST:
                to_call = max(0.0, outstanding - contrib.get(h.hero or "", 0.0))
                decisions.append({
                    "line_idx": len(lines),
                    "street": sname.value,
                    "board": list(st.board),
                    "pot_bb": round(pot / bb, 1),
                    "to_call_bb": round(to_call / bb, 1),
                    "actual": a.type.value,
                    "amount_bb": round(((a.to_amount or a.amount) / bb), 1),
                    "all_in": a.all_in,
                })
                amt = round((a.to_amount or a.amount) / bb, 1)
                lines.append(f"  VOCÊ {verbs.get(a.type.value, a.type.value)}"
                             + (f" {amt:g}bb" if amt else "")
                             + (" (all-in)" if a.all_in else ""))
            elif a.type != ActionType.POST:
                who = pos.get(a.actor, a.actor[:8])
                amt = round((a.to_amount or a.amount) / bb, 1)
                lines.append(f"  {who} {verbs.get(a.type.value, a.type.value)}"
                             + (f" {amt:g}bb" if amt else "")
                             + (" (all-in)" if a.all_in else ""))

            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET, ActionType.RAISE):
                pot += add
                if counts:
                    contrib[a.actor] = contrib.get(a.actor, 0.0) + add
    return lines, decisions


def _preflop_summary(h: CanonicalHand, stop_actor: str | None = None) -> str | None:
    """Resumo do pré-flop em ORDEM DE POSIÇÃO (UTG primeiro), compacto e
    legível — como um jogador conta a mão. Ignora posts de blind/ante.
    `stop_actor`: para antes da decisão do herói (quando a decisão é no pré)."""
    from app.models.canonical import ActionType, StreetName

    pre = h.street(StreetName.PREFLOP)
    if not pre:
        return None
    bb = h.stakes.big_blind or 1
    pos = {p.name: (p.position or "") for p in h.players}
    # ORDEM CRONOLÓGICA (que já é a ordem de ação correta: UTG primeiro).
    # Escondemos posts (ruído de blind/ante) e folds — como um jogador conta:
    # "MP abre 2bb · SB 3-beta 6bb · MP paga". Se folda até o herói, avisa.
    parts: list[str] = []
    folds_antes = 0
    n_raises = 0
    for a in pre.actions:
        if a.type == ActionType.POST:
            continue
        if stop_actor and a.actor == h.hero:
            break
        if a.type == ActionType.FOLD:
            folds_antes += 1
            continue
        who = "você" if a.actor == h.hero else (pos.get(a.actor) or a.actor[:6])
        amt = round((a.to_amount or a.amount) / bb, 1)
        if a.type == ActionType.RAISE:
            n_raises += 1
            verb = "abre" if n_raises == 1 else (
                "3-beta" if n_raises == 2 else "4-beta")
        else:
            verb = {"call": "paga", "bet": "abre", "check": "dá check"}.get(
                a.type.value, a.type.value)
        txt = f"{who} {verb}"
        # valor só em bet/raise (definem o preço); call = 'paga' (igualou)
        if amt and a.type.value in ("bet", "raise"):
            txt += f" {amt:g}bb"
        if a.all_in:
            txt += " (all-in)"
        parts.append(txt)
    if not parts:
        # ninguém aumentou/pagou antes do herói — foldou geral até você
        return "Pré-flop: folda até você" if folds_antes else None
    return "Pré-flop: " + " · ".join(parts)


def hand_storyboard_streets(h: "CanonicalHand", upto_di: int | None = None,
                            reveal: bool = False) -> list[dict]:
    """Bandas do storyboard (uma por street): {name, board, lines, pot_bb, note}.

    - `upto_di`: índice da decisão do herói. Corta na street daquela decisão —
      não spoila streets futuras (quiz). None = mão inteira (relatório).
    - `reveal`: quando True, na street da decisão mostra a ação real do herói
      (o gabarito); quando False, para ANTES dela (a pergunta).
    Pré-flop usa o resumo compacto; pós-flop, lance a lance em BB.
    """
    from app.models.canonical import ActionType, StreetName

    bb = h.stakes.big_blind or 1
    pos = {p.name: (p.position or p.name[:8]) for p in h.players}
    verbs = {"fold": "folda", "check": "dá check", "call": "paga",
             "bet": "aposta", "raise": "aumenta p/"}
    order = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN,
             StreetName.RIVER]
    label = {StreetName.PREFLOP: "Pré-flop", StreetName.FLOP: "Flop",
             StreetName.TURN: "Turn", StreetName.RIVER: "River"}

    stop_street = None
    if upto_di is not None:
        _, decisions = _walk_hand(h)
        if 0 <= upto_di < len(decisions):
            stop_street = decisions[upto_di]["street"]

    bands: list[dict] = []
    pot = 0.0
    full_board: list[str] = []
    for sname in order:
        st = h.street(sname)
        if not st:
            continue
        full_board = full_board + list(st.board)
        is_stop = (stop_street == sname.value)
        display_lines: list[str] = []
        hero_seen = False

        if sname == StreetName.PREFLOP:
            summ = _preflop_summary(
                h, stop_actor=(h.hero if (is_stop and not reveal) else None))
            if summ:
                display_lines.append(summ.replace("Pré-flop: ", ""))

        contrib: dict[str, float] = {}
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - contrib.get(a.actor, 0.0)
            is_hero = (a.actor == h.hero and a.type != ActionType.POST)
            # decisão-alvo: para aqui (a pergunta termina antes da ação real)
            if is_stop and is_hero and not hero_seen:
                hero_seen = True
                if not reveal:
                    if pot:
                        bands.append({"name": label[sname], "board": full_board,
                                      "lines": display_lines,
                                      "pot_bb": round(pot / bb, 1)})
                    return bands
            # narra pós-flop lance a lance (o pré já veio do resumo)
            if sname != StreetName.PREFLOP and a.type != ActionType.POST:
                amt = round((a.to_amount or a.amount) / bb, 1)
                who = "VOCÊ" if is_hero else pos.get(a.actor, a.actor[:8])
                show_amt = amt and a.type.value in ("bet", "raise", "call")
                display_lines.append(
                    f"{who} {verbs.get(a.type.value, a.type.value)}"
                    + (f" {amt:g}bb" if show_amt else "")
                    + (" (all-in)" if a.all_in else ""))
            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET,
                          ActionType.RAISE):
                pot += add
                if a.type != ActionType.POST or a.post_type in ("sb", "bb"):
                    contrib[a.actor] = contrib.get(a.actor, 0.0) + add

        bands.append({"name": label[sname], "board": full_board,
                      "lines": display_lines, "pot_bb": round(pot / bb, 1)})
        if is_stop:
            break
    return bands


def build_drill(telegram_id: int) -> dict | None:
    """Monta um spot de treino PROFISSIONAL: escolhe a decisão mais interessante
    das mãos do usuário (preço a pagar, pós-flop, all-in, stack curto — nada de
    fold trivial nem open óbvio de AA sem ação) com a história completa da mão
    até aquele momento. Retorna None sem material."""
    import random

    from app.analysis.tools import pot_odds

    hands = list(RECENT_HANDS.get(telegram_id, []))
    repo = get_repository()
    if not hands and repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        if user:
            hands = repo.get_all_hands(user["id"], limit=200)
    candidates = [h for h in hands if h.hero and h.hero_cards and h.stakes.big_blind]
    if not candidates:
        return None

    scored: list[tuple[float, CanonicalHand, int]] = []
    for h in candidates[:150]:
        try:
            _, decisions = _walk_hand(h)
        except Exception:
            continue
        seat = h.hero_seat()
        stack_bb = (seat.stack / h.stakes.big_blind) if seat else None
        ranks = {c[0] for c in h.hero_cards}
        premium_pair = len(h.hero_cards) == 2 and len(ranks) == 1 and ranks <= {"A", "K", "Q"}
        for di, d in enumerate(decisions):
            score = 0.0
            if d["to_call_bb"] > 0:
                score += 3          # tem preço a pagar = tem matemática
            if d["street"] != "preflop":
                score += 2          # pós-flop ensina mais
            if d["all_in"]:
                score += 2
            score += min(d["pot_bb"] / 10, 2)
            if stack_bb and stack_bb <= 15 and d["street"] == "preflop":
                score += 2          # zona de push/fold: Nash entra no gabarito
            if d["street"] == "preflop" and d["to_call_bb"] <= 1 and premium_pair:
                score -= 3          # "o que fazer com AA sem ação"? trivial
            if d["street"] == "preflop" and d["to_call_bb"] <= 1 and d["actual"] == "fold":
                score -= 2          # fold de lixo no pré sem raise = sem lição
            scored.append((score + random.random() * 0.8, h, di))

    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=True)
    _, h, di = random.choice(scored[:5])

    lines, decisions = _walk_hand(h)
    d = decisions[di]
    seat = h.hero_seat()
    bb = h.stakes.big_blind
    stack_bb = round(seat.stack / bb, 1) if seat else None

    # história limpa e EM ORDEM: pré-flop resumido por posição (UTG primeiro) +
    # cada street pós-flop lance a lance. O corte antigo (story[-12:]) fatiava
    # o pré no meio e embaralhava a leitura.
    def _street_start(tag: str) -> int:
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith(f"*{tag}*"):
                return i
        return len(lines)

    is_pre = d["street"] == "preflop"
    pre_sum = _preflop_summary(h, stop_actor=h.hero if is_pre else None)
    if is_pre:
        story = [pre_sum] if pre_sum else []
    else:
        flop_i = _street_start("FLOP")
        post = lines[flop_i:d["line_idx"]]
        story = ([pre_sum] if pre_sum else []) + post

    # vilões ATIVOS (para a figura da mesa): quem entrou no pote sem foldar
    villains = _active_villains(h)

    # o "vilão da vez": quem apostou/aumentou por último antes da decisão do
    # herói — a figura mostra as fichas dele na frente (situação completa).
    agg_pos, agg_bet = _decision_aggressor(h, d)
    for v in villains:
        if agg_pos and v.get("pos") == agg_pos:
            v["bet_bb"] = agg_bet
            v["to_act"] = True

    # storyboard da revelação: mão até a street da decisão, COM a ação real do
    # herói (o gabarito). Não spoila streets futuras. Custo zero de LLM.
    try:
        storyboard = hand_storyboard_streets(h, upto_di=di, reveal=True)
    except Exception:
        storyboard = []

    required = pot_odds(d["pot_bb"], d["to_call_bb"]) if d["to_call_bb"] > 0 else None
    return {
        "hand_id": h.hand_id,
        "cards": h.hero_cards,
        "cards_pretty": _pretty_cards(h.hero_cards),
        "position": (seat.position if seat else None),
        "stack_bb": stack_bb,
        "blinds": f"{h.stakes.small_blind:g}/{h.stakes.big_blind:g}"
                  + (f" (ante {h.stakes.ante:g})" if h.stakes.ante else ""),
        "players": len(h.players),
        "format": h.format.value,
        "street": d["street"],
        "board": d["board"],
        "board_pretty": _pretty_cards(d["board"]),
        "pot_bb": d["pot_bb"],
        "to_call_bb": d["to_call_bb"],
        "required_eq": round(required, 3) if required is not None else None,
        "story": "\n".join(story).strip(),
        "villains": villains,
        "storyboard": storyboard,
        "actual": d["actual"],
        "actual_amount_bb": d["amount_bb"],
        "all_in": d["all_in"],
        "net_bb": analyze_hand(h)["net_bb"],
    }


def _decision_aggressor(h: CanonicalHand, d: dict) -> tuple[str | None, float | None]:
    """Na street da decisão, quem foi o último a apostar/aumentar ANTES do herói
    — o vilão que o herói tem de responder — e o tamanho (em bb)."""
    from app.models.canonical import ActionType, StreetName

    bb = h.stakes.big_blind or 1
    try:
        st = h.street(StreetName(d["street"]))
    except Exception:
        st = None
    if not st:
        return None, None
    pos = {p.name: (p.position or p.name[:8]) for p in h.players}
    # o herói pode agir mais de uma vez na street (check, depois fold à aposta).
    # Guardamos a última aposta/aumento de VILÃO e, quando o herói responde a
    # ela, essa é a aposta que ele enfrenta.
    pending = (None, None)
    facing = (None, None)
    for a in st.actions:
        if a.actor == h.hero and a.type != ActionType.POST:
            if pending[0] is not None:
                facing = pending      # herói responde a uma aposta pendente
            continue
        if a.type in (ActionType.BET, ActionType.RAISE):
            pending = (a.actor, round((a.to_amount or a.amount) / bb, 1))
    name, amt = facing
    return (pos.get(name) if name else None), amt


def _active_villains(h: CanonicalHand) -> list[dict]:
    """Vilões que entraram no pote sem foldar (para a figura): posição+stack."""
    from app.models.canonical import ActionType

    bb = h.stakes.big_blind or 1
    folded, entered = set(), []
    for st in h.streets:
        for a in st.actions:
            if a.actor == h.hero or a.type == ActionType.POST:
                continue
            if a.type == ActionType.FOLD:
                folded.add(a.actor)
            elif a.type in (ActionType.CALL, ActionType.BET, ActionType.RAISE):
                if a.actor not in entered:
                    entered.append(a.actor)
    seat = {p.name: p for p in h.players}
    out = []
    for name in entered:
        if name in folded:
            continue
        p = seat.get(name)
        if not p:
            continue
        out.append({"pos": p.position or name[:6],
                    "stack_bb": round(p.stack / bb, 1)})
    return out[:6]


def drill_message(drill: dict, title: str = "🃏 *Quiz do dia* — mão real sua") -> str:
    """Texto do quiz/treino: contexto completo, história da mão e o preço."""
    fmt = "Torneio" if drill.get("format") in ("tournament", "sng") else "Cash"
    stack = f"{drill['stack_bb']:g}bb" if drill.get("stack_bb") else "?"
    head = (
        f"{title}\n"
        f"_{fmt} · blinds {drill['blinds']} · {drill.get('players') or '?'} jogadores_\n\n"
        f"Você: *{drill['cards_pretty']}* no *{drill['position'] or '?'}* · stack *{stack}*\n"
    )
    body = ("\n" + drill["story"] + "\n") if drill.get("story") else "\n"
    mesa = f"\nBoard: *{drill['board_pretty']}*" if drill.get("board_pretty") else ""
    price = (f" | pagar: *{drill['to_call_bb']:g}bb* "
             f"(precisa de ≈{drill['required_eq']*100:.0f}% de equity)"
             if drill.get("to_call_bb") else "")
    ask = (f"{mesa}\n👉 *Sua vez no {drill['street'].upper()}* — "
           f"pote: *{drill['pot_bb']:g}bb*{price}\n\nO que você faz?")
    return head + body + ask


def drill_buttons(drill: dict) -> list[list[dict]]:
    """Botões contextuais (formato Bot API): com preço = Fold/Call/Raise;
    sem = Check/Bet."""
    if drill.get("to_call_bb"):
        return [[{"text": "Fold", "callback_data": "drill:fold"},
                 {"text": "Call", "callback_data": "drill:call"},
                 {"text": "Raise/All-in", "callback_data": "drill:raise"}]]
    return [[{"text": "Check", "callback_data": "drill:check"},
             {"text": "Bet", "callback_data": "drill:bet"}]]


def reveal_drill(drill: dict, choice: str) -> str:
    """Gabarito profissional: sua escolha vs a real, a matemática do spot
    (equity vs preço), a referência Nash quando aplicável e o convite para
    discutir com o coach."""
    from app.analysis.equity import equity_vs_random

    verb = choice.upper()
    real = drill["actual"].upper()
    if drill.get("actual_amount_bb"):
        real += f" {drill['actual_amount_bb']:g}bb"
    if drill.get("all_in"):
        real += " (all-in)"

    lines = [
        f"Você escolheu: *{verb}*",
        f"Na mão real: *{real}* — a mão terminou em *{drill['net_bb']:+.1f} BB* para você.",
    ]

    # a matemática do spot: equity da sua mão vs o preço oferecido
    eq = None
    try:
        eq = equity_vs_random(drill["cards"], drill.get("board") or [],
                              1, iterations=2500, seed=11)
    except Exception:
        pass
    req = drill.get("required_eq")
    if eq is not None and req:
        margin = (eq - req) * 100
        if margin >= 3:
            veredito = "CALL é lucrativo pela matemática pura"
        elif margin <= -3:
            veredito = "pagar QUEIMA fichas pela matemática pura"
        else:
            veredito = "spot no fio da navalha — a leitura do vilão decide"
        lines.append(
            f"\n📐 *A conta:* sua equity ≈ *{eq*100:.0f}%* vs *{req*100:.0f}%* "
            f"exigidos pelo pote → {veredito}.\n"
            f"_(equity vs mão aleatória; contra o range real do vilão muda — "
            f"pergunte ao coach!)_"
        )
    elif eq is not None:
        lines.append(
            f"\n📐 Sem aposta a pagar; sua equity bruta ≈ *{eq*100:.0f}%* — "
            "aqui a pergunta certa é valor vs controle do pote."
        )

    # referência Nash para pré-flop de stack curto em torneio
    stack_bb = drill.get("stack_bb")
    if (stack_bb and stack_bb <= 20 and drill.get("street") == "preflop"
            and drill.get("format") in ("tournament", "sng")):
        from app.analysis.pushfold import push_fold

        pf = push_fold(drill["cards"], stack_bb, drill.get("position") or "MP")
        if pf.get("applicable"):
            lines.append(
                f"\n⚖️ *Equilíbrio ({stack_bb:g}bb, {drill.get('position') or '?'}):* "
                f"{pf['decision'].upper()} — sua mão está no top {pf['hand_top_pct']}% "
                f"e o range de shove é ≈{pf['shove_range_pct']}%."
            )

    lines.append("\n💬 _Discorda ou quer aprofundar? Responda aqui que o coach "
                 "abre o spot com você._")
    return "\n".join(lines)


def storyboard_spot_from_drill(drill: dict, choice: str | None = None) -> dict | None:
    """Monta a spec do storyboard (render_hand_strip) a partir de um drill.

    Usa as bandas já cortadas em `drill['storyboard']` (montadas no build_drill,
    com a street da decisão como último quadro). Matemática e veredito são
    DETERMINÍSTICOS (equity/pot-odds/EV) — custo zero de LLM, coerente com o
    reveal_drill. None se não houver bandas."""
    from app.analysis.equity import equity_vs_random
    from app.analysis.tools import ev_call

    bands = drill.get("storyboard") or []
    if not bands:
        return None

    eq = None
    try:
        eq = equity_vs_random(drill["cards"], drill.get("board") or [],
                              1, iterations=3000, seed=11)
    except Exception:
        pass
    need = drill.get("required_eq")
    to_call = drill.get("to_call_bb") or 0
    math_d: dict = {}
    if eq is not None:
        math_d = {"equity": eq, "need": need}
        if need and to_call:
            pot_now = (drill.get("pot_bb") or 0) + to_call
            math_d["ev_bb"] = ev_call(eq, pot_now, to_call)
            math_d["note"] = (f"o call precisaria de {need*100:.0f}% e você "
                              f"tem ~{eq*100:.0f}%")

    # recomendação determinística (só quando há preço a pagar e margem clara)
    verdict, verdict_text, correct = "mista", "", ""
    actual = (drill.get("actual") or "").lower()
    ch = (choice or "").lower()
    if eq is not None and need and to_call:
        margin = eq - need
        if margin >= 0.03:
            rec, rec_txt = "call", "CALL — a matemática do pote paga."
        elif margin <= -0.03:
            rec, rec_txt = "fold", "FOLD — pagar queima fichas."
        else:
            rec, rec_txt = "mista", "Spot no fio da navalha — a leitura decide."
        correct = rec_txt
        if rec == "mista":
            verdict = "mista"
            verdict_text = (
                f"Spot marginal: sua equity (~{eq*100:.0f}%) bate quase exato "
                f"os {need*100:.0f}% que o pote exige. Aqui não é conta, é "
                "leitura — contra um vilão que blefa, paga; contra um pedra, "
                "descarta.")
        else:
            aligned = (ch in ("call", "raise") and rec == "call") or \
                      (ch == "fold" and rec == "fold")
            verdict = "boa" if aligned else "ruim"
            verdict_text = (
                f"Pela matemática pura, sua equity é ~{eq*100:.0f}% e o pote "
                f"exige {need*100:.0f}%. " +
                ("Você escolheu certo. " if aligned else
                 "Sua escolha foge da conta aqui. ") +
                "Contra o range real do vilão muda — pergunte ao coach pra "
                "abrir a leitura.")
    else:
        verdict = "mista"
        verdict_text = (
            "Sem aposta a pagar, o jogo aqui é valor vs controle do pote — "
            "não tem gabarito de conta única. Responda que o coach abre a "
            "linha com você.")
        if eq is not None:
            verdict_text = (f"Sua equity bruta é ~{eq*100:.0f}%. " + verdict_text)

    stack = drill.get("stack_bb")
    return {
        "title": "Sua mão — o filme",
        "hero_cards": drill.get("cards") or [],
        "position": drill.get("position"),
        "stack_bb": stack,
        "blinds": drill.get("blinds"),
        "streets": bands,
        "math": math_d,
        "verdict": verdict,
        "verdict_text": verdict_text,
        "correct": correct,
    }

