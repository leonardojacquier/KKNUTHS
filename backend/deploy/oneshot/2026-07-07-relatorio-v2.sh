#!/usr/bin/env bash
# Relatório mão a mão v2 (feedback do admin: análise em TODAS as mãos +
# identificação por Nº da mão). Envia ao beta user e cópia ao admin.
set -uo pipefail
cd /opt/poker-bot || exit 1

fail=0
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 8972465711 --update || fail=1
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 8972465711 6452742024 --update || fail=1
exit $fail
