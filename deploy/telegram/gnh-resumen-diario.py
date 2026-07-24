#!/usr/bin/env python3
# ============================================================
# Resumo diário do gnhorizons.com -> Telegram
# Roda no VPS via cron (20h Asunción). Lê agregados do dia via
# a função protegida resumen_dia() de Supabase (chave pública +
# token de leitura) e envia pelo bot do Telegram. Sem PII, sem
# chave secreta poderosa no servidor.
#
# Config: /opt/gnh_lib/gnh-resumen.env  (chmod 600) com:
#   RESUMEN_TOKEN=...
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_CHAT_ID=...
# Uso:   python3 gnh-resumen-diario.py [offset_dias]   (0=hoje, 1=ontem)
# ============================================================
import json, os, sys, urllib.request

SUPABASE_URL = 'https://tqvrsusrbnyahpxhnwxe.supabase.co'
# chave anon (pública por design, protegida por RLS; a mesma do site)
ANON = ('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxdnJz'
        'dXNyYm55YWhweGhud3hlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2ODYxMzEsImV4cCI6MjA5'
        'MjI2MjEzMX0.EIWs1fTwRVT_C5nAjIThvEzZ-ZMMNK_QiYTeHMn-wZo')

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

def fetch(token, offset):
    body = json.dumps({'p_token': token, 'p_offset': offset}).encode()
    req = urllib.request.Request(
        f'{SUPABASE_URL}/rest/v1/rpc/resumen_dia',
        data=body, method='POST',
        headers={'Content-Type': 'application/json', 'apikey': ANON,
                 'Authorization': f'Bearer {ANON}'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())

def top(items, sep=' · ', n=6):
    return sep.join(f"{it['k']} ({it['n']})" for it in items[:n]) if items else '—'

def build_msg(d):
    if d.get('error'):
        return f"⚠️ Resumo GNH: {d['error']}"
    L = []
    L.append(f"📊 GNH · gnhorizons.com")
    L.append(f"Resumo de {d['fecha']}")
    L.append('')
    L.append(f"👥 {d['visitantes']} visitantes · {d['eventos']} ações")
    portas = {p['k']: p['n'] for p in d['portas']}
    L.append(f"🚪 Ventas {portas.get('ventas',0)} · Institucional {portas.get('institucional',0)}")
    if d.get('origenes'):
        L.append(f"📍 Origem: {top(d['origenes'])}")
    if d.get('idiomas'):
        L.append(f"🌐 Idiomas: {top(d['idiomas'])}")
    L.append('')
    if d['productos']:
        L.append(f"🔧 Produtos consultados: {top(d['productos'])}")
    if d['negocios']:
        L.append(f"🏢 Negócios (institucional): {top(d['negocios'])}")
    if d['busquedas']:
        L.append(f"🔎 Buscas: {top(d['busquedas'])}")
    if d['busquedas_vacias']:
        L.append(f"❗ Buscas SEM resultado: {top(d['busquedas_vacias'])}")
    if d['fichas']:
        L.append(f"📄 Fichas técnicas abertas: {d['fichas']}")
    L.append('')
    L.append(f"💬 WhatsApp: {d['whatsapp']} cliques · 📥 Leads: {d['leads']}")
    if d['whatsapp'] == 0 and d['leads'] == 0:
        L.append("(navegação sem contato hoje)")
    jt = d.get('jornadas_top') or []
    if jt:
        L.append('')
        L.append('🧭 Jornadas do dia:')
        for j in jt[:3]:
            marca = '✅ ' if j.get('contacto') else ''
            ruta = j['ruta'] if len(j['ruta']) <= 220 else j['ruta'][:217] + '…'
            L.append(f"{marca}{ruta}")
    return '\n'.join(L)

def send_one(bot, chat, text):
    body = json.dumps({'chat_id': chat, 'text': text,
                       'disable_web_page_preview': True}).encode()
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot}/sendMessage',
        data=body, method='POST',
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            print(f'  {chat}: enviado ({r.status})')
            return True
    except urllib.error.HTTPError as e:
        print(f'  {chat}: FALHOU {e.code} {e.read().decode()}')
        return False

def send(bot, chats, text):
    # TELEGRAM_CHAT_ID pode ter vários IDs separados por vírgula
    ids = [c.strip() for c in str(chats).split(',') if c.strip()]
    if not bot or not ids:
        sys.exit('TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID vazio no .env')
    return sum(send_one(bot, c, text) for c in ids)

def main():
    offset = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    env = load_env()
    data = fetch(env['RESUMEN_TOKEN'], offset)
    msg = build_msg(data)
    n = send(env['TELEGRAM_BOT_TOKEN'], env['TELEGRAM_CHAT_ID'], msg)
    print(f'{data.get("fecha")} — enviado para {n} destinatário(s)')
    print('enviado:', data.get('fecha'))

if __name__ == '__main__':
    main()
