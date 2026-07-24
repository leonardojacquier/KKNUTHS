/* ============================================================
   FASE 6C — Eventos de negocio y leads → Supabase
   Sin cookies: sesión anónima por sessionStorage. Si las claves
   están vacías (proyecto pausado), todo es un no-op inofensivo.
   ============================================================ */

// Proyecto Supabase: Base de Dados Resultado - GNH (clave anon: solo INSERT via RLS)
const SUPABASE_URL = 'https://tqvrsusrbnyahpxhnwxe.supabase.co'
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRxdnJzdXNyYm55YWhweGhud3hlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY2ODYxMzEsImV4cCI6MjA5MjI2MjEzMX0.EIWs1fTwRVT_C5nAjIThvEzZ-ZMMNK_QiYTeHMn-wZo'

function sid(): string {
  try {
    let s = sessionStorage.getItem('gnh-sid')
    if (!s) {
      s = Math.random().toString(36).slice(2) + Date.now().toString(36)
      sessionStorage.setItem('gnh-sid', s)
    }
    return s
  } catch {
    return 'anon'
  }
}

/** Código corto de referencia (deriva de la sesión anónima): va al final del
 *  mensaje de WhatsApp — cuando el cliente escribe, el código permite cruzar
 *  su conversación con lo que navegó antes (events.session_id LIKE 'xxxx%'). */
export function refCode(): string {
  return sid().slice(0, 4).toUpperCase()
}

function post(table: string, row: Record<string, unknown>): Promise<boolean> {
  if (!SUPABASE_URL || !SUPABASE_KEY) return Promise.resolve(false)
  return fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: 'POST',
    keepalive: true,
    headers: {
      'Content-Type': 'application/json',
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      Prefer: 'return=minimal',
    },
    body: JSON.stringify(row),
  }).then((r) => r.ok).catch(() => false)
}

/** Registra un evento de negocio (fire-and-forget). */
export function track(type: string, detail = ''): void {
  void post('events', {
    type: type.slice(0, 40),
    detail: detail.slice(0, 200),
    path: location.pathname.slice(0, 120),
    session_id: sid(),
  })
}

/** Guarda un lead del formulario de cotización. Devuelve true si se grabó. */
export function saveLead(l: { nombre: string; empresa?: string; whatsapp: string; producto?: string; mensaje?: string }): Promise<boolean> {
  return post('leads', {
    nombre: l.nombre.slice(0, 120),
    empresa: (l.empresa ?? '').slice(0, 120),
    whatsapp: l.whatsapp.slice(0, 40),
    producto: (l.producto ?? '').slice(0, 200),
    mensaje: (l.mensaje ?? '').slice(0, 500),
    origen: location.pathname.slice(0, 120),
    session_id: sid(),
  })
}

/** Primer contacto de la sesión (first touch): zona horaria + idioma del
 *  navegador como señal de origen — sin IP y sin llamada externa. Se dispara
 *  una sola vez por sesión, en la página donde el visitante entra. */
export function trackLanding(): void {
  try {
    if (sessionStorage.getItem('gnh-landed')) return
    sessionStorage.setItem('gnh-landed', '1')
  } catch { /* sin storage: igual registramos, una vez por carga */ }
  let tz = ''
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || '' } catch { /* noop */ }
  const lang = (navigator.language || '').slice(0, 5)
  const entry = location.pathname.includes('/ventas') ? 'ventas'
    : location.pathname.includes('/institucional') ? 'institucional' : 'gateway'
  track('landing', `${tz}|${lang}|${entry}`)
}

/** Delegación global: [data-ev], clics a WhatsApp y descargas de fichas. */
export function autoTrack(): void {
  document.addEventListener('click', (e) => {
    const el = (e.target as Element).closest?.('a, button') as HTMLElement | null
    if (!el) return
    if (el.dataset.ev) { track(el.dataset.ev, el.dataset.detail ?? ''); return }
    const href = (el as HTMLAnchorElement).href ?? ''
    if (href.includes('wa.me')) {
      let d = ''
      try { d = decodeURIComponent(href.split('text=')[1] ?? '') } catch { /* noop */ }
      track('whatsapp', d.slice(0, 150))
    } else if (href.includes('/fichas/')) {
      track('ficha', href.split('/').pop() ?? '')
    }
  }, { capture: true, passive: true })
}
