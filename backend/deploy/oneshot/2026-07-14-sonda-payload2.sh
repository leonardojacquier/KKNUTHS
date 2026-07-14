#!/usr/bin/env bash
# Payload v2: game_video/info com user_id+lang (POST que o CDP mostrou) e
# retry do log_review_hand.php com timeout maior. Um deles tem as ACOES da mao.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import urllib.request

from app.db import get_repository

KEY = "f48bcbb5-ef29-46d2-3a6c-5d8642064240"
UID = "10006351248"  # uid que apareceu na telemetria do proprio replay (CDP)
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604",
      "Referer": "https://replay.pppoker.net/"}
out = {"src": "pppoker-payload2"}


def req(url, data=None, timeout=25, form=False):
    h = dict(UA)
    body = None
    if data is not None:
        if form:
            from urllib.parse import urlencode
            body = urlencode(data).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            h["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h),
                                timeout=timeout) as r:
        return r.status, r.read(300_000).decode("utf-8", "ignore")


# 1) game_video/info — JSON e form, com user_id+lang
for tag, kw in (("info_json", {}), ("info_form", {"form": True})):
    try:
        st, body = req("https://bbs.pppoker.net/api/game_video/info",
                       {"share_key": KEY, "user_id": UID, "lang": "en"}, **kw)
        out[tag] = {"status": st, "len": len(body), "body": body[:5000]}
        if '"error_code":0' in body and len(body) > 200:
            break
    except Exception as exc:
        out[tag + "_erro"] = f"{type(exc).__name__}: {exc}"[:150]

# 2) game_video/play com params completos
try:
    st, body = req("https://bbs.pppoker.net/api/game_video/play",
                   {"share_key": KEY, "user_id": UID, "lang": "en"})
    out["play"] = {"status": st, "len": len(body), "body": body[:4000]}
except Exception as exc:
    out["play_erro"] = str(exc)[:150]

# 3) retry do endpoint direto com timeout longo
try:
    st, body = req(f"http://8.210.148.142/poker/api/log_review_hand.php"
                   f"?share_key={KEY}&rand=471_0.97", timeout=45)
    out["hand"] = {"status": st, "len": len(body), "body": body[:6000]}
except Exception as exc:
    out["hand_erro"] = f"{type(exc).__name__}: {exc}"[:150]

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag",
                   {"src": "pppoker-payload2", "d0": blob[:3400],
                    "d1": blob[3400:6800] or None, "d2": blob[6800:10200] or None,
                    "d3": blob[10200:13600] or None})
print("payload2 registrado:", len(json.dumps(out)))
PY
exit 0
