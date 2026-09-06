#!/usr/bin/env bash
# Revalidação prometida ao beta user (feedback via WhatsApp 06/07): mensagem
# de correção + quadro do torneio + relatório MÃO A MÃO das 54 mãos.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/revalidation_report.py 8972465711
