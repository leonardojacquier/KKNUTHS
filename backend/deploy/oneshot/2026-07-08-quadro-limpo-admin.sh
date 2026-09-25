#!/usr/bin/env bash
# Reenvia o quadro do torneio com o gráfico limpo (marcadores espaçados,
# rótulos sem colisão) para o admin conferir.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/send_board.py 6452742024 6452742024
