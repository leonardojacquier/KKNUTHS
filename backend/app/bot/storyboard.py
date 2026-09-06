"""O SPOT DO TREINO COMO IMAGEM — a mesa desenhada a partir do drill.

Saiu do processing.py quando o freio de tamanho disparou (3616 linhas contra
o teto de 3600). É função-folha conferida por AST: não chama nenhuma outra
função do processing nem lê global de lá, então mover não cria ciclo — a
mesma propriedade que tornou seguras as extrações de leitura_da_mao e menus.
"""
from __future__ import annotations

import logging

from app.bot.menus import drill_action, sizing_amounts

log = logging.getLogger("storyboard")


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
