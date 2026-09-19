#!/usr/bin/env bash
# URGENTE: o bot parou de receber. Última interação humana em bot_events foi
# 2026-07-26 22:47 UTC; depois disso só cron e deploy (telegram_id 0). O
# admin subiu um .txt e nem o evento saiu.
#
# Os crons rodam em processo PRÓPRIO, então eles logarem não prova nada
# sobre o bot: prova só que o VPS está de pé. O que precisa ser respondido:
#   1. o processo do bot está vivo? reiniciando em laço?
#   2. o que ele cuspiu no log antes de parar?
#   3. tem WEBHOOK registrado? webhook ativo MATA o long-polling em silêncio
#      — o bot fica de pé, saudável, e simplesmente não recebe nada;
#   4. tem mais de uma instância polling? (409 Conflict)
#
# Só leitura. Não reinicia nada: quero ver o estado do jeito que ele está.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

PM2_STATUS=$(pm2 jlist 2>/dev/null | head -c 4000)
export PM2_STATUS
PM2_LOG=$(pm2 logs poker-bot --lines 80 --nostream 2>&1 | tail -c 6000)
export PM2_LOG
QUANTOS=$(pgrep -fc "run_bot.py" 2>/dev/null || echo 0)
export QUANTOS

./venv/bin/python - <<'PY'
import json, os, re, urllib.request

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = 6452742024


def diga(t):
    print(t)
    if not TOKEN:
        return
    for i in range(0, len(t), 3800):
        c = json.dumps({"chat_id": CHAT, "text": t[i:i + 3800]}).encode()
        r = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=c,
            headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(r, timeout=25)
        except Exception as exc:
            print(f"(envio falhou: {exc})")


partes = []

# 1. processo
partes.append(f"processos run_bot.py vivos: {os.environ.get('QUANTOS')}")
try:
    apps = json.loads(os.environ.get("PM2_STATUS") or "[]")
    for a in apps:
        if "poker" not in (a.get("name") or ""):
            continue
        e = a.get("pm2_env", {})
        partes.append(f"  {a.get('name')}: {e.get('status')} · "
                      f"restarts={e.get('restart_time')} · "
                      f"unstable={e.get('unstable_restarts')} · "
                      f"pid={a.get('pid')}")
except Exception as exc:
    partes.append(f"  (pm2 jlist ilegível: {exc})")

# 2. WEBHOOK — a suspeita principal: mata o polling sem derrubar o processo
try:
    with urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo",
            timeout=20) as r:
        w = json.loads(r.read())["result"]
    partes.append(f"\nwebhook url: {w.get('url')!r}")
    partes.append(f"  pendentes: {w.get('pending_update_count')}")
    if w.get("last_error_message"):
        partes.append(f"  último erro: {w.get('last_error_message')}")
    if w.get("url"):
        partes.append("  ⚠️ WEBHOOK ATIVO — enquanto existir, o long-polling "
                      "NÃO recebe nada. É a causa mais provável.")
except Exception as exc:
    partes.append(f"\n(getWebhookInfo falhou: {exc})")

# 3. o bot responde à API? (getMe é leitura pura)
try:
    with urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=20) as r:
        me = json.loads(r.read())["result"]
    partes.append(f"\ngetMe ok: @{me.get('username')} (token válido)")
except Exception as exc:
    partes.append(f"\ngetMe FALHOU: {exc}")

# 4. log
log = os.environ.get("PM2_LOG") or ""
interessantes = [l for l in log.splitlines()
                 if re.search(r"error|exception|traceback|conflict|409|"
                              r"terminated|unauthorized|timeout", l, re.I)]
partes.append(f"\n== linhas de erro no log ({len(interessantes)}) ==")
partes += [f"  {l[:200]}" for l in interessantes[-15:]] or ["  (nenhuma)"]
partes.append("\n== fim do log ==")
partes += [f"  {l[:180]}" for l in log.splitlines()[-12:]]

diga("[bot parado]\n" + "\n".join(partes))
PY

exit 0
