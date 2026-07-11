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
- Crons de produto: resumo semanal (dom 18h), quiz diário (19h), calibração
  (seg 5h)
- Flags .env: `BAYES_STATS`, `REPORT_AUTO` (ver [[Runbook de Operação]])
