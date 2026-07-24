# ============================================================
# Lógica compartilhada do resumo GNH (usada pelo cron e pelo bot).
# Consulta agregados do dia via a função protegida resumen_dia()
# de Supabase (chave pública + token de leitura). Sem PII.
# ============================================================
import json, urllib.request

SUPABASE_URL = 'https://tqvrsusrbnyahpxhnwxe.supabase.co'
ANON = ('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxdnJz'
        'dXNyYm55YWhweGhud3hlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2ODYxMzEsImV4cCI6MjA5'
        'MjI2MjEzMX0.EIWs1fTwRVT_C5nAjIThvEzZ-ZMMNK_QiYTeHMn-wZo')


def fetch(token, offset=0):
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
    if not d or d.get('error'):
        return f"⚠️ Resumo GNH: {(d or {}).get('error', 'sem dados')}"
    L = [f"📊 GNH · gnhorizons.com", f"Resumo de {d['fecha']}", '']
    L.append(f"👥 {d['visitantes']} visitantes · {d['eventos']} ações")
    portas = {p['k']: p['n'] for p in d.get('portas', [])}
    L.append(f"🚪 Ventas {portas.get('ventas', 0)} · Institucional {portas.get('institucional', 0)}")
    if d.get('origenes'):
        L.append(f"📍 Origem: {top(d['origenes'])}")
    if d.get('idiomas'):
        L.append(f"🌐 Idiomas: {top(d['idiomas'])}")
    L.append('')
    if d.get('productos'):
        L.append(f"🔧 Produtos consultados: {top(d['productos'])}")
    if d.get('negocios'):
        L.append(f"🏢 Negócios (institucional): {top(d['negocios'])}")
    if d.get('busquedas'):
        L.append(f"🔎 Buscas: {top(d['busquedas'])}")
    if d.get('busquedas_vacias'):
        L.append(f"❗ Buscas SEM resultado: {top(d['busquedas_vacias'])}")
    if d.get('fichas'):
        L.append(f"📄 Fichas técnicas abertas: {d['fichas']}")
    L.append('')
    L.append(f"💬 WhatsApp: {d.get('whatsapp', 0)} cliques · 📥 Leads: {d.get('leads', 0)}")
    if not d.get('whatsapp') and not d.get('leads'):
        L.append("(navegação sem contato)")
    jt = d.get('jornadas_top') or []
    if jt:
        L.append('')
        L.append('🧭 Jornadas:')
        for j in jt[:3]:
            marca = '✅ ' if j.get('contacto') else ''
            ruta = j['ruta'] if len(j['ruta']) <= 220 else j['ruta'][:217] + '…'
            L.append(f"{marca}{ruta}")
    return '\n'.join(L)
