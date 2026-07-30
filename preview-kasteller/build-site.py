#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o site one-page da KASTELLER REVESTIMIENTOS como HTML autocontido.

Por que autocontido: o ambiente de trabalho bloqueia CDNs externos, e a prévia
é publicada sob CSP estrita. Então fontes (Google Fonts, subsetadas) e imagens
entram em base64. No projeto real isso vira /fonts e /img normais.

  python3 build-site.py [pasta-de-assets]  ->  kasteller-site.html

Assets esperados em assets-site/:
  fonts.css              faces @font-face já em base64 (Cormorant Garamond + Inter)
  ks-hero.jpg            foto real de ambiente
  marmol-blanco.jpg  marmol-negro.jpg  travertino.jpg
  piedra-gris.jpg    porcelanato.jpg   madera.jpg      texturas provisórias
"""
import base64, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'assets-site'


def data_uri(name, mime):
    p = SRC / name
    if not p.exists():
        raise SystemExit(f'falta o asset: {p}')
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()


IMG = {k: data_uri(f'{k}.jpg', 'image/jpeg') for k in (
    'ks-hero', 'marmol-blanco', 'marmol-negro', 'travertino',
    'piedra-gris', 'porcelanato', 'madera')}

# Cada imagem vira UMA variável CSS — usá-la N vezes no HTML não duplica os bytes.
VARS = (':root{' + ''.join(f'--i-{k}:url({v});' for k, v in IMG.items()) + '}\n'
        + '.ph{background-size:cover;background-position:center;background-repeat:no-repeat}\n'
        + '\n'.join(f'.i-{k}{{background-image:var(--i-{k})}}' for k in IMG))
FONTS = (SRC / 'fonts.css').read_text()

# Monograma K: traçado a partir da geometria real do logo (chevron + duas cunhas)
KMARK = ('<svg class="k" viewBox="0 0 113 126" aria-hidden="true">'
         '<path d="M50 0 H93 L43 63 L93 126 H50 L0 63 Z"/>'
         '<path d="M0 0 H37 L0 43 Z"/>'
         '<path d="M0 83 L37 126 H0 Z"/></svg>')

CSS = """
__FONTS__

:root{
  --negro:#000; --blanco:#fff; --crema:#E8E1D7; --taupe:#544F4B;
  --serif:'Cormorant Garamond',Georgia,'Times New Roman',serif;
  --sans:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;
  --gut:clamp(20px,4.6vw,64px);
  --aire:clamp(84px,13vh,200px);
}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--negro);color:var(--crema);font-family:var(--sans);
  font-weight:300;line-height:1.7;overflow-x:hidden;-webkit-font-smoothing:antialiased}
img{display:block;max-width:100%}
a{color:inherit;text-decoration:none}
:focus-visible{outline:2px solid var(--crema);outline-offset:4px}
.k{width:1em;height:1.115em;fill:currentColor;display:block}

.rotulo{font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;font-weight:500}
.serif{font-family:var(--serif);font-weight:300;line-height:1.04;letter-spacing:-.005em}
.marca-txt{font-family:var(--sans);font-weight:400;letter-spacing:.26em;text-transform:uppercase}

/* marcador-assinatura: quadradinho taupe */
.pin::before{content:'';display:inline-block;width:7px;height:7px;background:var(--taupe);
  margin-right:11px;vertical-align:middle}

/* ---------------- header ---------------- */
.top{position:fixed;inset:0 0 auto;z-index:60;display:flex;align-items:center;
  justify-content:space-between;gap:20px;padding:20px var(--gut);color:var(--blanco)}
.top::before{content:'';position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:linear-gradient(180deg,rgba(0,0,0,.72),rgba(0,0,0,.28) 55%,transparent);
  transition:background .45s ease}
/* passado o hero, fundo sólido: o logo branco continua legível sobre as seções creme */
.top.solido::before{background:rgba(0,0,0,.92)}
.top .logo{display:flex;align-items:center;gap:11px;font-size:14px}
.top .logo .k{width:19px;height:21px}
.top .logo b{font-weight:400;letter-spacing:.24em;font-size:13.5px}
.top .logo i{font-style:normal;letter-spacing:.24em;font-size:8px;opacity:.72;display:block;
  margin-top:2px}
