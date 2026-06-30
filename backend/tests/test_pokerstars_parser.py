from pathlib import Path

import pytest

from app.models.canonical import ActionType, HandFormat, StreetName
from app.parsers import detect_site, parse_text

SAMPLE = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"


@pytest.fixture
def raw():
    return SAMPLE.read_text()


def test_detect_site(raw):
    assert detect_site(raw) == "PokerStars"


def test_parses_two_hands(raw):
    hands = parse_text(raw)
    assert len(hands) == 2


def test_header_fields(raw):
    h = parse_text(raw)[0]
    assert h.hand_id == "243490000001"
    assert h.site == "PokerStars"
    assert h.format == HandFormat.TOURNAMENT
    assert h.tournament_id == "2900000000"
    assert h.stakes.buyin == 22.0          # $20 + $2
    assert h.stakes.small_blind == 30
    assert h.stakes.big_blind == 60
    assert h.stakes.ante == 8
    assert h.played_at == "2023-01-15T20:00:00"


def test_seats_and_positions(raw):
    h = parse_text(raw)[0]
    assert len(h.players) == 6
    pos = {p.name: p.position for p in h.players}
    assert pos["Hero"] == "SB"
    assert pos["Villain2"] == "BB"
    assert pos["Villain1"] == "BTN"     # botão é o seat 1
    assert pos["Villain5"] == "CO"


def test_hero_and_cards(raw):
    h = parse_text(raw)[0]
    assert h.hero == "Hero"
    assert h.hero_cards == ["As", "Kd"]
    assert h.hero_seat().is_hero is True


def test_streets_and_board(raw):
    h = parse_text(raw)[0]
    names = [s.name for s in h.streets]
    assert names == [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN, StreetName.RIVER]
    assert h.street(StreetName.FLOP).board == ["Ah", "7c", "2d"]
    assert h.street(StreetName.RIVER).board == ["Ah", "7c", "2d", "9s", "Kc"]
    assert h.final_board == ["Ah", "7c", "2d", "9s", "Kc"]


def test_actions_parsed(raw):
    h = parse_text(raw)[0]
    pre = h.street(StreetName.PREFLOP)
    # 3-bet do Hero: raise 300 to 420
    hero_raise = [a for a in pre.actions if a.actor == "Hero" and a.type == ActionType.RAISE]
    assert len(hero_raise) == 1
    assert hero_raise[0].amount == 300
    assert hero_raise[0].to_amount == 420

    river = h.street(StreetName.RIVER)
    allin = [a for a in river.actions if a.all_in]
    assert allin and allin[0].actor == "Hero"


def test_collected_and_pot(raw):
    h = parse_text(raw)[0]
    assert h.total_pot == 2884
    assert h.collected.get("Hero") == 2884
    assert h.rake == 0
