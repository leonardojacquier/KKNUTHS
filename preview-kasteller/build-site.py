#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o site one-page da KASTELLER REVESTIMIENTOS como HTML autocontido.

Estrutura, copy e movimentos espelham o arquivo de referência do cliente
(kastellersite_1.html): hero pin+zoom com payoff em vídeo, reveals palavra por
palavra, galeria de projetos PRESA com scroll horizontal, processo em degraus,
parallax no showroom e menu overlay com clip-path.

Diferenças deliberadas em relação à referência:
- GSAP/Lenis/Unsplash/Pexels estão bloqueados neste ambiente → animações em
  vanilla (sticky + progresso de scroll, o mesmo princípio do scrub) e assets
  locais em base64 (fontes subsetadas, texturas geradas, vídeo Ken Burns).
- O monograma K é o SVG traçado do logo real (chevron + duas cunhas), não a
  aproximação de dois polígonos da referência.
- Contatos reais da Kasteller; cifras marcadas "a confirmar".

  python3 build-site.py [pasta-de-assets]  ->  kasteller-site.html
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
# clipe do payoff: Ken Burns gerado localmente; trocar pelos vídeos reais
VIDEO = data_uri('kasteller-loop.webm', 'video/webm')
FONTS = (SRC / 'fonts.css').read_text()

# Cada imagem entra UMA vez como variável CSS; .ph i-<nome> a reusa sem duplicar bytes.
VARS = (':root{' + ''.join(f'--i-{k}:url({v});' for k, v in IMG.items()) + '}\n'
        + '.ph{background-size:cover;background-position:center;background-repeat:no-repeat}\n'
        + '\n'.join(f'.i-{k}{{background-image:var(--i-{k})}}' for k in IMG))

# Monograma K traçado da geometria real do logo
KMARK = ('<svg class="k" viewBox="0 0 113 126" aria-hidden="true">'
         '<path d="M50 0 H93 L43 63 L93 126 H50 L0 63 Z"/>'
         '<path d="M0 0 H37 L0 43 Z"/>'
         '<path d="M0 83 L37 126 H0 Z"/></svg>')

WA = 'https://wa.me/595985869600'

