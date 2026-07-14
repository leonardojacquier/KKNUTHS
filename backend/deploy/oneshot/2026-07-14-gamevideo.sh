#!/usr/bin/env bash
# Foco cirurgico: capturar o postData EXATO que o app envia para
# bbs.pppoker.net/api/game_video/* (endpoint ALCANCAVEL) + a resposta. E aqui
# que a mao vem (o IP China esta morto pelo VPS). Output so isso, sem lixo.
set -uo pipefail
cd /opt/poker-bot || exit 1

CHROME=""
for c in chromium chromium-browser google-chrome google-chrome-stable; do
    command -v "$c" >/dev/null 2>&1 && CHROME="$c" && break
done
[ -z "$CHROME" ] && exit 0
./venv/bin/pip install -q pychrome >/dev/null 2>&1 || true

rm -rf /tmp/ckn-gv && mkdir -p /tmp/ckn-gv
"$CHROME" --headless=new --disable-gpu --no-sandbox --mute-audio \
    --remote-debugging-port=9335 --user-data-dir=/tmp/ckn-gv about:blank \
    >/tmp/ckn-gv/chrome.log 2>&1 &
CHROME_PID=$!
sleep 4

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import time

from app.db import get_repository

URL = ("https://replay.pppoker.net/new_game_record_publish/Frame/rls_20260624/"
       "index.html?shareKey=f48bcbb5-ef29-46d2-3a6c-5d8642064240&lan=pt")
out = {"src": "pppoker-gamevideo"}
captured = {}  # requestId -> {url, method, post, headers}

try:
    import pychrome

    browser = pychrome.Browser(url="http://127.0.0.1:9335")
    tab = browser.new_tab()

    def on_req(**kw):
        r = kw.get("request", {})
        u = r.get("url", "")
        if "game_video" in u or "review_hand" in u:
            captured[kw.get("requestId")] = {
                "url": u[:150], "method": r.get("method"),
                "post": str(r.get("postData", ""))[:500],
                "hdr": {k: v for k, v in (r.get("headers") or {}).items()
                        if k.lower() in ("content-type", "token", "authorization",
                                         "x-token", "sign", "device")}}

    tab.set_listener("Network.requestWillBeSent", on_req)
    tab.start()
    tab.Network.enable()
    tab.Page.enable()
    tab.Page.navigate(url=URL)
    time.sleep(20)

    got = []
    for rid, info in captured.items():
        try:
            b = tab.Network.getResponseBody(requestId=rid)
            body = b.get("body", "")
            info["resp"] = body[:2500] if not b.get("base64Encoded") else "(b64)"
        except Exception as exc:
            info["resp_erro"] = str(exc)[:80]
        got.append(info)
    tab.stop()
    out["calls"] = got[:6]
except Exception as exc:
    out["erro"] = f"{type(exc).__name__}: {exc}"[:200]

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag",
                   {"src": "pppoker-gamevideo", "d0": blob[:3400],
                    "d1": blob[3400:6800] or None, "d2": blob[6800:10200] or None})
print("gamevideo registrado:", len(json.dumps(out)))
PY

kill "$CHROME_PID" 2>/dev/null || true
exit 0
