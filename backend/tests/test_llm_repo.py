"""Testes das frentes Claude + persistência, no caminho offline.

Herméticos: limpam as variáveis de ambiente e os caches de settings/repositório,
então passam igualmente com ou sem chaves reais no .env. Garantem a degradação
graciosa: sem ANTHROPIC_API_KEY o coaching cai no resumo determinístico; sem
Supabase o repositório vira no-op.
"""
import math
from pathlib import Path

import pytest

from app.agent import analyze_hand
from app.agent.llm import _dispatch, coach
from app.config import get_settings
from app.db.repository import Repository
from app.ingestion import ingest
from app.parsers import parse_text

PS = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"

_SECRET_VARS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "VOYAGE_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "STRIPE_SECRET_KEY",
    "TELEGRAM_BOT_TOKEN",
]


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    """Remove todas as credenciais do ambiente e limpa o cache de settings."""
    for var in _SECRET_VARS:
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()  # não vazar settings "offline" para outros testes


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
    repo = Repository()  # instância fresca, sem o cache de get_repository
    assert repo.enabled is False
    assert repo.get_or_create_user(123, "x") is None
    assert repo.save_hand("u", parse_text(PS.read_text())[0]) is None
    assert repo.search_analysis("u", [0.0] * 1536) == []


def test_image_ingest_needs_review_without_vision():
    res = ingest(b"\x89PNG fake bytes", "png")
    assert res.hands == []
    assert res.needs_review is True
