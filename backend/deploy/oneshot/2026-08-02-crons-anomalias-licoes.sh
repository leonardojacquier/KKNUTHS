#!/usr/bin/env bash
# Instala os crons novos (anomalias 21h, lições 9h15) na VPS existente e
# roda o BACKFILL das lições: as ~40 análises mais caras que já existem no
# banco viram as primeiras lições da biblioteca — o estoque começa cheio.
set -uo pipefail
APP_DIR=/opt/poker-bot

L1="0 21 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/anomalias.py >> /var/log/poker-anomalias.log 2>&1"
L2="15 9 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/destilar_licoes.py >> /var/log/poker-licoes.log 2>&1"
( crontab -l 2>/dev/null | grep -v "poker-anomalias\|anomalias.py\|poker-licoes\|destilar_licoes" ; \
  echo "$L1" ; echo "$L2" ) | crontab -

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' $APP_DIR/.env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

# backfill: destila o histórico (janela de 60 dias, teto de candidatas do
# script) — custo Haiku baixo e limitado
cd $APP_DIR || exit 1
SAIDA=$(PYTHONPATH=$APP_DIR ./venv/bin/python - <<'PY'
from datetime import datetime, timedelta, timezone

from app.db import get_repository
from scripts.destilar_licoes import candidatas, destilar

repo = get_repository()
desde = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
novas = 0
for analise in candidatas(repo, desde, limite=40):
    licao = destilar(analise)
    if not licao:
        continue
    try:
        repo.client.table("licoes").insert(
            {**licao, "hand_analysis_id": analise["id"]}).execute()
        novas += 1
    except Exception:
        pass
repo.log_event(0, "licoes", "licoes_destiladas", {"novas": novas,
                                                  "backfill": True})
print(novas)
PY
)
N=$(crontab -l | grep -c "anomalias.py\|destilar_licoes" || true)
MSG="[sensores] crons instalados ($N linhas). Backfill: $SAIDA lição(ões) na biblioteca — veja com /licoes. Anomalias avisam às 18h BRT quando houver."
echo "$MSG"
if [ -n "$TG_TOKEN" ]; then
  curl -s -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -H 'Content-Type: application/json' \
    -d "{\"chat_id\": 6452742024, \"text\": \"$MSG\"}" > /dev/null || true
fi
exit 0
