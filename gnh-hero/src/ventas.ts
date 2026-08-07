import './style.css'
import './ventas.css'
import { mountFooter } from './footer'
import { ADITIVOS, type Aditivo } from './aditivos-data'
import { autoTrack, refCode, saveLead, track, trackLanding } from './track'

const WA = '595995360060'
const wa = (msg: string) => `https://wa.me/${WA}?text=${encodeURIComponent(`${msg} (ref ${refCode()})`)}`

/* ============================================================
   CATÁLOGO — estrutura de dados. Preencher conforme as infos chegam.
   Cada categoria: título, ícone, link de ficha/catálogo (externo), produtos.
   Cada produto: nome, marca, imagem (placeholder até chegar), nota.
   ============================================================ */
import { CATALOG, SPECS, type Product, type Category } from './catalogo-data'
void SPECS  // reexportado para o gerador de páginas estáticas

/* ---------- ícones ---------- */
const ICONS: Record<string, string> = {
  hook: '<path d="M5 21V5.5L11 3v18M5 21h6M11 7h8.5M19.5 7v4.5"/><path d="M21.5 14a2.2 2.2 0 1 1-4.4 0"/>',
  flask: '<path d="M10 3h4M11 3v5.2L5.6 17.5A2 2 0 0 0 7.4 21h9.2a2 2 0 0 0 1.8-3.5L13 8.2V3"/><path d="M8.2 15h7.6"/>',
  truck: '<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13.5l9 5 9-5"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  arrow: '<path d="M4 12h15M13 6l6 6-6 6"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  gear: '<circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5 5l2.1 2.1M16.9 16.9L19 19M19 5l-2.1 2.1M7.1 16.9L5 19"/>',
  chevL: '<path d="M15 5l-7 7 7 7"/>',
  chevR: '<path d="M9 5l7 7-7 7"/>',
  spray: '<path d="M3 9h7l2-2h3v6h-3l-2 -2H3z"/><path d="M7 11v6a2 2 0 0 0 2 2h2"/><path d="M18.5 5.2l1.8-1.2M19.6 8.5h2.2M18.5 11.8l1.8 1.2"/>',
  floor: '<rect x="3" y="6" width="18" height="12" rx="1.5"/><path d="M3 12h18M9 6v6M15 12v6"/>',
}
const icon = (k: string, cls = '') =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="${cls}">${ICONS[k] ?? ''}</svg>`

/* ============================================================
   ADITIVOS — iconos por familia (sin fotos): pictograma + anillo dorado
   ============================================================ */
const FAM_PICT: Record<string, string> = {
  plastificantes: '<path d="M12 3.5c3 4.4 5.6 7.2 5.6 10a5.6 5.6 0 1 1-11.2 0c0-2.8 2.6-5.6 5.6-10z"/>',
  impermeabilizantes: '<path d="M12 3l7 2.8v5.1c0 4.5-2.9 8-7 10.1-4.1-2.1-7-5.6-7-10.1V5.8z"/><path d="M12 8.2c1.6 2.3 3 3.8 3 5.3a3 3 0 1 1-6 0c0-1.5 1.4-3 3-5.3z"/>',
  cura: '<path d="M7 15a5 5 0 0 1 .8-9.9A6 6 0 0 1 19 7.5 4 4 0 0 1 18 15"/><path d="M8 18.5v2M12 17.5v2M16 18.5v2"/>',
  'control-fraguado': '<circle cx="12" cy="13" r="7.5"/><path d="M12 9v4.2l2.8 1.6M9.5 3h5"/>',
  desmoldantes: '<path d="M4 8.2 12 4l8 4.2-8 4.2z"/><path d="M4 8.2v7.6l8 4.2 8-4.2V8.2M12 12.4v7.6"/>',
  pisos: '<path d="M5.5 8.5h13l2.5 3.5-9 8.5-9-8.5z"/><path d="M5.5 8.5 12 12l6.5-3.5M12 12v8.5"/>',
  fibras: '<path d="M5 4c3 5 3 11 0 16M12 4c3 5 3 11 0 16M19 4c-3 5-3 11 0 16" transform="rotate(14 12 12)"/>',
  pigmentos: '<path d="M12 3a9 9 0 1 0 .5 18c1.6 0 2.1-1 1.5-2-.7-1.2.1-2.5 1.5-2.5H17a4.5 4.5 0 0 0 4-4.5C21 7 17 3 12 3z"/><circle cx="8" cy="10" r="1" fill="currentColor"/><circle cx="12" cy="7.5" r="1" fill="currentColor"/><circle cx="16" cy="10" r="1" fill="currentColor"/>',
  selladores: '<path d="M4 11h11v6H4zM15 12.5h3.6l1.9 1.5-1.9 1.5H15zM7 11V8h6v3M9.5 8V6"/>',
  limpieza: '<path d="M8 9h6v11a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 8 20zM9 9V6.5h4V9M10 6.5V4h5.5M17 4h2"/><path d="M17.5 9.5l.9 1.9 2 .3-1.5 1.4.4 2-1.8-1-1.8 1 .4-2-1.5-1.4 2-.3z" fill="currentColor" stroke="none"/>',
  otros: ICONS.flask,
}
function aditivoIconSVG(a: Aditivo): string {
  const pict = FAM_PICT[a.family] ?? FAM_PICT.otros
  return `
  <svg viewBox="0 0 200 150" class="adi-svg" role="img" aria-label="${a.familyLabel}">
    <defs>
      <linearGradient id="gold-${a.slug}" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#F7E7B4"/><stop offset=".45" stop-color="#D4AF37"/>
        <stop offset=".75" stop-color="#8C6A1D"/><stop offset="1" stop-color="#E6C96A"/>
      </linearGradient>
      <radialGradient id="glow-${a.slug}" cx=".5" cy=".42" r=".65">
        <stop offset="0" stop-color="${a.color}" stop-opacity=".28"/><stop offset="1" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <rect width="200" height="150" fill="url(#glow-${a.slug})"/>
    <circle cx="100" cy="64" r="40" fill="rgba(255,255,255,.04)" stroke="url(#gold-${a.slug})" stroke-width="2.6"/>
    <circle cx="100" cy="64" r="33.5" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="1"/>
    <g transform="translate(78,42) scale(1.83)" fill="none" stroke="${a.color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${pict}</g>
    <text x="100" y="124" text-anchor="middle" font-family="Satoshi,Arial,sans-serif" font-weight="800" font-size="15" letter-spacing="1.4" fill="#fff">${a.initials}</text>
    <rect x="70" y="136" width="60" height="2.4" rx="1.2" fill="url(#gold-${a.slug})"/>
  </svg>`
}

function aditivoCard(a: Aditivo): string {
  const msg = `Hola, me interesa el aditivo ${a.name}`
  return `
    <article class="v-card adi-card" data-s="${deacc(`${a.name} ${a.familyLabel} ${a.sub} ${a.desc} ${a.kw.join(' ')}`)}">
      <div class="v-card-media adi-media" style="--fam:${a.color}">${aditivoIconSVG(a)}</div>
      <div class="v-card-body">
        <span class="v-brand" style="color:${a.color}">${a.familyLabel}</span>
        <h3 class="v-name">${a.name}</h3>
        ${a.desc ? `<p class="v-note">${a.desc.slice(0, 130)}${a.desc.length > 130 ? '…' : ''}</p>` : ''}
        <div class="adi-actions">
          ${a.ficha ? `<a class="adi-doc" href="../fichas/${a.slug}.html">Ficha técnica</a>
          <a class="adi-doc adi-pdf" href="../fichas/pdf/${a.slug}.pdf" download>PDF</a>` : ''}
          <a class="v-cta" href="${wa(msg)}" target="_blank" rel="noopener" data-ev="product" data-detail="${a.name}">Consultar ${icon('arrow', 'v-cta-i')}</a>
        </div>
      </div>
    </article>`
}

/* ---------- buscador inteligente (client-side, "tipo Google") ---------- */
const deacc = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

// puentes ES↔EN/PT y de problema→producto (los nombres comerciales están en inglés)
const ALIAS: Record<string, string[]> = {
  fibra: ['fiber'], fibras: ['fiber'], fiber: ['fibra'],
  hormigon: ['concreto'], concreto: ['hormigon'],
  mortero: ['argamassa', 'stable'], argamassa: ['mortero'],
  impermeabilizar: ['impermeabilizante', 'seal', 'admix'], impermeable: ['impermeabilizante', 'seal'],
  sellar: ['seal', 'sellador'], sellado: ['seal', 'sellador'],
  limpiar: ['removedor', 'bio', 'limpieza'], limpieza: ['removedor', 'bio'],
  piso: ['hardfloor', 'siltop', 'floor', 'litio'], pisos: ['hardfloor', 'siltop', 'floor', 'litio'],
  cura: ['curamix', 'curado'], curado: ['cura', 'curamix'], curar: ['cura', 'curamix'],
  desmoldante: ['desform'], desmolde: ['desform'], encofrado: ['desform', 'desmoldante'],
  acelerar: ['acelerador', 'accelera'], acelerador: ['accelera'], acelerante: ['accelera', 'acelerador'],
  retardador: ['stabilizer', 'stable'], retardante: ['stabilizer', 'stable'],
  plastificante: ['plast', 'flow'], superplastificante: ['superplast', 'flow'],
  fluidez: ['flow', 'superplast'], bombear: ['bombeo', 'flow'],
  color: ['pigmento', 'ferrox'], pintura: ['pigmento', 'color'], colorante: ['pigmento', 'ferrox'],
  grieta: ['fibra', 'fiber', 'fisura'], grietas: ['fibra', 'fiber', 'fisura'],
  rajadura: ['fisura', 'fibra', 'fiber'], fisura: ['fibra', 'fiber'], fisuras: ['fibra', 'fiber'],
  bloque: ['vibroprensado', 'superplast', 'press'], bloques: ['vibroprensado', 'superplast', 'press'],
  grua: ['araña'], excavadora: ['miniexcavadora'],
  // PT→ES (clientes brasileños): máquinas por su nombre en portugués
  escavadeira: ['excavadora'], retroescavadeira: ['retroexcavadora'],
  empilhadeira: ['montacargas', 'apilador', 'transpaleta'], paleteira: ['transpaleta'],
  guindaste: ['grua', 'araña'], betoneira: ['mezcladora', 'central'],
  carregadeira: ['minicargadora'], pala: ['minicargadora', 'bulldozer'],
  gerador: ['electrogeno'], generador: ['electrogeno'],
  regua: ['regla'], alisadora: ['allanadora'], acabadora: ['allanadora'],
  serra: ['cortadora'], caminhao: ['camion'], rolo: ['rodillo'],
  estaca: ['pilotes', 'hincadora'], andaime: ['plataforma'],
  // variantes PT/ES que aparecieron en las búsquedas reales del sitio
  escavadora: ['excavadora', 'miniexcavadora'], miniescavadeira: ['miniexcavadora'],
  retroescavadora: ['retroexcavadora'],
  tesoura: ['tijera'], plataformas: ['plataforma', 'tijera', 'mastil'],
  elevatoria: ['plataforma', 'elevadora'], elevador: ['plataforma', 'elevadora'],
  munck: ['grua', 'camion'], munk: ['grua', 'camion'], guincho: ['grua'],
  reboco: ['revoque', 'proyectora'], revoque: ['proyectora', 'mortero'],
  projetora: ['proyectora'], projecao: ['proyeccion', 'proyectora'],
  furadeira: ['perforadora'], perfuratriz: ['perforadora'],
  concreteira: ['central', 'mezcladora'], bomba: ['bombeadora', 'transportadora'],
  esteira: ['orugas'], lagarta: ['orugas'],
  transpalete: ['transpaleta'], garfo: ['montacargas'],
  telescopica: ['telescopico', 'manipulador'], manipulador: ['telescopico'],
}

/** ¿'a' y 'b' difieren en UN caracter como máximo? (distancia de edición ≤ 1).
 *  Corta apenas pasa de 1 — no hace falta la matriz completa. */
function casiIgual(a: string, b: string): boolean {
  if (Math.abs(a.length - b.length) > 1) return false
  let i = 0, j = 0, dif = 0
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { i++; j++; continue }
    if (++dif > 1) return false
    if (a.length > b.length) i++
    else if (a.length < b.length) j++
    else { i++; j++ }
  }
  return dif + (a.length - i) + (b.length - j) <= 1
}

// expande un término con alias + radicales (plural/terminaciones) — estilo Google
function variantsOf(t: string): string[] {
  const out = new Set<string>([t])
  for (const a of ALIAS[t] ?? []) out.add(a)
  // tipeo parcial: 'esc' ya activa la llave 'escavadeira' (y sus alias).
  // Con umbral 4 el cliente que escribía 'esc'/'exc' no llegaba a la máquina.
  if (t.length >= 3) {
    for (const k of Object.keys(ALIAS)) {
      if (k.startsWith(t)) { out.add(k); for (const a of ALIAS[k]) out.add(a) }
    }
  }
  // un error de tipeo no puede costar la visita: 'esxa' → 'esca…' → excavadora.
  // Solo si nada coincidió antes, para no ensuciar búsquedas que ya funcionan.
  if (t.length >= 4 && out.size === 1) {
    for (const k of Object.keys(ALIAS)) {
      if (casiIgual(t, k.slice(0, t.length))) { out.add(k); for (const a of ALIAS[k]) out.add(a) }
    }
  }
  for (const w of [...out]) {
    if (w.endsWith('s') && w.length >= 5) out.add(w.slice(0, -1))
    if (w.length >= 6) out.add(w.slice(0, w.length - 2))   // impermeabilizar → impermeabiliz…
    if (w.length >= 9) out.add(w.slice(0, w.length - 4))
  }
  return [...out].filter((v) => v.length >= 3 || v === t)
}
const termGroups = (q: string) => deacc(q).split(/\s+/).filter((t) => t.length >= 2).map(variantsOf)
const hitIn = (hay: string, vars: string[]) => vars.some((v) => hay.includes(v))

interface Hit { score: number; html: string; name: string }
function searchAll(q: string): Hit[] {
  const groups = termGroups(q)
  if (!groups.length) return []
  const hits: Hit[] = []
  const equipHits: Hit[] = []
  for (const a of ADITIVOS) {
    let s = 0, matched = 0
    const name = deacc(a.name), fam = deacc(a.familyLabel), sub = deacc(a.sub), desc = deacc(a.desc)
    const kwstr = a.kw.join(' ')
    for (const vars of groups) {
      let g = 0
      if (hitIn(name, vars)) g += 10
      if (hitIn(deacc(a.initials), vars)) g += 6
      if (hitIn(fam, vars)) g += 6
      if (hitIn(sub, vars)) g += 4
      if (hitIn(kwstr, vars)) g += 3
      if (hitIn(desc, vars)) g += 1
      if (g > 0) matched++
      s += g
    }
    if (matched === groups.length) s += 6   // bonus: todos los términos presentes
    if (s > 0) hits.push({ score: s, html: aditivoCard(a), name: a.name })
  }
  for (const c of CATALOG) {
    // productos con subgrupos (Equipos) Y productos directos (Morteros, etc.)
    const prods = [...(c.groups ?? []).flatMap((g) => g.products), ...(c.products ?? [])]
    for (const p of prods) {
      let s = 0
      const name = deacc(p.name), note = deacc(p.note ?? ''), tags = deacc((p.tags ?? []).join(' '))
      for (const vars of groups) {
        if (hitIn(name, vars)) s += 10
        if (hitIn(tags, vars)) s += 8
        if (hitIn(note, vars)) s += 3
      }
      if (s > 0) equipHits.push({ score: s, html: productCard(p), name: p.name })
    }
  }
  // cuota garantizada: los equipos que matchean SIEMPRE entran (hasta 8), no los tapan los aditivos
  hits.sort((x, y) => y.score - x.score)
  equipHits.sort((x, y) => y.score - x.score)
  return [...equipHits.slice(0, 8), ...hits.slice(0, 16)].sort((x, y) => y.score - x.score).slice(0, 24)
}

/* registra lo que la gente escribe en las búsquedas — cuando deja de tipear
   (1,6s), no tecla por tecla. 'busqueda' = con resultados; 'busqueda-vacia' =
   sin resultados (oro para saber qué falta en el catálogo). */
let bqT = 0
let bqLast = ''
function trackSearch(q: string, hits: number, donde: string): void {
  window.clearTimeout(bqT)
  if (q.length < 3) return
  bqT = window.setTimeout(() => {
    const key = `${q}|${donde}`
    if (key === bqLast) return
    bqLast = key
    track(hits ? 'busqueda' : 'busqueda-vacia', donde === 'general' ? q : `${q} [${donde}]`)
  }, 1600)
}

function initBuscador(): void {
  const input = document.getElementById('buscador-input') as HTMLInputElement | null
  const out = document.getElementById('buscador-results')
  if (!input || !out) return
  let t = 0
  input.addEventListener('input', () => {
    window.clearTimeout(t)
    t = window.setTimeout(() => {
      const q = input.value.trim()
      if (q.length < 2) { out.innerHTML = ''; out.classList.remove('has'); return }
      const hits = searchAll(q)
      trackSearch(q, hits.length, 'general')
      out.classList.add('has')
      out.innerHTML = hits.length
        ? `<p class="bsc-count">${hits.length} resultado${hits.length > 1 ? 's' : ''} para “${q}”</p><div class="bsc-grid">${hits.map((h) => h.html).join('')}</div>`
        : `<p class="bsc-empty">No encontramos resultados para “${q}”. <a href="${wa('Hola, busco: ' + q)}" target="_blank" rel="noopener">Consultá por WhatsApp</a> — seguro podemos ayudarte.</p>`
    }, 160)
  })
}

/* ============================================================
   CARROSSEL DO HERO — líneas destacadas (productos foco).
   Agregar aquí a medida que llega el material (BIO 360, Macro-fibras…).
   ============================================================ */
// bleed:true  → la imagen cubre TODO el banner (full-bleed, para fotos 21:9 de ambiente)
// bleed:false → recorte del producto centrado a la derecha (imágenes con fondo transparente)
// eyebrow: reemplaza el rótulo "Línea destacada"; launch:true lo pinta como sticker rojo
// seal: [texto grande, texto chico] — carimbo circular a la derecha del banner
// url/cta: el botón principal lleva a una landing propia en vez de abrir WhatsApp directo
interface Featured { name: string; tag: string; cat: string; bleed?: boolean; img?: string; imgMobile?: string; videoWebm?: string; videoMp4?: string; poster?: string; eyebrow?: string; launch?: boolean; url?: string; cta?: string; seal?: [string, string] }
const FEATURED: Featured[] = [
  // LANZAMIENTO ACTIVO — al terminar, borrar esta línea y restaurar el slide estático
  // de ventas/index.html + el preload del <head> a plataformas-o14 (ver comentario allí).
  { name: 'Generador 38 kVA', tag: 'Motor Ricardo, ¡pronta entrega! Ahora en GNH — vení a conocerlo en nuestro Show Room.', cat: 'equipos', bleed: true, videoWebm: '../video/generador.webm', videoMp4: '../video/generador.mp4', poster: '../img/prod/generador-poster-v2.jpg', eyebrow: 'Lanzamiento', launch: true, seal: ['Pronta<br>entrega', 'Ya en stock'], url: '/promo/generador-38kva/', cta: 'Ver el lanzamiento' },
  { name: 'Plataformas', tag: 'Plataforma electro-hidráulica de elevación de personal para trabajos en altura.', img: '../img/prod/plataformas-o.jpg', cat: 'equipos', bleed: true },
  { name: 'Grúas Araña', tag: 'Grúas araña de orugas de 1,5 t a 70 t. Compactas, potentes y de fácil acceso.', cat: 'equipos', bleed: true, videoWebm: '../video/grua.webm', videoMp4: '../video/grua.mp4', poster: '../img/prod/grua-poster.jpg' },
  { name: 'Mini Central de Concreto', tag: 'Mezcla y bombeo de concreto en un solo equipo, con motor Cummins.', img: '../img/prod/mini-central-o.jpg', cat: 'equipos', bleed: true },
  { name: 'Minibomba Eléctrica', tag: 'Bomba eléctrica compacta para el transporte de concreto en obra.', img: '../img/prod/minibomba-o.jpg', imgMobile: '../img/prod/minibomba-mobile-o.jpg', cat: 'equipos', bleed: true },
  { name: 'Mezcladora de Mortero', tag: 'Ideal para la aplicación de AC-I y AC-III.', img: '../img/prod/mezcladora-mortero-o.jpg', cat: 'equipos', bleed: true },
  { name: 'BIO 360', tag: 'Máxima potencia en limpieza de concreto, 100% biodegradable. Tan seguro que se aplica sin EPP.', cat: 'aditivos', bleed: true, videoWebm: '../video/bio360.webm', videoMp4: '../video/bio360.mp4', poster: '../img/prod/bio360-poster.jpg' },
  { name: 'Macro-fibras', tag: 'Refuerzo estructural del concreto con macro-fibras sintéticas.', cat: 'aditivos', bleed: true, videoWebm: '../video/macrofibras.webm', videoMp4: '../video/macrofibras.mp4', poster: '../img/prod/macrofibras-poster.jpg' },
]
const PAUSE_ICO = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="7" y="6" width="3.4" height="12" rx="1"/><rect x="13.6" y="6" width="3.4" height="12" rx="1"/></svg>'
const PLAY_ICO = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z"/></svg>'

function renderHeroCarousel(): void {
  const root = document.getElementById('hero-carousel')
  if (!root || !FEATURED.length) return
  const DUR = 5200
  root.className = 'v-showcase'
  root.style.setProperty('--vh-dur', DUR + 'ms')
  const slideHTML = (f: Featured, i: number) => `
        <article class="vh-slide${i === 0 ? ' is-active' : ''}${f.bleed ? ' is-bleed' : ''}" data-i="${i}">
          <div class="vh-media">${f.videoMp4
            ? `<video class="vh-el" muted loop playsinline preload="metadata" poster="${f.poster || ''}"><source src="${f.videoWebm}" type="video/webm"><source src="${f.videoMp4}" type="video/mp4"></video>`
            : `<picture>${f.imgMobile ? `<source media="(max-width: 760px)" srcset="${f.imgMobile.replace('.jpg', '.webp')}" type="image/webp"><source media="(max-width: 760px)" srcset="${f.imgMobile}">` : ''}<source srcset="${f.img!.replace('.jpg', '.webp')}" type="image/webp"><img class="vh-el" src="${f.img}" alt="${f.name}" ${i === 0 ? 'fetchpriority="high"' : 'loading="lazy"'}></picture>`}</div>
          ${f.seal ? `<div class="vh-seal" aria-hidden="true"><b>${f.seal[0]}</b><i>${f.seal[1]}</i></div>` : ''}
          <div class="vh-inner">
            <div class="vh-copy">
              <span class="vh-eyebrow${f.launch ? ' is-launch' : ''}">${f.eyebrow ?? 'Línea destacada'}</span>
              <h2 class="vh-title">${f.name}</h2>
              <p class="vh-desc">${f.tag}</p>
              <div class="vh-btns">
                ${f.url
                  ? `<a class="vh-cta" href="${f.url}" data-ev="product" data-detail="${f.name}">${f.cta ?? 'Ver más'} ${icon('arrow', 'vh-cta-i')}</a>`
                  : `<a class="vh-cta" href="${wa(`Hola, quiero cotizar: ${f.name}`)}" target="_blank" rel="noopener" data-ev="product" data-detail="${f.name}">Cotizar ${icon('arrow', 'vh-cta-i')}</a>`}
                <button class="vh-cta vh-cta-ghost" data-cat="${f.cat}">Ver productos</button>
              </div>
            </div>
          </div>
        </article>`
  const arrowsHTML = `
      <button class="vh-arrow vh-prev" aria-label="Anterior">${icon('chevL')}</button>
      <button class="vh-arrow vh-next" aria-label="Siguiente">${icon('chevR')}</button>`
  const controlsHTML = `
    <div class="vh-controls">
      <div class="vh-segs">${FEATURED.map((_, i) =>
        `<button class="vh-seg" data-i="${i}" aria-label="Ver ${i + 1}"><span class="vh-seg-fill"></span></button>`).join('')}</div>
      <button class="vh-pause" aria-label="Pausar o reanudar" aria-pressed="false">${PAUSE_ICO}</button>
    </div>`

  // hidratación: si el primer slide ya vino estático en el HTML (pintado antes
  // del JS = LCP temprano), se conserva intacto y solo se agrega el resto
  const staticTrack = root.querySelector('.vh-track')
  if (staticTrack && staticTrack.querySelector('.vh-slide')) {
    staticTrack.insertAdjacentHTML('beforeend', FEATURED.slice(1).map((f, i) => slideHTML(f, i + 1)).join('') + arrowsHTML)
    root.insertAdjacentHTML('beforeend', controlsHTML)
  } else {
    root.innerHTML = `<div class="vh-track">${FEATURED.map(slideHTML).join('')}${arrowsHTML}</div>${controlsHTML}`
  }

  const slides = Array.from(root.querySelectorAll<HTMLElement>('.vh-slide'))
  const segs = Array.from(root.querySelectorAll<HTMLElement>('.vh-seg'))
  const fills = Array.from(root.querySelectorAll<HTMLElement>('.vh-seg-fill'))
  const pauseBtn = root.querySelector<HTMLElement>('.vh-pause')!
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  let idx = 0, paused = reduce

  const paint = () => {
    slides.forEach((s, i) => {
      const active = i === idx
      s.classList.toggle('is-active', active)
      const vid = s.querySelector('video')
      if (vid) { if (active) { try { vid.currentTime = 0 } catch { /* noop */ } vid.play().catch(() => {}) } else { vid.pause() } }
    })
    segs.forEach((s, i) => { s.classList.remove('is-active', 'is-done'); if (i < idx) s.classList.add('is-done') })
    const cur = segs[idx]; void cur.offsetWidth; cur.classList.add('is-active') // reinicia la animación de llenado
  }
  const go = (n: number) => { idx = (n + FEATURED.length) % FEATURED.length; paint() }
  const next = () => go(idx + 1)
  const prev = () => go(idx - 1)

  // el avance lo dispara el fin de la animación del segmento activo (se sincroniza con la barra)
  fills.forEach((fl) => fl.addEventListener('animationend', () => {
    if (!paused && segs[idx].classList.contains('is-active')) next()
  }))
  const setPaused = (p: boolean) => {
    paused = p
    root.classList.toggle('is-paused', p)
    pauseBtn.setAttribute('aria-pressed', String(p))
    pauseBtn.innerHTML = p ? PLAY_ICO : PAUSE_ICO
  }
  pauseBtn.addEventListener('click', () => setPaused(!paused))
  root.querySelector('.vh-next')!.addEventListener('click', next)
  root.querySelector('.vh-prev')!.addEventListener('click', prev)
  segs.forEach((s) => s.addEventListener('click', () => go(Number(s.dataset.i))))
  root.querySelectorAll<HTMLElement>('.vh-cta[data-cat]').forEach((btn) =>
    btn.addEventListener('click', () => selectCategory(btn.dataset.cat || 'equipos', true)))
  // el slide estático trae el link de WhatsApp sin (ref): lo normaliza acá.
  // Solo toca links de WhatsApp — un slide puede apuntar a una landing propia.
  root.querySelectorAll<HTMLAnchorElement>('a.vh-cta[data-detail]').forEach((a) => {
    if (!a.href.includes('wa.me')) return
    if (!decodeURIComponent(a.href).includes('(ref ')) a.href = wa(`Hola, quiero cotizar: ${a.dataset.detail}`)
  })

  const track = root.querySelector<HTMLElement>('.vh-track')!
  let x0: number | null = null
  track.addEventListener('touchstart', (e) => { x0 = (e as TouchEvent).touches[0].clientX }, { passive: true })
  track.addEventListener('touchend', (e) => {
    if (x0 !== null) { const dx = (e as TouchEvent).changedTouches[0].clientX - x0; if (Math.abs(dx) > 40) (dx < 0 ? next() : prev()) }
    x0 = null
  }, { passive: true })

  paint()
  if (reduce) setPaused(true)
}

/* ---------- render do catálogo ---------- */
/** slug da página estática do produto (só existe para quem tem tabela de specs) */
const prodSlug = (name: string) => name.normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[()./]/g, ' ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

function productCard(p: Product): string {
  const msg = `Hola, me interesa: ${p.name}${p.brand ? ' (' + p.brand + ')' : ''}`
  const href = p.specs ? `/ventas/${prodSlug(p.name)}/` : ''   // página propia con specs y ficha
  const media = p.img ? `<img src="${p.img}" alt="${p.name}" loading="lazy">` : `<span class="ph">${p.name}</span>`
  return `
    <article class="v-card" data-s="${deacc(`${p.name} ${p.brand ?? ''} ${p.note ?? ''} ${(p.tags ?? []).join(' ')}`)}">
      <div class="v-card-media">${href
        ? `<a href="${href}" class="v-media-link" aria-label="Ver ficha de ${p.name}">${media}<span class="v-media-hint">Ver detalles</span></a>`
        : media}</div>
      <div class="v-card-body">
        ${p.brand ? `<span class="v-brand">${p.brand}</span>` : ''}
        <h3 class="v-name">${href ? `<a href="${href}">${p.name}</a>` : p.name}</h3>
        ${p.note ? `<p class="v-note">${p.note}</p>` : ''}
        ${p.specs ? `<details class="v-specs"><summary>Modelos y especificaciones</summary>
          <div class="v-specs-scroll"><table>
            <thead><tr>${p.specs.h.map((th) => `<th>${th}</th>`).join('')}</tr></thead>
            <tbody>${p.specs.r.map((row) => `<tr>${row.map((c) => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody>
          </table></div>
        </details>` : ''}
        <div class="v-card-actions">
          ${href ? `<a class="v-doc" href="${href}">Ver detalles</a>` : ''}
          <a class="v-cta" href="${wa(msg)}" target="_blank" rel="noopener" data-ev="product" data-detail="${p.name}">Consultar ${icon('arrow', 'v-cta-i')}</a>
        </div>
      </div>
    </article>`
}

/* painel do deck (categoria) */
function deckPanel(c: Category): string {
  return `
    <article class="v-cat-panel" data-cat="${c.id}" tabindex="0" role="button" aria-label="Ver productos de ${c.title}">
      <div class="ghost">${icon(c.icon)}</div>
      <div class="p-ic">${icon(c.icon)}</div>
      <span class="t-vert">${c.title}</span>
      <div class="p-body">
        <h3>${c.title}</h3>
        <p>${c.blurb}</p>
        <span class="p-go">Ver productos ${icon('arrow')}</span>
      </div>
    </article>`
}

/* mostra os produtos da categoria selecionada */
function selectCategory(id: string, scroll = false): void {
  const cat = CATALOG.find((c) => c.id === id)
  if (!cat) return
  document.querySelectorAll<HTMLElement>('.v-cat-panel').forEach((p) =>
    p.classList.toggle('is-active', p.dataset.cat === id))
  document.querySelectorAll<HTMLElement>('.v-chip').forEach((ch) =>
    ch.classList.toggle('is-active', ch.dataset.cat === id))

  // FletePar: marketplace de fletes — panel + doble camino (transportistas / embarcadores)
  const FP_WA = '595985336505' // WhatsApp FletePar
  const fpwa = (msg: string) => `https://wa.me/${FP_WA}?text=${encodeURIComponent(msg)}`
  const fletesIntro = cat.id !== 'fletes' ? '' : `
    <div class="fp-panel">
      <div class="fp-text">
        <img class="fp-logo" src="../img/fletepar-logo.png" alt="FletePar" onerror="this.remove()">
        <span class="v-brand">FletePar · Grupo GNH</span>
        <h3>La plataforma de fletes #1 de Paraguay</h3>
        <p>FletePar conecta <b>empresas con cargas</b> y <b>transportistas verificados</b> en tiempo real.
        Rastreo GPS con actualizaciones cada 30 segundos, verificación de identidad en 3 capas (facial,
        documental y vehicular), pagos protegidos y seguro de carga desde la recogida hasta la entrega.
        Soporte 24/7 por app y WhatsApp.</p>
      </div>
      <div class="fp-links">
        <a href="https://fletepar.com.py/" target="_blank" rel="noopener">🌐 fletepar.com.py</a>
        <a href="https://fletepar-consulta.web.app" target="_blank" rel="noopener">🔎 Consultá la reputación de un transportista</a>
        <a href="https://fletepar-ed077.web.app/tv" target="_blank" rel="noopener">🗺️ Mapa en vivo (pantalla TV)</a>
        <a href="${fpwa('Hola, quiero más información sobre FletePar')}" target="_blank" rel="noopener">💬 WhatsApp +595 985 336 505</a>
        <a href="mailto:everson@fletepar.com.py">✉️ everson@fletepar.com.py</a>
      </div>
    </div>
    <div class="fp-dual">
      <div class="fp-role fp-role-truck">
        <span class="fp-role-tag">Para transportistas</span>
        <h3>¿Tenés camión?<br>Sumate a la red</h3>
        <p>Recibí pedidos de flete cerca tuyo con matching inteligente, cobrá seguro con pagos integrados y construí tu reputación verificada.</p>
        <div class="fp-btns">
          <a class="fp-btn fp-btn-solid" href="${fpwa('Hola, soy transportista y quiero sumarme a FletePar')}" target="_blank" rel="noopener">Sumarme por WhatsApp</a>
          <a class="fp-btn" href="https://play.google.com/store/apps/details?id=com.everson.FleteParapp" target="_blank" rel="noopener">Google Play</a>
          <a class="fp-btn" href="https://apps.apple.com/app/id6759286072" target="_blank" rel="noopener">App Store</a>
        </div>
      </div>
      <div class="fp-role fp-role-cargo">
        <span class="fp-role-tag">Para empresas</span>
        <h3>¿Necesitás enviar<br>una carga?</h3>
        <p>Publicá tu carga y conectá en minutos con transportistas verificados: rastreo GPS en tiempo real, seguro de carga y notificaciones de entrega.</p>
        <div class="fp-btns">
          <a class="fp-btn fp-btn-solid" href="${fpwa('Hola, necesito enviar una carga con FletePar')}" target="_blank" rel="noopener">Enviar carga por WhatsApp</a>
          <a class="fp-btn" href="https://play.google.com/store/apps/details?id=com.everson.FleteParapp" target="_blank" rel="noopener">Google Play</a>
          <a class="fp-btn" href="https://apps.apple.com/app/id6759286072" target="_blank" rel="noopener">App Store</a>
        </div>
      </div>
    </div>`

  // Intonaco: revoque proyectado — panel con los números que cambian la etapa
  const IN_WA = '595993366650' // WhatsApp/teléfono Intonaco
  const inwa = (msg: string) => `https://wa.me/${IN_WA}?text=${encodeURIComponent(`${msg} (ref ${refCode()})`)}`
  const intonacoIntro = cat.id !== 'intonaco' ? '' : `
    <div class="fp-panel in-panel">
      <div class="fp-text">
        <img class="in-logo" src="../img/intonaco-logo.png" alt="Intonaco — Sistemas Constructivos"
             onerror="this.remove()">
        <h3>Revoque proyectado con método, plazo y estándar</h3>
        <p>De cada 20 días de obra, <b>3 se van en el revoque</b> — el 15% del cronograma. Una etapa con ese
        peso merece método, no improvisación. Intonaco ejecuta el revoque con <b>proyección mecanizada</b>,
        proceso, equipo y personal entrenado: espesura controlada sin variación entre paños, ejecución
        continua con menos juntas y una base correcta desde el inicio que evita retoques en el acabado.</p>
      </div>
      <div class="fp-links">
        <a href="${inwa('Hola, quiero más información sobre el revoque proyectado Intonaco')}" target="_blank" rel="noopener">💬 WhatsApp +595 993 366 650</a>
        <a href="mailto:comercial@intonaco.com.py">✉️ comercial@intonaco.com.py</a>
        <a href="tel:+595993366650">📞 +595 993 366 650</a>
      </div>
    </div>
    <div class="in-stats">
      <div class="in-stat"><b>5×</b><span>más productividad: de 30 a <strong>150 m²/día</strong> en el mismo día de obra</span></div>
      <div class="in-stat"><b>5–7 días</b><span>para 1.000 m² de pared — contra 35 a 40 días del revoque convencional</span></div>
      <div class="in-stat"><b>−20%</b><span>de desperdicio evitado: consumo de material controlado y previsible</span></div>
    </div>
    <div class="in-pillars">
      <span>Plazo</span><span>Costo</span><span>Calidad</span><span>Satisfacción</span>
      <p>Los 4 pilares que Intonaco defiende en cada obra.</p>
    </div>
    <figure class="in-photo">
      <img src="../img/intonaco-obra.jpg" alt="Pared antes y después del revoque proyectado Intonaco" loading="lazy" onerror="this.parentElement.remove()">
      <figcaption>«Lo que está por debajo define lo que se ve al final.» — el revoque como etapa estratégica.</figcaption>
    </figure>`

  // Kasteller: pisos y revestimientos de alta gama
  const KS_WA = '595985869600' // WhatsApp/teléfono Kasteller
  const kswa = (msg: string) => `https://wa.me/${KS_WA}?text=${encodeURIComponent(`${msg} (ref ${refCode()})`)}`
  const kastellerIntro = cat.id !== 'pisos' ? '' : `
    <div class="fp-panel">
      <div class="fp-text">
        <img class="ks-logo" src="../img/kasteller-logo.png" alt="Kasteller Revestimientos" onerror="this.remove()">
        <h3>Revestimientos que definen espacios</h3>
        <p>Pisos y revestimientos de alta gama para proyectos residenciales, comerciales y corporativos.
        <b>Kasteller Revestimientos</b> reúne porcelanatos, mármoles y acabados premium seleccionados
        para transformar cada ambiente en una declaración de estilo. Asesoramos tu proyecto desde
        la elección del material hasta la entrega en obra.</p>
      </div>
      <div class="fp-links">
        <a href="https://www.instagram.com/kastellerrevestimientos" target="_blank" rel="noopener">📷 Instagram — @kastellerrevestimientos</a>
        <a href="https://www.facebook.com/profile.php?id=100050328950600" target="_blank" rel="noopener">👍 Facebook — Kasteller Revestimientos</a>
        <a href="${kswa('Hola, quiero más información sobre los revestimientos Kasteller')}" target="_blank" rel="noopener">💬 WhatsApp +595 985 869 600</a>
        <a href="tel:+595985869600">📞 +595 985 869 600</a>
      </div>
    </div>
    <figure class="in-photo ks-photo">
      <img src="../img/kasteller-ambiente.jpg" alt="Ambiente con revestimientos Kasteller: mármol, madera y diseño de autor" loading="lazy" onerror="this.parentElement.remove()">
      <figcaption>Mármol, madera y luz: los revestimientos como protagonistas del proyecto.</figcaption>
    </figure>`

  let body: string
  if (cat.id === 'aditivos' && ADITIVOS.length) {
    // agrupa por familia
    const fams = new Map<string, Aditivo[]>()
    for (const a of ADITIVOS) {
      if (!fams.has(a.familyLabel)) fams.set(a.familyLabel, [])
      fams.get(a.familyLabel)!.push(a)
    }
    body = [...fams.entries()].map(([label, items]) => `
      <div class="v-subgroup">
        <h3 class="v-subtitle">${label} <span class="v-subcount">${items.length}</span></h3>
        <div class="v-rail">${items.map(aditivoCard).join('')}</div>
      </div>`).join('')
  } else if (cat.groups && cat.groups.length) {
    // categoria com subcategorias (ex.: Equipos → Construcción/Movimentación/Industria)
    body = cat.groups.map((g) => `
      <div class="v-subgroup">
        <h3 class="v-subtitle">${g.title}</h3>
        <div class="v-rail">${g.products.map(productCard).join('')}</div>
      </div>`).join('')
  } else if (cat.id === 'fletes') {
    body = '' // el panel FletePar (fletesIntro) es todo el contenido de la categoría
  } else if (cat.id === 'intonaco') {
    body = '' // el panel Intonaco (intonacoIntro) es todo el contenido de la categoría
  } else if (cat.id === 'pisos') {
    body = '' // el panel Kasteller (kastellerIntro) es todo el contenido de la categoría
  } else if (cat.products && cat.products.length) {
    body = `<div class="v-rail">${cat.products.map(productCard).join('')}</div>`
  } else {
    // categoria sin productos aún
    body = `
      <div class="v-empty">
        <p>Pronto sumaremos productos de esta línea.</p>
        <a class="btn-empty" href="${wa('Hola, quiero consultar sobre ' + cat.title)}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
      </div>`
  }

  const box = document.getElementById('v-products')!
  box.innerHTML = `
    <div class="v-products-head">
      <div class="v-cat-ic">${icon(cat.icon)}</div><h2>${cat.title}</h2>
      <div class="v-filter-box">
        <svg viewBox="0 0 24 24" class="v-filter-ic" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        <input class="v-filter" id="v-filter" type="search" autocomplete="off" placeholder="Buscar en ${cat.title.toLowerCase()}…">
      </div>
    </div>
    <div id="v-body">${fletesIntro}${intonacoIntro}${kastellerIntro}${body}</div>`
  // búsqueda DENTRO de la categoría: misma lógica que el buscador, pero solo con
  // los productos de esta categoría — muestra únicamente los que coinciden
  const flt = document.getElementById('v-filter') as HTMLInputElement | null
  const vbody = document.getElementById('v-body')!
  const defaultBody = fletesIntro + intonacoIntro + kastellerIntro + body
  flt?.addEventListener('input', () => {
    const groups = termGroups(flt.value)
    if (!groups.length) { vbody.innerHTML = defaultBody; return }
    const scored: { s: number; html: string }[] = []
    if (cat.id === 'aditivos') {
      for (const a of ADITIVOS) {
        let s = 0
        const name = deacc(a.name), fam = deacc(a.familyLabel), sub = deacc(a.sub), desc = deacc(a.desc)
        const kwstr = a.kw.join(' ')
        for (const vars of groups) {
          if (hitIn(name, vars)) s += 10
          if (hitIn(fam, vars)) s += 6
          if (hitIn(sub, vars)) s += 4
          if (hitIn(kwstr, vars)) s += 3
          if (hitIn(desc, vars)) s += 1
        }
        if (s > 0) scored.push({ s, html: aditivoCard(a) })
      }
    } else {
      const prods = cat.groups ? cat.groups.flatMap((g) => g.products) : (cat.products ?? [])
      for (const p of prods) {
        let s = 0
        const name = deacc(p.name), note = deacc(p.note ?? ''), tags = deacc((p.tags ?? []).join(' '))
        for (const vars of groups) {
          if (hitIn(name, vars)) s += 10
          if (hitIn(tags, vars)) s += 8
          if (hitIn(note, vars)) s += 3
        }
        if (s > 0) scored.push({ s, html: productCard(p) })
      }
    }
    scored.sort((x, y) => y.s - x.s)
    trackSearch(flt.value.trim(), scored.length, cat.id)
    vbody.innerHTML = scored.length
      ? `<p class="bsc-count v-count">${scored.length} resultado${scored.length > 1 ? 's' : ''} en ${cat.title}</p><div class="bsc-grid">${scored.map((h) => h.html).join('')}</div>`
      : `<div class="v-empty"><p>Sin resultados en ${cat.title} para “${flt.value.trim()}”.</p><a class="btn-empty" href="${wa('Hola, busco: ' + flt.value.trim())}" target="_blank" rel="noopener">Consultar por WhatsApp</a></div>`
  })
  box.classList.remove('revealing'); void box.offsetWidth; box.classList.add('revealing')
  if (scroll) box.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function renderCatalog(): void {
  const root = document.getElementById('catalog')!
  root.innerHTML = `
    <div class="v-deck">${CATALOG.map(deckPanel).join('')}</div>
    <div class="v-products" id="v-products"></div>`

  root.querySelectorAll<HTMLElement>('.v-cat-panel').forEach((panel) => {
    const id = panel.dataset.cat!
    panel.addEventListener('click', () => selectCategory(id, true))
    panel.addEventListener('keydown', (e) => {
      if ((e as KeyboardEvent).key === 'Enter' || (e as KeyboardEvent).key === ' ') { e.preventDefault(); selectCategory(id, true) }
    })
  })

  const chips = document.getElementById('cat-chips')
  if (chips) {
    chips.innerHTML = CATALOG.map((c) => `<button class="v-chip" data-cat="${c.id}">${c.title}</button>`).join('')
    chips.querySelectorAll<HTMLElement>('.v-chip').forEach((ch) =>
      ch.addEventListener('click', () => selectCategory(ch.dataset.cat!, true)))
  }

  selectCategory(CATALOG[0].id) // abre a primeira por padrão (sem rolar)
}

/* ---------- promoções (oculta se vazio) ---------- */
interface Promo { title: string; text: string; url?: string; img?: string; badge?: string; cta?: string }
const PROMOS: Promo[] = [
  {
    badge: 'Lanzamiento',
    title: 'Generador 38 kVA con Motor Ricardo',
    text: 'Grupo electrógeno diésel trifásico de 38 kVA, cabina súper silenciosa y tablero ATS para arranque automático ante un corte. Pronta entrega — vení a conocerlo en nuestro Show Room.',
    img: '../img/prod/generador-art-v2.jpg',
    url: '/promo/generador-38kva/',
    cta: 'Ver el lanzamiento',
  },
]

function renderPromos(): void {
  const el = document.getElementById('promos')!
  if (!PROMOS.length) { el.style.display = 'none'; return }
  el.innerHTML = `
    <h2 class="v-promo-h">Promociones</h2>
    <div class="v-promo-band">
      ${PROMOS.map((p) => `
        <article class="v-promo${p.img ? ' has-img' : ''}">
          ${p.img ? `<a class="v-promo-art" href="${p.url ?? '#'}"><img src="${p.img}" alt="${p.title}" loading="lazy"></a>` : ''}
          <div class="v-promo-body">
            ${p.badge ? `<span class="v-promo-badge">${p.badge}</span>` : ''}
            <h3>${p.title}</h3><p>${p.text}</p>
            <div class="v-promo-actions">
              ${p.url ? `<a class="v-promo-cta" href="${p.url}">${p.cta ?? 'Ver más'} →</a>` : ''}
              <a class="v-promo-wa" href="${wa(`Hola, me interesa la promoción: ${p.title}`)}" target="_blank" rel="noopener"
                 data-ev="promo" data-detail="${p.title}">Consultar por WhatsApp</a>
            </div>
          </div>
        </article>`).join('')}
    </div>`
}

/* ---------- formulário de cotización ---------- */
function initForm(): void {
  const form = document.getElementById('quote-form') as HTMLFormElement
  const status = document.getElementById('quote-status')!
  form.addEventListener('submit', (e) => {
    e.preventDefault()
    const f = new FormData(form)
    const nombre = String(f.get('nombre') ?? '').trim()
    const whatsapp = String(f.get('whatsapp') ?? '').trim()
    if (!nombre || !whatsapp) {
      status.textContent = 'Completá nombre y WhatsApp.'
      status.className = 'text-sm text-red-600'
      return
    }
    // Fase 6C: guarda el lead (fire-and-forget) y registra el evento
    void saveLead({
      nombre,
      whatsapp,
      empresa: String(f.get('empresa') ?? ''),
      producto: String(f.get('producto') ?? ''),
      mensaje: String(f.get('mensaje') ?? ''),
    })
    track('lead', nombre)
    const msg = `Cotización GNH%0A`
      + `Nombre: ${nombre}%0A`
      + `Empresa: ${f.get('empresa') ?? ''}%0A`
      + `Producto: ${f.get('producto') ?? ''}%0A`
      + `Mensaje: ${f.get('mensaje') ?? ''}%0A`
      + `(ref ${refCode()})`
    window.open(`https://wa.me/${WA}?text=${msg}`, '_blank')
    status.textContent = '¡Gracias! Te redirigimos a WhatsApp.'
    status.className = 'text-sm text-green-600'
    form.reset()
  })
}

renderHeroCarousel()
renderCatalog()
initBuscador()
renderPromos()
initForm()
autoTrack()
trackLanding()
mountFooter()
