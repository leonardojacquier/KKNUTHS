"""Quiz diário — o loop de retenção nº 1 (roadmap T3/2026 do business plan).

Todo dia (cron 19h) manda para cada usuário com histórico um spot REAL das
mãos dele com botões Fold/Call/Raise. A resposta é processada pelo bot
(handler drill:*), que busca o drill pendente no banco.

Cron:  0 19 * * *  cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/daily_quiz.py
"""
from __future__ import annotations

import json
import sys
import urllib.request

from app.bot.processing import build_drill
from app.config import get_settings
from app.db import get_repository


def send_quiz(token: str, chat_id: int, drill: dict) -> bool:
    from app.bot.processing import drill_buttons, drill_message

    text = drill_message(drill)
    if drill.get("streak_line"):
        text += "\n\n" + drill["streak_line"]
    keyboard = {"inline_keyboard": drill_buttons(drill)}
    body = json.dumps({
        "chat_id": chat_id, "text": text, "parse_mode": "Markdown",
        "reply_markup": keyboard,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("ok", False)
    except Exception:
        return False


def main() -> int:
    settings = get_settings()
    repo = get_repository()
    if not settings.telegram_bot_token or not repo.enabled:
        print("ERRO: precisa de TELEGRAM_BOT_TOKEN e Supabase configurados.")
        return 1

    users = repo.client.table("users").select("telegram_id").execute().data or []
    sent = 0
    for u in users:
        tg = u["telegram_id"]
        drill = build_drill(tg)   # usa o histórico do banco
        if not drill:
            continue
        # streak no convite: quem tem corrente não quer perder
        try:
            streak = repo.quiz_streak_days(tg)
            if streak >= 2:
                drill["streak_line"] = (f"🔥 Você está em {streak} dias seguidos "
                                        "— responde pra manter a corrente!")
        except Exception:
            pass
        repo.set_pending_drill(tg, drill)
        if send_quiz(settings.telegram_bot_token, tg, drill):
            repo.log_event(tg, None, "daily_quiz_sent", {"hand_id": drill.get("hand_id")})
            sent += 1
    print(f"Quiz enviado para {sent}/{len(users)} usuários.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
