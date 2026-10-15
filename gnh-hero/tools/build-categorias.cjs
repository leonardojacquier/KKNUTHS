#!/usr/bin/env node
/* ============================================================
   Páginas de categoria estáticas e indexáveis:
     /ventas/plataformas-elevadoras/  /ventas/gruas/  etc.
   Cada uma com texto próprio de categoria (não só grade de cards),
   lista dos produtos com link para a página de cada um e CollectionPage
   + BreadcrumbList em JSON-LD.
   Fonte: catalogo-data.ts (mesma do site e das páginas de produto).
   ============================================================ */
const fs = require('fs')
const path = require('path')
const esbuild = require('esbuild')

const REPO = path.resolve(__dirname, '..', '..')
const SRC = path.join(REPO, 'gnh-hero', 'src', 'catalogo-data.ts')
const OUT_DIRS = [path.join(REPO, 'assets', 'nuevo', 'ventas'), path.join(REPO, 'gnh-hero', 'dist', 'ventas')]
const BASE = 'https://gnhorizons.com'
const WA = '595995360060'

const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
const slugify = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[()./]/g, ' ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')

/* ---------- categorias a gerar: grupos de Equipos + categorias simples ----------
   texto próprio por categoria (o brief pede conteúdo, não só cards)          */
const DEF = [
  { slug: 'plataformas-elevadoras', from: { cat: 'equipos', group: 'Plataformas de Elevación' },
    h1: 'Plataformas de Elevación (Plataformas Elevatórias)',
    intro: `Plataformas de elevación de personal para trabajo en altura con seguridad: tijera eléctrica
      para interiores y pisos terminados, tijera de orugas para terreno irregular, brazo articulado y
      telescópico para alcance sobre obstáculos, y mástil de aluminio para mantenimiento liviano.
      Trabajamos alturas de trabajo de 4 a 34 m y capacidades de 100 a 460 kg.`,
    ayuda: `<p><strong>¿Cuál elegir?</strong> Si el piso es plano y el trabajo es vertical, la
      <em>tijera</em> rinde más por su plataforma amplia. Si hay que sortear un obstáculo o llegar de
      costado, se necesita <em>brazo articulado</em>. Para terreno de obra sin compactar, la versión
      <em>de orugas</em> con estabilizadores. Para mantenimiento en interiores, el <em>mástil de
      aluminio</em> es liviano y no marca el piso.</p>` },
  { slug: 'gruas', from: { cat: 'equipos', names: ['Grúa Araña', 'Grúa sobre Camión', 'Manipulador Telescópico', 'Hincadora de Pilotes'] },
    h1: 'Grúas y Equipos de Izaje (Guindastes)',
    intro: `Izaje para obra e industria: grúas araña (spider crane) de 1,5 a 16 t que entran por accesos
      de 0,65 m y se estabilizan con outriggers independientes, grúas sobre camión para carga y descarga,
      y manipuladores telescópicos para movimiento de materiales en altura.`,
    ayuda: `<p><strong>¿Grúa araña o grúa sobre camión?</strong> La araña resuelve donde el camión no
      entra ni se estabiliza: interiores, patios, pisos altos, montaje de vidrio. La grúa sobre camión
      rinde más en la calle, con desplazamiento rápido entre puntos de carga.</p>` },
  { slug: 'montacargas', from: { cat: 'equipos', group: 'Movimentación' },
    h1: 'Montacargas y Equipos de Movimentación (Empilhadeiras)',
    intro: `Montacargas eléctricos, diésel, todoterreno y trilaterales, apiladores, transpaletas y
      carretillas retráctiles (reach truck) para depósito, planta y obra. Capacidades de 1 a 12 t y
      elevaciones de hasta 15 m.`,
    ayuda: `<p><strong>Eléctrico o diésel?</strong> El eléctrico es para interiores y depósitos —sin
      emisiones ni ruido—; el diésel y el todoterreno, para patio, obra y piso irregular. El trilateral
      y el reach truck existen para pasillos angostos, donde el contrapesado no gira.</p>` },
  { slug: 'movimiento-de-suelo', from: { cat: 'equipos', group: 'Movimiento de Suelo' },
    h1: 'Movimiento de Suelo (Escavadeiras y Minicarregadeiras)',
    intro: `Mini excavadoras, minicargadoras (skid steer), retroexcavadoras, bulldozers y rodillos
      compactadores para excavación, nivelación y compactación en obra civil y vial.`,
    ayuda: `<p><strong>Mini excavadora o retroexcavadora?</strong> La mini entra en espacios reducidos y
      es más fácil de transportar; la retro combina pala frontal y brazo, y se desplaza sola por la obra.</p>` },
  { slug: 'equipos-de-concreto', from: { cat: 'equipos', group: 'Construcción' },
    h1: 'Equipos para Concreto y Pavimento',
    intro: `Centrales y bombas de concreto, reglas láser vibratorias, allanadoras, cortadoras de piso,
      máquinas de marcado vial y la proyectora de revoque GNH: producción, colocación, nivelación y
      terminación del hormigón en obra.`,
    ayuda: `<p>Para pisos de alta planicidad, la combinación es <em>regla láser + allanadora</em>. Para
      volumen continuo sin depender de hormigonera externa, la <em>central de concreto</em> con bomba.</p>` },
  { slug: 'morteros', from: { cat: 'morteros' },
    h1: 'Morteros Industrializados Hormigomix (Argamassas)',
    intro: `Morteros industrializados de calidad uniforme, listos para usar: adhesivos AC-1 y AC-3 para
      revestimientos, mortero estructural para reparación y mortero de proyección para revoque mecanizado.`,
    ayuda: `<p>El <em>mortero de proyección</em> es el complemento de la proyectora: rendimiento por
      metro cuadrado previsible y espesor controlado, sin la variación del preparado en obra.</p>` },
]

