// Monta /institucional/ a partir de gnh-redesign.html:
// - remove a seção Catálogo (é venda)
// - injeta no lugar um deck institucional "Frentes del grupo" (mesmo movimento .cat-deck)
// - fixa paths de vídeo p/ absolutos
const fs = require('fs')
const path = require('path')

// Raíz del repo (este archivo vive en gnh-hero/tools/)
const REPO = path.resolve(__dirname, '..', '..')
const src = fs.readFileSync(path.join(REPO, 'gnh-redesign.html'), 'utf8')
let lines = src.split('\n')

// 1) troca o item de menu "Catálogo" por "Grupo" -> #frentes
lines = lines.map((l) =>
  /<li><a href="#catalogo">Catálogo<\/a><\/li>/.test(l)
    ? '          <li><a href="#frentes">Grupo</a></li>'
    : l)

let html = lines.join('\n')

// 2) "Nuestras fortalezas" em formato CINEMATOGRÁFICO (cenas alternadas, big type, reveal)
const FRENTES = [
  ['i-globe', 'Comercio Internacional', 'Importación y exportación estratégica. Conectamos marcas globales con Paraguay y Brasil, con procesos aduaneros ágiles y seguros.'],
  ['i-truck', 'Logística — FletePar', 'El marketplace de fletes \u00231 de Paraguay: conecta cargas con transportistas verificados, con rastreo GPS y pagos seguros.'],
  ['i-handshake', 'Representación de Marcas', 'Representación exclusiva de marcas internacionales, con desarrollo comercial, posicionamiento y soporte local.'],
  ['i-spark', 'Alianzas Estratégicas', 'Socios en China, Brasil y Paraguay que amplían nuestro alcance, nuestra capacidad y nuestros horizontes.'],
]
// deck institucional: cada frente de negocio con su resumen (se revela al seleccionar)
const LINEAS = [
  {
    ic: 'i-gear', t: 'Equipos',
    s: 'Importamos y representamos equipos y maquinaria para la construcción y la industria: reglas láser, bombas, grúas araña, montacargas y generadores. Selección estratégica del mercado internacional, con respaldo y repuestos locales.',
    cta: 'Ver productos', href: '../ventas/',
  },
  {
    ic: 'i-flask', t: 'Aditivos',
    s: 'Distribuimos aditivos y soluciones químicas de marcas líderes para cada etapa de la obra: impermeabilizantes, plastificantes, curadores y desmoldantes, con asesoría técnica especializada.',
    cta: 'Ver productos', href: '../ventas/',
  },
  {
    ic: 'i-truck', t: 'Fletes · FletePar',
    s: 'Nuestra plataforma tecnológica de logística. FletePar es el marketplace de fletes #1 de Paraguay: conecta empresas con cargas y transportistas verificados, con rastreo GPS en tiempo real, pagos protegidos y seguro de carga de punta a punta.',
    links: [
      ['i-globe', 'fletepar.com.py', 'https://fletepar.com.py/'],
      ['i-handshake', 'WhatsApp +595 985 336 505', 'https://wa.me/595985336505?text=Hola,%20quiero%20m%C3%A1s%20informaci%C3%B3n%20sobre%20FletePar'],
      ['i-arrow-r', 'App para Android', 'https://play.google.com/store/apps/details?id=com.everson.FleteParapp'],
      ['i-arrow-r', 'App para iPhone', 'https://apps.apple.com/app/id6759286072'],
      ['i-spark', 'Consulta de reputación', 'https://fletepar-consulta.web.app'],
    ],
  },
  {
    ic: 'i-tiles', t: 'Morteros',
    s: 'Revoques y morteros industrializados de desempeño consistente. Soluciones listas para usar que aceleran la obra y garantizan calidad uniforme en cada aplicación.',
    cta: 'Ver productos', href: '../ventas/',
  },
  {
    ic: 'i-spray', t: 'Intonaco',
    s: 'Sistemas constructivos Intonaco: revoque proyectado con método, equipamiento y personal entrenado. Hasta 5× más productividad que el revoque convencional, 1.000 m² en 5 a 7 días y consumo de material controlado — plazo, costo, calidad y satisfacción en cada obra.',
    cta: 'Conocer el sistema', href: '../ventas/',
  },
  {
    ic: 'i-layers', t: 'Cementos',
    s: 'Cemento de alto desempeño para toda obra, con abastecimiento confiable y volúmenes a escala, respaldados por alianzas industriales de la región.',
    cta: 'Ver productos', href: '../ventas/',
  },
]

