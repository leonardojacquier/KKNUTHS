#!/usr/bin/env bash
# A mao e um JSON estatico no CDN Alibaba GLOBAL (alcancavel!):
# alicdn.pppoker.club/review_hand/<share_key>.json. Despeja o JSON inteiro
# para eu ver acoes/cartas e escrever o parser.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import urllib.request

from app.db import get_repository

KEY = "f48bcbb5-ef29-46d2-3a6c-5d8642064240"
URL = f"https://alicdn.pppoker.club/review_hand/{KEY}.json"
UA = {"User-Agent": "Mozilla/5.0 (iPhone)", "Referer": "https://replay.pppoker.net/"}

out = {"src": "pppoker-hand-json"}
try:
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA),
                                timeout=30) as r:
        raw = r.read(400_000).decode("utf-8", "ignore")
    out["len"] = len(raw)
    # tenta parsear e resumir a ESTRUTURA (chaves), depois despeja cru em chunks
    try:
        d = json.loads(raw)
        info = d.get("info", {})
        out["keys_top"] = list(d.keys())
        out["keys_info"] = list(info.keys())
        # a sequencia de acoes costuma estar em info['records'|'actions'|'steps']
        for cand in ("records", "actions", "steps", "operate", "game_record",
                     "hand_record"):
            if cand in info:
                out["actions_key"] = cand
                out["actions_sample"] = json.dumps(info[cand])[:1200]
        # cartas do heroi/board
        out["players_sample"] = json.dumps(
            [{"n": p.get("user_name"), "seat": p.get("seatid"),
              "self": p.get("isSelf"), "cards": p.get("cards") or p.get("hand_card")}
             for p in d.get("players", [])])[:900]
    except Exception as exc:
        out["parse_erro"] = str(exc)[:120]
    repo = get_repository()
    if repo.enabled:
        # o JSON cru inteiro, em pedacos, para reconstruir o formato exato
        chunks = {f"raw{i}": raw[i*3300:(i+1)*3300] or None for i in range(6)}
        meta = json.dumps(out, ensure_ascii=False)
        repo.log_event(0, "diag", "diag",
                       {"src": "pppoker-hand-json", "meta": meta[:3000], **chunks})
    print("hand-json registrado:", out.get("len"))
except Exception as exc:
    repo = get_repository()
    if repo.enabled:
        repo.log_event(0, "diag", "diag",
                       {"src": "pppoker-hand-json",
                        "erro": f"{type(exc).__name__}: {exc}"[:200]})
    print("erro:", exc)
PY
exit 0
