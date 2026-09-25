"""Calibração das likelihoods por showdown — fase 4 (o moat de dados).

Cada showdown revela as cartas de um vilão; cada ação pós-flop dele vira uma
observação rotulada (ação, tipo de mão naquela street). As contagens da base
inteira atualizam as tabelas P(ação | tipo) do range tracker via blend
bayesiano com o prior heurístico: com pouco dado o prior manda; conforme a
base cresce, o comportamento REAL do field assume o volante.

Roda em batch (cron semanal no VPS via scripts/calibrate_likelihood.py) e
grava calibration.json — o tracker carrega o arquivo se existir.
"""
from __future__ import annotations

import itertools

from app.analysis.equity import _FULL_DECK, _best_hand_score
from app.analysis.rangetracker import LIKELIHOOD, _has_draw
from app.models.canonical import ActionType, CanonicalHand, StreetName

BUCKETS = ("forte", "media", "draw", "ar")
_ACTS = ("bet", "check", "call", "raise")


def bucket_of_combo(cards: list[str], board: list[str]) -> str:
    """Tipo da mão REVELADA vs board: percentil entre todos os combos vivos
    (mesmos cortes do tracker: top 20% forte, até 55% média, resto draw/ar)."""
    dead = set(board) | set(cards)
    mine = _best_hand_score(list(cards) + board)
    live = [c for c in _FULL_DECK if c not in dead]
    better = total = 0
    for c1, c2 in itertools.combinations(live, 2):
        total += 1
        if _best_hand_score([c1, c2] + board) > mine:
            better += 1
    pct = better / (total or 1)
    if pct <= 0.20:
        return "forte"
    if pct <= 0.55:
        return "media"
    return "draw" if _has_draw(tuple(cards), board) else "ar"


def empty_counts() -> dict:
    return {a: {b: 0 for b in BUCKETS} for a in _ACTS}


def observe_showdowns(hands: list[CanonicalHand]) -> dict:
    """Conta (ação, tipo) dos VILÕES com cartas reveladas, street a street."""
    counts = empty_counts()
    seen = set()
    for h in hands:
        key = (h.site, h.hand_id)
        if key in seen:  # a base pode ter a mesma mão de dois usuários
            continue
        seen.add(key)
        for name, cards in (h.shown_cards or {}).items():
            if name == h.hero or len(cards) != 2:
                continue
            for st in h.streets:
                if st.name == StreetName.PREFLOP or not st.board:
                    continue
                try:
                    b = bucket_of_combo(cards, list(st.board))
                except Exception:
                    continue
                for a in st.actions:
                    if a.actor != name:
                        continue
                    if a.type == ActionType.BET:
                        counts["bet"][b] += 1
                    elif a.type == ActionType.CALL:
                        counts["call"][b] += 1
                    elif a.type == ActionType.RAISE:
                        counts["raise"][b] += 1
                    elif a.type == ActionType.CHECK:
                        counts["check"][b] += 1
    return counts


def calibrated_tables(counts: dict, strength: float = 25.0) -> dict:
    """Blend bayesiano: posterior = (prior×k + observado) / (k + total do tipo).

    Sem sizing no dado bruto, o "bet" observado é repartido entre bet_small e
    bet_big na proporção do prior — os dois sobem/descem juntos com o dado.
    """
    tables = {a: dict(LIKELIHOOD[a]) for a in LIKELIHOOD}
    for b in BUCKETS:
        n_b = sum(counts[a][b] for a in _ACTS)
        if not n_b:
            continue
        for act in ("check", "call", "raise"):
            k = counts[act][b]
            tables[act][b] = round(
                (LIKELIHOOD[act][b] * strength + k) / (strength + n_b), 3)
        kb = counts["bet"][b]
        ps, pb = LIKELIHOOD["bet_small"][b], LIKELIHOOD["bet_big"][b]
        share = ps / (ps + pb)
        tables["bet_small"][b] = round(
            (ps * strength + kb * share) / (strength + n_b), 3)
        tables["bet_big"][b] = round(
            (pb * strength + kb * (1 - share)) / (strength + n_b), 3)
    return tables
