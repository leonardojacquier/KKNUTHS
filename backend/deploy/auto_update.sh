#!/usr/bin/env bash
# Auto-deploy do poker-bot: roda no cron a cada 2 min; quando há commit novo no
# branch, puxa, redeploya (testes como portão) e avisa o admin no Telegram.
# Instalação (uma vez): ver deploy/README.md — seção "Auto-deploy".
set -euo pipefail

# ---------------------------------------------------------------------------
# RODA DE UMA CÓPIA. O cron chama /opt/poker-bot/deploy/auto_update.sh — que é
# EXATAMENTE um dos arquivos que o rsync mais abaixo sobrescreve. O bash lê
# script por OFFSET DE BYTE: trocar o arquivo no meio da execução faz ele
# retomar naquele mesmo offset dentro do arquivo NOVO, cair no meio de outra
# linha e morrer calado — exit 0, sem rodar o notify.
#
# Sempre foi assim, mas passava batido porque o arquivo mal mudava de tamanho
# e os offsets coincidiam. Em 07/08 o script cresceu ~50 linhas e o deploy
# sumiu sem dar nem erro nem sucesso. Reproduzido em /tmp:
#     linha 1: comecei
#     vitima.sh: line 4: nchimento: command not found
#     (exit 0, sem nunca chegar no fim)
#
# Copiar para /tmp e re-exec de lá resolve na raiz: o arquivo em EXECUÇÃO
# deixa de ser o arquivo em ATUALIZAÇÃO.
# ---------------------------------------------------------------------------
if [ "${AUTOUPDATE_EM_COPIA:-0}" != "1" ]; then
    _COPIA=$(mktemp /tmp/poker-autoupdate-XXXXXX.sh) || exit 1
    cat "$0" > "$_COPIA" && chmod +x "$_COPIA" || exit 1
    AUTOUPDATE_EM_COPIA=1 AUTOUPDATE_COPIA="$_COPIA" exec bash "$_COPIA" "$@"
fi
trap 'rm -f "${AUTOUPDATE_COPIA:-}"' EXIT

REPO=/opt/kknuths
APP=/opt/poker-bot
BRANCH=claude/poker-analysis-telegram-bot-mfuyhf
STATE=/tmp/poker-autoupdate.last

# nunca rodar duas instâncias ao mesmo tempo
exec 9>/tmp/poker-autoupdate.lock
flock -n 9 || exit 0

notify() {  # avisa o admin no Telegram (se configurado); nunca falha o deploy
    if grep -q '^TELEGRAM_ADMIN_CHAT_ID=' "$APP/.env" 2>/dev/null; then
        ADMIN=$(grep '^TELEGRAM_ADMIN_CHAT_ID=' "$APP/.env" | cut -d= -f2)
        (cd "$APP" && PYTHONPATH="$APP" ./venv/bin/python scripts/tg.py send "$ADMIN" "$1" >/dev/null 2>&1) || true
    fi
}

# set -e mata o script em qualquer erro (ex.: git fetch com rede instável) —
# sem este trap o aborto era SILENCIOSO: nem 🔄 nem ⚠️, e o commit ficava
# marcado como tentado (sem retry até o próximo push)
trap 'notify "⚠️ Auto-deploy abortou inesperadamente (linha $LINENO). Um push novo (pode ser vazio) reativa."' ERR

