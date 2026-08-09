"""A estrutura do torneio, MEDIDA nas mãos do aluno.

Até aqui o `/preparar` sabia o formato pela palavra que o aluno digitava:
`/preparar turbo pko de $22`. Se ele não escreve "turbo", não há formato — e
se escreve errado, a preparação inteira sai errada com ar de certeza.

Só que a estrutura está no dado. Todo hand history de torneio traz o NÍVEL,
o big blind e o horário de cada mão; a duração do nível é a diferença entre
o primeiro instante de um nível e o do seguinte. Medido nesta base:

    Stars $0,25     5,0 min/nível  ×1,25   (turbo)
    GG $8,88       11,7 min        ×1,20
    Stars 20k      10,1 min        ×1,37
    GG $10          9,5 min        ×1,14
    GG $22         34,8 min        ×1,33   (estrutura longa)

MEDIANA, e não média — a diferença não é estética. No GG $22 a média deu
35,7 min com desvio de 38,6, porque o aluno passou 116 minutos longe da mesa
e o intervalo entrou inteiro na conta. A mediana devolveu 34,8 e não se
mexeu. O mesmo vale para o intervalo de banheiro e para o break de hora em
hora, que existem em todo torneio.

O que a medida NÃO é: ela vale para o torneio que ele JÁ jogou. Serve para o
próximo se for o mesmo torneio — por isso toda saída daqui diz de onde veio
(sala, buy-in, data), para o aluno descartar quando não for o caso. Medida
sem procedência é palpite com número.

E o número que decide alguma coisa não é "5 min/nível", é a MEIA-VIDA: com
blind subindo ×1,25 a cada 5 minutos, um stack parado perde metade do seu
valor em big blinds a cada ~15 minutos. É isso que diz a hora de começar a
brigar, e ninguém entrega isso porque ninguém mede a estrutura que o aluno
de fato joga.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Any, NamedTuple

# Pares de níveis consecutivos abaixo disto = não sei. Três pares medem tão
# pouco que a mediana é praticamente um sorteio entre eles.
MINIMO_DE_PARES = 4

# Rótulos por ritmo. São CONVENÇÃO do poker, não medição — a fronteira entre
# turbo e regular é combinada, não descoberta. Ficam aqui, em código revisado,
# pelo mesmo motivo do `DICAS_FORMATO`: o modelo narra, não arbitra.
FAIXAS = ((4.0, "hyper"), (7.5, "turbo"), (16.0, "regular"), (10**9, "lento"))


class Estrutura(NamedTuple):
    minutos_por_nivel: float
    fator_blind: float
    ritmo: str
    meia_vida_min: float | None
    pares: int
    menor_min: float
    maior_min: float
    torneio: str | None
    sala: str | None
    buyin: float | None
    quando: str | None


def _instante(h: Any) -> datetime | None:
    bruto = getattr(h, "played_at", None)
    if not bruto:
        return None
    try:
        return datetime.fromisoformat(str(bruto).replace("Z", "+00:00"))
    except ValueError:
        return None


def _mediana(xs: list[float]) -> float:
    ys = sorted(xs)
    meio = len(ys) // 2
    return ys[meio] if len(ys) % 2 else (ys[meio - 1] + ys[meio]) / 2


def _ritmo(minutos: float) -> str:
    for teto, nome in FAIXAS:
        if minutos <= teto:
            return nome
    return "lento"


def meia_vida(minutos_por_nivel: float, fator: float) -> float | None:
    """Minutos até um stack PARADO valer metade em big blinds.

    O stack em fichas não muda; o que muda é o blind. Se ele cresce por um
    fator `f` a cada nível, o stack em bb cai pelo mesmo fator, e a metade
    chega em log(2)/log(f) níveis. Fator ≤ 1 não sobe blind nenhum — devolve
    None em vez de dividir por zero ou inventar infinito.
    """
    if fator <= 1.0 or minutos_por_nivel <= 0:
        return None
    return minutos_por_nivel * math.log(2) / math.log(fator)


def medir_um_torneio(maos: list) -> Estrutura | None:
    """Uma estrutura, ou None quando não dá para saber.

    Só entram níveis com horário E big blind. A ordem é a do BLIND, não a do
    nome do nível: "V" e "IX" são texto, e ordenar texto põe IX antes de V.
    """
    por_nivel: dict[float, datetime] = {}
    ident = {"torneio": None, "sala": None, "buyin": None, "quando": None}
    for h in maos:
        st = getattr(h, "stakes", None)
        bb = float(getattr(st, "big_blind", 0) or 0)
        quando = _instante(h)
        if not st or bb <= 0 or quando is None:
            continue
        if bb not in por_nivel or quando < por_nivel[bb]:
            por_nivel[bb] = quando
        ident["torneio"] = ident["torneio"] or getattr(h, "tournament_id", None)
        ident["sala"] = ident["sala"] or getattr(h, "site", None)
        ident["buyin"] = ident["buyin"] if ident["buyin"] is not None \
            else getattr(st, "buyin", None)
        if ident["quando"] is None or quando < ident["quando"]:
            ident["quando"] = quando

    if len(por_nivel) < MINIMO_DE_PARES + 1:
        return None

    niveis = sorted(por_nivel.items())          # por big blind crescente
    duracoes, fatores = [], []
    for (bb, ini), (bb2, prox) in zip(niveis, niveis[1:]):
        minutos = (prox - ini).total_seconds() / 60
        if minutos <= 0:
            continue                            # horário fora de ordem
        duracoes.append(minutos)
        fatores.append(bb2 / bb)

    if len(duracoes) < MINIMO_DE_PARES:
        return None

    dur, fat = _mediana(duracoes), _mediana(fatores)
    return Estrutura(
        minutos_por_nivel=round(dur, 1), fator_blind=round(fat, 2),
        ritmo=_ritmo(dur), meia_vida_min=(
            round(mv) if (mv := meia_vida(dur, fat)) else None),
        pares=len(duracoes), menor_min=round(min(duracoes), 1),
        maior_min=round(max(duracoes), 1),
        torneio=ident["torneio"], sala=ident["sala"], buyin=ident["buyin"],
        quando=ident["quando"].date().isoformat() if ident["quando"] else None)


def medir(maos: list) -> list[Estrutura]:
    """Uma estrutura por torneio, do mais recente para o mais antigo."""
    por_torneio: dict[str, list] = defaultdict(list)
    for h in maos:
        tid = getattr(h, "tournament_id", None)
        if tid:
            por_torneio[str(tid)].append(h)
    medidas = [e for grupo in por_torneio.values()
               if (e := medir_um_torneio(grupo)) is not None]
    return sorted(medidas, key=lambda e: e.quando or "", reverse=True)


def escolher(medidas: list[Estrutura], buyin: float | None = None
             ) -> Estrutura | None:
    """A estrutura que fala do torneio de HOJE, se houver uma.

    Com buy-in dito, casa por ele: quem vai jogar o $22 não se prepara com a
    estrutura do $0,25 turbo. Sem buy-in dito, o mais recente — e a saída
    carimba a procedência para o aluno descartar se não for o caso.
    """
    if not medidas:
        return None
    if buyin is not None:
        iguais = [e for e in medidas if e.buyin is not None
                  and abs(e.buyin - buyin) <= max(0.01, buyin * 0.05)]
        if iguais:
            return iguais[0]
        return None       # ele disse OUTRO torneio: calar é melhor que mentir
    return medidas[0]


def texto(e: Estrutura) -> str:
    """Bloco determinístico — os números não passam pelo modelo."""
    de = " · ".join(p for p in (
        e.sala, f"${e.buyin:g}" if e.buyin else None, e.quando) if p)
    linhas = [
        "🏟 *A estrutura que você joga* (medida nas suas mãos)",
        f"• Nível de *{e.minutos_por_nivel:g} min*, blind subindo "
        f"*×{e.fator_blind:g}* — ritmo *{e.ritmo}*",
    ]
    if e.meia_vida_min:
        linhas.append(
            f"• Parado, seu stack vale *metade em bb a cada "
            f"~{e.meia_vida_min:g} min*")
    linhas.append(
        f"_{e.pares} níveis medidos ({e.menor_min:g}–{e.maior_min:g} min)"
        + (f", em {de}" if de else "") + ". Vale se for o mesmo torneio._")
    return "\n".join(linhas)
