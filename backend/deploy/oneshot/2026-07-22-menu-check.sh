#!/usr/bin/env bash
# O admin não vê /leitura /vilao /banca no menu "/" do Telegram. O
# set_my_commands roda num try/except silencioso — este oneshot pergunta à
# API o que está registrado DE VERDADE, reaplica a lista completa e loga os
# dois estados (antes/depois) no bot_events.
set -uo pipefail
cd /opt/poker-bot || exit 1

TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2-)
[ -z "$TOKEN" ] && exit 0

ANTES=$(curl -s "https://api.telegram.org/bot${TOKEN}/getMyCommands" | head -c 1200)

DEPOIS=$(curl -s -X POST "https://api.telegram.org/bot${TOKEN}/setMyCommands" \
  -H "Content-Type: application/json" -d '{"commands":[
    {"command":"stats","description":"Seu perfil de estilo"},
    {"command":"estilo","description":"Você vs os grandes jogadores"},
    {"command":"evolucao","description":"Sua linha do tempo com gráficos"},
    {"command":"torneio","description":"Quadro do último torneio"},
    {"command":"relatorio","description":"Relatório mão a mão 📋"},
    {"command":"preparar","description":"Preparação pré-torneio 🎯"},
    {"command":"simular","description":"Rejogue uma mão sua 🎮"},
    {"command":"treino","description":"Drill rápido de um spot seu"},
    {"command":"leitura","description":"Adivinhe a mão do vilão 🔎"},
    {"command":"vilao","description":"Dossiê de um oponente 🎯"},
    {"command":"banca","description":"Risco de ruína e downswing 💰"},
    {"command":"range","description":"Gráficos de range 13×13"},
    {"command":"ask","description":"Busque no seu histórico"},
    {"command":"manual","description":"Manual do jogador em PDF 📖"},
    {"command":"plano","description":"Seu plano e limites"},
    {"command":"start","description":"Menu inicial"}
  ]}' | head -c 300)

CONFERE=$(curl -s "https://api.telegram.org/bot${TOKEN}/getMyCommands" | head -c 1200)

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<PY
from app.db import get_repository

get_repository().log_event(0, None, "diag", {
    "src": "menu-check", "antes": """$ANTES"""[:900],
    "set_resp": """$DEPOIS"""[:250], "depois": """$CONFERE"""[:900]})
print("menu verificado e reaplicado")
PY
exit 0
