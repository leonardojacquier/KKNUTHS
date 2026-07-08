---
tags: [kknuths, tecnica]
---
# Arquitetura Técnica

Python/FastAPI + python-telegram-bot (polling). Handlers async finos;
trabalho pesado em `processing.py` síncrono via `asyncio.to_thread`.

## Pipeline de upload
ingest (detecção de formato/parsers) → modelo canônico (Pydantic:
CanonicalHand com streets, actions, shown_cards, uncalled, net_won) →
`analyze_hand` determinístico (pot, spots, stacks em BB, **stack efetivo**) →
stats cumulativas + snapshot de evolução → coach LLM com 18 tools →
quadro do torneio → relatório mão a mão → embeddings p/ /ask.

## Princípio central
O LLM **julga**, não calcula: todo número vem de motor determinístico ou de
tool. Regra de prompt: nunca estimar stack (bug histórico "12bb vs 58bb").

## Módulos-chave (backend/app/)
- parsers/: pokerstars.py (parse_body compartilhado), ggpoker, winamax, csv…
- analysis/: bayes, leaks, mental, rangetracker, calibration, handreport,
  handsearch, tournament_board, evolution_chart, style_chart, range_chart,
  pushfold (Nash), equity (MC + avaliador 7 cartas), branding
- agent/: analyzer (determinístico), llm (tools + prompt), embeddings, speech
- bot/: handlers, processing
- api/: landing, manual_page, folder_page, admin (portal)

Paste reassembly: PENDING_PASTE com TTL 900s, algoritmo de emenda validado
contra corrupção no meio de linha.
