#!/usr/bin/env bash
# Fase 4 do motor bayesiano: o parser agora captura as cartas mostradas no
# showdown. Reprocessa os uploads guardados para preencher shown_cards nas
# mãos antigas e roda a PRIMEIRA calibração das likelihoods (depois o cron
# semanal de segunda 5h assume).
set -uo pipefail
cd /opt/poker-bot || exit 1

fail=0
for tgid in 8972465711 6104620007 6452742024; do
    echo "-- reprocessando uploads de $tgid --"
    PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/reprocess_uploads.py "$tgid" || fail=1
done
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/calibrate_likelihood.py || fail=1
exit $fail
