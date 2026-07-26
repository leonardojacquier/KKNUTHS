"""Resumo DIÁRIO de uso — enviado só pro admin (Leo) via Telegram.

O que o admin quer saber todo dia, numa mensagem: entrou alguém novo?, quantos
usaram hoje?, quantas mãos/perguntas/quizzes?, quem sumiu?. Lê bot_events e
users direto do Supabase; não depende do bot estar de pé.

Regra de ouro do resumo: a PRIMEIRA linha responde 'entrou gente nova?' —
porque é a métrica nº1 de crescimento e a que o admin cobra.

Cron sugerido:  0 23 * * *  (23h UTC = 20h BRT) cd /app/backend && \
  PYTHONPATH=. ./venv/bin/python scripts/daily_usage.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.db import get_repository

ADMIN_ID = 6452742024
# telegram_ids internos (deploy/diag/e2e/sondas) que não são usuários reais
_SYS_IDS = {0}


def notify_admin(token: str, text: str) -> bool:
    body = json.dumps({"chat_id": ADMIN_ID, "text": text[:4000],
                       "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("ok", False)
    except Exception:
        return False


def _events_since(repo, iso: str) -> list[dict]:
    """bot_events desde `iso` (paginado — a tabela cresce)."""
    out: list[dict] = []
    step = 1000
    for page in range(20):
        rows = (repo.client.table("bot_events")
                .select("telegram_id,username,event,created_at")
                .gte("created_at", iso)
                .order("created_at")
                .range(page * step, page * step + step - 1)
                .execute().data) or []
        out += rows
        if len(rows) < step:
            break
    return out


def build_summary(now: datetime, reais: list[dict], ev_24h: list[dict],
                  day_ago: str) -> tuple[str, dict]:
    """Monta a mensagem do resumo diário (função PURA — testável sem I/O).
    Devolve (texto_markdown, métricas). A 1ª linha SEMPRE responde 'entrou
    gente nova?' — a métrica que o admin cobra."""
    reais = [u for u in reais if u["telegram_id"] not in _SYS_IDS]
    ev_24h = [e for e in ev_24h if e["telegram_id"] not in _SYS_IDS]

    novos = [u for u in reais if (u.get("created_at") or "") >= day_ago]
    ativos_ids = {e["telegram_id"] for e in ev_24h}

    def _count(name):
        return sum(1 for e in ev_24h if e["event"] == name)

    perguntas = _count("followup")
    quiz = _count("drill_answer")
    sims = _count("simular")
    analises = sum(1 for e in ev_24h
                   if e["event"] in ("photo", "document", "replay_link",
                                     "analyze", "analise"))

    nomes = {u["telegram_id"]: (u.get("username") or str(u["telegram_id"]))
             for u in reais}
    por_user: dict[int, int] = {}
    for e in ev_24h:
        por_user[e["telegram_id"]] = por_user.get(e["telegram_id"], 0) + 1
    linhas_user = sorted(por_user.items(), key=lambda kv: -kv[1])
    sumidos = [nomes.get(u["telegram_id"], str(u["telegram_id"]))
               for u in reais if u["telegram_id"] not in ativos_ids]

    data_br = (now - timedelta(hours=3)).strftime("%d/%m")
    if novos:
        cab = (f"🟢 *+{len(novos)} usuário(s) novo(s) hoje!* — "
               + ", ".join(n.get("username") or str(n["telegram_id"])
                           for n in novos))
    else:
        cab = "⚪️ *Nenhum usuário novo hoje.*"

    l = [f"📊 *KKNuths — uso {data_br}*", "", cab, "",
         f"👥 Base: *{len(reais)}* usuários · *{len(ativos_ids)}* ativos hoje",
         f"🃏 Mãos enviadas: *{analises}* · 💬 perguntas: *{perguntas}* · "
         f"🎯 quiz: *{quiz}* · 🎮 simular: *{sims}*"]
    if linhas_user:
        l.append("\n*Ativos hoje:*")
        for tid, n in linhas_user[:8]:
            l.append(f"• {nomes.get(tid, tid)} — {n} ações")
    if sumidos:
        l.append(f"\n😴 Sem aparecer hoje: {', '.join(sumidos[:8])}")

    # TAXA DE ENTREGA: de cada pedido conferível (gráfico/número), quantos
    # saíram completos de primeira. Era a métrica que faltava — sem ela a
    # nota de entrega era opinião minha e o defeito só aparecia por print.
    ok_e = _count("entrega_ok")
    falha_e = _count("entrega_falha")
    remediou = _count("entrega_remediada")
    pedidos = ok_e + falha_e
    entrega_pct = round(100 * ok_e / pedidos) if pedidos else None
    if pedidos:
        icone = "🟢" if entrega_pct >= 90 else ("🟡" if entrega_pct >= 70
                                               else "🔴")
        l.append(f"\n{icone} *Entrega: {entrega_pct}%* — {ok_e}/{pedidos} "
                 f"pedidos de gráfico/número vieram completos de primeira"
                 + (f" · {remediou} consertado(s) pelo guarda" if remediou
                    else ""))
    sem_mao = _count("sem_mao_na_conversa")
    if sem_mao:
        l.append(f"⚠️ *{sem_mao}x* a ferramenta não achou a mão da conversa "
                 "(caminho de contexto quebrado)")

    metrics = {"novos": len(novos), "ativos": len(ativos_ids),
               "base": len(reais), "maos": analises, "perguntas": perguntas,
               "quiz": quiz, "entrega_pct": entrega_pct,
               "entrega_pedidos": pedidos, "entrega_remediada": remediou,
               "sem_mao": sem_mao}
    return "\n".join(l), metrics


def main() -> int:
    settings = get_settings()
    repo = get_repository()
    if not settings.telegram_bot_token or not repo.enabled:
        print("ERRO: precisa de TELEGRAM_BOT_TOKEN e Supabase.")
        return 1

    now = datetime.now(timezone.utc)
    day_ago = (now - timedelta(hours=24)).isoformat()

    users = repo.client.table("users").select(
        "id,telegram_id,username,created_at").execute().data or []
    ev_24h = _events_since(repo, day_ago)

    text, metrics = build_summary(now, users, ev_24h, day_ago)
    ok = notify_admin(settings.telegram_bot_token, text)
    repo.log_event(0, "daily_usage", "daily_usage", metrics)
    print(f"resumo diário: {'enviado' if ok else 'FALHOU'} — "
          f"{metrics['novos']} novos, {metrics['ativos']} ativos, "
          f"base {metrics['base']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
