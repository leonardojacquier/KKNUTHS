"""Dossiê do vilão: as mãos que ele MOSTROU, e o que fez em cada uma.

O `/vilao` de hoje entrega frequência — VPIP, PFR, AF, com intervalo. É a
resposta certa para "que tipo de jogador é ele", e a errada para a pergunta
que o aluno faz de verdade na mesa: *"o que esse cara aposta no river?"*.

Frequência precisa de amostra e de margem. Carta virada não precisa de nada:
o aluno VIU. Medido na base, dentro de um torneio só (GG 303773218): 28
vilões mostraram mão, 192 showdowns, o maior deles 26 mãos com as cartas
abertas. Isso não é amostra, é prova — e num torneio de 4 horas com as
mesmas pessoas, é o que muda decisão.

A classificação é pela LINHA, nunca pelo resultado. Quem agride o river com
J-high blefou, tendo ganhado ou não; quem agride com dois pares apostou por
valor, mesmo que o outro tivesse trinca. Classificar pelo resultado é o
raciocínio que este projeto inteiro existe para combater — e num dossiê seria
pior, porque viraria "ele blefa muito" toda vez que o vilão perdesse.

Também não se conta frequência de blefe aqui, e é de propósito: o vilão só
mostra quando alguém paga. A mão em que ele blefou e todo mundo foldou não
está no dado, então "ele blefa X% das vezes" seria um número enviesado com
cara de medida. O que se entrega é o que se viu, e o texto diz isso.
"""
from __future__ import annotations

from typing import Any, NamedTuple

from app.analysis.equity import _best_hand_score, describe_hand

# Só showdown do RIVER conta como "o que ele aposta": all-in de pré-flop com
# board completo depois é outra coisa e vai marcado como tal.
_AGRESSIVAS = ("bet", "raise")


class MaoMostrada(NamedTuple):
    hand_id: str
    cartas: tuple[str, ...]
    board: tuple[str, ...]
    descricao: str | None       # "par de 7, kicker A"
    papel: str                  # blefe | valor | valor fino | pagou | mostrou
    rua: str | None             # onde ele foi o último agressor
    linha: str                  # "raise pré · aposta flop · aposta river"


class Dossie(NamedTuple):
    vilao: str
    showdowns: int
    blefes: tuple[MaoMostrada, ...]
    valor: tuple[MaoMostrada, ...]
    pagou: tuple[MaoMostrada, ...]
    outras: tuple[MaoMostrada, ...]


def _tipo(a: Any) -> str:
    t = getattr(a, "type", None)
    return str(getattr(t, "value", t) or "").lower()


def _nome_da_rua(s: Any) -> str:
    n = getattr(s, "name", None)
    return str(getattr(n, "value", n) or "").lower()


def forca(cartas: list[str], board: list[str]) -> str:
    """forte | media | fraca — a régua do que é valor e do que é blefe.

    A fronteira que importa é o PAR TOPO: apostar par topo é valor fino;
    apostar par de baixo ou carta alta, contra alguém que pagou, é blefe ou
    valor tão fino que dá no mesmo para o aluno decidir. Dois pares ou melhor
    é valor sem discussão.
    """
    cartas = [c for c in (cartas or []) if c]
    board = [c for c in (board or []) if c]
    if len(cartas) < 2 or len(set(cartas + board)) < 5:
        return "desconhecida"
    categoria, *resto = _best_hand_score(cartas + board)
    if categoria >= 2:
        return "forte"
    if categoria == 0:
        return "fraca"
    # par: topo do board decide
    from app.analysis.equity import _rank_value

    do_board = [_rank_value(c[0]) for c in board]
    return "media" if resto and resto[0] >= max(do_board, default=0) else "fraca"


def _linha_do_vilao(hand: Any, nome: str) -> tuple[list[str], str | None, str]:
    """(ações legíveis, rua da última agressão dele, resumo em uma linha)."""
    curto = {"preflop": "pré", "flop": "flop", "turn": "turn", "river": "river"}
    verbo = {"bet": "aposta", "raise": "aumenta", "call": "paga",
             "check": "passa", "fold": "desiste"}
    legiveis: list[str] = []
    ultima_agressao: str | None = None
    for street in (getattr(hand, "streets", None) or ()):
        rua = _nome_da_rua(street)
        for a in (getattr(street, "actions", None) or ()):
            if getattr(a, "actor", None) != nome:
                continue
            t = _tipo(a)
            if t == "post":
                continue
            if t in _AGRESSIVAS or (t == "call" and getattr(a, "all_in", False)):
                if t in _AGRESSIVAS:
                    ultima_agressao = rua
            legiveis.append(f"{verbo.get(t, t)} {curto.get(rua, rua)}")
    return legiveis, ultima_agressao, " · ".join(legiveis)