.top nav{display:flex;gap:30px}
.top nav a{font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;opacity:.78}
.top nav a:hover{opacity:1}
.cita{border:1px solid rgba(255,255,255,.42);padding:11px 20px;font-size:10px;
  letter-spacing:.22em;text-transform:uppercase;white-space:nowrap;transition:.35s}
.cita:hover{background:var(--blanco);color:var(--negro);border-color:var(--blanco)}
.burger{display:none;background:none;border:0;color:inherit;font:inherit;cursor:pointer;
  font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;padding:8px 0}

/* menu mobile */
.overlay{position:fixed;inset:0;z-index:59;background:var(--negro);display:grid;
  align-content:center;gap:6px;padding:0 var(--gut);opacity:0;visibility:hidden;
  transition:opacity .45s ease,visibility .45s}
.overlay.on{opacity:1;visibility:visible}
.overlay a{font-family:var(--serif);font-size:clamp(34px,10vw,58px);line-height:1.18;
  color:var(--crema);opacity:0;transform:translateY(16px);
  transition:opacity .5s ease,transform .5s ease}
.overlay.on a{opacity:1;transform:none}
.overlay .k{position:absolute;right:-6vw;bottom:-4vh;width:56vw;height:auto;
  color:var(--crema);opacity:.05}

/* ---------------- hero ---------------- */
.hero{position:relative;min-height:100svh;overflow:hidden;background:var(--negro)}
.mosaico{position:absolute;inset:0;display:grid;grid-template-columns:repeat(3,1fr);gap:10px;
  padding:10px}
.col{display:grid;gap:10px;align-content:start;will-change:transform}
.col figure{margin:0;overflow:hidden;background:#121110;opacity:0;transform:translateY(26px)}
.col .ph{width:100%;height:100%;filter:grayscale(.18) brightness(.82)}
.col.a .ph{filter:grayscale(.3) brightness(.7)}
.col.c .ph{filter:grayscale(.12) brightness(.88)}
.col.a figure:nth-child(1){height:46vh}
.col.a figure:nth-child(2){height:34vh}
.col.a figure:nth-child(3){height:40vh}
.col.b figure:nth-child(1){height:38vh}
.col.b figure:nth-child(2){height:52vh}
.col.b figure:nth-child(3){height:32vh}
.col.c figure:nth-child(1){height:42vh}
.col.c figure:nth-child(2){height:36vh}
.col.c figure:nth-child(3){height:44vh}
.cargado .col figure{opacity:1;transform:none;
  transition:opacity .9s cubic-bezier(.22,1,.36,1),transform .9s cubic-bezier(.22,1,.36,1)}
.hero::after{content:'';position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(120% 90% at 50% 45%,rgba(0,0,0,.34),rgba(0,0,0,.76))}

.hero-centro{position:relative;z-index:3;min-height:100svh;display:grid;align-items:end;
  justify-items:center;padding:120px var(--gut) clamp(60px,11vh,120px)}
.panel{background:var(--crema);color:var(--negro);padding:clamp(34px,4.4vw,62px);
  width:min(44vw,560px);text-align:center;opacity:0;transform:translateY(22px)}
.cargado .panel{opacity:1;transform:none;transition:opacity 1s ease .95s,transform 1s ease .95s}
.panel .rotulo{color:var(--taupe)}
.panel p{margin:16px 0 26px;font-size:14.5px;color:#3A3733;max-width:34ch;margin-inline:auto}
.btn{display:inline-block;border:1px solid var(--taupe);color:var(--taupe);padding:14px 30px;
  font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;transition:.4s;opacity:.35}
.cargado .btn{opacity:1;transition:opacity .9s ease 1.5s,background .35s,color .35s}
.btn:hover{background:var(--negro);border-color:var(--negro);color:var(--blanco)}
.titular{position:absolute;left:0;right:0;top:33%;z-index:4;transform:translateY(-50%);
  text-align:center;pointer-events:none;padding:0 2vw;
  font-family:var(--serif);font-weight:300;color:var(--blanco);
  font-size:clamp(52px,9vw,140px);line-height:.92;
  text-shadow:0 2px 40px rgba(0,0,0,.55),0 1px 3px rgba(0,0,0,.4)}
.titular span{display:block;opacity:0;transform:translateY(26px)}
.cargado .titular span{opacity:1;transform:none;
  transition:opacity 1.1s cubic-bezier(.22,1,.36,1),transform 1.1s cubic-bezier(.22,1,.36,1)}
.cargado .titular span:nth-child(2){transition-delay:.12s}
.baja{position:absolute;left:50%;bottom:22px;z-index:5;transform:translateX(-50%);
  display:grid;justify-items:center;gap:8px;color:rgba(255,255,255,.62)}
.baja i{width:1px;height:40px;background:linear-gradient(rgba(255,255,255,.65),transparent)}

/* hero mobile: otra experiencia — textura + linework */
.hero-mob{display:none}

/* ---------------- secciones ---------------- */
section{position:relative}
.claro{background:var(--crema);color:var(--negro)}
.env{padding:var(--aire) var(--gut)}
.cab{display:flex;align-items:baseline;justify-content:space-between;gap:20px;flex-wrap:wrap;
  margin-bottom:clamp(28px,4vw,56px)}
.cab h2{margin:0;font-family:var(--serif);font-weight:300;font-size:clamp(30px,4.6vw,62px);
  line-height:1.02}
.cab .rotulo{opacity:.62}

/* manifesto */
.manifiesto p{font-family:var(--serif);font-size:clamp(27px,4.1vw,58px);line-height:1.16;
  margin:0;max-width:19ch}
.manifiesto .w{color:rgba(84,79,75,.42);transition:color .25s linear}
.claro .manifiesto .w.on{color:var(--negro)}
.cifras{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:clamp(24px,4vw,60px);margin-top:clamp(50px,7vw,96px);
  border-top:1px solid rgba(84,79,75,.28);padding-top:36px}
.cifra b{display:block;font-family:var(--serif);font-weight:300;
  font-size:clamp(46px,6.6vw,92px);line-height:1;font-variant-numeric:tabular-nums}
.cifra span{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--taupe)}
.aviso{display:inline-block;margin-top:26px;border:1px solid rgba(84,79,75,.4);
  padding:6px 12px;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--taupe)}

