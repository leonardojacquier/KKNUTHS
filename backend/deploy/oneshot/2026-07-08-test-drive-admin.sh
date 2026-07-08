#!/usr/bin/env bash
# Test-drive do torneio demo na conta do admin: pipeline completo + resultados
# no Telegram dele, deixando /simular e /treino prontos para testar.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/test_drive.py \
    tests/sample_hands/demo_kknuths_tournament.txt 6452742024
