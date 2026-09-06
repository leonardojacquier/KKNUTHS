import math
from pathlib import Path

from app.analysis import compute_player_stats, ev_call, pot_odds, spr
from app.analysis.tools import breakeven_bluff
from app.parsers import parse_text

SAMPLE = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"


def test_pot_odds():
    # pagar 50 num pote de 100 -> precisa de 50/150 = 33.3%
    assert math.isclose(pot_odds(100, 50), 1 / 3, rel_tol=1e-9)
    assert pot_odds(100, 0) == 0.0


def test_ev_call_neutral_at_required_equity():
    pot, to_call = 100, 50
    eq = pot_odds(pot, to_call)
    assert math.isclose(ev_call(eq, pot, to_call), 0.0, abs_tol=1e-9)


def test_ev_call_positive_above_required():
    assert ev_call(0.6, 100, 50) > 0


def test_spr():
    assert spr(300, 100) == 3.0
    assert spr(100, 0) == math.inf


def test_breakeven_bluff():
    # blefe de tamanho pote precisa de 50% de fold
    assert math.isclose(breakeven_bluff(100, 100), 0.5, rel_tol=1e-9)


def test_player_stats_from_sample():
    hands = parse_text(SAMPLE.read_text())
    s = compute_player_stats(hands, "Hero")
    assert s.hands == 2
    assert s.vpip == 50.0   # jogou 1 de 2 mãos
    assert s.pfr == 50.0    # deu raise em 1 de 2
    assert s.three_bet == 100.0  # 1 oportunidade, 1 3-bet
    assert s.af == 3.0      # 3 bets pós-flop, 0 calls
