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
PENDING_CHARTS: dict[int, list[tuple[bytes, str]]] = {}


def _stash_charts(telegram_id: int, specs: list, user_id: str | None = None) -> None:
    """Processa as specs coletadas do coach: notas de caderno vão para o banco;
    gráficos (máx. 2) são renderizados para envio pelo handler."""
    if not specs:
        return
    from app.analysis.range_chart import render_spec

    notes = [s for s in specs if s and s[0] == "note"]
    chart_specs = [s for s in specs if s and s[0] != "note"]

    if notes and user_id:
        repo = get_repository()
        for _, kind, note in notes[:3]:
            repo.save_note(user_id, kind, note)

    charts = []
    for spec in chart_specs[:2]:
        rendered = render_spec(spec)
        if rendered:
            charts.append(rendered)
    if charts:
        PENDING_CHARTS[telegram_id] = charts


def pop_charts(telegram_id: int) -> list[tuple[bytes, str]]:
    return PENDING_CHARTS.pop(telegram_id, [])


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
    content: bytes, fmt: str, telegram_id: int, username: str | None, lang: str = "pt"
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
                "😵 Meu banco de dados está instável agora e não consigo conferir "
                "sua cota. Tente de novo em alguns minutos — sua mão não foi "
                "descontada."
            )
        if not quota.allowed or (quota.remaining >= 0 and inflight >= quota.remaining):
            return (
                "🚦 Você atingiu o limite gratuito deste mês "
                f"({quota.plan}: análises esgotadas).\n"
                "Seu limite renova no próximo mês. Planos pagos chegam em breve!"
            )
        _INFLIGHT[telegram_id] = inflight + 1
    try:
        return _process_upload_inner(
            content, fmt, telegram_id, username, lang, repo, user
        )
    finally:
        with _inflight_lock():
            _INFLIGHT[telegram_id] = max(0, _INFLIGHT.get(telegram_id, 1) - 1)


