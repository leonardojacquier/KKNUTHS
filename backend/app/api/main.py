"""FastAPI: health, webhook do Telegram e webhook do Stripe (esqueleto)."""
from __future__ import annotations

from fastapi import FastAPI, Request

from app.config import get_settings

app = FastAPI(title="Poker Hand Analyzer API")


@app.get("/health")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "telegram_configured": bool(s.telegram_bot_token),
        "llm_configured": bool(s.anthropic_api_key),
        "db_configured": bool(s.database_url or s.supabase_url),
    }


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Recebe updates do Telegram (modo webhook em produção).

    Em produção: enfileira o update e processa em worker. Aqui apenas valida
    que a aplicação está montada.
    """
    from telegram import Update

    from app.bot.handlers import build_application

    application = build_application()
    data = await request.json()
    update = Update.de_json(data, application.bot)
    async with application:
        await application.process_update(update)
    return {"ok": True}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Recebe eventos do Stripe (checkout.session.completed, subscription.*, invoice.paid).

    Aqui é onde o plano do usuário é liberado/atualizado e os créditos creditados.
    Verificação de assinatura via STRIPE_WEBHOOK_SECRET entra antes de processar.
    """
    payload = await request.body()
    _ = payload  # validar assinatura + despachar por event.type (a implementar)
    return {"received": True}
