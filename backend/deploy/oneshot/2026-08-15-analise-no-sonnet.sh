#!/usr/bin/env bash
# O combinado de 15/08 com o dono: juiz do dia em 6.3 (meta 7) → a análise
# principal troca para o Sonnet 5. Dados que sustentam: A/B do juiz com
# sonnet 7.7 (n=12) vs opus 6.0 (n=13), custo ~5x menor. O .env pode ter
# ANALYSIS_MODEL fixado no Opus — este oneshot grava o novo valor.
# Reverter: ANALYSIS_MODEL=claude-opus-4-8 no .env + pm2 restart (sem deploy).
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')

# idempotente
sed -i '/^ANALYSIS_MODEL=/d' .env
printf 'ANALYSIS_MODEL=claude-sonnet-5\n' >> .env

# reinicia SÓ os processos do poker (VPS multi-tenant)
ALVOS=$(pm2 jlist 2>/dev/null | python3 -c '
import json,sys
for p in json.load(sys.stdin):
    n = p.get("name","")
    if "poker" in n.lower():
        print(n)' 2>/dev/null || true)
for a in $ALVOS; do pm2 restart "$a" > /dev/null 2>&1 || true; done

CONFERE=$(grep -c '^ANALYSIS_MODEL=claude-sonnet-5' .env || true)
MSG="[modelo] Análise principal → Sonnet 5 (combinado de 15/08: juiz 6.3 < meta 7; A/B sonnet 7.7 vs opus 6.0; custo ~5x menor). Junto entrou a conferência de números: número sem lastro nas ferramentas gera reescrita e evento no banco. Gravado no .env ($CONFERE linha), reiniciado: ${ALVOS:-nenhum processo poker?}. Reversão = 1 linha no .env."
echo "$MSG"
if [ -n "$TG_TOKEN" ]; then
  curl -s -X POST "https://api.telegram.org/bot$TG_TOKEN/sendMessage" \
    -H 'Content-Type: application/json' \
    -d "$(printf '{"chat_id": 6452742024, "text": %s}' \
          "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$MSG")")" \
    > /dev/null || true
fi
exit 0
