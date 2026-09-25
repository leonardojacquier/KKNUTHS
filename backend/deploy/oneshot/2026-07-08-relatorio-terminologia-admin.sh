#!/usr/bin/env bash
# Refaz o relatório do admin com terminologia REAL de poker (o prompt de
# simplificação inventava tradução tipo "par grande") e reenvia.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 6452742024 --update
