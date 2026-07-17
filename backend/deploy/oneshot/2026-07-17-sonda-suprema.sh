#!/usr/bin/env bash
# Sonda do replay SUPREMA (mesma engenharia do PPPoker): pega o último link
# de replay suprema visto no bot_events (runtime — nada de dado de usuário no
# repo), segue o redirect do link curto, e captura a REDE real do replay com
# o chromium (CDP), despejando URLs+corpos de dados no bot_events (diag).
set -uo pipefail
cd /opt/poker-bot || exit 1

CHROME=""
for c in chromium chromium-browser google-chrome google-chrome-stable; do
    command -v "$c" >/dev/null 2>&1 && CHROME="$c" && break
done
[ -z "$CHROME" ] && exit 0
./venv/bin/pip install -q pychrome >/dev/null 2>&1 || true

rm -rf /tmp/ckn-sup && mkdir -p /tmp/ckn-sup
"$CHROME" --headless=new --disable-gpu --no-sandbox --mute-audio \
    --remote-debugging-port=9345 --user-data-dir=/tmp/ckn-sup about:blank \
    >/tmp/ckn-sup/chrome.log 2>&1 &
sleep 4

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import time
import urllib.request

from app.db import get_repository

repo = get_repository()
out = {"src": "suprema-probe-v1"}

# 1) o link vem do BANCO (última mensagem com supremapoker) — não do repo
link = None
try:
    rows = (repo.client.table("bot_events").select("detail")
            .ilike("detail->>q", "%supremapoker%")
            .order("created_at", desc=True).limit(1).execute().data) or []
    if rows:
        m = re.search(r"https?://[^\s\"']+", rows[0]["detail"].get("q", ""))
        link = m.group(0) if m else None
except Exception as exc:
    out["db_err"] = str(exc)[:120]
out["link_found"] = bool(link)
if not link:
    repo.log_event(0, None, "diag", out)
    raise SystemExit(0)

# 2) segue o redirect do link curto (r.supremapoker.net/?t=...)
final_url, html_head = None, ""
try:
    req = urllib.request.Request(link, headers={
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605"})
    with urllib.request.urlopen(req, timeout=25) as r:
        final_url = r.geturl()
        html_head = r.read(4000).decode("utf-8", "ignore")
except Exception as exc:
    out["redir_err"] = str(exc)[:160]
out["final_url"] = (final_url or "")[:220]
out["html_head"] = html_head[:600]
out["scripts"] = re.findall(r'src="([^"]+)"', html_head)[:8]

# 3) CDP: abre o replay real e captura urls + corpos de respostas de DADOS
ASSET = (".js", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".ttf", ".woff",
         ".woff2", ".fnt", "egret", "eui.min", "tween", "assetsmanager",
         "favicon", ".css", ".thm")
try:
    import pychrome

    browser = pychrome.Browser(url="http://127.0.0.1:9345")
    tab = browser.new_tab()
    resp_meta, finished, posts = {}, [], {}

    def on_req(**kw):
        r = kw.get("request", {})
        if r.get("postData"):
            posts[kw.get("requestId")] = {
                "url": r.get("url", "")[:170],
                "post": str(r["postData"])[:400]}

    def on_resp(**kw):
        r = kw.get("response", {}) or {}
        u = r.get("url", "")
        if not any(a in u.lower() for a in ASSET):
            resp_meta[kw.get("requestId")] = {
                "url": u[:180], "mime": r.get("mimeType", "")}

    def on_fin(**kw):
        finished.append(kw.get("requestId"))

    tab.set_listener("Network.requestWillBeSent", on_req)
    tab.set_listener("Network.responseReceived", on_resp)
    tab.set_listener("Network.loadingFinished", on_fin)
    tab.start()
    tab.call_method("Network.enable")
    tab.call_method("Page.enable")
    tab.call_method("Page.navigate", url=final_url or link)
    time.sleep(22)

    bodies = []
    for rid in finished:
        meta = resp_meta.get(rid)
        if not meta:
            continue
        try:
            b = tab.call_method("Network.getResponseBody", requestId=rid)
            body = b.get("body", "")
            if body and len(body) > 40:
                bodies.append({"u": meta["url"], "mime": meta["mime"],
                               "len": len(body), "head": body[:500]})
        except Exception:
            continue
    out["cdp_urls"] = [m["url"] for m in resp_meta.values()][:15]
    out["cdp_posts"] = list(posts.values())[:5]
    # os corpos maiores primeiro: o JSON da mão costuma ser o maior
    bodies.sort(key=lambda x: -x["len"])
    out["cdp_bodies"] = bodies[:4]
    tab.stop()
except Exception as exc:
    out["cdp_err"] = str(exc)[:200]

repo.log_event(0, None, "diag", {"src": "suprema-probe-v1",
                                 "dados": json.dumps(out)[:7000]})
print("sonda suprema despejada no bot_events")
PY
pkill -f "remote-debugging-port=9345" 2>/dev/null || true
exit 0
