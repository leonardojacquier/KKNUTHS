#!/usr/bin/env bash
# Admin pediu para ver o quadro HUD (v2, stats PokerCraft) do torneio do beta.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/send_board.py 8972465711 6452742024
