"""Testes do pacote solver: river CFR+, população/exploit e Nash real (se gerado).

O caso do river é o gabarito clássico da teoria: range polarizado vs
bluff-catchers com aposta pote → agressão total ~75% (valor:blefe 2:1).
"""
import math
from pathlib import Path

import pytest

from app.analysis.population import exploit_hints, population_tendencies
from app.analysis.river_solver import solve_river
from app.parsers import parse_text

PS = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"


# ------------------------------ river CFR+ ------------------------------
def test_river_polarized_matches_theory():
    r = solve_river(
        board=["Kh", "8d", "5c", "2s", "7h"],
        oop_range="AA, 33",      # nuts + ar
        ip_range="QQ",           # só bluff-catchers
        pot=100, stack=100, player="oop", iterations=400,
    )
    freqs = {k: v["freq_pct"] for k, v in r["actions"].items()}
    aggression = sum(v for k, v in freqs.items() if k != "check")
    # teoria: 75% de agressão (6 AA + 3 combos de blefe) / 25% check
    assert 66 <= aggression <= 84, freqs
    # o valor (AA) aposta; o ar aparece no check
    jam_examples = " ".join(r["actions"].get("jam", {}).get("exemplos", []))
    assert "A" in jam_examples
    check_examples = " ".join(r["actions"].get("check", {}).get("exemplos", []))
    assert "3" in check_examples


def test_river_rejects_huge_range():
    with pytest.raises(ValueError):
        solve_river(["Kh", "8d", "5c", "2s", "7h"], "top 100%", "top 100%",
                    pot=100, stack=100)


# --------------------------- população/exploit ---------------------------
def test_population_tendencies_structure():
    hands = parse_text(PS.read_text())
    t = population_tendencies(hands)
    assert t["hands_sample"] == 2
    assert set(t["streets"]) == {"preflop", "flop", "turn", "river"}
    # na mão 1 o vilão pagou 3-bet, pagou flop/turn e foldou river
    assert t["streets"]["river"]["sample"] >= 1


def test_exploit_hints_guard_small_sample():
    hands = parse_text(PS.read_text())
    t = population_tendencies(hands)
    # amostra minúscula -> sem recomendações (proteção anti-ruído)
    assert exploit_hints(t) == []


# ----------------------------- Nash real (HU) ----------------------------
nash = pytest.importorskip("app.analysis.nash_pushfold")


@pytest.mark.skipif(not nash.available(), reason="tabela Nash ainda não gerada")
class TestNashReal:
    def test_aa_always(self):
        for s in (3, 10, 20):
            assert nash.nash_jam_fold(["As", "Ac"], s, "SB")["decision"] == "push"
            assert nash.nash_jam_fold(["As", "Ac"], s, "BB")["decision"] == "call"

    def test_marginal_jams_short_folds_deep(self):
        # T2o: jam com 2bb, fold com 15bb (monotonia do equilíbrio)
        assert nash.nash_jam_fold(["Ts", "2d"], 2, "SB")["decision"] == "push"
        assert nash.nash_jam_fold(["Ts", "2d"], 15, "SB")["decision"] == "fold"

    def test_true_trash_folds_even_short(self):
        # achado do solver real: com 2bb o BB paga 100% (sem fold equity),
        # então 72o FOLDA mesmo ultra-curto — contra a intuição popular
        assert nash.nash_jam_fold(["7s", "2d"], 2, "SB")["decision"] == "fold"
        assert nash.nash_jam_fold(["7s", "2d"], 12, "SB")["decision"] == "fold"

    def test_jam_range_monotonic_in_stack(self):
        from app.analysis.nash_pushfold import _table

        t = _table()["stacks"]
        wide = len(t["5"]["sb_jam"])
        tight = len(t["15"]["sb_jam"])
        assert wide > tight

    def test_source_labeled_as_computed(self):
        r = nash.nash_jam_fold(["As", "Kd"], 10, "SB")
        assert "calculado" in r["source"]


# ---------------------------- gráfico de range ---------------------------
def test_range_chart_png():
    from app.analysis.range_chart import chart_for_query, render_range_png

    png = render_range_png({"AA": 1.0, "AKs": 0.5}, "Teste")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert chart_for_query("BTN") is not None
    assert chart_for_query("XYZ") is None
