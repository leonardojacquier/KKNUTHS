#!/usr/bin/env bash
# Ingere as 6 mãos DEEP novas do demo (TM7000000150-155) na conta do Leo —
# silencioso, sem análise LLM. O treino/simulador ganham spots multi-street.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
from pathlib import Path

from app.parsers import parse_text
from app.db import get_repository

LEO = 6452742024
repo = get_repository()
if not repo.enabled:
    raise SystemExit("repo off")
user = repo.get_or_create_user(LEO, None)
hands = [h for h in parse_text(Path(
    "tests/sample_hands/demo_kknuths_tournament.txt").read_text())
    if h.hand_id.startswith("TM700000015")]
existing = {h.hand_id for h in repo.get_all_hands(user["id"], limit=500)}
new = [h for h in hands if h.hand_id not in existing]
for h in new:
    repo.save_hand(user["id"], h, None)
print(f"ingeridas {len(new)} mãos deep para o Leo (de {len(hands)} no arquivo)")
PY
exit 0
