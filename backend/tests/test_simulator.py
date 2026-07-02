"""Testes do simulador jogável (/simular): timeline, avanço, escolhas, resumo."""
from pathlib import Path

import pytest

from app.agent.analyzer import hand_timeline
from app.bot.processing import (
    RECENT_HANDS,
    build_simulation,
    remember_hands,
    sim_advance,
    sim_choose,
    sim_summary,
)
from app.config import get_settings
from app.parsers import parse_text

PS = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    RECENT_HANDS.clear()
    yield
    get_settings.cache_clear()
    RECENT_HANDS.clear()


def test_timeline_decisions_and_pot():
    hand = parse_text(PS.read_text())[0]   # mão do 3-bet com AKs
    ev = hand_timeline(hand)
    decisions = [e for e in ev if e["kind"] == "decision"]
    # herói: 3-bet preflop, bet flop, bet turn, all-in river = 4 decisões
    assert len(decisions) == 4
    assert decisions[0]["street"] == "preflop"
    assert decisions[0]["to_call"] > 0          # havia open do vilão para pagar
    assert decisions[-1]["all_in"] is True
    # pote antes da decisão do flop deve ser o pós-preflop (948)
    flop_dec = [d for d in decisions if d["street"] == "flop"][0]
    assert flop_dec["pot"] == 948


def test_simulation_full_walkthrough():
    remember_hands(555, parse_text(PS.read_text()))
    sim = build_simulation(555)
    assert sim is not None and sim["cards"] == ["As", "Kd"]

    played = 0
    step = sim_advance(sim)
    while not step["done"]:
        assert step["decision"] is not None
        assert "Sua vez" in step["narration"]
        sim_choose(sim, "call")
        played += 1
        step = sim_advance(sim)
        assert played < 20, "loop infinito"

    assert played == 4
    resumo = sim_summary(sim)
    assert "4" in resumo and "Resultado real" in resumo
    assert "equity mínima" in resumo          # preço explicado em pt simples


def test_simulation_none_without_hands():
    assert build_simulation(999999) is None


def test_sim_choose_records_board_and_whatif_offline():
    from app.bot.processing import sim_whatif

    remember_hands(556, parse_text(PS.read_text()))
    sim = build_simulation(556)
    step = sim_advance(sim)
    while not step["done"]:
        sim_choose(sim, "raise")
        step = sim_advance(sim)
    # board registrado nas decisões pós-flop (payload do modo "e se")
    flop = [r for r in sim["results"] if r["street"] == "flop"][0]
    assert flop["board"] == ["Ah", "7c", "2d"]
    # sem chave, o veredito é None e o fluxo não quebra
    assert sim_whatif(sim) is None


def test_pasted_hand_history_detected():
    from app.parsers import detect_site

    raw = PS.read_text()
    assert detect_site(raw) == "PokerStars"      # cole no chat -> vira análise
    assert detect_site("bela mão, hein?") is None  # conversa normal -> follow-up
