#!/usr/bin/env bash
# Sonda do SHOWDOWN da PPPoker: o replay da mão do admin teve showdown (vilão
# mostrou AK), mas o JSON não trouxe cartas em info.players — elas estão em
# OUTRO campo. Esta sonda varre a árvore inteira do JSON da última mão e
# reporta o CAMINHO de todo valor com cara de carta (int 258..1038, fora do
# board/herói já conhecidos) + as chaves completas de cada nível. Link do
# banco (runtime), nunca do repo.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import urllib.request

from app.db import get_repository

repo = get_repository()
out = {"src": "pppoker-showdown-probe-v1"}

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604",
      "Referer": "https://replay.pppoker.net/"}

key = None
try:
    rows = (repo.client.table("bot_events").select("detail")
            .ilike("detail->>q", "%pppoker%")
            .order("created_at", desc=True).limit(5).execute().data) or []
    for row in rows:
        m = re.search(r"[?&]shareKey=([0-9a-zA-Z-]{12,})",
                      row["detail"].get("q", ""))
        if m:
            key = m.group(1)
            break
except Exception as exc:
    out["db_err"] = str(exc)[:140]
out["key"] = key or ""

if key:
    try:
        req = urllib.request.Request(
            f"https://alicdn.pppoker.club/review_hand/{key}.json", headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            data = json.loads(r.read(900_000).decode("utf-8", "ignore"))

        def is_card(v):
            return isinstance(v, int) and 258 <= v <= 1038 and 2 <= v % 256 <= 14

        hits, keysets = [], {}

        def walk(node, path):
            if isinstance(node, dict):
                keysets.setdefault(path or "$", sorted(node.keys())[:20])
                for k, v in node.items():
                    walk(v, f"{path}.{k}" if path else k)
            elif isinstance(node, list):
                if node and all(is_card(x) for x in node):
                    hits.append({"path": path, "cards": node[:8]})
                else:
                    for i, v in enumerate(node[:12]):
                        walk(v, f"{path}[{i}]")
            elif is_card(node) and "chips" not in path.lower():
                hits.append({"path": path, "card": node})

        walk(data, "")
        out["card_hits"] = hits[:25]
        out["keysets"] = {k: v for k, v in list(keysets.items())[:25]}
    except Exception as exc:
        out["cdn_err"] = str(exc)[:160]

repo.log_event(0, None, "diag", {"src": "pppoker-showdown-probe-v1",
                                 "dados": json.dumps(out)[:9000]})
print("sonda showdown despejada no bot_events")
PY
exit 0
