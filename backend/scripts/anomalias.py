"""Anomalias — a trilha de erros do Sócio na versão que funciona com N=6.

Veredicto do conselho: com 6 usuários, dossiê e fila de propostas são
teatro; o que serve é um vigia enxuto que TE AVISA quando o comportamento
foge do padrão. Determinístico, sem LLM, cala quando não há nada.

O padrão que motiva cada regra já aconteceu de verdade:
  tropeço_e_sumico  -> Antônio: bug na 1ª mão, nunca mais voltou (29/07)
  envio_repetido    -> mesmo conteúdo 3x em minutos = aluno brigando com
                       a ferramenta (o replay que 'não ia' na Suprema)
  start_sem_mao     -> Lucas: 2 drills da demo em 2min30 e saiu sem nunca
                       mandar uma mão (28/07)
  falha_em_serie    -> mesmo tipo de erro 3+ vezes no dia = defeito novo,
                       não azar

Cron sugerido:  0 21 * * *  (21h UTC = 18h BRT) cd /app/backend && \
  PYTHONPATH=. ./venv/bin/python scripts/anomalias.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.db import get_repository

ADMIN_ID = 6452742024

_ERROS = ("upload_failed", "entrega_falha", "sem_mao_na_conversa")
_ENGAJA = ("upload_recebido", "print_recebido", "upload", "replay_pppoker",
           "replay_suprema", "followup", "drill_answer", "simular")


def _por_usuario(eventos: list[dict]) -> dict[int, list[dict]]:
    por: dict[int, list[dict]] = {}
    for e in eventos:
        tid = e.get("telegram_id")
        if isinstance(tid, int) and tid > 0:
            por.setdefault(tid, []).append(e)
    return por


def achar_anomalias(eventos: list[dict], agora: datetime,
                    nomes: dict[int, str] | None = None) -> list[str]:
    """Regras determinísticas sobre os eventos de 24h (função pura)."""
    nomes = nomes or {}
    achados: list[str] = []
    por = _por_usuario(sorted(eventos, key=lambda e: e.get("created_at") or ""))

    def _nome(tid):
        return nomes.get(tid) or str(tid)

    def _quando(e):
        raw = (e.get("created_at") or "").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return agora

    for tid, evs in por.items():
        # tropeçou e sumiu: o ÚLTIMO evento do dia é um erro, faz 3h+
        ultimo = evs[-1]
        if ultimo.get("event") in _ERROS and \
                agora - _quando(ultimo) > timedelta(hours=3):
            achados.append(
                f"🚨 {_nome(tid)} tropeçou ({ultimo['event']}) e não voltou "
                f"desde {_quando(ultimo).strftime('%H:%M')} UTC — o padrão "
                "do Antônio. Vale um toque hoje.")
        # envio repetido: mesmo evento 3x em <=10 min = brigando com a tela
        for i in range(len(evs) - 2):
            a, c = evs[i], evs[i + 2]
            if (a["event"] == evs[i + 1]["event"] == c["event"]
                    and a["event"] in _ENGAJA
                    and _quando(c) - _quando(a) <= timedelta(minutes=10)):
                achados.append(
                    f"⚠️ {_nome(tid)} repetiu '{a['event']}' 3x em "
                    "10 min — algo não está indo na primeira tentativa.")
                break
        # start sem mão: deu start hoje e não mandou NADA de conteúdo
        if any(e["event"] == "start" for e in evs) and \
                not any(e["event"] in _ENGAJA for e in evs):
            achados.append(
                f"👋 {_nome(tid)} deu /start e saiu sem mandar mão nem "
                "responder drill — o padrão do Lucas. Convite à primeira "
                "mão chegou nele?")

    # falha em série: mesmo tipo de erro 3+ no dia inteiro = defeito, não azar
    contagem: dict[str, int] = {}
    for e in eventos:
        if e.get("event") in _ERROS:
            contagem[e["event"]] = contagem.get(e["event"], 0) + 1
    for tipo, n in sorted(contagem.items(), key=lambda kv: -kv[1]):
        if n >= 3:
            achados.append(f"🔧 '{tipo}' aconteceu {n}x nas últimas 24h — "
                           "isso é defeito novo, não azar.")
    return achados


def notify_admin(token: str, text: str) -> bool:
    body = json.dumps({"chat_id": ADMIN_ID, "text": text[:4000]}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("ok", False)
    except Exception:
        return False


def main() -> int:
    settings = get_settings()
    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase")
        return 0
    agora = datetime.now(timezone.utc)
    desde = (agora - timedelta(hours=24)).isoformat()
    eventos = (repo.client.table("bot_events")
               .select("telegram_id,event,created_at")
               .gte("created_at", desde).order("created_at")
               .limit(3000).execute().data) or []
    users = (repo.client.table("users").select("telegram_id,username")
             .execute().data) or []
    nomes = {u["telegram_id"]: u.get("username") for u in users
             if u.get("telegram_id")}

    achados = achar_anomalias(eventos, agora, nomes)
    repo.log_event(0, "anomalias", "anomalias",
                   {"eventos": len(eventos), "achados": len(achados)})
    if achados and settings.telegram_bot_token:
        notify_admin(settings.telegram_bot_token,
                     "👁 Anomalias do dia:\n\n" + "\n\n".join(achados[:8]))
    print(f"anomalias: {len(eventos)} eventos, {len(achados)} achado(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
