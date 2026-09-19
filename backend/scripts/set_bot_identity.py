"""Configura a identidade do bot via API: descrição (chat vazio) e short
description (preview de compartilhamento). A FOTO de perfil a API não permite —
essa vai manualmente pelo @BotFather (/setuserpic).

Uso (no VPS): PYTHONPATH=. ./venv/bin/python scripts/set_bot_identity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.tg import call  # noqa: E402

DESC = (
    "♠ Coach de poker com IA, movido pelo Motor KKN.\n\n"
    "Manda o print da mesa ou o arquivo do torneio e recebe a leitura de um "
    "coach profissional: relatório mão a mão, leaks em bb/100, KKN Tilt "
    "Detector e leitura de vilão em odds — matemática de solver, nada de "
    "achismo.\n\nGrátis: 50 análises por mês. Manda uma mão e testa. 🃏"
)
SHORT = ("Coach de poker com IA — análise com matemática de solver, "
         "direto no Telegram. Pare de achar. Calcule. ♠")


def main() -> int:
    ok1 = call("setMyDescription", {"description": DESC[:512]}).get("ok")
    ok2 = call("setMyShortDescription",
               {"short_description": SHORT[:120]}).get("ok")
    print(f"descrição: {ok1} | short: {ok2}")
    return 0 if ok1 and ok2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
