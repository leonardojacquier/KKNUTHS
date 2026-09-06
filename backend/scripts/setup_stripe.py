"""Setup único do Stripe: cria produtos e preços dos planos e imprime os IDs.

O Stripe não tem como ser criado "de fora" — a conta é sua (https://dashboard.stripe.com,
criar conta leva ~2 min). Depois disso, este script automatiza todo o resto:

  1. Crie a conta Stripe e copie a Secret key (modo TEST primeiro: sk_test_...).
  2. Coloque em STRIPE_SECRET_KEY no .env.
  3. Rode:  PYTHONPATH=. python3 scripts/setup_stripe.py
  4. Copie os price IDs impressos para STRIPE_PRICE_PRO / STRIPE_PRICE_PREMIUM no .env.
  5. No dashboard, crie o webhook endpoint -> {PUBLIC_BASE_URL}/stripe/webhook e copie
     o signing secret (whsec_...) para STRIPE_WEBHOOK_SECRET.

Idempotente: se os produtos já existem (por nome), reaproveita e só garante os preços.
"""
from __future__ import annotations

import sys

from app.config import get_settings

PLANS = [
    {
        "name": "Poker Analyzer Pro",
        "lookup_key": "poker_pro_monthly",
        "amount_brl": 4900,      # R$ 49,00
        "env_var": "STRIPE_PRICE_PRO",
    },
    {
        "name": "Poker Analyzer Premium",
        "lookup_key": "poker_premium_monthly",
        "amount_brl": 12900,     # R$ 129,00
        "env_var": "STRIPE_PRICE_PREMIUM",
    },
]


def main() -> int:
    s = get_settings()
    if not s.stripe_secret_key:
        print("ERRO: defina STRIPE_SECRET_KEY no .env antes de rodar.")
        return 1

    import stripe

    stripe.api_key = s.stripe_secret_key
    mode = "TEST" if s.stripe_secret_key.startswith("sk_test") else "LIVE"
    print(f"Conectado ao Stripe em modo {mode}.\n")

    for plan in PLANS:
        # produto (reaproveita se já existe pelo nome)
        products = stripe.Product.search(query=f"name:'{plan['name']}'")
        product = products.data[0] if products.data else stripe.Product.create(
            name=plan["name"]
        )

        # preço mensal em BRL (reaproveita pelo lookup_key)
        prices = stripe.Price.list(lookup_keys=[plan["lookup_key"]], limit=1)
        price = prices.data[0] if prices.data else stripe.Price.create(
            product=product.id,
            unit_amount=plan["amount_brl"],
            currency="brl",
            recurring={"interval": "month"},
            lookup_key=plan["lookup_key"],
        )
        print(f"{plan['name']}")
        print(f"  product: {product.id}")
        print(f"  {plan['env_var']}={price.id}\n")

    print("Copie os price IDs acima para o .env e configure o webhook no dashboard:")
    print(f"  endpoint: {s.public_base_url}/stripe/webhook")
    print("  eventos: checkout.session.completed, customer.subscription.updated,")
    print("           customer.subscription.deleted, invoice.paid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
