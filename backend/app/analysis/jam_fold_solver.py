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
def solve_jam_fold(stack_bb: float, bf: float = 1.0) -> dict | None:
    """Equilíbrio SB-shove vs BB-call com EVs por mão (em BB, do início da mão).

    Perdas multiplicadas por `bf` (ICM); bf=1.0 = chip-EV puro.
    Retorna {hands, sb_jam, bb_call, sb_ev, bb_ev, bf, stack}.
    """
    data = _matrix()
    if data is None:
        return None
    hands, E, W = data
    s = float(stack_bb)
    n = len(hands)

    # utilidades (referência: início da mão; SB postou 0.5, BB postou 1)
    # showdown: ganha s (peso 1) ou perde s (peso bf).
    # E[i,j] = equity da mão da LINHA vs a da coluna. A mesma matriz serve aos
    # dois papéis: ev[x] = soma sobre a coluna com a PRÓPRIA mão na linha x.
    # (NUNCA transpor aqui — transposta calcula o EV do BB com a equity do SB
    # e inverte a estratégia inteira: bug real que mandava pagar com 72o.)
    show = E * s - (1 - E) * s * bf
    sb_fold = -0.5 * bf
    bb_fold = -1.0 * bf

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
        ev_jam_sb = (W * ((1 - avg_bb[None, :]) * 1.0
                          + avg_bb[None, :] * show)).sum(axis=1) / denom_sb
        br_sb = (ev_jam_sb > sb_fold).astype(float)

        avg_sb += (br_sb - avg_sb) / t
        avg_bb += (br_bb - avg_bb) / t

    # EVs finais contra as estratégias médias (equilíbrio)
    reach = W * avg_sb[None, :]
    denom = np.maximum(reach.sum(axis=1), 1e-12)
    ev_call_bb = (reach * show).sum(axis=1) / denom
    denom_sb = np.maximum(W.sum(axis=1), 1e-12)
    ev_jam_sb = (W * ((1 - avg_bb[None, :]) * 1.0
                      + avg_bb[None, :] * show)).sum(axis=1) / denom_sb

    return {
        "hands": hands,
        "stack": s,
        "bf": bf,
        "sb_jam": {h: round(float(f), 3) for h, f in zip(hands, avg_sb)},
        "bb_call": {h: round(float(f), 3) for h, f in zip(hands, avg_bb)},
        # EV da ação (jam/call) por mão; fold vale sb_fold/bb_fold — a diferença
        # é o quanto a ação ganha/perde versus desistir
        "sb_ev": {h: round(float(e), 3) for h, e in zip(hands, ev_jam_sb)},
        "bb_ev": {h: round(float(e), 3) for h, e in zip(hands, ev_call_bb)},
        "sb_fold_ev": round(sb_fold, 3),
        "bb_fold_ev": round(bb_fold, 3),
    }
