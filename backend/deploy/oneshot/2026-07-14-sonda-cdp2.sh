#!/usr/bin/env bash
# CDP definitivo: browser abre o replay (que FUNCIONA) e capturamos o CORPO
# real de cada resposta de dados + o postData exato. Resolve de vez: payload
# da mao + parametros certos. Sem filtro de mime; espera a rede terminar.
set -uo pipefail
cd /opt/poker-bot || exit 1

CHROME=""
for c in chromium chromium-browser google-chrome google-chrome-stable; do
    command -v "$c" >/dev/null 2>&1 && CHROME="$c" && break
done
[ -z "$CHROME" ] && exit 0
./venv/bin/pip install -q pychrome >/dev/null 2>&1 || true

rm -rf /tmp/ckn-cdp2 && mkdir -p /tmp/ckn-cdp2
"$CHROME" --headless=new --disable-gpu --no-sandbox --mute-audio \
    --remote-debugging-port=9334 --user-data-dir=/tmp/ckn-cdp2 about:blank \
    >/tmp/ckn-cdp2/chrome.log 2>&1 &
CHROME_PID=$!
sleep 4

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import time

from app.db import get_repository

URL = ("https://replay.pppoker.net/new_game_record_publish/Frame/rls_20260624/"
       "index.html?shareKey=f48bcbb5-ef29-46d2-3a6c-5d8642064240&lan=pt")
ASSET = (".js", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".ttf", ".woff",
         ".woff2", ".fnt", "egret", "eui.min", "tween", "assetsmanager",
         "favicon", "aliyuncs", ".thm")
DATA_HINT = ("log_review_hand", "game_video", "hand", "record", "review")
out = {"src": "pppoker-cdp2"}
posts = {}     # requestId -> postData
finished = []  # requestIds que terminaram
resp_meta = {}  # requestId -> {url, mime}

try:
    import pychrome

    browser = pychrome.Browser(url="http://127.0.0.1:9334")
    tab = browser.new_tab()

    def on_req(**kw):
        rid = kw.get("requestId")
        r = kw.get("request", {})
        pd = r.get("postData")
        if pd:
            posts[rid] = {"url": r.get("url", "")[:150], "post": str(pd)[:400]}

    def on_resp(**kw):
        rid = kw.get("requestId")
        r = kw.get("response", {}) or {}
        u = r.get("url", "")
        if not any(a in u.lower() for a in ASSET):
            resp_meta[rid] = {"url": u[:170], "mime": r.get("mimeType", "")}

    def on_fin(**kw):
        finished.append(kw.get("requestId"))

    tab.set_listener("Network.requestWillBeSent", on_req)
    tab.set_listener("Network.responseReceived", on_resp)
    tab.set_listener("Network.loadingFinished", on_fin)
    tab.start()
    tab.Network.enable()
    tab.Page.enable()
    tab.Page.navigate(url=URL)
    time.sleep(25)  # deixa TUDO carregar

    # corpo de cada resposta de dados que terminou
    got = []
    for rid, meta in resp_meta.items():
        interesting = any(h in meta["url"].lower() for h in DATA_HINT)
        if not interesting:
            continue
        item = {"url": meta["url"], "mime": meta["mime"],
                "finished": rid in finished}
        try:
            b = tab.Network.getResponseBody(requestId=rid)
            body = b.get("body", "")
            if b.get("base64Encoded"):
                item["b64"] = True
                item["body"] = body[:200]
            else:
                item["body"] = body[:5000]
        except Exception as exc:
            item["body_erro"] = str(exc)[:80]
        got.append(item)
    tab.stop()

    out["data_responses"] = got[:6]
    out["posts"] = [v for v in posts.values()
                    if any(h in v["url"].lower() for h in DATA_HINT)][:6]
except Exception as exc:
    out["erro"] = f"{type(exc).__name__}: {exc}"[:220]

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag",
                   {"src": "pppoker-cdp2", "d0": blob[:3400],
                    "d1": blob[3400:6800] or None, "d2": blob[6800:10200] or None,
                    "d3": blob[10200:13600] or None})
print("cdp2 registrado:", len(json.dumps(out)))
PY

kill "$CHROME_PID" 2>/dev/null || true
exit 0
