#!/usr/bin/env bash
# Cópia de admin: envia ao Leo (6452742024) o mesmo relatório mão a mão que o
# beta user 8972465711 recebeu — para conferência de qualidade.
set -uo pipefail
cd /opt/poker-bot || exit 1
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 8972465711 6452742024
