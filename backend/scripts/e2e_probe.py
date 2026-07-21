"""Sonda E2E — a conta-teste USA o bot de verdade pelo Telegram (camada 3).

Fecha a única zona cega que sobrou: a fiação do Telegram (foto que não
chega, botão que morre, "no text to edit"). A cada deploy (+ cron diário) a
conta-teste percorre o funil inteiro como um usuário:

  1. /start           -> resposta com botões
  2. cola um hand history sintético -> análise chega ("mão(s) lidas")
  3. /range btn       -> chega FOTO
  4. /treino          -> drill com botões -> clica -> reveal chega
  5. /simular         -> passo com botões -> Fold -> encerramento chega

DORME em silêncio se E2E_API_ID/E2E_API_HASH/E2E_SESSION não estiverem no
.env. Resultado -> bot_events (event='e2e'); FALHA -> avisa o admin no
Telegram. A conta-teste é um usuário normal pro bot (fica fora de qualquer
estatística humana por ser conhecida no evento).
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ADMIN_ID = 6452742024
BOT = "KKNUts_BOT"
SAMPLE = Path(__file__).resolve().parent.parent / "tests" / "sample_hands" / \
    "gg_tournament_paste.txt"


def _notify_admin(text: str) -> None:
    from app.config import get_settings

    token = get_settings().telegram_bot_token
    if not token:
        return
    body = json.dumps({"chat_id": ADMIN_ID, "text": text[:4000]}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


async def _run(api_id: int, api_hash: str, session: str) -> list[tuple[str, bool, str]]:
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    results: list[tuple[str, bool, str]] = []

    async def step(conv, name: str, send: str, expect_media: bool = False,
                   click: int | None = None, timeout: int = 90,
                   contains: str = ""):
        """Manda `send`, espera resposta; opcionalmente clica no 1º teclado."""
        try:
            await conv.send_message(send)
            resp = await conv.get_response(timeout=timeout)
            # pula mensagens intermediárias ("Recebido. Analisando…")
            for _ in range(4):
                ok_media = (not expect_media) or bool(resp.photo)
                ok_text = (not contains) or (contains.lower() in
                                             (resp.raw_text or "").lower())
                if ok_media and ok_text and (click is None or resp.buttons):
                    break
                resp = await conv.get_response(timeout=timeout)
            problema = ""
            if expect_media and not resp.photo:
                problema = "esperava FOTO e veio só texto"
            if contains and contains.lower() not in (resp.raw_text or "").lower():
                problema = (problema + "; " if problema else "") + \
                    f"faltou '{contains}' na resposta"
            if click is not None:
                if not resp.buttons:
                    problema = (problema + "; " if problema else "") + \
                        "sem botões pra clicar"
                else:
                    await resp.click(click)
                    follow = await conv.get_response(timeout=timeout)
                    if not (follow.raw_text or follow.photo):
                        problema = (problema + "; " if problema else "") + \
                            "clique sem resposta"
            results.append((name, not problema, problema))
        except asyncio.TimeoutError:
            results.append((name, False, f"timeout ({timeout}s) sem resposta"))
        except Exception as exc:
            results.append((name, False, str(exc)[:120]))

    client = TelegramClient(StringSession(session), api_id, api_hash)
    await client.start()
    try:
        async with client.conversation(BOT, timeout=100) as conv:
            await step(conv, "start", "/start")
            if SAMPLE.exists():
                await step(conv, "upload_texto",
                           SAMPLE.read_text()[:3500],
                           contains="lidas", timeout=120)
            await step(conv, "range_foto", "/range btn", expect_media=True)
            await step(conv, "treino_clique", "/treino", click=0)
            await step(conv, "simular_fold", "/simular", click=0)
    finally:
        await client.disconnect()
    return results


def _env(key: str) -> str | None:
    """Variável do ambiente OU do .env do app (cron não exporta o .env)."""
    v = os.getenv(key)
    if v:
        return v
    envf = Path(__file__).resolve().parent.parent / ".env"
    try:
        for line in envf.read_text().splitlines():
            if line.strip().startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def main() -> int:
    api_id = _env("E2E_API_ID")
    api_hash = _env("E2E_API_HASH")
    session = _env("E2E_SESSION")
    if not (api_id and api_hash and session):
        print("e2e dormindo (sem credenciais no .env)")
        return 0
    try:
        import telethon  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "telethon"], check=True)

    results = asyncio.run(_run(int(api_id), api_hash, session))
    falhas = [(n, p) for n, ok, p in results if not ok]

    from app.db import get_repository

    get_repository().log_event(0, None, "e2e", {
        "passos": len(results), "falhas": len(falhas),
        "detalhe": [{"passo": n, "ok": ok, "problema": p}
                    for n, ok, p in results]})
    if falhas:
        _notify_admin("🚨 E2E do Telegram FALHOU:\n" + "\n".join(
            f"• {n}: {p}" for n, p in falhas))
    print("e2e:", "; ".join(f"{n}={'OK' if ok else 'FALHA'}"
                            for n, ok, _ in results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
