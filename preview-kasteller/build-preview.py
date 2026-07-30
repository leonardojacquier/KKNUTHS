#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monta a prévia do site Kasteller como HTML autocontido (imagens em base64).
   Uso: python3 build-preview.py  →  kasteller-preview.html
   As imagens vêm do scratchpad da sessão; num projeto real virão de public/img/."""
import base64, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'assets'


def b64(name, mime):
    p = SRC / name
    if not p.exists():
        raise SystemExit(f'falta {p}')
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()


LOGO_W = b64('kasteller-blanco.png', 'image/png')
LOGO_B = b64('kasteller-negro.png', 'image/png')
HERO = b64('ks-hero.jpg', 'image/jpeg')

HTML = f"""<title>Kasteller Revestimientos — vista previa</title>
<style>
:root {{
  --negro:#000000; --arena:#E8E1D7; --taupe:#544F4B; --blanco:#FFFFFF;
  --fondo:var(--negro); --tinta:var(--arena); --sutil:#8E8880; --linea:rgba(232,225,215,.18);
  --panel:#0A0A0A;
  --display:'Futura','Century Gothic','Avenir Next','Questrial','Trebuchet MS',system-ui,sans-serif;
  --texto:'Avenir Next','Segoe UI',system-ui,-apple-system,'Helvetica Neue',sans-serif;
  --paso:clamp(18px,4vw,40px);
}}
@media (prefers-color-scheme: light) {{
  :root {{ --fondo:var(--arena); --tinta:#14120F; --sutil:#6B655D;
           --linea:rgba(20,18,15,.16); --panel:#DED6CA; }}
}}
:root[data-theme="light"] {{ --fondo:var(--arena); --tinta:#14120F; --sutil:#6B655D;
  --linea:rgba(20,18,15,.16); --panel:#DED6CA; }}
:root[data-theme="dark"] {{ --fondo:var(--negro); --tinta:var(--arena); --sutil:#8E8880;
  --linea:rgba(232,225,215,.18); --panel:#0A0A0A; }}

*,*::before,*::after {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--fondo); color:var(--tinta); font-family:var(--texto);
  line-height:1.65; overflow-x:hidden; -webkit-font-smoothing:antialiased; }}
img {{ max-width:100%; display:block; }}
a {{ color:inherit; }}
:focus-visible {{ outline:2px solid var(--tinta); outline-offset:3px; }}

.marca {{ font-family:var(--display); font-weight:300; letter-spacing:.34em;
  text-transform:uppercase; }}
.eyebrow {{ font-family:var(--display); font-size:11px; letter-spacing:.32em;
  text-transform:uppercase; color:var(--sutil); }}

/* ---------- cortina de apertura: se parte en chevron, la geometría de la K ---------- */
#cortina {{ position:fixed; inset:0; z-index:90; pointer-events:none; }}
#cortina .mitad {{ position:absolute; top:0; bottom:0; width:56%; background:var(--negro);
  transition:transform 1s cubic-bezier(.76,0,.24,1); }}
#cortina .izq {{ left:0;  clip-path:polygon(0 0,100% 0,calc(100% - 6vw) 50%,100% 100%,0 100%); }}
#cortina .der {{ right:0; clip-path:polygon(6vw 0,100% 0,100% 100%,6vw 100%,0 50%); }}
#cortina.abre .izq {{ transform:translateX(-102%); }}
#cortina.abre .der {{ transform:translateX(102%); }}
#cortina .centro {{ position:absolute; inset:0; display:grid; place-items:center;
  transition:opacity .5s ease; }}
#cortina.abre .centro {{ opacity:0; }}
.intro-marca {{ width:min(52vw,460px);
  clip-path:polygon(0 0,0 0,-12% 100%,-12% 100%);
  animation:revelar 1.15s cubic-bezier(.65,0,.35,1) .25s forwards; }}
@keyframes revelar {{ to {{ clip-path:polygon(0 0,118% 0,106% 100%,0 100%); }} }}
.intro-hilo {{ width:min(52vw,460px); height:1px; background:var(--linea); margin-top:22px;
  position:relative; overflow:hidden; }}
.intro-hilo::after {{ content:''; position:absolute; inset:0; background:var(--arena);
  transform:scaleX(0); transform-origin:left;
  animation:cargar 1.5s cubic-bezier(.4,0,.2,1) .5s forwards; }}
