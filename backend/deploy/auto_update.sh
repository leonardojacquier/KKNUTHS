#!/usr/bin/env bash
# Auto-deploy do poker-bot: roda no cron a cada 2 min; quando há commit novo no
# branch, puxa, redeploya (testes como portão) e avisa o admin no Telegram.
# Instalação (uma vez): ver deploy/README.md — seção "Auto-deploy".
set -euo pipefail

REPO=/opt/kknuths
APP=/opt/poker-bot
BRANCH=claude/poker-analysis-telegram-bot-mfuyhf
STATE=/tmp/poker-autoupdate.last

# nunca rodar duas instâncias ao mesmo tempo
exec 9>/tmp/poker-autoupdate.lock
flock -n 9 || exit 0

cd "$REPO"
git fetch origin "$BRANCH" -q
# compara com o último deploy BEM-SUCEDIDO (não com o HEAD do clone — um deploy
# que falhou no meio deixaria o HEAD avançado e mascararia o retry)
OK_FILE=/tmp/poker-autoupdate.ok
LOCAL=$(cat "$OK_FILE" 2>/dev/null || git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
[ "$LOCAL" = "$REMOTE" ] && exit 0

# não insistir num commit que acabou de falhar (espera o próximo push)
if [ -f "$STATE" ] && [ "$(cat "$STATE")" = "$REMOTE" ]; then
    exit 0
fi
echo "$REMOTE" > "$STATE"

echo "[$(date '+%F %T')] novo commit: ${LOCAL:0:7} -> ${REMOTE:0:7}; atualizando…"
git reset --hard -q "origin/$BRANCH"
cp -r "$REPO/backend/." "$APP/"

notify() {  # avisa o admin no Telegram (se configurado); nunca falha o deploy
    if grep -q '^TELEGRAM_ADMIN_CHAT_ID=' "$APP/.env" 2>/dev/null; then
        ADMIN=$(grep '^TELEGRAM_ADMIN_CHAT_ID=' "$APP/.env" | cut -d= -f2)
        cd "$APP" && PYTHONPATH="$APP" ./venv/bin/python scripts/tg.py send "$ADMIN" "$1" >/dev/null 2>&1 || true
    fi
}

if bash "$APP/deploy/vps_deploy.sh"; then
    MSG=$(cd "$REPO" && git log -1 --format='%s')
    echo "$REMOTE" > "$OK_FILE"
    echo "[$(date '+%F %T')] deploy OK em ${REMOTE:0:7}"
    notify "🔄 Bot atualizado (${REMOTE:0:7}): $MSG"
else
    echo "[$(date '+%F %T')] DEPLOY FALHOU em ${REMOTE:0:7} (testes?); bot antigo segue no ar"
    notify "⚠️ Auto-deploy falhou em ${REMOTE:0:7} — o bot continua na versão anterior. Ver /var/log/poker-autodeploy.log"
fi
