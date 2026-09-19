#!/usr/bin/env bash
# Liga a alavanca 2: mão de decisão única pré-flop vai pro Sonnet 5
# (US$ 3/15 vs 5/25 do Opus; intro 2/10 até 31/08). Mão com pós-flop,
# multiway ou ICM continua no Opus. O juiz das 8h passa a dar nota POR
# MODELO — se o Sonnet degradar a clareza, reverter é apagar a linha do
# .env (10 segundos, sem deploy).
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')

# idempotente: remove a linha antiga (se houver) e grava a nova
sed -i '/^SIMPLE_HAND_MODEL=/d' .env
printf 'SIMPLE_HAND_MODEL=claude-sonnet-5\n' >> .env

# reinicia SÓ os processos do poker (VPS multi-tenant; 'pm2 restart all'
# derrubaria Jarvis/GNHFIN)
ALVOS=$(pm2 jlist 2>/dev/null | python3 -c '
import json,sys
for p in json.load(sys.stdin):
    n = p.get("name","")
    if "poker" in n.lower():
        print(n)' 2>/dev/null || true)
for a in $ALVOS; do pm2 restart "$a" > /dev/null 2>&1 || true; done

CONFERE=$(grep -c '^SIMPLE_HAND_MODEL=claude-sonnet-5' .env || true)
MSG="[roteador] Alavanca 2 LIGADA: mão simples (decisão única pré-flop) → Sonnet 5; resto → Opus. Gravado no .env ($CONFERE linha), reiniciado: ${ALVOS:-nenhum processo poker?}. O juiz das 8h passa a comparar a clareza por modelo — se o Sonnet decepcionar, me pede a reversão que é 1 linha."
echo "$MSG"
if [ -n "$TG_TOKEN" ]; then
  curl -s -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -H 'Content-Type: application/json' \
    -d "$(printf '{"chat_id": 6452742024, "text": %s}' \
          "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$MSG")")" \
    > /dev/null || true
fi
exit 0
