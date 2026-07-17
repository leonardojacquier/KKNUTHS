#!/usr/bin/env bash
# Sonda do link NOVO de compartilhamento da PPPoker:
#   pppoker.club/poker/api/share.php?...&shareKey=<UUID>
# O link antigo (replay.pppoker.net/.../index.html?shareKey=<hex>) tinha o
# shareKey batendo direto no arquivo do CDN. O link novo usa UUID e pode NÃO
# bater direto — essa sonda descobre a rota certa e despeja no bot_events.
#
# Nada de dado de usuário no repo: o link vem do BANCO (última mensagem com
# pppoker.club vista no bot_events), igual à sonda da Suprema.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import urllib.request

from app.db import get_repository

repo = get_repository()
out = {"src": "pppoker-share-probe-v1"}

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604",
      "Referer": "https://replay.pppoker.net/"}


def get(url, limit=200_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.geturl(), r.read(limit).decode("utf-8", "ignore")


# 1) pega o link do BANCO — não do repo
link = None
try:
    rows = (repo.client.table("bot_events").select("detail")
            .ilike("detail->>q", "%pppoker.club%")
            .order("created_at", desc=True).limit(1).execute().data) or []
    if rows:
        m = re.search(r"https?://[^\s\"']+", rows[0]["detail"].get("q", ""))
        link = m.group(0) if m else None
except Exception as exc:
    out["db_err"] = str(exc)[:140]
out["link_found"] = bool(link)
if not link:
    repo.log_event(0, None, "diag", out)
    raise SystemExit(0)

m = re.search(r"[?&]shareKey=([0-9a-zA-Z-]{12,})", link)
key = m.group(1) if m else None
out["key"] = key or ""

# 2) tenta o CDN direto com o UUID (a hipótese principal)
if key:
    cdn = f"https://alicdn.pppoker.club/review_hand/{key}.json"
    try:
        u, body = get(cdn, 4000)
        out["cdn_direct"] = {"ok": body.strip().startswith(("{", "[")),
                             "len": len(body), "head": body[:300]}
    except Exception as exc:
        out["cdn_direct"] = {"err": str(exc)[:160]}

# 3) segue o share.php — o corpo/redirect pode revelar a URL real do replay
try:
    final, body = get(link, 6000)
    out["share_final"] = final[:220]
    out["share_head"] = body[:700]
    # procura qualquer URL de CDN/replay embutida na resposta
    out["urls_in_body"] = list(dict.fromkeys(re.findall(
        r"https?://[^\s\"'<>]+(?:cdn|review_hand|replay|\.json)[^\s\"'<>]*",
        body)))[:8]
    # e um shareKey diferente (o share.php pode remapear)
    keys = re.findall(r"shareKey[=\"':\s]+([0-9a-zA-Z-]{12,})", body)
    out["keys_in_body"] = list(dict.fromkeys(keys))[:6]
except Exception as exc:
    out["share_err"] = str(exc)[:160]

# 4) se o share.php devolveu JSON com uma url/key nova, tenta o CDN dela
for k in out.get("keys_in_body", []):
    if k and k != key:
        try:
            u, body = get(
                f"https://alicdn.pppoker.club/review_hand/{k}.json", 3000)
            out.setdefault("cdn_alt", []).append(
                {"key": k, "ok": body.strip().startswith(("{", "[")),
                 "head": body[:200]})
        except Exception as exc:
            out.setdefault("cdn_alt", []).append({"key": k, "err": str(exc)[:120]})

repo.log_event(0, None, "diag", {"src": "pppoker-share-probe-v1",
                                 "dados": json.dumps(out)[:7000]})
print("sonda pppoker share despejada no bot_events")
PY
exit 0
