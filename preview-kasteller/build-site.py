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
# clipe do payoff: Ken Burns gerado localmente (Pexels bloqueado aqui);
# trocar pelos vídeos reais do showroom quando chegarem
VIDEO = data_uri('kasteller-loop.webm', 'video/webm')

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

/* ---------------- hero: mosaico 5x3 preso, zoom controlado pelo scroll ----------------
   O "pin" é sticky nativo: a seção mede 350vh e o palco gruda no topo. O scroll
   dentro dessa altura vira progresso 0..1 e comanda o zoom. Sai mais previsível
   que capturar wheel — funciona igual com trackpad, roda e toque. */
.hero{position:relative;height:350vh;background:var(--negro)}
.hero-stage{position:sticky;top:0;height:100svh;overflow:hidden;background:var(--negro)}
.rejilla{position:absolute;top:50%;left:50%;width:160vmax;height:110vmax;
  display:grid;grid-template-columns:repeat(5,1fr);grid-template-rows:repeat(3,1fr);
  gap:1.6vmax;transform:translate(-50%,-50%) scale(.62);will-change:transform}
.celda{position:relative;overflow:hidden;background:#121110;opacity:0;transform:translateY(40px)}
.rejilla{--vec:.92}
.celda .ph{position:absolute;inset:0;filter:brightness(var(--vec))}
.celda.centro{grid-column:3;grid-row:2;z-index:2}
.celda.centro .ph{filter:brightness(.78)}
.celda.centro video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  filter:brightness(.78)}
.cargado .celda{opacity:1;transform:none;
  transition:opacity 1.1s cubic-bezier(.22,1,.36,1),transform 1.1s cubic-bezier(.22,1,.36,1)}

.velo{position:absolute;inset:0;z-index:5;background:var(--negro);opacity:0;pointer-events:none}

.hero-contenido{position:absolute;inset:0;z-index:10;display:flex;flex-direction:column;
  align-items:center;justify-content:center;text-align:center;pointer-events:none;
  color:var(--blanco);padding:0 6vw;will-change:transform,opacity}
.hero-sello{opacity:0;transform:translateY(20px)}
.cargado .hero-sello{opacity:1;transform:none;transition:opacity .8s ease .55s,transform .8s ease .55s}
.hero-sello .k{width:46px;height:51px;color:var(--crema)}
.titular{margin:26px 0 0;font-family:var(--serif);font-weight:400;
  font-size:clamp(46px,8.6vw,132px);line-height:1.02;letter-spacing:.01em;
  text-shadow:0 2px 40px rgba(0,0,0,.45)}
.titular .linea{display:block;overflow:hidden}
.titular .linea>span{display:inline-block;transform:translateY(110%)}
.cargado .titular .linea>span{transform:none;
  transition:transform 1.1s cubic-bezier(.16,1,.3,1) .8s}
.cargado .titular .linea:nth-child(2)>span{transition-delay:.92s}
.hero-sub{margin-top:24px;font-size:clamp(12px,1.4vw,15px);letter-spacing:.16em;
  text-transform:uppercase;opacity:0;color:rgba(255,255,255,.86)}
.cargado .hero-sub{opacity:1;transition:opacity .8s ease 1.5s}
.hero-cta{pointer-events:auto;margin-top:40px;opacity:0;display:inline-flex;align-items:center;
  gap:10px;background:rgba(232,225,215,.16);border:1px solid rgba(255,255,255,.55);
  backdrop-filter:blur(6px);padding:17px 38px;border-radius:999px;font-size:11px;
  letter-spacing:.18em;text-transform:uppercase;transition:background .35s,color .35s}
.cargado .hero-cta{opacity:1;transition:opacity .8s ease 1.75s,background .35s,color .35s}
.hero-cta:hover{background:var(--crema);color:var(--negro)}
.hero-hint{position:absolute;bottom:28px;left:50%;transform:translateX(-50%);z-index:11;
  display:grid;justify-items:center;gap:10px;opacity:0;
  font-size:10px;letter-spacing:.3em;text-transform:uppercase;color:rgba(255,255,255,.7)}
