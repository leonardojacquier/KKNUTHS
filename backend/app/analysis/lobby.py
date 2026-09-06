"""A estrutura lida do LOBBY: tabela de blinds, relógio e stack inicial.

O `estrutura.py` mede o ritmo no histórico — só que ele só sabe do torneio
que o aluno JÁ jogou, e só onde a mão traz horário (GG e Stars; as 119 mãos
de PPPoker da base vêm de print e link, sem `played_at`). O lobby resolve as
duas faltas de uma vez: ele descreve o torneio que vai começar, e é a única
fonte para a sala onde o aluno mais joga.

O que a tela dá, e nenhum histórico dá:

    fichas iniciais · duração do nível · tabela de blinds/ante INTEIRA
    late reg · pausa · rebuy/add-on · faixa de jogadores · entradas

Divisão de trabalho, a mesma do resto do projeto: a VISÃO transcreve (é o que
ela faz bem — número impresso na tela), e a conta é daqui, determinística. O
modelo não recalcula nada.

E há uma conferência que sai de graça, testada num caso real antes de este
módulo existir. O print do "MonsterStackHyperTur" do PDQ Online trazia a
escada 25/50 · 50/100 · 100/200(25) … 10K/20K(3000); as mãos daquele clube
no banco tinham 40K/80K(10K) … 1M/2M(300K). É a MESMA escada ×100 — 11 de 11
níveis, blinds e antes. Então a tabela lida da foto pode ser conferida contra
as mãos do próprio aluno, e um erro de leitura aparece antes de virar plano
de jogo. Por isso `conferir_com_maos` compara em ESCALA: o mesmo torneio
aparece com denominação diferente entre instâncias.

O nome, aliás, mentia: "Hyper" com nível de 15 minutos e 2.000 bb de stack
inicial. Medir ganha de ler o rótulo.
"""
from __future__ import annotations

import math
from typing import Any, NamedTuple

# a partir daqui o jogo é push/fold — abaixo disso não há pós-flop de verdade
PUSH_FOLD_BB = 20.0


class Nivel(NamedTuple):
    nivel: int
    sb: float
    bb: float
    ante: float = 0.0


class Lobby(NamedTuple):
    """O que a tela de "Informações do jogo" mostra. Tudo opcional menos os
    níveis: sala diferente mostra campo diferente, e faltar campo é normal —
    inventar não é."""
    niveis: tuple[Nivel, ...]
    nome: str | None = None
    buyin: float | None = None
    taxa: float | None = None
    fichas_iniciais: float | None = None
    minutos_por_nivel: float | None = None
    late_reg_nivel: int | None = None
    pausa_min: float | None = None
    pausa_cada_min: float | None = None
    rebuy: str | None = None
    addon: str | None = None
    jogadores: int | None = None
    faixa_max: int | None = None


class Marco(NamedTuple):
    nivel: int
    bb: float
    stack_bb: float
    minuto: int


def _relogio(minutos: float) -> str:
    h, m = divmod(int(round(minutos)), 60)
    return f"{h}h{m:02d}" if h else f"{m}min"