/* ---------- carga do catálogo ---------- */
function loadCatalog() {
  const js = esbuild.buildSync({ entryPoints: [SRC], bundle: true, write: false, format: 'cjs', platform: 'node', target: 'node18' }).outputFiles[0].text
  const mod = { exports: {} }
  new Function('module', 'exports', js)(mod, mod.exports)
  return mod.exports.CATALOG
}

function pick(CATALOG, from) {
  const cat = CATALOG.find((c) => c.id === from.cat)
  if (!cat) return []
  const all = [...(cat.groups ?? []).flatMap((g) => g.products.map((p) => ({ ...p, _g: g.title }))), ...(cat.products ?? [])]
  if (from.group) return all.filter((p) => p._g === from.group)
  if (from.names) return all.filter((p) => from.names.includes(p.name))
  return all
}

function page(def, prods) {
  const url = `${BASE}/ventas/${def.slug}/`
  const intro = def.intro.replace(/\s+/g, ' ').trim()
  const desc = `${intro} Distribuido por GNH en Paraguay — fichas técnicas y cotización por WhatsApp.`.slice(0, 300)
  const items = prods.map((p) => {
    const slug = slugify(p.name)
    const has = p.specs   // só produtos com página estática viram link
    return `<li>
      ${has ? `<a href="/ventas/${slug}/"><strong>${esc(p.name)}</strong></a>` : `<strong>${esc(p.name)}</strong>`}
      ${p.note ? `<br><span>${esc(p.note)}</span>` : ''}
    </li>`
  }).join('\n      ')

  const ld = {
    '@context': 'https://schema.org/', '@type': 'CollectionPage', name: def.h1,
    description: desc, url,
    mainEntity: {
      '@type': 'ItemList',
      itemListElement: prods.map((p, i) => ({
        '@type': 'ListItem', position: i + 1, name: p.name,
        ...(p.specs ? { url: `${BASE}/ventas/${slugify(p.name)}/` } : {}),
      })),
    },
  }
  const bc = {
    '@context': 'https://schema.org/', '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${BASE}/` },
      { '@type': 'ListItem', position: 2, name: 'Ventas', item: `${BASE}/ventas/` },
      { '@type': 'ListItem', position: 3, name: def.h1, item: url },
    ],
  }

  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(def.h1)} | GNH Paraguay</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${url}">
