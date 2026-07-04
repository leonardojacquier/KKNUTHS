"""FastAPI: health, webhook do Telegram e webhook do Stripe (esqueleto)."""
from __future__ import annotations

from fastapi import FastAPI, Request

from app.api.admin import router as admin_router
from app.config import get_settings

app = FastAPI(title="Poker Hand Analyzer API")
app.include_router(admin_router)


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

    Valida a assinatura (STRIPE_WEBHOOK_SECRET) e libera/atualiza o plano do usuário.
    """
    from fastapi import HTTPException

    from app.billing import handle_webhook

    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        return handle_webhook(payload, sig)
    except Exception as exc:  # assinatura inválida / payload malformado
        # não-2xx: o Stripe reenvia eventos legítimos que falharam; 200 com
        # {"error"} marcaria como entregue e o evento se perderia
        raise HTTPException(status_code=400, detail=str(exc))
