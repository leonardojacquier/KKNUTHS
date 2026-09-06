#!/usr/bin/env bash
# Segunda passada na PokerCraft, com o farejador corrigido.
#
# A primeira rodada resolveu o encurtador (gg.gl -> my.pokercraft.com) mas
# achou 0 endpoints. Duas cegueiras minhas explicam:
#   1. só varria URL ABSOLUTA — o app monta a URL a partir da origem
#      (`fetch(BASE + "/api/...")`), e o bundle inteiro tinha 2 URLs
#      absolutas, nenhuma da API;
#   2. o extrator de JSON embutido parava nos 8 primeiros achados, e
#      objeto pequeno de configuração enchia as vagas antes da mão.
#
# A página tem 85 KB (a da Suprema tinha 3,7 KB): dado embutido é a
# hipótese principal, não a API.
set -uo pipefail
cd /opt/poker-bot || exit 1

LINK="https://my.pokercraft.com/embedded/shared/hand-replay/_8gph8vo-nrui3C92ZH4A"

PYTHONPATH=/opt/poker-bot ./venv/bin/python \
    scripts/farejar_e_reportar.py "$LINK"

# Rede de segurança: se o farejador ainda não achar, a resposta está no
# HTML salvo. Mando os pedaços que interessam em vez de 85 KB inteiros.
PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json, pathlib, re, sys
sys.path.insert(0, "scripts")
from farejar_e_reportar import _enviar, em_blocos

p = pathlib.Path("/tmp/replay_sniff/pagina.html")
if not p.exists():
    _enviar("página não foi salva — ver /tmp/replay_sniff/")
    raise SystemExit(0)

html = p.read_text(errors="replace")
partes = [f"pagina.html: {len(html)} chars"]

# tags de dado embutido
for m in re.finditer(r"<script([^>]*)>", html, re.I):
    attrs = m.group(1).strip()
    if attrs and "src=" not in attrs.lower():
        partes.append(f"<script {attrs[:120]}>")

# nomes de estado global (window.__X__ = ...)
partes += [f"estado: {m.group(1)}" for m in
           re.finditer(r"(window\.__[A-Z_]+__|self\.__[A-Z_]+)", html)][:10]

# os maiores blobs JSON, por esqueleto
from sniff_replay import _blobs_json, esqueleto, parece_mao
for i, b in enumerate(_blobs_json(html)[:4], 1):
    partes.append(f"\n── blob {i} (pontos {parece_mao(b)})\n"
                  + json.dumps(esqueleto(b), ensure_ascii=False)[:1200])

texto = "\n".join(partes)
for i, bloco in enumerate(em_blocos(texto), 1):
    _enviar(f"[html {i}]\n{bloco}")
PY

exit 0
