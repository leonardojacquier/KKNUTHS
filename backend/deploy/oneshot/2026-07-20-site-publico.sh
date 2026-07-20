#!/usr/bin/env bash
# Publica o site: o uvicorn (landing/manual/folder) escuta só em 127.0.0.1:8014
# — ninguém de fora acessa. Este oneshot instala o Caddy e o coloca na frente
# com HTTPS automático via sslip.io (sem comprar domínio):
#   https://187-127-13-220.sslip.io  ->  127.0.0.1:8014
# Fallback sem Caddy: um segundo uvicorn público na porta 80 (http simples).
# Resultado (URL final) vai pro bot_events como diag.
set -uo pipefail
cd /opt/poker-bot || exit 1

IP=$(curl -s --max-time 8 https://api.ipify.org || hostname -I | awk '{print $1}')
HOST=$(echo "$IP" | tr '.' '-').sslip.io
OK=""

if ! command -v caddy >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq >/dev/null 2>&1 || true
    apt-get install -y -qq caddy >/dev/null 2>&1 || true
fi

if command -v caddy >/dev/null 2>&1; then
    cat > /etc/caddy/Caddyfile <<EOF
$HOST {
    reverse_proxy 127.0.0.1:8014
}
http://$IP {
    reverse_proxy 127.0.0.1:8014
}
EOF
    systemctl enable caddy >/dev/null 2>&1 || true
    systemctl restart caddy >/dev/null 2>&1 && OK="caddy"
fi

if [ -z "$OK" ]; then
    # fallback: uvicorn público na 80 (http) via pm2
    pm2 delete web-public >/dev/null 2>&1 || true
    pm2 start ./venv/bin/python --name web-public --interpreter none -- \
        -m uvicorn app.api.main:app --host 0.0.0.0 --port 80 \
        >/dev/null 2>&1 && OK="uvicorn80"
    pm2 save >/dev/null 2>&1 || true
fi

sleep 3
CODE_HTTPS=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 12 "https://$HOST/" || true)
CODE_HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "http://$IP/" || true)

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<PY
from app.db import get_repository

get_repository().log_event(0, None, "diag", {
    "src": "site-publico-v1", "modo": "${OK:-falhou}",
    "url_https": "https://$HOST/", "code_https": "$CODE_HTTPS",
    "url_http": "http://$IP/", "code_http": "$CODE_HTTP",
})
print("site publico: modo=${OK:-falhou} https=$CODE_HTTPS http=$CODE_HTTP")
PY
exit 0