/* categorías */
.cats{display:grid;grid-template-columns:repeat(3,1fr);gap:clamp(12px,1.6vw,26px);
  align-items:start}
.cat{position:relative;display:block;overflow:hidden;background:#121110}
.cat:nth-child(1){margin-top:0}
.cat:nth-child(2){margin-top:clamp(28px,5vw,80px)}
.cat:nth-child(3){margin-top:clamp(12px,2.4vw,38px)}
.cat .ph{aspect-ratio:3/4;width:100%;transition:transform 1.1s cubic-bezier(.22,1,.36,1)}
.cat:hover .ph{transform:scale(1.045)}
.chip{position:absolute;left:16px;top:16px;background:var(--blanco);color:var(--negro);
  padding:8px 14px;font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;font-weight:500}
.cat figcaption{padding:16px 2px 0;font-size:13px;color:rgba(232,225,215,.72)}

/* materiales */
.mats{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:clamp(14px,2vw,32px)}
.mat .ph{aspect-ratio:1/1;width:100%}
.mat h3{margin:14px 0 2px;font-family:var(--serif);font-weight:400;font-size:23px}
.mat span{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--taupe)}

/* proyectos: faixa horizontal com régua */
.regla{display:flex;align-items:flex-end;gap:9px;height:22px;margin-bottom:16px;
  opacity:.5;overflow:hidden}
.regla i{flex:0 0 auto;width:1px;background:var(--crema);height:7px}
.regla i:nth-child(5n+1){height:15px}
.pista{display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;
  padding-bottom:14px;cursor:grab;scrollbar-width:thin}
.pista.drag{cursor:grabbing;scroll-snap-type:none}
.pista figure{margin:0;flex:0 0 clamp(210px,25vw,320px);scroll-snap-align:start}
.pista .ph{aspect-ratio:2/3;width:100%;filter:grayscale(.1)}
.pista figcaption{padding-top:11px;font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
  color:rgba(232,225,215,.6)}

