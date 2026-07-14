#!/usr/bin/env bash
# Payload real da mao: o CDP revelou o endpoint REST log_review_hand.php.
# Aqui buscamos a resposta dele (e dos endpoints do bbs) para escrever o
# parser. Resultado em bot_events (diag).
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import urllib.request

from app.db import get_repository

KEY = "f48bcbb5-ef29-46d2-3a6c-5d8642064240"
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604",
      "Referer": "https://replay.pppoker.net/"}
out = {"src": "pppoker-payload"}


def get(url, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    with urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                timeout=25) as r:
        return r.status, r.read(200_000).decode("utf-8", "ignore")


def post(url, data):
    body = json.dumps(data).encode()
    h = dict(UA)
    h["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h),
                                timeout=25) as r:
        return r.status, r.read(200_000).decode("utf-8", "ignore")


# 1) o endpoint principal da mao (REST, GET com share_key)
try:
    st, body = get(f"http://8.210.148.142/poker/api/log_review_hand.php"
                   f"?share_key={KEY}&rand=471_0.97")
    out["hand"] = {"status": st, "len": len(body), "body": body[:6000]}
except Exception as exc:
    out["hand_erro"] = f"{type(exc).__name__}: {exc}"[:200]

# 2) metadados (recomendacao/info) — as vezes trazem blinds/mesa
try:
    st, body = get("https://bbs.pppoker.net/api/game_video/share_recommend_info"
                   f"?share_key={KEY}")
    out["recommend"] = {"status": st, "body": body[:1500]}
except Exception as exc:
    out["recommend_erro"] = str(exc)[:120]

for path in ("info", "play"):
    try:
        st, body = post(f"https://bbs.pppoker.net/api/game_video/{path}",
                        {"share_key": KEY})
        out[f"bbs_{path}"] = {"status": st, "body": body[:1200]}
    except Exception as exc:
        out[f"bbs_{path}_erro"] = str(exc)[:120]

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag",
                   {"src": "pppoker-payload", "d0": blob[:3400],
                    "d1": blob[3400:6800] or None, "d2": blob[6800:10200] or None,
                    "d3": blob[10200:13600] or None})
print("payload registrado:", len(json.dumps(out)))
PY
exit 0
