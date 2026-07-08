"""Calibra as likelihoods do range tracker com os showdowns da base — roda no
VPS (cron semanal). Grava calibration.json no diretório do app; o tracker
carrega automaticamente no próximo restart/uso.

Uso: PYTHONPATH=. ./venv/bin/python scripts/calibrate_likelihood.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.calibration import calibrated_tables, observe_showdowns  # noqa: E402
from app.db import get_repository  # noqa: E402
from app.models.canonical import CanonicalHand  # noqa: E402


def main() -> int:
    repo = get_repository()
    if not repo.enabled:
        print("Supabase indisponível — nada a calibrar")
        return 1

    rows = (
        repo.client.table("hands").select("canonical").limit(20000).execute()
    ).data or []
    hands: list[CanonicalHand] = []
    for r in rows:
        try:
            hands.append(CanonicalHand.model_validate(r["canonical"]))
        except Exception:
            continue

    counts = observe_showdowns(hands)
    n_obs = sum(v for by in counts.values() for v in by.values())
    tables = calibrated_tables(counts)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hands_scanned": len(hands),
        "observations": n_obs,
        "counts": counts,
        "tables": tables,
    }
    dest = Path("calibration.json")
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{len(hands)} mãos varridas, {n_obs} observações de showdown "
          f"-> {dest.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
