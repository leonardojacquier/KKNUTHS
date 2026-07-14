#!/usr/bin/env bash
# Sonda v2: index inteiro + TODOS os <script> (inline e CDN) + bundles do
# cdn-dls; rastreia shareKey -> requisição. Resultado em bot_events (diag).
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import urllib.request

from app.db import get_repository

IDX = ("https://replay.pppoker.net/new_game_record_publish/Frame/"
       "rls_20260624/index.html?shareKey=f48bcbb5-ef29-46d2-3a6c-5d8642064240&lan=pt")
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604"}
out = {"src": "pppoker-probe-v2"}


def get(url, limit=4_000_000):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=25) as r:
        return r.status, r.read(limit).decode("utf-8", "ignore")


def endpoints(js):
    found = set()
    for m in re.finditer(r'["\'`]((?:https?:)?//[a-zA-Z0-9._-]+/[a-zA-Z0-9_/.?=&%-]{3,110})'
                         r'["\'`]', js):
        found.add(m.group(1)[:130])
    for m in re.finditer(r'["\'`](/[a-zA-Z0-9_/.-]*(?:record|share|hand|api|query|'
                         r'get[A-Z])[a-zA-Z0-9_/.-]*)["\'`]', js):
        found.add(m.group(1)[:110])
    return sorted(found)[:30]


try:
    st, html = get(IDX)
    out["index_len"] = len(html)
    # TODOS os scripts: com src (qualquer host) + trechos inline
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
    out["scripts_src"] = srcs[:15]
    inline = " ".join(re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>',
                                 html, re.S))
    out["inline_share"] = [m[:180] for m in
                           re.findall(r'.{40}[sS]hare[kK]ey.{80}', inline)][:5]
    out["inline_load"] = [m[:160] for m in
                          re.findall(r'.{20}(?:loadScript|createElement\("script"|'
                                     r'\.src\s*=|import\().{80}', inline)][:6]

    eps, ctxs = set(), []
    for src in srcs:
        u = src if src.startswith("http") else (
            "https://replay.pppoker.net/new_game_record_publish/Frame/"
            "rls_20260624/" + src.lstrip("./"))
        try:
            _, js = get(u)
        except Exception as exc:
            ctxs.append({"js": src[-30:], "erro": str(exc)[:60]})
            continue
        eps.update(endpoints(js))
        for m in re.finditer(r'.{50}[sS]hare[kK]ey.{90}', js):
            ctxs.append({"js": src[-24:], "ctx": m.group(0)[:150]})
            if len(ctxs) >= 14:
                break
    out["endpoints"] = sorted(eps)[:30]
    out["share_ctx"] = ctxs[:14]
except Exception as exc:
    out["erro"] = f"{type(exc).__name__}: {exc}"[:200]

repo = get_repository()
if repo.enabled:
    blob = json.dumps(out, ensure_ascii=False)
    repo.log_event(0, "diag", "diag",
                   {"src": "pppoker-probe-v2",
                    "d0": blob[:3400], "d1": blob[3400:6800] or None,
                    "d2": blob[6800:10200] or None})
print("v2 registrado:", len(json.dumps(out)))
PY
exit 0
