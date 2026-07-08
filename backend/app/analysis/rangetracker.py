"""Leitura bayesiana do range do vilão — fase 3 do motor.

O range do vilão começa no prior (chart da posição/ação pré-flop) e cada ação
dele reponderada os combos: P(combo | ação) ∝ P(ação | combo) × P(combo).

P(ação | tipo de mão) vem das tabelas LIKELIHOOD abaixo — heurísticas
EXPLÍCITAS de comportamento do field (calibráveis por showdown na fase 4),
nunca números inventados na hora. O resultado é a narração que o pro faz de
cabeça: "o bet grande derrubou blefe de 40% pra 18% — 4 pra 1 que é valor".
"""
from __future__ import annotations

from app.analysis.equity import _best_hand_score
from app.analysis.ranges import (
    OPEN_RANGES, expand_combos, parse_range, preflop_range,
)

# P(ação | tipo de mão) — comportamento típico do field de MTT low/mid.
# Só a RAZÃO entre colunas importa na reponderação.
LIKELIHOOD: dict[str, dict[str, float]] = {
    "bet_small": {"forte": 0.35, "media": 0.35, "draw": 0.30, "ar": 0.25},
    "bet_big":   {"forte": 0.55, "media": 0.12, "draw": 0.35, "ar": 0.18},
    "check":     {"forte": 0.22, "media": 0.55, "draw": 0.45, "ar": 0.62},
    "call":      {"forte": 0.45, "media": 0.55, "draw": 0.55, "ar": 0.08},
    "raise":     {"forte": 0.62, "media": 0.10, "draw": 0.25, "ar": 0.08},
}

_PREMIUM = "QQ+, AKs, AKo"


