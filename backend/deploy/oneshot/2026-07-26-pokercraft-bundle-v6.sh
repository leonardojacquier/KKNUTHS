#!/usr/bin/env bash
# Quais OUTRAS chamadas o app faz?
#
# Evidência de que meu varredor vê pouco: ele reportou UM caminho relativo
# (/api/script) e o app comprovadamente chama /api/share/alias — que só
# apareceu porque estava gravado no ng-state. Se ele perdeu esse, perdeu
# outros. O ng-state guarda só o que o SERVIDOR renderizou; requisição feita
# depois, no navegador, não está lá.
#
# Então: baixo o bundle e procuro o vocabulário de rota (share, alias, api,
# hand, replay) com contexto, além de todo literal com cara de caminho.
# Autossuficiente e reporta a própria exceção (lição do v4).
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

./venv/bin/python - <<'PY'
import json, os, re, sys, traceback, urllib.request

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = 6452742024
BASE = "https://my.pokercraft.com"
BUNDLE = BASE + "/embedded/shared/hand-replay/main-464FIGUI.js"
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


def principal():
    req = urllib.request.Request(BUNDLE, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        js = r.read(20_000_000).decode("utf-8", "replace")
    partes = [f"bundle: {len(js)} chars"]

    # 1. o endpoint que já conhecemos aparece aqui? se não, ele é montado
    for termo in ("share/alias", "/api/share", "alias", "hand-replay",
                  "decrypt", "AES", "crypto", "subtle", "CryptoJS"):
        n = len(re.findall(re.escape(termo), js, re.I))
        partes.append(f"  «{termo}»: {n} ocorrência(s)")

    # 2. contexto de cada termo de ROTA (é onde a URL da 2ª chamada estaria)
    for termo in ("share/alias", "/api/share", "alias"):
        for m in list(re.finditer(re.escape(termo), js, re.I))[:3]:
            partes.append(f"\n── «{termo}» em {m.start()}\n"
                          + js[max(0, m.start() - 220):m.start() + 260]
                          .replace("\n", " "))

    # 3. TODO literal com cara de caminho, sem exigir palavra-chave — foi o
    #    filtro por palavra-chave que perdeu /api/share/alias
    caminhos = sorted({m.group(1) for m in
                       re.finditer(r"""['"](/[a-zA-Z0-9_./-]{3,60})['"]""", js)
                       if not re.search(r"\.(js|css|png|svg|woff2?)$",
                                        m.group(1), re.I)})
    partes.append(f"\n== literais de caminho ({len(caminhos)}) ==")
    partes += [f"  {c}" for c in caminhos[:60]]
    return "\n".join(partes)


try:
    diga("[bundle]\n" + principal())
except Exception:
    diga("[bundle] EXCEÇÃO:\n" + traceback.format_exc()[-2500:])
PY

exit 0
