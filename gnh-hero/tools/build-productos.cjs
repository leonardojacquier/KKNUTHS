#!/usr/bin/env node
/* ============================================================
   Gera UMA página HTML estática por produto a partir de catalogo-data.ts
   (fonte única de verdade). Objetivo: conteúdo indexável sem JS —
   h1, descrição, tabela de specs reais, breadcrumb, CTA de WhatsApp.

   Regras:
   - só gera página para produto com specs reais (não inventamos dado técnico)
   - sem preço (decisão do dono: nada de preço público) → JSON-LD sem Offer
   - HTML leve (< 25 KB), CSS inline mínimo, zero JS obrigatório
   Uso: node tools/build-productos.cjs   (depois de sincronizar assets/nuevo)
   ============================================================ */
const fs = require('fs')
const path = require('path')
const esbuild = require('esbuild')

const REPO = path.resolve(__dirname, '..', '..')
const SRC = path.join(REPO, 'gnh-hero', 'src', 'catalogo-data.ts')
const OUT_DIRS = [path.join(REPO, 'assets', 'nuevo', 'ventas'), path.join(REPO, 'gnh-hero', 'dist', 'ventas')]
const BASE = 'https://gnhorizons.com'
const WA = '595995360060'

/* ---------- carrega o catálogo TS ---------- */
function loadCatalog() {
  const js = esbuild.buildSync({
    entryPoints: [SRC], bundle: true, write: false, format: 'cjs', platform: 'node', target: 'node18',
  }).outputFiles[0].text
  const mod = { exports: {} }
  new Function('module', 'exports', js)(mod, mod.exports)
  return mod.exports
}

/* ---------- helpers ---------- */
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const slugify = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[()./]/g, ' ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

/** nomenclatura dupla ES/EN quando o nome comercial tem sinônimo conhecido */
const ALIAS_TITULO = {
  'Grúa Araña': 'Spider Crane',
  'Plataforma Tijera Autopropulsada': 'Scissor Lift',
  'Plataforma Tijera de Orugas': 'Tracked Scissor Lift',
  'Plataforma Tijera con Estabilizadores': 'Scissor Lift',
  'Plataforma Articulada y Telescópica': 'Boom Lift',
  'Plataforma de Mástil de Aluminio': 'Mast Lift',
  'Plataforma sobre Triciclo Eléctrico': 'Mast Lift',
  'Montacargas Eléctrico': 'Empilhadeira Elétrica',
  'Montacargas Diésel 2 a 5 t': 'Empilhadeira a Diesel',
  'Montacargas Trilateral': 'Trilateral Forklift',
  'Carretilla Retráctil (Reach Truck)': 'Empilhadeira Retrátil',
  'Transpaleta Eléctrica': 'Paleteira Elétrica',
  'Mini Excavadora HT15': 'Mini Escavadeira',
  'Minicargadora (Skid Steer)': 'Minicarregadeira',
  'Retroexcavadora': 'Retroescavadeira',
  'Grúa sobre Camión': 'Guindaste sobre Caminhão',
  'Manipulador Telescópico': 'Telehandler',
  'Hincadora de Pilotes': 'Bate-Estacas',
  'Perforadora para Taludes': 'Perfuratriz',
  'Cortacésped a Control Remoto': 'Roçadeira Robotizada',
}

/* ---------- template da página ---------- */
function page(p, cat, group) {
  const alias = ALIAS_TITULO[p.name]
  const h1 = alias ? `${p.name} (${alias})` : p.name
  const slug = slugify(p.name)
  const url = `${BASE}/ventas/${slug}/`
  const desc = `${p.note ?? h1} Modelos, capacidades y especificaciones técnicas. Distribuido por GNH en Paraguay — cotización por WhatsApp.`
    .replace(/\s+/g, ' ').slice(0, 300)
  const img = p.img ? p.img.replace('../', `${BASE}/`) : `${BASE}/img/logo-oficial.png`
  const waMsg = encodeURIComponent(`Hola, me interesa: ${p.name}`)

  const specRows = p.specs
    ? p.specs.r.map((row) => `<tr>${row.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('\n        ')
    : ''
  const specTable = p.specs ? `
      <h2>Modelos y especificaciones técnicas</h2>
      <table>
        <thead><tr>${p.specs.h.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead>
        <tbody>
        ${specRows}
        </tbody>
      </table>
      <p class="nota">Datos del catálogo del fabricante. Consultanos por configuraciones y disponibilidad.</p>` : ''

  const props = p.specs
    ? p.specs.r.slice(0, 12).map((row) => ({
        '@type': 'PropertyValue', name: `${p.specs.h[0]} ${row[0]}`,
        value: row.slice(1).map((v, i) => `${p.specs.h[i + 1]}: ${v}`).join(' · '),
      }))
    : []

  const ld = {
    '@context': 'https://schema.org/', '@type': 'Product', name: h1,
    description: desc, image: [img], url,
    ...(p.brand ? { brand: { '@type': 'Brand', name: p.brand } } : {}),
    category: cat.title,
    ...(props.length ? { additionalProperty: props } : {}),
    seller: { '@type': 'Organization', name: 'GNH — Generando Nuevos Horizontes', url: BASE },
  }
  const bc = {
    '@context': 'https://schema.org/', '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${BASE}/` },
      { '@type': 'ListItem', position: 2, name: 'Ventas', item: `${BASE}/ventas/` },
      { '@type': 'ListItem', position: 3, name: cat.title, item: `${BASE}/ventas/` },
      { '@type': 'ListItem', position: 4, name: h1, item: url },
    ],
  }

  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(h1)} | GNH Paraguay</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<meta property="og:type" content="product">
