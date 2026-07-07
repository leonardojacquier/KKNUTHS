#!/usr/bin/env bash
# Linguagem nova (voz de coach informal) no relatório — cópia SÓ para o admin
# vetar antes de qualquer reenvio ao beta.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 8972465711 6452742024 --update