def _ultimo_agressor_da_rua(hand: Any, rua: str) -> str | None:
    for street in (getattr(hand, "streets", None) or ()):
        if _nome_da_rua(street) != rua:
            continue
        agressor = None
        for a in (getattr(street, "actions", None) or ()):
            if _tipo(a) in _AGRESSIVAS:
                agressor = getattr(a, "actor", None)
        return agressor
    return None


def _rua_final(hand: Any) -> str:
    ruas = [r for r in ("river", "turn", "flop", "preflop")
            if any(_nome_da_rua(s) == r and (getattr(s, "actions", None) or ())
                   for s in (getattr(hand, "streets", None) or ()))]
    return ruas[0] if ruas else "preflop"


def ler_mao(hand: Any, nome: str) -> MaoMostrada | None:
    """Uma mão mostrada, classificada. None se ele não mostrou nada."""
    mostradas = getattr(hand, "shown_cards", None) or {}
    cartas = mostradas.get(nome)
    if not cartas:
        return None
    board = list(getattr(hand, "final_board", None) or ())
    legiveis, agrediu_em, linha = _linha_do_vilao(hand, nome)
    final = _rua_final(hand)
    f = forca(list(cartas), board)

    if agrediu_em == final and final != "preflop":
        papel = {"fraca": "blefe", "media": "valor fino",
                 "forte": "valor"}.get(f, "mostrou")
    elif any(p.startswith("paga") for p in legiveis) and final != "preflop":
        papel = "pagou"
    else:
        papel = "mostrou"

    return MaoMostrada(
        hand_id=str(getattr(hand, "hand_id", "") or ""),
        cartas=tuple(cartas), board=tuple(board),
        descricao=describe_hand(list(cartas), board),
        papel=papel, rua=agrediu_em, linha=linha)


def montar(hands: list, nome: str) -> Dossie | None:
    """Dossiê de um vilão a partir de um conjunto de mãos (um torneio, ou
    todas). None quando ele nunca mostrou nada — e aí o certo é dizer isso,
    não devolver um dossiê vazio com cara de dossiê."""
    lidas = [m for h in (hands or []) if (m := ler_mao(h, nome))]
    if not lidas:
        return None
    return Dossie(
        vilao=nome, showdowns=len(lidas),
        blefes=tuple(m for m in lidas if m.papel == "blefe"),
        valor=tuple(m for m in lidas if m.papel in ("valor", "valor fino")),
        pagou=tuple(m for m in lidas if m.papel == "pagou"),
        outras=tuple(m for m in lidas if m.papel == "mostrou"))


def _cartas(m: MaoMostrada) -> str:
    return " ".join(m.cartas)


def texto(d: Dossie, limite: int = 4) -> str:
    """Bloco determinístico. Mão por mão, com a linha e o que ele tinha."""
    linhas = [f"🔍 *{d.vilao}* — {d.showdowns} mão(s) que você VIU as cartas"]

    def bloco(titulo: str, maos: tuple[MaoMostrada, ...]) -> None:
        if not maos:
            return
        linhas.append(f"\n*{titulo}* ({len(maos)})")
        for m in maos[:limite]:
            desc = f" — {m.descricao}" if m.descricao else ""
            linhas.append(f"• `{_cartas(m)}`{desc}\n  _{m.linha}_")
        if len(maos) > limite:
            linhas.append(f"_…e mais {len(maos) - limite}._")

    bloco("Agrediu com mão fraca (blefe)", d.blefes)
    bloco("Apostou por valor", d.valor)
    bloco("Pagou até o showdown", d.pagou)
    bloco("Mostrou sem agredir no fim", d.outras)

    linhas.append(
        "\n_Só entram mãos que foram ao showdown: o vilão só mostra quando "
        "alguém paga. Por isso aqui não há frequência de blefe — teria viés "
        "de quem paga, não medida dele._")
    return "\n".join(linhas)
