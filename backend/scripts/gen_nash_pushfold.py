"""Resolve o equilíbrio Nash REAL do jogo jam/fold heads-up (SB shove vs BB call).

Fictitious play sobre a matriz de equity exata + pesos de card removal:
converge para o equilíbrio do jogo de soma (quase) zero. Substitui a
aproximação por thresholds — este é o solver de verdade do stack curto.

Uso:  PYTHONPATH=. python3 scripts/gen_nash_pushfold.py
Saída: app/analysis/data/nash_hu.json  {stack_bb: {sb_jam: {hand: freq}, bb_call: {...}}}
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np

DATA = Path("app/analysis/data")
STACKS = [round(s, 1) for s in
          [2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 9, 10,
           11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 25]]
ITERS = 4000


def solve_stack(s: float, E: np.ndarray, W: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Retorna (freq_jam_SB, freq_call_BB) por mão canônica no equilíbrio.

    Payoffs em BB, relativos ao início da mão (SB postou 0.5, BB postou 1):
      SB folda: -0.5 | SB jam + BB folda: +1.0 | showdown: 2s·eq − s.
    """
    n = E.shape[0]
    sb = np.ones(n)            # começa jam-any
    bb = np.zeros(n)
    avg_sb = sb.copy()
    avg_bb = bb.copy()

    for t in range(1, ITERS + 1):
        # BB best response contra a média do SB (com card removal W[j,i])
        reach = W * avg_sb[None, :]          # [j, i]: peso de SB=i dado BB=j
        denom = reach.sum(axis=1)
        showdown_bb = 2 * s * E - s          # E[j,i] = equity de j vs i
        ev_call = (reach * showdown_bb).sum(axis=1) / np.maximum(denom, 1e-12)
        br_bb = (ev_call > -1.0).astype(float)   # folda = perde a BB postada (-1)

        # SB best response contra a média do BB
        reach_sb = W                          # BB pode ter qualquer mão
        denom_sb = reach_sb.sum(axis=1)
        showdown_sb = 2 * s * E - s           # E[i,j] = equity de i vs j
        ev_jam = (reach_sb * ((1 - avg_bb[None, :]) * 1.0
                              + avg_bb[None, :] * showdown_sb)).sum(axis=1)
        ev_jam = ev_jam / np.maximum(denom_sb, 1e-12)
        br_sb = (ev_jam > -0.5).astype(float)

        avg_sb += (br_sb - avg_sb) / t
        avg_bb += (br_bb - avg_bb) / t

    return avg_sb, avg_bb


def main() -> int:
    src = DATA / "preflop_equity.json.gz"
    if not src.exists():
        print("ERRO: rode scripts/gen_equity_matrix.py primeiro.")
        return 1
    with gzip.open(src, "rt") as f:
        payload = json.load(f)
    hands = payload["hands"]
    E = np.array(payload["equity"])
    W = np.array(payload["overlap"])

    out: dict = {"hands": hands, "stacks": {}}
    for s in STACKS:
        jam, call = solve_stack(s, E, W)
        out["stacks"][str(s)] = {
            "sb_jam": {h: round(float(f), 3) for h, f in zip(hands, jam) if f > 0.01},
            "bb_call": {h: round(float(f), 3) for h, f in zip(hands, call) if f > 0.01},
        }
        jam_pct = 100 * float((jam * 1).mean())
        call_pct = 100 * float((call * 1).mean())
        print(f"stack {s:>4}bb: SB jam {jam_pct:5.1f}% das mãos | BB call {call_pct:5.1f}%")

    with gzip.open(DATA / "nash_hu.json.gz", "wt") as f:
        json.dump(out, f)
    print(f"OK: {DATA/'nash_hu.json.gz'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
