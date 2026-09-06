"""Envia o quadro do torneio (HUD) mais recente de um usuário para um chat.

Uso (no VPS): python scripts/send_board.py <telegram_id_dono> [chat_destino]

`chat_destino` (opcional): manda para outro chat — ex.: admin conferindo o
quadro de um beta — sem notificar o dono nem gravar evento.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.tournament_board import render_tournament_board  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import get_repository  # noqa: E402
from scripts.revalidation_report import _send_photo  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    tg_id = int(sys.argv[1])
    dest = int(sys.argv[2]) if len(sys.argv) > 2 else tg_id

    settings = get_settings()
    repo = get_repository()
    if not settings.telegram_bot_token or not repo.enabled:
        print("precisa de TELEGRAM_BOT_TOKEN e Supabase")
        return 1

    user = repo.get_or_create_user(tg_id, None)
    tourneys = [h for h in repo.get_all_hands(user["id"]) if h.tournament_id]
    if len(tourneys) < 3:
        print("sem torneio suficiente no banco")
        return 1
    latest = max(tourneys, key=lambda h: h.played_at or "")
    hands = sorted((h for h in tourneys if h.tournament_id == latest.tournament_id),
                   key=lambda h: h.played_at or "")
    png, cap = render_tournament_board(hands)
    _send_photo(settings.telegram_bot_token, dest, png, cap)
    print(f"quadro do torneio #{latest.tournament_id} ({len(hands)} mãos) -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
