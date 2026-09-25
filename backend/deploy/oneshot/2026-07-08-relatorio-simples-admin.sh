#!/usr/bin/env bash
# Regenera o relatório mão a mão do admin com a versão simples embutida em
# cada mão (toggle 🎈 no HTML) e reenvia.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 6452742024 --update
