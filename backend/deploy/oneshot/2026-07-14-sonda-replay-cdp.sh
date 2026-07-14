#!/usr/bin/env bash
# Recon DECISIVO: chromium headless + CDP captura a REDE real do replay Egret.
# As sondas estaticas (v1-v4) provaram que a URL da mao e montada em runtime
# dentro do jogo compilado — so um browser de verdade a dispara. Aqui gravamos
# toda requisicao XHR/fetch e frame de WebSocket. Resultado em bot_events.
set -uo pipefail
cd /opt/poker-bot || exit 1

# chromium do sistema (o mesmo do PDF do manual)
CHROME=""
for c in chromium chromium-browser google-chrome google-chrome-stable; do
    command -v "$c" >/dev/null 2>&1 && CHROME="$c" && break
done
[ -z "$CHROME" ] && { PYTHONPATH=/opt/poker-bot ./venv/bin/python -c "
from app.db import get_repository
get_repository().log_event(0,'diag','diag',{'src':'pppoker-cdp','erro':'sem chromium no PATH'})"; exit 0; }

./venv/bin/pip install -q pychrome >/dev/null 2>&1 || true

rm -rf /tmp/ckn-cdp && mkdir -p /tmp/ckn-cdp
"$CHROME" --headless=new --disable-gpu --no-sandbox --mute-audio \
    --remote-debugging-port=9333 --user-data-dir=/tmp/ckn-cdp about:blank \
    >/tmp/ckn-cdp/chrome.log 2>&1 &
CHROME_PID=$!
sleep 4

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import time

from app.db import get_repository

URL = ("https://replay.pppoker.net/new_game_record_publish/Frame/rls_20260624/"
       "index.html?shareKey=f48bcbb5-ef29-46d2-3a6c-5d8642064240&lan=pt")
ASSET = (".js", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".ttf", ".woff",
         ".woff2", ".thm", ".fnt", "egret", "eui.min", "tween", "assetsmanager")
out = {"src": "pppoker-cdp"}
reqs, sockets, frames, bodies = [], [], [], []

try:
    import pychrome

    browser = pychrome.Browser(url="http://127.0.0.1:9333")
    tab = browser.new_tab()

    def on_req(**kw):
        r = kw.get("request", {})
        u = r.get("url", "")
        if u and not any(a in u.lower() for a in ASSET):
            reqs.append({"m": r.get("method"), "u": u[:180],
                         "type": kw.get("type")})

    def on_ws_created(**kw):
        sockets.append(kw.get("url", "")[:180])

    def on_ws_recv(**kw):
        r = kw.get("response", {}) or {}
        p = str(r.get("payloadData", ""))[:200]
        if p:
            frames.append(p)

    def on_resp(**kw):
        r = kw.get("response", {}) or {}
        u = r.get("url", "")
        mime = r.get("mimeType", "")
        if ("json" in mime or "text" in mime) and not any(
                a in u.lower() for a in ASSET) and "manifest" not in u:
            bodies.append({"u": u[:150], "mime": mime,
                           "id": kw.get("requestId")})

    tab.set_listener("Network.requestWillBeSent", on_req)
    tab.set_listener("Network.webSocketCreated", on_ws_created)
    tab.set_listener("Network.webSocketFrameReceived", on_ws_recv)
    tab.set_listener("Network.responseReceived", on_resp)
    tab.start()
    tab.Network.enable()
    tab.Page.enable()
    tab.Page.navigate(url=URL)
    time.sleep(18)  # deixa o jogo carregar e buscar a mao

    # tenta ler o corpo das respostas de dados (antes de fechar)
    for b in bodies[:6]:
        try:
            resp = tab.Network.getResponseBody(requestId=b["id"])
            b["body"] = str(resp.get("body", ""))[:400]
        except Exception:
            b["body"] = "(sem corpo)"
    tab.stop()

    # dedup requests
    seen, uniq = set(), []
    for r in reqs:
        k = r["u"]
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    out["requests"] = uniq[:25]
    out["sockets"] = list(dict.fromkeys(sockets))[:8]
    out["frames"] = frames[:8]
    out["bodies"] = [{k: v for k, v in b.items() if k != "id"}
                     for b in bodies[:6]]
except Exception as exc:
    out["erro"] = f"{type(exc).__name__}: {exc}"[:220]

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag",
                   {"src": "pppoker-cdp", "d0": blob[:3400],
                    "d1": blob[3400:6800] or None, "d2": blob[6800:10200] or None,
                    "d3": blob[10200:13600] or None})
print("cdp registrado:", len(json.dumps(out)))
PY

kill "$CHROME_PID" 2>/dev/null || true
exit 0
