#!/usr/bin/env bash
# Diagnóstico do relatório v2: o oneshot anterior não deixou rastro e o admin
# reportou "não chegou". Reexecuta os envios CAPTURANDO tudo e reporta o
# desfecho (ok ou o erro exato) no Telegram do admin — nunca mais falha muda.
set -uo pipefail
cd /opt/poker-bot || exit 1

ADMIN=6452742024
BETA=8972465711
LOG=/var/log/poker-relatorio-v2.log
PY="./venv/bin/python"
run() { PYTHONPATH=/opt/poker-bot $PY "$@"; }

{
  echo "===== $(date +%F_%T) diagnóstico relatório v2 ====="
  if [ -f .oneshot-done/2026-07-07-relatorio-v2.sh ]; then
    echo "marcador do oneshot anterior EXISTE (ele terminou com exit 0)"
  else
    echo "marcador do oneshot anterior AUSENTE (nunca terminou ok)"
  fi

  fail=0
  echo "--- envio ao beta ($BETA) ---"
  run scripts/revalidation_report.py "$BETA" --update || { echo "EXIT=$?"; fail=1; }
  echo "--- cópia de admin ($ADMIN) ---"
  run scripts/revalidation_report.py "$BETA" "$ADMIN" --update || { echo "EXIT=$?"; fail=1; }
  echo "===== fim (fail=$fail) ====="
} >>"$LOG" 2>&1

# tira caracteres que quebram o parse_mode Markdown do tg.py
TAIL=$(tail -c 3000 "$LOG" | tr -d '_*`[]')
if [ "${fail:-1}" -eq 0 ]; then
  run scripts/tg.py send "$ADMIN" "✅ Relatório v2 reenviado com sucesso (beta + sua cópia). Log: $TAIL" || true
else
  run scripts/tg.py send "$ADMIN" "⚠️ Relatório v2 AINDA falhou. Log: $TAIL" || true
fi
exit 0
