"""Testes da extração de visão v2: snapshot rico -> mão canônica com ações."""
from app.agent import analyze_hand
from app.agent.llm import _norm_card, _snapshot_to_canonical
from app.models.canonical import StreetName

RICH_SNAPSHOT = {
    "site": "GGPoker",
    "format": "tournament",
    "hero_name": "KNuths",
    "hero_cards": ["Kc", "Qh"],
    "blinds": {"small_blind": 200, "big_blind": 400, "ante": 50},
    "players": [
        {"seat": 1, "name": "Villain1", "stack": 12000, "position": "BTN"},
        {"seat": 2, "name": "KNuths", "stack": 9500, "position": "BB"},
    ],
    "actions": {
        "preflop": [
            {"actor": "Villain1", "action": "raise", "amount": 800, "to_amount": 800},
            {"actor": "KNuths", "action": "call", "amount": 400},
        ],
        "flop": [
            {"actor": "KNuths", "action": "check"},
            {"actor": "Villain1", "action": "bet", "amount": 1200},
            {"actor": "KNuths", "action": "call", "amount": 1200},
        ],
        "turn": [
            {"actor": "KNuths", "action": "check"},
            {"actor": "Villain1", "action": "allin", "amount": 10000},
            {"actor": "KNuths", "action": "fold"},
        ],
    },
    "board": {"flop": ["10c", "9c", "6d"], "turn": "3h"},
    "total_pot": 4450,
    "winner": "Villain1",
}


def test_norm_card_variants():
    assert _norm_card("10c") == "Tc"
    assert _norm_card("AS") == "As"
    assert _norm_card("kh") == "Kh"
    assert _norm_card("??") is None
    assert _norm_card(None) is None


def test_snapshot_builds_streets_and_hero():
    hand = _snapshot_to_canonical(RICH_SNAPSHOT)
    assert hand.hero == "KNuths"
    assert hand.hero_seat() is not None and hand.hero_seat().is_hero
    assert hand.hero_cards == ["Kc", "Qh"]
    assert hand.stakes.big_blind == 400

    names = [s.name for s in hand.streets]
    assert StreetName.PREFLOP in names and StreetName.TURN in names
    flop = hand.street(StreetName.FLOP)
    assert flop.board == ["Tc", "9c", "6d"]           # '10c' normalizado
    turn = hand.street(StreetName.TURN)
    assert turn.board == ["Tc", "9c", "6d", "3h"]
    assert any(a.all_in for a in turn.actions)         # allin mapeado
    assert hand.confidence == 0.85                     # com ações lidas
    assert hand.collected.get("Villain1") == 4450


def test_snapshot_analyzable():
    hand = _snapshot_to_canonical(RICH_SNAPSHOT)
    a = analyze_hand(hand)
    # o analisador reconstrói o pote e acha os spots do herói
    assert a["hero"] == "KNuths"
    assert a["position"] == "BB"
    calls = [s for s in a["spots"] if s["decision"] == "call"]
    assert calls, "calls do herói devem virar spots com pot odds"
    assert all(s["required_equity"] > 0 for s in calls)


def test_snapshot_without_actions_lower_confidence():
    poor = {"site": "GGPoker", "hero_cards": ["As", "Kd"], "players": []}
    hand = _snapshot_to_canonical(poor)
    assert hand.confidence == 0.7
    assert hand.streets == []
