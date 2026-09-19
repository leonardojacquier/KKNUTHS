#!/usr/bin/env bash
# "Não sei a chave" — reenvia o link completo do portal pro privado do dono.
# Se ADMIN_TOKEN não existir no .env, gera um agora, grava e reinicia SÓ os
# processos do poker no pm2 (a VPS é multi-tenant; 'pm2 restart all' é
# proibido — derrubaria Jarvis/GNHFIN juntos).
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
ADMIN_TOKEN=$(grep -m1 '^ADMIN_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')

diga() {
  echo "$1"
  [ -n "$TG_TOKEN" ] && curl -s -X POST \
    "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -H 'Content-Type: application/json' \
    -d "$(printf '{"chat_id": 6452742024, "text": %s, "disable_web_page_preview": true}' \
          "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")")" \
    > /dev/null || true
}

NOTA=""
if [ -z "$ADMIN_TOKEN" ]; then
  ADMIN_TOKEN=$(openssl rand -hex 16)
  printf '\nADMIN_TOKEN=%s\n' "$ADMIN_TOKEN" >> .env
  # só os processos do poker — nunca 'pm2 restart all' nesta VPS
  ALVOS=$(pm2 jlist 2>/dev/null | python3 -c '
import json,sys
for p in json.load(sys.stdin):
    n = p.get("name","")
    if "poker" in n.lower():
        print(n)' 2>/dev/null || true)
  for a in $ALVOS; do pm2 restart "$a" > /dev/null 2>&1 || true; done
  NOTA="
(chave não existia — acabei de gerar e reiniciar o serviço do poker: ${ALVOS:-nenhum processo 'poker' no pm2?})"
fi

STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 \
  "https://poker.vortex369.com.br/admin?key=$ADMIN_TOKEN" || echo "000")

diga "[portal — seu acesso]
https://poker.vortex369.com.br/admin?key=$ADMIN_TOKEN

Teste agora: HTTP $STATUS $( [ "$STATUS" = "200" ] && echo '✅ é só clicar e salvar nos favoritos' || echo '— se não abrir em 1 min me avisa' )$NOTA

Não compartilhe este link: a chave na URL é o login."
exit 0