CSS = """
__FONTS__

:root{--negro:#000;--blanco:#fff;--crema:#E8E1D7;--taupe:#544F4B}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--crema);color:var(--negro);
  font-family:'Inter',system-ui,sans-serif;font-weight:300;overflow-x:hidden;
  -webkit-font-smoothing:antialiased}
img,video{display:block;max-width:100%}
a{color:inherit;text-decoration:none}
:focus-visible{outline:2px solid currentColor;outline-offset:4px}
.k{fill:currentColor;display:block}
.serif{font-family:'Cormorant Garamond',Georgia,serif}

/* ================= HEADER ================= */
header.top{position:fixed;inset:0 0 auto 0;z-index:90;display:flex;align-items:center;
  justify-content:space-between;padding:24px clamp(20px,4vw,48px);
  background:linear-gradient(to bottom,rgba(0,0,0,.55),transparent)}
.logo{display:flex;align-items:center;gap:10px;color:var(--blanco);z-index:95}
.logo .k{height:24px;width:22px}
.logo b{font-weight:600;letter-spacing:.32em;font-size:14px;display:block}
.logo small{display:block;font-weight:300;letter-spacing:.48em;font-size:7.5px;margin-top:3px}
nav.desktop{display:flex;gap:34px}
nav.desktop a{color:rgba(255,255,255,.85);font-size:13px;letter-spacing:.08em}
nav.desktop a:hover{color:var(--blanco)}
.cta-header{display:flex;align-items:center;gap:8px;border:1px solid rgba(255,255,255,.5);
  color:var(--blanco);padding:12px 22px;font-size:11px;letter-spacing:.14em;
  text-transform:uppercase;transition:.3s}
.cta-header i{width:7px;height:7px;background:var(--cream,#E8E1D7);background:var(--crema)}
.cta-header:hover{background:var(--blanco);color:var(--negro)}
.cta-header:hover i{background:var(--taupe)}
.burger{display:none;background:none;border:0;color:var(--blanco);z-index:95;cursor:pointer;
  font-size:11px;letter-spacing:.24em;text-transform:uppercase;padding:10px;font-family:inherit}
.overlay{position:fixed;inset:0;z-index:92;background:var(--negro);display:flex;
  flex-direction:column;justify-content:center;padding:0 10vw;gap:6px;
  clip-path:inset(0 0 100% 0);transition:clip-path .7s cubic-bezier(.76,0,.24,1)}
.overlay.open{clip-path:inset(0 0 0% 0)}
.overlay a{font-family:'Cormorant Garamond',serif;color:var(--crema);
  font-size:clamp(38px,9vw,64px);line-height:1.25;opacity:0;transform:translateY(24px);
  transition:opacity .5s,transform .5s}
.overlay.open a{opacity:1;transform:none}
.overlay .k{position:absolute;right:-6vw;bottom:-8vh;opacity:.07;height:60vh;width:auto;
  color:var(--crema)}
@media(max-width:860px){nav.desktop,.cta-header{display:none}.burger{display:block}}

/* ================= HERO: PIN + SCROLL-ZOOM ================= */
/* pin nativo: a seção mede 350vh, o palco é sticky, o scroll vira progresso 0..1 */
.hero{position:relative;height:350vh;background:var(--negro)}
.hero__stage{position:sticky;top:0;height:100svh;overflow:hidden;background:var(--negro)}
.grid{position:absolute;top:50%;left:50%;width:165vmax;height:112vmax;
  transform:translate(-50%,-50%) scale(.6);display:grid;
  grid-template-columns:repeat(5,1fr);grid-template-rows:repeat(3,1fr);
  gap:1.5vmax;will-change:transform;--vec:.9}
.cell{overflow:hidden;position:relative;opacity:0;transform:translateY(40px)}
.cell .ph{position:absolute;inset:0;filter:brightness(var(--vec))}
.cell--center{grid-column:3;grid-row:2;z-index:2}
.cell--center video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  filter:brightness(.82)}
.cargado .cell{opacity:1;transform:none;
  transition:opacity 1.1s cubic-bezier(.22,1,.36,1),transform 1.1s cubic-bezier(.22,1,.36,1)}
.hero__veil{position:absolute;inset:0;z-index:5;background:var(--negro);opacity:0;
  pointer-events:none}
.hero__content{position:absolute;inset:0;z-index:10;display:flex;flex-direction:column;
  align-items:center;justify-content:center;text-align:center;pointer-events:none;
  color:var(--blanco);padding:0 6vw;will-change:transform,opacity}
.hero__mark{opacity:0;transform:translateY(20px)}
.cargado .hero__mark{opacity:1;transform:none;
  transition:opacity .8s ease .55s,transform .8s ease .55s}
.hero__mark .k{height:52px;width:47px;color:var(--crema)}
.hero__content h1{font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:clamp(44px,8.5vw,124px);line-height:1.02;
  text-shadow:0 2px 40px rgba(0,0,0,.5);margin:24px 0 0}
.hero__content h1 .line{display:block;overflow:hidden}
.hero__content h1 .line span{display:inline-block;transform:translateY(110%)}
.cargado .hero__content h1 .line span{transform:none;
  transition:transform 1.1s cubic-bezier(.16,1,.3,1) .8s}
.cargado .hero__content h1 .line:nth-child(2) span{transition-delay:.92s}
.hero__sub{margin-top:24px;font-weight:300;font-size:clamp(12px,1.3vw,15px);
  letter-spacing:.16em;text-transform:uppercase;opacity:0}
.cargado .hero__sub{opacity:1;transition:opacity .8s ease 1.5s}
.hero__cta{pointer-events:auto;margin-top:42px;opacity:0;display:inline-flex;
  align-items:center;gap:10px;background:rgba(232,225,215,.14);
  border:1px solid rgba(255,255,255,.55);backdrop-filter:blur(6px);color:var(--blanco);
  padding:17px 38px;border-radius:999px;font-size:11px;letter-spacing:.2em;
  text-transform:uppercase;transition:background .3s,color .3s}
.cargado .hero__cta{opacity:1;transition:opacity .8s ease 1.75s,background .3s,color .3s}
.hero__cta:hover{background:var(--crema);color:var(--negro)}
.hero__scrollhint{position:absolute;bottom:28px;left:50%;transform:translateX(-50%);
  z-index:11;color:rgba(255,255,255,.7);font-size:9px;letter-spacing:.32em;
  text-transform:uppercase;display:flex;flex-direction:column;align-items:center;
  gap:10px;opacity:0}
.cargado .hero__scrollhint{opacity:1;transition:opacity .6s ease 2s}
.hero__scrollhint.scrub{transition:none}
.hero__scrollhint::after{content:'';width:1px;height:42px;
  background:linear-gradient(to bottom,rgba(255,255,255,.8),transparent);
  animation:drip 1.8s ease-in-out infinite}
@keyframes drip{0%{transform:scaleY(0);transform-origin:top}
  45%{transform:scaleY(1);transform-origin:top}
  55%{transform:scaleY(1);transform-origin:bottom}
  100%{transform:scaleY(0);transform-origin:bottom}}

/* hero mobile imersivo (FOR LIVING): textura + desenho técnico */
.hero-mob{display:none}

/* ================= SECCIONES BASE ================= */
section{position:relative}
.pad{padding:18vh 8vw}
.eyebrow{display:flex;align-items:center;gap:10px;font-size:10px;letter-spacing:.3em;
  text-transform:uppercase;color:var(--taupe);margin-bottom:40px}
.eyebrow i{width:8px;height:8px;background:var(--taupe);flex:none}
.eyebrow.on-dark{color:rgba(232,225,215,.75)}
.eyebrow.on-dark i{background:var(--crema)}
h2.sec{font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:clamp(34px,4.6vw,64px);line-height:1.1;max-width:16ch;margin:0}

/* MANIFESTO */
.manifesto{background:var(--crema)}
.manifesto p.reveal{font-family:'Cormorant Garamond',serif;
  font-size:clamp(32px,4.8vw,70px);line-height:1.15;font-weight:500;max-width:20ch;margin:0}
.reveal .w{color:rgba(84,79,75,.2)}
.on-dark-sec .reveal .w{color:rgba(232,225,215,.22)}
.stats{display:flex;gap:7vw;margin-top:13vh;flex-wrap:wrap}
.stat b{font-family:'Cormorant Garamond',serif;font-size:clamp(46px,5.6vw,84px);
  font-weight:600;display:block;line-height:1;font-variant-numeric:tabular-nums}
.stat span{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--taupe)}
.aviso{display:inline-block;margin-top:30px;border:1px solid rgba(84,79,75,.4);
  padding:6px 12px;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--taupe)}

/* CATEGORÍAS */
.cats{background:var(--negro);color:var(--blanco)}
.cats__row{display:flex;gap:4vw;margin-top:10vh;align-items:flex-start}
.cat{position:relative;flex:1;color:var(--blanco)}
.js .cat{opacity:0;transform:translateY(60px)}
.js .cat.vis{opacity:1;transform:none;
  transition:opacity 1s cubic-bezier(.22,1,.36,1),transform 1s cubic-bezier(.22,1,.36,1)}
.cat:nth-child(2){margin-top:9vh}
.cat:nth-child(3){margin-top:-4vh}
.cat .marco{overflow:hidden;aspect-ratio:3/4;position:relative}
.cat .marco .ph{position:absolute;inset:0;transition:transform .8s cubic-bezier(.22,1,.36,1)}
.cat:hover .marco .ph{transform:scale(1.06)}
.cat .chip{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  background:var(--blanco);color:var(--negro);font-size:11px;letter-spacing:.18em;
  padding:9px 16px;text-transform:uppercase;white-space:nowrap;z-index:2}
.cat p{margin-top:18px;font-weight:300;font-size:13px;color:rgba(255,255,255,.6);
  letter-spacing:.04em}
@media(max-width:820px){
  .cats__row{overflow-x:auto;scroll-snap-type:x mandatory;gap:5vw;padding-bottom:20px;
    -webkit-overflow-scrolling:touch}
  .cat{flex:0 0 78vw;scroll-snap-align:center;margin-top:0!important}
}

/* MATERIALES — grid editorial 12 colunas */
.materiales{background:var(--crema)}
.mat-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:2vw;margin-top:9vh}
.mat{overflow:hidden;margin:0}
.js .mat{opacity:0;transform:translateY(50px)}
.js .mat.vis{opacity:1;transform:none;
  transition:opacity 1s cubic-bezier(.22,1,.36,1),transform 1s cubic-bezier(.22,1,.36,1)}
.mat .marco{overflow:hidden;position:relative;height:100%}
.mat .marco .ph{position:absolute;inset:0;transition:transform .8s cubic-bezier(.22,1,.36,1)}
.mat:hover .marco .ph{transform:scale(1.05)}
.mat span{display:block;margin-top:12px;font-size:10px;letter-spacing:.24em;
  text-transform:uppercase;color:var(--taupe)}
.mat--a{grid-column:1/6;aspect-ratio:4/5}
.mat--b{grid-column:7/13;aspect-ratio:16/10;margin-top:10vh}
.mat--c{grid-column:2/7;aspect-ratio:16/10;margin-top:6vh}
.mat--d{grid-column:8/12;aspect-ratio:3/4}
@media(max-width:820px){
  .mat--a,.mat--b,.mat--c,.mat--d{grid-column:1/13;margin-top:0;aspect-ratio:4/3}}

/* PROYECTOS — galeria horizontal PRESA (a seção mede 100vh + a distância da faixa) */
.proyectos{background:var(--negro);color:var(--blanco)}
.proy__pin{position:sticky;top:0;height:100svh;overflow:hidden;display:flex;
  flex-direction:column;justify-content:center;padding-top:9vh}
.proy__cab{padding:0 8vw 5vh}
.ruler{height:20px;position:relative;margin:0 8vw 26px;
  background:repeating-linear-gradient(to right,rgba(255,255,255,.35) 0 1px,transparent 1px 12px)}
.ruler::before{content:'';position:absolute;inset:0;
  background:repeating-linear-gradient(to right,rgba(255,255,255,.6) 0 1px,transparent 1px 96px)}
.track{display:flex;gap:2.4vw;padding:0 8vw;will-change:transform}
.proj{flex:0 0 auto;width:clamp(240px,26vw,420px);margin:0}
.proj .marco{overflow:hidden;aspect-ratio:3/4.2;position:relative}
.proj .marco .ph{position:absolute;inset:0}
.proj figcaption{display:flex;justify-content:space-between;margin-top:14px;
  font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:rgba(255,255,255,.55)}
@media(max-width:820px){
  .proyectos{height:auto!important}
  .proy__pin{position:relative;height:auto;padding:14vh 0}
  .track{overflow-x:auto;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;
    padding-bottom:16px}
  .proj{scroll-snap-align:center}
}

/* PROCESO — degraus */
.proceso{background:var(--negro);color:var(--blanco);
  background-image:radial-gradient(ellipse 80% 50% at 70% 20%,rgba(84,79,75,.35),transparent)}
.steps{margin-top:8vh}
.step{display:flex;gap:26px;max-width:520px;padding:34px 0;
  border-top:1px solid rgba(232,225,215,.14)}
.js .step{opacity:0;transform:translateY(40px)}
.js .step.vis{opacity:1;transform:none;
  transition:opacity .9s cubic-bezier(.22,1,.36,1),transform .9s cubic-bezier(.22,1,.36,1)}
.step:nth-child(2){margin-left:8vw}
.step:nth-child(3){margin-left:16vw}
.step:nth-child(4){margin-left:24vw}
.step em{font-family:'Cormorant Garamond',serif;font-style:normal;font-size:20px;
  color:var(--taupe)}
.step h3{font-size:19px;font-weight:500;margin:0 0 10px}
.step p{font-weight:300;font-size:14px;line-height:1.7;color:rgba(255,255,255,.6);margin:0}
@media(max-width:820px){.step{margin-left:0!important}}

/* SHOWROOM — foto full com parallax */
.showroom{position:relative;min-height:92svh;display:flex;align-items:center;
  justify-content:center;text-align:center;color:var(--blanco);overflow:hidden}
.showroom .bg{position:absolute;inset:0;overflow:hidden}
.showroom .bg .ph{position:absolute;inset:-12% 0 0 0;height:124%;
  filter:brightness(.45);will-change:transform}
.showroom .inner{position:relative;z-index:2;padding:16vh 8vw}
.showroom h2{font-family:'Cormorant Garamond',serif;font-weight:500;
  font-size:clamp(38px,6vw,86px);line-height:1.05;margin:0}
.showroom .script{font-family:'Cormorant Garamond',serif;font-style:italic;
  font-size:clamp(18px,2.2vw,26px);color:var(--crema);opacity:.85;margin-bottom:18px}
.pill{display:inline-flex;align-items:center;gap:10px;margin-top:40px;
  border:1px solid rgba(255,255,255,.6);border-radius:999px;color:var(--blanco);
  padding:18px 44px;font-size:11px;letter-spacing:.2em;text-transform:uppercase;
  background:rgba(0,0,0,.25);backdrop-filter:blur(4px);transition:.3s}
.pill:hover{background:var(--crema);color:var(--negro);border-color:var(--crema)}

/* FOOTER */
footer{background:var(--negro);color:rgba(255,255,255,.6);padding:12vh 8vw 6vh}
.f-top{display:flex;justify-content:space-between;gap:6vw;flex-wrap:wrap;
  align-items:flex-start}
.f-top .k{height:64px;width:57px;opacity:.9;color:var(--crema)}
.f-col b{display:block;color:var(--crema);font-size:11px;letter-spacing:.24em;
  text-transform:uppercase;margin-bottom:16px;font-weight:500}
.f-col a,.f-col span{display:block;color:rgba(255,255,255,.55);font-size:13px;
  font-weight:300;line-height:2}
.f-col a:hover{color:var(--blanco)}
.f-bottom{margin-top:10vh;padding-top:26px;border-top:1px solid rgba(232,225,215,.12);
  display:flex;justify-content:space-between;font-size:10px;letter-spacing:.18em;
  text-transform:uppercase;flex-wrap:wrap;gap:12px}

/* ================= mobile: hero imersivo ================= */
@media(max-width:720px){
  .hero{height:auto;min-height:100svh}
  .hero__stage,.hero__scrollhint{display:none}
  .hero-mob{display:grid;position:relative;min-height:100svh;place-items:center;
    text-align:center;padding:110px 24px 70px;overflow:hidden;background:var(--negro)}
  .hero-mob>.ph{position:absolute;inset:0;z-index:0;
    filter:grayscale(.35) brightness(.42) contrast(1.05)}
  /* ordem explícita: textura 0 · desenho 1 · conteúdo 3 (a textura tem filter e cobriria o SVG) */
  .hero-mob .trazo{position:absolute;inset:0;z-index:1;width:100%;height:100%;opacity:.22;
    stroke:#fff;fill:none;stroke-width:1;
    filter:drop-shadow(0 0 7px rgba(255,255,255,.3))}
  .hero-mob::after{content:'';position:absolute;inset:0;z-index:2;
    background:radial-gradient(86% 64% at 50% 42%,rgba(0,0,0,.12),rgba(0,0,0,.8))}
  .hero-mob>div{position:relative;z-index:3;display:grid;justify-items:center;gap:18px}
  .sello{width:74px;height:74px;border:1px solid rgba(255,255,255,.42);border-radius:50%;
    display:grid;place-items:center;color:var(--blanco)}
  .sello .k{width:26px;height:29px}
  .hero-mob h1{margin:0;font-family:'Cormorant Garamond',serif;font-weight:400;
    text-transform:uppercase;font-size:clamp(38px,12.5vw,62px);line-height:1.02;
    background:linear-gradient(160deg,#fff 8%,var(--crema) 46%,var(--taupe) 96%);
    -webkit-background-clip:text;background-clip:text;color:transparent}
  .firma{font-family:'Cormorant Garamond',serif;font-style:italic;font-size:18px;
    color:rgba(232,225,215,.8)}
  .pill-mob{border:1px solid rgba(255,255,255,.6);border-radius:100px;padding:15px 32px;
    background:rgba(0,0,0,.32);color:#fff;font-size:10.5px;letter-spacing:.22em;
    text-transform:uppercase;backdrop-filter:blur(3px)}
  .pad{padding:14vh 7vw}
}

@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
  .hero{height:100svh}
  .hero__stage{position:relative}
  .cell{opacity:1!important;transform:none!important}
  .hero__content h1 .line span{transform:none!important}
  .hero__mark,.hero__sub,.hero__cta,.hero__scrollhint{opacity:1!important;transform:none!important}
  .js .cat,.js .mat,.js .step{opacity:1;transform:none}
  .proyectos{height:auto!important}
  .proy__pin{position:relative;height:auto;padding:14vh 0}
  .track{overflow-x:auto}
}
"""

