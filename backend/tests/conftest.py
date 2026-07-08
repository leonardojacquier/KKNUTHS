"""Isolamento GLOBAL da suite: nenhum teste toca serviço externo.

Sem isto a suite dependia da ORDEM dos módulos: o singleton do repositório
era criado "disabled" por acaso (algum módulo anterior limpava o env). Rodando
um módulo isolado, o singleton nascia com as credenciais reais e os testes
batiam em Supabase/Anthropic de verdade (403 no sandbox, custo em produção).
Aqui cada teste nasce e morre offline, em qualquer ordem.
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.db.repository import get_repository

_SECRET_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "VOYAGE_API_KEY",
    "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "STRIPE_SECRET_KEY",
    "TELEGRAM_BOT_TOKEN", "DATABASE_URL",
]


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    for var in _SECRET_VARS:
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    get_repository.cache_clear()
    from app.quota import reset_memory

    reset_memory()
    yield
    get_settings.cache_clear()
    get_repository.cache_clear()
    reset_memory()
