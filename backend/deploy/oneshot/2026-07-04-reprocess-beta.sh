#!/usr/bin/env bash
# Reprocessa os uploads dos primeiros beta users com o parser corrigido
# (bug de vírgula de milhar + ante no header gravou mãos de torneio como cash).
set -uo pipefail
cd /opt/poker-bot

for tgid in 8972465711 6104620007 6452742024; do
    echo "-- reprocessando uploads de $tgid --"
    PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/reprocess_uploads.py "$tgid" || true
done
