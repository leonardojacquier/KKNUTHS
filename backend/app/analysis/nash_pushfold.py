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
    if role not in ("SB", "BB"):
        return None
    hand = canonical_hand(cards)
    # preferência: equilíbrio em RUNTIME com ANTE (torneio real tem ante; a
    # tabela estática sem ante sai tight — achado do conselho). Cai na tabela
    # estática se o solver não estiver disponível.
    freq = None
    key = f"{min(max(stack_bb, 2.0), 25.0):g}"
    nota_ante = "com ante 12.5% do bb"
    try:
        from app.analysis.jam_fold_solver import solve_jam_fold

        sol = solve_jam_fold(round(min(max(stack_bb, 2.0), 25.0), 1), 1.0, 0.125)
        if sol:
            freq = (sol["sb_jam"] if role == "SB" else sol["bb_call"]).get(hand, 0.0)
    except Exception:
        freq = None
    if freq is None:
        table = _table()
        if table is None:
            return None
        stacks = list(table["stacks"].keys())
        key = _nearest_stack(stacks, min(max(stack_bb, 2.0), 25.0))
        entry = table["stacks"][key]
        freq = (entry["sb_jam"] if role == "SB" else entry["bb_call"]).get(hand, 0.0)
        nota_ante = "sem ante (tabela estática)"

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
        "nota": f"jogo jam/fold heads-up SB vs BB, chip-EV, {nota_ante}; "
                "sob ICM exigir margem extra",
    }
