---
tags: [kknuths, operacao]
---
# Runbook de Operação

## Executar algo no VPS
Criar `deploy/oneshot/AAAA-MM-DD-nome.sh` (idempotente, `set -uo pipefail`,
`cd /opt/poker-bot`), commit + push → roda no próximo deploy (~2min). Falhou →
retenta no próximo. Instrumentar: capturar log e reportar no Telegram do admin.

⚠️ **`exit 0` no fim ANULA o retry.** Sem `set -e`, um Python que quebra no
meio não muda o código de saída: o deploy marca a tarefa como concluída, nada
chega no Telegram e ela nunca mais roda. Aconteceu com o oneshot v4 da
PokerCraft — silêncio total, indistinguível de "não rodou".

Regra para oneshot de DIAGNÓSTICO:
- envolver tudo em `try/except` e **mandar o traceback** pelo Telegram: um
  diagnóstico que falha calado é pior que nenhum;
- só biblioteca padrão e token lido do `.env` por `grep` — importar módulo do
  app acrescenta uma classe inteira de falha ao que deveria ser o passo mais
  simples;
- `exit 0` só depois de ter reportado.

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

## ⚠️ `/opt/poker-bot` NÃO é clone do GitHub
`git init` local só para versionar o estado; **não tem remote**. `git pull`
ali sempre falha ("no tracking information"). O código chega por rsync do
`auto_update.sh` (cron de 2 min). Para saber se o commit subiu:
`tail -5 /var/log/poker-autodeploy.log`.

## Investigar um clube de replay novo
```
cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python \
  scripts/sniff_replay.py "<link>" --telegram
```
Detalhes e armadilhas em [[Ingestão de Replays de Clube]]. Se der 0 achados,
o material bruto fica em `/tmp/replay_sniff/` — ler o HTML e `grep` os
bundles resolve mais rápido que outra rodada automática.

## Flags (.env do VPS)
- `BAYES_STATS=0` — desliga shrinkage (rollback de emergência)
- `REPORT_AUTO=0` — relatório só via /relatorio

## Diagnóstico via bot_events (SQL, sem SSH)
- `event='deploy'` (tg 0): hash/mensagem do commit NO AR
- `event='upload_failed'`: note traz a CAUSA real da visão (exceção)
- `event='chart_failed'`: gráfico prometido que não renderizou (spec)
- `event='diag'`: oneshot de diagnóstico despeja tail de log no banco
  (padrão: 2026-07-09-diagnostico-print-v2.sh)
- `event='custo_llm'`: dólar por chamada ([[Custo de LLM]])
- `event='entrega_ok|entrega_falha|entrega_remediada'`: taxa de entrega
- `event='sem_mao_na_conversa'`: caminho de contexto quebrado
- `event='replay_link'` com `chave_ilegivel=true`: link de PPPoker/Suprema
  que o parser não abriu — é BUG, não limite do produto; a url vai junto
- `event='jornadas'`: sonda diária ([[Guarda da Saída]])

## Sintomas conhecidos
- Deploy sem 🔄/⚠️ → ver ERR trap / STATE file do auto_update
- MCP Supabase instável na sandbox → retry ou rotear via oneshot
- Botões novos só aparecem em MENSAGENS NOVAS (Telegram não edita antigas)
- `temperature is deprecated for this model` (400) → wrapper `_create`
  já refaz sem o parâmetro e memoriza (`_NO_TEMP`); NÃO passar
  temperature direto em `client.messages.create` novo
- Excerpt binário em log_event derrubava o INSERT (NUL byte, 22P05) →
  `_scrub_nul` no repositório; binário vira '<fmt binário, N bytes>'
