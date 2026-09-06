#!/usr/bin/env bash
# Sonda 3 da SUPREMA: o replayInfo.php devolveu 13.7KB no navegador (CDP) mas
# [] no GET direto dias depois — o share EXPIRA. Esta sonda roda no deploy e:
#   1) pega o link suprema MAIS RECENTE do banco (quando o admin colar um
#      novo, esta rodada captura a estrutura fresca)
#   2) tenta o GET direto com headers de navegador completos
#   3) fallback: abre o replayer no chromium (CDP) e captura o corpo real
#   4) despeja ESTRUTURA (keysets + campos com cara de carta + trecho bruto)
set -uo pipefail
cd /opt/poker-bot || exit 1

CHROME=""
for c in chromium chromium-browser google-chrome google-chrome-stable; do
    command -v "$c" >/dev/null 2>&1 && CHROME="$c" && break
done
rm -rf /tmp/ckn-sup3 && mkdir -p /tmp/ckn-sup3
if [ -n "$CHROME" ]; then
    "$CHROME" --headless=new --disable-gpu --no-sandbox --mute-audio \
        --remote-debugging-port=9347 --user-data-dir=/tmp/ckn-sup3 about:blank \
        >/tmp/ckn-sup3/chrome.log 2>&1 &
    sleep 4
fi

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import time
import urllib.request

from app.db import get_repository

repo = get_repository()
out = {"src": "suprema-v3"}


def structure(raw: str) -> dict:
    o: dict = {"len": len(raw)}
    try:
        data = json.loads(raw)
    except Exception:
        o["not_json"] = raw[:200]
        return o
    keysets: dict = {}

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
    o["keysets"] = {k: v for k, v in list(keysets.items())[:36]}
    o["raw_mid"] = raw[400:3600]
    return o


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
m = re.search(r"[?&]t=([0-9a-zA-Z]+)", link or "")
code = m.group(1)[:8] if m else None
out["code"] = code or ""

if code:
    url = f"https://ra.supremapoker.net/supremaAPI/replayInfo.php?s={code}"
    # 2) GET com headers completos de navegador
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) "
                          "AppleWebKit/605 Mobile/15E148 Safari/604",
            "Referer": "https://r.supremapoker.net/",
            "Origin": "https://r.supremapoker.net",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=25) as r:
            out["direct"] = structure(r.read(900_000).decode("utf-8", "ignore"))
    except Exception as exc:
        out["direct"] = {"err": str(exc)[:160]}

    # 3) fallback CDP se o direto veio vazio
    if (out.get("direct") or {}).get("len", 0) < 100 and link:
        try:
            import pychrome

            browser = pychrome.Browser(url="http://127.0.0.1:9347")
            tab = browser.new_tab()
            meta, fin = {}, []
            tab.set_listener("Network.responseReceived", lambda **kw: meta.update(
                {kw.get("requestId"): (kw.get("response") or {}).get("url", "")}))
            tab.set_listener("Network.loadingFinished",
                             lambda **kw: fin.append(kw.get("requestId")))
            tab.start()
            tab.call_method("Network.enable")
            tab.call_method("Page.enable")
            tab.call_method("Page.navigate", url=link)
            time.sleep(20)
            for rid in fin:
                if "replayInfo" in (meta.get(rid) or ""):
                    b = tab.call_method("Network.getResponseBody", requestId=rid)
                    out["cdp"] = structure(b.get("body", ""))
                    break
            tab.stop()
        except Exception as exc:
            out["cdp"] = {"err": str(exc)[:160]}

repo.log_event(0, None, "diag", {"src": "suprema-v3",
                                 "dados": json.dumps(out)[:9500]})
print("sonda suprema v3 despejada")
PY
pkill -f "remote-debugging-port=9347" 2>/dev/null || true
exit 0
