#!/usr/bin/env bash
# Instala o cron da "lição do dia" (11h BRT) na VPS existente.
set -uo pipefail
APP_DIR=/opt/poker-bot
L="0 14 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/licao_do_dia.py >> /var/log/poker-licaodia.log 2>&1"
( crontab -l 2>/dev/null | grep -v "poker-licaodia\|licao_do_dia" ; echo "$L" ) | crontab -
TG=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' $APP_DIR/.env | cut -d= -f2- | tr -d '"'"'"' \r')
N=$(crontab -l | grep -c "licao_do_dia" || true)
M="[lição do dia] cron instalado ($N linha), roda 11h BRT. Nada sai enquanto você não aprovar: /licoes N ok. Fila vazia = eu te aviso, aluno não recebe nada."
echo "$M"
[ -n "$TG" ] && curl -s -X POST "https://api.telegram.org/bot$TG/sendMessage" \
  -H 'Content-Type: application/json' \
  -d "{\"chat_id\": 6452742024, \"text\": \"$M\"}" > /dev/null || true
exit 0
