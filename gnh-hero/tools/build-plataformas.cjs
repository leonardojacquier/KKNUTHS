#!/usr/bin/env node
/* ============================================================
   Fichas técnicas das PLATAFORMAS DE MÁSTIL DE ALUMINIO (ZS,
   séries SJY simples / SJYL duplo) — mesmo formato das fichas
   de grúas e aditivos: folha A4 com marca GNH.

   Gera  gnh-hero/public/fichas/plataforma-<modelo>.html
   (os PDFs saem depois com tools/make-pdfs.cjs, que varre a pasta)

   ⚠️ Dados transcritos do catálogo do fabricante (mesma fonte da
   tabela de catalogo-data.ts). NÃO inventar: os arquivos enviados
   pelo fornecedor trazem só fotos, sem tabela de specs — por isso
   a ficha traz capacidade/altura/peso e manda consultar o resto.
   ============================================================ */
const fs = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')
const OUT = path.join(ROOT, 'public', 'fichas')
const IMGDIR = path.join(ROOT, 'public', 'img', 'prod', 'plataforma')
const WA = '595995360060'

/* ---------- modelos (catálogo do fabricante) ----------
   foto: arquivo em public/img/prod/plataforma/ quando temos foto real da unidade */
const MODELOS = [
  { m: 'SJY0.15-4',   mastil: 'Simple', cap: '150 kg', alt: '4 m',  peso: '230 kg', foto: null },
  { m: 'SJY0.15-6',   mastil: 'Simple', cap: '150 kg', alt: '6 m',  peso: '270 kg', foto: null },
  { m: 'SJY0.12-8',   mastil: 'Simple', cap: '120 kg', alt: '8 m',  peso: '290 kg', foto: null },
  { m: 'SJY0.1-9',    mastil: 'Simple', cap: '100 kg', alt: '9 m',  peso: '320 kg', foto: 'sjy-0-1-9' },
  { m: 'SJY0.1-10',   mastil: 'Simple', cap: '100 kg', alt: '10 m', peso: '330 kg', foto: 'sjy-0-1-10' },
  { m: 'SJYL0.2-4',   mastil: 'Doble',  cap: '240 kg', alt: '4 m',  peso: '360 kg', foto: null },
  { m: 'SJYL0.23-6',  mastil: 'Doble',  cap: '230 kg', alt: '6 m',  peso: '400 kg', foto: 'sjyl-0-23-6' },
  { m: 'SJYL0.23-8',  mastil: 'Doble',  cap: '230 kg', alt: '8 m',  peso: '440 kg', foto: null },
  { m: 'SJYL0.23-10', mastil: 'Doble',  cap: '230 kg', alt: '10 m', peso: '520 kg', foto: null },
  { m: 'SJYL0.22-12', mastil: 'Doble',  cap: '220 kg', alt: '12 m', peso: '610 kg', foto: 'sjyl-0-22-12' },
  { m: 'SJYL0.2-14',  mastil: 'Doble',  cap: '200 kg', alt: '14 m', peso: '670 kg', foto: null },
  { m: 'SJYL0.15-16', mastil: 'Doble',  cap: '150 kg', alt: '16 m', peso: '750 kg', foto: null },
]

const slugOf = (m) => 'plataforma-' + m.toLowerCase().replace(/[^a-z0-9]+/g, '-')

/* ---------- helpers ---------- */
const b64 = (p) => (fs.existsSync(p) ? fs.readFileSync(p).toString('base64') : '')
const logoB64 = b64(path.join(ROOT, 'public', 'img', 'logo-ficha.png'))
const logoImg = (h) => logoB64
  ? `<img src="data:image/png;base64,${logoB64}" alt="GNH" style="height:${h}px;width:auto">`
  : '<b>GNH</b>'

/* CSS compartilhado com as fichas de grúa — lido da fonte para não divergir */
const gruas = fs.readFileSync(path.join(__dirname, 'build-gruas.cjs'), 'utf8')
const cssMatch = gruas.match(/<style>[\s\S]*?<\/style>/)
if (!cssMatch) throw new Error('CSS das fichas não encontrado em build-gruas.cjs')
// cor da família: âmbar (grúas) → azul (plataformas)
// cor da família + regras de impressão (evita página órfã só com o rodapé)
const CSS = cssMatch[0] + '<style>:root{--fam:#3B82F6}'
  + '.body figure{margin-top:10px}'
  + '@media print{.foot{break-inside:avoid;page-break-inside:avoid}'
  + '.body h2{break-after:avoid;page-break-after:avoid}}</style>'

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const row = (k, v) => (v ? `<tr><th>${k}</th><td>${v}</td></tr>` : '')

const fotoTag = (m) => {
  if (!m.foto || !fs.existsSync(path.join(IMGDIR, `${m.foto}.jpg`))) return ''
  return `<h2>Unidad</h2>
  <figure><img src="../img/prod/plataforma/${m.foto}.jpg" alt="Plataforma ${esc(m.m)} — mástil de aluminio ${m.mastil.toLowerCase()}"
    style="width:100%;max-width:330px;height:auto;border:1px solid var(--hair)">
  <figcaption>Foto real de la unidad ${esc(m.m)} — mástil de aluminio ${m.mastil.toLowerCase()}, chasis con ruedas y estabilizadores manuales.</figcaption></figure>`
}