BODY = """
<header class="top" id="siteHeader">
  <a class="logo" href="#top" aria-label="Kasteller">
    __KMARK__
    <span><b>KASTELLER</b><small>REVESTIMIENTOS</small></span>
  </a>
  <nav class="desktop">
    <a href="#categorias">Colecciones</a>
    <a href="#materiales">Materiales</a>
    <a href="#proyectos">Proyectos</a>
    <a href="#proceso">Proceso</a>
    <a href="#showroom">Showroom</a>
  </nav>
  <a class="cta-header" href="#showroom"><i></i>Agendar visita</a>
  <button class="burger" id="burger" aria-label="Menú" aria-expanded="false">Menú</button>
</header>

<div class="overlay" id="overlay">
  <a href="#categorias">Colecciones</a>
  <a href="#materiales">Materiales</a>
  <a href="#proyectos">Proyectos</a>
  <a href="#proceso">Proceso</a>
  <a href="#showroom">Showroom</a>
  __KMARK__
</div>

<!-- ============ HERO ============ -->
<section class="hero" id="top" data-video="__VIDEO__" data-poster="__POSTER__">
  <div class="hero__stage">
    <div class="grid" id="grid" aria-hidden="true"></div>
    <div class="hero__veil" id="veil"></div>
    <div class="hero__content" id="heroContent">
      <div class="hero__mark">__KMARK__</div>
      <h1>
        <span class="line"><span>Superficies que</span></span>
        <span class="line"><span>definen espacios</span></span>
      </h1>
      <div class="hero__sub">Revestimientos de alto padrón</div>
      <a class="hero__cta" href="#manifesto">Conocer Kasteller</a>
    </div>
    <div class="hero__scrollhint" id="scrollHint" aria-hidden="true">Scroll</div>
  </div>

  <!-- hero mobile: macrotextura + desenho técnico -->
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
      <a class="pill-mob" href="#showroom">Agendar visita</a>
    </div>
  </div>
</section>

<!-- ============ MANIFESTO ============ -->
<section class="manifesto pad" id="manifesto">
  <div class="eyebrow"><i></i>Kasteller Revestimientos</div>
  <p class="reveal">Cada superficie cuenta una historia. Nosotros elegimos las que merecen ser contadas.</p>
  <div class="stats">
    <div class="stat"><b data-count="500">0</b><span>Proyectos</span></div>
    <div class="stat"><b data-count="80">0</b><span>Marcas exclusivas</span></div>
    <div class="stat"><b data-count="15">0</b><span>Años</span></div>
  </div>
  <span class="aviso">Cifras de ejemplo — a confirmar con Kasteller</span>
</section>

<!-- ============ CATEGORÍAS ============ -->
<section class="cats pad on-dark-sec" id="categorias">
  <div class="eyebrow on-dark"><i></i>Colecciones</div>
  <h2 class="sec reveal">Tres universos, una misma obsesión por el detalle.</h2>
  <div class="cats__row">
    <a class="cat" href="#materiales">
      <div class="marco"><div class="ph i-porcelanato" role="img" aria-label="Porcelanatos"></div></div>
      <span class="chip">Porcelanatos</span>
      <p>Grandes formatos, acabados técnicos y estética de piedra natural.</p>
    </a>
    <a class="cat" href="#materiales">
      <div class="marco"><div class="ph i-marmol-blanco" role="img" aria-label="Piedras naturales"></div></div>
      <span class="chip">Piedras Naturales</span>
      <p>Mármoles y cuarcitas seleccionados bloque por bloque.</p>
    </a>
    <a class="cat" href="#materiales">
      <div class="marco"><div class="ph i-piedra-gris" role="img" aria-label="Revestimientos especiales"></div></div>
      <span class="chip">Especiales</span>
      <p>Mosaicos, maderas técnicas y superficies de autor.</p>
    </a>
  </div>
</section>

<!-- ============ MATERIALES ============ -->
<section class="materiales pad" id="materiales">
  <div class="eyebrow"><i></i>Materiales</div>
  <h2 class="sec reveal">La textura no se explica. Se toca, se vive, se elige bien.</h2>
  <div class="mat-grid">
    <figure class="mat mat--a"><div class="marco"><div class="ph i-marmol-blanco" role="img" aria-label="Mármol, detalle"></div></div><span>Mármol · Detalle</span></figure>
    <figure class="mat mat--b"><div class="marco"><div class="ph i-ks-hero" role="img" aria-label="Aplicación residencial"></div></div><span>Aplicación residencial</span></figure>
    <figure class="mat mat--c"><div class="marco"><div class="ph i-porcelanato" role="img" aria-label="Gran formato"></div></div><span>Gran formato</span></figure>
    <figure class="mat mat--d"><div class="marco"><div class="ph i-travertino" role="img" aria-label="Piedra natural"></div></div><span>Piedra natural</span></figure>
  </div>
</section>

<!-- ============ PROYECTOS (galeria presa, scroll horizontal) ============ -->
<section class="proyectos on-dark-sec" id="proyectos">
  <div class="proy__pin" id="proyPin">
    <div class="proy__cab">
      <div class="eyebrow on-dark"><i></i>Proyectos</div>
      <h2 class="sec">Obras que hablan por nosotros.</h2>
    </div>
    <div class="ruler" aria-hidden="true"></div>
    <div class="track" id="track">
      <figure class="proj"><div class="marco"><div class="ph i-ks-hero" role="img" aria-label="Residencia AV"></div></div><figcaption><span>Residencia AV</span><span>2025</span></figcaption></figure>
      <figure class="proj"><div class="marco"><div class="ph i-marmol-negro" role="img" aria-label="Casa Patio"></div></div><figcaption><span>Casa Patio</span><span>2025</span></figcaption></figure>
      <figure class="proj"><div class="marco"><div class="ph i-travertino" role="img" aria-label="Loft Centro"></div></div><figcaption><span>Loft Centro</span><span>2024</span></figcaption></figure>
      <figure class="proj"><div class="marco"><div class="ph i-marmol-blanco" role="img" aria-label="Torre Jardín"></div></div><figcaption><span>Torre Jardín</span><span>2024</span></figcaption></figure>
      <figure class="proj"><div class="marco"><div class="ph i-madera" role="img" aria-label="Casa Bosque"></div></div><figcaption><span>Casa Bosque</span><span>2023</span></figcaption></figure>
      <figure class="proj"><div class="marco"><div class="ph i-piedra-gris" role="img" aria-label="Showroom K"></div></div><figcaption><span>Showroom K</span><span>2023</span></figcaption></figure>
    </div>
  </div>
</section>

<!-- ============ PROCESO ============ -->
<section class="proceso pad on-dark-sec" id="proceso">
  <div class="eyebrow on-dark"><i></i>Proceso</div>
  <h2 class="sec">Nos ocupamos de toda la complejidad.</h2>
  <div class="steps">
    <div class="step"><em>1</em><div><h3>Visita al showroom</h3><p>Conocés los materiales en persona, en piezas de gran formato, con asesoría dedicada.</p></div></div>
    <div class="step"><em>2</em><div><h3>Curaduría de materiales</h3><p>Seleccionamos junto a vos y tu arquitecto las superficies exactas para cada ambiente.</p></div></div>
    <div class="step"><em>3</em><div><h3>Especificación técnica</h3><p>Paginación, cortes, juntas y detalles resueltos antes de que llegue la primera caja.</p></div></div>
    <div class="step"><em>4</em><div><h3>Entrega y acompañamiento</h3><p>Logística coordinada con la obra y soporte hasta la última pieza colocada.</p></div></div>
  </div>
</section>

<!-- ============ SHOWROOM ============ -->
<section class="showroom" id="showroom">
  <div class="bg"><div class="ph i-ks-hero" id="showroomBg" role="img" aria-label="Showroom Kasteller"></div></div>
  <div class="inner">
    <div class="script">te esperamos</div>
    <h2>Vení a tocar<br>cada superficie.</h2>
    <a class="pill" href="__WA__" target="_blank" rel="noopener"><span>Agendar una visita</span></a>
  </div>
</section>

<!-- ============ FOOTER ============ -->
<footer>
  <div class="f-top">
    __KMARK__
    <div class="f-col"><b>Showroom</b><span>Ciudad del Este · Paraguay</span><span>Dirección y horario a confirmar</span></div>
    <div class="f-col"><b>Contacto</b><a href="__WA__">WhatsApp +595 985 869 600</a><a href="tel:+595985869600">+595 985 869 600</a></div>
    <div class="f-col"><b>Seguinos</b><a href="https://www.instagram.com/kastellerrevestimientos" target="_blank" rel="noopener">Instagram</a><a href="https://www.facebook.com/profile.php?id=100050328950600" target="_blank" rel="noopener">Facebook</a></div>
  </div>
  <div class="f-bottom"><span>© 2026 Kasteller Revestimientos</span><span>Superficies que definen espacios</span></div>
</footer>

<script>
(function () {
  var root = document.documentElement;
  var lento = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!lento) root.classList.add('js');

  function entre(v, a, b) { return Math.max(0, Math.min(1, (v - a) / (b - a))); }

  /* ---------- mosaico 5x3; a célula central é o VÍDEO ---------- */
  var hero = document.getElementById('top'),
      grid = document.getElementById('grid'),
      TEX = ['i-marmol-blanco','i-travertino','i-piedra-gris','i-porcelanato',
             'i-marmol-negro','i-madera'];
  if (grid) {
    var t = 0;
    for (var r = 1; r <= 3; r++) for (var c = 1; c <= 5; c++) {
      var centro = (r === 2 && c === 3);
      var cell = document.createElement('div');
      cell.className = 'cell' + (centro ? ' cell--center' : '');
      cell.style.gridColumn = c; cell.style.gridRow = r;
      if (centro) {
        var v = document.createElement('video');
        v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true;
        v.setAttribute('playsinline', '');
        v.poster = hero.dataset.poster;
        v.src = hero.dataset.video;
        if (lento) { v.autoplay = false; } else { v.play && v.play().catch(function () {}); }
        cell.appendChild(v);
      } else {
        var ph = document.createElement('div');
        ph.className = 'ph ' + TEX[t++ % TEX.length];
        cell.appendChild(ph);
      }
      grid.appendChild(cell);
    }
    /* stagger from:"random" (embaralho determinístico) */
    var cells = [].slice.call(grid.children);
    var orden = cells.map(function (_, i) { return i; });
    for (var k = orden.length - 1; k > 0; k--) {
      var j = (k * 9301 + 49297) % (k + 1);
      var tmp = orden[k]; orden[k] = orden[j]; orden[j] = tmp;
    }
    orden.forEach(function (idx, pos) { cells[idx].style.transitionDelay = (pos * 0.07) + 's'; });
  }
  requestAnimationFrame(function () { root.classList.add('cargado'); });

  /* ---------- menu overlay (clip-path) ---------- */
  var burger = document.getElementById('burger'), overlay = document.getElementById('overlay');
  if (burger) {
    burger.addEventListener('click', function () {
      var open = overlay.classList.toggle('open');
      burger.textContent = open ? 'Cerrar' : 'Menú';
      burger.setAttribute('aria-expanded', open);
      overlay.querySelectorAll('a').forEach(function (a, i) {
        a.style.transitionDelay = open ? (0.06 * i + 0.2) + 's' : '0s';
      });
    });
    overlay.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        overlay.classList.remove('open'); burger.textContent = 'Menú';
        burger.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------- reveal palavra por palavra (prepara os spans) ---------- */
  var reveals = [];
  document.querySelectorAll('.reveal').forEach(function (el) {
    var dark = !!el.closest('.on-dark-sec');
    el.innerHTML = el.textContent.trim().split(/\\s+/)
      .map(function (w) { return '<span class="w">' + w + '</span>'; }).join(' ');
    reveals.push({ el: el, ws: el.querySelectorAll('.w'),
                   color: dark ? '#FFFFFF' : '#000000' });
  });

  /* ---------- contadores ---------- */
  var oc = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      oc.unobserve(e.target);
      var el = e.target, fin = +el.dataset.count, t0 = 0;
      function paso(ts) {
        if (!t0) t0 = ts;
        var k = Math.min(1, (ts - t0) / 1800);
        el.textContent = Math.round(fin * (1 - Math.pow(1 - k, 3))) + '+';
        if (k < 1) requestAnimationFrame(paso);
      }
      if (lento) { el.textContent = fin + '+'; } else { requestAnimationFrame(paso); }
    });
  }, { threshold: .5 });
  document.querySelectorAll('.stat b').forEach(function (el) { oc.observe(el); });

  /* ---------- reveals genéricos (.cat .mat .step) ---------- */
  var ov = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('vis'); ov.unobserve(e.target); }
    });
  }, { threshold: .12 });
  document.querySelectorAll('.cat,.mat,.step').forEach(function (el, i) {
    el.style.transitionDelay = ((i % 3) * 0.08) + 's'; ov.observe(el);
  });

  if (lento) return;

  /* ================== motor de scroll (um rAF só) ==================
     hero: pin sticky + zoom scrub (o mesmo princípio do ScrollTrigger:
     progresso = posição de scroll, nunca eventos de wheel — trackpad,
     roda e toque se comportam igual) */
  var stage = document.querySelector('.hero__stage'),
      veil = document.getElementById('veil'),
      contenido = document.getElementById('heroContent'),
      hint = document.getElementById('scrollHint'),
      cabecera = document.getElementById('siteHeader'),
      videoC = null,
      ESC0 = 0.6, ESC1 = 3.4;

  /* proyectos: seção mede 100vh + distância; o pin interno é sticky */
  var proy = document.getElementById('proyectos'),
      proyPin = document.getElementById('proyPin'),
      track = document.getElementById('track'),
      horizontal = innerWidth > 820;

  function medirProy() {
    if (!proy || !track || !horizontal) return;
    var dist = Math.max(0, track.scrollWidth + track.offsetLeft * 2 - innerWidth);
    proy.style.height = 'calc(100svh + ' + dist + 'px)';
    proy.dataset.dist = dist;
  }
  medirProy();
  addEventListener('resize', function () { horizontal = innerWidth > 820; medirProy(); });

  var showroomBg = document.getElementById('showroomBg'),
      showroom = document.getElementById('showroom');

  var tick = false;
  function pintar() {
    tick = false;

    /* HERO */
    if (grid && getComputedStyle(grid).display !== 'none') {
      if (!videoC) videoC = document.querySelector('.cell--center video');
      var r = hero.getBoundingClientRect();
      var p = entre(-r.top, 0, hero.offsetHeight - innerHeight);
      if (hint) hint.classList.add('scrub');
      /* zoom completa em ~72%; o resto é o payoff do vídeo em tela cheia */
      var q = entre(p, 0, 0.72);
      grid.style.transform = 'translate(-50%,-50%) scale(' + (ESC0 + (ESC1 - ESC0) * q) + ')';
      grid.style.setProperty('--vec', 0.9 - 0.4 * q);
      var f = entre(p, 0.15, 0.55);
      contenido.style.transform = 'scale(' + (1 - 0.08 * f) + ')';
      contenido.style.opacity = 1 - f;
      if (videoC) videoC.style.filter = 'brightness(' + (0.82 + 0.18 * entre(p, 0.3, 0.65)) + ')';
      veil.style.opacity = entre(p, 0.85, 1) * 0.4;
      if (hint) hint.style.opacity = 1 - entre(p, 0.05, 0.3);
      /* header some no zoom e VOLTA no finalzinho (como na referência) */
      var o = 1 - entre(p, 0.5, 0.85);
      if (p > 0.95) o = entre(p, 0.95, 1);
      cabecera.style.opacity = o;
    }

    /* PROYECTOS: scroll vertical vira deslocamento horizontal da faixa */
    if (proy && horizontal && track) {
      var rp = proy.getBoundingClientRect();
      var dist = +proy.dataset.dist || 0;
      var pp = entre(-rp.top, 0, proy.offsetHeight - innerHeight);
      track.style.transform = 'translate3d(' + (-dist * pp) + 'px,0,0)';
    }

    /* SHOWROOM: parallax do fundo */
    if (showroom && showroomBg) {
      var rs = showroom.getBoundingClientRect();
      var ps = entre(innerHeight - rs.top, 0, innerHeight + rs.height);
      showroomBg.style.transform = 'translate3d(0,' + (ps * 12 - 6) + '%,0)';
    }

    /* REVEALS palavra por palavra (scrub) */
    reveals.forEach(function (rv) {
      var rr = rv.el.getBoundingClientRect();
      var pr = entre(innerHeight * 0.75 - rr.top, 0, innerHeight * 0.55);
      var n = Math.round(pr * rv.ws.length);
      rv.ws.forEach(function (w, i) { w.style.color = i < n ? rv.color : ''; });
    });
  }
  addEventListener('scroll', function () {
    if (!tick) { tick = true; requestAnimationFrame(pintar); }
  }, { passive: true });
  pintar();
})();
</script>
"""


def montar():
    css = CSS.replace('__FONTS__', FONTS) + '\n' + VARS
    body = (BODY.replace('__KMARK__', KMARK)
                .replace('__VIDEO__', VIDEO)
                .replace('__POSTER__', IMG['ks-hero'])
                .replace('__WA__', WA))
    for token in ('__IMG_', '__KMARK__', '__FONTS__', '__VIDEO__', '__POSTER__', '__WA__'):
        if token in body or token in css:
            raise SystemExit(f'token não substituído: {token}')
    return (f'<title>Kasteller Revestimientos — superficies que definen espacios</title>\n'
            f'<style>{css}</style>\n{body}')


out = HERE / 'kasteller-site.html'
out.write_text(montar(), encoding='utf-8')
print(f'{out} — {out.stat().st_size/1024:.0f} KB')
