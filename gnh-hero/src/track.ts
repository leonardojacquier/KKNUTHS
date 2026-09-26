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

/* ---------- origen de la visita (first touch) ----------
   El referrer solo existe en la página de entrada: si no se guarda ahí, se
   pierde. Se resuelve una vez por sesión y viaja en TODOS los eventos, así
   cualquier conversión se puede atribuir a su origen.

   Ojo: Google Maps y la Búsqueda de Google mandan el mismo referrer
   (https://www.google.com/). Para separar el perfil de empresa hay que poner
   ?utm_source=google-business en el enlace del sitio dentro del perfil — el
   utm_source siempre gana sobre el referrer. */
const REDES: Array<[RegExp, string]> = [
  [/(^|\.)maps\.google\./, 'google-maps'],
  [/com\.google\.android\.apps\.maps/, 'google-maps'],
  [/(^|\.)google\./, 'google'],
  [/(^|\.)instagram\.com$/, 'instagram'],
  [/(^|\.)(facebook|fb)\.com$/, 'facebook'],
  [/(wa\.me|whatsapp\.com)$/, 'whatsapp'],
  [/(^|\.)tiktok\.com$/, 'tiktok'],
  [/(^|\.)(linkedin\.com|lnkd\.in)$/, 'linkedin'],
  [/(^|\.)(twitter\.com|x\.com|t\.co)$/, 'x'],
  [/(^|\.)(bing\.com|duckduckgo\.com|search\.yahoo\.com)$/, 'buscador'],
  // motores generativos: es lo que el trabajo de GEO (llms.txt, JSON-LD) busca mover
  [/(^|\.)(chatgpt\.com|openai\.com)$/, 'chatgpt'],
  [/(^|\.)perplexity\.ai$/, 'perplexity'],
  [/(^|\.)(gemini|bard)\.google\.com$/, 'gemini'],
  [/(^|\.)claude\.ai$/, 'claude'],
]

function origen(): string {
  try {
    const guardado = sessionStorage.getItem('gnh-ref')
    if (guardado) return guardado
  } catch { /* sin storage: se recalcula por carga, no rompe */ }

  let o = ''
  try {
    o = (new URLSearchParams(location.search).get('utm_source') ?? '')
      .toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 30)
  } catch { /* noop */ }

  if (!o) {
    const r = document.referrer
    if (!r) o = 'directo'
    else {
      let h = ''
      try { h = new URL(r).hostname.toLowerCase().replace(/^www\./, '') } catch { /* noop */ }
      if (!h) o = 'directo'
      else if (h === location.hostname.replace(/^www\./, '')) o = 'interno'
      else o = REDES.find(([re]) => re.test(h))?.[1] ?? h.slice(0, 40)
    }
  }

  try { sessionStorage.setItem('gnh-ref', o) } catch { /* noop */ }
  return o
}

/** Registra un evento de negocio (fire-and-forget). */
export function track(type: string, detail = ''): void {
  void post('events', {
    type: type.slice(0, 40),
    detail: detail.slice(0, 200),
    path: location.pathname.slice(0, 120),
    session_id: sid(),
    ref: origen(),
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

/** Aparato del visitante. Decide más que parece: en celular el CTA tiene que
 *  estar visible sin scroll, y una ficha PDF de 3 MB es otra experiencia. */
function aparato(): string {
  try {
    const uad = (navigator as unknown as { userAgentData?: { mobile?: boolean } }).userAgentData
    if (uad && typeof uad.mobile === 'boolean') return uad.mobile ? 'celular' : 'computadora'
  } catch { /* noop */ }
  const ua = navigator.userAgent || ''
  // iPad moderno se anuncia como Mac: el desempate es la pantalla táctil
  if (/iPad|Tablet/i.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return 'tablet'
  if (/Mobi|Android|iPhone|iPod/i.test(ua)) return 'celular'
  return 'computadora'
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
  const base = location.pathname.includes('/promo') ? 'promo'
    : location.pathname.includes('/ventas') ? 'ventas'
    : location.pathname.includes('/institucional') ? 'institucional' : 'gateway'
  // red de origen cuando el enlace trae ?utm_source= (instagram, facebook, whatsapp…)
  let src = ''
  try { src = (new URLSearchParams(location.search).get('utm_source') ?? '').toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 20) } catch { /* noop */ }
  const entry = src ? `${base}-${src}` : base
  // qué campaña, no sólo qué red: ?utm_campaign=generador-38kva
  let camp = ''
  try {
    camp = (new URLSearchParams(location.search).get('utm_campaign') ?? '')
      .toLowerCase().replace(/[^a-z0-9-]/g, '').slice(0, 40)
  } catch { /* noop */ }
  // el formato crece por el final: fila vieja con 3 campos sigue leyéndose igual
  track('landing', `${tz}|${lang}|${entry}|${aparato()}|${camp}`)
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
