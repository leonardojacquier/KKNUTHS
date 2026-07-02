# Poker Hand Analyzer — Backend

Backend do SaaS de análise de pôquer via Telegram. Veja o plano completo em [`../PLANO.md`](../PLANO.md).

## Estrutura

```
backend/
  app/
    config.py          # settings via env
    models/
      canonical.py     # formato canônico de mão (Pydantic) — tudo converge p/ cá
    parsers/
      base.py          # interface de parser + detecção
      pokerstars.py    # parser determinístico PokerStars (.txt)
      registry.py      # roteia o input para o parser certo
    analysis/
      cards.py         # utilidades de cartas
      equity.py        # equity (treys / Monte Carlo)
      tools.py         # pot odds, EV, SPR — funções puras (tools do agente)
    bot/
      handlers.py      # handlers do Telegram (/start, upload)
    api/
      main.py          # FastAPI (webhook + health)
    db/
      schema.sql       # schema Postgres + pgvector
  tests/               # pytest (parser + math, sem dependências externas)
```

## Rodar

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha as chaves

# testes (parser + math não precisam de chaves)
pytest -q

# API + bot (precisa de TELEGRAM_BOT_TOKEN)
uvicorn app.api.main:app --reload
```

## Estado atual

Implementado e testável **sem chaves** (26 testes):
- Formato canônico de mão (validação Pydantic).
- Parsers **PokerStars** e **GGPoker** (torneio + cash) → canônico, com corpo compartilhado.
- Ferramentas de análise: pot odds, EV, SPR, blefe; equity Monte Carlo (interno + `treys`).
- Agente determinístico: reconstrução de pote, spots, relatório de torneio, stats de estilo.
- Degradação graciosa: sem chave o coaching cai no resumo determinístico; sem Supabase o
  repositório vira no-op.

Conectado, ativa com credenciais:
- **Claude** (`app/agent/llm.py`): coaching em linguagem natural com *tool use* — o LLM
  chama equity/pot-odds/EV/SPR e nunca inventa número. Define `ANTHROPIC_API_KEY`.
- **Visão** (`extract_from_image`): prints/PDF-imagem → snapshot canônico (confidence < 1.0).
- **Supabase** (`app/db/repository.py`): usuários, uploads, mãos, análise, stats, RAG.
  Aplique `app/db/schema.sql` e defina `SUPABASE_URL`/`SUPABASE_SERVICE_KEY`.
- **Embeddings / RAG** (`app/agent/embeddings.py`): Voyage ou OpenAI; popula o vetor de
  `hand_analysis` e habilita `/ask` (busca semântica na base de conhecimento).
- **Billing Stripe** (`app/billing/stripe_service.py`): `/assinar` gera Checkout; webhook
  em `POST /stripe/webhook` libera/atualiza plano. Defina `STRIPE_*`.
- **Bot Telegram** (`/start`, `/stats`, `/ask`, `/plano`, `/assinar`, upload): "recebido → analisando".

A conectar:
- Fila de jobs (RQ) para processamento assíncrono de arquivos grandes.
- Painel web (read-only) com gráficos do histórico.

## Colocar no ar (checklist)

1. **Claude / OpenAI / Telegram** — chaves no `.env` (`ANTHROPIC_API_KEY`,
   `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`).
2. **Supabase service key** — a única que precisa de 2 cliques manuais (o MCP/API de
   management não expõe a service_role por segurança):
   Dashboard → projeto **kknuths-poker** → *Project Settings* → *API Keys* →
   copie a **service_role** para `SUPABASE_SERVICE_KEY`.
   Link direto: https://supabase.com/dashboard/project/htvjviovcfvtpgeloekn/settings/api-keys
3. **Stripe** — crie a conta em https://dashboard.stripe.com (~2 min), copie a
   *Secret key* (`sk_test_...` primeiro) para `STRIPE_SECRET_KEY` e rode:
   `PYTHONPATH=. python3 scripts/setup_stripe.py`
   O script cria os produtos/preços (Pro R$49, Premium R$129) e imprime os
   `STRIPE_PRICE_*`. Depois configure o webhook no dashboard →
   `{PUBLIC_BASE_URL}/stripe/webhook` e copie o `whsec_...`.
4. **Rodar o bot (dev)**: `PYTHONPATH=. python3 run_bot.py` (long-polling).
   Produção: `uvicorn app.api.main:app` atrás de HTTPS + webhook do Telegram.
