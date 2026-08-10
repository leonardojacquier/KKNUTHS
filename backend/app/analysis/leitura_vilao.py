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


def plano_contra(rotulo: str = "", gap_pp: int | None = None,
                 vpip_pct: int | None = None, margem_pp: int | None = None,
                 blefes_vistos: int = 0, valor_visto: int = 0,
                 overfold: bool = False, fold_pct: int | None = None,
                 limiar_pct: int | None = None) -> list[str]:
    """O plano de jogo contra ELE — a síntese que o dono pediu.

    Cada conselho carrega a evidência entre parênteses: conselho sem a
    origem é opinião, e opinião o aluno já tem de graça. Tudo vem do que os
    módulos mediram (rótulo sustentado, gap, showdowns, defesa) — nada de
    modelo, nada de taxa inventada.
    """
    plano: list[str] = []

    if "solto" in rotulo and vpip_pct is not None:
        plano.append(f"Pré-flop: 3-bet mais por valor — os opens dele "
                     f"carregam mão fraca (VPIP {vpip_pct}%"
                     + (f" ±{margem_pp}" if margem_pp else "") + ", solto "
                     "sustentado pelo intervalo)")
    if "fechado" in rotulo:
        plano.append("Pré-flop: roube os blinds dele sem medo — e abandone "
                     "quando ele acordar (perfil fechado sustentado)")
    if "passivo" in rotulo and gap_pp is not None:
        plano.append(f"Pós-flop: aposte por valor mais fino — ele paga e "
                     f"não ataca (gap de {gap_pp}pp entre entrar e atacar)")
        plano.append(f"Quando ELE aposta, respeite — agressão de quem "
                     f"quase nunca agride costuma ser honesta (o outro lado "
                     f"do mesmo gap de {gap_pp}pp)")

    if blefes_vistos:
        plano.append(f"River: pague mais leve — ele blefa de verdade "
                     f"(mostrou {blefes_vistos} blefe(s) neste torneio)")
    elif valor_visto:
        plano.append(f"River: o fold da mão média tende a estar certo — "
                     f"todas as {valor_visto} mãos que ele mostrou "
                     f"agredindo eram valor")

    if overfold and fold_pct is not None and limiar_pct is not None:
        plano.append(f"A correção mais urgente é SUA: contra ele você "
                     f"largou {fold_pct}% das apostas de river (o blefe "
                     f"dele lucra acima de {limiar_pct}%) — pague mais")

    if not plano:
        plano.append("Ainda não há evidência que sustente um plano "
                     "específico — jogue o padrão e deixe a amostra crescer")
    return plano


# ------------------------------------------------------------- narrativa ----
def _tamanho(fracao: float) -> str:
    if fracao > 1.1:
        return f"overbet ({fracao:.1f}× pote)"
    if fracao >= 0.75:
        return f"aposta grande ({round(100 * fracao)}% do pote)"
    if fracao >= 0.40:
        return f"aposta média ({round(100 * fracao)}% do pote)"
    return f"aposta pequena ({round(100 * fracao)}% do pote)"


def _a_carta_mudou(board: list[str], ate: int) -> str:
    """O que a carta `board[ate]` fez neste board. Fato, não leitura."""
    carta, antes = board[ate], board[:ate]
    ranks = "23456789TJQKA"
    naipes = [c[1].lower() for c in antes]
    fatos = []
    if naipes.count(carta[1].lower()) >= 2:
        fatos.append(f"completou flush possível de "
                     f"{_ICONE.get(carta[1].lower(), carta[1])}")
    if carta[0].upper() in [c[0].upper() for c in antes]:
        fatos.append("pareou o board")
    topo = max((c[0].upper() for c in antes), key=lambda r: ranks.index(r))
    if ranks.index(carta[0].upper()) > ranks.index(topo):
        fatos.append(f"overcard (acima do {_NOME[topo]})")
    return " e ".join(fatos) if fatos else "brick"


def narrar_mao(hand, vilao: str) -> list[str]:
    """A mão DELE narrada pelos números DELA — o que individualiza a análise.

    Uma frase por rua em que ele agiu: o tamanho em fração do pote naquele
    momento (não no fim), o que a carta da rua mudou, e como a mesa reagiu.
    Duas mãos só saem com o mesmo texto se foram de fato jogadas igual.
    """
    from app.models.canonical import ActionType

    board = list(getattr(hand, "final_board", None) or ())
    pos = next((p.position for p in (getattr(hand, "players", None) or ())
                if p.name == vilao and getattr(p, "position", None)), None)
    frases: list[str] = []
    pote = 0.0
    idx_rua = {"flop": 3, "turn": 4, "river": 5}
    for st in (getattr(hand, "streets", None) or ()):
        rua = str(getattr(st.name, "value", st.name)).lower()
        na_street: dict[str, float] = {}
        acoes = list(st.actions or ())
        for i, a in enumerate(acoes):
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - na_street.get(a.actor, 0.0)
            add = max(0.0, add)
            if a.actor == vilao and a.type in (ActionType.BET,
                                               ActionType.RAISE):
                if rua == "preflop":
                    bb = float(getattr(getattr(hand, "stakes", None),
                                       "big_blind", 0) or 0)
                    alvo = (a.to_amount or a.amount)
                    quanto = (f"para {alvo / bb:g}bb" if bb > 0 and alvo
                              else "")
                    de_onde = f" do {pos}" if pos else ""
                    verbo = ("3-bet" if any(
                        x.type == ActionType.RAISE and x.actor != vilao
                        for x in acoes[:i]) else "abriu")
                    frases.append(f"pré: {verbo}{de_onde} {quanto}".rstrip())
                elif pote > 0 and add > 0:
                    n = idx_rua.get(rua)
                    carta = (f" — o {rua} ({board[n - 1]}) "
                             f"{_a_carta_mudou(board, n - 1)}"
                             if n and len(board) >= n else "")
                    verbo = "aumentou:" if a.type == ActionType.RAISE                         else ""
                    frases.append(f"{rua}: {verbo}{_tamanho(add / pote)}"
                                  f"{carta}")
                # a reação da mesa à agressão dele
                depois = acoes[i + 1:]
                fugiram = [x.actor for x in depois
                           if x.type == ActionType.FOLD]
                pagaram = [x.actor for x in depois
                           if x.type == ActionType.CALL]
                reacao = []
                if pagaram:
                    reacao.append(", ".join(pagaram[:2]) + " pagou")
                if fugiram:
                    reacao.append(", ".join(fugiram[:2]) + " largou")
                if reacao and frases:
                    frases[-1] += " → " + "; ".join(reacao)
            na_street[a.actor] = na_street.get(a.actor, 0.0) + add
            pote += add
    return frases
