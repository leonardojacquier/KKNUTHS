#!/usr/bin/env bash
# "E o portal de gestão, onde está?" — testa o /admin de dentro da VPS e
# manda o link PRONTO (com a chave) pro dono no Telegram. A chave viaja só
# do .env da VPS pro chat privado dele — nunca pelo repositório.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
ADMIN_TOKEN=$(grep -m1 '^ADMIN_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
PORTA=$(grep -m1 '^PORT=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
PORTA=${PORTA:-8014}

diga() {
  echo "$1"
  [ -n "$TG_TOKEN" ] && curl -s -X POST \
    "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -H 'Content-Type: application/json' \
    -d "$(printf '{"chat_id": 6452742024, "text": %s, "disable_web_page_preview": true}' \
          "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")")" \
    > /dev/null || true
}

if [ -z "$ADMIN_TOKEN" ]; then
  diga "[portal] ADMIN_TOKEN não está no .env — o /admin está no ar mas sem chave definida. Me diga se quer que eu gere uma."
  exit 0
fi

LOCAL=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  "http://127.0.0.1:$PORTA/admin?key=$ADMIN_TOKEN" || echo "000")
PUBLICO=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  "https://vorte369.com.br/admin?key=$ADMIN_TOKEN" || echo "000")

M="[portal de gestão]
Local (porta $PORTA): HTTP $LOCAL
Público: HTTP $PUBLICO

Seu link (guarda, tem a chave):
https://vorte369.com.br/admin?key=$ADMIN_TOKEN"

if [ "$PUBLICO" != "200" ] && [ "$LOCAL" = "200" ]; then
  M="$M

⚠️ O serviço está de pé mas o domínio não respondeu 200 — provável DNS/Caddy do vorte369.com.br. Me avisa que eu diagnostico (sem tocar no Caddy global)."
elif [ "$LOCAL" != "200" ]; then
  M="$M

🚨 Nem localmente respondeu 200 — vou investigar o serviço web."
fi
diga "$M"
exit 0
