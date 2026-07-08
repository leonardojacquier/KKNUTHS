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

RLS ativo. Regra: dados individuais nunca compartilhados; agregado anônimo
calibra o motor (dito no FAQ do manual).
