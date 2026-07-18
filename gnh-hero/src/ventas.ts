import './style.css'
import './ventas.css'
import { mountFooter } from './footer'

const WA = '595985311031'
const wa = (msg: string) => `https://wa.me/${WA}?text=${encodeURIComponent(msg)}`

/* ============================================================
   CATÁLOGO — estrutura de dados. Preencher conforme as infos chegam.
   Cada categoria: título, ícone, link de ficha/catálogo (externo), produtos.
   Cada produto: nome, marca, imagem (placeholder até chegar), nota.
   ============================================================ */
interface Product { name: string; brand?: string; img?: string; note?: string }
interface SubGroup { title: string; products: Product[] }
interface Category {
  id: string
  title: string
  icon: string
  blurb: string                 // texto curto no painel do deck
  products?: Product[]          // categoria simples
  groups?: SubGroup[]           // categoria com subcategorias (ex.: Equipos)
}

const CATALOG: Category[] = [
  {
    id: 'equipos', title: 'Equipos', icon: 'gear',
    blurb: 'Reglas láser, bombas de concreto, allanadoras, grúas, generadores y más.',
    groups: [
      {
        title: 'Construcción',
        products: [
          { name: 'Regla Láser Vibratoria WS940', img: '../img/prod/ws940.png', note: 'Nivelación láser de pisos de concreto de alta precisión.' },
          { name: 'Bomba Transportadora de Concreto', img: '../img/prod/bomba-cemento.png', note: 'Bombeo y transporte de concreto con caudal estable y operación continua.' },
          { name: 'Allanadora de Concreto 1 m', img: '../img/prod/allanadora.png', note: 'Alisado y pulido de pisos de concreto. Ancho de trabajo de 1 metro.' },
          { name: 'Cortadora de Piso', img: '../img/prod/cortadora.png', note: 'Corte de juntas en concreto y asfalto con disco diamantado.' },
          { name: 'Máquina de Marcado Vial', img: '../img/prod/marcado.png', note: 'Marcación de pavimentos y viales con pintura de alto rendimiento.' },
          { name: 'Central de Concreto JBTS20', img: '../img/prod/central-concreto.png', note: 'Mezcladora y bomba de concreto sobre remolque. Equipada con motor Cummins, para producción y bombeo continuo en obra.' },
        ],
      },
      {
        title: 'Movimentación',
        products: [
          { name: 'Grúa Araña', brand: 'GNH', img: '../img/prod/grua-arana.png', note: 'Grúas araña de orugas de 1,5 t a 70 t de capacidad. Control remoto e indicador de par incluidos. Brazo extensor y cesto opcionales.' },
          { name: 'Mini Excavadora HT15', img: '../img/prod/excavadora.png', note: 'Miniexcavadora de orugas con motor Kubota. Balanceo lateral del brazo, cabina y aire acondicionado opcionales.' },
          { name: 'Camión Volquete de Orugas', img: '../img/prod/volquete.png', note: 'Dumper de orugas para transporte de materiales en obra. Capacidades de 0,5 t y 1,2 t; versión giratoria con motor diésel.' },
          { name: 'Carretilla Elevadora Diésel 3,5 t', img: '../img/prod/carretilla.png', note: 'Montacargas diésel, capacidad 3,5 t y elevación de 3 m. Dispositivo rotatorio opcional.' },
          { name: 'Montacargas Todoterreno 3,5 t', img: '../img/prod/montacargas.png', note: 'Montacargas todoterreno 3,5 t para superficies difíciles.' },
          { name: 'Apilador Eléctrico', img: '../img/prod/apilador.png', note: 'Apiladores eléctricos — capacidades de 1 a 2 t y alturas de 1,6 a 4,5 m.' },
          { name: 'Elevador de Dos Columnas', img: '../img/prod/elevador.png', note: 'Plataforma de elevación de personal de dos mástiles, uso industrial.' },
        ],
      },
      {
        title: 'Industria',
        products: [
          { name: 'Ensayo a Compresión HST-YES2000', img: '../img/prod/compresion.png', note: 'Prensa digital para ensayos de resistencia a la compresión. Control de calidad.' },
          { name: 'Motor Diésel 4HZD', img: '../img/prod/motor.png', note: 'Motor diésel industrial de alto desempeño para generación y usos estacionarios.' },
          { name: 'Grupo Electrógeno Diésel 38 kVA', img: '../img/prod/generador.png', note: 'Generador trifásico 400 V / 50 Hz, cabina súper silenciosa.' },
        ],
      },
    ],
  },
  {
    id: 'aditivos', title: 'Aditivos', icon: 'flask',
    blurb: 'Aditivos y soluciones químicas para construcción.',
    products: [],
  },
  {
    id: 'fletes', title: 'Fletes', icon: 'truck',
    blurb: 'Transporte y fletes de carga con cobertura regional.',
    products: [
      { name: 'Transporte de Cargas', brand: 'FletePar', note: 'Fletes con cobertura regional y trazabilidad total, del origen al destino.' },
    ],
  },
  {
    id: 'morteros', title: 'Morteros', icon: 'grid',
    blurb: 'Revoques y morteros industrializados.',
    products: [],
  },
  {
    id: 'cementos', title: 'Cementos', icon: 'layers',
    blurb: 'Cemento de alto desempeño para toda obra.',
    products: [],
  },
]

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
}
const icon = (k: string, cls = '') =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="${cls}">${ICONS[k] ?? ''}</svg>`

/* ============================================================
   CARROSSEL DO HERO — líneas destacadas (productos foco).
   Agregar aquí a medida que llega el material (BIO 360, Macro-fibras…).
   ============================================================ */
// bleed:true  → la imagen cubre TODO el banner (full-bleed, para fotos 21:9 de ambiente)
// bleed:false → recorte del producto centrado a la derecha (imágenes con fondo transparente)
interface Featured { name: string; tag: string; cat: string; bleed?: boolean; img?: string; videoWebm?: string; videoMp4?: string; poster?: string }
const FEATURED: Featured[] = [
  { name: 'Plataformas', tag: 'Plataforma electro-hidráulica de elevación de personal para trabajos en altura.', img: '../img/prod/plataformas.jpg', cat: 'equipos', bleed: true },
  { name: 'Grúas Araña', tag: 'Grúas araña de orugas de 1,5 t a 70 t. Compactas, potentes y de fácil acceso.', cat: 'equipos', bleed: true, videoWebm: '../video/grua.webm', videoMp4: '../video/grua.mp4', poster: '../img/prod/grua-poster.jpg' },
  { name: 'Mini Central de Concreto', tag: 'Mezcla y bombeo de concreto en un solo equipo, con motor Cummins.', img: '../img/prod/mini-central.jpg', cat: 'equipos', bleed: true },
  { name: 'Minibomba Eléctrica', tag: 'Bomba eléctrica compacta para el transporte de concreto en obra.', img: '../img/prod/minibomba.jpg', cat: 'equipos', bleed: true },
  { name: 'Mezcladora de Mortero', tag: 'Ideal para la aplicación de AC-I y AC-III.', img: '../img/prod/mezcladora-mortero.jpg', cat: 'equipos', bleed: true },
  // Cuando lleguen las fotos 21:9 de ambiente, reemplazar img y poner bleed: true:
  // { name: 'BIO 360', tag: 'Solución BIO 360.', img: '../img/prod/bio360.jpg', cat: 'aditivos', bleed: true },
  // { name: 'Macro-fibras', tag: 'Refuerzo estructural del concreto con macro-fibras.', img: '../img/prod/macrofibras.jpg', cat: 'aditivos', bleed: true },
]
const PAUSE_ICO = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="7" y="6" width="3.4" height="12" rx="1"/><rect x="13.6" y="6" width="3.4" height="12" rx="1"/></svg>'
const PLAY_ICO = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l11-6.5z"/></svg>'

function renderHeroCarousel(): void {
  const root = document.getElementById('hero-carousel')
  if (!root || !FEATURED.length) return
  const DUR = 5200
  root.className = 'v-showcase'
  root.style.setProperty('--vh-dur', DUR + 'ms')
  root.innerHTML = `
    <div class="vh-track">
      ${FEATURED.map((f, i) => `
        <article class="vh-slide${i === 0 ? ' is-active' : ''}${f.bleed ? ' is-bleed' : ''}" data-i="${i}">
          <div class="vh-media">${f.videoMp4
            ? `<video class="vh-el" muted loop playsinline preload="metadata" poster="${f.poster || ''}"><source src="${f.videoWebm}" type="video/webm"><source src="${f.videoMp4}" type="video/mp4"></video>`
            : `<img class="vh-el" src="${f.img}" alt="${f.name}" ${i === 0 ? '' : 'loading="lazy"'}>`}</div>
          <div class="vh-inner">
            <div class="vh-copy">
              <span class="vh-eyebrow">Línea destacada</span>
              <h2 class="vh-title">${f.name}</h2>
              <p class="vh-desc">${f.tag}</p>
              <button class="vh-cta" data-cat="${f.cat}">Ver productos ${icon('arrow', 'vh-cta-i')}</button>
            </div>
          </div>
        </article>`).join('')}
      <button class="vh-arrow vh-prev" aria-label="Anterior">${icon('chevL')}</button>
      <button class="vh-arrow vh-next" aria-label="Siguiente">${icon('chevR')}</button>
    </div>
    <div class="vh-controls">
      <div class="vh-segs">${FEATURED.map((_, i) =>
        `<button class="vh-seg" data-i="${i}" aria-label="Ver ${i + 1}"><span class="vh-seg-fill"></span></button>`).join('')}</div>
      <button class="vh-pause" aria-label="Pausar o reanudar" aria-pressed="false">${PAUSE_ICO}</button>
    </div>`

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
  root.querySelectorAll<HTMLElement>('.vh-cta').forEach((btn) =>
    btn.addEventListener('click', () => selectCategory(btn.dataset.cat || 'equipos', true)))

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
function productCard(p: Product): string {
  const msg = `Hola, me interesa: ${p.name}${p.brand ? ' (' + p.brand + ')' : ''}`
  return `
    <article class="v-card">
      <div class="v-card-media">${p.img ? `<img src="${p.img}" alt="${p.name}" loading="lazy">` : `<span class="ph">${p.name}</span>`}</div>
      <div class="v-card-body">
        ${p.brand ? `<span class="v-brand">${p.brand}</span>` : ''}
        <h3 class="v-name">${p.name}</h3>
        ${p.note ? `<p class="v-note">${p.note}</p>` : ''}
        <a class="v-cta" href="${wa(msg)}" target="_blank" rel="noopener" data-ev="product" data-detail="${p.name}">Consultar ${icon('arrow', 'v-cta-i')}</a>
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

  let body: string
  if (cat.groups && cat.groups.length) {
    // categoria com subcategorias (ex.: Equipos → Construcción/Movimentación/Industria)
    body = cat.groups.map((g) => `
      <div class="v-subgroup">
        <h3 class="v-subtitle">${g.title}</h3>
        <div class="v-rail">${g.products.map(productCard).join('')}</div>
      </div>`).join('')
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
    <div class="v-products-head"><div class="v-cat-ic">${icon(cat.icon)}</div><h2>${cat.title}</h2></div>
    ${body}`
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
interface Promo { title: string; text: string; url?: string }
const PROMOS: Promo[] = [] // AJUSTAR: agregar promociones activas

function renderPromos(): void {
  const el = document.getElementById('promos')!
  if (!PROMOS.length) { el.style.display = 'none'; return }
  el.innerHTML = `
    <div class="v-promo-band">
      ${PROMOS.map((p) => `
        <div class="v-promo">
          <h3>${p.title}</h3><p>${p.text}</p>
          ${p.url ? `<a href="${p.url}" target="_blank" rel="noopener">Ver más →</a>` : ''}
        </div>`).join('')}
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
    // TODO Fase 6: gravar lead no Supabase antes de abrir o WhatsApp
    const msg = `Cotización GNH%0A`
      + `Nombre: ${nombre}%0A`
      + `Empresa: ${f.get('empresa') ?? ''}%0A`
      + `Producto: ${f.get('producto') ?? ''}%0A`
      + `Mensaje: ${f.get('mensaje') ?? ''}`
    window.open(`https://wa.me/${WA}?text=${msg}`, '_blank')
    status.textContent = '¡Gracias! Te redirigimos a WhatsApp.'
    status.className = 'text-sm text-green-600'
    form.reset()
  })
}

renderHeroCarousel()
renderCatalog()
renderPromos()
initForm()
mountFooter()
