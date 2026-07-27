#!/usr/bin/env node
/* ============================================================
   Fichas técnicas das GRÚAS ARAÑA (ZS) — mesmo formato visual das
   fichas de aditivos: folha A4 com marca GNH, tabela de dados,
   curva de carga e diagrama dimensional do fabricante.

   Gera  gnh-hero/public/fichas/grua-arana-<t>.html
   (os PDFs saem depois com tools/make-pdfs.cjs, que varre essa pasta)

   ⚠️ Dados transcritos dos catálogos do fabricante. Não inventar nada:
   campo sem dado no catálogo fica fora da tabela.
   ============================================================ */
const fs = require('fs')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')
const OUT = path.join(ROOT, 'public', 'fichas')
const IMGDIR = path.join(ROOT, 'public', 'img', 'prod', 'grua')
const WA = '595995360060'

/* ---------- dados dos catálogos (1 objeto por modelo) ---------- */
const MODELOS = [
  { t: '1.5', cap: '1,5 t', radio: '6 m', altura: '6,5 m', ancho: '0,65 m', largo: '2,5 m', alto: '1,5 m',
    peso: '1.300 kg', motor: 'Honda 390, nafta (arranque eléctrico)', pluma: '2 m × 4 secciones · 6,5 m / 20 s',
    gancho: '0-8 m/min (4 cables)', cable: 'Ø 8 mm × 45 m', giro: '0-360° continuo / 60 s',
    outrigger: '3.600 (largo) × 3.400 (tras.) × 3.400 (del.) mm', oruga: '180 mm de ancho',
    marcha: '0-2,5 km/h · rampa 25° (36%)', chart: null },
  { t: '3', cap: '3 t', radio: '10,5 m', altura: '10,8 m', ancho: '0,80 m', largo: '3,5 m', alto: '1,85 m',
    peso: '3.000 kg', motor: 'Changchai EV80 diésel (Fase II)', pluma: '6 secciones · 10,8 m · 3,1-9,2 m / 20 s',
    gancho: '0-12 m/min (4 cables)', cable: 'Ø 8 mm × 50 m', giro: '0-360° continuo / 60 s',
    outrigger: '4.530 (largo) × 4.370 (tras.) × 3.700 (del.) mm', oruga: '230 mm de ancho',
    marcha: '0-2,5 km/h · rampa 25° (36%)', chart: '3t' },
  { t: '4', cap: '4 t', radio: '13 m', altura: '15 m', ancho: '1,00 m', largo: '4,25 m', alto: '1,83 m',
    peso: '3.000 kg (según catálogo)', motor: 'Changchai 380G diésel, 3 cilindros, 14,7 kW',
    pluma: '2,8 m × 7 secciones · 3,1-15 m / 20 s', gancho: '0-8 m/min (4 cables)', cable: 'Ø 8 mm × 45 m',
    giro: '0-360° continuo / 60 s', outrigger: '4.230 × 3.830 × 4.310 mm',
    oruga: '230 mm de ancho', marcha: '0-2,5 km/h · rampa 25% (36%)', chart: null },
  { t: '5', cap: '5 t', radio: '15 m', altura: '17 m', ancho: '1,50 m', largo: '4,7 m', alto: '2,25 m',
    peso: '6.100 kg', motor: 'Diésel 55 kW (490), Fase II', pluma: '5 secciones · 21 m · 4,5-17 m / 54 s',
    gancho: '12 m/min (4 cables)', cable: 'Ø 11 mm × 60 m', giro: '0-360° continuo / 38 s',
    outrigger: '5.800 (largo) × 4.900 (tras.) × 5.600 (del.) mm', oruga: '2.200 mm largo × 300 mm ancho',
    marcha: '0-2,5 km/h · rampa 25° (36%)', chart: '5t' },
  { t: '8', cap: '8 t', radio: '18 m', altura: '21 m', ancho: '1,60 m', largo: '6,15 m', alto: '2,25 m',
    peso: '8.700 kg', motor: 'Diésel 55 kW (490), Fase II', pluma: '5 secciones · 21 m · 5,5-21 m / 54 s',
    gancho: '12 m/min (4 cables)', cable: 'Ø 12 mm × 80 m', giro: '0-360° continuo / 38 s',
    outrigger: '7.400 mm (largo) × 5.800 mm (ancho)', oruga: '2.600 mm largo × 350 mm ancho',
    marcha: '0-2,5 km/h (dos velocidades) · rampa 25° (36%)', chart: '8t' },
  { t: '10', cap: '10 t', radio: '18,5 m', altura: '19,5 m', ancho: '1,80 m', largo: '5,9 m', alto: '2,3 m',
    peso: '10.500 kg', motor: 'Diésel 55 kW, Fase II', pluma: '5 secciones · 21 m · 12,3 m / 58 s',
    gancho: '11 m/min (4 cables)', cable: 'Ø 12 mm × 100 m', giro: '0-360° continuo / 40 s',
    outrigger: '7.000 mm (izq./der.) × 6.500 mm (del./tras.)', oruga: '2.600 mm largo × 350 mm ancho',
    marcha: '0-2,5 km/h (dos velocidades) · rampa 25° (36%)', chart: '10t' },
  { t: '12', cap: '12 t', radio: '19 m', altura: '21 m', ancho: '1,83 m', largo: '6,15 m', alto: '2,48 m',
    peso: '12.500 kg', motor: 'Diésel 55 kW, Fase II', pluma: '5 secciones · 21 m · 12,3 m / 60 s',
    gancho: '10 m/min (4 cables)', cable: 'Ø 12 mm × 120 m', giro: '0-360° continuo / 40 s',
    outrigger: '7.000 mm (izq./der.) × 7.100 mm (del./tras.)', oruga: '2.800 mm largo × 400 mm ancho',
    marcha: '0-2,5 km/h (dos velocidades) · rampa 25° (36%)', chart: '12t' },
  { t: '16', cap: '16 t', radio: '23 m', altura: '25 m', ancho: '2,70 m', largo: '6,6 m', alto: '2,48 m',
    peso: '16.500 kg', motor: 'Yuchai diésel, Fase II', pluma: '6,5 secciones · 25 m · 12,3 m / 40 s',
    gancho: '10 m/min (4 cables)', cable: 'Ø 12 mm × 140 m', giro: '0-360° continuo / 42 s',
    outrigger: '8.100 (largo) × 5.600 (tras.) × 6.700 (del.) mm', oruga: 'accionamiento hidráulico, dos velocidades',
    marcha: '0-2,5 km/h · rampa 25° (36%)', chart: '16t' },
]