const scenes = FRENTES.map(([ic, title, desc], i) => `
    <div class="fort-scene reveal">
      <div class="wrap fort-row">
        <div class="fort-num" aria-hidden="true">0${i + 1}</div>
        <div class="fort-text">
          <div class="fort-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><use href="#${ic}"/></svg></div>
          <h3>${title}</h3>
          <p>${desc}</p>
        </div>
        <div class="fort-ghost" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><use href="#${ic}"/></svg></div>
      </div>
    </div>`).join('')

const NEW_DECK = `<!-- ============ NUESTRAS FORTALEZAS (cinematográfico) ============ -->
<style>
.fort-cine{background:radial-gradient(900px 500px at 80% 0%,rgba(242,109,33,.12),transparent 60%),linear-gradient(180deg,var(--navy-deep),var(--navy-ink));padding:104px 0 72px;position:relative;overflow:hidden}
.fort-cine .head{margin-bottom:26px}
.fort-cine .head h2{color:#fff;font-size:clamp(30px,4.6vw,50px)}
.fort-cine .head p{color:rgba(255,255,255,.62);font-size:18px;margin-top:10px}
.fort-scene{padding:44px 0;border-top:1px solid rgba(255,255,255,.07)}
.fort-row{display:flex;align-items:center;gap:36px;position:relative}
.fort-scene:nth-child(even) .fort-row{flex-direction:row-reverse}
.fort-num{font-family:var(--font-head);font-weight:800;font-size:clamp(64px,11vw,140px);line-height:.85;color:transparent;-webkit-text-stroke:1.5px rgba(255,255,255,.14);flex-shrink:0}
.fort-text{max-width:600px}
.fort-ic{width:58px;height:58px;border-radius:16px;background:linear-gradient(135deg,#ff7a2e,#ff9e5e);display:grid;place-items:center;margin-bottom:18px;box-shadow:0 12px 30px -6px rgba(242,109,33,.75),inset 0 1px 0 rgba(255,255,255,.35)}
.fort-ic svg{width:31px;height:31px;stroke:#fff;stroke-width:2.2}
.fort-text h3{color:#fff;font-size:clamp(24px,3.2vw,36px);margin-bottom:12px}
.fort-text p{color:rgba(255,255,255,.72);font-size:17.5px;line-height:1.6}
.fort-ghost{margin-left:auto;opacity:.05;flex-shrink:0}
.fort-scene:nth-child(even) .fort-ghost{margin-left:0;margin-right:auto}
.fort-ghost svg{width:150px;height:150px;stroke:#fff}
@media(max-width:820px){
  .fort-row,.fort-scene:nth-child(even) .fort-row{flex-direction:column;text-align:center;gap:6px}
  .fort-ic{margin-inline:auto}.fort-ghost{display:none}.fort-text p{margin-inline:auto}
}
/* enlaces FletePar dentro de la caja del deck */
.cat .fp-links{display:flex;flex-direction:column;gap:2px;margin-top:4px}
.cat .fp-links a{display:flex;align-items:center;gap:9px;min-height:40px;color:rgba(255,255,255,.85);text-decoration:none;font-size:14px;border-bottom:1px solid rgba(255,255,255,.09)}
.cat .fp-links a:last-child{border-bottom:0}
.cat .fp-links a:hover{color:var(--orange-soft)}
.cat .fp-links svg{width:16px;height:16px;stroke:var(--orange-soft);flex-shrink:0}
</style>
<section class="fort-cine" id="frentes">
  <div class="wrap head reveal">
    <span class="tag">Grupo GNH</span>
    <h2>Nuestras <span style="color:var(--orange)">fortalezas</span></h2>
    <p>Cuatro pilares que trabajan como uno.</p>
  </div>
  ${scenes}
</section>

<!-- ============ NUESTROS NEGOCIOS (deck institucional) ============ -->
<section class="section alt" id="lineas">
  <div class="wrap">
    <h2 class="reveal d1">Nuestros <span style="color:var(--orange)">Negocios</span></h2>
    <div class="cat-deck reveal d2">${LINEAS.map((L) => `
      <article class="cat" tabindex="0">
        <div class="ghost"><svg viewBox="0 0 24 24" fill="none"><use href="#${L.ic}"/></svg></div>
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><use href="#${L.ic}"/></svg></div>
        <span class="t-vert">${L.t}</span>
        <div class="body">
          <h3>${L.t}</h3>
          <p>${L.s}</p>
          ${L.links
            ? `<div class="fp-links">${L.links.map(([ic, label, href]) => `
            <a href="${href}" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><use href="#${ic}"/></svg> ${label}</a>`).join('')}
          </div>`
            : `<a class="go" href="${L.href}">${L.cta} <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"><use href="#i-arrow-r"/></svg></a>`}
        </div>
      </article>`).join('')}
    </div>
  </div>
</section>

`

