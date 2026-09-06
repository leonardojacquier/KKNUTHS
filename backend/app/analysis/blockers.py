"""Blockers / card removal — o que as SUAS cartas tiram do range do vilão.

Linguagem de profissional: "seu A♠ bloqueia o nut flush — blefe melhor do
range" ou "seu K♦ bloqueia AK/KK do range dele — o call sobe de valor".
Tudo determinístico: enumeração de combos, zero estimativa.

Leitura clássica:
- BLEFE bom bloqueia as mãos que PAGAM (os monstros do vilão);
- CALL bom bloqueia as mãos de VALOR dele (sobram blefes no range);
- bloquear os folds do vilão é anti-blefe (ele folda menos do que parece).
"""
from __future__ import annotations

from app.analysis.ranges import expand_combos, parse_range
from app.analysis.river_solver import _strengths

_MAX = 600
# treys: rank menor = mais forte; limiar de "mão forte" = dois pares ou melhor
_TWO_PAIR_MAX_RANK = 3325


def blocker_effects(hero_cards: list[str], board: list[str],
                    villain_range: str) -> dict:
    """Quanto das mãos FORTES do vilão as suas cartas bloqueiam (por carta)."""
    if len(board) < 3:
        raise ValueError("blockers precisam de board (3-5 cartas)")
    dead = set(board)  # NÃO tira as cartas do herói: queremos medir o bloqueio
    combos = expand_combos(parse_range(villain_range), dead)
    if not combos:
        raise ValueError("range vazio dado o board")
    if len(combos) > _MAX:
        raise ValueError("range grande demais; use um range mais estreito")

    ranks = _strengths(combos, list(board))
    fortes = [c for c, r in zip(combos, ranks) if r <= _TWO_PAIR_MAX_RANK]
    total_fortes = len(fortes)
    total = len(combos)

    por_carta = {}
    hero = list(hero_cards or [])[:2]
    for hc in hero:
        bloq_fortes = sum(1 for c in fortes if hc in c)
        bloq_total = sum(1 for c in combos if hc in c)
        por_carta[hc] = {
            "combos_fortes_bloqueados": bloq_fortes,
            "pct_dos_fortes": round(100 * bloq_fortes / total_fortes, 1)
            if total_fortes else 0.0,
            "combos_bloqueados_no_range": bloq_total,
        }

    bloq_fortes_tot = sum(1 for c in fortes if set(c) & set(hero))
    pct = round(100 * bloq_fortes_tot / total_fortes, 1) if total_fortes else 0.0

    if pct >= 25:
        leitura = ("suas cartas cortam um pedaço GRANDE das mãos fortes do "
                   "vilão — blefe sobe de valor (menos combos pagam) e o "
                   "range dele fica mais blefável")
    elif pct >= 10:
        leitura = ("bloqueio moderado das mãos fortes — conta a favor do "
                   "blefe, mas não decide sozinho")
    else:
        leitura = ("suas cartas quase não bloqueiam as mãos fortes dele — "
                   "sem desconto de blocker; jogue pela equity e pelo preço")

    return {
        "board": list(board),
        "range_do_vilao": villain_range,
        "combos_no_range": total,
        "combos_fortes": total_fortes,
        "fortes_bloqueados_pct": pct,
        "por_carta": por_carta,
        "leitura": leitura,
        "nota": ("forte = dois pares ou melhor NESTE board (enumeração "
                 "determinística de combos; treys)"),
    }
