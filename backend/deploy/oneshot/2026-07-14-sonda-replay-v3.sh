#!/usr/bin/env bash
# Sonda v3: despeja o HTML CRU do index (7.8KB) — o regex das v1/v2 nao viu
# o loader do app. Ler com os proprios olhos revela como o shareKey entra.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import urllib.request

from app.db import get_repository

IDX = ("https://replay.pppoker.net/new_game_record_publish/Frame/"
       "rls_20260624/index.html?shareKey=f48bcbb5-ef29-46d2-3a6c-5d8642064240&lan=pt")
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604"}

with urllib.request.urlopen(urllib.request.Request(IDX, headers=UA),
                            timeout=25) as r:
    html = r.read(200_000).decode("utf-8", "ignore")

repo = get_repository()
if repo.enabled:
    repo.log_event(0, "diag", "diag", {
        "src": "pppoker-html",
        "h0": html[:3400], "h1": html[3400:6800] or None,
        "h2": html[6800:10200] or None})
print("html registrado:", len(html))
PY
exit 0
