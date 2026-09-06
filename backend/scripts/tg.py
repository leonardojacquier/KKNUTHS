"""Opera a Bot API do Telegram a partir do VPS (replica o padrão Jarvis/GNHFIN).

Usa o token do .env do próprio servidor — nenhum segredo circula fora dele.

Uso (no VPS):
    cd /opt/poker-bot
    PYTHONPATH=. ./venv/bin/python scripts/tg.py me
    PYTHONPATH=. ./venv/bin/python scripts/tg.py chat <chat_id>
    PYTHONPATH=. ./venv/bin/python scripts/tg.py send <chat_id> <texto...>

IMPORTANTE: getUpdates NÃO é exposto de propósito — o bot no pm2 consome o
polling; um segundo consumidor roubaria as mensagens dele.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

from app.config import get_settings


def call(method: str, params: dict | None = None) -> dict:
    token = get_settings().telegram_bot_token
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN ausente no .env")
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params or {}).encode() if params else None
    with urllib.request.urlopen(url, data=data, timeout=20) as r:
        return json.load(r)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("me", "chat", "send"):
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd in ("chat", "send") and len(sys.argv) < 3:
        print(f"uso: tg.py {cmd} <chat_id>" + (" <mensagem>" if cmd == "send" else ""))
        return 1
    if cmd == "send" and len(sys.argv) < 4:
        print("uso: tg.py send <chat_id> <mensagem>")
        return 1

    if cmd == "me":
        out = call("getMe")
    elif cmd == "chat":
        out = call("getChat", {"chat_id": sys.argv[2]})
    else:  # send
        out = call(
            "sendMessage",
            {"chat_id": sys.argv[2], "text": " ".join(sys.argv[3:]), "parse_mode": "Markdown"},
        )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
