#!/usr/bin/env bash
# Backup do banco do Umami (pg_dump comprimido, mantém os últimos 8)
# Instalar no cron:  bash deploy/umami/backup-umami.sh --install-cron
set -euo pipefail
DEST="$HOME/backups/umami"
mkdir -p "$DEST"

if [[ "${1:-}" == "--install-cron" ]]; then
  SCRIPT="$(readlink -f "$0")"
  ( crontab -l 2>/dev/null | grep -v backup-umami.sh; echo "20 3 * * 1 bash $SCRIPT >> $DEST/backup.log 2>&1" ) | crontab -
  echo "Cron instalado: toda segunda às 03:20. Backups em $DEST"
  exit 0
fi

STAMP=$(date +%F)
docker exec umami-db pg_dump -U umami -d umami | gzip > "$DEST/umami-$STAMP.sql.gz"
ls -1t "$DEST"/umami-*.sql.gz | tail -n +9 | xargs -r rm -f
echo "$(date '+%F %H:%M') backup ok: umami-$STAMP.sql.gz ($(du -h "$DEST/umami-$STAMP.sql.gz" | cut -f1))"
