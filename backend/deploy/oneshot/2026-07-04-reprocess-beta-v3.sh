#!/usr/bin/env bash
# v3: reprocessa de novo após a caçada de bugs — o parser agora captura
# "Uncalled bet returned" (resultado líquido de mão ganha sem showdown estava
# errado nas mãos gravadas) e valores com $/€.
set -uo pipefail
cd /opt/poker-bot || exit 1

fail=0
for tgid in 8972465711 6104620007 6452742024; do
    echo "-- reprocessando uploads de $tgid --"
    PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/reprocess_uploads.py "$tgid" || fail=1
done
exit $fail
