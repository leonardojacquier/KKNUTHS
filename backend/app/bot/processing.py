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
from app.analysis.tools import fmt_chips as _fmt_chips
from app.bot.progresso import marcar
from app.config import get_settings
from app.db import get_repository
from app.bot.memoria_do_processo import (esquecer, guardar_com_prazo,
                                        lembrar, varrer_expirados)
# EXTRAÍDOS daqui (o arquivo passou de 3.870 linhas): funções puras de
# leitura de mão e de montagem de teclado. Reexportadas para não quebrar
# quem importa de `processing` — o import antigo continua valendo.
from app.bot.leitura_da_mao import (_decision_aggressor, _describe_safe,
                                    _fmt_bb, _mark_aggressor,
                                    _preflop_summary, _pretty_cards,
                                    _seats_at_decision, _walk_hand)
from app.analysis.stats import perfil_que_pode_ser_dito
from app.bot.menus import (_DRILL_ACTIONS, action_menu_rows,
                          botoes_pos_treino, drill_action,
                          size_menu_rows, sizing_amounts)
from app.ingestion import ingest
from app.models.canonical import CanonicalHand
from app.quota import (ADMIN_TELEGRAM_ID, MAX_COACHED_HANDS, PLANOS_MANUAIS,
                       check_quota, consume_quota, limite_do_plano)

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

# anti-repetição do /treino: as últimas mãos mostradas por usuário (não cair
# sempre na mesma) + as streets recentes (rotaciona o TIPO de spot: não só
# shove pré-flop)
RECENT_DRILLS: dict[int, list[str]] = {}
_RECENT_DRILL_STREETS: dict[int, list[str]] = {}
_DRILL_MEMORY = 15
_STREET_MEMORY = 8

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

    def _key(s: tuple) -> tuple:
        """Identidade SEMÂNTICA do gráfico: push_fold + send_range_chart do
        MESMO spot geravam specs diferentes (nash vs nashmode) e o mesmo
        gráfico saía DUAS vezes; range igual com título diferente idem."""
        try:
            if s[0] == "range":
                return ("range", str(s[1]).replace(" ", "").lower())
            if s[0] == "nash":
                return ("nash", str(s[1]).upper(), round(float(s[2]), 1), "freq")
            if s[0] == "nashmode":
                mode = s[3] if len(s) > 3 else "freq"
                return ("nash", str(s[1]).upper(), round(float(s[2]), 1), mode)
            if s[0] == "nashpos":
                mode = s[3] if len(s) > 3 else "freq"
                return ("pos", str(s[1]).upper(), round(float(s[2]), 1), mode)
            if s[0] == "spot":
                return ("spot", s[1], str(s[2]).upper(),
                        round(float(s[3]), 1), s[4] or "freq", s[5],
                        round(float(s[6]), 1), int(s[7]))
        except Exception:
            pass
        return s

    chart_specs, seen = [], set()
    for s in specs:  # dedupe preservando ordem: mesmo conteúdo 2x = 1 gráfico
        if s and s[0] != "note" and _key(s) not in seen:
            seen.add(_key(s))
            chart_specs.append(s)

    # pedido do admin: range Nash vem ACOMPANHADO do EV por mão como segundo
    # gráfico — a frequência diz O QUE jogar; o EV diz QUANTO cada mão rende
    for s in list(chart_specs):
        k = _key(s)
        ev = None
        if k[0] == "nash" and k[3] == "freq":
            ev = ("nashmode", k[1], k[2], "ev", 1.0)
        elif k[0] == "spot" and k[4] == "freq":
            ev = ("spot", s[1], s[2], s[3], "ev", s[5], s[6], s[7])
        elif s[0] == "posflop" and s[7] == "ev":
            # pós-flop: o VALOR de cada mão sozinho não diz o que fazer com
            # ela — a frequência de agressão vem junto, do MESMO equilíbrio
            # (o solve fica em cache, o segundo gráfico é de graça)
            ev = ("posflop", s[1], s[2], s[3], s[4], s[5], s[6], None)
        elif k[0] == "pos" and k[3] == "freq":
            # open-shove de mesa cheia: o EV por mão agora existe (solver
            # multiway) — vem junto, igual ao par de SB vs BB
            ev = ("nashpos", k[1], k[2], "ev")
        if ev and _key(ev) not in seen:
            seen.add(_key(ev))
            chart_specs.insert(chart_specs.index(s) + 1, ev)
            break

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
        guardar_com_prazo(PENDING_CHARTS, telegram_id,
                          (_time.time(), charts), _CHART_TTL)


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

    guardar_com_prazo(PENDING_PASTE, telegram_id,
                      (text[-_PASTE_CAP:], time.time(), parts), _PASTE_TTL,
                      quando=lambda v: v[1])


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
    lembrar(RECENT_HANDS, telegram_id, (cur + hands)[-_RECENT_CAP:])


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
            from app.quota import texto_cota_esgotada

            # evento próprio: bater no teto é o momento em que o aluno some,
            # e sem isso o portal não distingue "parou de usar" de "não pôde"
            if repo.enabled:
                repo.log_event(telegram_id, username, "cota_esgotada",
                               {"plano": quota.plan})
            return texto_cota_esgotada(quota.plan)
        _INFLIGHT[telegram_id] = inflight + 1
    try:
        return _process_upload_inner(
            content, fmt, telegram_id, username, lang, repo, user, caption
        )
    finally:
        with _inflight_lock():
            restante = max(0, _INFLIGHT.get(telegram_id, 1) - 1)
            if restante:
                _INFLIGHT[telegram_id] = restante
            else:
                esquecer(_INFLIGHT, telegram_id)


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
    marcar(telegram_id, "Lendo o arquivo")
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
        if fmt in ("pppoker_replay", "suprema_replay"):
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
    marcar(telegram_id, f"Guardando {len(hands)} mão(s)"
           if len(hands) > 1 else "Guardando a mão")
    hand_row_ids: list[str | None] = []
    if user:
        upload_id = repo.save_upload(
            user["id"], raw_path, result.source_format, result.site, result.confidence
        )
        for h in hands:
            hand_row_ids.append(repo.save_hand(user["id"], h, upload_id))

    # ---- análise determinística ----
    marcar(telegram_id, f"Calculando {len(hands)} mão(s)"
           if len(hands) > 1 else "Calculando a mão")
    is_tournament = hands[0].format.value in ("tournament", "sng") and len(hands) > 1
    lembrar(LAST_UPLOAD_KIND, telegram_id,
            "tournament" if is_tournament else "hand")
    key_hands = None
    if is_tournament:
        structured = analyze_tournament(hands)
        key_hands = select_key_hands(hands, k=MAX_COACHED_HANDS)
    else:
        structured = analyze_hand(hands[0])
        if result.source_format == "image":
            _augment_snapshot(structured, hands[0])
        lembrar(LAST_HAND_META, telegram_id, {
            "hand_id": hands[0].hand_id,
            "position": structured.get("position"),
            "stack_bb": structured.get("effective_bb")
            or structured.get("hero_stack_bb"),
        })
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
    # só o que conta para o PERFIL desce do banco: replay e print são
    # descartados aqui de qualquer jeito, e baixá-los para jogar fora custa
    # 15 MB e 2.3 s de pydantic a cada envio quando o histórico cresce
    all_hands, fora = repo.get_hands_para_perfil(user["id"]) if user else ([], 0)
    stats_source = all_hands or RECENT_HANDS.get(telegram_id, hands)
    stats = compute_player_stats(stats_source, player=None,
                                 fora_da_amostra=fora if all_hands else 0)
    # só grava stats calculadas do HISTÓRICO COMPLETO: uma falha transitória do
    # get_all_hands não pode sobrescrever o perfil acumulado com a amostra em
    # memória (ex.: 5000 mãos viram 3)
    if user and all_hands and stats.hands:
        repo.upsert_player_stats(user["id"], stats)
        # ponto na linha do tempo de evolução (/evolucao): net do lote atual
        repo.snapshot_player_stats(user["id"], stats,
                                   net_bb=structured.get("net_bb"))

    # ---- coaching (Claude com tools; fallback determinístico) ----
    from app.agent.llm import set_tool_chat, set_tool_user

    set_tool_user(user["id"] if user else None)  # habilita search_hands
    set_tool_chat(telegram_id)
    # ICM automático: premiação salva pelo aluno entra no contexto — o coach
    # calcula bubble factor com os stacks da mão sem pedir os payouts de novo
    if user and structured.get("format") == "tournament":
        saved = repo.get_user_meta(user["id"], "payouts")
        if saved and saved.get("valores"):
            structured["payouts_salvos"] = saved
    # TORNEIO SEM ICM É CASH GAME COM BLIND SUBINDO. Sem a premiação o bf
    # fica 1.0 calado — 25 de 25 análises de torneio saíram assim. Aqui o
    # motor MEDE o que a bolha mudaria (o range de call cai de ~36% para
    # ~14%) e entrega o número, para o coach dizer isso em uma linha em vez
    # de dar aula de ICM ou ficar mudo.
    if structured.get("format") == "tournament":
        try:
            from app.analysis.torneio import situacao_icm

            falta = situacao_icm(structured, structured.get("payouts_salvos"))
            if falta:
                structured["falta_icm"] = falta
        except Exception as exc:
            log.warning("situação de ICM falhou: %s", exc)
    # MEMÓRIA: o que o coach já viu — as mãos parecidas deste aluno e os
    # padrões destilados de TODOS. Sem isto, 385 análises indexadas ficavam
    # só sendo escritas (o único leitor era /ask, usado zero vezes) e o
    # aprendizado de um aluno nunca chegava no outro.
    saberes_usados: list[str] = []
    try:
        from app.agent.memoria import montar as montar_memoria

        bloco, saberes_usados = montar_memoria(
            structured, repo, user["id"] if user else None, embed_text)
        structured.update(bloco)
    except Exception as exc:
        log.warning("memória do coach falhou: %s", exc)

    # A HISTÓRIA DO RESULTADO vem da conta, não da imaginação. Sem isto o
    # coach fechou uma mão dominada (29% pré, 0% no turn) com "cooler de
    # river" e chamou os dois pares DA MESA de "seus dois pares" — o aluno
    # que sabe jogar lê isso e perde a confiança no resto da análise.
    historia = None
    if hands and not is_tournament:
        try:
            from app.analysis.historia import historia_do_resultado

            historia = historia_do_resultado(hands[0])
            if historia:
                structured["historia_do_resultado"] = historia
                structured["instrucao_historia"] = (
                    "A trajetória acima é CONTA FEITA rua a rua contra as "
                    "cartas reais do showdown. O parágrafo final sobre o "
                    "desfecho segue a 'leitura' à risca — quem estava na "
                    "frente em cada rua não é opinião. Cite as mãos finais "
                    "pelos nomes dados (sua_mao_final: dois pares da MESA "
                    "não são 'seus dois pares').")
        except Exception as exc:
            log.warning("história do resultado falhou: %s", exc)

    chart_specs: list = []
    marcar(telegram_id, "Montando o relatório do torneio"
           if is_tournament else "Escrevendo a análise")
    # perfil só vai pro coach se for dizível. Amostra escolhida a dedo dava
    # VPIP 94% pra quem joga 26%, e o coach repetia isso como fato na análise.
    perfil = stats.__dict__ if stats.publicavel else {
        "indisponivel": True,
        "por_que": ("O aluno só mandou mãos avulsas (replay/print), que ele "
                    "escolheu — não dá pra tirar VPIP/PFR/3-bet daí. NÃO cite "
                    "nenhuma frequência do jogo dele nem rótulo de estilo. "
                    "Se o estilo importar pra resposta, peça um export da "
                    "sessão inteira."),
        "maos_avulsas": stats.detail.get("maos_fora_da_amostra", 0)}
    # roteamento por complexidade (atras de flag; vazio = tudo no modelo
    # cheio). Mao de decisao unica pre-flop pode ir num modelo mais barato —
    # o juiz compara a clareza POR MODELO antes de a flag ligar de verdade.
    from app.agent.llm import mao_simples

    settings_rt = get_settings()
    modelo_escolhido = (settings_rt.simple_hand_model
                       if settings_rt.simple_hand_model and not is_tournament
                       and mao_simples(structured) else None)
    coaching = coach(structured, perfil, lang=lang, key_hands=key_hands,
                     collect_charts=chart_specs, model=modelo_escolhido)

    # CONFERE os fatos que dá para provar: "só te vira favorito com QQ ou AA"
    # saiu numa análise de KK, e KK ganha de QQ em 80%. O aluno que acredita
    # passa a foldar KK contra 4-bet. O prompt já proíbe inventar (F1/F4) e
    # saiu assim mesmo — então a conta confere antes de entregar.
    if coaching and hands and getattr(hands[0], "hero_cards", None):
        try:
            from app.bot.guarda_fatos import conferir_dominancia

            from app.bot.guarda_fatos import conta_sem_numero

            # o BOARD vai junto: com mesa, "só perdia pra 77" é pergunta
            # sobre a mão FEITA. Conferir isso com equity pré-flop dava a
            # resposta certa para a pergunta errada.
            coaching, mentiras = conferir_dominancia(
                coaching, list(hands[0].hero_cards),
                list(getattr(hands[0], "final_board", None) or []))
            if mentiras and repo.enabled:
                repo.log_event(telegram_id, username, "fato_corrigido",
                               {"maos": mentiras[:6],
                                "heroi": list(hands[0].hero_cards)})
            # "A conta que mais pesa: você paga sempre" — prosa com nome de
            # conta. Só mede: reescrever prosa de LLM na marra estraga mais
            # do que conserta, mas a TAXA diz se o prompt está errado.
            vazias = conta_sem_numero(coaching)
            if vazias and repo.enabled:
                repo.log_event(telegram_id, username, "conta_sem_numero",
                               {"trecho": vazias[0]})
            # "cooler de river" numa mão em que o aluno nunca esteve na
            # frente: a trajetória prova que a virada não existiu
            from app.analysis.historia import (citou_showdown_errado,
                                               narrou_azar_inexistente)

            trecho = narrou_azar_inexistente(coaching, historia)
            if trecho and repo.enabled:
                repo.log_event(telegram_id, username, "narrativa_enganosa",
                               {"trecho": trecho[:200],
                                "equity": (historia or {}).get("equity_pct")})
            # "o vilão apareceu com 77" quando ele mostrou 7♦2♦: as cartas
            # do showdown são dado gravado — citar errado inverte o desfecho
            # da mão na cabeça do aluno (caso real: narrou derrota numa mão
            # que ele GANHOU). CORRIGE, não só anota: até aqui isto era
            # telemetria, e telemetria não impede o aluno de ler a mentira.
            if hands:
                from app.analysis.historia import (cita_mao_impossivel,
                                                   corrigir_showdown)

                coaching, erro_sd = corrigir_showdown(coaching, hands[0])
                if erro_sd and repo.enabled:
                    repo.log_event(telegram_id, username, "showdown_errado",
                                   {"citado": erro_sd["citado"],
                                    "reais": erro_sd["reais"],
                                    "corrigido_para": erro_sd.get(
                                        "corrigido_para"),
                                    "trecho": erro_sd["trecho"][:200]})
                # par citado que não cabe no baralho ("77" com três setes já
                # à vista). Só mede: a frase inteira costuma estar podre, e
                # trocar o rank não conserta o raciocínio em volta.
                impossiveis = cita_mao_impossivel(coaching, hands[0])
                if impossiveis and repo.enabled:
                    repo.log_event(telegram_id, username, "mao_impossivel",
                                   {"citadas": impossiveis[:4]})
        except Exception as exc:
            log.warning("guarda de fatos falhou: %s", exc)

    _stash_charts(telegram_id, chart_specs, user["id"] if user else None)

    # mão única (replay da PPPoker, .txt, print legível): o FILME da mão
    # inteira — street a street, lance a lance — vai junto da análise.
    # Feedback do admin: "o link do pppoker tem que contar a mão toda".
    if not is_tournament:
        try:
            from app.models.canonical import ActionType as _AT

            h0 = hands[0]
            has_story = any(a.type != _AT.POST
                            for st in h0.streets for a in st.actions)
            film = hand_film_png(h0) if (has_story and h0.hero_cards) else None
            if film:
                import time as _time

                _ts, _lst = PENDING_CHARTS.get(telegram_id) or (0.0, [])
                _lst.insert(0, (film, "🎬 O filme da mão — cada street com a "
                                      "conta na figura (▲/▼ = à frente/atrás "
                                      "da mão que ele mostrou, o confronto do "
                                      "replay). O veredito da JOGADA (boa/ruim "
                                      "vs o range) está na análise em texto."))
                PENDING_CHARTS[telegram_id] = (_time.time(), _lst)
        except Exception as exc:
            log.warning("filme da mão falhou: %s", exc)

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
            guardar_com_prazo(PENDING_DOCS, telegram_id,
                              (_time.time(), _docs), _CHART_TTL)
        except Exception as exc:
            log.warning("relatório mão a mão falhou: %s", exc)

    # conta o uso dos saberes coletivos: é o que vai dizer, daqui a um mês,
    # se a memória serviu — ou se virou outro /ask que ninguém chama
    if saberes_usados:
        try:
            repo.marcar_uso_conhecimento(saberes_usados)
        except Exception:
            log.debug("marcar uso do conhecimento falhou", exc_info=True)

    # ---- base de conhecimento ----
    if user and hand_row_ids and hand_row_ids[0]:
        try:
            embedding = embed_text(coaching)
            repo.save_hand_analysis(
                hand_row_ids[0], structured, coaching, embedding,
                modelo=modelo_escolhido or settings_rt.analysis_model)
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
    # a conversa anterior ENCERROU aqui (mão nova = contexto novo): destila o
    # que ela revelou sobre o aluno pro caderno do coach, em background
    _notebook_from_session(LAST_ANALYSIS.get(telegram_id), telegram_id)
    abrir_conversa(
        telegram_id,
        context={"analysis": structured, "key_hands": key_hands,
                 "coaching_anterior": coaching},
        hand_row_id=hand_row_ids[0] if hand_row_ids else None,
        hand_id=hands[0].hand_id if hands else None,
        user_id=user["id"] if user else None,
        sem_mao=not hands,
        image_b64=image_b64, media=media)
    persist_conversation(telegram_id)

    # PROCEDÊNCIA: fonte incerta (print/foto) abre declarando o que foi lido
    # e avisa quando as duas leituras discordaram. Sem isso, análise de print
    # chegava com a MESMA cara de análise de replay exato — e o aluno não
    # tinha como saber quando duvidar.
    from app.analysis.procedencia import bloco_leitura, selo_procedencia

    leitura = ""
    try:
        divs = (structured.get("leitura_dupla") or {}).get("divergencias")
        leitura = bloco_leitura(hands[0] if hands else None,
                                result.source_format, result.confidence, divs)
        if leitura:
            leitura += "\n\n"
    except Exception:
        leitura = ""

    header = f"📊 *{len(hands)} mão(s)* lidas de {result.site}.\n"
    footer = ("\n\n" + selo_procedencia(result.source_format, result.confidence)
              + "\n💬 _Discorda ou quer aprofundar? É só responder aqui._")
    if quota_after.remaining >= 0:
        footer += f"\n_Análises restantes no mês: {quota_after.remaining}_"
    return header + "\n" + leitura + coaching + footer


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
    # leitura DUPLA do print (item 5 do roadmap-10): se as duas passadas
    # divergiram, o coach ABRE confirmando o dado com o aluno — nunca chuta
    try:
        from app.agent.llm import LAST_VISION_CHECK

        if LAST_VISION_CHECK and LAST_VISION_CHECK.get("divergencias"):
            structured["leitura_dupla"] = LAST_VISION_CHECK
            structured["instrucao_snapshot"] += (
                " ATENÇÃO: a dupla leitura da imagem DIVERGIU (veja "
                "leitura_dupla). ABRA a resposta confirmando o dado divergente "
                "com o aluno ('li A♠K♦ — confere?') antes de qualquer conta."
            )
    except Exception:
        pass


