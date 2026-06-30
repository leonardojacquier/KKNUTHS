from pathlib import Path

import pytest

from app.models.canonical import ActionType, HandFormat, StreetName
from app.parsers import detect_site, parse_text

SAMPLE = Path(__file__).parent / "sample_hands" / "ggpoker_tournament.txt"


@pytest.fixture
def raw():
    return SAMPLE.read_text()


def test_detect_ggpoker(raw):
    assert detect_site(raw) == "GGPoker"


def test_header(raw):
    h = parse_text(raw)[0]
    assert h.site == "GGPoker"
    assert h.hand_id == "TM3344556677"
    assert h.format == HandFormat.TOURNAMENT
    assert h.tournament_id == "98765432"
    assert h.stakes.buyin == 5.25
    assert h.stakes.small_blind == 150
    assert h.stakes.big_blind == 300
    assert h.stakes.ante == 30


def test_positions_and_hero(raw):
    h = parse_text(raw)[0]
    pos = {p.name: p.position for p in h.players}
    assert pos["Hero"] == "BTN"        # botão é o seat 2
    assert pos["5e6f7g8h"] == "SB"
    assert pos["9i0j1k2l"] == "BB"
    assert h.hero_cards == ["Qh", "Qd"]


def test_streets_and_3bet(raw):
    h = parse_text(raw)[0]
    assert h.street(StreetName.FLOP).board == ["Qs", "7h", "2c"]
    pre = h.street(StreetName.PREFLOP)
    hero_raises = [a for a in pre.actions if a.actor == "Hero" and a.type == ActionType.RAISE]
    assert hero_raises and hero_raises[0].to_amount == 1500   # 3-bet to 1500
