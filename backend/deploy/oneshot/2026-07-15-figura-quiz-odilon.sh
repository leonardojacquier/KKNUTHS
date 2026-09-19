#!/usr/bin/env bash
# Envia ao Odilon (6104620007) um exemplo do quiz NOVO — figura da mesa +
# narração em ordem — e pede feedback. Roda uma vez no deploy.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import io
import urllib.request
import uuid

from app.bot.processing import build_drill
from app.config import get_settings

ODILON = 6104620007
token = get_settings().telegram_bot_token
if not token:
    raise SystemExit("sem token")


def send_message(chat, text):
    import json
    import urllib.parse
    data = urllib.parse.urlencode(
        {"chat_id": chat, "text": text, "parse_mode": "Markdown"}).encode()
    urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20)


def send_photo(chat, png, caption):
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("chat_id", str(chat)), ("caption", caption),
                 ("parse_mode", "Markdown")):
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n")
    body = b"".join(p.encode() for p in parts)
    body += (f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; "
             f"filename=\"quiz.png\"\r\nContent-Type: image/png\r\n\r\n").encode()
    body += png + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    urllib.request.urlopen(req, timeout=30)


# monta um treino real das mãos do Odilon
drill = build_drill(ODILON)
sent_fig = False
if drill:
    try:
        from app.analysis.hand_figure import render_hand_figure, spot_from_drill
        png = render_hand_figure(spot_from_drill(drill))
        cap = "🎯 *Treino* — mão real sua"
        if drill.get("story"):
            cap += "\n\n" + drill["story"]
        cap += "\n\n👉 *O que você faz?*"
        send_photo(ODILON, png, cap[:1000])
        sent_fig = True
    except Exception as exc:
        print("figura falhou:", exc)

msg = (
    "E aí, Odilon! 👋 Fiz um ajuste no *Treino/Quiz* e queria muito tua "
    "opinião.\n\n"
    "Duas mudanças:\n"
    "1️⃣ A *sequência das ações* agora vem em ordem certa (começa no primeiro "
    "a agir) e mais limpa — sem aquela bagunça de antes.\n"
    "2️⃣ Manda junto uma *figura da mesa* com as cartas, o board, os stacks e "
    "o pote — pra bater o olho e já entender o spot"
    + (" (mandei um exemplo aí em cima ☝️)." if sent_fig else ".") +
    "\n\nTesta com /treino aí e me diz: *ficou mais fácil de ler?* O que "
    "melhora? Teu feedback vale ouro pra gente. 🙏")
send_message(ODILON, msg)
print("enviado ao Odilon; figura:", sent_fig)
PY
exit 0
