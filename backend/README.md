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
- Parsers **PokerStars, GGPoker, Winamax, PartyPoker e 888poker** (torneio + cash)
  → canônico; **CSV de trackers** (HM/PT) vira mãos-resumo.
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

Recursos de lançamento:
- **Cota gratuita** (`app/quota.py`): 15 análises/mês no free (env `FREE_MONTHLY_ANALYSES`),
  limite de upload 2 MB, máx. 5 mãos coacheadas por torneio. Funciona com banco
  (usage_events) ou em memória (dev). Planos pro/premium (coluna `users.plan`) = ilimitado.
- **Bot não-bloqueante**: pipeline síncrono em `bot/processing.py` roda via
  `asyncio.to_thread` — análises longas não travam os outros usuários.
- **Stats cumulativas**: perfil calculado sobre TODO o histórico do banco (hero de
  cada mão, robusto a nicks diferentes entre salas).
- **História do torneio**: mãos decisivas (all-ins + maiores swings) analisadas
  individualmente e narradas em conjunto pelo Claude.
- **/treino**: drill interativo — um spot real seu, botões Fold/Call/Raise, com
  referência Nash push/fold em stack curto.
- **Push/fold Nash** (`analysis/pushfold.py`): tabela determinística por posição/stack,
  exposta como tool ao Claude.
- **Relatório semanal** (`scripts/weekly_report.py`): resumo + leak da semana via cron.
- **Prompt caching** no coaching e **Haiku** na síntese do /ask (custo controlado).

Adiado (decisão de produto): billing Stripe (código pronto em `app/billing/`, desligado
sem `STRIPE_SECRET_KEY`; `scripts/setup_stripe.py` cria produtos quando for a hora).

## Colocar no ar (checklist)

1. **Chaves no `.env`** — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN` (feito).
2. **Supabase service key** — 2 cliques manuais (a API de management não expõe a
   service_role por segurança): Dashboard → projeto **kknuths-poker** → *Project
   Settings* → *API Keys* → copie a **service_role** para `SUPABASE_SERVICE_KEY`.
   Link direto: https://supabase.com/dashboard/project/htvjviovcfvtpgeloekn/settings/api-keys
   (Sem ela o bot funciona, mas sem memória entre reinícios.)
3. **Rodar o bot (dev)**: `PYTHONPATH=. python3 run_bot.py` (long-polling).
4. **Deploy**: `docker build -t kknuths . && docker run --env-file .env kknuths`
   (Railway/Fly/Render detectam o Dockerfile). Cron do relatório semanal:
   `0 18 * * 0 PYTHONPATH=/app python3 scripts/weekly_report.py`.
5. **Depois do beta**: rotacionar as chaves (foram trocadas por chat) e, quando for
   cobrar, `scripts/setup_stripe.py`.
