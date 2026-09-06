"""Prévia do /stats de um usuário enviada a OUTRO chat (admin conferindo as
análises novas sem notificar o usuário).

Uso (no VPS): python scripts/send_stats_preview.py <telegram_id_dono> <chat_destino>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bot.processing import stats_report  # noqa: E402
from app.config import get_settings  # noqa: E402
from scripts.revalidation_report import _send_text  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    owner, dest = int(sys.argv[1]), int(sys.argv[2])
    msg = stats_report(owner, None)
    if not msg:
        print("sem dados para esse usuário")
        return 1
    token = get_settings().telegram_bot_token
    _send_text(token, dest,
               f"👁 Prévia de admin — o /stats do usuário {owner} como sai "
               "hoje (números corrigidos por amostra, leaks em bb/100 e "
               "KKN Tilt Detector):")
    _send_text(token, dest, msg)
    print(f"prévia de {owner} enviada a {dest} ({len(msg)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