/* proceso em degraus */
.pasos{display:grid;gap:2px}
.paso{display:grid;grid-template-columns:auto 1fr;gap:clamp(18px,3vw,44px);align-items:baseline;
  padding:clamp(22px,3vw,40px) 0;border-top:1px solid rgba(232,225,215,.16)}
.paso:nth-child(2){padding-left:clamp(0px,4vw,90px)}
.paso:nth-child(3){padding-left:clamp(0px,8vw,180px)}
.paso:nth-child(4){padding-left:clamp(0px,12vw,270px)}
.paso b{font-family:var(--serif);font-weight:300;font-size:clamp(30px,4vw,56px);
  color:var(--taupe);line-height:1;font-variant-numeric:tabular-nums}
.paso h3{margin:0 0 5px;font-family:var(--serif);font-weight:400;font-size:clamp(20px,2.4vw,30px)}
.paso p{margin:0;font-size:14px;color:rgba(232,225,215,.66);max-width:46ch}

/* showroom */
.showroom{position:relative;min-height:78svh;display:grid;place-items:center;overflow:hidden;
  text-align:center;padding:var(--aire) var(--gut)}
.showroom .ph{position:absolute;inset:0;filter:grayscale(.2) brightness(.5)}
.showroom>div{position:relative;z-index:2;display:grid;justify-items:center;gap:20px}
.showroom h2{margin:0;font-family:var(--serif);font-weight:300;font-size:clamp(34px,5.4vw,76px);
  line-height:1.04;max-width:15ch}
.btn-claro{border-color:rgba(255,255,255,.55);color:var(--blanco);opacity:1}
.btn-claro:hover{background:var(--blanco);color:var(--negro);border-color:var(--blanco)}

/* footer */
.pie{padding:clamp(52px,7vw,96px) var(--gut) 40px;border-top:1px solid rgba(232,225,215,.16);
  display:grid;gap:44px}
.pie-top{display:grid;grid-template-columns:auto 1fr;gap:clamp(28px,6vw,90px);align-items:start}
.pie .k{width:64px;height:71px;color:var(--crema);opacity:.9}
.pie-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:32px}
.pie h4{margin:0 0 10px;font-size:10px;letter-spacing:.26em;text-transform:uppercase;
  color:var(--taupe);font-weight:500}
.pie a:hover{color:var(--blanco)}
.pie-bajo{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:11px;
  color:rgba(232,225,215,.42);border-top:1px solid rgba(232,225,215,.12);padding-top:22px}

/* revelações — só ativas quando o JS liga */
.js .rv{opacity:0;transform:translateY(26px)}
.js .rv.on{opacity:1;transform:none;
  transition:opacity .9s cubic-bezier(.22,1,.36,1),transform .9s cubic-bezier(.22,1,.36,1)}

