"""Lição do dia — varre a FILA do que o dono aprovou e não disparou na hora.

Desde 07/08 o `/licoes N ok` DISPARA na hora (pedido do dono: "seria legal
disparar quando eu faço a seleção, no mesmo instante"). Este cron deixou de
ser o caminho principal e virou a rede: pega o que a trava anti-rajada
segurou (aprovar 3 seguidas não vira 3 pushes) e avisa quando a fila seca.

O motor de envio mora em app/bot/licao_envio.py — um só lugar para o
comando e o cron, senão os dois divergem.

Cron:  0 14 * * *  (14h UTC = 11h BRT — manhã, longe do quiz das 19h)
  cd /app/backend && PYTHONPATH=. ./venv/bin/python scripts/licao_do_dia.py
"""
from __future__ import annotations

import sys

from app.bot.licao_envio import (  # noqa: F401 (reexport p/ testes antigos)
    ADMIN_ID, _post, enviar_licao, proxima_licao, texto_da_licao,
)
from app.config import get_settings
from app.db import get_repository


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

    r = enviar_licao(repo, settings.telegram_bot_token, licao)
    _post(settings.telegram_bot_token, ADMIN_ID,
          f"📖 Lição do dia enviada: #{licao['id']} «{licao['titulo']}» → "
          f"{r['enviados']} aluno(s). Fila: {r['fila']} aprovada(s) "
          f"restante(s).")
    print(f"lição {licao['id']} enviada para {r['enviados']} aluno(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
