#!/usr/bin/env bash
# Atualiza o site GNH — rodar NO SERVIDOR (VPS), de dentro de ~/KKNUTHS
# Uso: bash deploy-local.sh
set -euo pipefail

BRANCH="claude/professional-website-design-qqgnfg"
DEST="/opt/gnh"

git fetch origin "$BRANCH"
git checkout "$BRANCH" -q
git pull origin "$BRANCH" -q

[[ -f gnh-redesign.html ]] || { echo "ERRO: gnh-redesign.html não encontrado"; exit 1; }
grep -q "</html>" gnh-redesign.html || { echo "ERRO: HTML truncado"; exit 1; }

mkdir -p "$DEST"
cp -r assets "$DEST/"

# Sitio actual de gnhorizons.com en la RAÍZ: preserva las URLs ya indexadas
# (/ventas/, /fichas/, /institucional/, /promo/, /img/, robots.txt, sitemap.xml).
cp -r assets/nuevo/. "$DEST/"

# La home siempre es el rediseño — al final, para pisar assets/nuevo/index.html
cp gnh-redesign.html "$DEST/"
cp gnh-redesign.html "$DEST/index.html"

echo "Deploy OK — build $(md5sum "$DEST/index.html" | cut -c1-10)"
echo "Recarregue com Ctrl+Shift+R: https://gnh.vortex369.com.br"
