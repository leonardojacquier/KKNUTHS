"""Envia um DOCUMENTO (PDF etc.) pelo bot do Telegram — multipart, sem deps.

Uso: python scripts/tg_send_doc.py <chat_id> <caminho_do_arquivo> [legenda...]
"""
from __future__ import annotations

import json
import mimetypes
import sys
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402


def send_document(chat_id: str, path: Path, caption: str = "") -> dict:
    token = get_settings().telegram_bot_token
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN ausente")

    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    def field(name: str, value: str) -> bytes:
        return (f"--{boundary}\r\nContent-Disposition: form-data; "
                f"name=\"{name}\"\r\n\r\n{value}\r\n").encode()

    body = field("chat_id", chat_id)
    if caption:
        body += field("caption", caption[:1024])
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; "
             f"filename=\"{path.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
    body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    out = send_document(sys.argv[1], Path(sys.argv[2]), " ".join(sys.argv[3:]))
    print(json.dumps({"ok": out.get("ok"),
                      "message_id": (out.get("result") or {}).get("message_id")}))
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
