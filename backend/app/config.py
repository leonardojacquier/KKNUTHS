"""Configuração central via variáveis de ambiente."""
from __future__ import annotations

import os
from functools import lru_cache

try:  # dotenv é conveniência de dev; ausência não deve quebrar runtime/testes
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class Settings:
    """Settings lidos do ambiente na instanciação (não no import), para que
    get_settings.cache_clear() reflita mudanças de env — essencial em testes."""

    def __init__(self) -> None:
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.analysis_model: str = os.getenv("ANALYSIS_MODEL", "claude-opus-4-8")
        self.cheap_model: str = os.getenv("CHEAP_MODEL", "claude-haiku-4-5-20251001")

        # Embeddings (Anthropic não tem; Voyage ou OpenAI). Dim casa com vector(N).
        self.voyage_api_key: str = os.getenv("VOYAGE_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))

        self.supabase_url: str = os.getenv("SUPABASE_URL", "")
        self.supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
        self.database_url: str = os.getenv("DATABASE_URL", "")

        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        self.stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
        self.stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.stripe_price_pro: str = os.getenv("STRIPE_PRICE_PRO", "")
        self.stripe_price_premium: str = os.getenv("STRIPE_PRICE_PREMIUM", "")

        self.public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
        self.default_lang: str = os.getenv("DEFAULT_LANG", "pt")


@lru_cache
def get_settings() -> Settings:
    return Settings()
