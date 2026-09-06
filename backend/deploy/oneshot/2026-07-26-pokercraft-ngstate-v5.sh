#!/usr/bin/env bash
# v5 — o v4 não mandou NADA, nem erro. Culpa do desenho, não do alvo.
#
# Meus oneshots terminam em `exit 0` e não usam `set -e`: se o Python
# quebra, o deploy marca a tarefa como concluída, nada chega no Telegram e
# ela nunca mais roda. Diagnóstico que falha em silêncio é pior que nenhum —
# é o mesmo defeito do `-1` da Suprema, agora do meu lado.
#
# Este é AUTOSSUFICIENTE de propósito:
#   • só biblioteca padrão (nada de importar módulo meu, que é uma das
#     hipóteses de falha do v4);
#   • token lido direto do .env, sem app.config;
#   • TODA exceção vira mensagem no Telegram, com traceback.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
if [ -z "${TG_TOKEN:-}" ]; then
    echo "sem TELEGRAM_BOT_TOKEN no .env — só saída local"
fi
export TG_TOKEN

./venv/bin/python - <<'PY'
import base64, gzip, json, os, re, sys, traceback, urllib.request

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = 6452742024
LINK = ("https://my.pokercraft.com/embedded/shared/hand-replay/"
        "_8gph8vo-nrui3C92ZH4A")
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/150.0.0.0 Safari/537.36"),
      "Accept": "*/*"}


def diga(texto):
    print(texto)
    if not TOKEN:
        return
    for i in range(0, len(texto), 3800):
        corpo = json.dumps({"chat_id": CHAT,
                            "text": texto[i:i + 3800]}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data=corpo, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=25)
        except Exception as exc:
            print(f"(falha ao enviar: {exc})")


def principal():
    req = urllib.request.Request(LINK, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read(4_000_000).decode("utf-8", "replace")

    m = re.search(r"""<script id=["']ng-state["'][^>]*>(.*?)</script>""",
                  html, re.I | re.S)
    if not m:
        return "ng-state não está mais na página"

    cru = m.group(1).strip()
    partes = [f"ng-state: {len(cru)} chars"]
    estado = json.loads(cru)

    for chave, val in estado.items():
        if not isinstance(val, dict):
            continue
        partes.append(f"\n== {chave} ==")
        partes.append(f"u  = {val.get('u')!r}")
        partes.append(f"s  = {val.get('s')}  st = {val.get('st')!r}  "
                      f"rt = {val.get('rt')!r}")
        corpo = val.get("b")
        if isinstance(corpo, dict):
            partes.append(f"b  = dict, chaves {list(corpo)[:10]}")
        dado = corpo.get("data") if isinstance(corpo, dict) else corpo
        if not isinstance(dado, str):
            partes.append(f"b  = {type(dado).__name__}: "
                          + json.dumps(dado, ensure_ascii=False)[:1200])
            continue
        partes.append(f"\nb.data CRU ({len(dado)} chars):\n{dado}")
        try:
            bruto = base64.b64decode(dado + "==", validate=False)
        except Exception as exc:
            partes.append(f"(não é base64: {exc})")
            continue
        partes.append(f"\nbase64 -> {len(bruto)} bytes; "
                      f"primeiros: {bruto[:24].hex()}")
        try:
            bruto = gzip.decompress(bruto)
            partes.append(f"gzip -> {len(bruto)} bytes")
        except Exception:
            pass
        partes.append("\ncomo texto:\n"
                      + bruto[:1500].decode("utf-8", "replace"))
    return "\n".join(partes)


try:
    diga("[ng5]\n" + principal())
except Exception:
    diga("[ng5] EXCEÇÃO — era isto que o v4 engolia:\n\n"
         + traceback.format_exc()[-3000:])
PY

exit 0