/* ---------- helpers ---------- */
const b64 = (p) => (fs.existsSync(p) ? fs.readFileSync(p).toString('base64') : '')
const logoB64 = b64(path.join(ROOT, 'public', 'img', 'logo-ficha.png'))
const logoImg = (h) => logoB64
  ? `<img src="data:image/png;base64,${logoB64}" alt="GNH" style="height:${h}px;width:auto">`
  : '<b>GNH</b>'
// caminho relativo: leve na web e resolve igual no file:// do gerador de PDF
const imgTag = (file, alt) => {
  if (!fs.existsSync(path.join(IMGDIR, file))) return ''
  return `<img src="../img/prod/grua/${file}" alt="${alt}" style="width:100%;height:auto;border:1px solid var(--hair)">`
}

const row = (k, v) => v ? `<tr><th>${k}</th><td>${v}</td></tr>` : ''

function ficha(m) {
  const slug = `grua-arana-${m.t.replace('.', '-')}t`
  const name = `Grúa Araña ${m.cap} (Spider Crane)`
  const waMsg = encodeURIComponent(`Hola, me interesa la Grúa Araña de ${m.cap}`)
  const chart = m.chart ? imgTag(`carga-${m.chart}.jpg`, `Curva de carga — grúa araña ${m.cap}`) : ''
  const dim = imgTag(`dim-${m.t}t.jpg`, `Diagrama dimensional — grúa araña ${m.cap}`)

  return `<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${name} — Ficha Técnica | GNH</title>
<meta name="description" content="Ficha técnica de la grúa araña de ${m.cap}: radio máximo ${m.radio}, altura ${m.altura}, ancho de paso ${m.ancho}, peso ${m.peso}. Curva de carga y dimensiones. GNH Paraguay.">
<link rel="canonical" href="https://gnhorizons.com/fichas/${slug}.html">
<style>
:root{--navy:#14213D;--ink:#1e2733;--orange:#F26D21;--gold:#C9A961;--line:#D8DEE8;--hair:#E6EAF0;--fam:#F59E0B}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'General Sans','Liberation Sans','Helvetica Neue',Arial,sans-serif;color:var(--ink);background:#EEF1F5;line-height:1.6}
.sheet{max-width:860px;margin:0 auto;background:#fff;min-height:100vh;box-shadow:0 30px 80px -40px rgba(15,23,42,.3)}
.top{background:#fff;padding:30px 46px 0}
.brand-row{display:flex;align-items:center;justify-content:space-between;gap:18px;padding-bottom:18px}
.doc-tag{text-align:right}
.doc-tag .dt{display:block;font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-weight:800;font-size:17px;letter-spacing:.24em;text-transform:uppercase;color:var(--navy)}
.doc-tag .fam{display:inline-flex;align-items:center;gap:7px;margin-top:7px;font-size:10.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#5B6472;border:1px solid var(--line);border-radius:3px;padding:3px 10px}
.doc-tag .fam::before{content:'';width:8px;height:8px;border-radius:50%;background:var(--fam)}
.rule{height:2px;background:var(--navy);position:relative}
.rule::after{content:'';position:absolute;left:0;top:2px;height:1px;width:100%;background:var(--gold)}
.title-block{padding:24px 0 20px;border-bottom:1px solid var(--line)}
h1{font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-weight:800;font-size:clamp(24px,4vw,34px);letter-spacing:-.01em;text-transform:uppercase;color:var(--navy);line-height:1.06}
.sub{color:#5B6472;margin-top:6px;font-size:15.5px}
.actions{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap;padding-bottom:8px}
.btn{display:inline-flex;align-items:center;gap:8px;min-height:42px;padding:9px 20px;border-radius:6px;font-weight:700;font-size:13.5px;text-decoration:none;font-family:'Satoshi','Liberation Sans',Arial,sans-serif}
.btn-pdf{background:var(--navy);color:#fff}
.btn-wa{background:#22c15e;color:#fff}
.btn-back{background:#fff;color:var(--navy);border:1.5px solid var(--line)}
.body{padding:6px 46px 26px}
.body h2{font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-size:12px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--navy);margin:26px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--hair);display:flex;align-items:center;gap:10px}
.body h2::before{content:'';width:3px;height:13px;background:var(--navy);flex-shrink:0}
.body p{font-size:13.2px;color:#3c4657;line-height:1.7;margin:0 0 10px}
table.kv{width:100%;border-collapse:collapse;border:1px solid var(--hair);border-top:2px solid var(--navy)}
.kv th{width:34%;text-align:left;font-weight:600;color:var(--navy);background:#F4F6FA;padding:8px 18px;font-size:12.6px;border-bottom:1px solid var(--hair);border-right:1px solid var(--hair);vertical-align:top}
.kv td{padding:8px 18px;font-size:12.8px;color:#3c4657;border-bottom:1px solid var(--hair)}
.kv tr:last-child th,.kv tr:last-child td{border-bottom:0}
.hero-num{display:flex;gap:26px;flex-wrap:wrap;margin:14px 0 4px}
.hero-num div{min-width:96px}
.hero-num b{display:block;font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-size:26px;color:var(--orange);line-height:1.1}
.hero-num span{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#7c8698}
figure{margin:10px 0 4px}
figcaption{font-size:11px;color:#8a93a3;margin-top:6px;font-style:italic}
.foot{padding:18px 46px 22px;border-top:2px solid var(--navy);font-size:11.5px;color:#5B6472}
.foot b{color:var(--navy)}
.foot .note{font-style:italic;color:#8a93a3;font-size:10.5px;margin-top:12px;padding-top:9px;border-top:1px solid var(--hair);text-align:center}
@media print{body{background:#fff}.sheet{box-shadow:none;max-width:none}.actions{display:none}}
</style></head>
<body><div class="sheet">
<div class="top">
  <div class="brand-row">${logoImg(58)}
    <div class="doc-tag"><span class="dt">Ficha Técnica</span><span class="fam">Grúas araña</span></div>
  </div>
  <div class="rule"></div>
  <div class="title-block">
    <h1>${name}</h1>
    <p class="sub">Grúa araña de orugas · izaje en espacios reducidos · control remoto e indicador de par</p>
    <div class="actions">
      <a class="btn btn-pdf" href="pdf/${slug}.pdf" download>Descargar PDF</a>
      <a class="btn btn-wa" href="https://wa.me/${WA}?text=${waMsg}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
      <a class="btn btn-back" href="/ventas/grua-arana/">Ver todos los modelos</a>
    </div>
  </div>
</div>
<div class="body">
  <div class="hero-num">
    <div><b>${m.cap}</b><span>Capacidad</span></div>
    <div><b>${m.radio}</b><span>Radio máx.</span></div>
    <div><b>${m.altura}</b><span>Altura máx.</span></div>
    <div><b>${m.ancho}</b><span>Ancho de paso</span></div>
  </div>

  <h2>Rendimiento</h2>
  <table class="kv">
    ${row('Capacidad máxima', m.cap)}
    ${row('Radio máximo de operación', m.radio)}
    ${row('Altura máxima de elevación', m.altura)}
    ${row('Pluma telescópica', m.pluma)}
    ${row('Velocidad del gancho', m.gancho)}
    ${row('Cable de acero', m.cable)}
    ${row('Rotación', m.giro)}
  </table>

  <h2>Dimensiones y traslado</h2>
  <table class="kv">
    ${row('Ancho de paso', `<b>${m.ancho}</b> — define por dónde entra la máquina`)}
    ${row('Largo × alto (transporte)', `${m.largo} × ${m.alto}`)}
    ${row('Peso propio', m.peso)}
    ${row('Apertura de estabilizadores', m.outrigger)}
    ${row('Orugas', m.oruga)}
    ${row('Traslación', m.marcha)}
  </table>

  <h2>Motorización</h2>
  <table class="kv">
    ${row('Motor', m.motor)}
    ${row('Sistema eléctrico', 'AC 380 V · arranque eléctrico')}
    ${row('Operación', 'Manual (pluma y traslación) · control remoto opcional')}
    ${row('Opcionales', 'Controlador de par de torsión · control remoto · cesta suspensa · pluma auxiliar hidráulica')}
  </table>

  ${chart ? `<h2>Curva de carga</h2>
  <figure>${chart}<figcaption>Tabla de cargas del fabricante: capacidad según radio de operación y ángulo de pluma. Consultá la curva antes de definir el izaje.</figcaption></figure>` : ''}

  ${dim ? `<h2>Diagrama dimensional</h2>
  <figure>${dim}<figcaption>Dimensiones de transporte y apertura de estabilizadores (mm).</figcaption></figure>` : ''}

  <h2>Aplicaciones</h2>
  <p>Montaje de vidrio y fachadas, instalación de equipos en interiores, mantenimiento de subestaciones,
  obras con acceso restringido, patios y plantas industriales — donde una grúa convencional no entra ni se estabiliza.
  El chasis de orugas de goma no daña el piso terminado.</p>
</div>
<div class="foot">
  <p><b>GNH — Generando Nuevos Horizontes</b> · Av. República del Perú km 7, Ciudad del Este · Acceso Sur, Ñemby, Paraguay</p>
  <p>WhatsApp <b>+595 995 360060</b> · comercial@gnhorizons.com · gnhorizons.com</p>
  <p class="note">Datos transcritos del catálogo del fabricante (ZS / Jinan Zhishen). Sujetos a cambio sin previo aviso;
  confirmá la configuración final con nuestro equipo técnico antes de la compra.</p>
</div>
</div></body></html>
`
}

/* ---------- main ---------- */
fs.mkdirSync(OUT, { recursive: true })
let n = 0
for (const m of MODELOS) {
  const slug = `grua-arana-${m.t.replace('.', '-')}t`
  fs.writeFileSync(path.join(OUT, `${slug}.html`), ficha(m))
  n++
}
console.log(`gruas OK — ${n} fichas técnicas geradas em public/fichas/`)
module.exports = { MODELOS }
