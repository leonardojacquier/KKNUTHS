"""FastAPI: health, webhook do Telegram e webhook do Stripe (esqueleto)."""
from __future__ import annotations

from fastapi import FastAPI, Request

from app.api.admin import router as admin_router
from app.api.landing import router as landing_router
from app.config import get_settings

app = FastAPI(title="Poker Hand Analyzer API")
app.include_router(admin_router)
app.include_router(landing_router)


@app.get("/health")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "telegram_configured": bool(s.telegram_bot_token),
        "llm_configured": bool(s.anthropic_api_key),
        "db_configured": bool(s.database_url or s.supabase_url),
    }


# REMOVIDO: POST /telegram/webhook (auditoria de 07/08).
#
# A rota fazia Update.de_json(body) + process_update SEM validar nada — nem
# o X-Telegram-Bot-Api-Secret-Token, nem origem. Como TODA autorização de
# admin do bot é `tg_id != ADMIN_TELEGRAM_ID` e esse tg_id sai do corpo da
# requisição, qualquer POST anônimo forjava a identidade do dono: dar-se
# `/planode premium`, ler `/quem`, e disparar process_upload na conta de
# qualquer aluno (queimando cota e crédito da Anthropic). O ID default ainda
# por cima está no código (app/quota.py:18).
#
# E a rota era CÓDIGO MORTO: o bot roda run_polling() (handlers.py:1919),
# nunca webhook. Era superfície de ataque pura, servida no mesmo app que o
# portal em poker.vortex369.com.br.
#
# Se um dia o modo webhook for necessário, ele volta com secret_token
# definido no setWebhook e conferido aqui com secrets.compare_digest — não
# assim. (O /stripe/webhook abaixo faz o certo: valida a assinatura.)


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
