#!/usr/bin/env bash
# v2 do diagnóstico: além de mandar ao admin, grava o tail do log de erro em
# bot_events (event 'diag') — o erro fica legível de fora, via SQL.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
from pathlib import Path

from app.db import get_repository

candidates = [
    Path.home() / ".pm2/logs/poker-bot-error.log",
    Path("/root/.pm2/logs/poker-bot-error.log"),
]
tail = ""
for p in candidates:
    if p.exists():
        lines = p.read_text(errors="ignore").splitlines()
        # só o que interessa: do último Traceback em diante, senão as 60 finais
        idxs = [i for i, l in enumerate(lines) if "Traceback" in l]
        start = idxs[-1] if idxs else max(0, len(lines) - 60)
        tail = "\n".join(lines[start:start + 80])
        break

repo = get_repository()
if repo.enabled:
    repo.log_event(0, "diag", "diag", {"src": "poker-bot-error.log",
                                       "tail": tail[-3500:] or "(log vazio)"})
print("diag gravado:", len(tail), "chars")
PY
