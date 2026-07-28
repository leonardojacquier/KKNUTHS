#!/usr/bin/env bash
# "/quem não tá funcionando" — e ele falha em SILÊNCIO, que é o pior modo.
#
# Três causas possíveis, e todas dão exatamente a mesma tela (nenhuma):
#   1. ADMIN_TELEGRAM_ID no .env do VPS != 6452742024 -> o guard retorna sem
#      responder, e o dono fica achando que o bot ignorou o comando;
#   2. `relatorio_do_mes` levanta exceção -> handler morre calado;
#   3. Markdown quebrado (apelido com `_` ou `*`) -> o Telegram RECUSA a
#      mensagem inteira e nada chega.
#
# Este roda o relatório com o ambiente REAL do servidor e manda o resultado.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN
ADMIN_NO_ENV=$(grep -m1 '^ADMIN_TELEGRAM_ID=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export ADMIN_NO_ENV

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json, os, traceback, urllib.request

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = 6452742024


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


partes = []
try:
    from app.quota import ADMIN_TELEGRAM_ID

    no_env = os.environ.get("ADMIN_NO_ENV") or "(não definido no .env)"
    partes.append(f"ADMIN_TELEGRAM_ID em uso: {ADMIN_TELEGRAM_ID}")
    partes.append(f"ADMIN_TELEGRAM_ID no .env: {no_env}")
    if ADMIN_TELEGRAM_ID != CHAT:
        partes.append("⚠️ NÃO BATE com o chat do dono — é esta a causa: o "
                      "guard do comando retorna sem responder nada.")

    from app.agent.custo import relatorio_do_mes

    txt = relatorio_do_mes(None)
    partes.append(f"\nrelatorio_do_mes: OK, {len(txt)} chars")

    ruins = [c for c in "_*[]`" if c in txt]
    if ruins:
        partes.append(f"⚠️ caracteres que podem quebrar o Markdown: {ruins} "
                      "— o Telegram recusa a mensagem INTEIRA e nada chega")

    # tenta enviar do jeito que o comando envia
    corpo = json.dumps({"chat_id": CHAT, "text": txt[:3800],
                        "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=corpo,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            json.loads(r.read())
        partes.append("envio COM Markdown: ok (o relatório chegou acima)")
    except Exception as exc:
        partes.append(f"envio COM Markdown FALHOU: {exc}")
        partes.append("-> é o Markdown. O _safe_reply novo cai pra texto puro.")
except Exception:
    partes.append("EXCEÇÃO:\n" + traceback.format_exc()[-1500:])

diga("[quem?]\n" + "\n".join(partes))
PY

exit 0
