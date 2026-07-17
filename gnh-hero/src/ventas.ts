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
        ],
      },
      {
        title: 'Movimentación',
        products: [
          { name: 'Grúa Araña', brand: 'GNH', img: '../img/prod/grua-arana.png', note: 'Grúas araña de orugas de 1,5 t a 70 t de capacidad. Control remoto e indicador de par incluidos. Brazo extensor y cesto opcionales.' },
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
}
const icon = (k: string, cls = '') =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="${cls}">${ICONS[k] ?? ''}</svg>`

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

  const chips = document.getElementById('cat-chips')!
  chips.innerHTML = CATALOG.map((c) => `<button class="v-chip" data-cat="${c.id}">${c.title}</button>`).join('')
  chips.querySelectorAll<HTMLElement>('.v-chip').forEach((ch) =>
    ch.addEventListener('click', () => selectCategory(ch.dataset.cat!, true)))

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

renderCatalog()
renderPromos()
initForm()
mountFooter()
