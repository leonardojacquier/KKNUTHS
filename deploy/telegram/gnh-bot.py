#!/usr/bin/env python3
# ============================================================
# Bot de estatísticas GNH — responde comandos sob demanda no Telegram.
# Comandos: /resumo (hoje) · /ontem · /semana · /ajuda
# Long-polling (getUpdates). Roda como serviço (systemd) no VPS.
#
# ⚠️ Um token de bot só pode ter UM escutador. Use um bot DEDICADO
#    (criado no @BotFather) — não o mesmo do agente-century se ele já
#    escutar comandos.
#
# Config em /opt/gnh_lib/gnh-bot.env  (chmod 600):
#   RESUMEN_TOKEN=...            (mesmo token de leitura do Supabase)
#   BOT_TOKEN=...                (token do bot dedicado)
#   ALLOWED_CHATS=id1,id2        (só estes chats podem consultar)
# ============================================================
import json, os, sys, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gnhresumen as R

ENV_PATH = '/opt/gnh_lib/gnh-bot.env'
COMMANDS = [
    {'command': 'resumo', 'description': 'Resumo dos acessos de hoje'},
    {'command': 'ontem', 'description': 'Resumo de ontem'},
    {'command': 'semana', 'description': 'Resumo dos últimos 7 dias'},
    {'command': 'ajuda', 'description': 'O que este bot faz'},
]
AYUDA = ('🤖 Bot de estatísticas do gnhorizons.com\n\n'
         '/resumo — acessos de hoje\n'
         '/ontem — acessos de ontem\n'
         '/semana — últimos 7 dias\n\n'
         'Dados anônimos e agregados (sem dados pessoais).')


def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def api(bot, method, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{bot}/{method}',
                                 data=body, method='POST',
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=70) as r:
        return json.loads(r.read())


def send(bot, chat, text):
    try:
        api(bot, 'sendMessage', {'chat_id': chat, 'text': text,
                                 'disable_web_page_preview': True})
    except Exception as e:
        print('send erro:', e)


def semana(rtoken):
    # soma simples dos 7 dias (chama a função por dia)
    tot_v = tot_e = tot_wa = tot_leads = 0
    prod = {}
    for off in range(7):
        d = R.fetch(rtoken, off)
        if not d or d.get('error'):
            continue
        tot_v += d.get('visitantes', 0)
        tot_e += d.get('eventos', 0)
        tot_wa += d.get('whatsapp', 0)
        tot_leads += d.get('leads', 0)
        for p in d.get('productos', []):
            prod[p['k']] = prod.get(p['k'], 0) + p['n']
    topp = sorted(prod.items(), key=lambda kv: -kv[1])[:6]
    L = ['📊 GNH · gnhorizons.com', 'Últimos 7 dias', '',
         f'👥 {tot_v} visitas · {tot_e} ações',
         f'💬 {tot_wa} cliques WhatsApp · 📥 {tot_leads} leads']
    if topp:
        L += ['', '🔧 Mais consultados: ' + ' · '.join(f'{k} ({n})' for k, n in topp)]
    return '\n'.join(L)


def handle(bot, rtoken, chat, text):
    cmd = text.strip().lower().split('@')[0].split()[0] if text.strip() else ''
    if cmd in ('/resumo', '/hoy', '/hoje'):
        send(bot, chat, R.build_msg(R.fetch(rtoken, 0)))
    elif cmd in ('/ontem', '/ayer'):
        send(bot, chat, R.build_msg(R.fetch(rtoken, 1)))
    elif cmd in ('/semana',):
        send(bot, chat, semana(rtoken))
    elif cmd in ('/ajuda', '/start', '/help'):
        send(bot, chat, AYUDA)
    # outras mensagens: ignora em silêncio


def main():
    env = load_env()
    bot = env['BOT_TOKEN']
    rtoken = env['RESUMEN_TOKEN']
    allowed = {c.strip() for c in env.get('ALLOWED_CHATS', '').split(',') if c.strip()}
    # registra o menu de comandos (o botão "/" no Telegram)
    try:
        api(bot, 'setMyCommands', {'commands': COMMANDS})
        print('menu de comandos registrado')
    except Exception as e:
        print('setMyCommands falhou:', e)
    offset = 0
    print('bot ativo, aguardando comandos…')
    while True:
        try:
            r = api(bot, 'getUpdates', {'offset': offset, 'timeout': 60})
            for upd in r.get('result', []):
                offset = upd['update_id'] + 1
                msg = upd.get('message') or upd.get('edited_message')
                if not msg or 'text' not in msg:
                    continue
                chat = str(msg['chat']['id'])
                if allowed and chat not in allowed:
                    send(bot, chat, '⛔ Chat não autorizado.')
                    continue
                handle(bot, rtoken, chat, msg['text'])
        except urllib.error.HTTPError as e:
            print('HTTP', e.code, e.read().decode()[:200]); time.sleep(5)
        except Exception as e:
            print('loop erro:', e); time.sleep(5)


if __name__ == '__main__':
    main()
