#!/usr/bin/env bash
# O bot está em LAÇO DE REINÍCIO: 275 restarts, mem 4.0kb, e o out.log com
# "bot iniciando em modo polling…" repetido dezenas de vezes seguidas. O
# error.log NÃO tem traceback recente — sinal de saída limpa, não exceção.
# Saída limpa significa que `run_polling()` está RETORNANDO em vez de ficar
# bloqueado, e o pm2 relança em seguida.
#
# Só um jeito de ver: rodar em primeiro plano e capturar tudo.
#
# O pm2 é PARADO antes (duas instâncias polling dão 409 e mascaram o erro
# real) e RELIGADO num trap — se este script morrer no meio, por qualquer
# motivo, o bot volta. Ele já está fora do ar para o usuário, então a
# parada de 30s não custa disponibilidade nenhuma.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')

avisa() {
    [ -z "${TG_TOKEN:-}" ] && { echo "$1"; return; }
    curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "$(python3 -c 'import json,sys;print(json.dumps({"chat_id":6452742024,"text":sys.stdin.read()[:3900]}))' <<< "$1")" \
        >/dev/null || true
}

# GARANTIA: aconteça o que acontecer, o pm2 volta
religa() { pm2 start poker-bot >/dev/null 2>&1 || pm2 restart poker-bot >/dev/null 2>&1 || true; }
trap religa EXIT

DESCR=$(pm2 describe poker-bot 2>&1 | grep -iE "exit code|restarts|uptime|script|status|unstable" | head -12)

pm2 stop poker-bot >/dev/null 2>&1 || true
sleep 2

SAIDA=$(cd /opt/poker-bot && PYTHONPATH=/opt/poker-bot timeout 25 \
        ./venv/bin/python run_bot.py 2>&1 | tail -c 3000)
CODIGO=$?

avisa "[foreground] pm2 describe:
${DESCR}

--- rodando run_bot.py em primeiro plano (25s) ---
código de saída: ${CODIGO}  (124 = seguiu vivo até o timeout = SAUDÁVEL)

${SAIDA}"

exit 0
