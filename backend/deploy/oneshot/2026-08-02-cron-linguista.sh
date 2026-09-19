#!/usr/bin/env bash
# Instala o cron do linguista na VPS já existente (o vps_deploy.sh só roda
# na instalação inicial; cron novo não chega sozinho pelo auto_update).
set -uo pipefail
APP_DIR=/opt/poker-bot

LINHA="40 7 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/linguista.py >> /var/log/poker-linguista.log 2>&1"
( crontab -l 2>/dev/null | grep -v "poker-linguista\|linguista.py" ; echo "$LINHA" ) | crontab -

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' $APP_DIR/.env | cut -d= -f2- | tr -d '"'"'"' \r')
INSTALADO=$(crontab -l | grep -c "linguista.py" || true)
MSG="[linguista] cron instalado ($INSTALADO linha). Roda 7h40 UTC, propostas chegam antes do juiz das 8h. Aprovação: /termo"
echo "$MSG"
if [ -n "$TG_TOKEN" ]; then
  curl -s -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -H 'Content-Type: application/json' \
    -d "{\"chat_id\": 6452742024, \"text\": \"$MSG\"}" > /dev/null || true
fi
exit 0
