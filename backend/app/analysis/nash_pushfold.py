"""Nash push/fold heads-up REAL — equilíbrio calculado, não aproximado.

Carrega o resultado do fictitious play (scripts/gen_nash_pushfold.py) sobre a
matriz de equity exata. Cobre o jogo SB-vs-BB jam/fold — a decisão dominante
do stack curto em MTT. Para posições não-HU, o sistema cai na aproximação
por thresholds (pushfold.py), sinalizando a diferença.
"""
from __future__ import annotations

import gzip
import json
from functools import lru_cache
from pathlib import Path

from app.analysis.pushfold import canonical_hand

_DATA = Path(__file__).parent / "data" / "nash_hu.json.gz"


@lru_cache
def _table() -> dict | None:
    if not _DATA.exists():
        return None
    with gzip.open(_DATA, "rt") as f:
        return json.load(f)


def available() -> bool:
    return _table() is not None


def _nearest_stack(stacks: list[str], stack_bb: float) -> str:
    return min(stacks, key=lambda s: abs(float(s) - stack_bb))


def nash_jam_fold(cards: list[str], stack_bb: float, role: str) -> dict | None:
    """Decisão de equilíbrio calculado. role: 'SB' (empurra?) ou 'BB' (paga?).

    Retorna None se a tabela não estiver disponível ou o papel não for HU.
    """
    table = _table()
    if table is None or role not in ("SB", "BB"):
        return None
    stacks = list(table["stacks"].keys())
    key = _nearest_stack(stacks, min(max(stack_bb, 2.0), 25.0))
    entry = table["stacks"][key]
    hand = canonical_hand(cards)
    freq = (entry["sb_jam"] if role == "SB" else entry["bb_call"]).get(hand, 0.0)

    action = ("push" if role == "SB" else "call") if freq >= 0.5 else "fold"
    return {
        "applicable": True,
        "decision": action,
        "frequency": round(freq, 3),
        "hand": hand,
        "stack_bb": stack_bb,
        "stack_resolvido": float(key),
        "role": role,
        "source": "equilíbrio Nash calculado (fictitious play, matriz de equity exata)",
        "nota": "jogo jam/fold heads-up SB vs BB, chip-EV; sob ICM exigir margem extra",
    }
