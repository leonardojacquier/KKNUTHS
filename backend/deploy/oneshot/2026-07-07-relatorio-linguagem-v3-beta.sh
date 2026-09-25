#!/usr/bin/env bash
# Admin aprovou a linguagem nova — envia o relatório mão a mão ao beta user.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 8972465711 --update