def minuto_do_nivel(lobby: Lobby, nivel: int) -> float | None:
    """Minutos de torneio até o nível COMEÇAR, pausas incluídas.

    A pausa não é detalhe: 5 min a cada 55 empurram o nível 12 em 15 minutos.
    Quem planeja "vou estar em push/fold às 3h" e ignora as pausas erra a
    conta para menos, que é o lado ruim de errar.
    """
    if not lobby.minutos_por_nivel or nivel < 1:
        return None
    jogo = (nivel - 1) * lobby.minutos_por_nivel
    if lobby.pausa_min and lobby.pausa_cada_min:
        jogo += (jogo // lobby.pausa_cada_min) * lobby.pausa_min
    return jogo


def fator_mediano(lobby: Lobby) -> float | None:
    """Crescimento típico do blind entre níveis consecutivos.

    Mediana porque a escada não é geométrica: começa dobrando (25→50→100) e
    depois assenta em ~1,4. A média seria puxada pelo começo, que dura três
    níveis e some.
    """
    bbs = [n.bb for n in sorted(lobby.niveis, key=lambda n: n.nivel) if n.bb > 0]
    fatores = sorted(b / a for a, b in zip(bbs, bbs[1:]) if a > 0)
    if not fatores:
        return None
    meio = len(fatores) // 2
    return (fatores[meio] if len(fatores) % 2
            else (fatores[meio - 1] + fatores[meio]) / 2)


def meia_vida_min(lobby: Lobby) -> float | None:
    """Minutos até um stack PARADO valer metade em big blinds."""
    fator = fator_mediano(lobby)
    if not fator or fator <= 1 or not lobby.minutos_por_nivel:
        return None
    return lobby.minutos_por_nivel * math.log(2) / math.log(fator)


def linha_do_tempo(lobby: Lobby) -> list[Marco]:
    """Onde o stack INICIAL estará, nível a nível, se ele não ganhar nada.

    É a hipótese pessimista de propósito: serve para saber quando o relógio
    obriga a agir, não para prever o torneio.
    """
    if not lobby.fichas_iniciais:
        return []
    marcos = []
    for n in sorted(lobby.niveis, key=lambda n: n.nivel):
        if n.bb <= 0:
            continue
        minuto = minuto_do_nivel(lobby, n.nivel)
        marcos.append(Marco(n.nivel, n.bb, lobby.fichas_iniciais / n.bb,
                            int(round(minuto)) if minuto is not None else -1))
    return marcos


def quando_vira_push_fold(lobby: Lobby) -> Marco | None:
    """O primeiro nível em que o stack parado cai a 20bb ou menos."""
    for m in linha_do_tempo(lobby):
        if m.stack_bb <= PUSH_FOLD_BB:
            return m
    return None


def stack_no_fim_do_late_reg(lobby: Lobby) -> float | None:
    """Quantos bb tem quem entra no último minuto do registro tardio.

    Decide se vale a pena entrar tarde — e, para quem já está dentro, quanta
    gente nova com stack curto vai sentar procurando all-in.
    """
    if not (lobby.late_reg_nivel and lobby.fichas_iniciais):
        return None
    for n in lobby.niveis:
        if n.nivel == lobby.late_reg_nivel and n.bb > 0:
            return lobby.fichas_iniciais / n.bb
    return None


def conferir_com_maos(lobby: Lobby, maos: list) -> tuple[int, int, float | None]:
    """(níveis batidos, níveis conferíveis, escala) contra as mãos do aluno.

    Leitura de tela erra, e erro de leitura vira plano de jogo errado com ar
    de certeza. A escada de blinds é conferível: as mãos gravadas do mesmo
    clube têm que cair NELA.

    Em ESCALA, porque a mesma estrutura roda com denominação diferente entre
    instâncias — o caso conferido à mão tinha o print em 25/50 e as mãos em
    2.500/5.000. A escala é escolhida como a que mais bate, e devolvida junto
    para quem chama poder desconfiar dela.
    """
    da_foto = sorted({n.bb for n in lobby.niveis if n.bb > 0})
    do_hist = sorted({float(bb) for h in maos
                      if (bb := getattr(getattr(h, "stakes", None),
                                        "big_blind", 0) or 0) > 0})
    if not da_foto or not do_hist:
        return 0, 0, None

    def bate(escala: float) -> int:
        return sum(any(abs(h - f * escala) <= max(0.01, f * escala * 0.02)
                       for f in da_foto) for h in do_hist)

    candidatas = {h / f for h in do_hist for f in da_foto if f > 0}
    melhor = max(candidatas, key=bate, default=None)
    return (bate(melhor) if melhor else 0), len(do_hist), melhor


def texto(lobby: Lobby, conferencia: tuple[int, int, float | None] | None = None
          ) -> str:
    """Bloco determinístico do lobby — os números não passam pelo modelo."""
    linhas = [f"🏟 *{lobby.nome or 'O torneio'}* — lido do lobby"]

    inicial = (lobby.fichas_iniciais / lobby.niveis[0].bb
               if lobby.fichas_iniciais and lobby.niveis
               and lobby.niveis[0].bb > 0 else None)
    if inicial:
        linhas.append(f"• Começa com *{inicial:.0f} bb* "
                      f"({lobby.fichas_iniciais:,.0f} fichas)".replace(",", "."))
    if lobby.minutos_por_nivel:
        fator = fator_mediano(lobby)
        pedaco = f"• Nível de *{lobby.minutos_por_nivel:g} min*"
        if fator:
            pedaco += f", blind ×{fator:.2f} por nível".replace(".", ",")
        linhas.append(pedaco)
    if (mv := meia_vida_min(lobby)):
        linhas.append(f"• Parado, seu stack vale *metade em bb a cada "
                      f"~{_relogio(mv)}*")

    pf = quando_vira_push_fold(lobby)
    if pf and pf.minuto >= 0:
        linhas.append(f"• Sem ganhar nada, *push/fold no nível {pf.nivel}* "
                      f"({pf.stack_bb:.0f} bb) — por volta de "
                      f"*{_relogio(pf.minuto)}* de torneio")
    if (lr := stack_no_fim_do_late_reg(lobby)) is not None:
        linhas.append(f"• Late reg fecha no nível {lobby.late_reg_nivel}: "
                      f"quem entra no fim senta com *{lr:.0f} bb*")
    if lobby.rebuy and lobby.rebuy.lower() not in ("não", "nao", "no"):
        linhas.append(f"• Rebuy: {lobby.rebuy} — o early vira campo de tiro")

    if conferencia and conferencia[1]:
        batidos, total, _ = conferencia
        linhas.append(
            f"_Tabela conferida contra as suas mãos deste clube: "
            f"{batidos}/{total} níveis batem._" if batidos == total else
            f"⚠️ _A tabela lida bate em só {batidos} dos {total} níveis das "
            f"suas mãos deste clube — confira os números antes de confiar._")
    return "\n".join(linhas)
