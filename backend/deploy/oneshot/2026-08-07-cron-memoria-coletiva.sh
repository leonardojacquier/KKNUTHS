#!/usr/bin/env bash
# Instala o cron da MEMÓRIA COLETIVA e roda a primeira destilação.
#
# Por que existe: até aqui o produto sabia muito sobre cada aluno e nada
# sobre o conjunto — a busca semântica trava em user_id e o caderno também.
# O tema "3-bet" aparece no caderno de 4 alunos distintos e nenhum deles se
# beneficia do que os outros ensinaram. Este cron destila o que se repete
# ENTRE alunos e a análise passa a ler isso (app/agent/memoria.py).
#
# Roda 40 minutos depois do destilador de lições para não competir por CPU
# no mesmo minuto (a VPS é compartilhada).
set -uo pipefail
APP_DIR=/opt/poker-bot

L1="40 9 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/destilar_conhecimento.py >> /var/log/poker-conhecimento.log 2>&1"
( crontab -l 2>/dev/null | grep -v "poker-conhecimento\|destilar_conhecimento" ; \
  echo "$L1" ) | crontab -

echo "cron instalado:"
crontab -l | grep destilar_conhecimento

# primeira rodada agora, para o estoque não nascer vazio
cd $APP_DIR || exit 1
PYTHONPATH=$APP_DIR ./venv/bin/python scripts/destilar_conhecimento.py

echo
echo "conferência — o que entrou na memória coletiva:"
PYTHONPATH=$APP_DIR ./venv/bin/python - <<'PY'
from app.db import get_repository

repo = get_repository()
saberes = repo.listar_conhecimento(limit=50)
if not saberes:
    print("  (vazio — nenhum tema atingiu 2 alunos ainda, ou o modelo recusou)")
for s in saberes:
    print(f"  [{s['alunos']} alunos] {s['titulo']}")
    print(f"      QUANDO: {s['gatilho']}")
PY