<meta property="og:type" content="website">
<meta property="og:title" content="${esc(def.h1)} | GNH">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${BASE}/img/logo-oficial.png">
<script type="application/ld+json">${JSON.stringify(ld)}</script>
<script type="application/ld+json">${JSON.stringify(bc)}</script>
<style>
:root{--navy:#14213D;--ink:#1e2733;--orange:#F26D21;--line:#dbe2ec;--mut:#5b6472}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'General Sans',system-ui,-apple-system,Segoe UI,Arial,sans-serif;color:var(--ink);background:#f4f6fa;line-height:1.6}
header{background:var(--navy);color:#fff;padding:14px 0}
header .in{max-width:920px;margin:0 auto;padding:0 20px}
header a{color:#fff;text-decoration:none;font-weight:700}
header nav a{font-weight:500;opacity:.85;margin-left:18px;font-size:14px}
main{background:#fff;padding:28px 20px 40px;margin:0 auto;max-width:920px}
.bc{font-size:13px;color:var(--mut);margin-bottom:14px}
.bc a{color:var(--mut)}
h1{font-family:'Satoshi',system-ui,Arial,sans-serif;font-size:clamp(25px,4vw,34px);line-height:1.15;color:var(--navy);margin-bottom:12px}
.lead{font-size:16.5px;color:#39434f;margin-bottom:18px}
h2{font-family:'Satoshi',system-ui,Arial,sans-serif;font-size:19px;color:var(--navy);margin:26px 0 12px}
ul.prods{list-style:none}
ul.prods li{border-top:1px solid var(--line);padding:12px 0}
ul.prods li:last-child{border-bottom:1px solid var(--line)}
ul.prods a{color:var(--navy);text-decoration:none}
ul.prods a:hover{text-decoration:underline}
ul.prods span{font-size:14px;color:var(--mut)}
.ayuda{background:#f1f5f9;border-radius:10px;padding:16px 18px;font-size:14.5px;color:#39434f;margin:8px 0 6px}
.ayuda em{color:var(--navy);font-style:normal;font-weight:600}
.cta{display:inline-block;margin:22px 0 6px;background:#22c15e;color:#fff;text-decoration:none;font-weight:700;padding:14px 26px;border-radius:100px}
footer{max-width:920px;margin:0 auto;padding:22px 20px 40px;font-size:13px;color:var(--mut)}
footer a{color:var(--navy)}
</style>
</head>
<body>
<header><div class="in"><a href="/">GNH</a>
<nav style="display:inline"><a href="/ventas/">Catálogo</a><a href="/institucional/">Institucional</a></nav></div></header>

<main>
  <p class="bc"><a href="/">Inicio</a> › <a href="/ventas/">Ventas</a> › ${esc(def.h1)}</p>
  <h1>${esc(def.h1)}</h1>
  <p class="lead">${esc(intro)}</p>
  <div class="ayuda">${def.ayuda}</div>

  <h2>Modelos disponibles</h2>
  <ul class="prods">
      ${items}
  </ul>

  <a class="cta" href="https://wa.me/${WA}?text=${encodeURIComponent(`Hola, quiero información sobre ${def.h1}`)}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
  <p style="font-size:14px;color:var(--mut);margin-top:14px">Asesoramiento técnico para elegir el equipo según la obra. Atendemos en español y portugués.</p>
</main>

<footer>
  <p><strong>GNH — Generando Nuevos Horizontes</strong> · Av. República del Perú km 7, Ciudad del Este · Acceso Sur, Ñemby, Paraguay</p>
  <p>WhatsApp <a href="https://wa.me/${WA}">+595 995 360060</a> · <a href="mailto:comercial@gnhorizons.com">comercial@gnhorizons.com</a> · <a href="/ventas/">Catálogo completo</a></p>
</footer>
</body>
</html>
`
}

/* ---------- main ---------- */
const CATALOG = loadCatalog()
let n = 0
for (const def of DEF) {
  const prods = pick(CATALOG, def.from)
  if (!prods.length) { console.warn(`  aviso: categoria ${def.slug} sem produtos, pulada`); continue }
  const html = page(def, prods)
  for (const out of OUT_DIRS) {
    const dir = path.join(out, def.slug)
    fs.mkdirSync(dir, { recursive: true })
    fs.writeFileSync(path.join(dir, 'index.html'), html)
  }
  n++
}
console.log(`categorías OK — ${n} páginas de categoria geradas`)
