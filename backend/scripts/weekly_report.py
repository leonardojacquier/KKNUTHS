"""Relatório semanal automático — enviar via cron (ex.: domingo 18h).

Para cada usuário com mãos nos últimos 7 dias: perfil atualizado, resultado da
semana e o "leak da semana" (maior perda). Envia direto pela API HTTP do Telegram.

Cron sugerido:  0 18 * * 0  cd /opt/poker-bot && PYTHONPATH=. python3 scripts/weekly_report.py
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
        # placar do QUIZ da semana (retenção): respondidos, acertos, streak
        quiz_block = ""
        try:
            ev = (repo.client.table("bot_events").select("event,detail")
                  .eq("telegram_id", user["telegram_id"])
                  .gte("created_at", week_ago)
                  .in_("event", ["drill_answer", "drill_verdict"])
                  .execute()).data or []
            respondidos = sum(1 for e in ev if e["event"] == "drill_answer")
            boas = sum(1 for e in ev if e["event"] == "drill_verdict"
                       and (e.get("detail") or {}).get("verdict") == "boa")
            if respondidos:
                streak = repo.quiz_streak_days(user["telegram_id"])
                quiz_block = (f"\n🎯 *Placar do quiz*: {respondidos} respondidos, "
                              f"{boas} decisões boas")
                if streak >= 2:
                    quiz_block += f" · 🔥 {streak} dias seguidos"
                quiz_block += "\n"
        except Exception:
            quiz_block = ""

        rows = (
            repo.client.table("hands")
            .select("canonical")
            .eq("user_id", user["id"])
            .gte("played_at", week_ago)
            .execute()
        ).data or []
        if not rows and not quiz_block:
            continue
        if not rows:
            # semana só de quiz: manda o placar mesmo assim (retenção)
            text = ("📅 *Seu resumo da semana*\n" + quiz_block +
                    "\nEnvie novas mãos para o resumo completo. ♠️")
            if send_message(settings.telegram_bot_token,
                            user["telegram_id"], text):
                sent += 1
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

        # mesmos números do /stats (bayes-corrigidos): o resumo semanal não
        # pode contradizer o que o comando mostra no mesmo dia
        vpip, pfr, af = stats.vpip, stats.pfr, stats.af
        if settings.bayes_stats:
            try:
                from app.analysis.bayes import bayes_stats

                b = bayes_stats(stats)
                vpip = round(b["vpip"]["mean"])
                pfr = round(b["pfr"]["mean"])
                af = round(b["af"]["mean"], 2)
            except Exception:
                pass

        text = (
            "📅 *Seu resumo da semana*\n\n"
            f"• Mãos analisadas: {len(hands)}\n"
            f"• Resultado: {net_bb:+.1f} BB\n"
            f"• VPIP {vpip}% | PFR {pfr}% | AF {af}\n"
            + quiz_block
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