/* ---------------- responsivo ---------------- */
@media (max-width:1024px){
  .top nav{display:none}
  .panel{width:min(72vw,540px)}
  .cats{grid-template-columns:1fr 1fr}
  .cat:nth-child(3){grid-column:1/-1;max-width:52%}
}
@media (max-width:720px){
  .burger{display:block}
  .cita{display:none}
  .hero .mosaico,.hero .hero-centro,.hero .baja,.hero .titular,.hero::after{display:none}
  .hero{min-height:100svh}
  .hero-mob{display:grid;position:relative;min-height:100svh;place-items:center;
    text-align:center;padding:110px 24px 70px;overflow:hidden}
  .hero-mob>.ph{position:absolute;inset:0;z-index:0;
    filter:grayscale(.35) brightness(.42) contrast(1.05)}
  /* ordem explícita: textura 0 · desenho 1 · conteúdo 3. Sem isto a div de
     textura (que tem filter) cobre o desenho técnico. */
  .hero-mob .trazo{position:absolute;inset:0;z-index:1;width:100%;height:100%;opacity:.22;
    stroke:#fff;fill:none;stroke-width:1;
    filter:drop-shadow(0 0 7px rgba(255,255,255,.3))}
  .hero-mob::after{content:'';position:absolute;inset:0;
    background:radial-gradient(86% 64% at 50% 42%,rgba(0,0,0,.12),rgba(0,0,0,.8))}
  .hero-mob>div{position:relative;z-index:3;display:grid;justify-items:center;gap:18px}
  .sello{width:74px;height:74px;border:1px solid rgba(255,255,255,.42);border-radius:50%;
    display:grid;place-items:center;color:var(--blanco)}
  .sello .k{width:26px;height:29px}
  .hero-mob h1{margin:0;font-family:var(--serif);font-weight:300;text-transform:uppercase;
    font-size:clamp(38px,12.5vw,62px);line-height:1.02;letter-spacing:.01em;
    background:linear-gradient(160deg,#fff 8%,var(--crema) 46%,var(--taupe) 96%);
    -webkit-background-clip:text;background-clip:text;color:transparent}
  .firma{font-family:var(--serif);font-style:italic;font-size:18px;color:rgba(232,225,215,.8)}
  .pill{border:1px solid rgba(255,255,255,.6);border-radius:100px;padding:15px 32px;
    background:rgba(0,0,0,.32);color:#fff;font-size:10.5px;letter-spacing:.22em;
    text-transform:uppercase;backdrop-filter:blur(3px)}
  .cats{grid-template-columns:none;display:flex;overflow-x:auto;scroll-snap-type:x mandatory;
    gap:14px;margin-inline:calc(var(--gut)*-1);padding-inline:var(--gut)}
  .cat{flex:0 0 84%;scroll-snap-align:center;margin-top:0!important;max-width:none!important}
  .paso{grid-template-columns:1fr;gap:6px;padding-left:0!important}
  .pie-top{grid-template-columns:1fr}
}

@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
  .js .rv{opacity:1;transform:none}
  .col figure,.panel,.titular span,.btn{opacity:1!important;transform:none!important}
}
"""

BODY = """
<header class="top">
  <a class="logo" href="#inicio">
    __KMARK__
    <span><b>KASTELLER</b><i>Revestimientos</i></span>
  </a>
  <nav>
    <a href="#materiales">Materiales</a>
    <a href="#proyectos">Proyectos</a>
    <a href="#proceso">Proceso</a>
    <a href="#showroom">Showroom</a>
  </nav>
  <a class="cita pin" href="#showroom">Agendar visita</a>
  <button class="burger" id="burger" type="button" aria-expanded="false">Menú</button>
</header>

<div class="overlay" id="overlay">
  <a href="#materiales">Materiales</a>
  <a href="#proyectos">Proyectos</a>
  <a href="#proceso">Proceso</a>
  <a href="#showroom">Showroom</a>
  __KMARK__
</div>