@keyframes cargar {{ to {{ transform:scaleX(1); }} }}
#saltar {{ position:fixed; right:22px; bottom:20px; z-index:95; background:none; cursor:pointer;
  border:1px solid rgba(232,225,215,.35); color:var(--arena); padding:9px 18px; font-size:10px;
  font-family:var(--display); letter-spacing:.24em; text-transform:uppercase; }}
#saltar:hover {{ border-color:var(--arena); }}

/* ---------- barra ---------- */
.barra {{ position:fixed; top:0; left:0; right:0; z-index:40; display:flex; align-items:center;
  justify-content:space-between; padding:20px var(--paso);
  opacity:0; transition:opacity .7s ease .2s; }}
.barra::before {{ content:''; position:absolute; inset:0; z-index:-1; pointer-events:none;
  background:linear-gradient(180deg,rgba(0,0,0,.55),transparent); }}
.listo .barra {{ opacity:1; }}
.barra img {{ height:26px; width:auto; }}
.barra nav {{ display:flex; gap:26px; }}
.barra nav a {{ font-family:var(--display); font-size:11px; letter-spacing:.26em;
  text-transform:uppercase; text-decoration:none; color:#fff; opacity:.8; }}
.barra nav a:hover {{ opacity:1; }}
@media (max-width:640px) {{ .barra nav {{ display:none; }} }}

/* ---------- hero ---------- */
.hero {{ position:relative; min-height:100svh; display:grid; place-items:center;
  overflow:hidden; background:var(--negro); }}
.hero-foto {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover;
  object-position:center 38%; opacity:.72; transform:scale(1.02);
  animation:respirar 18s ease-out forwards; }}
@keyframes respirar {{ to {{ transform:scale(1.11); }} }}
.hero::after {{ content:''; position:absolute; inset:0;
  background:linear-gradient(180deg,rgba(0,0,0,.55),rgba(0,0,0,.18) 42%,rgba(0,0,0,.78)); }}
.hero-contenido {{ position:relative; z-index:2; text-align:center; padding:0 var(--paso);
  opacity:0; transform:translateY(18px); transition:opacity 1s ease,transform 1s ease; }}
.listo .hero-contenido {{ opacity:1; transform:none; }}
.hero-contenido img {{ width:min(66vw,540px); margin:0 auto; }}
.hero-lema {{ margin:30px auto 0; max-width:34ch; color:#EDE7DE; font-size:clamp(14px,1.6vw,17px);
  letter-spacing:.02em; }}
.hero-baja {{ position:absolute; bottom:26px; left:50%; transform:translateX(-50%); z-index:2;
  display:grid; justify-items:center; gap:9px; }}
.hero-baja span {{ font-family:var(--display); font-size:10px; letter-spacing:.3em;
  text-transform:uppercase; color:rgba(237,231,222,.62); }}
.hero-baja i {{ width:1px; height:44px; background:linear-gradient(rgba(237,231,222,.6),transparent);
  animation:caer 2.4s ease-in-out infinite; }}
@keyframes caer {{ 0%,100% {{ opacity:.25; }} 50% {{ opacity:1; }} }}

/* ---------- gateway: la misma diagonal de la K ---------- */
.puertas {{ display:grid; grid-template-columns:1fr 1fr; min-height:82svh; position:relative;
  background:var(--fondo); }}
.puerta {{ position:relative; display:grid; align-content:center; gap:14px; padding:9vh var(--paso);
  text-decoration:none; overflow:hidden; transition:flex-grow .5s ease; }}
.puerta.ventas {{ background:var(--panel);
  clip-path:polygon(0 0,100% 0,calc(100% - 4vw) 100%,0 100%); margin-right:-2vw; z-index:2; }}
.puerta.inst .eyebrow {{ color:rgba(232,225,215,.66); }}
.puerta.inst {{ background:var(--taupe); color:var(--arena); padding-left:calc(var(--paso) + 3vw); }}
.puerta h2 {{ font-family:var(--display); font-weight:300; letter-spacing:.2em;
  text-transform:uppercase; font-size:clamp(21px,3vw,33px); margin:0; }}
.puerta p {{ margin:0; max-width:32ch; font-size:14.5px; color:inherit; opacity:.72; }}
.puerta .ir {{ font-family:var(--display); font-size:10.5px; letter-spacing:.28em;
  text-transform:uppercase; display:inline-flex; align-items:center; gap:10px; margin-top:6px; }}
.puerta .ir::after {{ content:''; width:26px; height:1px; background:currentColor;
  transition:width .4s ease; }}
.puerta:hover .ir::after {{ width:52px; }}
@media (max-width:760px) {{
  .puertas {{ grid-template-columns:1fr; }}
  .puerta.ventas {{ clip-path:polygon(0 0,100% 0,100% calc(100% - 5vw),0 100%);
    margin-right:0; margin-bottom:-3vw; }}
  .puerta.inst {{ padding-left:var(--paso); padding-top:calc(9vh + 3vw); }}
}}

/* ---------- colecciones ---------- */
.seccion {{ padding:clamp(64px,10vh,120px) var(--paso); }}
.seccion-cab {{ display:flex; align-items:baseline; justify-content:space-between;
  gap:20px; border-bottom:1px solid var(--linea); padding-bottom:16px; margin-bottom:34px;
  flex-wrap:wrap; }}
.seccion-cab h2 {{ font-family:var(--display); font-weight:300; letter-spacing:.18em;
  text-transform:uppercase; font-size:clamp(19px,2.4vw,27px); margin:0; }}
.rejilla {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:2px; }}
.pieza {{ position:relative; aspect-ratio:3/4; background:#151311; display:grid;
  align-content:end; gap:5px; padding:22px; overflow:hidden; }}
