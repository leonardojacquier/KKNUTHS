#!/usr/bin/env bash
# Regrava as mãos PPPoker já salvas com o mapa de naipes CORRIGIDO
# (1=♦ 2=♣ 3=♥ 4=♠ — o vídeo do replay confirmou; o mapa antigo trocava
# espadas por paus). O share_key está no próprio hand_id (pppoker-<key>):
# re-busca o JSON no CDN e regrava o canonical. Nada de dado no repo.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json

from app.db import get_repository
from app.parsers.pppoker_replay import fetch_and_parse

repo = get_repository()
out = {"src": "reparse-naipes-v1", "ok": 0, "fail": 0}

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
print(f"reparse naipes: {out}")
PY
exit 0
