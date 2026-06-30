"""Testes das frentes Claude + persistência, no caminho offline (sem chaves).

Garantem que o produto degrada graciosamente: sem ANTHROPIC_API_KEY o coaching cai
no resumo determinístico; sem Supabase o repositório vira no-op.
"""
import math
from pathlib import Path

from app.agent import analyze_hand
from app.agent.llm import _dispatch, coach
from app.db import get_repository
from app.ingestion import ingest
from app.parsers import parse_text

PS = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"


def test_coach_falls_back_without_api_key():
    structured = analyze_hand(parse_text(PS.read_text())[0])
    out = coach(structured, None, lang="pt")
    # sem chave -> exatamente o resumo determinístico
    assert out == structured["summary"]


def test_tool_dispatch_matches_pure_functions():
    assert math.isclose(_dispatch("pot_odds", {"pot": 100, "to_call": 50}), 1 / 3, rel_tol=1e-9)
    assert math.isclose(_dispatch("ev_call", {"equity": 0.6, "pot": 100, "to_call": 50}), 40.0)
    assert _dispatch("spr", {"effective_stack": 300, "pot": 100}) == 3.0
    eq = _dispatch("equity", {"hero_cards": ["As", "Ac"], "board": []})
    assert 0.8 < eq < 0.9   # AA vs 1 random ~85%


def test_repository_disabled_without_config():
    repo = get_repository()
    assert repo.enabled is False
    assert repo.get_or_create_user(123, "x") is None
    assert repo.save_hand("u", parse_text(PS.read_text())[0]) is None
    assert repo.search_analysis("u", [0.0] * 1536) == []


def test_image_ingest_needs_review_without_vision():
    res = ingest(b"\x89PNG fake bytes", "png")
    assert res.hands == []
    assert res.needs_review is True
