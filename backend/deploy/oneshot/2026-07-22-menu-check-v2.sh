#!/usr/bin/env bash
# v2 do menu-check: a v1 interpolava JSON no heredoc do shell e morreu sem
# logar. Esta faz TUDO em python (urllib) — sem hazard de quoting — e
# aposenta o marcador da v1 pra ela parar de re-tentar.
set -uo pipefail
cd /opt/poker-bot || exit 1
mkdir -p .oneshot-done && touch .oneshot-done/2026-07-22-menu-check.sh

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json
import urllib.request

from app.db import get_repository

token = None
for line in open(".env"):
    if line.startswith("TELEGRAM_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

out = {"src": "menu-check", "token": bool(token)}
if token:
    api = f"https://api.telegram.org/bot{token}"

    def get(url, data=None):
        req = urllib.request.Request(
            url, data=json.dumps(data).encode() if data else None,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())

    try:
        antes = get(f"{api}/getMyCommands")
        out["antes"] = [c["command"] for c in antes.get("result", [])]
    except Exception as exc:
        out["antes_err"] = str(exc)[:150]

    cmds = [
        ("stats", "Seu perfil de estilo"),
        ("estilo", "Você vs os grandes jogadores"),
        ("evolucao", "Sua linha do tempo com gráficos"),
        ("torneio", "Quadro do último torneio"),
        ("relatorio", "Relatório mão a mão 📋"),
        ("preparar", "Preparação pré-torneio 🎯"),
        ("simular", "Rejogue uma mão sua 🎮"),
        ("treino", "Drill rápido de um spot seu"),
        ("leitura", "Adivinhe a mão do vilão 🔎"),
        ("vilao", "Dossiê de um oponente 🎯"),
        ("banca", "Risco de ruína e downswing 💰"),
        ("range", "Gráficos de range 13×13"),
        ("ask", "Busque no seu histórico"),
        ("manual", "Manual do jogador em PDF 📖"),
        ("plano", "Seu plano e limites"),
        ("start", "Menu inicial"),
    ]
    try:
        r = get(f"{api}/setMyCommands", {
            "commands": [{"command": c, "description": d} for c, d in cmds]})
        out["set_ok"] = r.get("ok")
        depois = get(f"{api}/getMyCommands")
        out["depois"] = [c["command"] for c in depois.get("result", [])]
    except Exception as exc:
        out["set_err"] = str(exc)[:150]

get_repository().log_event(0, None, "diag", out)
print("menu-check v2:", out)
PY
exit 0
