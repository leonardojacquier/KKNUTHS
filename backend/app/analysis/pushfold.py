"""Push/fold para stacks curtos em torneio (aproximação Nash, determinística).

`HAND_RANKING` foi gerado por Monte Carlo (equity vs mão aleatória, treys, seed fixo)
com o próprio avaliador do projeto — ordenação estável e reproduzível. Os limiares
por posição/stack aproximam ranges Nash de open-shove publicados; são uma referência
de MVP (o LLM contextualiza como "aproximação"), não um solver.
"""
from __future__ import annotations

HAND_RANKING = [
    "AA", "KK", "QQ", "JJ", "TT", "99", "88", "AQs", "AKs", "AJs", "77", "AQo", "ATs",
    "AKo", "AJo", "A9s", "ATo", "A8s", "KQs", "66", "A9o", "A7s", "KTs", "KJs", "KQo", "A8o",
    "A6s", "A7o", "55", "A5s", "QJs", "QTs", "KTo", "K9s", "A4s", "KJo", "A3s", "Q9s", "JTs",
    "A6o", "QTo", "K8s", "A2s", "QJo", "K9o", "A5o", "J9s", "Q8s", "K7s", "Q9o", "A4o", "44",
    "JTo", "K8o", "K6s", "A3o", "K5s", "K7o", "T9s", "J9o", "A2o", "Q7s", "Q8o", "K4s", "J8s",
    "Q6s", "K3s", "K6o", "J7s", "K2s", "T8s", "Q5s", "33", "T9o", "Q7o", "Q4s", "J8o", "T7s",
    "K5o", "Q6o", "Q3s", "K4o", "98s", "T8o", "Q2s", "J6s", "K3o", "J5s", "22", "J7o", "Q5o",
    "J4s", "T7o", "K2o", "T6s", "97s", "Q4o", "J3s", "98o", "J2s", "87s", "96s", "Q3o", "J6o",
    "T5s", "Q2o", "J5o", "T4s", "86s", "T6o", "97o", "J4o", "T2s", "87o", "T3s", "95s", "J3o",
    "96o", "T5o", "J2o", "85s", "86o", "76s", "T4o", "94s", "93s", "92s", "T2o", "T3o", "75s",
    "95o", "84s", "85o", "65s", "76o", "82s", "83s", "54s", "74s", "93o", "64s", "94o", "92o",
    "75o", "73s", "84o", "63s", "72s", "53s", "65o", "52s", "83o", "82o", "43s", "62s", "54o",
    "74o", "64o", "42s", "73o", "63o", "32s", "53o", "72o", "52o", "62o", "43o", "42o", "32o",
]
_RANK_INDEX = {h: i for i, h in enumerate(HAND_RANKING)}
_N = len(HAND_RANKING)

# % do range que se empurra por (grupo de posição, teto de stack em bb).
# Aproximação de Nash open-shove (sem callers atrás considerados individualmente).
_THRESHOLDS: dict[str, list[tuple[float, float]]] = {
    # posição: [(stack_max_bb, % de mãos empurradas)]
    "EP":  [(5, 0.25), (8, 0.15), (10, 0.12), (12, 0.10), (15, 0.08), (20, 0.06)],
    "MP":  [(5, 0.30), (8, 0.20), (10, 0.16), (12, 0.13), (15, 0.10), (20, 0.07)],
    "CO":  [(5, 0.40), (8, 0.28), (10, 0.24), (12, 0.20), (15, 0.15), (20, 0.10)],
    "BTN": [(5, 0.50), (8, 0.38), (10, 0.33), (12, 0.28), (15, 0.22), (20, 0.14)],
    "SB":  [(5, 0.70), (8, 0.55), (10, 0.50), (12, 0.42), (15, 0.32), (20, 0.20)],
}

_POSITION_GROUP = {
    "UTG": "EP", "UTG+1": "EP", "UTG+2": "EP",
    "MP": "MP", "MP+1": "MP", "LJ": "MP", "HJ": "MP",
    "CO": "CO", "BTN": "BTN", "SB": "SB", "BB": "SB",
}


def canonical_hand(cards: list[str]) -> str:
    """['As','Kd'] -> 'AKo' ; ['Ts','9s'] -> 'T9s' ; ['7h','7d'] -> '77'."""
    order = "AKQJT98765432"
    r1, s1 = cards[0][0], cards[0][1]
    r2, s2 = cards[1][0], cards[1][1]
    if order.index(r1) > order.index(r2):
        r1, r2, s1, s2 = r2, r1, s2, s1
    if r1 == r2:
        return r1 + r2
    return f"{r1}{r2}{'s' if s1 == s2 else 'o'}"


def hand_percentile(cards: list[str]) -> float:
    """Posição da mão no ranking, 0.0 (melhor) a 1.0 (pior)."""
    return _RANK_INDEX[canonical_hand(cards)] / (_N - 1)


def shove_threshold(position: str, stack_bb: float) -> float | None:
    """% do range que se empurra (0-1) por posição/stack; None acima de 20bb."""
    group = _POSITION_GROUP.get((position or "").upper(), "MP")
    for stack_max, pct in _THRESHOLDS[group]:
        if stack_bb <= stack_max:
            return pct
    return None


def push_fold(cards: list[str], stack_bb: float, position: str,
              ante_bb: float = 0.125) -> dict:
    """Decisão push/fold para open-shove em stack curto.

    Usa o SOLVER de open-shove (equilíbrio resolvido para a posição, com os
    antes da mesa) quando disponível; a tabela estática fica de reserva. A
    tabela ignorava os antes e saía sistematicamente mais tight — e o
    gráfico de EV, que vem do solver, contradiria o veredito.

    Retorna decisão, limiar usado e o percentil da mão — o LLM usa isso para
    contextualizar ("sua mão está no top X%, o range de shove aqui é Y%").
    """
    if stack_bb <= 20:
        try:
            from app.analysis.open_shove_solver import solve_open_shove

            sol = solve_open_shove((position or "MP").upper(),
                                   round(float(stack_bb), 1), 1.0,
                                   round(float(ante_bb), 3))
        except Exception:
            sol = None
        if sol:
            mao = canonical_hand(cards)
            freq = sol["shove"].get(mao, 0.0)
            return {
                "applicable": True,
                "decision": "push" if freq > 0.5 else "fold",
                "hand": mao,
                "hand_top_pct": round(hand_percentile(cards) * 100, 1),
                "shove_range_pct": sol["shove_pct"],
                "ev_bb": sol["ev"].get(mao),
                "stack_bb": stack_bb,
                "position": position,
                "fonte": "solver",
                "premissas": sol["premissas"],
            }

    group = _POSITION_GROUP.get(position or "", "MP")
    table = _THRESHOLDS[group]
    threshold = None
    for stack_max, pct in table:
        if stack_bb <= stack_max:
            threshold = pct
            break
    if threshold is None:
        # stack > 20bb: push/fold deixa de ser o framework certo
        return {
            "applicable": False,
            "reason": "stack acima de 20bb: jogo padrão de raise/fold, não push/fold",
            "hand": canonical_hand(cards),
            "stack_bb": stack_bb,
            "position": position,
        }

    pct = hand_percentile(cards)
    return {
        "applicable": True,
        "decision": "push" if pct <= threshold else "fold",
        "hand": canonical_hand(cards),
        "hand_top_pct": round(pct * 100, 1),
        "shove_range_pct": round(threshold * 100, 1),
        "stack_bb": stack_bb,
        "position": position,
        "position_group": group,
        "note": "aproximação Nash de open-shove; ajustar por antes, ICM e leitura",
    }