def _suit_count(cards: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in cards:
        out[c[1]] = out.get(c[1], 0) + 1
    return out


def _has_draw(combo: tuple[str, str], board: list[str]) -> bool:
    """Flush draw ou straight draw (aberto/gutshot) — só faz sentido até o turn."""
    if len(board) >= 5:
        return False
    cards = list(combo) + board
    # flush draw: 4 do mesmo naipe usando pelo menos 1 carta da mão
    suits = _suit_count(cards)
    for s, n in suits.items():
        if n == 4 and any(c[1] == s for c in combo):
            return True
    # straight draw: 4 ranks numa janela de 5, usando pelo menos 1 da mão
    from app.analysis.equity import _rank_value

    ranks = sorted({_rank_value(c[0]) for c in cards})
    hand_ranks = {_rank_value(c[0]) for c in combo}
    if 14 in ranks:
        ranks = [1] + ranks  # roda A-2-3-4-5
    for lo in range(1, 11):
        window = [r for r in ranks if lo <= r <= lo + 4]
        if len(window) >= 4 and any(lo <= r <= lo + 4 for r in hand_ranks):
            return True
    return False


class RangeTracker:
    """Acompanha o range de UM vilão ao longo da mão."""

    def __init__(self, position: str, preflop: str = "open",
                 dead: list[str] | None = None) -> None:
        pos = (position or "MP").upper()
        spec = None
        if preflop == "3bet":
            spec = preflop_range(pos, "3bet") or preflop_range("CO", "3bet")
        elif preflop == "call":
            # flat: range de open da posição menos as mãos que 3-betariam
            base = OPEN_RANGES.get(pos) or OPEN_RANGES["CO"]
            premium = set(parse_range(_PREMIUM))
            spec_hands = [x for x in parse_range(base) if x not in premium]
        if preflop != "call":
            spec_hands = parse_range(spec or OPEN_RANGES.get(pos) or OPEN_RANGES["MP"])
        self.weights: dict[tuple[str, str], float] = {
            c: 1.0 for c in expand_combos(spec_hands, set(dead or []))
        }
        self.steps: list[dict] = []

    # ------------------------------ buckets ------------------------------
    def _buckets(self, board: list[str]) -> dict[tuple[str, str], str]:
        live = [c for c, w in self.weights.items() if w > 1e-9]
        scored = []
        for c in live:
            if any(card in board for card in c):
                self.weights[c] = 0.0
                continue
            scored.append((c, _best_hand_score(list(c) + board)))
        scored.sort(key=lambda x: x[1], reverse=True)
        n = len(scored) or 1
        out: dict[tuple[str, str], str] = {}
        for i, (c, _) in enumerate(scored):
            pct = i / n
            if pct <= 0.20:
                out[c] = "forte"
            elif pct <= 0.55:
                out[c] = "media"
            else:
                out[c] = "draw" if _has_draw(c, board) else "ar"
        return out

    def shares(self, board: list[str]) -> dict[str, float]:
        """Fatia de valor/média/draw/ar do range atual (pesos normalizados)."""
        buckets = self._buckets(board)
        tot = {"forte": 0.0, "media": 0.0, "draw": 0.0, "ar": 0.0}
        for c, b in buckets.items():
            tot[b] += self.weights[c]
        s = sum(tot.values()) or 1.0
        return {k: round(v / s, 3) for k, v in tot.items()}

    # ------------------------------ update -------------------------------
    def update(self, board: list[str], action: str,
               size_pct_pot: float | None = None) -> dict:
        """Reponderada o range pela ação do vilão nesta street."""
        act = action.lower()
        if act == "bet":
            act = "bet_big" if (size_pct_pot or 50) > 66 else "bet_small"
        lk = LIKELIHOOD.get(act)
        antes = self.shares(board)
        if lk:
            buckets = self._buckets(board)
            for c, b in buckets.items():
                self.weights[c] *= lk[b]
        depois = self.shares(board)
        step = {
            "street": {0: "preflop", 3: "flop", 4: "turn", 5: "river"}.get(
                len(board), f"{len(board)} cartas"),
            "acao": act + (f" ({size_pct_pot:.0f}% do pote)" if size_pct_pot else ""),
            "antes": antes,
            "depois": depois,
        }
        self.steps.append(step)
        return step

    # ----------------------------- narração ------------------------------
    def summary(self, board: list[str]) -> dict:
        sh = self.shares(board)
        valor = sh["forte"] + 0.5 * sh["media"]
        blefe = sh["ar"] + 0.5 * sh["draw"]
        leitura = odds_pt(valor, blefe)
        return {
            "fatias": sh,
            "p_valor": round(valor, 2),
            "p_blefe_ou_draw": round(blefe, 2),
            "leitura": leitura,
            "passos": self.steps,
            "atencao": "estimativa por comportamento típico do field — "
                       "ajuste pela dinâmica do vilão",
        }


def odds_pt(p_a: float, p_b: float) -> str:
    """(0.8, 0.2) -> 'cerca de 4 pra 1 que é valor'."""
    if p_b <= 0.001:
        return "quase certeza de valor"
    if p_a <= 0.001:
        return "quase certeza de blefe/draw"
    r = p_a / p_b
    if r >= 1:
        return f"cerca de {r:.0f} pra 1 que é valor" if r >= 1.5 else \
            "equilibrado entre valor e blefe"
    inv = 1 / r
    return f"cerca de {inv:.0f} pra 1 que é blefe/draw" if inv >= 1.5 else \
        "equilibrado entre valor e blefe"


def read_villain(position: str, preflop: str, board: list[str],
                 actions: list[dict], hero_cards: list[str] | None = None) -> dict:
    """Ponto de entrada da tool: monta o tracker e aplica a linha do vilão.

    `actions`: [{"board_cards": 3|4|5, "action": "bet|check|call|raise",
                 "size_pct_pot": 75}] — board_cards diz até onde a street vê
    o board (3=flop, 4=turn, 5=river).
    """
    tr = RangeTracker(position, preflop or "open", dead=hero_cards or [])
    for a in actions or []:
        k = int(a.get("board_cards") or len(board))
        tr.update(board[:k], str(a.get("action") or "check"),
                  a.get("size_pct_pot"))
    return tr.summary(board)
