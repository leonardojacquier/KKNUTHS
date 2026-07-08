#!/usr/bin/env bash
# Test-drive v2 na conta do admin: torneio demo COMPLETO (150 mãos) pelo fluxo
# real de upload — que agora anexa o relatório mão a mão automaticamente.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/test_drive.py \
    tests/sample_hands/demo_kknuths_tournament.txt 6452742024
