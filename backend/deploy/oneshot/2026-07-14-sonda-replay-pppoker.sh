#!/usr/bin/env bash
# Engenharia reversa do replay da PPPoker (e Suprema): descobrir de onde o
# app JS puxa o JSON da mão. Roda no VPS (rede livre; o sandbox bloqueia o
# domínio). Resultado vai para bot_events (event 'diag') — legível via SQL.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import urllib.request

from app.db import get_repository

URL = ("https://replay.pppoker.net/new_game_record_publish/Frame/"
       "rls_20260624/index.html?shareKey=f48bcbb5-ef29-46d2-3a6c-5d8642064240&lan=pt")
BASE = "https://replay.pppoker.net/new_game_record_publish/Frame/rls_20260624/"
KEY = "f48bcbb5-ef29-46d2-3a6c-5d8642064240"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126"}

out: dict = {"src": "pppoker-probe"}


def get(url, limit=2_000_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read(limit).decode("utf-8", "ignore")


try:
    st, html = get(URL)
    out["index"] = {"status": st, "len": len(html), "head": html[:300]}
    assets = re.findall(r'(?:src|href)=["\']([^"\']+\.js[^"\']*)["\']', html)
    out["assets"] = assets[:8]

    hits = []
    for a in assets[:5]:
        js_url = a if a.startswith("http") else BASE + a.lstrip("./")
        try:
            st2, js = get(js_url)
        except Exception as exc:
            hits.append({"js": a, "erro": str(exc)[:80]})
            continue
        # padrões de endpoint/XHR no bundle
        for m in re.finditer(
            r'["\']((?:https?:)?//[^"\']{8,120})["\']|["\'](/[a-zA-Z0-9_/.-]{4,80}'
            r'(?:record|Record|share|Share|hand|Hand|api|query|Query)'
            r'[a-zA-Z0-9_/.-]{0,60})["\']', js,
        ):
            frag = (m.group(1) or m.group(2) or "").strip()
            if frag and frag not in [h.get("u") for h in hits]:
                hits.append({"js": a[-25:], "u": frag[:120]})
            if len(hits) >= 25:
                break
        # como o shareKey é usado?
        for m in re.finditer(r'.{60}[sS]hare[kK]ey.{80}', js):
            hits.append({"ctx": m.group(0)[:150]})
            if len(hits) >= 32:
                break
    out["hits"] = hits[:32]
except Exception as exc:
    out["erro_geral"] = f"{type(exc).__name__}: {exc}"[:200]

# Suprema: só seguir o redirect para ver aonde aponta
try:
    req = urllib.request.Request("https://r.supremapoker.net/?t=ob2mfsa3002pt&er=5",
                                 headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        out["suprema"] = {"final_url": r.url[:200], "status": r.status,
                          "head": r.read(400).decode("utf-8", "ignore")[:300]}
except Exception as exc:
    out["suprema"] = {"erro": f"{type(exc).__name__}: {exc}"[:150]}

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag", {"src": "pppoker-probe",
                                       "dados": blob[:3500],
                                       "dados2": blob[3500:7000] or None})
print("probe registrado:", len(json.dumps(out)))
PY
exit 0
