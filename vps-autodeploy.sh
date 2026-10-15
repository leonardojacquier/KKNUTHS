#!/usr/bin/env bash
# Auto-deploy do site GNH — roda NO VPS via cron (a cada 2 min).
# Publica somente quando a branch remota tiver commit novo.
# Instalação (uma vez): ver bloco no final deste arquivo ou DEPLOY-GNH.md.
set -euo pipefail

REPO="/root/KKNUTHS"
BRANCH="claude/professional-website-design-qqgnfg"
DEST="/opt/gnh"
LOG="/var/log/gnh-autodeploy.log"

cd "$REPO"
git fetch origin "$BRANCH" -q

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
[ "$LOCAL" = "$REMOTE" ] && exit 0    # nada novo — sai em silêncio

git checkout "$BRANCH" -q
git reset --hard "origin/$BRANCH" -q

grep -q "</html>" gnh-redesign.html || { echo "$(date -u +%FT%TZ) ERRO: HTML truncado — deploy abortado" >> "$LOG"; exit 1; }

mkdir -p "$DEST"
cp -r assets "$DEST/"

# Sitio actual de gnhorizons.com publicado en la RAÍZ: preserva las URLs ya
# indexadas (/ventas/, /fichas/, /institucional/, /promo/, /img/, robots.txt,
# sitemap.xml). Sin esto, apuntar gnhorizons.com al VPS devolvería 404 en las
# 110 URLs del sitemap. Ver DEPLOY-GNH.md § "Migrar gnhorizons.com al VPS".
cp -r assets/nuevo/. "$DEST/"

# La home siempre es el rediseño — va al final para pisar assets/nuevo/index.html
cp gnh-redesign.html "$DEST/"
cp gnh-redesign.html "$DEST/index.html"

echo "$(date -u +%FT%TZ) deploy OK $(git rev-parse --short HEAD)" >> "$LOG"

# ── Instalação (rodar UMA vez no VPS) ──────────────────────────────
# cp /root/KKNUTHS/vps-autodeploy.sh /opt/gnh-autodeploy.sh
# chmod +x /opt/gnh-autodeploy.sh
# ( crontab -l 2>/dev/null | grep -v gnh-autodeploy ; \
#   echo "*/2 * * * * /opt/gnh-autodeploy.sh >/dev/null 2>&1" ) | crontab -