# campos-gabarito que o analyzer entrega hoje: se a conversa persistida não
# os tiver, ela é de uma versão anterior e precisa de refresh
_GABARITO_KEYS = ("linha_da_mao", "hand_by_street", "showdown_cards",
                  "showdown_hands", "hero_final_hand", "pot_winners",
                  "pko", "bounties", "cartas_texto", "textura_do_board")


def _refresh_gabarito(ctx: dict, telegram_id: int) -> None:
    """Recomputa os campos-gabarito da análise a partir da mão salva quando a
    conversa persistida veio de uma versão anterior do analyzer."""
    try:
        an = (ctx.get("context") or {}).get("analysis")
        if not (isinstance(an, dict) and ctx.get("hand_row_id")):
            return
        if all(k in an for k in _GABARITO_KEYS):
            return
        h = get_repository().get_hand_canonical(ctx["hand_row_id"])
        if not h:
            return
        from app.agent.analyzer import analyze_hand

        fresh = analyze_hand(h)
        an.update({k: fresh[k] for k in _GABARITO_KEYS if k in fresh})
        persist_conversation(telegram_id)
    except Exception:
        pass  # refresh é rede de segurança; nunca derruba a conversa


def persist_conversation(telegram_id: int) -> None:
    """Grava o estado da conversa no banco (sem a imagem — pesada demais).

    Chamado a cada mudança de contexto/troca: restart do auto-deploy deixa
    de apagar o fio da conversa (item 4 do roadmap-10)."""
    ctx = LAST_ANALYSIS.get(telegram_id)
    if not ctx:
        return
    try:
        state = {k: v for k, v in ctx.items() if k not in ("image_b64", "media")}
        state["history"] = (state.get("history") or [])[-_HISTORY_CAP:]
        get_repository().set_conversation(telegram_id, state)
    except Exception:
        pass  # persistência é rede de segurança; nunca derruba a conversa


def redefine_hero(telegram_id: int, nome: str,
                  cards: list[str] | None = None) -> dict:
    """O aluno disse quem ELE é na mão ('eu sou o dscholze1979') — refaz a
    análise inteira do ponto de vista certo. Caso real: print com 5
    jogadores, a visão escolheu o herói errado, o aluno explicou e o coach
    não tinha como corrigir.

    Troca o herói no canonical (fuzzy match no nome), move as cartas
    conhecidas pra ele (num print, as cartas abertas são as do aluno; um
    par explícito em `cards` tem prioridade), regrava a mão no banco e
    substitui a análise da conversa. Devolve a análise nova (resumida) ou
    {'error': ...}."""
    import difflib

    ctx = LAST_ANALYSIS.get(telegram_id) or {}
    row_id = ctx.get("hand_row_id")
    repo = get_repository()
    h = repo.get_hand_canonical(row_id) if row_id else None
    if not h:
        return {"error": "não achei a mão desta conversa no banco — peça pro "
                         "aluno reenviar o print/link"}
    alvo = (nome or "").strip()
    nomes = [p.name for p in h.players]
    match = next((n for n in nomes if n.lower() == alvo.lower()), None)
    if not match:
        match = next((n for n in nomes if alvo.lower() in n.lower()), None)
    if not match:
        close = difflib.get_close_matches(alvo, nomes, n=1, cutoff=0.6)
        match = close[0] if close else None
    if not match:
        return {"error": f"'{alvo}' não está na mesa; jogadores: "
                         + ", ".join(nomes)}

    # CARTAS DO NOVO HERÓI — nunca chutar (bug real: mantínhamos as cartas
    # que a visão deu ao herói ERRADO e colávamos no novo). Ordem de
    # confiança: 1) as que o aluno disse; 2) as que ESSE jogador mostrou no
    # showdown; senão ficam DESCONHECIDAS e o coach pergunta antes de opinar.
    from app.agent.llm import _norm_cards

    shown = (h.shown_cards or {}).get(match)
    novas = _norm_cards(cards) if cards else []
    aviso = None
    if len(novas) == 2:
        h.hero_cards = novas
    elif shown and len(shown) == 2:
        h.hero_cards = list(shown)
        aviso = f"cartas de {match} vieram do showdown"
    else:
        # as cartas que estavam salvas eram do herói ANTIGO: descarta
        h.hero_cards = []
        aviso = ("NÃO SEI as cartas do aluno — as que estavam na análise "
                 "eram do herói anterior. PERGUNTE 'quais eram suas cartas?' "
                 "e só afirme a mão feita/veredito depois da resposta.")

    h.hero = match
    for p in h.players:
        p.is_hero = (p.name == match)
    repo.update_hand_canonical(row_id, h)

    fresh = analyze_hand(h)
    an = (ctx.get("context") or {}).get("analysis")
    if isinstance(ctx.get("context"), dict):
        # preserva o que o aluno relatou; o resto é recalculado do zero
        relato = (an or {}).get("relato_do_usuario") if isinstance(an, dict) \
            else None
        if relato:
            fresh["relato_do_usuario"] = relato
        ctx["context"]["analysis"] = fresh
        persist_conversation(telegram_id)
    return {"ok": True, "heroi": match,
            "cartas_conhecidas": bool(h.hero_cards),
            "aviso": aviso,
            "analysis": {k: fresh.get(k) for k in
                         ("hero", "hero_cards", "position", "hero_stack_bb",
                          "net_bb", "hero_final_hand", "linha_da_mao",
                          "cartas_texto", "summary")}}


def abrir_conversa(telegram_id: int, *, context: dict,
                   hand_row_id: str | None = None,
                   hand_id: str | None = None,
                   user_id: str | None = None,
                   sem_mao: bool = False, **extra) -> dict:
    """A ÚNICA porta para começar uma conversa. Exige decidir, na hora de
    escrever, qual mão é esta — ou declarar que não há mão.

    Por que virou função: quatro lugares montavam este dicionário na mão e
    DOIS esqueceram o hand_id (quiz e simulador). O efeito era o mesmo nos
    dois: terminou a jornada, morreram todas as ferramentas de mão. Um
    canário com a lista dos escritores conhecidos não impede o quinto —
    isto impede, porque não existe outro caminho.

    `sem_mao=True` é para conversa que legitimamente não tem mão (coaching
    geral, banca, tilt). É explícito de propósito: esquecer não pode ser o
    default.
    """
    if not (hand_row_id or hand_id or sem_mao):
        raise ValueError(
            "conversa sem mão: passe hand_row_id/hand_id, ou sem_mao=True "
            "se ela realmente não tem mão (esquecer é o bug de sempre)")
    ctx = {
        "context": {**context, **({"hand_id": hand_id} if hand_id else {})},
        "history": [],
        "hand_row_id": hand_row_id,
        "user_id": user_id,
        **extra,
    }
    lembrar(LAST_ANALYSIS, telegram_id, ctx)
    return ctx


def conversation_hand(telegram_id: int) -> "CanonicalHand | None":
    """A mão da conversa ativa: pela linha persistida (banco) ou pelo hand_id
    guardado no contexto (acervo em memória). Base da análise street a street."""
    ctx = LAST_ANALYSIS.get(telegram_id) or {}
    row_id = ctx.get("hand_row_id")
    if row_id:
        h = get_repository().get_hand_canonical(row_id)
        if h:
            return h
    context = ctx.get("context") if isinstance(ctx.get("context"), dict) else {}
    hand_id = _hand_id_no_contexto(context)
    if hand_id:
        for x in _user_hands(telegram_id):
            if x.hand_id == hand_id and x.hero:
                return x
    # falha SILENCIOSA era o pior caso: as tools de mão devolviam "não achei"
    # e o coach virava prosa. Fica registrado pra aparecer no diagnóstico.
    #
    # SÓ para chat de gente. telegram_id <= 0 é sistema por convenção aqui, e
    # a sonda de jornadas exercita este caminho de propósito a cada deploy —
    # 32 registros num dia, afogando o sinal que o evento existe para dar.
    # Alarme que dispara sozinho é alarme que ninguém lê.
    if telegram_id and telegram_id > 0:
        try:
            get_repository().log_event(telegram_id, None,
                                       "sem_mao_na_conversa",
                                       {"chaves": sorted(context)[:8]})
        except Exception:
            pass
    return None


