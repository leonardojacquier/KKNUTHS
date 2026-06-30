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

## Estado atual (fundação)

Implementado e testável **sem chaves**:
- Formato canônico de mão (validação Pydantic).
- Parser PokerStars (torneio + cash) → canônico.
- Ferramentas de análise: pot odds, EV, SPR, equity (via `treys`).

Plugável / a conectar:
- Bot Telegram (esqueleto com fluxo "recebido → analisando").
- Agente LLM (Claude) + base de conhecimento (Supabase/pgvector).
- Billing (Stripe).
