"""EV DE CADA DECISÃO, STREET A STREET, EM POTE MULTIWAY — sem all-in.

Pedido do aluno, nas palavras dele: "se a mão for até showdown sem all-in,
tem como calcular o EV de cada street sendo multiway? Isso é o que eu
quero." Até aqui a conta multiway só existia em all-in (potes paralelos,
overcall). Mão normal — aposta, aposta, aposta, showdown — tinha equity
mínima e o EV do call, mas com dois furos:

1. A equity saía contra quem MOSTROU no showdown. Se três viram o flop e um
   foldou no turn, o flop era tratado como heads-up: menos adversários do
   que existiam, logo equity INFLADA — o mesmo erro do overcall.
2. Aposta e aumento não tinham EV nenhum. Só o call tinha.

Aqui cada decisão do herói é avaliada com o campo que estava vivo NAQUELE
momento — cartas conhecidas de quem mostrou, range de referência pela
posição de quem não mostrou — e com EV por tipo de ação.

MODELO (declarado, porque premissa escondida vira alucinação):
  · BASE   — toda opção é medida na MESMA régua: fichas que você ainda tira
             do pote daqui pra frente. Foldar = 0; dar check NÃO é 0 (você
             segue podendo ganhar no showdown).
  · CALL   — EV = equity × pote − (1−equity) × preço. Exato, dada a equity.
  · APOSTA — dois caminhos: ou todos foldam, ou alguém paga.
             No equilíbrio multiway a defesa se reparte de modo que a chance
             de TODOS foldarem é exatamente alpha = aposta/(pote+aposta) —
             é a mesma conta do MDF que a ferramenta já usa. Então
             EV = alpha × pote + (1−alpha) × [equity × (pote+2×aposta) − aposta].
             Supõe UM pagador (o caso comum); com dois, o pote cresce mais e
             a equity pesa mais — está dito na resposta.
  · CHECK  — vai ao showdown de graça: EV = equity × pote.
  · FOLD   — 0 por definição. O que já está no pote não é mais seu.
  · CUSTO  — cada nó também traz a MELHOR opção e a diferença para a que foi
             jogada. É esse custo que soma na mão inteira (somar o EV de
             streets diferentes contaria o mesmo pote várias vezes).

EV IMEDIATO: a conta é da street, supondo que daí em diante a mão anda até
o showdown sem mais aposta. Não é o EV da árvore inteira (isso é o solver,
e ele é heads-up).
"""
from __future__ import annotations

from app.models.canonical import ActionType, CanonicalHand, StreetName

_ORDEM = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN,
          StreetName.RIVER]
_NOME = {StreetName.PREFLOP: "pré-flop", StreetName.FLOP: "flop",
         StreetName.TURN: "turn", StreetName.RIVER: "river"}


def _range_ref(hand: CanonicalHand, nome: str, agressor: str | None) -> str:
    from app.analysis.postflop_spot import _range_de

    return _range_de(hand, nome, agressor)


def _papel_pre(hand: CanonicalHand) -> dict[str, str]:
    """open / 3bet / call de cada jogador no pré-flop (o que o tracker usa)."""
    pre = hand.street(StreetName.PREFLOP)
    papel: dict[str, str] = {}
    raises = 0
    for a in (pre.actions if pre else []):
        if a.type == ActionType.RAISE:
            raises += 1
            papel[a.actor] = "open" if raises == 1 else "3bet"
        elif a.type == ActionType.CALL and a.actor not in papel:
            papel[a.actor] = "call"
    return papel


def _combos_ponderados(tracker, peso_minimo: float = 1 / 16) -> list:
    """Combos do range que o vilão REPRESENTA, repetidos pelo peso — o
    sorteio da equity é uniforme na lista, então repetir é ponderar."""
    pesos = {c: w for c, w in tracker.weights.items() if w > 1e-9}
    if not pesos:
        return []
    wmax = max(pesos.values())
    out = []
    for c, w in pesos.items():
        reps = int(round(8 * w / wmax))
        if reps >= 1 and w / wmax >= peso_minimo:
            out.extend([c] * reps)
    return out


_ACAO_TRACKER = {ActionType.BET: "bet", ActionType.RAISE: "raise",
                 ActionType.CALL: "call", ActionType.CHECK: "check"}