function ficha(m) {
  const slug = slugOf(m.m)
  const name = `Plataforma Eléctrica ${m.m}`
  const doble = m.mastil === 'Doble'
  const waMsg = encodeURIComponent(`Hola, me interesa la Plataforma Eléctrica ${m.m} (${m.cap} · ${m.alt})`)

  return `<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${name} — Ficha Técnica | GNH</title>
<meta name="description" content="Ficha técnica de la plataforma eléctrica ${m.m}: mástil de aluminio ${m.mastil.toLowerCase()}, capacidad ${m.cap}, altura ${m.alt}, peso ${m.peso}. GNH Paraguay.">
<link rel="canonical" href="https://gnhorizons.com/fichas/${slug}.html">
${CSS}</head>
<body><div class="sheet">
<div class="top">
  <div class="brand-row">${logoImg(58)}
    <div class="doc-tag"><span class="dt">Ficha Técnica</span><span class="fam">Plataformas elevadoras</span></div>
  </div>
  <div class="rule"></div>
  <div class="title-block">
    <h1>${name}</h1>
    <p class="sub">Plataforma electro-hidráulica de elevación de personal · mástil de aluminio ${m.mastil.toLowerCase()} · sin emisiones</p>
    <div class="actions">
      <a class="btn btn-pdf" href="pdf/${slug}.pdf" download>Descargar PDF</a>
      <a class="btn btn-wa" href="https://wa.me/${WA}?text=${waMsg}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
      <a class="btn btn-back" href="/ventas/plataforma-de-mastil-de-aluminio/">Ver todos los modelos</a>
    </div>
  </div>
</div>
<div class="body">
  <div class="hero-num">
    <div><b>${m.alt}</b><span>Altura</span></div>
    <div><b>${m.cap}</b><span>Capacidad</span></div>
    <div><b>${m.mastil}</b><span>Mástil</span></div>
    <div><b>${m.peso}</b><span>Peso propio</span></div>
  </div>

  <h2>Datos del modelo</h2>
  <table class="kv">
    ${row('Modelo', m.m)}
    ${row('Tipo', `Plataforma electro-hidráulica de elevación de personal`)}
    ${row('Mástil', `Aluminio, ${m.mastil.toLowerCase()}${doble ? ' (dos columnas)' : ''}`)}
    ${row('Capacidad de carga', m.cap)}
    ${row('Altura', m.alt)}
    ${row('Peso propio', m.peso)}
  </table>

  <h2>Construcción</h2>
  <table class="kv">
    ${row('Chasis', 'Con ruedas para traslado manual y estabilizadores de husillo en las cuatro esquinas')}
    ${row('Accionamiento', 'Electro-hidráulico — silencioso y sin emisiones, apto para uso en interiores')}
    ${row('Seguridad', 'Parada de emergencia en el chasis · barandas perimetrales en la canasta · uso obligatorio con estabilizadores apoyados')}
    ${row('Alimentación', 'Consultar — se configura según la instalación del cliente')}
    ${row('Dimensiones de transporte', 'Consultar por modelo')}
  </table>

  ${fotoTag(m)}

  <h2>Aplicaciones</h2>
  <p>Mantenimiento de luminarias, cielorrasos, ductos y aire acondicionado; montaje eléctrico y de señalización en altura;
  limpieza de fachadas internas; instalaciones en depósitos, supermercados y centros logísticos.
  Al no tener motor a combustión, trabaja dentro de locales cerrados sin ventilación forzada.</p>

  <h2>Cómo elegir el modelo</h2>
  <p>Definí primero la <b>altura</b> que necesitás alcanzar y cuánto peso sube a la canasta (persona + herramientas).
  Los modelos de mástil <b>simple</b> (SJY) son más livianos y pasan por accesos estrechos;
  los de mástil <b>doble</b> (SJYL) sostienen más carga y llegan más alto.</p>
</div>
<div class="foot">
  <p><b>GNH — Generando Nuevos Horizontes</b> · Av. República del Perú km 7, Ciudad del Este · Acceso Sur, Ñemby, Paraguay</p>
  <p>WhatsApp <b>+595 995 360060</b> · comercial@gnhorizons.com · gnhorizons.com</p>
  <p class="note">Datos transcritos del catálogo del fabricante (ZS). Sujetos a cambio sin previo aviso;
  confirmá dimensiones, alimentación eléctrica y configuración final con nuestro equipo técnico antes de la compra.</p>
</div>
</div></body></html>
`
}

/* ---------- main ---------- */
fs.mkdirSync(OUT, { recursive: true })
let n = 0
for (const m of MODELOS) {
  fs.writeFileSync(path.join(OUT, `${slugOf(m.m)}.html`), ficha(m))
  n++
}
console.log(`plataformas OK — ${n} fichas técnicas geradas em public/fichas/`)
module.exports = { MODELOS, slugOf }
