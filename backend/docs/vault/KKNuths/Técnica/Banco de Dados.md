---
tags: [kknuths, tecnica]
---
# Banco de Dados (Supabase/Postgres + pgvector)

| Tabela | Conteúdo |
|---|---|
| users | telegram_id, username, plano |
| hands | canônico JSONB; upsert por (user_id, site, hand_id) — reenvio não duplica |
| hand_analysis | análise + embedding (RAG do /ask) |
| player_stats | perfil cumulativo |
| player_stats_history | snapshots p/ /evolucao |
| player_notes | caderno do coach (leak/progresso/meta/estilo) |
| uploads | linhagem dos arquivos (bucket) |
| bot_events | telemetria: TODA interação, erros, followup (logado ANTES do LLM), simplify, relatorio… |
| usage_events | cota (fail-closed com flag degraded + guarda de concorrência) |
| conversation_state | contexto da conversa viva (é o que a sonda de jornadas percorre) |
| user_meta | 0 linhas — lugar natural do estado de promoção ([[Pricing e Planos]]) |
| subscriptions | 0 linhas — `stripe_customer`/`stripe_sub_id`, billing desligado |

15 tabelas no total. RLS ativo. Regra: dados individuais nunca
compartilhados; agregado anônimo calibra o motor (dito no FAQ do manual).

## `bot_events.detail` é jsonb — telemetria nova não pede migração
Foi por isso que o custo por chamada entrou sem tocar em schema
([[Custo de LLM]]). Eventos que valem SQL estão listados no
[[Runbook de Operação]].

## Backup
`scripts/backup_db.py` (cron 4h): dump JSON.gz de todas as tabelas, 14 dias,
sem a coluna de embedding. Fica **no VPS** — `backups/` no .gitignore.
Cuidado registrado: o `.gitignore` chegou a ter `*.json.gz` genérico, que
teria ignorado o `preflop_equity.json.gz` versionado; hoje o padrão é
escopado a `backups/`.