def ev_por_street(hand: CanonicalHand, quem: str | None = None,
                  iters: int = 6000) -> dict:
    """Cada decisão do jogador com o EV daquela jogada, contra o campo VIVO
    naquele instante. Funciona em pote multiway e sem all-in nenhum."""
    from app.analysis.equity import pretty_cards
    from app.analysis.multiway_equity import equity_vs_campo

    heroi = quem or hand.hero
    if not heroi:
        return {"error": "sem herói definido nesta mão"}
    alvo = next((p.name for p in hand.players
                 if p.name.lower() == heroi.lower()), None) \
        or next((p.name for p in hand.players
                 if heroi.lower() in p.name.lower()), None)
    if not alvo:
        return {"error": f"'{heroi}' não está na mesa"}

    cartas = (list(hand.hero_cards) if alvo == hand.hero and hand.hero_cards
              else list((hand.shown_cards or {}).get(alvo) or []))
    if len(cartas) != 2:
        return {"error": f"não sei as cartas de {alvo} — sem elas não há EV"}

    bb = hand.stakes.big_blind or 1
    mostrou = {n: list(cs) for n, cs in (hand.shown_cards or {}).items()
               if cs and len(cs) == 2 and n != alvo}
    pre = hand.street(StreetName.PREFLOP)
    agressor = None
    for a in (pre.actions if pre else []):
        if a.type == ActionType.RAISE:
            agressor = a.actor

    vivos = {p.name for p in hand.players}
    pot = 0.0
    board: list[str] = []
    decisoes: list[dict] = []
    usou_range = False
    # O RANGE QUE CADA VILÃO REPRESENTA, street a street. É contra ele que a
    # decisão se julga — nunca contra as cartas do showdown, que o aluno não
    # tinha na hora (25/09: 7 análises com ❌ no river porque "a Q completou
    # o straight dele e sua equity caiu pra 0%"). Começa na posição + ação
    # pré-flop e é repondado a cada ação dele (RangeTracker).
    from app.analysis.rangetracker import RangeTracker

    papel = _papel_pre(hand)
    trackers: dict[str, RangeTracker] = {}

    def _tracker(nome: str) -> RangeTracker:
        if nome not in trackers:
            pos = next((p.position for p in hand.players if p.name == nome),
                       None) or "MP"
            trackers[nome] = RangeTracker(pos, papel.get(nome, "call"),
                                          dead=list(cartas))
        return trackers[nome]

    for sname in _ORDEM:
        st = hand.street(sname)
        if not st:
            continue
        for c in (st.board or []):
            if c not in board:
                board.append(c)
        contrib: dict[str, float] = {}
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - contrib.get(a.actor, 0.0)
            add = max(0.0, add)
            pendente = max(contrib.values(), default=0.0)

            if a.actor == alvo and a.type != ActionType.POST:
                oponentes = sorted(v for v in vivos if v != alvo)
                usou_range = usou_range or bool(oponentes)
                # a DECISÃO: todo oponente entra com o range que representava
                # — inclusive quem mostrou depois
                if sname == StreetName.PREFLOP or len(board) < 3:
                    ranges_dec = [_range_ref(hand, n, agressor)
                                  for n in oponentes]
                else:
                    ranges_dec = [_combos_ponderados(_tracker(n))
                                  or _range_ref(hand, n, agressor)
                                  for n in oponentes]
                eq = None
                if oponentes:
                    eq = equity_vs_campo(cartas, [], ranges_dec,
                                         board, iters=iters)
                # o RESULTADO: contra as cartas de quem mostrou. Conta o que
                # aconteceu; não julga a decisão.
                conhecidas = [mostrou[n] for n in oponentes if n in mostrou]
                eq_rev = None
                if conhecidas:
                    resto = [r for n, r in zip(oponentes, ranges_dec)
                             if n not in mostrou]
                    eq_rev = equity_vs_campo(cartas, conhecidas, resto,
                                             board, iters=iters)
                # o modelo da aposta também julga a decisão: sem cartas fixas
                conhecidas_dec: list = []
                ranges = ranges_dec
                nomes_conhecidos: list = []

                def _modelo_aposta(aposta: float, pote: float,
                                   _b=list(board), _c=list(conhecidas_dec),
                                   _r=list(ranges),
                                   _nc=list(nomes_conhecidos)):
                    """(chance de TODOS foldarem, equity contra quem paga).

                    Dois cuidados que o primeiro modelo não tinha:
                    · quem MOSTROU tem cartas fixas — ou ele continua (e aí
                      não existe fold equity contra ele) ou não;
                    · a equity que vale é contra quem PAGA, não contra o
                      range inteiro (senão apostar ganhava sempre).
                    """
                    from app.analysis.multiway_equity import (continua_com,
                                                              range_que_continua)

                    if not (_c or _r) or len(_b) < 3 or pote + aposta <= 0:
                        return None
                    n = max(1, len(_c) + len(_r))
                    alpha = aposta / (pote + aposta)
                    p_folda_um = alpha ** (1.0 / n)      # MDF multiway
                    defende = 1 - p_folda_um
                    mortas = set(cartas) | set(_b)
                    for cs in _c:
                        mortas.update(cs)

                    p_fold = 1.0
                    segue_conhecidas = []
                    for nome, cs in zip(_nc, _c):
                        ref = _range_ref(hand, nome, agressor)
                        segue = continua_com(cs, ref, _b, mortas, defende)
                        if segue is None:
                            return None
                        if segue:
                            p_fold = 0.0
                            segue_conhecidas.append(cs)
                        # se não segue, ele folda sempre: p_fold não muda
                    novos = []
                    for nota in _r:
                        rc = range_que_continua(nota, _b, mortas, defende)
                        if not rc:
                            return None
                        novos.append(rc)
                        p_fold *= p_folda_um
                    if not segue_conhecidas and not novos:
                        return None
                    eq_call = equity_vs_campo(cartas, segue_conhecidas, novos,
                                              _b, iters=max(2000, iters // 2))
                    if eq_call is None:
                        return None
                    return p_fold, eq_call
                pagar = max(0.0, pendente - contrib.get(alvo, 0.0))
                pote_bb = round(pot / bb, 2)
                d = {
                    "street": _NOME[sname],
                    "board": pretty_cards(board) if board else "—",
                    "adversarios": len(oponentes),
                    "quem": [("mostrou" if n in mostrou else "range") + f":{n}"
                             for n in oponentes],
                    "pote_bb": pote_bb,
                    "acao": a.type.value,
                    "pagar_bb": round(pagar / bb, 2),
                    "aposta_bb": round((a.to_amount or a.amount) / bb, 2)
                    if a.type in (ActionType.BET, ActionType.RAISE) else 0.0,
                }
                if eq_rev is not None:
                    d["equity_vs_mao_revelada_pct"] = round(eq_rev * 100, 1)
                if eq is not None:
                    d["equity_pct"] = round(eq * 100, 1)
                    d.update(_opcoes(a, eq, pot, pagar, add, bb,
                                     _modelo_aposta))
                decisoes.append(d)

            if (a.actor != alvo and sname != StreetName.PREFLOP
                    and len(board) >= 3 and a.type in _ACAO_TRACKER):
                tamanho = (add / pot * 100 if pot > 0 and a.type in
                           (ActionType.BET, ActionType.RAISE) else None)
                _tracker(a.actor).update(list(board), _ACAO_TRACKER[a.type],
                                         tamanho)

            if a.type == ActionType.FOLD:
                vivos.discard(a.actor)
            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET,
                          ActionType.RAISE):
                pot += add
                contrib[a.actor] = contrib.get(a.actor, 0.0) + add

    premissas = [
        "EV imediato de cada street: supõe que daqui até o showdown não "
        "entra mais aposta (não é o EV da árvore inteira)",
        "a equity é contra quem estava VIVO naquele momento, não contra "
        "quem sobrou no showdown",
    ]
    if usou_range:
        premissas.append(
            "cada adversário entra com range de REFERÊNCIA pela posição e "
            "pela ação pré-flop, reponderado pela linha dele até a decisão — "
            "é suposição, não leitura")
    premissas.append(
        "equity_pct julga a DECISÃO: é contra o range que o vilão "
        "representava na hora, mesmo que ele tenha mostrado a mão depois. "
        "equity_vs_mao_revelada_pct é o RESULTADO — conta o que aconteceu "
        "e nunca vira selo de erro")
    return {
        "jogador": "VOCÊ" if alvo == hand.hero else alvo,
        "cartas": pretty_cards(cartas),
        "decisoes": decisoes,
        "multiway": any(d["adversarios"] > 1 for d in decisoes),
        # somar EV de streets diferentes não faz sentido (cada uma conta o
        # mesmo pote); o que soma é o ERRO — quanto a linha escolhida deixou
        # na mesa em relação à melhor opção de cada nó
        "custo_total_bb": round(
            sum(d.get("custo_do_erro_bb", 0.0) for d in decisoes), 2),
        "premissas": premissas,
    }


def _opcoes(a, eq: float, pot: float, pagar: float,
            aposta: float, bb: float, eq_pagos=None) -> dict:
    """As alternativas daquele nó, TODAS na mesma base: fichas que você
    ainda tira do pote daqui pra frente (foldar = 0).

    A base comum é o detalhe que faz a comparação valer. Na primeira versão
    o check valia 0 e a aposta valia +4bb — números que não se comparam,
    porque quem dá check continua podendo ganhar o pote no showdown.
    """
    opcoes: dict[str, float] = {}
    enfrenta = pagar > 0
    if enfrenta:
        # pot já inclui a aposta do vilão; pagar `pagar` e ir ao showdown
        opcoes["pagar"] = eq * pot - (1 - eq) * pagar
        opcoes["foldar"] = 0.0
        escolhida = {"call": "pagar", "fold": "foldar",
                     "raise": "aumentar"}.get(a.type.value, a.type.value)
        if a.type == ActionType.RAISE and aposta > 0:
            v = _ev_aposta(eq, pot, aposta, eq_pagos)
            if v is not None:
                opcoes["aumentar"] = v
    else:
        opcoes["check"] = eq * pot            # vai ao showdown de graça
        ref = aposta if aposta > 0 else round(2 * pot / 3, 2)
        rotulo_aposta = f"apostar {ref / bb:.2g}bb"
        if ref > 0:
            v = _ev_aposta(eq, pot, ref, eq_pagos)
            if v is not None:
                opcoes[rotulo_aposta] = v
        escolhida = ("check" if a.type == ActionType.CHECK
                     else rotulo_aposta)

    if not opcoes:
        return {}
    melhor = max(opcoes, key=lambda k: opcoes[k])
    if escolhida not in opcoes:      # a jogada feita não pôde ser avaliada
        return {"opcoes_bb": {k: round(v / bb, 2) for k, v in opcoes.items()},
                "leitura": "não consegui avaliar esta jogada com segurança"}
    ev = opcoes[escolhida]
    custo = opcoes[melhor] - ev
    out = {
        "ev_bb": round(ev / bb, 2),
        "opcoes_bb": {k: round(v / bb, 2) for k, v in opcoes.items()},
        "melhor": melhor,
        "custo_do_erro_bb": round(custo / bb, 2),
    }
    if enfrenta and pot + pagar:
        out["equity_minima_pct"] = round(100 * pagar / (pot + pagar), 1)
    if aposta > 0 and not enfrenta:
        alpha = aposta / (pot + aposta)
        out["todos_foldam_pct"] = round(alpha * 100, 1)
    out["leitura"] = (
        f"{escolhida} rende {ev / bb:+.2f}bb"
        + ("" if custo < 0.01 else
           f"; {melhor} renderia {opcoes[melhor] / bb:+.2f}bb "
           f"({custo / bb:.2f}bb de diferença)"))
    return out


def _ev_aposta(eq: float, pot: float, aposta: float,
               eq_pagos=None) -> float | None:
    """EV de apostar `aposta` num pote `pot`, mesma base das outras opções.

    No equilíbrio multiway a defesa se reparte de modo que a chance de TODOS
    foldarem é alpha = aposta/(pote+aposta) — a mesma conta do MDF. Com isso
    um blefe puro (equity 0) dá exatamente zero, que é o teste do modelo.
    Supõe UM pagador quando alguém paga.
    """
    # a equity QUANDO PAGAM é menor que a geral: quem paga é a parte do range
    # que bate em você. Sem isso o modelo dizia "aposte sempre".
    modelo = eq_pagos(aposta, pot) if eq_pagos is not None else None
    if modelo is None:
        # sem saber a equity CONTRA QUEM PAGA, o número de apostar sairia
        # otimista sempre. Melhor não oferecer a opção do que oferecer errada.
        return None
    p_fold, eq_call = modelo
    ev_pago = eq_call * (pot + 2 * aposta) - aposta
    return p_fold * pot + (1 - p_fold) * ev_pago