<main id="inicio">
  <!-- ---------- hero desktop: mosaico ---------- -->
  <section class="hero">
    <div class="mosaico" aria-hidden="true">
      <div class="col a">
        <figure><div class="ph i-marmol-blanco"></div></figure>
        <figure><div class="ph i-travertino"></div></figure>
        <figure><div class="ph i-piedra-gris"></div></figure>
      </div>
      <div class="col b">
        <figure><div class="ph i-ks-hero"></div></figure>
        <figure><div class="ph i-marmol-negro"></div></figure>
        <figure><div class="ph i-porcelanato"></div></figure>
      </div>
      <div class="col c">
        <figure><div class="ph i-madera"></div></figure>
        <figure><div class="ph i-marmol-blanco"></div></figure>
        <figure><div class="ph i-travertino"></div></figure>
      </div>
    </div>

    <h1 class="titular"><span>Superficies que</span><span>definen espacios</span></h1>

    <div class="hero-centro">
      <div class="panel">
        <span class="rotulo">Revestimientos de alto padrón</span>
        <p>Porcelanatos, mármoles y piedras naturales seleccionados pieza por pieza.
        Del showroom a la obra, con especificación técnica.</p>
        <a class="btn" href="#materiales">Ver materiales</a>
      </div>
    </div>

    <div class="baja" aria-hidden="true"><i></i><span class="rotulo">Bajar</span></div>

    <!-- hero mobile: textura + desenho técnico -->
    <div class="hero-mob">
      <div class="ph i-marmol-negro" role="img" aria-label="Macrotextura de piedra natural"></div>
      <svg class="trazo" viewBox="0 0 390 780" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <rect x="34" y="150" width="150" height="210"/><rect x="34" y="150" width="150" height="96"/>
        <rect x="196" y="150" width="160" height="330"/><rect x="196" y="366" width="160" height="114"/>
        <rect x="34" y="374" width="150" height="150"/>
        <path d="M34 536h322M34 560h150M196 560h160"/>
        <path d="M60 150v-40M60 130h124M184 150v-40"/>
        <circle cx="266" cy="270" r="46"/><circle cx="266" cy="270" r="26"/>
        <path d="M34 596h322v96H34z"/><path d="M34 644h322"/>
      </svg>
      <div>
        <span class="sello">__KMARK__</span>
        <h1>Superficies que definen espacios</h1>
        <span class="firma">Ciudad del Este</span>
        <a class="pill" href="#showroom">Agendar visita</a>
      </div>
    </div>
  </section>

  <!-- ---------- manifiesto ---------- -->
  <section class="claro env">
    <div class="manifiesto">
      <p id="manif">La piedra ya tiene el diseño adentro. Nuestro trabajo es elegir la pieza correcta y ponerla donde importa.</p>
    </div>
    <div class="cifras">
      <div class="cifra"><b data-n="500" data-suf="+">0</b><span>Proyectos entregados</span></div>
      <div class="cifra"><b data-n="80" data-suf="+">0</b><span>Marcas exclusivas</span></div>
      <div class="cifra"><b data-n="15" data-suf="">0</b><span>Años de showroom</span></div>
    </div>
    <span class="aviso">Cifras de ejemplo — a confirmar con Kasteller</span>
  </section>

  <!-- ---------- categorías ---------- -->
  <section class="env rv" id="categorias">
    <div class="cab">
      <h2>Tres familias,<br>un mismo criterio</h2>
      <span class="rotulo">Categorías</span>
    </div>
    <div class="cats">
      <a class="cat" href="#materiales">
        <span class="chip">Porcelanatos</span>
        <div class="ph i-porcelanato" role="img" aria-label="Porcelanato de gran formato"></div>
        <figcaption>Gran formato rectificado, hasta 320 × 160 cm.</figcaption>
      </a>
      <a class="cat" href="#materiales">
        <span class="chip">Piedras naturales</span>
        <div class="ph i-marmol-blanco" role="img" aria-label="Mármol natural"></div>
        <figcaption>Mármol, granito y cuarcita en placa entera.</figcaption>
      </a>
      <a class="cat" href="#materiales">
        <span class="chip">Revestimientos especiales</span>
        <div class="ph i-piedra-gris" role="img" aria-label="Revestimiento especial de piedra"></div>
        <figcaption>Muros, fachadas ventiladas y texturas a medida.</figcaption>
      </a>
    </div>
  </section>

  <!-- ---------- materiales ---------- -->
  <section class="claro env rv" id="materiales">
    <div class="cab">
      <h2>Materiales</h2>
      <span class="rotulo">Origen y acabado</span>
    </div>
    <div class="mats">
      <figure class="mat"><div class="ph i-marmol-blanco" role="img" aria-label="Mármol Calacatta"></div>
        <h3>Calacatta</h3><span>Mármol · Italia</span></figure>
      <figure class="mat"><div class="ph i-marmol-negro" role="img" aria-label="Mármol Nero Marquina"></div>
        <h3>Nero Marquina</h3><span>Mármol · España</span></figure>
      <figure class="mat"><div class="ph i-travertino" role="img" aria-label="Travertino romano"></div>
        <h3>Travertino</h3><span>Piedra natural · Turquía</span></figure>
      <figure class="mat"><div class="ph i-porcelanato" role="img" aria-label="Porcelanato gran formato"></div>
        <h3>Gran formato</h3><span>Porcelanato · Brasil</span></figure>
    </div>
  </section>

  <!-- ---------- proyectos ---------- -->
  <section class="env rv" id="proyectos">
    <div class="cab">
      <h2>Proyectos que<br>hablan por nosotros</h2>
      <span class="rotulo">Arrastrá para ver</span>
    </div>
    <div class="regla" id="regla" aria-hidden="true"></div>
    <div class="pista" id="pista">
      <figure><div class="ph i-ks-hero" role="img" aria-label="Escalera en mármol"></div><figcaption>Residencia · Escalera en mármol</figcaption></figure>
      <figure><div class="ph i-marmol-negro" role="img" aria-label="Muro en piedra oscura"></div><figcaption>Corporativo · Muro Nero</figcaption></figure>
      <figure><div class="ph i-travertino" role="img" aria-label="Fachada en travertino"></div><figcaption>Comercial · Fachada travertino</figcaption></figure>
      <figure><div class="ph i-marmol-blanco" role="img" aria-label="Baño en Calacatta"></div><figcaption>Residencia · Baño Calacatta</figcaption></figure>
      <figure><div class="ph i-piedra-gris" role="img" aria-label="Piso de gran formato"></div><figcaption>Showroom · Piso gran formato</figcaption></figure>
    </div>
  </section>

  <!-- ---------- proceso ---------- -->
  <section class="env rv" id="proceso">
    <div class="cab">
      <h2>Cómo trabajamos</h2>
      <span class="rotulo">Proceso</span>
    </div>
    <div class="pasos">
      <div class="paso"><b>01</b><div><h3>Visita al showroom</h3>
        <p>Ver la pieza en tamaño real, con la luz que va a tener en obra.</p></div></div>
      <div class="paso"><b>02</b><div><h3>Curaduría de materiales</h3>
        <p>Seleccionamos opciones según el proyecto, el uso y el presupuesto.</p></div></div>
      <div class="paso"><b>03</b><div><h3>Especificación técnica</h3>
        <p>Formato, espesor, junta y paginación definidos antes de comprar.</p></div></div>
      <div class="paso"><b>04</b><div><h3>Entrega y acompañamiento</h3>
        <p>Logística a obra y seguimiento durante la colocación.</p></div></div>
    </div>
  </section>

  <!-- ---------- showroom ---------- -->
  <section class="showroom rv" id="showroom">
    <div class="ph i-ks-hero" role="img" aria-label="Showroom Kasteller"></div>
    <div>
      <span class="rotulo">Showroom</span>
      <h2>Vení a ver el material antes de decidir</h2>
      <a class="btn btn-claro" href="https://wa.me/595985869600">Agendar visita por WhatsApp</a>
    </div>
  </section>
