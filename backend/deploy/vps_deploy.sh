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

# 6a2. registra a versão que subiu (bot_events) — auditável do lado de fora
PYTHONPATH="$APP_DIR" ./venv/bin/python scripts/log_deploy.py || true

# 6b. portal de gestão (uvicorn na 8014, atrás do Caddy)
if pm2 describe poker-web >/dev/null 2>&1; then
    pm2 restart poker-web --update-env
else
    pm2 start ./venv/bin/python --name poker-web --cwd "$APP_DIR" \
        --interpreter none -- -m uvicorn app.api.main:app --host 127.0.0.1 --port 8014
fi
pm2 save

# 6c. tarefas one-shot (rodam UMA vez por arquivo, marcador em .oneshot-done/)
#     Ex.: reprocessar uploads após correção de parser. Falha não aborta deploy.
mkdir -p .oneshot-done
if [ -d deploy/oneshot ]; then
    for task in deploy/oneshot/*.sh; do
        [ -e "$task" ] || continue
        marker=".oneshot-done/$(basename "$task")"
        if [ ! -f "$marker" ]; then
            echo "== oneshot: $(basename "$task") =="
            if bash "$task"; then
                touch "$marker"
            else
                echo "AVISO: oneshot $(basename "$task") falhou; tentará no próximo deploy." >&2
            fi
        fi
    done
fi

# 7. crons do produto: relatório semanal (dom 18h) + quiz diário (19h)
#    + calibração das likelihoods por showdown (seg 5h, invisível ao usuário)
CRON_WEEKLY="0 18 * * 0 cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/weekly_report.py >> /var/log/poker-weekly.log 2>&1"
CRON_QUIZ="0 19 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/daily_quiz.py >> /var/log/poker-quiz.log 2>&1"
CRON_CALIB="0 5 * * 1 cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/calibrate_likelihood.py >> /var/log/poker-calibrate.log 2>&1"
CRON_COHER="0 6 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/nightly_coherence.py >> /var/log/poker-coherence.log 2>&1"
CRON_E2E="30 7 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/e2e_probe.py >> /var/log/poker-e2e.log 2>&1"
# resumo DIÁRIO de uso pro admin (23h UTC = 20h BRT): entrou gente nova?, ativos, mãos
CRON_USAGE="0 23 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/daily_usage.py >> /var/log/poker-usage.log 2>&1"
# juiz da SAÍDA (8h): audita as respostas que o coach mandou — selo, números,
# jargão proibido, calque. Os outros canários só olham a matemática.
CRON_JUDGE="0 8 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/output_judge.py >> /var/log/poker-judge.log 2>&1"
# BACKUP do banco (4h UTC = 1h BRT): o histórico do aluno é o ativo e vivia
# sem cópia. Dump em JSON.gz no disco do VPS, 14 dias; avisa o admin se falhar.
CRON_BACKUP="0 4 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/backup_db.py >> /var/log/poker-backup.log 2>&1"
# SONDA DE JORNADAS (7h): o caminho do aluno entrega artefato? Roda em
# processo (sem Telegram, sem LLM) — a sonda E2E depende de uma conta-teste
# que nunca foi criada e por isso nunca rodou uma vez sequer.
CRON_JORNADAS="0 7 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/jornadas.py >> /var/log/poker-jornadas.log 2>&1"
# SONDA DE RECEBIMENTO (de hora em hora): o bot ainda ESCUTA? Nenhum outro
# monitor cobre isso — todos rodam em processo próprio e não tocam no
# Telegram, então passam alegremente com o bot mudo. Só fala quando há
# problema: webhook registrado ou getMe falhando = certeza; silêncio humano
# longo em horário ativo = suspeita.
CRON_LINGUA="40 7 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/linguista.py >> /var/log/poker-linguista.log 2>&1"
# LINGUISTA (7h40, antes do juiz das 8h): IA propoe termos calcados que
# leu nas analises do dia; o dono aprova via /termo; corretor e juiz
# executam. A IA nunca edita o prompt nem aprova a si mesma.
CRON_LICAODIA="0 14 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/licao_do_dia.py >> /var/log/poker-licaodia.log 2>&1"
# LICAO DO DIA (14h UTC = 11h BRT, longe do quiz das 19h): manda UMA licao
# da fila APROVADA pelo dono. Fila vazia = silencio pro aluno e aviso pro
# dono. Reativa quem so recebe quiz e convida a 1a mao.
CRON_ANOMALIA="0 21 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/anomalias.py >> /var/log/poker-anomalias.log 2>&1"
# ANOMALIAS (21h UTC = 18h BRT): vigia deterministico de comportamento —
# tropecou-e-sumiu, envio repetido, start sem mao, falha em serie. Cala
# quando nao ha nada.
CRON_LICOES="15 9 * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/destilar_licoes.py >> /var/log/poker-licoes.log 2>&1"
# LICOES (9h15): destila erros/acertos caros do dia em licoes anonimas.
# Estoca em silencio; publicar e decisao humana via /licoes.
CRON_RECEB="7 * * * * cd $APP_DIR && PYTHONPATH=$APP_DIR ./venv/bin/python scripts/sonda_recebimento.py >> /var/log/poker-recebimento.log 2>&1"
( crontab -l 2>/dev/null | grep -v "poker-weekly\|poker-quiz\|poker-calibrate\|poker-coherence\|poker-e2e\|poker-usage\|poker-judge\|poker-backup\|poker-jornadas\|weekly_report\|daily_quiz\|calibrate_likelihood\|nightly_coherence\|e2e_probe\|daily_usage\|output_judge\|backup_db\|jornadas\|poker-recebimento\|sonda_recebimento\|poker-linguista\|linguista.py\|poker-anomalias\|anomalias.py\|poker-licoes\|destilar_licoes\|poker-licaodia\|licao_do_dia" ; \
  echo "$CRON_WEEKLY" ; echo "$CRON_QUIZ" ; echo "$CRON_CALIB" ; echo "$CRON_COHER" ; echo "$CRON_E2E" ; echo "$CRON_USAGE" ; echo "$CRON_JUDGE" ; echo "$CRON_BACKUP" ; echo "$CRON_JORNADAS" ; echo "$CRON_RECEB" ; echo "$CRON_LINGUA" ; echo "$CRON_ANOMALIA" ; echo "$CRON_LICOES" ; echo "$CRON_LICAODIA" ) | crontab -

# 7b. E2E pós-deploy: a conta-teste usa o bot de verdade (dorme sem credenciais
#     no .env). Em background, com folga pro bot terminar de subir.
( sleep 30 && cd "$APP_DIR" && PYTHONPATH="$APP_DIR" ./venv/bin/python \
    scripts/e2e_probe.py >> /var/log/poker-e2e.log 2>&1 ) &
# jornadas pós-deploy: 10s, sem LLM, pega release que quebrou a entrega
( sleep 20 && cd "$APP_DIR" && PYTHONPATH="$APP_DIR" ./venv/bin/python \
    scripts/jornadas.py >> /var/log/poker-jornadas.log 2>&1 ) &

echo "== OK: pm2 status =="
pm2 status "$PM2_NAME"
echo
echo "Logs:  pm2 logs $PM2_NAME --lines 50"
