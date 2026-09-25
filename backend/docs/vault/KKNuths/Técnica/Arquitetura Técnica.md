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
- parsers/: pokerstars.py (parse_body compartilhado), ggpoker, winamax, csv,
  phh, **pppoker_replay**, **suprema_replay** ([[Ingestão de Replays de Clube]])
- analysis/: bayes, leaks, mental, rangetracker, calibration, handreport,
  handsearch, tournament_board, evolution_chart, style_chart, range_chart,
  pushfold (Nash), equity (MC + avaliador 7 cartas), branding,
  **multiway_equity**, **side_pots**, **ev_streets**
  ([[EV Multiway e Potes Paralelos]]), **postflop_spot** (monta o spot do
  solver a partir da mão em conversa, sem interrogar o aluno),
  **procedencia** (o quanto a fonte permite afirmar), **selfcheck** (8
  classes de prova real)
- agent/: analyzer (determinístico), llm (tools + prompt), embeddings,
  speech, **custo** ([[Custo de LLM]])
- bot/: handlers, processing, **guarda_saida** ([[Guarda da Saída]]),
  **notify** (aviso de espera do solver)
- api/: landing, manual_page, folder_page, admin (portal)

## Pontos únicos (choke points) — e por que existem
| ponto | garante |
|---|---|
| `llm._create` | toda chamada ao modelo é contabilizada em dólar |
| `abrir_conversa` | conversa sem mão levanta exceção, não vira bug silencioso |
| `guarda_saida.conferir_e_remediar` | pedido conferido antes de entregar |
Cada um tem canário que varre o diretório atrás de quem passe por fora
([[Testes e Qualidade]]).

Paste reassembly: PENDING_PASTE com TTL 900s, algoritmo de emenda validado
contra corrupção no meio de linha.
