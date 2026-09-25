#!/usr/bin/env bash
# O ng-state tem a resposta da API cacheada. Falta ver os VALORES.
#
#   "371745488": {"u": str(40), "b": {"data": str(672)}, "s": 200, "st": "OK"}
#
# `u` é a URL que o app chamou (40 chars) e `b.data` é o corpo (672 chars).
# O esqueleto esconde valor de propósito — aqui eu quero exatamente o valor.
#
# 672 chars é POUCO para uma mão inteira: ou vem codificado/comprimido, ou é
# um envelope com ponteiro para o resto. As duas hipóteses se separam
# olhando o conteúdo, então este oneshot tenta decodificar antes de opinar.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import base64, gzip, json, re, sys, urllib.request
sys.path.insert(0, "scripts")
from farejar_e_reportar import _enviar, em_blocos
from sniff_replay import _UA_MOBILE, desembrulhar, esqueleto, parece_mao

LINK = ("https://my.pokercraft.com/embedded/shared/hand-replay/"
        "_8gph8vo-nrui3C92ZH4A")

req = urllib.request.Request(LINK, headers=_UA_MOBILE)
with urllib.request.urlopen(req, timeout=25) as r:
    html = r.read(4_000_000).decode("utf-8", "replace")

m = re.search(r"""<script id=["']ng-state["'][^>]*>(.*?)</script>""",
              html, re.I | re.S)
if not m:
    _enviar("ng-state sumiu da página — o HTML mudou")
    raise SystemExit(0)

estado = json.loads(m.group(1))
partes = [f"ng-state: {len(m.group(1))} chars, "
          f"chaves de topo: {list(estado)[:6]}"]

for chave, val in estado.items():
    if not isinstance(val, dict) or "b" not in val:
        continue
    partes.append(f"\n== entrada {chave} ==")
    partes.append(f"URL chamada (u): {val.get('u')!r}")
    partes.append(f"status: {val.get('s')} {val.get('st')} "
                  f"· responseType: {val.get('rt')}")
    corpo = val.get("b")
    partes.append(f"corpo (b): {type(corpo).__name__} "
                  + (f"chaves {list(corpo)[:8]}" if isinstance(corpo, dict)
                     else f"{len(str(corpo))} chars"))

    # o valor cru, que é o que interessa
    dado = corpo.get("data") if isinstance(corpo, dict) else corpo
    if isinstance(dado, str):
        partes.append(f"\nb.data CRU ({len(dado)} chars):\n{dado}")
        for nome, tentativa in (
                ("base64", lambda: base64.b64decode(dado + "==", validate=False)),
                ("base64+gzip", lambda: gzip.decompress(
                    base64.b64decode(dado + "==", validate=False)))):
            try:
                bruto = tentativa()
            except Exception:
                continue
            amostra = bruto[:600]
            legivel = amostra.decode("utf-8", "replace")
            partes.append(f"\ndecodificado como {nome} "
                          f"({len(bruto)} bytes):\n{legivel}")
            break

    for d in desembrulhar(val):
        partes.append(f"\nDENTRO (pontos {parece_mao(d)}):\n"
                      + json.dumps(esqueleto(d), ensure_ascii=False)[:1500])

texto = "\n".join(partes)
for i, b in enumerate(em_blocos(texto), 1):
    _enviar(f"[ng {i}]\n{b}")
print(texto[:4000])
PY

exit 0
