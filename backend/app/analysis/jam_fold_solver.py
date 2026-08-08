"""Solver jam/fold heads-up em runtime — com EV por mão e ajuste de ICM.

Fictitious play sobre a matriz de equity exata (gerada uma vez). Além das
frequências de equilíbrio, expõe o EV de cada mão:

- **chip-EV** (bf=1.0): fichas valem o valor de face.
- **ICM** (bf>1.0): fichas PERDIDAS valem `bf` vezes mais que as ganhas
  (bubble factor) — o equilíbrio inteiro é re-resolvido sob essa utilidade.
  Aproximação simétrica, claramente rotulada; o bf exato de uma mesa vem
  da tool `bubble_factor` (Malmuth-Harville).

Resolve em ~1s por stack (numpy) e cacheia por (stack, bf).
"""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

_DATA = Path(__file__).parent / "data" / "preflop_equity.json.gz"
_ITERS = 3000


@lru_cache
def _matrix() -> tuple[list[str], np.ndarray, np.ndarray] | None:
    if not _DATA.exists():
        return None
    with gzip.open(_DATA, "rt") as f:
        payload = json.load(f)
    return payload["hands"], np.array(payload["equity"]), np.array(payload["overlap"])


def available() -> bool:
    return _matrix() is not None


@lru_cache(maxsize=64)
def solve_jam_fold(stack_bb: float, bf: float = 1.0,
                   ante_bb: float = 0.0) -> dict | None:
    """Equilíbrio SB-shove vs BB-call com EVs por mão (em BB, do início da mão).

    Perdas multiplicadas por `bf` (ICM); bf=1.0 = chip-EV puro.
    `ante_bb`: ante POR JOGADOR em bb (ex.: 100/200(25) -> 0.125). O ante é
    dinheiro morto: aumenta o custo do fold e o prêmio do pote não disputado —
    sem ele o equilíbrio sai sistematicamente mais tight que o dos torneios
    reais (achado do conselho de revisão).
    Retorna {hands, sb_jam, bb_call, sb_ev, bb_ev, bf, stack, ante}.
    """
    data = _matrix()
    if data is None:
        return None
    hands, E, W = data
    s = float(stack_bb)
    a = max(0.0, float(ante_bb))
    n = len(hands)

    # utilidades (referência: início da mão; SB postou 0.5+a, BB postou 1+a)
    # showdown: ganha s (peso 1) ou perde s (peso bf) — antes fazem parte dos
    # stacks e se transferem inteiros no all-in, então o showdown não muda.
    # E[i,j] = equity da mão da LINHA vs a da coluna. A mesma matriz serve aos
    # dois papéis: ev[x] = soma sobre a coluna com a PRÓPRIA mão na linha x.
    # (NUNCA transpor aqui — transposta calcula o EV do BB com a equity do SB
    # e inverte a estratégia inteira: bug real que mandava pagar com 72o.)
    show = E * s - (1 - E) * s * bf
    sb_fold = -(0.5 + a) * bf     # fold entrega blind + ante
    bb_fold = -(1.0 + a) * bf
    uncontested = 1.0 + a         # jam ganha o blind do BB + o ante dele

    sb = np.ones(n)
    bb = np.zeros(n)
    avg_sb = sb.copy()
    avg_bb = bb.copy()

    for t in range(1, _ITERS + 1):
        reach = W * avg_sb[None, :]
        denom = np.maximum(reach.sum(axis=1), 1e-12)
        ev_call_bb = (reach * show).sum(axis=1) / denom   # [mão do BB]
        br_bb = (ev_call_bb > bb_fold).astype(float)

        denom_sb = np.maximum(W.sum(axis=1), 1e-12)
        ev_jam_sb = (W * ((1 - avg_bb[None, :]) * uncontested
                          + avg_bb[None, :] * show)).sum(axis=1) / denom_sb
        br_sb = (ev_jam_sb > sb_fold).astype(float)

        avg_sb += (br_sb - avg_sb) / t
        avg_bb += (br_bb - avg_bb) / t

    # EVs finais contra as estratégias médias (equilíbrio)
    reach = W * avg_sb[None, :]
    denom = np.maximum(reach.sum(axis=1), 1e-12)
    ev_call_bb = (reach * show).sum(axis=1) / denom
    denom_sb = np.maximum(W.sum(axis=1), 1e-12)
    ev_jam_sb = (W * ((1 - avg_bb[None, :]) * uncontested
                      + avg_bb[None, :] * show)).sum(axis=1) / denom_sb

    return {
        "hands": hands,
        "stack": s,
        "bf": bf,
        "ante": a,
        "sb_jam": {h: round(float(f), 3) for h, f in zip(hands, avg_sb)},
        "bb_call": {h: round(float(f), 3) for h, f in zip(hands, avg_bb)},
        # EV da ação (jam/call) por mão; fold vale sb_fold/bb_fold — a diferença
        # é o quanto a ação ganha/perde versus desistir
        "sb_ev": {h: round(float(e), 3) for h, e in zip(hands, ev_jam_sb)},
        "bb_ev": {h: round(float(e), 3) for h, e in zip(hands, ev_call_bb)},
        "sb_fold_ev": round(sb_fold, 3),
        "bb_fold_ev": round(bb_fold, 3),
        "aviso": _aviso_de_degeneracao(avg_sb, avg_bb, bf),
    }


def _aviso_de_degeneracao(avg_sb, avg_bb, bf: float) -> str | None:
    """A aproximação simétrica de bf quebrou? Então diga, não entregue range.

    Achado da auditoria (07/08): com bf>=2 o solver devolve "empurre 100% do
    range" a 10bb, e em bf=3 o 32o marca EV positivo. Investigado: NÃO é erro
    de conta nem de convergência — é o equilíbrio correto DESTE modelo. Com
    bf=3 o BB só paga 4.7% (AA, AKs, KK, QQ, JJ, TT, 99, 88); contra alguém
    que folda 95% das vezes, empurrar qualquer duas cartas ganha 1.125bb sem
    disputa, mais que os 0.625bb que o fold entrega.

    O defeito é o MODELO: aplicar o mesmo bf aos dois lados (o docstring já
    chama de "aproximação simétrica") exagera o aperto do pagador sem
    representar que o empurrador também arrisca ser eliminado. Numa bolha de
    verdade o bf é assimétrico, e nenhum solver de ICM manda jogar 100%.

    Não dá para consertar sem stacks+payouts aqui dentro. Dá para AVISAR —
    e um range que o coach não pode citar é melhor que um range errado.
    """
    jam = float((avg_sb > 0.5).mean())
    call = float((avg_bb > 0.5).mean())
    if bf > 1.0 and (jam >= 0.99 or call <= 0.06):
        return ("MODELO DEGENERADO: com bf={:.1f} este solver devolve "
                "jam {:.0f}% / call {:.0f}%. É o equilíbrio do modelo de bf "
                "SIMÉTRICO, não conselho de bolha — o pagador aperta demais "
                "e o empurrador não paga por arriscar eliminação. NÃO cite "
                "esse range ao aluno; fale da DIREÇÃO (na bolha o call "
                "aperta muito) e use bf <= 1.6 para número."
                .format(bf, jam * 100, call * 100))
    return None
