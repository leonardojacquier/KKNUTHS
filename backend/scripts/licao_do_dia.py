"""Lição do dia — manda para os alunos UMA lição da fila aprovada.

Pedido do dono (07/08): "criar um enviar diário dessa lição escolhida".

Fronteira dura, a mesma do resto: o destilador ESTOCA, o dono APROVA
(/licoes N ok), e só então este cron ENVIA. Lição não aprovada nunca sai —
uma lição errada no grupo/no privado queima a credibilidade com o público
exato que a gente quer atrair.

Vale como reativação: dá aos adormecidos um motivo de abrir o bot que não
é o quiz — e cada lição fecha com o convite à mão, que é a muralha real
do funil (4 usuários entraram em 10 dias, nenhum mandou mão ainda).

Cron sugerido:  0 14 * * *  (14h UTC = 11h BRT — manhã, longe do quiz das
19h) cd /app/backend && PYTHONPATH=. ./venv/bin/python scripts/licao_do_dia.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone

from app.config import get_settings
from app.db import get_repository

ADMIN_ID = 6452742024


def texto_da_licao(licao: dict) -> str:
    """Formata a lição para o aluno. Termina SEMPRE com o convite à mão —
    é o único CTA que ataca o gargalo do produto."""
    ev = licao.get("ev_bb")
    custo = f" (custou {abs(ev):.1f}bb)" if isinstance(ev, (int, float)) \
        and ev < 0 else (f" (rendeu {ev:.1f}bb)" if isinstance(ev, (int, float))
                         and ev > 0 else "")
    return (f"📖 *Lição do dia — {licao['titulo']}*\n\n"
            f"{licao['spot']}\n\n"
            f"{licao['licao']}{custo}\n\n"
            "———\n"
            "_Spot real de um aluno, anonimizado._ 🃏 *Manda uma mão sua* "
            "(print, arquivo ou link do replay) que eu analiso na hora.")


def proxima_licao(repo) -> dict | None:
    """A mais antiga aprovada e ainda não enviada — fila FIFO, sem repetir."""
    linhas = (repo.client.table("licoes").select("*")
              .eq("aprovada", True).is_("enviada_em", "null")
              .order("id").limit(1).execute().data) or []
    return linhas[0] if linhas else None


def _post(token: str, chat_id: int, texto: str) -> bool:
    body = json.dumps({"chat_id": chat_id, "text": texto[:4000],
                       "parse_mode": "Markdown"}).encode()
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
    if not settings.telegram_bot_token or not repo.enabled:
        print("ERRO: precisa de TELEGRAM_BOT_TOKEN e Supabase.")
        return 1

    licao = proxima_licao(repo)
    if not licao:
        # fila vazia é SILÊNCIO para o aluno, mas o dono precisa saber —
        # senão o canal seca sem ninguém perceber
        estoque = (repo.client.table("licoes").select("id", count="exact")
                   .eq("aprovada", False).execute().count or 0)
        _post(settings.telegram_bot_token, ADMIN_ID,
              f"📖 Lição do dia: fila VAZIA — nada foi enviado hoje. "
              f"{estoque} lição(ões) esperando sua aprovação em /licoes.")
        print("fila vazia")
        return 0

    texto = texto_da_licao(licao)
    users = (repo.client.table("users").select("telegram_id")
             .execute().data) or []
    enviados = 0
    for u in users:
        tg = u.get("telegram_id")
        if not isinstance(tg, int) or tg <= 0:
            continue
        if _post(settings.telegram_bot_token, tg, texto):
            repo.log_event(tg, None, "licao_recebida", {"licao": licao["id"]})
            enviados += 1

    repo.client.table("licoes").update({
        "enviada_em": datetime.now(timezone.utc).isoformat(),
        "publicada": True}).eq("id", licao["id"]).execute()
    repo.log_event(0, "licao_do_dia", "licao_do_dia",
                   {"licao": licao["id"], "enviados": enviados,
                    "titulo": licao["titulo"]})
    restam = (repo.client.table("licoes").select("id", count="exact")
              .eq("aprovada", True).is_("enviada_em", "null")
              .execute().count or 0)
    _post(settings.telegram_bot_token, ADMIN_ID,
          f"📖 Lição do dia enviada: #{licao['id']} «{licao['titulo']}» → "
          f"{enviados} aluno(s). Fila: {restam} aprovada(s) restante(s).")
    print(f"lição {licao['id']} enviada para {enviados} aluno(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