.cargado .hero-hint{opacity:1;transition:opacity .6s ease 2s}
.hero-hint.scrub{transition:none}
.hero-hint::after{content:'';width:1px;height:44px;
  background:linear-gradient(rgba(255,255,255,.85),transparent);
  animation:gotear 1.9s ease-in-out infinite}
@keyframes gotear{
  0%{transform:scaleY(0);transform-origin:top}
  45%{transform:scaleY(1);transform-origin:top}
  55%{transform:scaleY(1);transform-origin:bottom}
  100%{transform:scaleY(0);transform-origin:bottom}}

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
  /* mobile não tem o zoom: some o palco e a altura de scroll extra */
  .hero{height:auto;min-height:100svh}
  .hero-stage,.hero-hint{display:none}
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
  /* sem zoom preso: o mosaico fica estático e a página rola normalmente */
  .hero{height:100svh}
  .hero-stage{position:relative}
  .celda{opacity:1!important;transform:none!important}
  .titular .linea>span{transform:none!important}
  .hero-sello,.hero-sub,.hero-cta{opacity:1!important;transform:none!important}
  .js .rv{opacity:1;transform:none}
  .panel,.btn{opacity:1!important;transform:none!important}
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
  <section class="hero" id="hero">
    <div class="hero-stage">
      <div class="rejilla" id="rejilla" aria-hidden="true"></div>
      <div class="velo" id="velo"></div>
      <div class="hero-contenido" id="hero-contenido">
        <div class="hero-sello">__KMARK__</div>
        <h1 class="titular">
          <span class="linea"><span>Superficies que</span></span>
          <span class="linea"><span>definen espacios</span></span>
        </h1>
        <p class="hero-sub">Revestimientos de alto padrón · Ciudad del Este</p>
        <a class="hero-cta" href="#manifiesto">Conocer el showroom</a>
      </div>
      <div class="hero-hint" aria-hidden="true">Scroll</div>
    </div>

    <!-- hero mobile: textura + desenho técnico (substitui o mosaico em telas pequenas) -->
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

  /* mosaico 5x3: a célula central (3,2) é o destino do zoom */
  var rejilla = document.getElementById('rejilla');
  var TEX = ['i-marmol-blanco','i-travertino','i-piedra-gris','i-porcelanato',
             'i-marmol-negro','i-madera'];
  if (rejilla) {
    var t = 0;
    for (var r = 1; r <= 3; r++) {
      for (var c = 1; c <= 5; c++) {
        var centro = (r === 2 && c === 3);
        var cel = document.createElement('div');
        cel.className = 'celda' + (centro ? ' centro' : '');
        cel.style.gridColumn = c; cel.style.gridRow = r;
        if (centro) {
          /* payoff: o destino do zoom é um vídeo (muted+playsinline = autoplay ok) */
          var vid = document.createElement('video');
          vid.muted = true; vid.loop = true; vid.autoplay = true;
          vid.playsInline = true; vid.setAttribute('playsinline', '');
          vid.poster = document.getElementById('inicio').dataset.poster;
          vid.src = document.getElementById('inicio').dataset.video;
          vid.play && vid.play().catch(function () {});
          cel.appendChild(vid);
        } else {
          var ph = document.createElement('div');
          ph.className = 'ph ' + TEX[t++ % TEX.length];
          cel.appendChild(ph);
        }
        rejilla.appendChild(cel);
      }
    }
    /* stagger aleatório, como no demo (from:"random") */
    var celdas = [].slice.call(rejilla.children);
    var orden = celdas.map(function (_, i) { return i; });
    for (var k = orden.length - 1; k > 0; k--) {
      var j2 = (k * 9301 + 49297) % (k + 1);      // embaralho determinístico
      var tmp = orden[k]; orden[k] = orden[j2]; orden[j2] = tmp;
    }
    orden.forEach(function (idx, pos) { celdas[idx].style.transitionDelay = (pos * 0.07) + 's'; });
  }
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

  if (lento) {
    var v0 = document.querySelector('.celda.centro video');
    if (v0) { v0.autoplay = false; v0.pause(); }
    return;
  }

  /* manifesto: palavra por palavra conforme o scroll */
  var manif = document.getElementById('manif'), palabras = [];
  if (manif) {
    manif.innerHTML = manif.textContent.trim().split(/\\s+/)
      .map(function (w) { return '<span class="w">' + w + '</span>'; }).join(' ');
    palabras = manif.querySelectorAll('.w');
  }

  /* ---- HERO: o scroll dentro da seção vira progresso 0..1 e comanda o zoom ----
     A seção mede 350vh e o palco é sticky; então "prender" a tela é o próprio
     sticky. Nada de capturar wheel: assim trackpad, roda e toque se comportam
     igual, e o usuário pode voltar rolando para cima. */
  var hero = document.getElementById('hero'),
      rej = document.getElementById('rejilla'),
      velo = document.getElementById('velo'),
      contenido = document.getElementById('hero-contenido'),
      cabecera = document.querySelector('.top'),
      pista_hint = document.querySelector('.hero-hint'),
      video_c = document.querySelector('.celda.centro video'),
      ESC0 = 0.62, ESC1 = 3.4, tick = false;

  function entre(v, a, b) { return Math.max(0, Math.min(1, (v - a) / (b - a))); }

  function zoom(p) {
    if (!rej) return;
    /* o zoom completa em ~72% do trajeto; o resto é o payoff: vídeo em tela
       cheia, limpo, rodando — o véu só entra nos últimos 15% */
    var q = entre(p, 0, 0.72);
    rej.style.transform = 'translate(-50%,-50%) scale(' + (ESC0 + (ESC1 - ESC0) * q) + ')';
    /* o conteúdo recua e some, dando lugar à imagem */
    var f = entre(p, 0.15, 0.55);
    contenido.style.transform = 'scale(' + (1 - 0.08 * f) + ')';
    contenido.style.opacity = 1 - f;
    /* véu SÓ no finalzinho (últimos ~15%) — o payoff do vídeo fica limpo */
    velo.style.opacity = entre(p, 0.85, 1) * 0.4;
    /* o vídeo central sai de .78 para brilho pleno enquanto vira tela cheia */
    if (video_c) video_c.style.filter = 'brightness(' + (0.78 + 0.22 * entre(p, 0.3, 0.65)) + ')';
    /* vizinhas escurecem; a central mantém o brilho */
    rej.style.setProperty('--vec', 0.92 - 0.37 * p);
    cabecera.style.opacity = 1 - entre(p, 0.5, 0.85);
    if (pista_hint) pista_hint.style.opacity = 1 - entre(p, 0.05, 0.3);
  }

  function pintar() {
    tick = false;
    if (hero && rej && getComputedStyle(rej).display !== 'none') {
      if (pista_hint) pista_hint.classList.add('scrub');
      var r = hero.getBoundingClientRect();
      zoom(entre(-r.top, 0, hero.offsetHeight - innerHeight));
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
  var top = cabecera;
  function fijar() { top.classList.toggle('solido', scrollY > hero.offsetHeight * 0.92); }
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
    body = (f'<div style="display:none" id="datos"></div>' + body) if False else body
    faltantes = [t for t in ('__IMG_', '__KMARK__', '__FONTS__') if t in body or t in css]
    if faltantes:
        raise SystemExit(f'token não substituído: {faltantes}')
    return (f'<title>Kasteller Revestimientos — superficies que definen espacios</title>\n'
            f'<style>{css}</style>\n'
            f'<script>document.addEventListener("DOMContentLoaded",function(){{}});</script>\n'
            + body.replace('<main id="inicio">',
                           f'<main id="inicio" data-video="{VIDEO}" data-poster="{IMG["ks-hero"]}">'))


out = HERE / 'kasteller-site.html'
out.write_text(montar(), encoding='utf-8')
print(f'{out} — {out.stat().st_size/1024:.0f} KB')
