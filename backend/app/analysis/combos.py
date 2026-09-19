"""Cartas prováveis: CONTAGEM de combos de um range suposto — nunca "X%".

O dono pediu "dizer que prováveis cartas ele tinha". O jeito honesto tem uma
suposição e três fatos:

- A SUPOSIÇÃO (sempre à mostra no texto): ele abre o top N% das mãos, com
  N = o PFR MEDIDO dele neste torneio. É suposição porque range de abertura
  não se observa; o que se observa é a frequência com que ele abriu.
- Os FATOS dado isso: quais combos são fisicamente possíveis (bloqueadores:
  board e as SUAS cartas), e o que cada um vira NESTE board — valor,
  marginal, draw, ar — pela mesma régua `forca()` do dossiê.

O que NÃO existe aqui é probabilidade ("70% de chance de blefe") nem poda
por "ele teria desistido no flop" — isso seria um modelo do jogador entrando
pela porta dos fundos. Contagem de combos dado um range declarado é
aritmética; o leitor vê a suposição e tira a conclusão.

O ranking das 169 mãos foi gerado UMA vez com o avaliador do próprio repo
(equity vs mão aleatória, Monte Carlo com seed fixa, 40k iterações por mão —
scripts/gera_ranking_169.py) e colado como constante: em runtime é tabela,
não sorteio. Equity contra aleatória é um critério declarado de ordenação,
não "o range verdadeiro" — ranges reais abrem mais suited connector e menos
ás fraco; a suposição continua sendo suposição, e o texto a carrega.
"""
from __future__ import annotations

from typing import NamedTuple

from app.analysis.equity import RANKS as _RANKS_ASC, _best_hand_score

_NAIPES = "shdc"

# 169 mãos, da melhor para a pior, por equity vs aleatória (seed fixa).
RANKING_169 = (
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "AKs",
    "AQs", "77", "AJs", "AKo", "ATs", "AQo", "AJo", "66",
    "KQs", "ATo", "A9s", "KJs", "A8s", "KTs", "KQo", "A7s",
    "55", "A9o", "KJo", "A5s", "A6s", "A8o", "QJs", "K9s",
    "KTo", "QTs", "A4s", "K8s", "A7o", "A3s", "A6o", "QJo",
    "A5o", "JTs", "Q9s", "K9o", "K7s", "A2s", "QTo", "44",
    "A4o", "K6s", "K8o", "Q8s", "A3o", "K5s", "J9s", "Q9o",
    "JTo", "K7o", "A2o", "K4s", "J8s", "K6o", "Q7s", "K3s",
    "T9s", "33", "Q6s", "Q8o", "K2s", "J9o", "K5o", "Q5s",
    "T8s", "J7s", "K4o", "Q4s", "J8o", "Q7o", "T9o", "K3o",
    "Q3s", "98s", "J6s", "Q6o", "T7s", "K2o", "Q2s", "22",
    "J5s", "T8o", "Q5o", "J7o", "J4s", "97s", "T6s", "Q4o",
    "J3s", "Q3o", "98o", "87s", "J6o", "T7o", "J2s", "96s",
    "Q2o", "T5s", "J5o", "86s", "T4s", "J4o", "97o", "T6o",
    "J3o", "95s", "T3s", "76s", "87o", "T2s", "85s", "J2o",
    "96o", "T5o", "94s", "75s", "T4o", "86o", "93s", "65s",
    "84s", "92s", "T3o", "95o", "76o", "54s", "74s", "T2o",
    "85o", "64s", "83s", "94o", "82s", "75o", "73s", "53s",
    "93o", "65o", "84o", "63s", "92o", "43s", "74o", "54o",
    "52s", "64o", "72s", "62s", "83o", "82o", "42s", "73o",
    "53o", "63o", "32s", "43o", "52o", "72o", "62o", "42o",
    "32o",
)


class Contagem(NamedTuple):
    suposicao: str              # a frase que declara o range — vai no texto
    pct: float                  # o N do top-N%
    total: int                  # combos possíveis após bloqueadores
    valor: int                  # forte (dois pares ou melhor)
    marginal: int               # par topo
    draws: int                  # flush draw de 2 cartas / OESD do flop
    ar: int                     # o resto
    draws_vivos: bool           # board incompleto: o draw ainda pode bater
    exemplos: dict              # balde -> tuple de combos legíveis (até 4)


def _combos_da_mao(mao: str) -> list[tuple[str, str]]:
    """"AKs" -> os 4 combos concretos; par -> 6; offsuit -> 12."""
    a, b = mao[0], mao[1]
    if a == b:
        return [(a + x, b + y) for i, x in enumerate(_NAIPES)
                for y in _NAIPES[i + 1:]]
    if mao.endswith("s"):
        return [(a + x, b + x) for x in _NAIPES]
    return [(a + x, b + y) for x in _NAIPES for y in _NAIPES if x != y]


def range_top(pct: float) -> list[str]:
    """As mãos do topo do ranking até cobrir `pct` dos 1326 combos."""
    alvo = max(0.0, pct) * 1326
    saida: list[str] = []
    cum = 0
    for mao in RANKING_169:
        peso = len(_combos_da_mao(mao))
        if cum + peso > alvo:
            break
        saida.append(mao)
        cum += peso
    return saida