def _hand_id_no_contexto(context: dict) -> str | None:
    """Acha o hand_id no contexto, inclusive ANINHADO.

    Depois de responder um quiz, o contexto vira {'modo':…, 'spot':{…,
    'hand_id':…}} — e a busca só olhava o primeiro nível. Resultado: toda
    ferramenta de mão (gráfico de EV, street a street, potes) morria numa
    conversa de treino, dizendo que não achava a mão. O aluno pediu o
    gráfico três vezes seguidas e recebeu três desculpas.
    """
    if not isinstance(context, dict):
        return None
    direto = context.get("hand_id")
    if isinstance(direto, str) and direto:
        return direto
    for valor in context.values():
        if isinstance(valor, dict):
            achado = _hand_id_no_contexto(valor)
            if achado:
                return achado
    return None


def ensure_hand_context(telegram_id: int, hand_id: str | None) -> bool:
    """Garante que a conversa aponte para ESTA mão (a do filme), pra análise
    street a street achar os âncoras mesmo vindo de um botão. True se ok."""
    ctx = LAST_ANALYSIS.get(telegram_id)
    if ctx and ((ctx.get("context") or {}).get("hand_id") == hand_id
                or (ctx.get("hand_row_id") and not hand_id)):
        return True
    hands = _user_hands(telegram_id)
    h = next((x for x in hands if x.hand_id == hand_id and x.hero), None) \
        if hand_id else next((x for x in hands if x.hero and x.hero_cards), None)
    if not h:
        return bool(ctx)
    try:
        structured = analyze_hand(h)
    except Exception:
        return bool(ctx)
    repo = get_repository()
    user = repo.get_or_create_user(telegram_id, None) if repo.enabled else None
    abrir_conversa(telegram_id, context={"analysis": structured},
                   hand_id=h.hand_id,
                   user_id=user["id"] if user else None)
    persist_conversation(telegram_id)
    return True


def summarize_session_to_notebook(prev: dict | None, telegram_id: int) -> int:
    """Conversa encerrada -> caderno do aluno: destila 0-2 observações NOVAS
    (o que a conversa revelou sobre como o aluno pensa) e grava em
    player_notes. Devolve quantas notas gravou. É o 'coach que te conhece':
    a próxima análise já abre sabendo o que ficou da conversa anterior."""
    try:
        history = (prev or {}).get("history") or []
        user_id = (prev or {}).get("user_id")
        if len(history) < 2 or not user_id:
            return 0
        repo = get_repository()
        if not repo.enabled:
            return 0
        existentes = [n.get("note", "") for n in repo.get_notes(user_id, limit=8)]
        an = ((prev or {}).get("context") or {}).get("analysis") or {}
        resumo = str(an.get("summary") or "")[:400] if isinstance(an, dict) else ""
        from app.agent.llm import session_notebook_notes

        notas = session_notebook_notes(history, resumo, existentes)
        for n in notas:
            repo.save_note(user_id, n["kind"], n["note"])
        if notas:
            repo.log_event(telegram_id, None, "caderno_auto",
                           {"notas": len(notas)})
        return len(notas)
    except Exception:
        logging.getLogger(__name__).debug("caderno_auto falhou", exc_info=True)
        return 0


def _notebook_from_session(prev: dict | None, telegram_id: int) -> None:
    """Dispara o destilador em background — o upload novo não espera LLM."""
    if not prev or len(prev.get("history") or []) < 2:
        return
    import threading

    threading.Thread(target=summarize_session_to_notebook,
                     args=(prev, telegram_id), daemon=True).start()


