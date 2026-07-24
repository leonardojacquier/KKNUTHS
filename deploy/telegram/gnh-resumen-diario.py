#!/usr/bin/env python3
# ============================================================
# Resumo diário do gnhorizons.com -> Telegram (cron, 20h Asunción)
# Envia o resumo agregado do dia. Config em /opt/gnh_lib/gnh-resumen.env:
#   RESUMEN_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (vários = vírgula)
# Uso: python3 gnh-resumen-diario.py [offset_dias]   (0=hoje, 1=ontem)
# ============================================================
import json, os, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gnhresumen as R


def load_env(path='/opt/gnh_lib/gnh-resumen.env'):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        sys.exit(f'falta {path}')
    return env


def send_one(bot, chat, text):
    body = json.dumps({'chat_id': chat, 'text': text,
                       'disable_web_page_preview': True}).encode()
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot}/sendMessage',
        data=body, method='POST', headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            print(f'  {chat}: enviado ({r.status})'); return True
    except urllib.error.HTTPError as e:
        print(f'  {chat}: FALHOU {e.code} {e.read().decode()}'); return False


def main():
    offset = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    env = load_env()
    bot = env.get('TELEGRAM_BOT_TOKEN')
    ids = [c.strip() for c in str(env.get('TELEGRAM_CHAT_ID', '')).split(',') if c.strip()]
    if not bot or not ids:
        sys.exit('TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID vazio no .env')
    data = R.fetch(env['RESUMEN_TOKEN'], offset)
    msg = R.build_msg(data)
    n = sum(send_one(bot, c, msg) for c in ids)
    print(f'{data.get("fecha")} — enviado para {n} destinatário(s)')


if __name__ == '__main__':
    main()
