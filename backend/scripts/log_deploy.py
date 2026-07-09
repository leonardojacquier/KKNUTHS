"""Registra o deploy em bot_events — visibilidade de qual versão está NO AR.

Chamado pelo vps_deploy.sh após o restart. Sem isto, 'não subiu o ajuste'
era indistinguível de 'o ajuste não funciona'.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_repository  # noqa: E402


def main() -> int:
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip() or "?"
    msg = subprocess.run(["git", "log", "-1", "--format=%s"],
                         capture_output=True, text=True).stdout.strip()[:120]
    repo = get_repository()
    if repo.enabled:
        repo.log_event(0, "deploy", "deploy", {"rev": rev, "msg": msg})
    print(f"deploy registrado: {rev} {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
