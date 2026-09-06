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
        # @ do bot — o que monta os deep links `t.me/<BOT>?start=...`. Estava
        # escrito à mão em cinco arquivos (landing, manual, branding, figura da
        # mão, rodapé do relatório); aqui ele tem um nome só. Vem do ambiente
        # porque o bot de teste tem outro @, e um deep link com o @ errado é
        # um botão que abre o bot errado — falha muda, no aluno.
        self.telegram_bot_username: str = os.getenv("TELEGRAM_BOT_USERNAME",
                                                    "KKNUts_BOT")

        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        # Sonnet como default desde 15/08: no A/B do juiz, sonnet 7.7 (n=12)
        # vs opus 6.0 (n=13) e ~5x mais barato; a nota do dia (6.3) ficou
        # abaixo da meta de 7 e o combinado com o dono era trocar. Reverter =
        # ANALYSIS_MODEL=claude-opus-4-8 no .env, sem deploy.
        self.analysis_model: str = os.getenv("ANALYSIS_MODEL",
                                             "claude-sonnet-5")
        self.cheap_model: str = os.getenv("CHEAP_MODEL", "claude-haiku-4-5-20251001")
        # RESERVA do titular quando ele degenera: 3x (16/08 2x, 21/08) o
        # sonnet-5 entrou em loop de escrita em mãos de replay PDQ e cortou
        # o teto na análise E no resgate. Repetir o mesmo modelo repete o
        # loop; o opus-4-8 analisou essas mesmas mãos em 300-750 tokens.
        self.analysis_fallback_model: str = os.getenv(
            "ANALYSIS_FALLBACK_MODEL", "claude-opus-4-8")
        # roteamento por complexidade: mão de decisão única pré-flop pode ir
        # num modelo mais barato (ex.: claude-sonnet-5). VAZIO = desligado —
        # só liga depois que o juiz comparar a clareza por modelo.
        self.simple_hand_model: str = os.getenv("SIMPLE_HAND_MODEL", "")

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
        self.admin_token: str = os.getenv("ADMIN_TOKEN", "")

        # flag de rollout do shrinkage bayesiano nas stats (BAYES_STATS=0
        # desliga em produção sem deploy); morre quando estabilizar
        self.bayes_stats: bool = os.getenv("BAYES_STATS", "1") != "0"
        # relatório mão a mão anexado automaticamente no upload de torneio;
        # REPORT_AUTO=0 muda para só sob demanda (/relatorio) — alavanca de
        # plano no futuro (free = sob demanda, Pro = automático)
        self.report_auto: bool = os.getenv("REPORT_AUTO", "1") != "0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
