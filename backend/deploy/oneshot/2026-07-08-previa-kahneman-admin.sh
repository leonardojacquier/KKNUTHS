#!/usr/bin/env bash
# Admin pediu exemplo das análises novas (Bayes + Kahneman) na base do beta,
# só para ele: prévia do /stats + relatório mão a mão com selos de decisão.
set -uo pipefail
cd /opt/poker-bot || exit 1

fail=0
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/send_stats_preview.py 8972465711 6452742024 || fail=1
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 8972465711 6452742024 --update || fail=1
exit $fail