</main>

<footer class="pie">
  <div class="pie-top">
    __KMARK__
    <div class="pie-cols">
      <div><h4>Contacto</h4>
        <p><a href="https://wa.me/595985869600">+595 985 869 600</a></p></div>
      <div><h4>Redes</h4>
        <p><a href="https://www.instagram.com/kastellerrevestimientos">Instagram</a><br>
        <a href="https://www.facebook.com/profile.php?id=100050328950600">Facebook</a></p></div>
      <div><h4>Showroom</h4>
        <p>Ciudad del Este · Paraguay<br><span style="opacity:.55">Dirección a confirmar</span></p></div>
      <div><h4>Horario</h4>
        <p><span style="opacity:.55">A confirmar</span></p></div>
    </div>
  </div>
  <div class="pie-bajo">
    <span>Kasteller Revestimientos</span>
    <span>Vista previa de dirección visual · fotos y textos provisorios</span>
  </div>
</footer>

<script>
(function () {
  var root = document.documentElement;
  var lento = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!lento) root.classList.add('js');

  /* entrada escalonada do mosaico */
  var figs = document.querySelectorAll('.col figure');
  figs.forEach(function (f, i) { f.style.transitionDelay = (i * 0.1) + 's'; });
  requestAnimationFrame(function () { root.classList.add('cargado'); });

  /* menu mobile */
  var burger = document.getElementById('burger'), ov = document.getElementById('overlay');
  if (burger) {
    burger.addEventListener('click', function () {
      var on = ov.classList.toggle('on');
      burger.textContent = on ? 'Cerrar' : 'Menú';
      burger.setAttribute('aria-expanded', on);
      document.body.style.overflow = on ? 'hidden' : '';
      ov.querySelectorAll('a').forEach(function (a, i) {
        a.style.transitionDelay = on ? (0.06 * i + 0.1) + 's' : '0s';
      });
    });
    ov.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () { burger.click(); });
    });
  }

  /* régua da faixa de projetos */
  var regla = document.getElementById('regla');
  if (regla) { for (var i = 0; i < 90; i++) regla.appendChild(document.createElement('i')); }

  /* arrastar a faixa no desktop */
  var pista = document.getElementById('pista');
  if (pista) {
    var abajo = false, x0 = 0, s0 = 0;
    pista.addEventListener('pointerdown', function (e) {
      abajo = true; x0 = e.clientX; s0 = pista.scrollLeft; pista.classList.add('drag');
    });
    addEventListener('pointerup', function () { abajo = false; pista.classList.remove('drag'); });
    pista.addEventListener('pointermove', function (e) {
      if (!abajo) return; e.preventDefault(); pista.scrollLeft = s0 - (e.clientX - x0);
    });
  }

  if (lento) return;

  /* manifesto: palavra por palavra conforme o scroll */
  var manif = document.getElementById('manif'), palabras = [];
  if (manif) {
    manif.innerHTML = manif.textContent.trim().split(/\\s+/)
      .map(function (w) { return '<span class="w">' + w + '</span>'; }).join(' ');
    palabras = manif.querySelectorAll('.w');
  }

  /* parallax por coluna + scrub do manifesto, num único rAF */
  var cols = document.querySelectorAll('.col'), vel = [0.14, 0.05, 0.20], tick = false;
  function pintar() {
    tick = false;
    var y = scrollY;
    if (y < innerHeight * 1.2) {
      cols.forEach(function (c, i) { c.style.transform = 'translate3d(0,' + (-y * vel[i]) + 'px,0)'; });
    }
    if (palabras.length) {
      var r = manif.getBoundingClientRect();
      var p = (innerHeight * 0.82 - r.top) / (r.height + innerHeight * 0.34);
      p = Math.max(0, Math.min(1, p));
      var n = Math.round(p * palabras.length);
      palabras.forEach(function (w, i) { w.classList.toggle('on', i < n); });
    }
  }
  addEventListener('scroll', function () {
    if (!tick) { tick = true; requestAnimationFrame(pintar); }
  }, { passive: true });
  pintar();

  /* header sólido depois do hero */
  var top = document.querySelector('.top');
  function fijar() { top.classList.toggle('solido', scrollY > innerHeight * 0.72); }
  addEventListener('scroll', fijar, { passive: true }); fijar();

  /* revelações */
  var obs = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('on'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.rv').forEach(function (el) { obs.observe(el); });

  /* contadores */
  var oc = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      oc.unobserve(e.target);
      var el = e.target, fin = +el.dataset.n, suf = el.dataset.suf || '', t0 = 0;
      function paso(t) {
        if (!t0) t0 = t;
        var k = Math.min(1, (t - t0) / 1400);
        el.textContent = Math.round(fin * (1 - Math.pow(1 - k, 3))) + (k === 1 ? suf : '');
        if (k < 1) requestAnimationFrame(paso);
      }
      requestAnimationFrame(paso);
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('.cifra b').forEach(function (el) { oc.observe(el); });
})();
</script>
"""


def montar():
    css = CSS.replace('__FONTS__', FONTS) + '\n' + VARS
    body = BODY.replace('__KMARK__', KMARK)
    for k, v in IMG.items():
        body = body.replace(f'__IMG_{k}__', v)
    faltantes = [t for t in ('__IMG_', '__KMARK__', '__FONTS__') if t in body or t in css]
    if faltantes:
        raise SystemExit(f'token não substituído: {faltantes}')
    return (f'<title>Kasteller Revestimientos — superficies que definen espacios</title>\n'
            f'<style>{css}</style>\n{body}')


out = HERE / 'kasteller-site.html'
out.write_text(montar(), encoding='utf-8')
print(f'{out} — {out.stat().st_size/1024:.0f} KB')
