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
interface Category {
  id: string
  title: string
  icon: string
  docLabel?: string   // "Ficha técnica" | "Catálogo"
  docUrl?: string     // link externo (Drive/servidor) — download nunca trava a página
  products: Product[]
}

const CATALOG: Category[] = [
  {
    id: 'equipos', title: 'Equipos', icon: 'hook', docLabel: 'Catálogo', docUrl: '',
    products: [
      { name: 'Grúa araña', brand: 'GNH', note: 'Elevación de precisión' },
      { name: 'Equipo — placeholder', note: 'AJUSTAR' },
    ],
  },
  {
    id: 'aditivos', title: 'Aditivos', icon: 'flask', docLabel: 'Ficha técnica', docUrl: '',
    products: [
      { name: 'Aditivo — placeholder', brand: 'Camargo Química', note: 'AJUSTAR' },
    ],
  },
  {
    id: 'fletes', title: 'Fletes', icon: 'truck',
    products: [
      { name: 'Transporte de cargas', brand: 'FletePar', note: 'Cobertura regional' },
    ],
  },
  {
    id: 'cemento', title: 'Cemento', icon: 'layers', docLabel: 'Ficha técnica', docUrl: '',
    products: [
      { name: 'Cemento — placeholder', brand: 'Itambé', note: 'AJUSTAR' },
    ],
  },
  {
    id: 'morteros', title: 'Morteros', icon: 'grid', docLabel: 'Ficha técnica', docUrl: '',
    products: [
      { name: 'Mortero — placeholder', brand: 'Intonaco', note: 'AJUSTAR' },
    ],
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

function categoryBlock(c: Category): string {
  const doc = c.docUrl
    ? `<a class="v-doc" href="${c.docUrl}" target="_blank" rel="noopener" data-ev="doc" data-detail="${c.id}">${icon('doc', 'v-doc-i')} ${c.docLabel}</a>`
    : c.docLabel ? `<span class="v-doc v-doc-off">${icon('doc', 'v-doc-i')} ${c.docLabel} — próximamente</span>` : ''
  return `
    <section class="v-cat" id="cat-${c.id}">
      <div class="v-cat-head">
        <div class="v-cat-ic">${icon(c.icon)}</div>
        <h2 class="v-cat-title">${c.title}</h2>
        ${doc}
      </div>
      <div class="v-rail">${c.products.map(productCard).join('')}</div>
    </section>`
}

function renderCatalog(): void {
  const root = document.getElementById('catalog')!
  root.innerHTML = CATALOG.map(categoryBlock).join('')

  const chips = document.getElementById('cat-chips')!
  chips.innerHTML = CATALOG.map((c) => `<a class="v-chip" href="#cat-${c.id}">${c.title}</a>`).join('')
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
