#!/usr/bin/env bash
# Os CHUNKS. O print do DevTools do admin mostrou o que minha varredura não via:
#
#   <link rel="modulepreload" href="chunk-UX76QKQI.js">
#   <link rel="modulepreload" href="chunk-DDE4YXTD.js">
#   <link rel="modulepreload" href="chunk-FNHOYFV4.js">
#
# App Angular dividido em pedaços declara os chunks como <link>, não como
# <script src> — e eu só olhava <script src>. Baixei o main-*.js, não achei
# `/api/share/alias`, e conclui que a rota era montada dinamicamente. Estava
# escrita, noutro arquivo que eu nunca abri.
#
# Aqui: baixa TODOS os .js referenciados pela página e procura em cada um.
# Autossuficiente, reporta a própria exceção (lição do v4).
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

./venv/bin/python - <<'PY'
import json, os, re, sys, traceback, urllib.request
from urllib.parse import urljoin

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = 6452742024
LINK = ("https://my.pokercraft.com/embedded/shared/hand-replay/"
        "_8gph8vo-nrui3C92ZH4A")
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/150.0.0.0 Safari/537.36"), "Accept": "*/*"}


def diga(t):
    print(t)
    if not TOKEN:
        return
    for i in range(0, len(t), 3800):
        c = json.dumps({"chat_id": CHAT, "text": t[i:i + 3800]}).encode()
        r = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=c,
            headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(r, timeout=25)
        except Exception as exc:
            print(f"(envio falhou: {exc})")


def pega(u):
    req = urllib.request.Request(u, headers={**UA, "Referer": LINK})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(20_000_000).decode("utf-8", "replace")


ROTAS = ("share/alias", "/api/share", "hand-replay", "handreplay",
         "/api/hand", "replay/detail", "shared/hand")
CRIPTO = ("decrypt", "AES", "crypto.subtle", "CryptoJS", "cipher",
          "fromCharCode", "atob(", "hex")


def principal():
    html = pega(LINK)
    arquivos = [urljoin(LINK, m.group(1)) for m in re.finditer(
        r"""<script[^>]+src=['"]([^'"]+\.js[^'"]*)['"]""", html, re.I)]
    arquivos += [urljoin(LINK, m.group(1)) for m in re.finditer(
        r"""<link[^>]*(?:modulepreload|preload)[^>]*href=['"]([^'"]+\.js[^'"]*)['"]""",
        html, re.I)]
    arquivos += [urljoin(LINK, m.group(1)) for m in re.finditer(
        r"""<link[^>]*href=['"]([^'"]+\.js[^'"]*)['"][^>]*(?:modulepreload|preload)""",
        html, re.I)]
    # chunks costumam ser citados dentro do próprio bundle também
    arquivos = list(dict.fromkeys(a for a in arquivos
                                  if "newrelic" not in a.lower()))
    partes = [f"{len(arquivos)} arquivo(s) .js na página:"]
    partes += [f"  {a}" for a in arquivos]

    todos = {}
    for a in arquivos[:14]:
        try:
            todos[a] = pega(a)
        except Exception as exc:
            partes.append(f"  ! {a.split('/')[-1]}: {exc}")

    for nome, js in todos.items():
        curto = nome.split("/")[-1]
        achou_rota = {t: len(re.findall(re.escape(t), js, re.I))
                      for t in ROTAS}
        achou_cripto = {t: len(re.findall(re.escape(t), js, re.I))
                        for t in CRIPTO}
        partes.append(f"\n== {curto} ({len(js)} chars) ==")
        r = {k: v for k, v in achou_rota.items() if v}
        c = {k: v for k, v in achou_cripto.items() if v}
        partes.append(f"  rota:   {r or '(nada)'}")
        partes.append(f"  cripto: {c or '(nada)'}")
        for termo in [k for k, v in achou_rota.items() if v][:3]:
            m = re.search(re.escape(termo), js, re.I)
            partes.append(f"\n  ── «{termo}»\n  "
                          + js[max(0, m.start() - 250):m.start() + 300]
                          .replace("\n", " "))

    caminhos = set()
    for js in todos.values():
        caminhos |= {m.group(1) for m in
                     re.finditer(r"""['"](/[a-zA-Z0-9_./-]{4,60})['"]""", js)
                     if not re.search(r"\.(js|css|png|svg|woff2?)$",
                                      m.group(1), re.I)}
    partes.append(f"\n== literais de caminho em TODOS os js ({len(caminhos)}) ==")
    partes += [f"  {c}" for c in sorted(caminhos)[:70]]
    return "\n".join(partes)


try:
    diga("[chunks]\n" + principal())
except Exception:
    diga("[chunks] EXCEÇÃO:\n" + traceback.format_exc()[-2500:])
PY

exit 0