<meta property="og:title" content="${esc(h1)} | GNH">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${esc(img)}">
<script type="application/ld+json">${JSON.stringify(ld)}</script>
<script type="application/ld+json">${JSON.stringify(bc)}</script>
<style>
:root{--navy:#14213D;--ink:#1e2733;--orange:#F26D21;--line:#dbe2ec;--mut:#5b6472}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'General Sans',system-ui,-apple-system,Segoe UI,Arial,sans-serif;color:var(--ink);background:#f4f6fa;line-height:1.6}
header{background:var(--navy);color:#fff;padding:14px 0}
header .in,main{max-width:920px;margin:0 auto;padding:0 20px}
header a{color:#fff;text-decoration:none;font-weight:700;letter-spacing:.02em}
header nav a{font-weight:500;opacity:.85;margin-left:18px;font-size:14px}
main{background:#fff;padding:28px 20px 40px;margin:0 auto;max-width:920px}
.bc{font-size:13px;color:var(--mut);margin-bottom:14px}
.bc a{color:var(--mut)}
h1{font-family:'Satoshi',system-ui,Arial,sans-serif;font-size:clamp(25px,4vw,36px);line-height:1.15;color:var(--navy);margin-bottom:10px}
.cat{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--orange);margin-bottom:8px}
.lead{font-size:17px;color:#39434f;margin:12px 0 22px}
figure{margin:18px 0}
figure img{width:100%;max-width:560px;height:auto;border-radius:10px;background:#eef2f7}
h2{font-family:'Satoshi',system-ui,Arial,sans-serif;font-size:20px;color:var(--navy);margin:26px 0 12px}
table{width:100%;border-collapse:collapse;font-size:14px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;white-space:nowrap}
th{background:#eef2f7;font-weight:700;color:var(--navy)}
tbody tr:nth-child(even){background:#fafbfd}
.nota{font-size:13px;color:var(--mut);margin-top:10px}
.cta{display:inline-block;margin:24px 0 8px;background:#22c15e;color:#fff;text-decoration:none;font-weight:700;padding:14px 26px;border-radius:100px}
.cta.alt{background:var(--orange)}
.tags{margin-top:26px;font-size:13px;color:var(--mut)}
footer{max-width:920px;margin:0 auto;padding:22px 20px 40px;font-size:13px;color:var(--mut)}
footer a{color:var(--navy)}
</style>
</head>
<body>
<header><div class="in"><a href="/">GNH</a>
<nav style="display:inline"><a href="/ventas/">Catálogo</a><a href="/institucional/">Institucional</a></nav></div></header>

<main>
  <p class="bc"><a href="/">Inicio</a> › <a href="/ventas/">Ventas</a> › ${esc(cat.title)}${group ? ` › ${esc(group)}` : ''}</p>
  <span class="cat">${esc(cat.title)}${group ? ` · ${esc(group)}` : ''}</span>
  <h1>${esc(h1)}</h1>
  ${p.note ? `<p class="lead">${esc(p.note)}</p>` : ''}
  ${p.img ? `<figure><img src="${esc(p.img.replace('../', '/'))}" alt="${esc(h1)}" loading="lazy" width="560" height="380"></figure>` : ''}

  <a class="cta" href="https://wa.me/${WA}?text=${waMsg}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
${specTable}

  <h2>Disponibilidad y asesoramiento</h2>
  <p>GNH distribuye e importa ${esc(p.name.toLowerCase())} en Paraguay, con asesoramiento técnico
  para elegir el modelo correcto según la obra. Atendemos en español y portugués.</p>
  <p><a class="cta alt" href="https://wa.me/${WA}?text=${waMsg}" target="_blank" rel="noopener">Pedir cotización</a></p>
  ${p.tags && p.tags.length ? `<p class="tags">También buscado como: ${esc(p.tags.slice(0, 10).join(', '))}.</p>` : ''}
</main>

<footer>
  <p><strong>GNH — Generando Nuevos Horizontes</strong> · Av. República del Perú km 7, Ciudad del Este · Acceso Sur, Ñemby, Paraguay</p>
  <p>WhatsApp <a href="https://wa.me/${WA}">+595 995 360060</a> · <a href="mailto:comercial@gnhorizons.com">comercial@gnhorizons.com</a> · <a href="/ventas/">Ver catálogo completo</a></p>
</footer>
</body>
</html>
`
}

/* ---------- main ---------- */
const { CATALOG } = loadCatalog()
let gerados = 0, pulados = []
for (const cat of CATALOG) {
  const items = [
    ...(cat.groups ?? []).flatMap((g) => g.products.map((p) => ({ p, group: g.title }))),
    ...((cat.products ?? []).map((p) => ({ p, group: null }))),
  ]
  for (const { p, group } of items) {
    if (!p.specs) { pulados.push(p.name); continue }   // sem spec real → não gera
    const slug = slugify(p.name)
    const html = page(p, cat, group)
    for (const out of OUT_DIRS) {
      const dir = path.join(out, slug)
      fs.mkdirSync(dir, { recursive: true })
      fs.writeFileSync(path.join(dir, 'index.html'), html)
    }
    gerados++
  }
}
console.log(`productos OK — ${gerados} páginas estáticas geradas`)
if (pulados.length) console.log(`  (${pulados.length} sem tabela de specs, não geradas: ${pulados.slice(0, 6).join(', ')}…)`)
