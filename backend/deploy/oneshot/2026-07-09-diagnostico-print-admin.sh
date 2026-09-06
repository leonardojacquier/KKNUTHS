#!/usr/bin/env bash
# Diagnóstico: retest do admin (print de mão) não gerou NENHUM evento em
# bot_events depois de 10:27 UTC — nem upload, nem upload_failed. Captura o
# log do processo para ver se o handler quebrou e reporta ao admin.
set -uo pipefail
cd /opt/poker-bot || exit 1

ADMIN=6452742024
LOG=/var/log/poker-diagnostico-print.log

{
    echo "== pm2 status =="
    pm2 jlist 2>/dev/null | ./venv/bin/python -c "
import json,sys
for p in json.load(sys.stdin):
    if p['name'] in ('poker-bot','poker-web'):
        e = p.get('pm2_env', {})
        print(p['name'], e.get('status'), 'restarts=', e.get('restart_time'))
" 2>&1
    echo
    echo "== últimas 120 linhas de erro do poker-bot =="
    tail -n 120 "$HOME/.pm2/logs/poker-bot-error.log" 2>/dev/null || \
        tail -n 120 /root/.pm2/logs/poker-bot-error.log 2>/dev/null
    echo
    echo "== últimas 60 linhas de saída do poker-bot =="
    tail -n 60 "$HOME/.pm2/logs/poker-bot-out.log" 2>/dev/null || \
        tail -n 60 /root/.pm2/logs/poker-bot-out.log 2>/dev/null
} > "$LOG" 2>&1

TAIL=$(grep -iE "error|exception|traceback" "$LOG" | tail -n 12)
[ -z "$TAIL" ] && TAIL="(nenhum erro no log — ver $LOG completo no VPS)"

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/tg.py send "$ADMIN" \
"🔧 Diagnóstico do print que 'não leu' — log capturado em $LOG. Últimos erros do processo:

${TAIL:0:2800}" || exit 1
exit 0