cd "$REPO"
git fetch origin "$BRANCH" -q
# compara com o último deploy BEM-SUCEDIDO (não com o HEAD do clone — um deploy
# que falhou no meio deixaria o HEAD avançado e mascararia o retry)
OK_FILE=/tmp/poker-autoupdate.ok
LOCAL=$(cat "$OK_FILE" 2>/dev/null || git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
[ "$LOCAL" = "$REMOTE" ] && exit 0

# não insistir num commit que acabou de falhar (espera o próximo push)
if [ -f "$STATE" ] && [ "$(cat "$STATE")" = "$REMOTE" ]; then
    exit 0
fi
echo "$REMOTE" > "$STATE"

echo "[$(date '+%F %T')] novo commit: ${LOCAL:0:7} -> ${REMOTE:0:7}; atualizando…"
git reset --hard -q "origin/$BRANCH"

# ---------------------------------------------------------------------------
# PORTÃO ANTES DA CÓPIA. Até 07/08 a ordem era o inverso: o rsync substituía
# /opt/poker-bot e SÓ ENTÃO o vps_deploy.sh rodava o pytest. Testes vermelhos
# abortavam o restart, o Telegram avisava "o bot continua na versão anterior"
# — e era mentira: o processo seguia com o código antigo apenas porque o
# Python já estava carregado em memória. O disco tinha a versão REPROVADA, e
# o próximo restart (crash, reboot, pm2 restart, o deploy seguinte) subia ela
# calada. Auditoria reproduziu a sequência inteira.
#
# Agora o teste roda no CLONE. Produção só é tocada por código aprovado.
# ---------------------------------------------------------------------------
cd "$REPO/backend"
# dependência nova primeiro, senão o teste falha por ImportError e a gente
# culpa o commit errado. Só quando requirements.txt mudou de verdade.
if ! cmp -s "$REPO/backend/requirements.txt" "$APP/requirements.txt"; then
    echo "[$(date '+%F %T')] requirements.txt mudou; instalando no venv"
    "$APP/venv/bin/pip" install -q -r "$REPO/backend/requirements.txt" || true
fi
if ! PYTHONPATH="$REPO/backend" "$APP/venv/bin/python" -m pytest -q tests/; then
    echo "[$(date '+%F %T')] TESTES VERMELHOS em ${REMOTE:0:7}; produção intacta"
    notify "⛔ Testes falharam em ${REMOTE:0:7} — *produção não foi tocada*, o bot segue no ar na versão boa. Ver /var/log/poker-autodeploy.log"
    exit 1
fi

# SNAPSHOT antes de mexer: o portão cobre teste vermelho, não cobre código
# que passa nos testes e morre no import ao subir. Sem isto, "voltar atrás"
# dependia de um push de reversão — minutos com o bot fora.
BACKUP=/tmp/poker-bot-anterior
rm -rf "$BACKUP" && mkdir -p "$BACKUP"
rsync -a --exclude='venv/' --exclude='.git/' "$APP/" "$BACKUP/" 2>/dev/null || \
    cp -r "$APP/." "$BACKUP/" 2>/dev/null || true

# rsync --delete: arquivo removido do repo sai do servidor também (cp -r só
# sobrepõe — módulo deletado ficava vivo em /opt/poker-bot para sempre)
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
        --exclude='.env' --exclude='venv/' --exclude='.git/' \
        --exclude='.oneshot-done/' --exclude='__pycache__/' \
        --exclude='calibration.json' \
        "$REPO/backend/" "$APP/"
else
    cp -r "$REPO/backend/." "$APP/"
fi

# ---------------------------------------------------------------------------
# SÃO DOIS PROCESSOS. O vps_deploy.sh sobe `poker-bot` (o bot) e `poker-web`
# (uvicorn na 8014, que serve o site e o portal) — e este portão conferia
# APENAS o primeiro. Deploy que derrubasse o site anunciava "🔄 Bot
# atualizado", o rollback não disparava, e ninguém ficava sabendo até o dono
# abrir o navegador. Aconteceu em 09/08.
#
# E não basta `pm2 describe poker-web | grep online`: uvicorn fica online com
# a aplicação quebrada. Quem responde essa pergunta é o próprio HTTP.
# ---------------------------------------------------------------------------
web_responde() {
    local codigo
    codigo=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
                  http://127.0.0.1:8014/health 2>/dev/null || echo 000)
    [ "$codigo" = "200" ]
}

# o portão já passou no clone; não pagar 3 minutos de pytest de novo
export PORTAO_JA_PASSOU=1
if bash "$APP/deploy/vps_deploy.sh" && sleep 8 && \
   pm2 describe poker-bot 2>/dev/null | grep -q "online" && \
   web_responde; then
    MSG=$(cd "$REPO" && git log -1 --format='%s')
    echo "$REMOTE" > "$OK_FILE"
    echo "[$(date '+%F %T')] deploy OK em ${REMOTE:0:7}"
    notify "🔄 Bot atualizado (${REMOTE:0:7}): $MSG"
else
    # passou nos testes e não subiu: RESTAURA em vez de deixar o disco com
    # uma versão que não roda
    echo "[$(date '+%F %T')] SUBIDA FALHOU em ${REMOTE:0:7}; restaurando anterior"
    rsync -a --delete --exclude='venv/' --exclude='.env' \
        "$BACKUP/" "$APP/" 2>/dev/null || cp -r "$BACKUP/." "$APP/"
    # os DOIS: restaurar o disco e reiniciar só o bot deixava o poker-web
    # rodando de memória o código reprovado, até o próximo restart qualquer
    pm2 restart poker-bot --update-env >/dev/null 2>&1 || true
    pm2 restart poker-web --update-env >/dev/null 2>&1 || true
    notify "⚠️ ${REMOTE:0:7} passou nos testes mas não subiu — *restaurei a versão anterior* e reiniciei bot e site. Ver /var/log/poker-autodeploy.log"
fi
