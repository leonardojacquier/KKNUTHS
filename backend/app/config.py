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
    """Settings lidos do ambiente. Mantido simples e sem dependência de rede."""

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    analysis_model: str = os.getenv("ANALYSIS_MODEL", "claude-opus-4-8")
    cheap_model: str = os.getenv("CHEAP_MODEL", "claude-haiku-4-5-20251001")

    # Embeddings (Anthropic não tem embeddings; usamos Voyage — recomendado pela
    # Anthropic — ou OpenAI). Dim deve casar com vector(N) no schema.
    voyage_api_key: str = os.getenv("VOYAGE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "voyage-large-2")  # 1536 dims
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))

    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "")

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_pro: str = os.getenv("STRIPE_PRICE_PRO", "")
    stripe_price_premium: str = os.getenv("STRIPE_PRICE_PREMIUM", "")

    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    default_lang: str = os.getenv("DEFAULT_LANG", "pt")


@lru_cache
def get_settings() -> Settings:
    return Settings()
