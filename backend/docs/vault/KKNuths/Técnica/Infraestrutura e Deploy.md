---
tags: [kknuths, tecnica, operacao]
---
# Infraestrutura e Deploy

- VPS GNH: app em `/opt/poker-bot`, pm2 (`poker-bot` = bot, `poker-web` =
  portal :8014 atrás do Caddy → vorte369.com.br)
- **Deploy automático**: cron 2min roda `deploy/auto_update.sh` (rsync
  --delete com excludes: .env, venv, .git, .oneshot-done, calibration.json)
  → `deploy/vps_deploy.sh` (pytest como GATE; falhou = não sobe) → pm2 restart
- Notificações de deploy no Telegram do admin (🔄 ok / ⚠️ falha via ERR trap)
- **Versão no ar auditável**: `scripts/log_deploy.py` (hook no vps_deploy)
  grava o hash do clone do GitHub (`/opt/kknuths`, NÃO o git-snapshot
  local) em `bot_events` (event `deploy`, telegram_id 0) — "não subiu o
  ajuste" se responde com SQL, sem adivinhação
- **One-shots**: `deploy/oneshot/*.sh` rodam UMA vez (marcador em
  .oneshot-done/); falha = retenta no próximo deploy. É o braço p/ executar
  qualquer coisa no VPS (broadcasts, reprocessos, reenvios)
- Crons (instalados por `vps_deploy.sh`, horários UTC):
  | hora | cron | o quê |
  |---|---|---|
  | dom 18h | weekly_report | resumo semanal |
  | 19h | daily_quiz | quiz diário |
  | seg 5h | calibrate_likelihood | calibração por showdown |
  | 6h | nightly_coherence | coerência gráfico↔texto |
  | **7h** | **jornadas** | sonda de entrega ([[Guarda da Saída]]) |
  | 7h30 | e2e_probe | **nunca rodou** — falta a conta-teste |
  | 8h | output_judge | juiz da saída (nota de clareza) |
  | 23h | daily_usage | resumo de uso + **custo do dia** |
  | **4h** | **backup_db** | dump JSON.gz, 14 dias, avisa se falhar |
- `jornadas` também roda 20s após cada deploy: pega release que quebrou a
  entrega antes do aluno perceber
- **Backup**: o histórico do aluno é o ativo e vivia sem cópia.
  `scripts/backup_db.py` pagina 1000/página, descarta a coluna de embedding
  (1536 floats), alerta o admin se falhar ou se `hands` vier vazia;
  `--restaurar` só faz upsert do que falta. Dumps ficam no VPS —
  `backups/` está no .gitignore, mão de aluno **nunca** vai para o repo
- Flags .env: `BAYES_STATS`, `REPORT_AUTO`, `FREE_MONTHLY_ANALYSES`,
  `PILOTO_MONTHLY_ANALYSES`, `ADMIN_TELEGRAM_ID` (ver [[Runbook de Operação]])
