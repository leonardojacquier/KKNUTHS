#!/usr/bin/env bash
# Sonda dos NAIPES da PPPoker: o admin conferiu o vídeo do replay e as cartas
# que decodificamos como PAUS eram ESPADAS — o mapa _SUIT {1:s,2:h,3:d,4:c}
# tem naipes trocados. Esta sonda coleta a evidência pra fechar o mapa certo:
#   1) valores BRUTOS (ints) de todas as cartas do JSON da última mão
#      (hero, board, jogadores no showdown, winning_info)
#   2) o JS do replayer web (que converte código->sprite do naipe) — a fonte
#      da verdade de como o cliente desenha cada código
# O link vem do BANCO (runtime), nunca do repo.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import re
import urllib.request

from app.db import get_repository

repo = get_repository()
out = {"src": "pppoker-naipes-probe-v1"}

UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                    "Mobile/15E148 Safari/604",
      "Referer": "https://replay.pppoker.net/"}


def get(url, limit=900_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(limit).decode("utf-8", "ignore")


# 1) última mão pppoker vista no banco -> JSON bruto do CDN
key = None
try:
    rows = (repo.client.table("bot_events").select("detail")
            .ilike("detail->>q", "%pppoker%")
            .order("created_at", desc=True).limit(3).execute().data) or []
    for row in rows:
        m = re.search(r"[?&]shareKey=([0-9a-zA-Z-]{12,})",
                      row["detail"].get("q", ""))
        if m:
            key = m.group(1)
            break
except Exception as exc:
    out["db_err"] = str(exc)[:140]
out["key"] = key or ""

if key:
    try:
        data = json.loads(get(
            f"https://alicdn.pppoker.club/review_hand/{key}.json"))
        info = data.get("info") or {}
        flow = data.get("flow") or {}
        out["hero_cards_raw"] = info.get("cards")
        out["board_raw"] = {k: (flow.get(k) or {}).get("cards")
                            for k in ("flop", "turn", "river")}
        # cartas reveladas de CADA jogador (showdown) — campos possíveis
        out["players_card_fields"] = [
            {kk: p.get(kk) for kk in p.keys()
             if "card" in kk.lower() or kk in ("user_name", "seatid")}
            for p in (info.get("players") or [])]
        out["winning_info"] = flow.get("winning_info") or data.get("winning_info")
        # qualquer outro campo com 'card'/'show' no flow (revelação no river?)
        extras = {}
        for sk, sv in flow.items():
            if isinstance(sv, dict):
                for kk, vv in sv.items():
                    if kk not in ("cards", "actions", "pools", "chips_back"):
                        extras[f"{sk}.{kk}"] = vv
        out["flow_extras"] = str(extras)[:800]
    except Exception as exc:
        out["cdn_err"] = str(exc)[:160]

# 2) o JS do replayer: procura o trecho que converte código -> naipe/sprite
try:
    html = get("https://replay.pppoker.net/new_game_record_publish/Frame/"
               "rls_20260624/index.html", 60_000)
    js_files = re.findall(r'src="([^"]+\.js)"', html)
    out["js_files"] = js_files[:8]
    snippets = []
    for jf in js_files:
        if any(x in jf for x in ("egret", "tween", "eui", "assetsmanager")):
            continue  # engine, não lógica do jogo
        url = jf if jf.startswith("http") else (
            "https://replay.pppoker.net/new_game_record_publish/Frame/"
            "rls_20260624/" + jf)
        try:
            js = get(url)
        except Exception:
            continue
        # âncoras: divisão/shift por 256 e nomes de naipe
        for pat in (r".{160}(?:>>\s*8|/\s*256|%\s*256).{160}",
                    r".{80}(?:spade|club|heart|diamond|hua_?se|naipe).{160}",
                    r".{80}(?:_1_|card_)\w*(?:png|Type|Res).{120}"):
            for mm in re.finditer(pat, js, re.IGNORECASE):
                s = mm.group(0)
                if s not in snippets:
                    snippets.append(s)
                if len(snippets) >= 14:
                    break
            if len(snippets) >= 14:
                break
    out["js_snippets"] = snippets[:14]
except Exception as exc:
    out["js_err"] = str(exc)[:160]

repo.log_event(0, None, "diag", {"src": "pppoker-naipes-probe-v1",
                                 "dados": json.dumps(out)[:9000]})
print("sonda de naipes despejada no bot_events")
PY
exit 0