// 3) substitui a seção Catálogo pelo novo deck
const start = html.indexOf('<!-- ============ CATÁLOGO ============ -->')
const showcase = html.indexOf('<!-- ============ SHOWCASE FROTA GNH ============ -->')
if (start !== -1 && showcase !== -1 && showcase > start) {
  html = html.slice(0, start) + NEW_DECK + html.slice(showcase)
} else {
  throw new Error('marcadores de catálogo não encontrados')
}

// 3b) quita la banda clara de Contacto (el pie oscuro ya trae contacto y redes);
//     el ancla #contacto pasa al propio footer para que el menú siga funcionando
const cStart = html.indexOf('<!-- ============ CONTACTO ============ -->')
const cEnd = html.indexOf('<!-- ============ FOOTER ============ -->')
if (cStart !== -1 && cEnd !== -1 && cEnd > cStart) {
  html = html.slice(0, cStart) + html.slice(cEnd)
  html = html.replace('<!-- ============ FOOTER ============ -->\n<footer>', '<!-- ============ FOOTER ============ -->\n<footer id="contacto">')
} else {
  throw new Error('marcadores de contacto não encontrados')
}

// 4) vídeos e logos de clientes: caminho absoluto (a página fica em /assets/nuevo/institucional/)
html = html.replace(/(src|data-src)="assets\/video\//g, '$1="/assets/video/')
html = html.replace(/'assets\/img\/clients\/'/g, "'/assets/img/clients/'")

// 5) grava en dist/ y en assets/nuevo/ (esta última es la copia versionada que se despliega)
const outDirs = [
  path.join(REPO, 'gnh-hero', 'dist', 'institucional'),
  path.join(REPO, 'assets', 'nuevo', 'institucional'),
]
for (const outDir of outDirs) {
  fs.mkdirSync(outDir, { recursive: true })
  fs.writeFileSync(path.join(outDir, 'index.html'), html)
}

// sanity
if (/id="catalogo"/.test(html)) throw new Error('catálogo ainda presente')
if (/Contacta con nosotros/.test(html)) throw new Error('banda de contacto ainda presente')
if (!/<footer id="contacto">/.test(html)) throw new Error('âncora #contacto não movida ao footer')
if (!/id="frentes"/.test(html)) throw new Error('deck de frentes não injetado')
if (!/id="flota"/.test(html)) throw new Error('showcase sumiu')
if (!/<\/html>\s*$/.test(html)) throw new Error('HTML truncado')
console.log('institucional OK —', (html.length / 1024).toFixed(0) + 'KB, deck "Frentes del grupo" injetado, catálogo removido')
