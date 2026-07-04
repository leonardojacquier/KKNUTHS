"""Testes do nível profissional: ranges, equity vs range, ICM, follow-up.

Valores de equity comparados com resultados conhecidos da literatura
(tolerância de Monte Carlo). ICM de 2 jogadores tem forma fechada exata.
"""
import math

import pytest

from app.analysis.icm import bubble_factor, icm_call_threshold, icm_equity
from app.analysis.ranges import (
    equity_vs_range,
    expand_combos,
    parse_range,
    preflop_range,
)
from app.bot.processing import LAST_ANALYSIS, process_followup
from app.config import get_settings


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    LAST_ANALYSIS.clear()
    yield
    get_settings.cache_clear()
    LAST_ANALYSIS.clear()


# ------------------------------- parser -------------------------------
def test_parse_single_hands():
    assert parse_range("AA") == ["AA"]
    assert parse_range("AKs") == ["AKs"]
    assert set(parse_range("22+")) == {r * 2 for r in "23456789TJQKA"}


def test_parse_plus_and_interval():
    assert set(parse_range("KTs+")) == {"KTs", "KJs", "KQs"}
    assert set(parse_range("22-66")) == {"22", "33", "44", "55", "66"}
    assert len(parse_range("A2s+")) == 12  # A2s..AKs


def test_parse_top_percent():
    # "top X%" é medido em COMBOS (pares=6, suited=4, offsuit=12), padrão da
    # indústria — não em classes de mão
    from app.analysis.ranges import _combos_of

    top10 = parse_range("top 10%")
    combos = sum(_combos_of(h) for h in top10)
    assert 0.09 * 1326 <= combos <= 0.12 * 1326
    assert "AA" in top10 and "KK" in top10


def test_parse_invalid_token():
    with pytest.raises(ValueError):
        parse_range("XYZ")


def test_expand_combos_counts():
    assert len(expand_combos(["AA"])) == 6
    assert len(expand_combos(["AKs"])) == 4
    assert len(expand_combos(["AKo"])) == 12
    # carta morta remove combos: As fora -> AA tem 3 combos
    assert len(expand_combos(["AA"], dead={"As"})) == 3


def test_preflop_charts_exist():
    for pos in ("UTG", "MP", "CO", "BTN", "SB"):
        assert preflop_range(pos, "open")
    assert preflop_range("BTN", "3bet")
    assert preflop_range("XX", "open") is None


# --------------------------- equity vs range ---------------------------
def test_equity_aa_vs_kk():
    # literatura: AA vs KK pré-flop ≈ 81.9%
    r = equity_vs_range(["As", "Ah"], "KK", iterations=6000, seed=7)
    assert math.isclose(r["equity"], 0.82, abs_tol=0.03)
    assert r["range_combos"] == 6


def test_equity_aks_vs_qq():
    # literatura: AKs vs QQ ≈ 46%
    r = equity_vs_range(["As", "Ks"], "QQ", iterations=6000, seed=7)
    assert math.isclose(r["equity"], 0.46, abs_tol=0.03)


def test_equity_vs_wide_range_beats_vs_tight():
    strong = equity_vs_range(["As", "Kd"], "QQ+, AK", iterations=4000, seed=3)["equity"]
    wide = equity_vs_range(["As", "Kd"], "top 30%", iterations=4000, seed=3)["equity"]
    assert wide > strong  # AK vai melhor contra range largo do que contra premium


def test_equity_dead_cards_respected():
    # range só de AA com 2 ases mortos: sobra 1 combo
    r = equity_vs_range(["Ac", "Ad"], "AA", iterations=500, seed=1)
    assert r["range_combos"] == 1


# --------------------------------- ICM ---------------------------------
def test_icm_two_players_closed_form():
    # 2 jogadores: eq_i = p1*pay1 + (1-p1)*pay2 (exato)
    eq = icm_equity([7000, 3000], [70, 30])
    assert math.isclose(eq[0], 0.7 * 70 + 0.3 * 30, abs_tol=1e-6)   # 58
    assert math.isclose(eq[1], 0.3 * 70 + 0.7 * 30, abs_tol=1e-6)   # 42


def test_icm_equal_stacks_equal_equity():
    eq = icm_equity([1000, 1000, 1000], [50, 30, 20])
    for e in eq:
        assert math.isclose(e, 100 / 3, abs_tol=1e-3)


def test_icm_sum_and_monotonic():
    eq = icm_equity([5000, 3000, 2000], [50, 30, 20])
    assert math.isclose(sum(eq), 100, abs_tol=1e-3)
    assert eq[0] > eq[1] > eq[2]
    # chip-EV puro daria 50/30/20; ICM comprime o topo
    assert eq[0] < 50 and eq[2] > 20


def test_bubble_factor_pressure():
    # bubble clássico: 4 jogadores, 3 pagos — all-in é caro em $
    stacks = [4000, 3000, 2000, 1000]
    bf = bubble_factor(stacks, [50, 30, 20], hero_idx=1, villain_idx=0)
    assert bf > 1.0
    thr = icm_call_threshold(stacks, [50, 30, 20], 1, 0)
    assert thr > 0.5  # precisa de mais que os 50% do chip-EV


def test_bubble_factor_validates_indexes():
    with pytest.raises(ValueError):
        bubble_factor([100, 100], [70, 30], 0, 0)


# ------------------------------ follow-up ------------------------------
def test_general_chat_creates_context_even_without_hands():
    # pergunta aleatória sem mão: entra no modo coach geral (offline -> fallback)
    out = process_followup(424242, "x", "como lidar com bad beats?")
    assert out is not None and "indisponível" in out.lower()
    ctx = LAST_ANALYSIS[424242]
    assert "coaching geral" in ctx["context"]["modo"]


def test_followup_fallback_without_llm():
    LAST_ANALYSIS[424243] = {
        "context": {"analysis": {"resumo": "teste"}},
        "history": [],
        "hand_row_id": None,
        "user_id": None,
    }
    out = process_followup(424243, "x", "e se o vilão for tight?")
    assert out is not None and "indisponível" in out.lower()
