#!/usr/bin/env bash
# Regrava as mãos PPPoker salvas AGORA COM O SHOWDOWN: o parser aprendeu a
# ler flow.show_hands/show_cards (cartas reveladas), então re-busca o JSON
# de cada mão no CDN e regrava o canonical completo. Mesma mecânica do
# reparse dos naipes; idempotente e sem dado de usuário no repo.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json

from app.db import get_repository
from app.parsers.pppoker_replay import fetch_and_parse

repo = get_repository()
out = {"src": "reparse-showdown-v1", "ok": 0, "fail": 0}

rows = (repo.client.table("hands").select("id,hand_id")
        .like("hand_id", "pppoker-%").execute().data) or []
out["total"] = len(rows)
for row in rows:
    key = row["hand_id"].removeprefix("pppoker-")
    try:
        h = fetch_and_parse(key)
        if not h:
            out["fail"] += 1
            continue
        repo.client.table("hands").update(
            {"canonical": json.loads(h.model_dump_json())}
        ).eq("id", row["id"]).execute()
        out["ok"] += 1
    except Exception as exc:
        out["fail"] += 1
        out.setdefault("errs", []).append(str(exc)[:100])

repo.log_event(0, None, "diag", out)
print(f"reparse showdown: {out}")
PY
exit 0
