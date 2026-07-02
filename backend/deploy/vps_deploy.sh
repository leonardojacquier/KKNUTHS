#!/usr/bin/env bash
# Deploy do Poker Hand Analyzer no VPS GNH (root@187.127.13.220)
# Segue o padrão dos sistemas existentes (/opt/agente-century, GNHFIN):
#   - app em /opt/poker-bot
#   - venv próprio por projeto (recomendação da Revisão Geral de Código 2026-06-11)
#   - processo gerenciado pelo pm2 (mesmo padrão do telegram-bot do Jarvis)
#   - cron do relatório semanal usando o python do venv
# Idempotente: rodar de novo atualiza o código e reinicia o serviço.
set -euo pipefail

APP_DIR=/opt/poker-bot
PM2_NAME=poker-bot

echo "== Poker Bot deploy =="

# 1. código (o rsync/scp já deve ter colocado os arquivos em $APP_DIR)
cd "$APP_DIR"

# 2. git safety-net (lição do VPS: nada de .bak, tudo versionado)
#    segredos e artefatos ficam fora do git do servidor
cat > .gitignore <<'GITIGNORE'
.env
venv/
__pycache__/
*.pyc
.pytest_cache/
GITIGNORE
if [ ! -d .git ]; then
    git init -q && git add -A && git commit -qm "estado inicial do deploy"
else
    git add -A && git commit -qm "deploy $(date +%F_%T)" || true
fi

# 3. venv próprio (não misturar com o python do sistema)
if [ ! -d venv ]; then
    python3 -m venv venv
fi
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt

# 4. .env precisa existir (com as chaves)
if [ ! -f .env ]; then
    echo "ERRO: crie $APP_DIR/.env antes (modelo em .env.example)." >&2
    exit 1
fi

# 5. sanity check offline antes de subir
PYTHONPATH="$APP_DIR" ./venv/bin/python -m pytest -q tests/ || {
    echo "ERRO: testes falharam; deploy abortado." >&2
    exit 1
}

# 6. pm2 (mesmo gerenciador dos outros bots do VPS)
if pm2 describe "$PM2_NAME" >/dev/null 2>&1; then
    pm2 restart "$PM2_NAME" --update-env
else
    pm2 start ./venv/bin/python --name "$PM2_NAME" --cwd "$APP_DIR" \
        --interpreter none -- run_bot.py
fi
pm2 save

# 7. cron do relatório semanal (domingo 18h) — instala só se não existir
CRON_LINE="0 18 * * 0 cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/weekly_report.py >> /var/log/poker-weekly.log 2>&1"
( crontab -l 2>/dev/null | grep -v "poker-weekly" ; echo "$CRON_LINE" ) | crontab -

echo "== OK: pm2 status =="
pm2 status "$PM2_NAME"
echo
echo "Logs:  pm2 logs $PM2_NAME --lines 50"