.pieza::before {{ content:''; position:absolute; inset:0;
  background:
    repeating-linear-gradient(115deg,rgba(232,225,215,.05) 0 2px,transparent 2px 9px),
    radial-gradient(120% 80% at 25% 15%,rgba(232,225,215,.14),transparent 62%),
    linear-gradient(160deg,#2A2724,#151311); }}
.pieza > * {{ position:relative; }}
.pieza b {{ font-family:var(--display); font-weight:400; letter-spacing:.16em;
  text-transform:uppercase; font-size:14px; color:var(--arena); }}
.pieza span {{ font-size:12px; color:#9C958B; }}
.pieza em {{ position:absolute; top:16px; left:16px; font-style:normal; font-size:9.5px;
  letter-spacing:.2em; text-transform:uppercase; color:#BDB5A9;
  border:1px solid rgba(232,225,215,.34); padding:4px 9px; }}

/* ---------- contacto ---------- */
.contacto {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:34px;
  border-top:1px solid var(--linea); padding-top:38px; }}
.contacto h3 {{ font-family:var(--display); font-size:10.5px; letter-spacing:.28em;
  text-transform:uppercase; color:var(--sutil); margin:0 0 10px; font-weight:400; }}
.contacto a {{ text-decoration:none; border-bottom:1px solid var(--linea); }}
.contacto a:hover {{ border-color:currentColor; }}
.pie {{ padding:26px var(--paso) 40px; display:flex; justify-content:space-between; gap:16px;
  flex-wrap:wrap; font-size:11.5px; color:var(--sutil); border-top:1px solid var(--linea); }}
.pie img {{ height:22px; width:auto; opacity:.75; }}
:root[data-theme="light"] .pie img.oscuro, .pie img.oscuro {{ display:none; }}
@media (prefers-color-scheme: light) {{
  .pie img.claro {{ display:none; }} .pie img.oscuro {{ display:block; }}
}}
:root[data-theme="light"] .pie img.claro {{ display:none; }}
:root[data-theme="light"] .pie img.oscuro {{ display:block; }}
:root[data-theme="dark"] .pie img.claro {{ display:block; }}
:root[data-theme="dark"] .pie img.oscuro {{ display:none; }}

/* sin JS el contenido se ve igual: solo con .js se esconde para revelarse */
.js .revela {{ opacity:0; transform:translateY(22px); transition:opacity .8s ease,transform .8s ease; }}
.js .revela.visible {{ opacity:1; transform:none; }}

@media (prefers-reduced-motion: reduce) {{
  *,*::before,*::after {{ animation:none !important; transition:none !important; }}
  .js .revela {{ opacity:1; transform:none; }}
  .hero-foto {{ transform:none; }}
}}
</style>

<div id="cortina" aria-hidden="true">
  <div class="mitad izq"></div>
  <div class="mitad der"></div>
  <div class="centro">
    <div>
      <img class="intro-marca" src="{LOGO_W}" alt="">
      <div class="intro-hilo"></div>
    </div>
  </div>
</div>
<button id="saltar" type="button">Saltar</button>

<header class="barra">
  <img src="{LOGO_W}" alt="Kasteller Revestimientos">
  <nav>
    <a href="#puertas">Ventas</a>
    <a href="#puertas">Institucional</a>
    <a href="#colecciones">Colecciones</a>
    <a href="#contacto">Contacto</a>
  </nav>
</header>

<main>
  <section class="hero">
    <img class="hero-foto" src="{HERO}" alt="Escalera y revestimientos en mármol de un proyecto Kasteller">
    <div class="hero-contenido">
      <img src="{LOGO_W}" alt="Kasteller Revestimientos">
      <p class="hero-lema">Revestimientos que definen espacios.<br>Porcelanatos, mármoles y acabados premium
      para proyectos residenciales, comerciales y corporativos.</p>
    </div>
    <div class="hero-baja"><i></i><span>Descubrir</span></div>
  </section>

  <section class="puertas" id="puertas">
    <a class="puerta ventas" href="#colecciones">
      <span class="eyebrow">01 · Catálogo</span>
      <h2>Ventas</h2>
      <p>Colecciones por ambiente, formato y acabado. Asesoramiento del material a la obra,
      con cotización directa por WhatsApp.</p>
      <span class="ir">Ver colecciones</span>
    </a>
    <a class="puerta inst" href="#contacto">
      <span class="eyebrow">02 · La casa</span>
      <h2>Institucional</h2>
      <p>Quiénes somos, el showroom, los proyectos entregados y cómo acompañamos
      a arquitectos y estudios de diseño.</p>
      <span class="ir">Conocer Kasteller</span>
    </a>
  </section>

  <section class="seccion revela" id="colecciones">
    <div class="seccion-cab">
      <h2>Colecciones</h2>
      <span class="eyebrow">Estructura de ejemplo</span>
    </div>
    <div class="rejilla">
      <article class="pieza"><em>Foto pendiente</em><b>Mármoles</b><span>Calacatta · Statuario · Nero</span></article>
      <article class="pieza"><em>Foto pendiente</em><b>Porcelanatos</b><span>Gran formato · rectificado</span></article>
      <article class="pieza"><em>Foto pendiente</em><b>Maderas</b><span>Símil madera · exterior</span></article>
      <article class="pieza"><em>Foto pendiente</em><b>Revestimientos</b><span>Muros · fachadas · texturas</span></article>
    </div>
  </section>

  <section class="seccion revela" id="contacto">
    <div class="seccion-cab">
      <h2>Contacto</h2>
      <span class="eyebrow">Ciudad del Este · Paraguay</span>
    </div>
    <div class="contacto">
      <div><h3>WhatsApp</h3><a href="https://wa.me/595985869600">+595 985 869 600</a></div>
      <div><h3>Instagram</h3><a href="https://www.instagram.com/kastellerrevestimientos">@kastellerrevestimientos</a></div>
      <div><h3>Facebook</h3><a href="https://www.facebook.com/profile.php?id=100050328950600">Kasteller Revestimientos</a></div>
      <div><h3>Showroom</h3><span>Dirección a confirmar</span></div>
    </div>
  </section>
</main>

<footer class="pie">
  <img class="claro" src="{LOGO_W}" alt="Kasteller">
  <img class="oscuro" src="{LOGO_B}" alt="Kasteller">
  <span>Vista previa de dirección visual · contenido y fotos pendientes</span>
</footer>

<script>
(function () {{
  var root = document.documentElement,
      cortina = document.getElementById('cortina'),
      saltar = document.getElementById('saltar'),
      lento = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!lento) root.classList.add('js');

  function abrir() {{
    if (!cortina || cortina.classList.contains('abre')) return;
    cortina.classList.add('abre');
    root.classList.add('listo');
    if (saltar) saltar.remove();
    setTimeout(function () {{ if (cortina) cortina.remove(); }}, 1200);
  }}

  if (lento) {{ abrir(); }} else {{ setTimeout(abrir, 2400); }}
  if (saltar) saltar.addEventListener('click', abrir);

  var obs = new IntersectionObserver(function (es) {{
    es.forEach(function (e) {{ if (e.isIntersecting) {{ e.target.classList.add('visible');
      obs.unobserve(e.target); }} }});
  }}, {{ threshold: .14 }});
  document.querySelectorAll('.revela').forEach(function (el) {{ obs.observe(el); }});
}})();
</script>
"""

out = HERE / 'kasteller-preview.html'
out.write_text(HTML, encoding='utf-8')
print(f'{out} — {out.stat().st_size/1024:.0f} KB')
