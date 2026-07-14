#!/usr/bin/env bash
# Make-or-break: o VPS consegue ALCANCAR o endpoint da mao (IP China)? Se nao,
# a busca por HTTP morre e pivotamos. Testa reachability crua (curl -v, ping,
# timeouts longos) + variacoes de host. Resultado enxuto em bot_events.
set -uo pipefail
cd /opt/poker-bot || exit 1

IP="8.210.148.142"
KEY="f48bcbb5-ef29-46d2-3a6c-5d8642064240"
U="http://$IP/poker/api/log_review_hand.php?share_key=$KEY&rand=471_0.97"

{
  echo "== curl 90s =="
  curl -sS -m 90 -A "Mozilla/5.0 (iPhone)" -H "Referer: https://replay.pppoker.net/" \
       -w "\nHTTP=%{http_code} time=%{time_total}s size=%{size_download}\n" "$U" 2>&1 | head -c 2500
  echo; echo "== curl HEAD conexao (10s) =="
  curl -sS -m 10 -o /dev/null -w "connect=%{time_connect} appconnect=%{time_appconnect} HTTP=%{http_code}\n" "$U" 2>&1 | head -c 400
  echo "== tcp 80 =="
  timeout 6 bash -c "echo > /dev/tcp/$IP/80" 2>&1 && echo "porta 80 ABRE" || echo "porta 80 FECHADA/timeout"
} > /tmp/alcance.txt 2>&1

TAIL="$(head -c 3000 /tmp/alcance.txt)"
PYTHONPATH=/opt/poker-bot ./venv/bin/python - "$TAIL" <<'PY'
import sys
from app.db import get_repository
get_repository().log_event(0, "diag", "diag",
                           {"src": "pppoker-alcance", "out": sys.argv[1][:3300]})
print("alcance registrado")
PY
exit 0