def process_followup(telegram_id: int, username: str | None, question: str) -> str | None:
    """Continua a conversa sobre a última análise. None se não há contexto.

    Grava o que importa: cada troca vai para bot_events e, quando há mão
    persistida, o insight (Q+A) entra na base de conhecimento com embedding —
    o /ask encontra depois.
    """
    ctx = LAST_ANALYSIS.get(telegram_id)
    if not ctx:
        # bot reiniciou? 1º: o estado COMPLETO da conversa (contexto rico +
        # histórico) persistido no banco — retoma exatamente de onde parou
        saved = get_repository().get_conversation(telegram_id)
        if saved and saved.get("context"):
            ctx = saved
            lembrar(LAST_ANALYSIS, telegram_id, ctx)
    if not ctx:
        # 2º (legado): reconstrói o mínimo a partir da última análise salva
        repo = get_repository()
        if repo.enabled:
            user = repo.get_or_create_user(telegram_id, username)
            latest = repo.get_latest_analysis(user["id"]) if user else None
            if latest and latest.get("summary"):
                canonical = latest.get("canonical") or {}
                ctx = abrir_conversa(
                    telegram_id,
                    context={
                        "analysis_anterior": latest["summary"],
                        "mao": {
                            "hero_cards": canonical.get("hero_cards"),
                            "final_board": canonical.get("final_board"),
                            "site": canonical.get("site"),
                            "format": canonical.get("format"),
                        },
                    },
                    hand_row_id=latest.get("hand_row_id"),
                    hand_id=canonical.get("hand_id"),
                    user_id=user["id"],
                    sem_mao=not (latest.get("hand_row_id")
                                 or canonical.get("hand_id")))

    if not ctx:
        # modo coach geral: pergunta aberta de poker, sem mão específica —
        # personaliza com o perfil do jogador quando existe
        repo = get_repository()
        stats = None
        user = None
        if repo.enabled:
            user = repo.get_or_create_user(telegram_id, username)
            stats = perfil_que_pode_ser_dito(
                repo.get_player_stats(user["id"])) if user else None
        ctx = abrir_conversa(
            telegram_id,
            context={
                "modo": "coaching geral — sem mão específica; responda a "
                "pergunta do aluno como coach de poker (estratégia, tilt, "
                "bankroll, ranges…)",
                "perfil_do_jogador": stats,
            },
            user_id=user["id"] if user else None,
            sem_mao=True)

    # GABARITO SEMPRE FRESCO: a conversa persistida atravessa deploys — e
    # congelava a análise de ANTES de um upgrade do analyzer (caso real: o
    # fix da linha_da_mao deployou e a conversa restaurada seguiu sem ela,
    # repetindo o erro que o deploy corrigia). Se faltar campo-gabarito
    # atual, recomputa da mão salva.
    _refresh_gabarito(ctx, telegram_id)

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

    from app.agent.llm import followup, set_tool_chat, set_tool_user

    set_tool_user(ctx.get("user_id"))  # habilita search_hands na conversa
    set_tool_chat(telegram_id)         # habilita definir_heroi (troca de herói)
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
            from app.agent import llm as _llm

            repo.log_event(telegram_id, username, "followup_failed",
                           {"q": question[:300],
                            "motivo": _llm.LAST_FOLLOWUP_ERROR})
        # Se a API caiu (crédito, chave, limite), o aluno merece a verdade:
        # "me embananei" joga a culpa numa confusão do coach que não houve.
        from app.agent.saude import recado_recente

        return recado_recente() or (
            "Opa, me embananei aqui — me pergunta de novo em um instante? 🙏"
        )

    # GUARDA DA SAÍDA: pediu gráfico e não veio gráfico? pediu EV e a
    # resposta não tem número? Conserta ANTES de enviar, chamando a conta na
    # marra. Mais regra no prompt já foi tentado quatro vezes e falhou.
    try:
        from app.bot.guarda_saida import conferir_e_remediar

        tem_grafico = bool(PENDING_CHARTS.get(telegram_id, (0.0, []))[1])
        answer, extra_specs = conferir_e_remediar(
            telegram_id, question, answer, tem_grafico)
        if extra_specs:
            _stash_charts(telegram_id, extra_specs, ctx.get("user_id"))
    except Exception as exc:
        log.warning("guarda da saída falhou: %s", exc)

    ctx["history"] = (ctx["history"] + [{"q": question, "a": answer}])[-_HISTORY_CAP:]
    persist_conversation(telegram_id)

    if repo.enabled:
        # a RESPOSTA também. Só a pergunta ficava gravada, então o portal
        # mostrava o que o aluno perguntou e nada do que o coach respondeu —
        # metade da conversa, e a metade que diz se o coach prestou.
        repo.log_event(telegram_id, username, "followup_resposta",
                       {"q": question[:300], "r": (answer or "")[:900]})
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
    # AUDITORIA DE ALL-INS: o motor de equilíbrio roda em cada decisão de
    # all-in/fold de stack curto do torneio — determinístico, custo zero de
    # IA. Era o que faltava pra "análise completa de torneio" ter a conta.
    from app.analysis.allin_audit import (auditar_allins, auditar_posflop,
                                          auditar_preflop_deep,
                                          resumo_auditoria)

    auditoria = auditar_allins(hands)
    pre_deep = auditar_preflop_deep(hands)
    posflop = auditar_posflop(hands, max_spots=3)
    resumo = resumo_auditoria(auditoria)
    html = build_report_html(hands, "", board_png, per_hand_analysis=per_hand,
                             auditoria=auditoria, pre_deep=pre_deep,
                             posflop=posflop)
    repo.log_event(telegram_id, username, "relatorio",
                   {"tournament": latest.tournament_id, "hands": len(hands),
                    "allins_auditados": resumo.get("total", 0),
                    "erros": resumo.get("erros", 0),
                    "pre_deep": len(pre_deep), "posflop": len(posflop)})
    cap = ("📋 Relatório mão a mão do seu último torneio — cada mão com "
           "análise e a versão 🎈 mais simples.")
    if resumo:
        cap += (f"\n\n⚖️ *Auditoria de all-ins*: {resumo['total']} decisões "
                f"de stack curto · {resumo['certos']} certas")
        if resumo["erros"]:
            cap += (f" · {resumo['erros']} fora do equilíbrio, custando "
                    f"{resumo['custo_total_bb']:g}bb")
            pior = resumo.get("pior")
            if pior:
                cap += (f"\nA mais cara: {pior['mao']} no {pior['posicao']} "
                        f"({pior['stack_bb']:g}bb) — você {pior['voce_fez']}, "
                        f"o equilíbrio manda {pior['equilibrio']} "
                        f"({pior['custo_bb']:g}bb).")
    fora_pre = sum(1 for l in pre_deep if not l["acertou"])
    if pre_deep:
        cap += (f"\n📐 *Pré-flop deep*: {len(pre_deep)} decisões contra o range "
                f"de referência · {len(pre_deep)-fora_pre} dentro")
    fora_pos = sum(1 for l in posflop if not l["acertou"])
    if posflop:
        cap += (f"\n🎲 *Pós-flop*: {len(posflop)} spots maiores resolvidos no "
                f"CFR+ · {len(posflop)-fora_pos} no equilíbrio")
    cap += "\n\nQuer abrir alguma? Me manda o Nº ou as cartas aqui no chat."
    return (
        html.encode("utf-8"),
        f"KKNuths-MaoAMao-{latest.tournament_id or 'torneio'}.html",
        cap,
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
        from app.agent import llm as _llm
        from app.agent.saude import recado_recente

        # duas causas, respostas OPOSTAS: com a API fora o coach nem rodou
        # ("já está simples" seria mentira); com a API de pé e o texto já
        # simples, "me embananei" é que seria mentira — e repetir o mesmo
        # texto faz o aluno achar que o botão quebrou.
        if _llm.LAST_SIMPLIFY_REASON == "ja_simples":
            return ("Essa resposta já está no nível mais simples que eu "
                    "consigo escrever 😅 Me diz qual pedaço ficou confuso "
                    "que eu destrincho esse — pode ser um termo, uma conta, "
                    "ou a decisão inteira.")
        return recado_recente() or (
            "Opa, me embananei aqui — toca o botão de novo em um instante? 🙏")
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


def maos_do_ultimo_torneio(telegram_id: int) -> list[CanonicalHand]:
    """As mãos do torneio mais recente — o quadro e a leitura de estratégia
    olham exatamente o MESMO conjunto (senão os dois se contradizem)."""
    repo = get_repository()
    if repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        all_hands = repo.get_all_hands(user["id"]) if user else []
        tourneys = [h for h in all_hands if h.tournament_id]
        if tourneys:
            latest = max(tourneys, key=lambda h: h.played_at or "")
            return [h for h in tourneys
                    if h.tournament_id == latest.tournament_id]
    return [h for h in RECENT_HANDS.get(telegram_id, []) if h.tournament_id]


def tournament_board_report(telegram_id: int) -> tuple[bytes, str] | None:
    """Quadro-resumo do torneio mais recente do usuário (None sem material)."""
    hands = maos_do_ultimo_torneio(telegram_id)
    if len(hands) < 2:
        return None
    from app.analysis.tournament_board import render_tournament_board

    return render_tournament_board(hands)


def estrategia_do_torneio(telegram_id: int) -> str:
    """Onde o EV foi embora, por profundidade de stack. '' sem material.

    Acompanha o quadro do /torneio porque a curva do stack mostra O QUE
    aconteceu e não POR QUÊ: o aluno via a linha cair e não sabia em que
    faixa ele estava deixando dinheiro.
    """
    from app.analysis.estrategia_torneio import por_faixa, texto

    hands = maos_do_ultimo_torneio(telegram_id)
    return texto(por_faixa(hands)) if len(hands) >= 2 else ""


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
        hands, fora = repo.get_hands_para_perfil(user["id"]) if user \
            else ([], 0)
        if hands:
            stats = compute_player_stats(hands, player=None,
                                         fora_da_amostra=fora)
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
# pppoker.club = link de compartilhamento novo (share.php?...&shareKey=UUID);
# replay.pppoker.net = link antigo do frame do replayer. Ambos carregam o
# shareKey que é o nome do arquivo JSON no CDN.
# gg.gl é o ENCURTADOR de replay da GGPoker. Sem ele na lista o link não era
# nem reconhecido como replay: caía no leitor de texto e o aluno recebia
# "não entendi", que é a pior resposta possível — sugere que ele errou.
_REPLAY_HOSTS = ("replay.pppoker.net", "pppoker.net", "pppoker.club",
                 "supremapoker.net", "clubgg.com", "wepoker", "pokerbros",
                 "upoker", "gg.gl", "ggpoker.com", "ggpoker.net",
                 "gg.poker")


def replay_link_info(text: str, legenda: bool = False) -> dict | None:
    """Detecta link de replay de clube na mensagem. Retorna
    {'site', 'share_key'} ou None. Só dispara quando a mensagem É o link
    (não quando cita uma url no meio de uma pergunta longa).

    `legenda=True` para caption de foto compartilhada: ali a regra do
    "mensagem é só o link" não vale — o app do clube escreve o texto
    promocional dele em volta do link, e o aluno não controla isso."""
    import re as _re

    t = (text or "").strip()
    m = _re.search(r'https?://[^\s]+', t)
    if m:
        raw = m.group(0)
        url = raw
    else:
        # o público cola o link SEM https:// (copiado do chat do clube):
        # "replay.pppoker.net/...?shareKey=..." tem que funcionar igual
        m = _re.search(r'\b[\w][\w.-]*\.[a-z]{2,6}/[^\s]+', t, _re.IGNORECASE)
        if not m:
            return None
        raw = m.group(0)
        url = "https://" + raw
    host = _re.sub(r'^https?://([^/]+).*', r'\1', url).lower()
    if not any(h in host for h in _REPLAY_HOSTS):
        return None
    if not legenda and len(t) > len(raw) + 40:
        return None
    from app.parsers.pppoker_replay import share_key_from_url

    site = ("pppoker" if "pppoker" in host else
            "suprema" if "suprema" in host else
            "ggpoker" if ("gg.gl" in host or "ggpoker" in host
                          or "gg.poker" in host) else "outro")
    if site == "suprema":
        # a Suprema recebe o LINK inteiro: a chave sai dele dentro do parser
        from app.parsers.suprema_replay import token_do_link

        return {"site": site, "url": url,
                "share_key": url if token_do_link(url) else None}
    return {"site": site, "url": url,
            "share_key": share_key_from_url(url) if site == "pppoker" else None}


# clubes cujo link eu RECONHEÇO mas não sei abrir — dizer o nome é a
# diferença entre "a ferramenta é limitada" e "a ferramenta está quebrada"
_NOME_CLUBE = {"suprema": "Suprema", "clubgg": "ClubGG", "wepoker": "WePoker",
               "pokerbros": "PokerBros", "upoker": "UPoker",
               "ggpoker": "GGPoker"}


def termo_reply(args: list[str]) -> str:
    """/termo — o portão de aprovação do glossário vivo (só o dono).

    O linguista propõe de madrugada; aqui o dono decide com um toque:
      /termo               lista pendentes e aprovados
      /termo ok N          aprova como 'vigiar' (o juiz acusa quando sair)
      /termo ok N corrigir aprova como troca automática na entrega
      /termo nao N         descarta a proposta
    """
    repo = get_repository()
    if not repo.enabled:
        return "Sem banco agora — tenta de novo em instantes."
    t = repo.client.table("glossario")

    if args and args[0].lower() in ("ok", "nao", "não"):
        if len(args) < 2 or not args[1].isdigit():
            return "Uso: /termo ok N [corrigir]  ·  /termo nao N"
        alvo = int(args[1])
        linha = (t.select("*").eq("id", alvo).execute().data or [None])[0]
        if not linha:
            return f"Não achei proposta #{alvo}."
        if args[0].lower() != "ok":
            t.delete().eq("id", alvo).execute()
            return f"🗑 Descartado: «{linha['errado']}»."
        tipo = "corrigir" if (len(args) > 2
                              and args[2].lower() == "corrigir") else "vigiar"
        t.update({"aprovado": True, "tipo": tipo}).eq("id", alvo).execute()
        acao = ("trocado automaticamente na entrega" if tipo == "corrigir"
                else "o juiz acusa quando aparecer")
        return (f"✅ «{linha['errado']}» → «{linha['certo']}» aprovado "
                f"({acao}). Vale em até 10 min.")

    linhas = (t.select("id,errado,certo,tipo,aprovado")
              .order("id", desc=True).limit(30).execute().data) or []
    pend = [x for x in linhas if not x["aprovado"]]
    aprov = [x for x in linhas if x["aprovado"]]
    out = []
    if pend:
        out.append("⏳ *Esperando seu veredito:*")
        out += [f"#{x['id']}  «{x['errado']}» → «{x['certo']}»" for x in pend]
        out.append("\n/termo ok N · /termo ok N corrigir · /termo nao N")
    else:
        out.append("Nenhuma proposta pendente.")
    if aprov:
        out.append(f"\n📗 Aprovados ({len(aprov)}):")
        out += [f"• «{x['errado']}» → «{x['certo']}» ({x['tipo']})"
                for x in aprov[:10]]
    return "\n".join(out)


def licoes_reply(args: list[str]) -> str:
    """/licoes — biblioteca + fila da "lição do dia" (só o dono).

    O destilador estoca; o dono aprova e a lição SAI NA HORA:
      /licoes            lista (fila primeiro)
      /licoes N          mostra a lição inteira
      /licoes N ok       aprova e ENVIA agora (ou enfileira se saiu uma há
                         menos de 6h — trava anti-rajada)
      /licoes N ja       envia agora ignorando a trava
      /licoes N nao      tira da fila (volta pra estante)
    """
    repo = get_repository()
    if not repo.enabled:
        return "Sem banco agora — tenta de novo em instantes."
    t = repo.client.table("licoes")

    if args and args[0].isdigit():
        alvo = int(args[0])
        linha = (t.select("*").eq("id", alvo).execute().data or [None])[0]
        if not linha:
            return f"Não achei a lição #{alvo}."
        acao = args[1].lower() if len(args) > 1 else ""
        if acao == "ok":
            if linha.get("enviada_em"):
                return f"Lição #{alvo} já foi enviada em "\
                       f"{str(linha['enviada_em'])[:10]} — não repete."
            from app.bot.licao_qualidade import com_cartas, problemas_da_licao

            probs = problemas_da_licao(com_cartas(repo, linha))
            if probs:
                # vai pra TODOS de uma vez e leva a assinatura da ferramenta:
                # aqui o portão para, e o dono decide com o defeito na tela
                return ("🛑 Não mandei — essa lição tem ponto que queima "
                        "credibilidade:\n"
                        + "\n".join(f"• {p}" for p in probs)
                        + f"\n\nConserta o texto, ou manda assim mesmo com "
                          f"/licoes {alvo} ja")
            t.update({"aprovada": True}).eq("id", alvo).execute()
            # aprovar DISPARA na hora — o dono aprovava e esperava até o
            # outro dia sem ver nada acontecer. A trava anti-rajada segura
            # a 2ª aprovação seguida pra não virar 3 pushes no aluno.
            from app.bot.licao_envio import (
                JANELA_ANTI_RAJADA_H, enviar_licao,
                horas_desde_o_ultimo_envio, pode_disparar_agora,
            )

            horas = horas_desde_o_ultimo_envio(repo)
            if not pode_disparar_agora(horas):
                fila = (t.select("id", count="exact").eq("aprovada", True)
                        .is_("enviada_em", "null").execute().count or 0)
                return (f"✅ #{alvo} aprovada, mas saiu lição há "
                        f"{horas:.1f}h — pra não metralhar o aluno, esta vai "
                        f"na FILA (sai 11h BRT). Fila: {fila}.\n"
                        f"_Se quiser mandar agora mesmo: /licoes {alvo} ja_")
            token = get_settings().telegram_bot_token
            r = enviar_licao(repo, token, linha)
            return (f"📤 #{alvo} ENVIADA agora para {r['enviados']} aluno(s).\n"
                    f"_{linha['titulo']}_\n\n"
                    + (f"Fila: {r['fila']} aprovada(s) — sai 11h BRT."
                       if r["fila"] else
                       f"Fila vazia (próxima aprovação dispara em "
                       f"{JANELA_ANTI_RAJADA_H:.0f}h)."))
        if acao == "ja":
            # escape hatch: ignora a trava anti-rajada de propósito
            if linha.get("enviada_em"):
                return f"Lição #{alvo} já foi enviada — não repete."
            from app.bot.licao_envio import enviar_licao

            t.update({"aprovada": True}).eq("id", alvo).execute()
            r = enviar_licao(repo, get_settings().telegram_bot_token, linha)
            return (f"📤 #{alvo} enviada agora (forçado) para "
                    f"{r['enviados']} aluno(s).")
        if acao in ("nao", "não"):
            t.update({"aprovada": False}).eq("id", alvo).execute()
            return f"↩️ #{alvo} saiu da fila (segue na estante)."
        from app.bot.licao_qualidade import com_cartas, problemas_da_licao

        probs = problemas_da_licao(com_cartas(repo, linha))
        aviso = ("\n\n⚠️ *Antes de mandar pra todo mundo:*\n"
                 + "\n".join(f"• {p}" for p in probs)) if probs else ""
        return (f"📖 *#{linha['id']} — {linha['titulo']}* "
                f"({linha['categoria']}, {linha['ev_bb']:+.1f}bb)\n\n"
                f"{linha['spot']}\n\n{linha['licao']}"
                f"{aviso}\n\n"
                f"Aprovar e ENVIAR agora: /licoes {linha['id']} ok")

    linhas = (t.select("id,titulo,categoria,ev_bb,aprovada,enviada_em")
              .order("id", desc=True).limit(20).execute().data) or []
    if not linhas:
        return ("Biblioteca vazia por enquanto — o destilador roda todo dia "
                "às 9h15 UTC sobre as análises das últimas 24h.")
    fila = [x for x in linhas if x.get("aprovada") and not x.get("enviada_em")]
    enviadas = [x for x in linhas if x.get("enviada_em")]
    estante = [x for x in linhas if not x.get("aprovada")
               and not x.get("enviada_em")]

    def _linha(x, marca):
        return (f"{marca} #{x['id']} {x['titulo']} "
                f"({x['categoria']}, {x['ev_bb']:+.1f}bb)")

    out = []
    if fila:
        out.append(f"🚀 *Na fila de envio ({len(fila)}):*")
        out += [_linha(x, "•") for x in fila]
    else:
        out.append("🚀 *Fila de envio VAZIA* — nada sai amanhã.")
    if estante:
        out.append(f"\n📚 *Na estante ({len(estante)}, esperando seu ok):*")
        out += [_linha(x, "•") for x in estante[:10]]
    if enviadas:
        out.append(f"\n📤 *Já enviadas:* "
                   + ", ".join(f"#{x['id']}" for x in enviadas[:10]))
    out.append("\n/licoes N pra ler · /licoes N ok pra mandar pra fila")
    return "\n".join(out)


def replay_fallback_text(site: str | None = None,
                         chave_ilegivel: bool = False) -> str:
    """Mensagem para replay que não dá para puxar automático.

    Ela era UMA só para dois casos muito diferentes: "esse clube eu não
    abro" e "é PPPoker, que eu ABRO, mas não consegui ler a chave deste
    link". O aluno não tinha como saber em qual caiu — e no segundo caso a
    mensagem é simplesmente falsa, porque o replay dele eu sei ler.
    """
    saidas = ("📸 *Print do replay* — foto da tela da mão (cartas + board).\n"
              "✍️ *Ou descreve* — _\"77 no CO, 30bb, limpei, flop A♦7♣9♣...\"_"
              " — que eu rodo os números na hora. 🃏")
    if chave_ilegivel:
        return ("🔗 É um link da *PPPoker* — esse eu abro sozinho, mas não "
                "achei o código da mão neste aqui. Costuma ser link cortado "
                "ou encurtado: reabre o replay no app e usa *Compartilhar* "
                "para copiar o link inteiro.\n\nSe preferir não repetir:\n\n"
                + saidas)
    if site == "ggpoker":
        # a GGPoker cifra a mão (medido: 22 kB, entropia 7,99/8, blocos AES).
        # Mas ela tem uma saída OFICIAL e melhor: o histórico do PokerCraft
        # traz a SESSÃO inteira, não uma mão — e é isso que alimenta stats,
        # leaks e evolução. Mandar o aluno para o print seria pior conselho.
        # O alias do link (_8gph8vo-…) é código de COMPARTILHAMENTO, resolvido
        # só no servidor deles — não dá para virar Hand ID por fora. Mas o
        # PokerCraft mostra o Hand ID na própria mão, e a busca por id já
        # existe no `handsearch`. Então o aluno traz o número, e eu acho no
        # arquivo dele: fecha o ciclo sem depender do link.
        # Nada de mandar o aluno caçar código: `find_hand` casa por CARTAS
        # ("QJ", "QJs", "QdJd"), e ele está olhando o replay — as cartas
        # estão na cara dele. O Nº da mão é só uma das formas, e a menos
        # conveniente. Exigi-lo era atrito que eu mesmo inventei.
        return ("🔗 Link de replay da *GGPoker*. Esse eu não abro — o site "
                "não libera a mão pelo link.\n\n"
                "*Faz assim, que fica até melhor:*\n\n"
                "1️⃣ PokerCraft → *Hand History* → período → *Download*\n"
                "2️⃣ me manda o `.txt` aqui\n"
                "3️⃣ pede a mão pelas *cartas*: _\"abre a mão de AK\"_\n\n"
                "Não precisa procurar número nenhum — as cartas que você está "
                "vendo no replay bastam (e o Nº da mão também serve, se "
                "preferir).\n\n"
                "O `.txt` traz a *sessão inteira*: além dessa mão, sai seu "
                "perfil, seus leaks e sua evolução — o que uma mão sozinha "
                "nunca mostra. 🃏\n\n"
                "Se preferir resolver só esta agora:\n\n" + saidas)
    clube = _NOME_CLUBE.get(site or "")
    quem = f"da *{clube}*" if clube else "desse clube"
    return (f"🔗 Esse é um *link de replay* {quem}. Abro sozinho só os da "
            "*PPPoker* e da *Suprema* por enquanto — mas analiso a mão "
            "*agora* de dois jeitos:\n\n" + saidas)


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
    do_banco, fora = repo.get_hands_para_perfil(user["id"]) if user \
        else ([], 0)
    src_hands = do_banco or RECENT_HANDS.get(telegram_id, [])
    if not src_hands:
        return None
    stats = compute_player_stats(src_hands, player=None,
                                 fora_da_amostra=fora if do_banco else 0)
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
        # "Simular ESTA mão": só aquela mão. Se ela não existe ou não tem
        # sequência de ações jogável, NÃO troca por outra — devolve o sentinelas
        # 'wrong_hand' pra o handler avisar (antes trazia uma mão diferente).
        for h in hands:
            if h.hand_id == hand_id and h.hero and h.hero_cards:
                ev = hand_timeline(h)
                if any(e["kind"] == "decision" for e in ev):
                    best, best_events = h, ev
                break
        if best is None:
            return {"unsimulable": True, "hand_id": hand_id}
    else:
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

    # figura da mesa por decisão (situação completa, custo zero de LLM). Chave
    # por índice do evento em string (sobrevive a serialização do user_data).
    from app.analysis.tools import pot_odds as _po

    bbv = best.stakes.big_blind or 1
    seat = best.hero_seat()
    stack_bb = round(seat.stack / bbv, 1) if seat else None
    from app.analysis.tools import fmt_chips as _fc

    blinds = f"{_fc(best.stakes.small_blind)}/{_fc(best.stakes.big_blind)}" + (
        f" (ante {_fc(best.stakes.ante)})" if best.stakes.ante else "")
    pos_stack = {p.position: round(p.stack / bbv, 1)
                 for p in best.players if p.position}
    figures: dict[str, dict] = {}
    dec_i = -1
    for idx, e in enumerate(best_events):
        if e["kind"] != "decision":
            continue
        dec_i += 1
        pot_bb = round(e["pot"] / bbv, 1)
        to_call_bb = round(e["to_call"] / bbv, 1)
        vills = _seats_at_decision(best, dec_i)
        if to_call_bb > 0:
            agg_pos, agg_bet = _decision_aggressor(best, e)
            _mark_aggressor(vills, agg_pos, agg_bet, pos_stack)
        figures[str(idx)] = {
            "title": "Simulação — sua vez",
            "hero_cards": best.hero_cards,
            "board": e["board"],
            "position": a["position"],
            "stack_bb": stack_bb,
            "pot_bb": pot_bb,
            "to_call_bb": to_call_bb,
            "required_eq": round(_po(pot_bb, to_call_bb), 3) if to_call_bb > 0 else None,
            "street": e["street"],
            "blinds": blinds,
            "villains": vills,
        }

    # herói que só teve UMA decisão e nela FOLDOU está fora da mão — não há o
    # que "rejogar" decisão a decisão (o Leo colou um replay onde foldou o pré e
    # a simulação morria num toque só). Marca pra o handler mostrar o FILME.
    hero_decs = [e for e in best_events if e["kind"] == "decision"]
    dead_end = len(hero_decs) == 1 and hero_decs[0].get("actual") == "fold"

    return {
        "hand_id": best.hand_id,
        "cards": best.hero_cards,
        "position": a["position"],
        "bb": bbv,
        "net_bb_real": a["net_bb"],
        "events": best_events,
        "figures": figures,
        "pos": 0,
        "results": [],
        "dead_end": dead_end,
        # gabarito determinístico da mão (board, showdown, mão feita por
        # street) — vai no payload do "e se" e no contexto de conversa para o
        # coach NÃO improvisar leitura (fonte das alucinações já flagradas)
        "gabarito": {
            "board": a["final_board"],
            "showdown_cards": a["showdown_cards"],
            "hero_final_hand": a["hero_final_hand"],
            "showdown_hands": a["showdown_hands"],
            "hand_by_street": a["hand_by_street"],
            "pot_winners": a["pot_winners"],
            "cartas_texto": a.get("cartas_texto"),
            "textura_do_board": a.get("textura_do_board"),
        },
    }


# treino de leitura pendente por usuário (v1 em memória; um treino por vez)
HR_PENDING: dict[int, dict] = {}


def build_hand_reading(telegram_id: int) -> dict | None:
    """Treino de LEITURA DE MÃOS (quiz invertido): uma mão real com showdown
    de vilão; o aluno vê a história SEM as cartas dele e adivinha o que ele
    mostrou entre 4 opções — a real + 3 iscas plausíveis espalhadas por
    força (determinístico por mão). None sem material."""
    import random as _r

    from app.analysis.equity import describe_hand
    from app.analysis.ranges import expand_combos, parse_range
    from app.analysis.river_solver import _strengths

    hands = _user_hands(telegram_id)
    candidatas = []
    for h in hands:
        if not (h.hero and len(h.final_board or []) == 5):
            continue
        alvo = next((w for w, cs in (h.shown_cards or {}).items()
                     if w != h.hero and len(cs) == 2), None)
        if alvo:
            candidatas.append((h, alvo))
    if not candidatas:
        return None
    h, vilao = candidatas[0]
    real = list(h.shown_cards[vilao])

    dead = set(h.final_board) | set(h.hero_cards or []) | set(real)
    pool = expand_combos(parse_range(
        "22+, A2s+, A7o+, K9s+, KTo+, QTs+, JTs, T9s, 98s, 87s, 76s"), dead)
    if len(pool) < 3:
        return None
    ranks = _strengths(pool, h.final_board)
    ordenado = [c for _, c in sorted(zip(ranks.tolist(), pool),
                                     key=lambda x: x[0])]
    # iscas em três alturas: quase-nuts, miolo e fraca — o aluno compara a
    # LINHA jogada com a força plausível
    iscas = []
    for q in (0.04, 0.5, 0.92):
        c = ordenado[min(len(ordenado) - 1, int(len(ordenado) * q))]
        if list(c) not in iscas:
            iscas.append(list(c))
    while len(iscas) < 3:
        iscas.append(list(ordenado[_r.Random(len(iscas)).randrange(len(ordenado))]))

    opts = [real] + iscas[:3]
    _r.Random(h.hand_id).shuffle(opts)
    lines, _ = _walk_hand(h)
    return {
        "hand_id": h.hand_id,
        "vilao": vilao,
        "story": "\n".join(lines)[:1600],
        "options": opts,
        "correct": opts.index(real),
        "leitura": describe_hand(real, h.final_board) or "",
    }


def villain_report(telegram_id: int, name: str) -> str:
    """/vilao <nome> — perfil de exploit de um oponente recorrente, montado
    das mãos do próprio aluno (determinístico, custo zero de LLM)."""
    hands = _user_hands(telegram_id)
    if not hands:
        return "Ainda não tenho mãos suas na base — envie um replay primeiro."
    from app.analysis.villains import villain_profile

    prof = villain_profile(hands, name)
    if not prof:
        nomes = sorted({p.name for h in hands for p in h.players
                        if p.name and not p.is_hero
                        and not p.name.startswith("seat")})[:12]
        return (f"Não achei '{name}' nas suas mãos. Vilões que já vi: "
                + ", ".join(nomes) if nomes else
                f"Não achei '{name}' nas suas mãos.")

    l = [f"🎯 *{prof['vilao']}* — {prof['maos_na_base']} mão(s) na sua base "
         f"(amostra {prof['amostra']})"]
    v, p = prof["vpip"], prof["pfr"]
    l.append(f"VPIP *{v['media']:g}%* ({v['ic95'][0]:g}–{v['ic95'][1]:g}) · "
             f"PFR *{p['media']:g}%* · AF *{prof['af']:g}*")
    fq = prof.get("fold_quando_apostado")
    if fq:
        l.append(f"Folda quando apostado: *{fq['media']:g}%* "
                 f"(amostra {fq['amostra']})")
    if prof.get("showdowns_vistos"):
        sd = ", ".join(f"{_pretty_cards(s['cartas'])}"
                       for s in prof["showdowns_vistos"])
        l.append(f"Showdowns já vistos: {sd}")
    if prof.get("exploits"):
        l.append("\n*Como explorar:*")
        l += [f"• {e}" for e in prof["exploits"]]
    if prof.get("aviso"):
        l.append(f"\n⚠️ _{prof['aviso']}_")
    l.append("\n💬 _Pergunta 'como jogo contra ele?' que o coach monta o plano._")
    return "\n".join(l)


def ensure_demo_material(telegram_id: int) -> bool:
    """Usuário ZERO (sem nenhuma mão): injeta uma mão-DEMO sintética na
    memória — nunca no banco — pra /treino e /simular funcionarem no
    primeiro minuto (item 6 do roadmap-10). True se injetou."""
    if RECENT_HANDS.get(telegram_id):
        return False
    repo = get_repository()
    if repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        if user and repo.get_all_hands(user["id"], limit=1):
            return False
    from app.api.site_assets import _demo_hand

    RECENT_HANDS[telegram_id] = [_demo_hand()]
    return True




# DEMO: a mão que todo mundo recebe antes de mandar a sua. Quem só treinou
# nela ainda não usou o produto de verdade.
_HAND_ID_DEMO = "demo-site"


def texto_convite_primeira_mao() -> str:
    """Convite explícito para mandar a PRIMEIRA mão própria. PURA.

    Nasceu do primeiro usuário externo: entrou às 02h, clicou em treinar,
    respondeu dois drills na mão-demo e saiu em 2min30 — sem nunca mandar
    uma mão dele. O funil parava exatamente aqui, e não porque ele desistiu:
    ninguém tinha CONVIDADO. O drill acabava e pronto.
    """
    return ("\n\n━━━━━━━━━━━━━━\n"
            "🎯 *Esse treino foi numa mão de exemplo.*\n"
            "O KKNuths fica bom mesmo é nas *suas* mãos — aí ele acha os "
            "seus vazamentos, não os de um desconhecido.\n\n"
            "*Manda uma agora:* print da mesa, arquivo de mãos, ou o link "
            "do replay (PPPoker/Suprema). Leva 10 segundos.")


def merece_convite_primeira_mao(telegram_id: int, hand_id: str | None) -> bool:
    """Convidar quem AINDA NÃO mandou mão — e só nesse caso.

    Insistir com quem já usa vira ruído no fim de todo treino, e ruído a
    gente aprende a pular.
    """
    if hand_id and hand_id != _HAND_ID_DEMO:
        return False          # o drill já foi numa mão DELE
    try:
        return not any(h.hand_id != _HAND_ID_DEMO
                       for h in _user_hands(telegram_id))
    except Exception:
        return False          # na dúvida, não incomoda


def _user_hands(telegram_id: int) -> list:
    """Mãos do usuário: memória recente e, se vazio, o histórico do banco."""
    hands = list(RECENT_HANDS.get(telegram_id, []))
    repo = get_repository()
    if not hands and repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        if user:
            hands = repo.get_all_hands(user["id"], limit=200)
    return hands


def film_bands(h) -> list[dict]:
    """Bandas do filme da mão inteira: streets + banda final "Resultado" com
    o showdown (cartas reveladas) e quem levou o pote."""
    bands = hand_storyboard_streets(h)  # upto_di=None -> mão inteira
    if not bands:
        return []
    bb = h.stakes.big_blind or 1

    # banda final: showdown (cartas reveladas) + quem levou o pote. Sem emoji
    # aqui — o render é PIL/DejaVu e emoji vira tofu na imagem.
    def _label(who: str) -> str:
        if who == h.hero:
            return "VOCÊ"
        p = next((x.position for x in h.players if x.name == who), None)
        return f"{who} ({p})" if p else who

    from app.analysis.equity import describe_hand

    # showdown GRÁFICO: cartas do vilão desenhadas na banda (pedido do
    # admin: "mostre as cartas do vilão em forma gráfica")
    reveals = [
        {"who": f"{_label(who)} mostra",
         "cards": cs,
         "desc": describe_hand(cs, h.final_board)}
        for who, cs in (h.shown_cards or {}).items()
    ]
    hero_desc = describe_hand(h.hero_cards, h.final_board)
    result_lines: list[str] = []
    for who, amount in sorted((h.collected or {}).items(),
                              key=lambda kv: -kv[1]):
        # sem "►" aqui: o render já prefixa cada linha com a seta
        line = f"{_label(who)} leva o pote ({round(amount / bb, 1):g}bb)"
        if who == h.hero and hero_desc:
            line += f" — {hero_desc}"
        result_lines.append(line)
    if result_lines or reveals:
        band = {"name": "Resultado",
                "board": list(h.final_board or []),
                "lines": result_lines,
                "reveals": reveals,
                "pot_bb": round((h.total_pot or 0) / bb, 1) or None}
        # pote final menor que o da última street = aposta não paga devolvida
        # (sem a nota, parece erro de conta — leitor compara os dois números)
        prev = bands[-1].get("pot_bb") if bands else None
        if prev and band["pot_bb"] and band["pot_bb"] < prev - 0.05:
            band["note"] = "aposta não paga volta pro dono — por isso o pote final é menor"
        bands.append(band)

    # COMENTÁRIO NA FIGURA: veredito do herói por street, com a conta (números
    # determinísticos de decisions_by_street). Custo zero de IA.
    _attach_hero_notes(h, bands)
    # ALL-IN: nas streets do run-out (sem mais ação), a equity de cada mão
    # conhecida evoluindo — como o replayer da sala (era o buraco que fazia
    # a mão de all-in "confusa de ler": bandas vazias sem contar nada)
    _attach_allin_equity(h, bands)
    return bands


# mapeia o nome da banda (render) -> chave de street (decisions_by_street)
_BAND_STREET = {"pré-flop": "preflop", "pre-flop": "preflop",
                "flop": "flop", "turn": "turn", "river": "river"}


def _attach_allin_equity(h, bands: list[dict]) -> None:
    """Nas streets de RUN-OUT de um all-in (sem mais aposta), anexa a equity
    de cada mão conhecida naquele board — a evolução que o replayer da sala
    mostra. É o que faltava pra mão de all-in não ficar 'confusa de ler':
    em vez de bandas vazias, cada street conta como a corrida estava."""
    from app.analysis.equity import equity_vs_hands
    from app.analysis.equity import pretty_cards as _pc
    from app.models.canonical import ActionType, StreetName

    # mãos conhecidas que foram ao showdown (herói + quem mostrou)
    conhecidas: dict[str, list[str]] = {}
    if h.hero and h.hero_cards:
        conhecidas[h.hero] = list(h.hero_cards)
    for nm, cs in (h.shown_cards or {}).items():
        if cs and len(cs) == 2:
            conhecidas[nm] = list(cs)
    if len(conhecidas) < 2:
        return
    # só vale a evolução se houve all-in (senão alguém ainda podia foldar e a
    # equity "crua" enganaria)
    if not any(a.all_in for st in h.streets for a in st.actions):
        return

    pos = {p.name: p.position for p in h.players}

    def _quem(nm: str) -> str:
        if nm == h.hero:
            return "VOCÊ"
        p = pos.get(nm)
        return f"{nm[:12]} ({p})" if p else nm[:12]

    _map = {StreetName.FLOP: "Flop", StreetName.TURN: "Turn",
            StreetName.RIVER: "River"}
    by_name = {b.get("name"): b for b in bands}
    for sname, label in _map.items():
        st = h.street(sname)
        band = by_name.get(label)
        if not st or not band:
            continue
        # RUN-OUT: a street não teve aposta/aumento/pagamento (só correu carta)
        if any(a.type in (ActionType.BET, ActionType.RAISE, ActionType.CALL)
               for a in st.actions):
            continue
        board = band.get("board") or []
        if len(board) < 3:
            continue
        partes = []
        for nm, cs in conhecidas.items():
            eq = equity_vs_hands(cs, [o for k, o in conhecidas.items()
                                      if k != nm], board)
            if eq is not None:
                partes.append((nm, round(eq * 100)))
        if not partes:
            continue
        # herói primeiro, resto por equity desc
        partes.sort(key=lambda x: (x[0] != h.hero, -x[1]))
        band["equity_line"] = "equity: " + " · ".join(
            f"{_quem(nm)} {pct}%" for nm, pct in partes)


def _attach_hero_notes(h, bands: list[dict]) -> None:
    """Anexa a cada banda de street o veredito do herói COM a conta — o
    replayer comentado na própria figura. Marca ✔/≈/✘ pelo EV (contra a mão
    real do vilão, quando houve showdown) ou • quando é só informativo."""
    try:
        dbs = decisions_by_street(h)
    except Exception:
        return
    if not isinstance(dbs, dict) or dbs.get("error"):
        return
    # fração justa da equity num pote com N jogadores — referência pra marcar
    # um lance AGRESSIVO como bom (estar acima da fração já é vantagem)
    n_show = dbs.get("jogadores_no_showdown") or 2
    fair = 100.0 / n_show
    por_street: dict[str, list[dict]] = {}
    for d in dbs.get("decisoes_por_street") or []:
        por_street.setdefault(d["street"], []).append(d)

    for band in bands:
        key = _BAND_STREET.get((band.get("name") or "").strip().lower())
        ds = por_street.get(key or "")
        if not ds:
            continue
        # decisão representativa: a que botou dinheiro (pagar>0); senão a última
        d = next((x for x in ds if x.get("pagar_bb", 0) > 0), ds[-1])
        tipo = d.get("acao_tipo")
        emin = d.get("equity_minima_pct")
        ereal = d.get("equity_real_pct")
        # A figura mostra o FATO DO REPLAY (à frente/atrás da mão que ele
        # mostrou), NÃO o veredito de bom/ruim — esse é do texto (contra o
        # RANGE). Sem isso a figura dizia ✔ 'jogou bem' num all-in que o texto
        # chamava de ❌ (você era 59% vs a mão dele, mas ~28% vs o range).
        alvo = "vs a mão dele" if n_show <= 2 else "vs o campo"
        preco = f"pedia {emin}% · " if (tipo == "call" and emin is not None) \
            else ""
        if ereal is not None:
            conta = f" — {preco}{ereal}% {alvo}"
            # seta NEUTRA de confronto: acima/abaixo da fração justa do pote
            tag = "▲" if ereal >= fair + 5 else ("▼" if ereal <= fair - 5
                                                 else "≈")
        elif preco:
            conta, tag = f" — pedia {emin}%", "•"
        else:
            conta, tag = "", "•"
        # kind 'info' -> cor neutra (dourado) no render: sem verde/vermelho de
        # veredito, pra não brigar com o selo do texto
        band["hero_note"] = {"tag": tag, "kind": "info",
                             "text": f"VOCÊ {d.get('acao', '')}{conta}"}


def hand_film_png(h) -> bytes | None:
    """Filme da mão INTEIRA (todas as streets, lance a lance) numa imagem só.
    Render determinístico (PIL) — custo zero de LLM. None se não der."""
    from app.analysis.hand_figure import render_hand_strip

    bands = film_bands(h)
    if not bands:
        return None
    bb = h.stakes.big_blind or 1
    seat = h.hero_seat()
    from app.analysis.tools import fmt_chips as _fc

    blinds = f"{_fc(h.stakes.small_blind)}/{_fc(h.stakes.big_blind)}" + (
        f" (ante {_fc(h.stakes.ante)})" if h.stakes.ante else "")
    spot = {
        "title": "Sua mão — o filme",  # sem emoji: PIL/DejaVu renderiza tofu
        "hero_cards": h.hero_cards,
        "position": seat.position if seat else None,
        "stack_bb": round(seat.stack / bb, 1) if seat else None,
        "blinds": blinds,
        "streets": bands,
    }
    try:
        return render_hand_strip(spot)
    except Exception:
        return None


def hand_film(telegram_id: int, hand_id: str | None = None) -> bytes | None:
    """Filme da mão inteira a partir do acervo do usuário (por hand_id, com
    fallback pra mão mais recente). Usado quando não há decisão do herói pra
    rejogar (ex.: foldou o pré-flop) — em vez de um beco sem saída, o aluno vê
    como a mão terminou."""
    hands = _user_hands(telegram_id)
    h = None
    if hand_id:
        h = next((x for x in hands
                  if x.hand_id == hand_id and x.hero and x.hero_cards), None)
    if h is None:
        h = next((x for x in hands if x.hero and x.hero_cards), None)
    if h is None:
        return None
    return hand_film_png(h)


_SPOT_ALIASES = {"open": "open_shove", "open_shove": "open_shove",
                 "shove": "open_shove", "reshove": "reshove",
                 "3bet": "reshove", "squeeze": "squeeze",
                 "call": "call_shove", "call_shove": "call_shove",
                 "pagar": "call_shove", "overcall": "overcall"}
_SPOT_NOME_PT = {"open_shove": "abrir de all-in", "reshove": "re-shove sobre o open",
                 "squeeze": "squeeze all-in", "call_shove": "pagar o all-in",
                 "overcall": "overcall do all-in"}


def spot_reply(texto: str) -> tuple[str, list[tuple]] | None:
    """/spot — resolve um spot de all-in escrito em linguagem de mesa.

    Aceita "reshove btn 12 co", "open mp 10", "squeeze bb 15 mp 1".
    Devolve (texto do veredito, [specs de gráfico]) ou None se não entendeu.
    """
    from app.analysis.allin_engine import available, solve_spot

    if not available():
        return None
    toks = [t for t in (texto or "").lower().replace(",", " ").split() if t]
    if not toks:
        return None
    kind = _SPOT_ALIASES.get(toks[0])
    if not kind:
        return None
    posicoes, stack, pagaram = [], None, 0
    for t in toks[1:]:
        limpo = t.replace("bb", "")
        if limpo.replace(".", "", 1).isdigit():
            v = float(limpo)
            if stack is None and v > 3:
                stack = v
            else:
                pagaram = int(v)
        else:
            posicoes.append(t.upper())
    if stack is None:
        return None
    hero = posicoes[0] if posicoes else "MP"
    vil = posicoes[1] if len(posicoes) > 1 else None
    if kind in ("reshove", "squeeze", "call_shove", "overcall") and not vil:
        vil = {"reshove": "CO", "squeeze": "MP",
               "call_shove": "MP", "overcall": "CO"}[kind]
    if kind in ("squeeze", "overcall") and not pagaram:
        pagaram = 1

    sol = solve_spot(kind, hero, round(float(stack), 1), 0.125, 1.0,
                     vil, 2.2, pagaram)
    if not sol:
        return None
    vs = f" contra o {sol['vilao_pos']}" if sol.get("vilao_pos") else ""
    # tudo aqui é vs FOLDAR, igual ao gráfico logo abaixo. Com o EV absoluto
    # a legenda dizia "verde = melhor que foldar" ao lado de outro número, e
    # a "fronteira" saía errada: indiferença é ev == ev do fold (que é
    # NEGATIVO, ~-0.6bb), não ev perto de zero. KTs aparecia como "quase
    # indiferente" valendo +0.95bb a mais que foldar — um call óbvio.
    top = sorted(sol["ev_vs_fold"].items(), key=lambda kv: -kv[1])
    fronteira = [h for h, v in top if abs(v) <= 0.2][:6]
    linhas = [
        f"⚖️ *{_SPOT_NOME_PT[kind].capitalize()}* — {hero}{vs} · "
        f"{stack:g}bb",
        f"\nEquilíbrio: joga *{sol['acao_pct']:g}%* das mãos · "
        f"pote morto {sol['dead']:g}bb",
        f"\n*Melhores* (bb a mais que foldar): "
        + ", ".join(f"{h} ({v:+.1f})" for h, v in top[:5]),
    ]
    if fronteira:
        linhas.append("*Na fronteira* (tanto faz agir ou foldar): "
                      + ", ".join(fronteira))
    linhas.append("\n_Os dois gráficos abaixo: o range do equilíbrio e o EV "
                  "de cada mão em bb (verde = melhor que foldar)._")
    specs = [("spot", kind, hero, float(stack), "freq", vil, 2.2, pagaram),
             ("spot", kind, hero, float(stack), "ev", vil, 2.2, pagaram)]
    return "\n".join(linhas), specs


def texto_do_plano(plan: str | None, restantes: int, teto: int | None) -> str:
    """Mensagem do /plano. Função PURA — testável sem banco nem Telegram.

    Passou a ler o plano DE VERDADE porque o teto deixou de ser um só: um
    testador com 100 análises lendo 'você tem 50' é o produto mentindo pra
    ele, e ele não tem como saber qual dos dois números vale.
    """
    base = ("Inclui: análise de mãos e torneios com IA, perfil de estilo, "
            "base de conhecimento (/ask) e drills (/treino).")
    if teto is None:
        return (f"♾️ *Plano {(plan or 'pro').upper()}*\n\n"
                f"Análises *ilimitadas*.\n{base}")
    cabecalho = ("🧪 *Piloto — convidado*" if (plan or "") == "piloto"
                 else "🎁 *Beta gratuito*")
    return (f"{cabecalho}\n\n"
            f"Você tem *{teto}* análises por mês, renovadas todo mês — "
            f"restam *{restantes}* neste mês.\n{base}\n\n"
            "Planos pagos chegam depois do piloto.")


def plano_reply(telegram_id: int, username: str | None = None) -> str:
    repo = get_repository()
    user = repo.get_or_create_user(telegram_id, username) if repo.enabled else None
    quota = check_quota(telegram_id, user, repo)
    teto = limite_do_plano(quota.plan)
    if telegram_id == ADMIN_TELEGRAM_ID:
        teto = None
    return texto_do_plano(quota.plan, quota.remaining, teto)


def _usos_do_mes_por_user(repo) -> dict[str, int]:
    """{user_id: análises no mês}. Vazio se o banco engasgar."""
    from datetime import datetime, timezone

    try:
        inicio = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        linhas = (repo.client.table("usage_events").select("user_id")
                  .gte("created_at", inicio).execute().data) or []
    except Exception:
        return {}
    out: dict[str, int] = {}
    for l in linhas:
        uid = l.get("user_id")
        if uid:
            out[uid] = out.get(uid, 0) + 1
    return out


def listar_planos_reply() -> str:
    """Quem é quem, com plano e consumo — é aqui que se acha o telegram_id."""
    from app.quota import limite_do_plano

    repo = get_repository()
    if not repo.enabled:
        return "Banco desligado — não dá para listar."
    try:
        users = (repo.client.table("users")
                 .select("id,telegram_id,username,plan").execute().data) or []
    except Exception as exc:
        return f"Não consegui ler os usuários: {type(exc).__name__}: {exc}"
    usos = _usos_do_mes_por_user(repo)
    users.sort(key=lambda u: -usos.get(u.get("id"), 0))
    linhas = ["👥 *Usuários e planos* (uso do mês)", ""]
    for u in users:
        if u.get("telegram_id") in (0, None):
            continue          # linhas de sistema (deploy, crons)
        teto = limite_do_plano(u.get("plan"))
        n = usos.get(u.get("id"), 0)
        quanto = f"{n}/{teto}" if teto is not None else f"{n}/∞"
        linhas.append(f"• `{u['telegram_id']}` {u.get('username') or '—'} — "
                      f"*{u.get('plan') or 'free'}* · {quanto}")
    linhas.append("\nPara mudar: `/planode <telegram_id> <plano>`")
    linhas.append("Planos: " + ", ".join(f"`{p}`" for p in PLANOS_MANUAIS))
    return "\n".join(linhas)


def mudar_plano_reply(alvo: str, plano: str) -> tuple[str, int | None]:
    """Muda o plano de um aluno. Devolve (resposta ao admin, telegram_id).

    O telegram_id volta para que o CHAMADOR avise o aluno — quem teve o
    limite mexido merece saber, senão a promoção é invisível para quem
    ela beneficia.
    """
    from app.quota import limite_do_plano

    plano = (plano or "").strip().lower()
    if plano not in PLANOS_MANUAIS:
        return ("Plano desconhecido. Use: "
                + ", ".join(f"`{p}`" for p in PLANOS_MANUAIS), None)
    repo = get_repository()
    if not repo.enabled:
        return ("Banco desligado — não dá para mudar plano.", None)

    chave = alvo.strip().lstrip("@")
    try:
        q = repo.client.table("users").select("id,telegram_id,username,plan")
        if chave.isdigit():
            linhas = q.eq("telegram_id", int(chave)).execute().data or []
        else:
            linhas = q.ilike("username", chave).execute().data or []
    except Exception as exc:
        return (f"Falha ao procurar `{alvo}`: {type(exc).__name__}", None)
    if not linhas:
        return (f"Não achei `{alvo}`. Rode `/planode` sem argumento para ver "
                "a lista com os telegram_id.", None)
    if len(linhas) > 1:
        return (f"`{alvo}` casou com {len(linhas)} usuários — use o "
                "telegram_id para não mudar o plano da pessoa errada.", None)

    u = linhas[0]
    antes = u.get("plan") or "free"
    repo.update_user_plan(u["id"], plano)
    # confere no banco em vez de confiar: update_user_plan engole exceção
    try:
        agora = (repo.client.table("users").select("plan")
                 .eq("id", u["id"]).execute().data or [{}])[0].get("plan")
    except Exception:
        agora = None
    if agora != plano:
        return (f"⚠️ Pedi a troca de *{u.get('username') or u['telegram_id']}* "
                f"para `{plano}`, mas o banco ainda diz `{agora or '?'}`. "
                "Nada mudou — tente de novo.", None)
    teto = limite_do_plano(plano)
    return (f"✅ *{u.get('username') or u['telegram_id']}* "
            f"(`{u['telegram_id']}`): `{antes}` → `{plano}` — "
            + ("análises ilimitadas" if teto is None
               else f"{teto} análises/mês") + ".",
            u.get("telegram_id"))


def prova_real_reply(telegram_id: int) -> str:
    """/prova — a ferramenta se auditando nas mãos DO ALUNO.

    Nasceu de "não estou confiando que a ferramenta esteja confiável". Em vez
    de pedir confiança, entrega verificação que ele controla e vê — com a
    ressalva de honestidade junto (uma prova limpa não prova tudo)."""
    from app.analysis.selfcheck import prova_real, texto_prova

    hands = _user_hands(telegram_id)
    return texto_prova(prova_real(hands))


def sim_advance(sim: dict) -> dict:
    """Avança a simulação: narra ações dos vilões até a próxima decisão do herói.

    Retorna {"narration": str, "decision": evento|None, "done": bool}.
    """
    lines: list[str] = []
    last_street = None
    while sim["pos"] < len(sim["events"]):
        e = sim["events"][sim["pos"]]
        if e["street"] != last_street:
            board = _pretty_cards(e["board"]) if e["board"] else "—"
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
        # gabarito calculado (board/showdown/mão feita por street): o veredito
        # do "e se" fica ancorado — sem recontar mão de cabeça
        **(sim.get("gabarito") or {}),
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
        f"🏁 *Fim da simulação!*  ({_pretty_cards(sim['cards'])} em {sim['position'] or '?'})\n"
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






def decisions_by_street(h: CanonicalHand, actor: str | None = None) -> dict:
    """Decisões de UM jogador (herói por padrão) street a street, com o
    contexto ANCORADO de cada uma: pote antes, preço a pagar, equity mínima,
    ação real e a mão feita naquele ponto (se as cartas dele são conhecidas).

    É a matéria-prima da análise street a street do filme — o coach comenta
    cada jogada a partir DAQUI, sem recontar a mão de cabeça."""
    from app.analysis.equity import equity_vs_hands
    from app.analysis.equity import pretty_cards as _pc  # '10♥', ícones
    from app.analysis.tools import ev_call, pot_odds
    from app.models.canonical import ActionType, StreetName

    who = actor or h.hero
    if not who:
        return {"error": "sem herói definido nesta mão"}
    match = next((p.name for p in h.players
                  if p.name.lower() == who.lower()), None) \
        or next((p.name for p in h.players
                 if who.lower() in p.name.lower()), None)
    if not match:
        nomes = ", ".join(p.name for p in h.players)
        return {"error": f"'{who}' não está na mesa; jogadores: {nomes}"}

    # cartas conhecidas do jogador: herói -> hero_cards; senão -> showdown
    cards = (list(h.hero_cards) if match == h.hero and h.hero_cards
             else list((h.shown_cards or {}).get(match) or []))
    pos = next((p.position for p in h.players if p.name == match), None)
    bb = h.stakes.big_blind or 1

    # CAMPO de referência pra equity EXATA (all-in do replayer): TODOS os
    # oponentes com cartas conhecidas (showdown, + o herói quando analisamos
    # um vilão). Funciona multiway — equity vs o campo inteiro.
    conhecidos: dict[str, list[str]] = {}
    if match != h.hero and h.hero_cards:
        conhecidos[h.hero] = list(h.hero_cards)
    for nm, cs in (h.shown_cards or {}).items():
        if nm != match and cs and len(cs) == 2:
            conhecidos[nm] = list(cs)
    campo = list(conhecidos.values())
    verbs = {"fold": "foldou", "check": "deu check", "call": "pagou",
             "bet": "apostou", "raise": "aumentou p/"}
    order = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN,
             StreetName.RIVER]
    full_board: list[str] = []
    out: list[dict] = []
    pot = 0.0
    for sname in order:
        st = h.street(sname)
        if not st:
            continue
        sb = list(st.board)
        if len(sb) >= len(full_board):
            full_board = sb
        else:
            full_board = full_board + [c for c in sb if c not in full_board]
        contrib: dict[str, float] = {}
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - contrib.get(a.actor, 0.0)
            outstanding = max(contrib.values(), default=0.0)
            if a.actor == match and a.type != ActionType.POST:
                to_call = max(0.0, outstanding - contrib.get(match, 0.0))
                to_call_bb = round(to_call / bb, 1)
                pot_bb = round(pot / bb, 1)
                d = {
                    "street": sname.value,
                    "board": _pc(full_board) if full_board else "—",
                    "acao_tipo": a.type.value,   # call/bet/raise/check/fold
                    "pote_antes_bb": pot_bb,
                    "pagar_bb": to_call_bb,
                    "acao": f"{verbs.get(a.type.value, a.type.value)}"
                            + (f" {round((a.to_amount or a.amount)/bb,1):g}bb"
                               if a.type.value in ("bet", "raise", "call")
                               and (a.to_amount or a.amount) else "")
                            + (" (all-in)" if a.all_in else ""),
                }
                # 'pedia X%' (pot odds) só faz sentido num CALL — não num
                # raise/aposta (aluno reclamou de 'pedia' aparecendo num raise)
                if to_call_bb > 0 and a.type == ActionType.CALL:
                    d["equity_minima_pct"] = round(
                        pot_odds(pot_bb, to_call_bb) * 100)
                if cards and len(full_board) >= 3:
                    fh = _describe_safe(cards, full_board)
                    if fh:
                        d["mao_feita"] = fh
                # A CONTA de cada decisão (determinística, custo zero de IA):
                # equity REAL vs o CAMPO que apareceu no showdown (all-in do
                # replayer, multiway inclusive), e o EV quando é call.
                if cards and campo:
                    eq = equity_vs_hands(cards, campo, full_board)
                    if eq is not None:
                        d["equity_real_pct"] = round(eq * 100)
                        if to_call_bb > 0 and a.type == ActionType.CALL:
                            d["ev_call_bb"] = round(
                                ev_call(eq, pot_bb, to_call_bb), 1)
                out.append(d)
            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET,
                          ActionType.RAISE):
                pot += add
                if a.type != ActionType.POST or a.post_type in ("sb", "bb"):
                    contrib[a.actor] = contrib.get(a.actor, 0.0) + add

    result = {
        "jogador": "VOCÊ" if match == h.hero else match,
        "posicao": pos,
        "cartas": _pc(cards) if cards else None,
        "cartas_conhecidas": bool(cards),
        "decisoes_por_street": out,
        "showdown": {n: _pc(cs)
                     for n, cs in (h.shown_cards or {}).items()} or None,
        "resultado_bb": round((h.collected or {}).get(match, 0) / bb, 1)
        if (h.collected or {}).get(match) else None,
    }
    if conhecidos:
        # equity_real_pct é EXATA contra o CAMPO conhecido (all-in do replay).
        # Multiway: é a equity vs TODAS as mãos que apareceram, junto.
        result["equity_real_vs"] = [
            "VOCÊ" if nm == h.hero else nm for nm in conhecidos]
        result["equity_real_cartas"] = {
            ("VOCÊ" if nm == h.hero else nm): _pc(cs)
            for nm, cs in conhecidos.items()}
        result["jogadores_no_showdown"] = len(conhecidos) + 1
    return result




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
    # pós-flop identifica o vilão por NOME (posição) — "TabaVet (BB) aposta";
    # o pré segue compacto por posição (jeito que jogador narra a mão)
    posmap = {p.name: p.position for p in h.players}

    def _who(nm: str) -> str:
        if nm == h.hero:
            return "VOCÊ"
        short = (nm or "?").strip()[:14]
        p = posmap.get(nm)
        return f"{short} ({p})" if p else short

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
        # board da street: uns parsers dão o board COMPLETO por street (flop=3,
        # turn=4, river=5), outros só o incremento (1 carta). Detecta e evita
        # duplicar (senão o turn saía com 7 cartas: flop repetido + turn).
        sb = list(st.board)
        if len(sb) >= len(full_board):
            full_board = sb                       # já é o board completo da street
        else:
            full_board = full_board + [c for c in sb if c not in full_board]
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
                who = _who(a.actor)
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


