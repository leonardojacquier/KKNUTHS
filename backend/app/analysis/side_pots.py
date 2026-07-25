"""POTE PRINCIPAL E POTES PARALELOS — quem pode ganhar o quê.

Buraco apontado pelo aluno (com material na mão): num all-in a 3+ com stacks
DIFERENTES, o pote não é um bolo só. Quem está com o stack curto disputa
apenas a parte que cobriu; o resto vira pote paralelo entre os que têm mais
fichas. Contar o pote inteiro como prêmio do curto INFLA o EV dele — é o
mesmo tipo de erro do overcall (prêmio que não existe).

Aqui a divisão é aritmética exata a partir do que cada um colocou:
ordenam-se os investimentos e cada "degrau" vira um pote, elegível só para
quem alcançou aquele degrau e não desistiu.

O EV de cada jogador soma os potes em que ele é elegível, cada um pesado
pela equity DENTRO daquele subconjunto de adversários — não pela equity
geral (no pote paralelo o curto nem está).

VALIDAÇÃO: numa mão real de replay, a soma dos potes tem que bater com o
`total_pot` lido da sala, e quem a sala pagou tem que ser elegível ao pote
que recebeu. Está no canário.
"""
from __future__ import annotations

from app.models.canonical import ActionType, CanonicalHand


def contribuicoes(hand: CanonicalHand) -> dict[str, float]:
    """Quanto cada jogador colocou na mão inteira (raise é 'até', não '+')."""
    total: dict[str, float] = {}
    for st in hand.streets:
        na_street: dict[str, float] = {}
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - na_street.get(a.actor, 0.0)
            add = max(0.0, add)
            na_street[a.actor] = na_street.get(a.actor, 0.0) + add
            total[a.actor] = total.get(a.actor, 0.0) + add
    return total


def desistiram(hand: CanonicalHand) -> set[str]:
    return {a.actor for st in hand.streets for a in st.actions
            if a.type == ActionType.FOLD}


def dividir_potes(investido: dict[str, float],
                  fora: set[str] | None = None,
                  extra: float = 0.0) -> list[dict]:
    """Divide o total em pote principal + paralelos.

    investido: nome -> fichas colocadas. fora: quem foldou (o dinheiro DELE
    fica no pote, mas ele não disputa nada).
    extra: fichas que estão no pote mas não vieram de nenhuma ação lida
    (ante recolhido pela sala, blind que o parser não detalhou). Vão para o
    pote PRINCIPAL, que todo mundo disputa — é onde elas realmente estão.
    Devolve [{'valor': x, 'elegiveis': [nomes], 'nivel': teto}] do principal
    para o último paralelo.
    """
    fora = set(fora or ())
    vivos = {n: v for n, v in investido.items() if v > 0}
    if not vivos:
        return []
    niveis = sorted({round(v, 6) for v in vivos.values()})
    potes: list[dict] = []
    anterior = 0.0
    for nivel in niveis:
        fatia = nivel - anterior
        if fatia <= 0:
            continue
        # todo mundo que chegou NESTE nível paga esta fatia (inclusive quem
        # foldou depois de ter colocado: o dinheiro dele fica no pote)
        pagantes = [n for n, v in vivos.items() if v >= nivel - 1e-9]
        elegiveis = [n for n in pagantes if n not in fora]
        valor = fatia * len(pagantes)
        if valor <= 0:
            anterior = nivel
            continue
        if elegiveis:
            potes.append({"valor": round(valor, 6), "nivel": nivel,
                          "elegiveis": sorted(elegiveis)})
        elif potes:
            # ninguém elegível nesse degrau: o dinheiro volta pro pote anterior
            potes[-1]["valor"] = round(potes[-1]["valor"] + valor, 6)
        anterior = nivel
    if extra > 0 and potes:
        potes[0]["valor"] = round(potes[0]["valor"] + float(extra), 6)
    return potes


def ev_por_pote(hand: CanonicalHand, quem: str | None = None) -> dict:
    """EV do jogador num all-in multiway, pote a pote.

    Usa as cartas CONHECIDAS (showdown do replay) — equity exata dentro de
    cada pote, contra apenas os elegíveis àquele pote. Sem cartas de todo
    mundo, devolve a divisão dos potes sem equity (é o que dá pra afirmar).
    """
    from app.analysis.equity import equity_vs_hands

    heroi = quem or hand.hero
    if not heroi:
        return {"error": "sem herói definido nesta mão"}
    inv = contribuicoes(hand)
    if heroi not in inv:
        return {"error": f"{heroi} não colocou fichas nesta mão"}
    # o que a sala diz que está no pote e não veio de ação lida (ante,
    # blind não detalhado) entra no pote principal em vez de sumir
    extra = max(0.0, float(hand.total_pot or 0) - sum(inv.values()))
    potes = dividir_potes(inv, desistiram(hand), extra)
    if len(potes) < 2:
        return {"potes": potes, "multiway": False,
                "nota": "pote único: todos cobriram o mesmo valor"}

    conhecidas: dict[str, list[str]] = {}
    if hand.hero and hand.hero_cards:
        conhecidas[hand.hero] = list(hand.hero_cards)
    for nm, cs in (hand.shown_cards or {}).items():
        if cs and len(cs) == 2:
            conhecidas[nm] = list(cs)

    bb = hand.stakes.big_blind or 1
    board = list(hand.final_board or [])
    linhas, ev_total = [], 0.0
    devolvido_bb = 0.0
    for p in potes:
        elegivel = heroi in p["elegiveis"]
        # pote com UM elegível é aposta não paga: volta pro dono, não é
        # prêmio. Contar como pote inflaria o "pote total" e, no caso do
        # herói, sumiria com fichas que ele recebe de volta.
        if len(p["elegiveis"]) == 1:
            if elegivel:
                devolvido_bb += p["valor"] / bb
            linhas.append({"valor_bb": round(p["valor"] / bb, 2),
                           "elegiveis": p["elegiveis"], "voce_disputa": False,
                           "devolvido": True})
            continue
        linha = {"valor_bb": round(p["valor"] / bb, 2),
                 "elegiveis": p["elegiveis"], "voce_disputa": elegivel}
        rivais = [conhecidas[n] for n in p["elegiveis"]
                  if n != heroi and n in conhecidas]
        if elegivel and heroi in conhecidas and rivais:
            eq = equity_vs_hands(conhecidas[heroi], rivais, board)
            if eq is not None:
                linha["equity"] = round(eq, 4)
                linha["ev_bb"] = round(eq * p["valor"] / bb, 2)
                ev_total += eq * p["valor"] / bb
        linhas.append(linha)

    # o que voltou pro herói (aposta não paga) não é investimento perdido
    investido_bb = inv[heroi] / bb - devolvido_bb
    disputado = sum(p["valor"] for p in potes
                    if len(p["elegiveis"]) > 1) / bb
    return {
        "potes": linhas, "multiway": True,
        "investido_bb": round(investido_bb, 2),
        "ev_bruto_bb": round(ev_total, 2),
        "ev_liquido_bb": round(ev_total - investido_bb, 2),
        "pote_total_bb": round(disputado, 2),
        "devolvido_bb": round(devolvido_bb, 2),
        "nota": ("cada pote é disputado só por quem o cobriu — a sua equity "
                 "vale sobre o pote em que você está, não sobre o bolo todo"),
    }
