#!/usr/bin/env bash
# Backfill do played_at nas mãos que chegaram SEM data de jogo (replay e
# print): recebe a data de CHEGADA (created_at).
#
# Por quê: 21/09 o dono mandou 5 replays e o coach disse quatro vezes que
# elas não estavam no histórico. Replay grava played_at NULL; o Postgres põe
# NULL primeiro no DESC em ordem arbitrária, e a busca "últimas mãos" não
# encontra a mão que acabou de chegar. Medido: 65 mãos do dono sem data, 52
# delas replay. O save_hand passou a preencher daqui pra frente; este script
# cuida das antigas.
#
# SÓ toca em played_at IS NULL — nunca sobrescreve uma data de jogo real.
set -uo pipefail
cd /opt/poker-bot || exit 1

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
from app.db import get_repository

repo = get_repository()
if not repo.enabled:
    raise SystemExit("banco desligado")

rows = (repo.client.table("hands").select("id,created_at")
        .is_("played_at", "null").limit(5000).execute().data) or []
print(f"mãos sem played_at: {len(rows)}")
feitas = 0
for r in rows:
    repo.client.table("hands").update({"played_at": r["created_at"]}) \
        .eq("id", r["id"]).is_("played_at", "null").execute()
    feitas += 1
print(f"backfill: {feitas} mãos receberam played_at = created_at")
repo.log_event(0, None, "backfill_played_at", {"maos": feitas})
PY
