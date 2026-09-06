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


def _git(args: list[str], cwd: str | None) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip()


def main() -> int:
    # rev do CLONE do GitHub (/opt/kknuths) — o git de /opt/poker-bot é só um
    # snapshot local do vps_deploy.sh e o hash de lá não existe no GitHub
    src = "/opt/kknuths" if Path("/opt/kknuths/.git").exists() else None
    rev = _git(["rev-parse", "--short", "HEAD"], src) or "?"
    msg = _git(["log", "-1", "--format=%s"], src)[:120]
    repo = get_repository()
    if repo.enabled:
        repo.log_event(0, "deploy", "deploy", {"rev": rev, "msg": msg})
    print(f"deploy registrado: {rev} {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