def drill_category(drill: dict) -> str:
    """Categoria de LEAK de um spot de treino — o eixo da repetição espaçada.

    push_fold (pré-flop curto em torneio) é separado do pré-flop deep porque
    o erro é de natureza diferente (Nash vs range de abertura)."""
    st = (drill.get("street") or "preflop").lower()
    if st != "preflop":
        return st
    stk = drill.get("stack_bb")
    if stk and stk <= 20 and drill.get("format") in ("tournament", "sng"):
        return "push_fold"
    return "preflop"


def leak_error_rates(verdicts: list[dict]) -> dict[str, dict]:
    """Taxa de erro por categoria a partir dos eventos drill_verdict
    (ruim=1, mista=0.5, boa=0), com suavização de Laplace — um erro isolado
    não vira leak. Eventos antigos sem 'cat' são ignorados."""
    peso = {"boa": 0.0, "mista": 0.5, "ruim": 1.0}
    agg: dict[str, list[float]] = {}
    for v in verdicts or []:
        cat, verd = v.get("cat"), v.get("verdict")
        if cat and verd in peso:
            agg.setdefault(cat, []).append(peso[verd])
    out: dict[str, dict] = {}
    for cat, errs in agg.items():
        n = len(errs)
        out[cat] = {"n": n, "erros": round(sum(errs), 1),
                    "taxa": round((sum(errs) + 1.0) / (n + 2.0), 3)}
    return out


