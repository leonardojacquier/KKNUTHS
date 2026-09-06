#!/usr/bin/env bash
# Test-drive v3: demo regenerado (sem o call sumido) e selo de decisão agora
# vem do veredito do próprio coach — inclusive ❌/⚠️.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/test_drive.py \
    tests/sample_hands/demo_kknuths_tournament.txt 6452742024
