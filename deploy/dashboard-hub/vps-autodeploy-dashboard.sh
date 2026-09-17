#!/usr/bin/env bash
# Auto-deploy do portal dashboard.vortex369.com.br — roda NO VPS via cron.
#
# Mesmo princípio do vps-autodeploy.sh do site: o VPS puxa sozinho, ninguém
# entra por SSH de fora (o fail2ban não gosta de rajadas de ssh/scp).
# A diferença é que aqui existe build: e build que falha NÃO pode derrubar o
# portal que está no ar.
#
# Instalação (UMA vez, no VPS):
#   cp /opt/dashboard-gnh/deploy/vps-autodeploy-dashboard.sh /opt/dashboard-autodeploy.sh
#   chmod +x /opt/dashboard-autodeploy.sh
#   ( crontab -l 2>/dev/null | grep -v dashboard-autodeploy ; \
#     echo "*/5 * * * * /opt/dashboard-autodeploy.sh >/dev/null 2>&1" ) | crontab -
set -euo pipefail

REPO="/opt/dashboard-gnh"
BRANCH="main"
APP="dashboard-gnh"
LOG="/var/log/dashboard-autodeploy.log"

log() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

cd "$REPO"
git fetch origin "$BRANCH" -q

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
[ "$LOCAL" = "$REMOTE" ] && exit 0    # nada novo — sai em silêncio

log "commit novo $(git rev-parse --short "origin/$BRANCH") — atualizando"
git reset --hard "origin/$BRANCH" -q

# dependência nova só reinstala quando o lockfile mudou
if ! git diff --quiet "$LOCAL" "$REMOTE" -- package-lock.json package.json; then
  log "package.json/lock mudou — npm ci"
  npm ci --no-audit --no-fund >> "$LOG" 2>&1
fi

# guarda o build que está no ar antes de tentar o novo
rm -rf .next-prev
[ -d .next ] && cp -a .next .next-prev

if npm run build >> "$LOG" 2>&1; then
  pm2 restart "$APP" --update-env >> "$LOG" 2>&1
  log "deploy OK $(git rev-parse --short HEAD)"
else
  # build quebrado: devolve o anterior e NÃO reinicia — o portal segue no ar
  log "ERRO: build falhou — mantendo a versão anterior. Veja o log acima."
  rm -rf .next
  [ -d .next-prev ] && mv .next-prev .next
  # volta o código também, senão o próximo cron tenta o mesmo commit quebrado
  git reset --hard "$LOCAL" -q
  log "revertido para $(git rev-parse --short HEAD)"
  exit 1
fi
