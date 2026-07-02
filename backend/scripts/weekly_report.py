"""Relatório semanal automático — enviar via cron (ex.: domingo 18h).

Para cada usuário com mãos nos últimos 7 dias: perfil atualizado, resultado da
semana e o "leak da semana" (maior perda). Envia direto pela API HTTP do Telegram.

Cron sugerido:  0 18 * * 0  cd /app/backend && PYTHONPATH=. python3 scripts/weekly_report.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from app.agent import analyze_hand
from app.analysis import compute_player_stats
from app.config import get_settings
from app.db import get_repository


def send_message(token: str, chat_id: int, text: str) -> bool:
    data = json.dumps(
        {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
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

    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    users = repo.client.table("users").select("*").execute().data or []
    sent = 0

    for user in users:
        rows = (
            repo.client.table("hands")
            .select("canonical")
            .eq("user_id", user["id"])
            .gte("played_at", week_ago)
            .execute()
        ).data or []
        if not rows:
            continue

        from app.models.canonical import CanonicalHand

        hands = []
        for r in rows:
            try:
                hands.append(CanonicalHand.model_validate(r["canonical"]))
            except Exception:
                continue
        if not hands:
            continue

        stats = compute_player_stats(hands, player=None)
        analyses = [analyze_hand(h) for h in hands if h.hero]
        net_bb = round(sum(a["net_bb"] for a in analyses), 1)
        worst = min(analyses, key=lambda a: a["net_bb"], default=None)

        text = (
            "📅 *Seu resumo da semana*\n\n"
            f"• Mãos analisadas: {len(hands)}\n"
            f"• Resultado: {net_bb:+.1f} BB\n"
            f"• VPIP {stats.vpip}% | PFR {stats.pfr}% | AF {stats.af}\n"
        )
        if worst and worst["net_bb"] < 0:
            text += (
                f"\n🔍 *Leak da semana* ({worst['net_bb']:+.1f} BB):\n_{worst['summary']}_\n"
            )
        text += "\nEnvie novas mãos para continuar evoluindo. ♠️"

        if send_message(settings.telegram_bot_token, user["telegram_id"], text):
            sent += 1

    print(f"Relatórios enviados: {sent}/{len(users)} usuários.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
