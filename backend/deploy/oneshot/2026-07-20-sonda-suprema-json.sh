#!/usr/bin/env bash
# Sonda 2 da SUPREMA: a sonda CDP descobriu o endpoint da mão —
#   https://ra.supremapoker.net/supremaAPI/replayInfo.php?s=<code>
# onde <code> = primeiros 8 chars do t= do link curto (r.supremapoker.net/?t=...).
# Esta sonda baixa o JSON completo e despeja a ESTRUTURA (keysets por nível +
# campos com cara de carta +头 do payload) pra escrever o parser. Link do
# banco (runtime), nunca do repo.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import urllib.request

from app.db import get_repository

repo = get_repository()
out = {"src": "suprema-json-probe-v1"}

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604",
      "Referer": "https://r.supremapoker.net/"}

code = None
try:
    rows = (repo.client.table("bot_events").select("detail")
            .ilike("detail->>q", "%supremapoker%")
            .order("created_at", desc=True).limit(3).execute().data) or []
    for row in rows:
        m = re.search(r"[?&]t=([0-9a-zA-Z]+)", row["detail"].get("q", ""))
        if m:
            code = m.group(1)[:8]
            break
except Exception as exc:
    out["db_err"] = str(exc)[:140]
out["code"] = code or ""

if code:
    try:
        req = urllib.request.Request(
            f"https://ra.supremapoker.net/supremaAPI/replayInfo.php?s={code}",
            headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read(900_000).decode("utf-8", "ignore")
        out["len"] = len(raw)
        data = json.loads(raw)

        keysets = {}

        def walk(node, path, depth=0):
            if depth > 6:
                return
            if isinstance(node, dict):
                keysets.setdefault(path or "$", sorted(node.keys())[:24])
                for k, v in node.items():
                    walk(v, f"{path}.{k}" if path else k, depth + 1)
            elif isinstance(node, list):
                for i, v in enumerate(node[:3]):
                    walk(v, f"{path}[{i}]", depth + 1)

        walk(data, "")
        out["keysets"] = {k: v for k, v in list(keysets.items())[:40]}
        # o miolo: um trecho generoso do payload cru (cartas, ações, nomes)
        out["raw_mid"] = raw[500:4200]
    except Exception as exc:
        out["err"] = str(exc)[:200]

repo.log_event(0, None, "diag", {"src": "suprema-json-probe-v1",
                                 "dados": json.dumps(out)[:9500]})
print("sonda suprema-json despejada")
PY
exit 0
