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
  /<a href="#catalogo"/.test(l) && /Catálogo<\/a><\/li>/.test(l)
    ? '          <li><a href="#frentes" data-i18n="nav.grupo">Grupo</a></li>'
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
    k: 'equipos', ic: 'i-gear', t: 'Equipos',
    s: 'Importamos y representamos equipos y maquinaria para la construcción y la industria: reglas láser, bombas, grúas araña, montacargas y generadores. Selección estratégica del mercado internacional, con respaldo y repuestos locales.',
    cta: 'Ver productos', href: '../ventas/',
  },
  {
    k: 'aditivos', ic: 'i-flask', t: 'Aditivos',
    logo: '<img class="deck-logo on-chip" src="../img/logo-camargo.png" alt="Camargo Química" loading="lazy" onerror="this.remove()">',
    s: 'Distribuidores exclusivos de Camargo Química en Paraguay: aditivos y soluciones químicas para cada etapa de la obra — impermeabilizantes, plastificantes, curadores y desmoldantes, con asesoría técnica especializada.',
    cta: 'Ver productos', href: '../ventas/',
  },
  {
    k: 'fletes', ic: 'i-truck', t: 'Fletes · FletePar',
    logo: '<img class="deck-logo" src="../img/fletepar-logo.png" alt="FletePar" loading="lazy" onerror="this.remove()">',
    s: 'Nuestra plataforma tecnológica de logística. FletePar es el marketplace de fletes #1 de Paraguay: conecta empresas con cargas y transportistas verificados, con rastreo GPS en tiempo real, pagos protegidos y seguro de carga de punta a punta.',
    links: [
      ['i-android', 'App para Android — Google Play', 'https://play.google.com/store/apps/details?id=com.everson.FleteParapp'],
      ['i-apple', 'App para iPhone — App Store', 'https://apps.apple.com/app/id6759286072'],
    ],
  },
  {
    k: 'morteros', ic: 'i-tiles', t: 'Morteros',
    s: 'Revoques y morteros industrializados de desempeño consistente. Soluciones listas para usar que aceleran la obra y garantizan calidad uniforme en cada aplicación.',
    cta: 'Ver productos', href: '../ventas/',
  },
  {
    k: 'intonaco', ic: 'i-spray', t: 'Intonaco',
    logo: '<img class="deck-logo on-chip" src="../img/intonaco-logo.png" alt="Intonaco — Sistemas Constructivos" loading="lazy" onerror="this.remove()">',
    s: 'Sistemas constructivos Intonaco: revoque proyectado con método, equipamiento y personal entrenado. Hasta 5× más productividad que el revoque convencional, 1.000 m² en 5 a 7 días y consumo de material controlado — plazo, costo, calidad y satisfacción en cada obra.',
    cta: 'Conocer el sistema', ctaK: 'cta.conocer', href: '../ventas/',
  },
  {
    k: 'cementos', ic: 'i-layers', t: 'Cementos',
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
          <h3 data-i18n="fort.${i + 1}t">${title}</h3>
          <p data-i18n="fort.${i + 1}d">${desc}</p>
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
/* logos de marca dentro de las cajas del deck */
.cat .deck-logo{display:block;height:38px;width:auto;margin-bottom:12px}
.cat .deck-logo.on-chip{background:#fff;padding:7px 12px;border-radius:10px;height:46px}
/* enlaces FletePar dentro de la caja del deck */
.cat .fp-links{display:flex;flex-direction:column;gap:2px;margin-top:4px}
.cat .fp-links a{display:flex;align-items:center;gap:9px;min-height:40px;color:rgba(255,255,255,.85);text-decoration:none;font-size:14px;border-bottom:1px solid rgba(255,255,255,.09)}
.cat .fp-links a:last-child{border-bottom:0}
.cat .fp-links a:hover{color:var(--orange-soft)}
.cat .fp-links svg{width:18px;height:18px;stroke:var(--orange-soft);color:var(--orange-soft);flex-shrink:0}
</style>
<section class="fort-cine" id="frentes">
  <div class="wrap head reveal">
    <span class="tag">Grupo GNH</span>
    <h2 data-i18n="fort.h2">Nuestras <span style="color:var(--orange)">fortalezas</span></h2>
    <p data-i18n="fort.p">Cuatro pilares que trabajan como uno.</p>
  </div>
  ${scenes}
</section>

<!-- ============ NUESTROS NEGOCIOS (deck institucional) ============ -->
<section class="section alt" id="lineas">
  <div class="wrap">
    <h2 class="reveal d1" data-i18n="negocios.h2">Nuestros <span style="color:var(--orange)">Negocios</span></h2>
    <div class="cat-deck reveal d2">${LINEAS.map((L) => `
      <article class="cat" tabindex="0">
        <div class="ghost"><svg viewBox="0 0 24 24" fill="none"><use href="#${L.ic}"/></svg></div>
        <div class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><use href="#${L.ic}"/></svg></div>
        <span class="t-vert" data-i18n="deck.${L.k}.t">${L.t}</span>
        <div class="body">
          ${L.logo ?? ''}<h3 data-i18n="deck.${L.k}.t">${L.t}</h3>
          <p data-i18n="deck.${L.k}.s">${L.s}</p>
          ${L.links
            ? `<div class="fp-links">${L.links.map(([ic, label, href]) => `
            <a href="${href}" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><use href="#${ic}"/></svg> <span data-i18n="fp.${ic === 'i-android' ? 'android' : 'iphone'}">${label}</span></a>`).join('')}
          </div>`
            : `<a class="go" href="${L.href}"><span data-i18n="${L.ctaK ?? 'cta.ver'}">${L.cta}</span> <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"><use href="#i-arrow-r"/></svg></a>`}
        </div>
      </article>`).join('')}
    </div>
  </div>
</section>

<script>
window.I18N_EXTRA = {
pt: {
 'fort.h2':'Nossas <span style="color:var(--orange)">forças</span>','fort.p':'Quatro pilares que trabalham como um só.',
 'fort.1t':'Comércio Internacional','fort.1d':'Importação e exportação estratégicas. Conectamos marcas globais ao Paraguai e ao Brasil, com processos aduaneiros ágeis e seguros.',
 'fort.2t':'Logística — FletePar','fort.2d':'O marketplace de fretes nº 1 do Paraguai: conecta cargas a transportadores verificados, com rastreamento GPS e pagamentos seguros.',
 'fort.3t':'Representação de Marcas','fort.3d':'Representação exclusiva de marcas internacionais, com desenvolvimento comercial, posicionamento e suporte local.',
 'fort.4t':'Alianças Estratégicas','fort.4d':'Parceiros na China, no Brasil e no Paraguai que ampliam nosso alcance, nossa capacidade e nossos horizontes.',
 'negocios.h2':'Nossos <span style="color:var(--orange)">Negócios</span>',
 'deck.equipos.t':'Equipamentos','deck.equipos.s':'Importamos e representamos equipamentos e máquinas para a construção e a indústria: réguas a laser, bombas, guindastes-aranha, empilhadeiras e geradores. Seleção estratégica do mercado internacional, com suporte e peças locais.',
 'deck.aditivos.t':'Aditivos','deck.aditivos.s':'Distribuidores exclusivos da Camargo Química no Paraguai: aditivos e soluções químicas para cada etapa da obra — impermeabilizantes, plastificantes, curadores e desmoldantes, com assessoria técnica especializada.',
 'deck.fletes.t':'Fretes · FletePar','deck.fletes.s':'Nossa plataforma tecnológica de logística. O FletePar é o marketplace de fretes nº 1 do Paraguai: conecta empresas com cargas a transportadores verificados, com rastreamento GPS em tempo real, pagamentos protegidos e seguro de carga de ponta a ponta.',
 'deck.morteros.t':'Argamassas','deck.morteros.s':'Revestimentos e argamassas industrializadas de desempenho consistente. Soluções prontas para uso que aceleram a obra e garantem qualidade uniforme em cada aplicação.',
 'deck.intonaco.t':'Intonaco','deck.intonaco.s':'Sistemas construtivos Intonaco: reboco projetado com método, equipamento e equipe treinada. Até 5× mais produtividade que o reboco convencional, 1.000 m² em 5 a 7 dias e consumo de material controlado — prazo, custo, qualidade e satisfação em cada obra.',
 'deck.cementos.t':'Cimentos','deck.cementos.s':'Cimento de alto desempenho para toda obra, com abastecimento confiável e volumes em escala, respaldados por alianças industriais da região.',
 'cta.ver':'Ver produtos','cta.conocer':'Conhecer o sistema','fp.android':'App para Android — Google Play','fp.iphone':'App para iPhone — App Store'
},
en: {
 'fort.h2':'Our <span style="color:var(--orange)">strengths</span>','fort.p':'Four pillars working as one.',
 'fort.1t':'International Trade','fort.1d':'Strategic import and export. We connect global brands with Paraguay and Brazil through fast, secure customs processes.',
 'fort.2t':'Logistics — FletePar','fort.2d':"Paraguay's #1 freight marketplace: connecting cargo with verified carriers, with GPS tracking and secure payments.",
 'fort.3t':'Brand Representation','fort.3d':'Exclusive representation of international brands, with commercial development, positioning and local support.',
 'fort.4t':'Strategic Alliances','fort.4d':'Partners in China, Brazil and Paraguay expanding our reach, capacity and horizons.',
 'negocios.h2':'Our <span style="color:var(--orange)">Businesses</span>',
 'deck.equipos.t':'Equipment','deck.equipos.s':'We import and represent equipment and machinery for construction and industry: laser screeds, pumps, spider cranes, forklifts and generators. Strategically sourced worldwide, with local support and spare parts.',
 'deck.aditivos.t':'Admixtures','deck.aditivos.s':'Exclusive distributors of Camargo Química in Paraguay: admixtures and chemical solutions for every stage of the job — waterproofing agents, plasticizers, curing compounds and release agents, with specialized technical advice.',
 'deck.fletes.t':'Freight · FletePar','deck.fletes.s':"Our logistics technology platform. FletePar is Paraguay's #1 freight marketplace: connecting companies with cargo to verified carriers, with real-time GPS tracking, protected payments and end-to-end cargo insurance.",
 'deck.morteros.t':'Mortars','deck.morteros.s':'Industrialized renders and mortars with consistent performance. Ready-to-use solutions that speed up the job and guarantee uniform quality in every application.',
 'deck.intonaco.t':'Intonaco','deck.intonaco.s':'Intonaco building systems: sprayed rendering with method, equipment and trained crews. Up to 5× the productivity of conventional rendering, 1,000 m² in 5–7 days and controlled material consumption — schedule, cost, quality and satisfaction on every job.',
 'deck.cementos.t':'Cements','deck.cementos.s':'High-performance cement for every job, with reliable supply and volumes at scale, backed by regional industrial alliances.',
 'cta.ver':'See products','cta.conocer':'Discover the system','fp.android':'Android app — Google Play','fp.iphone':'iPhone app — App Store'
},
zh: {
 'fort.h2':'我们的<span style="color:var(--orange)">优势</span>','fort.p':'四大支柱，协同如一。',
 'fort.1t':'国际贸易','fort.1d':'战略性进出口业务。我们以快捷安全的清关流程，连接全球品牌与巴拉圭和巴西市场。',
 'fort.2t':'物流 — FletePar','fort.2d':'巴拉圭排名第一的货运平台：连接货主与认证承运人，提供GPS追踪与安全支付。',
 'fort.3t':'品牌代理','fort.3d':'国际品牌独家代理：商业开发、市场定位与本地支持。',
 'fort.4t':'战略联盟','fort.4d':'中国、巴西与巴拉圭的合作伙伴，不断拓展我们的覆盖、能力与视野。',
 'negocios.h2':'我们的<span style="color:var(--orange)">业务</span>',
 'deck.equipos.t':'设备','deck.equipos.s':'我们进口并代理建筑与工业设备机械：激光整平机、泵送设备、蜘蛛吊、叉车与发电机。全球战略选品，本地保障与备件供应。',
 'deck.aditivos.t':'外加剂','deck.aditivos.s':'Camargo Química在巴拉圭的独家经销商：覆盖施工各阶段的外加剂与化学解决方案——防水剂、减水剂、养护剂与脱模剂，并提供专业技术咨询。',
 'deck.fletes.t':'货运 · FletePar','deck.fletes.s':'我们的物流科技平台。FletePar是巴拉圭排名第一的货运平台：连接货主企业与认证承运人，提供实时GPS追踪、支付保障与全程货物保险。',
 'deck.morteros.t':'砂浆','deck.morteros.s':'性能稳定的工业化抹灰与砂浆。即取即用，加快施工进度，确保每次施工质量均一。',
 'deck.intonaco.t':'Intonaco','deck.intonaco.s':'Intonaco建筑体系：以方法、设备与训练有素的团队实施机械喷涂抹灰。生产效率最高可达传统抹灰的5倍，1000平方米仅需5–7天，材料消耗可控——工期、成本、质量与满意度全面保障。',
 'deck.cementos.t':'水泥','deck.cementos.s':'适用于各类工程的高性能水泥，供应可靠、规模保障，依托区域工业联盟支持。',
 'cta.ver':'查看产品','cta.conocer':'了解系统','fp.android':'安卓应用 — Google Play','fp.iphone':'iPhone应用 — App Store'
}
};
</script>

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