def leak_boost(rates: dict[str, dict], cat: str) -> float:
    """Multiplicador de peso no sorteio do drill: categorias em que o aluno
    ERRA aparecem mais (até ~4x); sem histórico ou indo bem, fica em 1.
    Conforme a taxa de acerto sobe, o boost cai sozinho — é a repetição
    espaçada guiada por erro."""
    r = rates.get(cat) or {}
    if not r or r.get("n", 0) < 1:
        return 1.0
    return 1.0 + max(0.0, r["taxa"] - 0.4) * 6.0


_CAT_NOMES = {"push_fold": "pré-flop de stack curto (push/fold)",
              "preflop": "pré-flop", "flop": "flop", "turn": "turn",
              "river": "river"}


def _leak_note(rates: dict[str, dict], cat: str) -> str | None:
    """Aviso de treino dirigido: só quando há amostra (3+) e erro sustentado —
    o aluno precisa SENTIR que a ferramenta está perseguindo o leak dele."""
    r = rates.get(cat) or {}
    if r.get("n", 0) >= 3 and r.get("taxa", 0.0) >= 0.55:
        return (f"🎯 _Spot na mira: você errou {r['erros']:g} dos últimos "
                f"{r['n']} treinos de {_CAT_NOMES.get(cat, cat)} — esse tipo "
                f"vai voltar até virar rotina._")
    return None


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
            cat = drill_category({"street": d["street"], "stack_bb": stack_bb,
                                  "format": h.format.value})
            scored.append((score, h, di, d["street"], h.hand_id, cat))

    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=True)

    # VARIEDADE (senão cai sempre nas mesmas 5 mãos parecidas):
    # 1) tira as mãos já mostradas recentemente a este usuário
    recent = set(RECENT_DRILLS.get(telegram_id, []))
    fresh = [t for t in scored if t[4] not in recent] or scored
    # 2) sorteia de um pool AMPLO (top 22), + garante os melhores spots pós-flop
    #    no pool mesmo quando o topo é todo shove pré-flop (senão nunca aparecem)
    pool = fresh[:22]
    for t in [x for x in fresh if x[3] != "preflop"][:6]:
        if t not in pool:
            pool.append(t)
    # 3) peso = qualidade do spot ÷ o quanto aquela street já apareceu — puxa
    #    pra cima flop/turn/river quando os últimos foram todos pré-flop
    from collections import Counter

    st_counts = Counter(_RECENT_DRILL_STREETS.get(telegram_id, []))
    # REPETIÇÃO ESPAÇADA: categorias em que o aluno vem ERRANDO (vereditos
    # dos últimos quizzes) pesam mais no sorteio — o treino persegue o leak
    # até a taxa de acerto subir, quando o boost decai sozinho
    try:
        err_rates = leak_error_rates(repo.drill_verdicts(telegram_id)) \
            if repo.enabled else {}
    except Exception:
        err_rates = {}
    weights = [max(t[0], 0.1) * leak_boost(err_rates, t[5])
               / (1 + 1.5 * st_counts.get(t[3], 0)) for t in pool]
    _, h, di, chosen_street, chosen_hid, chosen_cat = \
        random.choices(pool, weights=weights, k=1)[0]

    # atualiza as memórias anti-repetição (mãos e streets). `lembrar` também
    # marca o usuário como recente: quem treina toda noite não é despejado
    # por causa de quem mandou um arquivo e sumiu.
    mem = list(RECENT_DRILLS.get(telegram_id) or []) + [chosen_hid]
    lembrar(RECENT_DRILLS, telegram_id, mem[-_DRILL_MEMORY:])
    stm = list(_RECENT_DRILL_STREETS.get(telegram_id) or []) + [chosen_street]
    lembrar(_RECENT_DRILL_STREETS, telegram_id, stm[-_STREET_MEMORY:])

    lines, decisions = _walk_hand(h)
    d = decisions[di]
    seat = h.hero_seat()
    bb = h.stakes.big_blind
    stack_bb = round(seat.stack / bb, 1) if seat else None

    # esta é a mão que o aluno está vendo agora: /simular e "Simular esta mão"
    # devem cair NELA, não numa mão qualquer com mais decisões
    lembrar(LAST_HAND_META, telegram_id, {
        "hand_id": h.hand_id,
        "position": seat.position if seat else None,
        "stack_bb": stack_bb,
    })

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

    # a mesa COMPLETA no momento da decisão: todos os jogadores, foldados
    # esmaecidos — a figura não pode "mentir" o spot (multiway ≠ heads-up)
    villains = _seats_at_decision(h, di)

    # o "vilão da vez": quem apostou/aumentou por último antes da decisão do
    # herói — a figura mostra as fichas dele na frente (situação completa).
    if d["to_call_bb"] > 0:
        agg_pos, agg_bet = _decision_aggressor(h, d)
        pos_stack = {p.position: round(p.stack / bb, 1)
                     for p in h.players if p.position}
        _mark_aggressor(villains, agg_pos, agg_bet, pos_stack)

    # storyboard da revelação: a mão INTEIRA, todas as streets até o fim — é o
    # "filme completo". Só aparece DEPOIS que o aluno responde, então mostrar
    # tudo é o certo. Custo zero de LLM.
    try:
        storyboard = hand_storyboard_streets(h)
    except Exception:
        storyboard = []

    required = pot_odds(d["pot_bb"], d["to_call_bb"]) if d["to_call_bb"] > 0 else None
    return {
        "cat": chosen_cat,
        # transparência do treino dirigido: quando o spot foi escolhido de
        # propósito por ser o tipo que o aluno mais erra, o quiz avisa
        "leak_note": _leak_note(err_rates, chosen_cat),
        "hand_id": h.hand_id,
        "cards": h.hero_cards,
        "cards_pretty": _pretty_cards(h.hero_cards),
        "position": (seat.position if seat else None),
        "stack_bb": stack_bb,
        "blinds": f"{_fmt_chips(h.stakes.small_blind)}/{_fmt_chips(h.stakes.big_blind)}"
                  + (f" (ante {_fmt_chips(h.stakes.ante)})" if h.stakes.ante else ""),
        "players": len(h.players),
        "format": h.format.value,
        "street": d["street"],
        "board": d["board"],
        "board_pretty": _pretty_cards(d["board"]),
        # gabarito da mão feita NO MOMENTO da decisão — a conversa pós-quiz
        # usa isto em vez do coach reler o board de cabeça
        "mao_feita": _describe_safe(h.hero_cards, d["board"]),
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
    mira = f"\n\n{drill['leak_note']}" if drill.get("leak_note") else ""
    return head + body + ask + mira














def drill_buttons(drill: dict) -> list[list[dict]]:
    """Menu principal do quiz (Fold/Call + Raise ▸ ou Check + Bet ▸)."""
    return action_menu_rows(drill.get("pot_bb"), drill.get("to_call_bb"),
                            drill.get("stack_bb"), "drill")


def drill_size_buttons(drill: dict) -> list[list[dict]]:
    """Submenu de tamanhos do quiz (abre no toque em Raise/Bet)."""
    return size_menu_rows(drill.get("pot_bb"), drill.get("to_call_bb"),
                          drill.get("stack_bb"), "drill")




def reveal_drill(drill: dict, choice: str) -> str:
    """Gabarito profissional: sua escolha vs a real, a matemática do spot
    (equity vs preço), a referência Nash quando aplicável e o convite para
    discutir com o coach."""
    from app.analysis.equity import equity_vs_random

    _, verb = drill_action(choice)   # rótulo legível (com o tamanho escolhido)
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
                + ("\n_Mesmo o call sendo +EV, o JAM domina: nega fold equity "
                   "e evita pós-flop curto._"
                   if pf.get("decision") == "push" and drill.get("to_call_bb")
                   else "")
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

    # equity com a MELHOR premissa disponível, sempre ROTULADA na imagem:
    # - decisão PRÉ-FLOP com agressor identificado -> vs o range de abertura
    #   da posição dele (range real, não mão aleatória)
    # - senão -> vs o nº real de oponentes ativos, mãos aleatórias
    n_opp = max(1, len([v for v in (drill.get("villains") or [])
                        if not v.get("folded")]))
    eq = None
    eq_label = None
    if (drill.get("street") == "preflop" and drill.get("to_call_bb")):
        agg = next((v for v in (drill.get("villains") or [])
                    if v.get("bet_bb")), None)
        agg_pos = (agg or {}).get("pos", "")
        base_pos = agg_pos.split("+")[0] if agg_pos else ""
        try:
            from app.analysis.ranges import OPEN_RANGES, equity_vs_range
            key = agg_pos if agg_pos in OPEN_RANGES else (
                base_pos if base_pos in OPEN_RANGES else None)
            if key:
                r = equity_vs_range(drill["cards"], OPEN_RANGES[key],
                                    drill.get("board") or [],
                                    iterations=4000, seed=11)
                eq = float(r["equity"]) if isinstance(r, dict) else float(r)
                eq_label = f"vs range de abertura do {agg_pos}"
        except Exception:
            eq = None
    if eq is None:
        try:
            eq = equity_vs_random(drill["cards"], drill.get("board") or [],
                                  n_opp, iterations=3000, seed=11)
            eq_label = (f"vs {n_opp} mão{'s' if n_opp > 1 else ''} aleatória"
                        f"{'s' if n_opp > 1 else ''}")
        except Exception:
            pass
    need = drill.get("required_eq")
    to_call = drill.get("to_call_bb") or 0
    math_d: dict = {}
    if eq is not None:
        math_d = {"equity": eq, "need": need}
        if need and to_call:
            # pot_bb JÁ inclui a aposta do vilão (mesma base do required_eq).
            # Somar to_call de novo inflava o EV (+28bb onde era +20bb).
            math_d["ev_bb"] = ev_call(eq, drill.get("pot_bb") or 0, to_call)
            math_d["note"] = (
                f"call precisa de {need*100:.0f}%; você tem ~{eq*100:.0f}% "
                f"({eq_label})")

    # veredito CLARO: reconcilia o que VOCÊ respondeu, o que é CERTO e o que
    # rolou na mão REAL (senão o filme mostra 'fold' e o rodapé diz 'call' —
    # confuso). Sem jargão, sem "pergunte ao coach" (o coach é ele).
    verdict, verdict_text, correct = "mista", "", ""
    actual = (drill.get("actual") or "").lower()
    ch, ch_lbl = drill_action((choice or "").lower())
    ch_lbl = ch_lbl.split()[0] if ch_lbl else (ch or "").upper()
    real_lbl = {"fold": "foldou", "call": "pagou", "check": "deu check",
                "bet": "apostou", "raise": "aumentou"}.get(actual, actual)
    # EQUITY VS ALEATÓRIA NÃO DECIDE PÓS-FLOP CONTRA AGRESSÃO. Caso real da
    # auditoria: A♥T♥ no turn 9♥7♠3♦Q♣ contra check-raise no flop + jam de
    # 24bb. Vs mão aleatória dá 43.6% e o pote pedia 28% -> o bot carimbava
    # "o certo era PAGAR" e marcava o fold CORRETO do aluno como "ruim".
    # Contra o range que dá check-raise e depois jam, a equity real é ~4%.
    # Pior: o veredito alimenta leak_error_rates, então o sorteio passava a
    # perseguir o aluno justamente na categoria em que ele acertou.
    vs_aleatoria = "aleatóri" in (eq_label or "")
    pos_flop = (drill.get("street") or "preflop") != "preflop"
    conta_fraca = vs_aleatoria and pos_flop and to_call
    if conta_fraca:
        eqp, needp = (eq or 0) * 100, (need or 0) * 100
        # o TEXTO já explicava que a conta não decide; a IMAGEM continuava
        # com o número em verde grande e a ressalva em cinza 2× menor. Marcar
        # aqui é o que faz o desenho contar a mesma história.
        math_d["fraca"] = True
        math_d["note"] = (
            f"⚠️ {eqp:.0f}% é contra mão QUALQUER — ele apostou, e quem "
            f"aposta não aposta com mão qualquer. Contra o range dele a "
            f"equity cai muito; o preço de {needp:.0f}% não decide sozinho.")
        verdict, correct = "mista", "Depende do range dele"
        verdict_text = (
            f"Contra uma mão qualquer você teria ~{eqp:.0f}% e o pote pede "
            f"{needp:.0f}% — mas ele APOSTOU, e quem aposta não aposta com "
            "mão qualquer. Contra o range que joga assim a sua equity cai "
            "muito. Aqui o preço não decide sozinho: decide a leitura.")
        return {**(drill or {}), "choice": choice, "math": math_d,
                "verdict": verdict, "verdict_text": verdict_text,
                "correct": correct}
    if eq is not None and need and to_call:
        eqp, needp = eq * 100, need * 100
        ev = math_d.get("ev_bb", 0)
        margin = eq - need
        if margin >= 0.03:
            rec = "call"
            correct = "PAGAR (call)"
            math_line = (f"Você tinha ~{eqp:.0f}% de equity e o pote pedia só "
                         f"{needp:.0f}% — pagar rende {ev:+.0f}bb.")
        elif margin <= -0.03:
            rec = "fold"
            correct = "FOLDAR"
            math_line = (f"Você tinha ~{eqp:.0f}% de equity mas o pote pedia "
                         f"{needp:.0f}% — pagar perde {ev:+.0f}bb.")
        else:
            rec = "mista"
            correct = "Depende da leitura"
            math_line = (f"Sua equity (~{eqp:.0f}%) bate quase exato os "
                         f"{needp:.0f}% que o pote pede — spot no fio.")
        # stack curto no pré: call vs fold NÃO basta — o jam pode dominar o
        # call (caso real: imagem dizia "PAGAR" com TT/15bb, o certo é ALL-IN;
        # o coach dizia jam e a imagem contradizia). Consulta o equilíbrio.
        jam = None
        stk = drill.get("stack_bb")
        if (drill.get("street") == "preflop" and stk and stk <= 20
                and drill.get("cards")
                and drill.get("format") in ("tournament", "sng")):
            try:
                from app.analysis.pushfold import push_fold

                pf = push_fold(drill["cards"], stk,
                               drill.get("position") or "MP")
                if pf.get("applicable") and pf.get("decision") == "push":
                    jam = pf
            except Exception:
                jam = None

        if jam and rec in ("call", "mista"):
            rec = "raise"
            correct = "ALL-IN (jam)"
            aligned = ch == "raise"
            verdict = "boa" if aligned else ("mista" if ch == "call" else "ruim")
            verdict_text = (
                f"Você respondeu {ch_lbl} — "
                + ("certo: com esse stack a jogada é mandar tudo. " if aligned
                   else f"com {stk:g}bb o certo é ALL-IN. ")
                + math_line
                + f" E o jam rende MAIS que o call: nega a fold equity e "
                  f"evita pós-flop curto (sua mão está no top "
                  f"{jam['hand_top_pct']}%; o shove de equilíbrio é "
                  f"≈{jam['shove_range_pct']}%).")
        elif rec == "mista":
            verdict = "mista"
            verdict_text = (f"Você respondeu {ch_lbl}. {math_line} Aqui não é "
                            "conta, é leitura: contra quem blefa, paga; contra "
                            "um pedra, descarta."
                            + (" Seu aumento vira semi-blefe de leitura — "
                               "válido, sem gabarito de conta."
                               if ch == "raise" else ""))
        elif ch == "raise" and rec == "fold":
            # ESPELHO do caso "raise sobre call +EV": aumentar onde pagar é
            # -EV é BLEFE — e a conta (call vs fold) não julga blefe. Antes
            # carimbava "RUIM — o certo era FOLDAR" por cima de um possível
            # blefe legítimo. Vira misto, com o alpha do sizing citado.
            verdict = "mista"
            correct = "FOLDAR (pagar queimava)"
            alpha_txt = ""
            try:
                amt = sizing_amounts(drill.get("pot_bb"), to_call,
                                     drill.get("stack_bb")).get(
                    (choice or "").lower())
                if amt:
                    alpha = amt / (amt + (drill.get("pot_bb") or 0))
                    alpha_txt = (f" — precisa que o vilão folde "
                                 f"~{alpha*100:.0f}% das vezes pra se pagar")
            except Exception:
                pass
            verdict_text = (
                f"{math_line} Você AUMENTOU: virou blefe puro"
                f"{alpha_txt}. Blefe é leitura, não conta — contra quem "
                "folda, funciona; contra estação, é caro.")
        else:
            aligned = (ch in ("call", "raise") and rec == "call") or \
                      (ch == "fold" and rec == "fold")
            verdict = "boa" if aligned else "ruim"
            if aligned and ch == "raise" and rec == "call":
                # o aluno AUMENTOU num spot em que a conta prova o call:
                # a imagem dizia "DECISÃO CERTA: PAGAR" por cima de um raise
                # marcado como bom — contradição (caso real). A conta só
                # avalia call vs fold; o rótulo certo é o PISO.
                correct = "NÃO FOLDAR (call é o piso)"
                verdict_text = (
                    f"Você aumentou — certo no essencial: {math_line} "
                    "Seu raise adiciona fold equity por cima do piso (a "
                    "conta não avalia o raise); o único erro claro aqui "
                    "era foldar.")
            else:
                verdict_text = (
                    f"Você respondeu {ch_lbl} — "
                    + ("certo. " if aligned else f"o certo era {correct}. ")
                    + math_line)
        # reconcilia com o filme: se a mão real terminou diferente, avisa
        if actual and actual != rec and actual != ch:
            verdict_text += f" (Na mão real o herói {real_lbl}.)"
    else:
        verdict = "mista"
        correct = "Valor vs controle do pote"
        base = ("Sem aposta pra pagar, a questão é apostar por valor ou "
                "controlar o tamanho do pote — não tem gabarito de conta única.")
        verdict_text = (f"Sua equity bruta é ~{eq*100:.0f}%. " + base) if eq \
            is not None else base

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

