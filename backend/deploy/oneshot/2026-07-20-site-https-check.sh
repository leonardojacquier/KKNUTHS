#!/usr/bin/env bash
# Re-sonda do HTTPS do site: na publicação o http respondeu 200 mas o https
# via sslip.io deu 000 (certificado ainda emitindo, 443 fechada ou rate-limit
# do Let's Encrypt no dominio compartilhado). Confere com calma e loga tudo.
set -uo pipefail
cd /opt/poker-bot || exit 1

IP=$(curl -s --max-time 8 https://api.ipify.org || hostname -I | awk '{print $1}')
HOST=$(echo "$IP" | tr '.' '-').sslip.io

sleep 20   # margem pra emissão do certificado desde o restart do caddy
CODE=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 20 "https://$HOST/" || true)
P443=$(ss -tlnp 2>/dev/null | grep -c ':443 ' || true)
CADDY_LOG=$(journalctl -u caddy --no-pager -n 12 2>/dev/null | grep -i -m4 \
    "certificate\|error\|obtain" | tail -c 500 || true)

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<PY
from app.db import get_repository

get_repository().log_event(0, None, "diag", {
    "src": "site-https-check", "host": "$HOST", "code_https": "$CODE",
    "porta_443_listen": "$P443", "caddy_log": """$CADDY_LOG"""[:480],
})
print("https-check: $CODE (443 listen=$P443)")
PY
exit 0
