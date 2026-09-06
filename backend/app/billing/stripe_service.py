"""Cobrança via Stripe (assinatura + créditos).

Fluxo:
  1. Bot pede /assinar -> create_checkout_session() gera link do Stripe Checkout.
  2. Usuário paga -> Stripe chama nosso webhook (POST /stripe/webhook).
  3. handle_webhook() valida a assinatura e libera/atualiza o plano no banco.

Sem STRIPE_SECRET_KEY o billing fica desabilitado (is_enabled()==False); o bot
informa que a cobrança ainda não está configurada, sem quebrar.
"""
from __future__ import annotations

import logging

from app.config import get_settings
from app.db import get_repository

log = logging.getLogger("billing")


def _prices() -> dict[str, str]:
    s = get_settings()
    return {"pro": s.stripe_price_pro, "premium": s.stripe_price_premium}


# exposto para validação de plano nas camadas acima
PLAN_PRICES = _prices


def is_enabled() -> bool:
    return bool(get_settings().stripe_secret_key)


def _client():
    import stripe  # lazy import

    stripe.api_key = get_settings().stripe_secret_key
    return stripe


def create_checkout_session(user_id: str, plan: str) -> str | None:
    """Cria uma sessão de Checkout e retorna a URL de pagamento. None se indisponível."""
    if not is_enabled():
        return None
    prices = _prices()
    price_id = prices.get(plan)
    if not price_id:
        log.warning("plano sem price configurado: %s", plan)
        return None

    s = get_settings()
    stripe = _client()
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=user_id,        # liga o pagamento ao nosso usuário
        metadata={"plan": plan, "user_id": user_id},
        success_url=f"{s.public_base_url}/billing/success",
        cancel_url=f"{s.public_base_url}/billing/cancel",
        allow_promotion_codes=True,
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str | None) -> dict:
    """Valida e processa um evento do Stripe. Atualiza plano/assinatura no banco."""
    s = get_settings()
    if not is_enabled():
        return {"ignored": "billing desabilitado"}

    # assinatura é OBRIGATÓRIA: sem ela, qualquer POST na internet viraria
    # "me dá premium" — um secret esquecido no .env não pode abrir essa porta
    if not s.stripe_webhook_secret:
        raise ValueError(
            "STRIPE_WEBHOOK_SECRET não configurado — webhook rejeitado por segurança"
        )
    if not sig_header:
        raise ValueError("cabeçalho stripe-signature ausente — evento rejeitado")
    stripe = _client()
    event = stripe.Webhook.construct_event(payload, sig_header, s.stripe_webhook_secret)

    etype = event["type"]
    obj = event["data"]["object"]
    repo = get_repository()

    if etype == "checkout.session.completed":
        user_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id")
        plan = (obj.get("metadata") or {}).get("plan", "pro")
        if user_id:
            repo.update_user_plan(user_id, plan)
            repo.upsert_subscription(
                {
                    "user_id": user_id,
                    "stripe_customer": obj.get("customer"),
                    "stripe_sub_id": obj.get("subscription"),
                    "plan": plan,
                    "status": "active",
                    "period_end": None,
                }
            )
        return {"handled": etype, "user_id": user_id, "plan": plan}

    if etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        status = obj.get("status", "canceled")
        plan = (obj.get("metadata") or {}).get("plan", "pro")
        period_end = obj.get("current_period_end")
        active = status in ("active", "trialing")
        # Reflete no banco. (Mapeamento customer->user_id pode vir da tabela de subs.)
        repo.upsert_subscription(
            {
                "user_id": (obj.get("metadata") or {}).get("user_id"),
                "stripe_customer": obj.get("customer"),
                "stripe_sub_id": obj.get("id"),
                "plan": plan if active else "free",
                "status": status,
                "period_end": period_end,
            }
        )
        return {"handled": etype, "status": status}

    if etype == "invoice.paid":
        return {"handled": etype}

    return {"ignored": etype}
