#!/usr/bin/env bash
# Sonda v4 (decisiva): manifest.json + bundles do jogo Egret. Descobre COMO a
# mao chega — endpoint REST legivel (facil) ou socket/binario (caro). Grep por
# shareKey/http/ws/getRecord nos bundles. Resultado em bot_events (diag).
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import urllib.request

from app.db import get_repository

BASE = ("https://replay.pppoker.net/new_game_record_publish/Frame/rls_20260624/")
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604"}
out = {"src": "pppoker-v4"}


def get(url, limit=6_000_000):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=30) as r:
        return r.read(limit).decode("utf-8", "ignore")


def scan(js):
    hits = {}
    for label, pat in {
        "http": r'["\'`](https?://[a-zA-Z0-9._-]+/[a-zA-Z0-9_/.?=&%{}-]{3,90})',
        "ws": r'["\'`](wss?://[a-zA-Z0-9._:/-]{4,90})',
        "share": r'.{30}[sS]hare[kK]ey.{50}',
        "record": r'["\'`](/?[a-zA-Z0-9_/.-]*[rR]ecord[a-zA-Z0-9_/.-]{0,50})["\'`]',
        "socket": r'(new\s+WebSocket|websocket|WebSocket\()',
        "proto": r'(protobuf|\.proto|decodePacket|readMessage|ByteArray)',
    }.items():
        found = list({m.group(0)[:120] if label in ("share", "socket", "proto")
                      else m.group(1)[:110]
                      for m in re.finditer(pat, js)})
        if found:
            hits[label] = found[:8]
    return hits


try:
    manifest = json.loads(get(BASE + "manifest.json?v=1"))
    scripts = (manifest.get("initial", []) + manifest.get("game", []))
    out["manifest"] = {"initial": manifest.get("initial", [])[:6],
                       "game": manifest.get("game", [])[:20]}
    # os bundles do "game" sao onde mora a logica da mao
    agg = {}
    for src in manifest.get("game", [])[:12]:
        try:
            js = get(src if src.startswith("http") else BASE + src.lstrip("./"))
        except Exception as exc:
            agg.setdefault("erros", []).append(f"{src[-30:]}: {exc}"[:80])
            continue
        for k, v in scan(js).items():
            agg.setdefault(k, [])
            for item in v:
                if item not in agg[k]:
                    agg[k].append(item)
    out["scan"] = {k: v[:10] for k, v in agg.items()}
except Exception as exc:
    out["erro"] = f"{type(exc).__name__}: {exc}"[:200]

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag",
                   {"src": "pppoker-v4", "d0": blob[:3400],
                    "d1": blob[3400:6800] or None, "d2": blob[6800:10200] or None})
print("v4 registrado:", len(json.dumps(out)))
PY
exit 0
