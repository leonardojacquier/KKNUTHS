"""Login ÚNICO da conta-teste do E2E (roda uma vez, interativo).

Pré-requisitos (conta de Telegram SEPARADA, só pra teste):
  1. entrar em https://my.telegram.org com o número da conta-teste
     -> API development tools -> criar app -> copiar api_id e api_hash
  2. na VPS:  cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/e2e_login.py
     (pede api_id, api_hash, telefone e o código que chega no Telegram)
  3. colar as 3 linhas impressas no /opt/poker-bot/.env e rodar o deploy.

A sessão NUNCA vai pro repositório — vive só no .env da VPS.
"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    try:
        from telethon.sessions import StringSession
        from telethon.sync import TelegramClient
    except ImportError:
        print("instalando telethon…")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "telethon"], check=True)
        from telethon.sessions import StringSession
        from telethon.sync import TelegramClient

    api_id = int(input("api_id da conta-teste: ").strip())
    api_hash = input("api_hash: ").strip()
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session = client.session.save()
        me = client.get_me()
    print("\n✅ logado como", me.first_name, f"(id {me.id})")
    print("\nCole no /opt/poker-bot/.env:\n")
    print(f"E2E_API_ID={api_id}")
    print(f"E2E_API_HASH={api_hash}")
    print(f"E2E_SESSION={session}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
