#!/usr/bin/env bash
# Deploy do site GNH para o VPS vortex369 — mesmo padrão do TitanCalc/deploy.sh
# Uso: bash deploy-gnh.sh   (da raiz do repo KKNUTHS)
set -euo pipefail

HOST="root@srv1555380.hstgr.cloud"
DEST="/opt/gnh"

# ── 1. Gate: sanidade dos arquivos (aborta se algo estiver errado) ──────────
[[ -f gnh-redesign.html ]] || { echo "ERRO: gnh-redesign.html não encontrado — rode da raiz do repo"; exit 1; }
grep -q "</html>" gnh-redesign.html || { echo "ERRO: gnh-redesign.html truncado (sem </html>)"; exit 1; }
[[ -f assets/video/hero.webm ]] || { echo "ERRO: assets/video/hero.webm ausente"; exit 1; }
[[ -f assets/video/hero.mp4  ]] || { echo "ERRO: assets/video/hero.mp4 ausente"; exit 1; }

# ── 2. Carimbo do build (rastreabilidade, como no TitanCalc) ────────────────
HASH=$(md5sum gnh-redesign.html | cut -c1-10)
echo "Build local: $HASH"

# ── 3. Envio em UMA conexão só (fail2ban-friendly: tar via pipe ssh) ────────
tar czf - gnh-redesign.html assets \
  | ssh -o StrictHostKeyChecking=accept-new "$HOST" \
      "mkdir -p $DEST && tar xzf - -C $DEST"

# ── 4. Site antigo na raiz + index.html + md5 (segunda e última conexão) ────
# `cp -r assets/nuevo/. .` publica /ventas/, /fichas/, /institucional/, /promo/,
# /img/, robots.txt e sitemap.xml na raiz, preservando as 110 URLs já indexadas
# no gnhorizons.com. O index.html vem depois para a home continuar sendo o redesign.
LOCAL_MD5=$(md5sum gnh-redesign.html | cut -d' ' -f1)
REMOTE_MD5=$(ssh "$HOST" \
  "cd $DEST && cp -r assets/nuevo/. . && cp gnh-redesign.html index.html && md5sum index.html | cut -d' ' -f1")

if [[ "$LOCAL_MD5" != "$REMOTE_MD5" ]]; then
  echo "ERRO: md5 divergente — local $LOCAL_MD5 x remoto $REMOTE_MD5"
  exit 1
fi

echo "Deploy OK — md5 $LOCAL_MD5"
echo "Site: https://gnh.vortex369.com.br (config única de DNS+Caddy: ver DEPLOY-GNH.md)"
