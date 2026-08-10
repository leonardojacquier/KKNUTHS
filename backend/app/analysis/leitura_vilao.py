"""A LEITURA da mão escura: o que ele representa, e para onde pende.

O dono pediu com todas as letras: "uma projeção do que ele provavelmente
tinha, como recomendação". A recusa anterior confundiu duas coisas. O que
continua proibido é a TAXA — "ele blefa X%" tirada de showdowns que só
existem quando alguém paga. O que sempre foi legítimo é a LEITURA: o que um
coach diz olhando a mão — "essa linha representa isso, os blefes naturais
aqui são aqueles, e pelo perfil dele pende para tal lado". Leitura é
recomendação com razões à mostra, não medição — e sai rotulada assim.

Tudo determinístico: as razões vêm dos sinais da linha (fatos do board e da
sequência), do perfil medido do vilão (rótulo sustentado por intervalo) e do
que ele JÁ mostrou neste torneio. Cada razão é citável; a inclinação é a
contagem delas. Sem número de probabilidade em lugar nenhum — "pende para"
é o máximo que a evidência sustenta, e é o que o aluno precisa para decidir.
"""
from __future__ import annotations

from typing import NamedTuple

_NOME = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7",
         "8": "8", "9": "9", "T": "10", "J": "J", "Q": "Q", "K": "K",
         "A": "A"}
_ICONE = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}


class Leitura(NamedTuple):
    inclinacao: str              # blefe | valor | polarizada
    razoes: tuple[str, ...]      # cada uma um fato citável
    representa: str              # o que a linha representa neste board
    conselho: str                # a recomendação prática


def _o_que_representa(board: list[str], sinais: tuple[str, ...]) -> str:
    """A história que a linha conta NESTE board — mãos, não porcentagem."""
    if len(board or []) < 3:
        return "agressão pré-flop: range de open, forte ou não"
    ranks = "23456789TJQKA"
    topo = _NOME[max((c[0].upper() for c in board[:3]),
                     key=lambda r: ranks.index(r))]
    partes = [f"pares de {topo} para cima, dois pares e sets"]
    if "o flush draw do flop não bateu" in sinais:
        naipe = _naipe_do_draw(board)
        partes.append(f"os draws de {naipe} que não bateram são os blefes "
                      f"naturais desta linha")
    if "o river fechou flush possível" in sinais:
        partes.append("a aposta também representa o flush que chegou — com "
                      "ou sem ele")
    return "; ".join(partes)


def _naipe_do_draw(board: list[str]) -> str:
    naipes_flop = [c[1].lower() for c in board[:3]]
    todos = [c[1].lower() for c in board]
    for n in set(naipes_flop):
        if naipes_flop.count(n) == 2 and todos.count(n) == 2:
            return _ICONE.get(n, n)
    return "?"


def ler_linha(sinais: tuple[str, ...], board: list[str], rotulo: str = "",
              ja_mostrou_blefe: bool = False,
              ja_mostrou_valor: bool = False) -> Leitura:
    """A leitura de UMA linha escura. Determinística e citável.

    O peso maior é o que ele JÁ MOSTROU neste torneio — é a única evidência
    que é DELE, não do board nem do estereótipo do perfil.
    """
    pro_blefe: list[str] = []
    pro_valor: list[str] = []

    if "o flush draw do flop não bateu" in sinais:
        pro_blefe.append("o draw natural do board não chegou — é o blefe "
                         "pronto desta linha")
    if "acordou só no river" in sinais:
        pro_blefe.append("todo mundo mostrou fraqueza e ele atacou só na "
                         "última rua")
    if "solto" in rotulo:
        pro_blefe.append("perfil solto (sustentado): o range dele chega "
                         "aqui com muita mão fraca")
    if ja_mostrou_blefe:
        pro_blefe.append("neste torneio ele JÁ mostrou blefe depois de "
                         "linha agressiva")

    if "passivo" in rotulo:
        pro_valor.append("perfil passivo (sustentado): quando ele ataca, "
                         "costuma ter")
    if "fechado" in rotulo:
        pro_valor.append("perfil fechado (sustentado): entra com pouco, "
                         "chega forte")
    if ja_mostrou_valor and not ja_mostrou_blefe:
        pro_valor.append("todas as mãos que ele mostrou agredindo neste "
                         "torneio eram valor")

    polariza = any(s.startswith("overbet") for s in sinais)
    if len(pro_blefe) > len(pro_valor):
        inclinacao = "blefe"
        conselho = ("pague mais leve nesses spots — um bluff-catcher "
                    "decente vira call")
    elif len(pro_valor) > len(pro_blefe):
        inclinacao = "valor"
        conselho = ("só continue com mão que aguenta showdown — o meio do "
                    "range é fold")
    else:
        inclinacao = "polarizada"
        conselho = ("pague com bluff-catcher ou largue a mão média — o pior "
                    "lugar é o meio")
    if polariza and inclinacao != "blefe":
        conselho += " (o overbet poucas vezes é mão média: ou muito, ou nada)"

    return Leitura(inclinacao=inclinacao,
                   razoes=tuple(pro_blefe + pro_valor),
                   representa=_o_que_representa(board, sinais),
                   conselho=conselho)
