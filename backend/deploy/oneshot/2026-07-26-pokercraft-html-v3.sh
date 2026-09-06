#!/usr/bin/env bash
# A mão ESTÁ nesses 85 KB de HTML? Pergunta binária, resposta direta.
#
# O farejador achou 0 blobs com cara de mão, mas ele exige JSON ESTRITO —
# objeto JS minificado (chave sem aspas, aspas simples) é rejeitado pelo
# json.loads. Antes de inventar outra teoria, procuro no HTML CRU as
# palavras que só existem numa mão de poker.
#
# Também baixa /api/script, que é um endpoint servindo SCRIPT — nome
# estranho o bastante para merecer um olhar.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json, re, sys, urllib.request
sys.path.insert(0, "scripts")
from farejar_e_reportar import _enviar, em_blocos
from sniff_replay import _UA_MOBILE

BASE = "https://my.pokercraft.com"
LINK = BASE + "/embedded/shared/hand-replay/_8gph8vo-nrui3C92ZH4A"

def pega(u):
    try:
        req = urllib.request.Request(u, headers={**_UA_MOBILE,
                                                 "Referer": LINK})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read(4_000_000).decode("utf-8", "replace")
    except Exception as exc:
        return f"(falhou: {exc})"

html = pega(LINK)
partes = [f"pagina: {len(html)} chars"]

# 1. a mão está aqui? procuro o vocabulário que só existe em poker
TERMOS = ("holeCard", "holecards", "seatId", "smallBlind", "bigBlind",
          "potSize", "communityCard", "showdown", "handId", "winAmount",
          "cardId", "suit", "rank", "blinds", "playerName", "stackSize")
achou = []
for t in TERMOS:
    for m in re.finditer(re.escape(t), html, re.I):
        achou.append(f"«{t}» em {m.start()}: "
                     + html[max(0, m.start()-90):m.start()+160]
                     .replace("\n", " "))
        break
partes.append(f"\n== termos de poker no HTML: {len(achou)}/{len(TERMOS)}")
partes += achou[:8]

# 2. como cada <script> se apresenta (sem despejar o conteúdo)
partes.append("\n== tags de script ==")
for m in re.finditer(r"<script([^>]*)>", html, re.I):
    a = m.group(1).strip()
    partes.append(f"  <script {a[:150]}>" if a else "  <script> (inline)")

# 3. estado global e trechos grandes entre chaves (mesmo sem ser JSON válido)
partes.append("\n== estado global ==")
partes += sorted({m.group(1) for m in re.finditer(
    r"(window\.[A-Za-z_$][\w$]*|self\.__[A-Z_]+)", html)})[:15] or ["(nenhum)"]

# 4. /api/script — endpoint servindo script é nome estranho o bastante
s = pega(BASE + "/api/script")
partes.append(f"\n== /api/script: {len(s)} chars ==")
partes.append(s[:900])

texto = "\n".join(partes)
for i, b in enumerate(em_blocos(texto), 1):
    _enviar(f"[pc {i}]\n{b}")
print(texto[:4000])
PY

exit 0
