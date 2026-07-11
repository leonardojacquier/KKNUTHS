---
tags: [kknuths, operacao]
---
# Runbook de Operação

## Executar algo no VPS
Criar `deploy/oneshot/AAAA-MM-DD-nome.sh` (idempotente, `set -uo pipefail`,
`cd /opt/poker-bot`), commit + push → roda no próximo deploy (~2min). Falhou →
retenta no próximo. Instrumentar: capturar log e reportar no Telegram do admin.

## Scripts prontos (scripts/)
- revalidation_report.py <tg> [dest] [--update] — relatório mão a mão
- send_stats_preview.py <dono> <dest> — prévia do /stats p/ admin
- send_board.py <dono> [dest] — quadro do torneio
- test_drive.py <arquivo> <tg> — pipeline completo numa conta
- reprocess_uploads.py <tg> — re-parseia uploads (best-version-wins)
- calibrate_likelihood.py — calibração (também no cron)
- set_bot_identity.py — descrição do bot via API
- gen_demo_tournament.py [seed] [n] — torneio demo
- tg.py / tg_send_doc.py — Telegram do VPS (token do .env local)

## Flags (.env do VPS)
- `BAYES_STATS=0` — desliga shrinkage (rollback de emergência)
- `REPORT_AUTO=0` — relatório só via /relatorio

## Diagnóstico via bot_events (SQL, sem SSH)
- `event='deploy'` (tg 0): hash/mensagem do commit NO AR
- `event='upload_failed'`: note traz a CAUSA real da visão (exceção)
- `event='chart_failed'`: gráfico prometido que não renderizou (spec)
- `event='diag'`: oneshot de diagnóstico despeja tail de log no banco
  (padrão: 2026-07-09-diagnostico-print-v2.sh)

## Sintomas conhecidos
- Deploy sem 🔄/⚠️ → ver ERR trap / STATE file do auto_update
- MCP Supabase instável na sandbox → retry ou rotear via oneshot
- Botões novos só aparecem em MENSAGENS NOVAS (Telegram não edita antigas)
- `temperature is deprecated for this model` (400) → wrapper `_create`
  já refaz sem o parâmetro e memoriza (`_NO_TEMP`); NÃO passar
  temperature direto em `client.messages.create` novo
- Excerpt binário em log_event derrubava o INSERT (NUL byte, 22P05) →
  `_scrub_nul` no repositório; binário vira '<fmt binário, N bytes>'