def _process_upload_inner(
    content, fmt, telegram_id: int, username: str | None, lang: str, repo, user
) -> str:

    # ---- arquivo bruto no Storage (auditoria/reprocessamento) ----
    raw_path = None
    if repo.enabled and isinstance(content, (bytes, bytearray)):
        raw_path = repo.store_raw_file(telegram_id, bytes(content), fmt)
    elif repo.enabled and isinstance(content, str):
        raw_path = repo.store_raw_file(telegram_id, content.encode(), fmt or "txt")

    # ---- ingestão ----
    result = ingest(content, source_format=fmt)
    if not result.hands:
        # registra a falha COM um trecho do conteúdo — permite diagnóstico e
        # correção do parser sem pedir o arquivo de novo
        excerpt = ""
        if isinstance(content, (bytes, bytearray)):
            excerpt = bytes(content[:500]).decode("utf-8", "ignore")
        elif isinstance(content, str):
            excerpt = content[:500]
        repo.log_event(
            telegram_id, username, "upload_failed",
            {"format": fmt, "note": result.note, "excerpt": excerpt,
             "raw_path": raw_path},
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
    key_hands = None
    if is_tournament:
        structured = analyze_tournament(hands)
        key_hands = select_key_hands(hands, k=MAX_COACHED_HANDS)
    else:
        structured = analyze_hand(hands[0])

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
    chart_specs: list = []
    coaching = coach(structured, stats.__dict__, lang=lang, key_hands=key_hands,
                     collect_charts=chart_specs)
    _stash_charts(telegram_id, chart_specs, user["id"] if user else None)

    # quadro-resumo do campeonato: chega ANTES dos outros gráficos
    if is_tournament and len(hands) >= 3:
        try:
            from app.analysis.tournament_board import render_tournament_board

            board = render_tournament_board(hands)
            PENDING_CHARTS.setdefault(telegram_id, []).insert(0, board)
        except Exception as exc:
            log.warning("quadro do torneio falhou: %s", exc)

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

    from app.agent.llm import followup

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
        return (
            "Não consegui aprofundar agora (LLM indisponível). "
            "Tente de novo em instantes."
        )

    ctx["history"] = (ctx["history"] + [{"q": question, "a": answer}])[-_HISTORY_CAP:]

    repo = get_repository()
    if repo.enabled:
        repo.log_event(telegram_id, username, "followup", {"q": question[:300]})
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

    m = match_pro_style(stats.vpip, stats.pfr, stats.af, stats.three_bet, desired)
    png = render_style_png(stats.vpip, stats.pfr, stats.af, stats.three_bet)

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
    """Perfil atual + benchmark contra o field da ferramenta + caderno."""
    repo = get_repository()
    stats = None
    user = None
    if repo.enabled:
        user = repo.get_or_create_user(telegram_id, username)
        hands = repo.get_all_hands(user["id"]) if user else []
        if hands:
            stats = compute_player_stats(hands, player=None)
    if stats is None:
        recent = RECENT_HANDS.get(telegram_id, [])
        stats = compute_player_stats(recent, player=None) if recent else None
    if not stats or not stats.hands:
        return None

    msg = (
        f"*Seu perfil* ({stats.hands} mãos)\n"
        f"• VPIP {stats.vpip}% | PFR {stats.pfr}% | 3-bet {stats.three_bet}%\n"
        f"• Agressão (AF) {stats.af}\n"
        f"• Estilo: *{stats.label}*"
    )

    # com amostra decente, aproxima dos grandes nomes (perfis públicos)
    if stats.hands >= 30:
        from app.analysis.pro_styles import match_pro_style

        m = match_pro_style(stats.vpip, stats.pfr, stats.af, stats.three_bet)
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
        msg += (
            f"\n\n*Você vs o field KKNuths* ({len(others)} jogadores)\n"
            f"• VPIP: você {stats.vpip}% · field {med_vpip:.0f}%\n"
            f"• PFR: você {stats.pfr}% · field {med_pfr:.0f}%"
        )

    if user:
        notes = repo.get_notes(user["id"], limit=3)
        if notes:
            msg += "\n\n📒 *Caderno do coach:*"
            for n in reversed(notes):
                msg += f"\n• _[{n['kind']}]_ {n['note']}"

    msg += "\n\n📈 Veja sua linha do tempo com /evolucao"
    return msg


def build_simulation(telegram_id: int) -> dict | None:
    """Monta uma simulação jogável a partir de uma mão real do usuário.

    Escolhe a mão com mais pontos de decisão do herói. Retorna None sem material.
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
            lines.append(f"\n🃏 *{e['street'].upper()}*  (mesa: {board})")
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


def sim_whatif(sim: dict) -> str | None:
    """Modo "e se": veredito do coach sobre a linha alternativa escolhida.

    None quando o LLM está indisponível (o resumo determinístico já foi enviado).
    """
    from app.agent.llm import evaluate_line

    payload = {
        "hero_cards": sim["cards"],
        "position": sim["position"],
        "big_blind": sim["bb"],
        "resultado_real_bb": sim["net_bb_real"],
        "decisoes": sim["results"],
    }
    return evaluate_line(payload)


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
            price = f" — equity mínima p/ pagar (chance de ganhar necessária): {req*100:.0f}%"
        lines.append(
            f"{icon} *{r['street']}*: você: {r['choice']} | na mão real: {r['actual']}{price}"
        )
    lines.append(
        f"\nResultado real da mão: {sim['net_bb_real']:+.1f} BB "
        f"(BB = big blind, a aposta grande da mesa)."
    )
    lines.append(
        f"Você repetiu a linha real em {matches}/{len(sim['results'])} decisões."
    )
    lines.append("\n💬 _Quer discutir alguma dessas decisões? É só responder aqui._")
    return "\n".join(lines)


def build_drill(telegram_id: int) -> dict | None:
    """Monta um spot de treino a partir das mãos do usuário (mais recente primeiro
    com hero conhecido). Retorna None se não houver material."""
    import random

    hands = list(RECENT_HANDS.get(telegram_id, []))
    repo = get_repository()
    if not hands and repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        if user:
            hands = repo.get_all_hands(user["id"], limit=200)
    candidates = [h for h in hands if h.hero and h.hero_cards and h.stakes.big_blind]
    if not candidates:
        return None

    h = random.choice(candidates)
    seat = h.hero_seat()
    stack_bb = round((seat.stack / h.stakes.big_blind), 1) if seat else None
    analysis = analyze_hand(h)

    # ação real do herói no preflop (primeira não-post)
    actual = "fold"
    for s in analysis["spots"]:
        if s["street"] == "preflop":
            actual = "raise" if s["decision"] == "aggression" else "call"
            break

    return {
        "hand_id": h.hand_id,
        "cards": h.hero_cards,
        "position": analysis["position"],
        "stack_bb": stack_bb,
        "blinds": f"{h.stakes.small_blind:g}/{h.stakes.big_blind:g}",
        "format": h.format.value,
        "actual": actual,
        "net_bb": analysis["net_bb"],
        "summary": analysis["summary"],
    }


def reveal_drill(drill: dict, choice: str) -> str:
    """Compara a escolha do usuário com o que aconteceu + referência push/fold."""
    lines = [
        f"Você escolheu: *{choice.upper()}*",
        f"Na mão real você fez: *{drill['actual'].upper()}* "
        f"(resultado: {drill['net_bb']:+.1f} BB)",
    ]
    stack_bb = drill.get("stack_bb")
    if stack_bb and stack_bb <= 20 and drill["format"] in ("tournament", "sng"):
        from app.analysis.pushfold import push_fold

        pf = push_fold(drill["cards"], stack_bb, drill.get("position") or "MP")
        if pf.get("applicable"):
            lines.append(
                f"📐 Referência Nash ({stack_bb}bb, {drill['position']}): "
                f"*{pf['decision'].upper()}* — sua mão está no top {pf['hand_top_pct']}%, "
                f"range de shove ≈ {pf['shove_range_pct']}%."
            )
    lines.append(f"\n_{drill['summary']}_")
    return "\n".join(lines)