def _classificar(cartas: tuple[str, str], board: list[str]) -> str:
    """forte | media | fraca — RELATIVA ao board, não absoluta.

    A `forca()` do dossiê olha a categoria da mão pronta, e num board
    PAREADO isso mente: em 8♦Q♠6♥9♠9♥, 55 vira "dois pares" (55+99) e sairia
    contado como valor — mas o par do board é de todo mundo, e 55 ali é um
    underpair que nenhum coach chama de valor. Aqui, dois pares só é forte
    quando os DOIS pares são do jogador; par que apoia no board é julgado
    pelo rank da carta dele contra o topo do board — a mesma fronteira do
    par topo que o dossiê já usa."""
    ranks_board = [_RANKS_ASC.index(c[0].upper()) for c in board]
    topo = max(ranks_board)
    pareado = len(set(ranks_board)) < len(ranks_board)
    cat, *resto = _best_hand_score(list(cartas) + board)
    r1, r2 = (_RANKS_ASC.index(c[0].upper()) for c in cartas)
    if cat >= 3:
        return "forte"                    # trinca ou melhor: sempre dele
    if cat == 2:
        if not pareado:
            return "forte"                # dois pares num board seco = dele
        # um dos "dois pares" é o do próprio board
        if r1 == r2:
            return "forte" if r1 > topo else "fraca"   # overpair | underpair
        return "media" if topo in (r1, r2) else "fraca"
    if cat == 1:
        # par simples: par topo (ou overpair) = media — fronteira do dossiê
        return "media" if resto and resto[0] >= topo else "fraca"
    return "fraca"


def _e_draw(cartas: tuple[str, str], board: list[str]) -> bool:
    """Flush draw de DUAS cartas ou OESD do flop usando as duas cartas.

    Só os draws inequívocos: gutshot e draw de uma carta ficam de fora — o
    balde existe para nomear os blefes NATURAIS da linha, não para inflar."""
    flop = board[:3]
    # flush draw: 2 na mão + exatamente 2 do naipe no flop, sem completar
    if cartas[0][1] == cartas[1][1]:
        naipe = cartas[0][1]
        if ([c[1] for c in flop].count(naipe) == 2
                and [c[1] for c in board].count(naipe) == 2):
            return True
    # OESD: 4 valores consecutivos entre mão+flop, usando AMBAS as cartas
    vals = sorted({_RANKS_ASC.index(c[0].upper()) for c in cartas}
                  | {_RANKS_ASC.index(c[0].upper()) for c in flop})
    da_mao = {_RANKS_ASC.index(c[0].upper()) for c in cartas}
    for i in range(len(vals) - 3):
        janela = vals[i:i + 4]
        if (janela[3] - janela[0] == 3 and da_mao <= set(janela)):
            return True
    return False


def _legivel(cartas: tuple[str, str]) -> str:
    from app.analysis.equity import pretty_cards

    return pretty_cards(list(cartas)).replace(" ", "")


def contar(pct: float, board: list[str], mortas: list[str],
           origem: str) -> Contagem | None:
    """A contagem no board dado. None quando não há board para classificar.

    `origem` diz DE ONDE veio o pct — "PFR medido 22% (41 mãos)" — porque a
    suposição sem a origem é chute com cara de conta."""
    board = [c for c in (board or []) if c]
    if len(board) < 3 or pct <= 0:
        return None
    proibidas = {c for c in board} | {c for c in (mortas or []) if c}
    baldes: dict[str, list[tuple[str, str]]] = {
        "valor": [], "marginal": [], "draws": [], "ar": []}
    for mao in range_top(pct):
        for combo in _combos_da_mao(mao):
            if combo[0] in proibidas or combo[1] in proibidas:
                continue
            f = _classificar(combo, board)
            if f == "forte":
                baldes["valor"].append(combo)
            elif f == "media":
                baldes["marginal"].append(combo)
            elif _e_draw(combo, board):
                baldes["draws"].append(combo)
            else:
                baldes["ar"].append(combo)
    total = sum(len(v) for v in baldes.values())
    if not total:
        return None
    return Contagem(
        suposicao=(f"supondo que ele entra com o top "
                   f"{round(100 * pct)}% das mãos ({origem})"),
        pct=pct, total=total,
        valor=len(baldes["valor"]), marginal=len(baldes["marginal"]),
        draws=len(baldes["draws"]), ar=len(baldes["ar"]),
        draws_vivos=len(board) < 5,
        exemplos={k: tuple(_legivel(c) for c in v[:4])
                  for k, v in baldes.items() if v})


def linhas(c: Contagem) -> list[str]:
    """O texto da contagem — chat e HTML formatam por cima."""
    nome_draw = ("draws ainda vivos" if c.draws_vivos
                 else "draws que não bateram")

    def ex(balde: str) -> str:
        e = c.exemplos.get(balde)
        return f" (ex.: {', '.join(e)})" if e else ""

    saida = [f"{c.suposicao}, sobram {c.total} combos possíveis neste board:"]
    saida.append(f"• {c.valor} de valor — do overpair para cima{ex('valor')}")
    saida.append(f"• {c.marginal} marginais — par topo{ex('marginal')}")
    saida.append(f"• {c.draws} {nome_draw}{ex('draws')}")
    saida.append(f"• {c.ar} fracas — ar e pares abaixo do topo{ex('ar')}")
    if not c.draws_vivos and c.draws:
        saida.append("Os draws que não bateram são os blefes naturais "
                     "desta linha.")
    return saida
