#!/usr/bin/env bash
# O dono apontou o DNS de poker.vortex369.com.br (resolve pra
# 187.127.13.220). Confere a cadeia inteira DE DENTRO da VPS e diz
# exatamente o que falta. REGRA: este script NÃO altera o Caddy — a VPS é
# multi-tenant e configuração global é do dono; no máximo entrega o
# comando pronto pra ele colar.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
ADMIN_TOKEN=$(grep -m1 '^ADMIN_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
PORTA=$(grep -m1 '^PORT=' .env | cut -d= -f2- | tr -d '"'"'"' \r'); PORTA=${PORTA:-8014}
HOST=poker.vortex369.com.br

diga() {
  echo "$1"
  [ -n "$TG_TOKEN" ] && curl -s -X POST \
    "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -H 'Content-Type: application/json' \
    -d "$(printf '{"chat_id": 6452742024, "text": %s, "disable_web_page_preview": true}' \
          "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")")" \
    > /dev/null || true
}

MEU_IP=$(curl -s --max-time 10 https://api.ipify.org || echo "?")
DNS_IP=$(getent hosts $HOST | awk '{print $1}' | head -1)
LOCAL=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  "http://127.0.0.1:$PORTA/admin?key=$ADMIN_TOKEN" || echo "000")
PUBLICO=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 \
  "https://$HOST/admin?key=$ADMIN_TOKEN" || echo "000")
NO_CADDY="não"
grep -Rqs "poker.vortex369" /etc/caddy/ 2>/dev/null && NO_CADDY="sim"

M="[portal — checagem da cadeia]
DNS: $HOST -> ${DNS_IP:-não resolve}
IP desta VPS: $MEU_IP
Serviço local (:$PORTA): HTTP $LOCAL
Hostname no Caddy: $NO_CADDY
Público (https): HTTP $PUBLICO"

if [ "$PUBLICO" = "200" ]; then
  M="$M

✅ TUDO DE PÉ. Seu portal:
https://$HOST/admin?key=$ADMIN_TOKEN"
elif [ "$DNS_IP" != "$MEU_IP" ]; then
  M="$M

⚠️ O DNS aponta pra $DNS_IP mas esta VPS é $MEU_IP — o registro está indo pro servidor errado. Corrige o A record pra $MEU_IP."
elif [ "$NO_CADDY" = "não" ]; then
  M="$M

Falta só a entrada no Caddy. Cola isto na VPS (eu não mexo no Caddy — é global):

echo '
poker.vortex369.com.br {
    reverse_proxy 127.0.0.1:$PORTA
}' | sudo tee -a /etc/caddy/Caddyfile > /dev/null && sudo systemctl reload caddy

Aí me manda qualquer coisa que eu confiro de novo."
else
  M="$M

Caddy conhece o hostname mas o público não respondeu 200 — provável certificado ainda emitindo (dá uns minutos) ou porta 443 filtrada. Enquanto isso: http://$MEU_IP:$PORTA/admin?key=$ADMIN_TOKEN"
fi
diga "$M"
exit 0
