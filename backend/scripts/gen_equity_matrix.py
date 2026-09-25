"""Gera a matriz de equity pré-flop all-in 169×169 (insumo do solver Nash).

Para cada par de mãos canônicas, Monte Carlo com amostragem de combos (respeita
interação de naipes e card removal) usando o avaliador treys. Também computa a
matriz de sobreposição de combos W[i][j] (peso exato de card removal), usada no
fictitious play.

Saída: app/analysis/data/preflop_equity.json.gz
Uso:   PYTHONPATH=. python3 scripts/gen_equity_matrix.py [iters]
"""
from __future__ import annotations

import gzip
import json
import random
import sys
import time
from pathlib import Path

from treys import Card, Evaluator

RANKS = "AKQJT98765432"
SUITS = "cdhs"


def canonical_hands() -> list[str]:
    out = []
    for i, r1 in enumerate(RANKS):
        for j, r2 in enumerate(RANKS):
            if i < j:
                out.append(f"{r1}{r2}s")
                out.append(f"{r1}{r2}o")
            elif i == j:
                out.append(r1 * 2)
    return out


def combos_of(hand: str) -> list[tuple[str, str]]:
    if len(hand) == 2:
        cards = [hand[0] + s for s in SUITS]
        return [(a, b) for k, a in enumerate(cards) for b in cards[k + 1:]]
    r1, r2, kind = hand[0], hand[1], hand[2]
    out = []
    for s1 in SUITS:
        for s2 in SUITS:
            if kind == "s" and s1 != s2:
                continue
            if kind == "o" and s1 == s2:
                continue
            out.append((r1 + s1, r2 + s2))
    return out


def main() -> int:
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    hands = canonical_hands()
    n = len(hands)
    combos = [combos_of(h) for h in hands]

    # W[i][j]: nº médio de combos de j disponíveis dado um combo de i (card removal)
    W = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            total = 0
            for ci in combos[i]:
                si = set(ci)
                total += sum(1 for cj in combos[j] if not (set(cj) & si))
            W[i][j] = total / len(combos[i])

    evaluator = Evaluator()
    deck_all = [r + s for r in RANKS for s in SUITS]
    card_int = {c: Card.new(c) for c in deck_all}

    E = [[0.5] * n for _ in range(n)]
    rng = random.Random(2026)
    t0 = time.time()
    done = 0
    total_pairs = n * (n + 1) // 2

    for i in range(n):
        for j in range(i, n):
            wins = ties = valid = 0
            ci_list, cj_list = combos[i], combos[j]
            for _ in range(iters):
                ci = ci_list[rng.randrange(len(ci_list))]
                cj = cj_list[rng.randrange(len(cj_list))]
                if set(ci) & set(cj):
                    continue
                dead = set(ci) | set(cj)
                board = rng.sample([c for c in deck_all if c not in dead], 5)
                b = [card_int[c] for c in board]
                hi = evaluator.evaluate(b, [card_int[ci[0]], card_int[ci[1]]])
                hj = evaluator.evaluate(b, [card_int[cj[0]], card_int[cj[1]]])
                valid += 1
                if hi < hj:
                    wins += 1
                elif hi == hj:
                    ties += 1
            eq = (wins + ties / 2) / valid if valid else 0.5
            E[i][j] = round(eq, 5)
            E[j][i] = round(1 - eq, 5)
            done += 1
        if i % 20 == 0:
            rate = done / max(time.time() - t0, 1)
            print(f"linha {i}/{n} — {done}/{total_pairs} pares, "
                  f"{rate:.0f} pares/s, ETA {(total_pairs-done)/max(rate,1)/60:.0f} min",
                  flush=True)

    out = Path("app/analysis/data")
    out.mkdir(parents=True, exist_ok=True)
    payload = {"hands": hands, "equity": E, "overlap": W, "iters": iters}
    with gzip.open(out / "preflop_equity.json.gz", "wt") as f:
        json.dump(payload, f)
    print(f"OK: {out/'preflop_equity.json.gz'} em {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
