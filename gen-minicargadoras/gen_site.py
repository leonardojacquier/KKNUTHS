#!/usr/bin/env python3
"""Genera en el repo la línea de minicargadoras: fotos, páginas, categoría, implementos, fichas HTML/PDF, bundle y sitemap.

Fuente: "Catálogo de minicargadoras" del fabricante (Shandong Hightop Machinery, en español, 22 páginas dobles).
Las tablas están como imagen en el PDF: los números se transcribieron a mano en dados.py, con la página de origen.
Las fotos de img/ son los recortes del propio catálogo (800×600 con transparencia); img/implementos/ son los
recortes de las páginas 41-44 (320×240, fondo blanco). El PDF del catálogo NO está en el repo.

Reemplaza la tarjeta única "Minicargadora (Skid Steer)" de Movimiento de Suelo por un grupo propio en el bundle,
y deja la URL vieja /ventas/minicargadora-skid-steer/ redirigiendo a la línea.

Correrlo de nuevo es seguro: sobrescribe fotos/páginas/fichas, reescribe el grupo del bundle y sólo agrega al
sitemap lo que falta.  Uso:  python3 gen-minicargadoras/gen_site.py
"""
import base64, hashlib, html as H_, importlib.util, json, pathlib, re, unicodedata, urllib.parse
import numpy as np
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parent
NU = REPO / 'assets/nuevo'
def carga(nome, *attrs):
    s = importlib.util.spec_from_file_location(f'mini_{nome}', AQUI / f'{nome}.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return [getattr(m, a) for a in attrs]
M, = carga('dados', 'M')
MARCA, CURTO, FAMILIA, OPERADOR, LINHA_NOME, LINHA_NOTE, IMPL_NOME, IMPL_NOTE = carga('contenido', 'MARCA', 'CURTO', 'FAMILIA', 'OPERADOR', 'LINHA_NOME', 'LINHA_NOTE', 'IMPL_NOME', 'IMPL_NOTE')
IMPL, GRUPOS_IMPL = carga('implementos', 'IMPL', 'GRUPOS')
WA_N = '595995360060'
CAT_SLUG = 'minicargadoras'; CAT_NOME = 'Minicargadoras'; GRUPO = 'Minicargadoras'
URL_VELHA = 'minicargadora-skid-steer'; NOME_VELHO = 'Minicargadora (Skid Steer)'
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

def ua(a):  # idéntico al slug del bundle
    a = unicodedata.normalize('NFD', a); a = ''.join(c for c in a if not unicodedata.combining(c)).lower()
    a = re.sub(r'[()./]', ' ', a); a = re.sub(r'[^a-z0-9]+', '-', a); return a.strip('-')
def esc(s): return H_.escape(s, quote=True)
def wa(msg): return f'https://wa.me/{WA_N}?text=' + urllib.parse.quote(msg)
def b64(p): return base64.b64encode(pathlib.Path(p).read_bytes()).decode()

MODELOS = list(M)
assert set(MODELOS) == set(CURTO), set(MODELOS) ^ set(CURTO)
def nome(m): return f'Minicargadora {m}'
def slug(m): return ua(nome(m))
LINHA_SLUG = ua(LINHA_NOME); IMPL_SLUG = ua(IMPL_NOME)
FOTO_LINHA = 'zs-minicargadora.png'          # la foto que ya estaba en el sitio: no se toca
FOTO_IMPL = 'implementos-minicargadora.png'

# ---------- texto derivado de los datos ----------
ROD = {'operador de pie': 'con operador de pie', 'a bordo o a pie': 'con operador a bordo o a pie',
       'sentado con techo': 'con asiento y techo', 'cabina': 'con cabina'}
def frase_conf(m):
    p = CURTO[m][0].split(' · ')
    return f'sobre {p[0].lower()}' + (f', {ROD[p[1]]}' if len(p) > 1 else '')
def val(d, k):
    v = d[k]
    if not isinstance(v, list): return v
    if len(set(v)) == 1: return v[0]
    if k == 'motores': return ' o '.join(v)
    return ' · '.join(f'{x} ({mo})' for x, mo in zip(v, d['motores']))
def motor(d):
    if 'motores' in d: return val(d, 'motores')
    return d['motor'].split(' · ')[0] if 'motor' in d else None
def note(m):
    d = M[m]; c = CURTO[m]
    s = f'{FAMILIA[c[3]][0]} {frase_conf(m)}. Carga operativa {c[1]}'
    if 'cucharon' in d: s += f', balde de {d["cucharon"]}'
    s += f', potencia {c[2]}'
    if 'peso' in d: s += f', peso operativo {d["peso"].replace("kg", "").strip()} kg'
    return s + '.'
def lead(m):
    d = M[m]; c = CURTO[m]; mo = motor(d)
    s = f'{FAMILIA[c[3]][0]} {m} {frase_conf(m)}, con carga operativa de {c[1]}'
    if 'cucharon' in d: s += f' y balde de {d["cucharon"]}'
    s += '.'
    if mo: s += f' Motor {mo}, {c[2]}.'
    else: s += f' Potencia nominal de {c[2]}.'
    return s
def uso(m):
    t = FAMILIA[CURTO[m][3]][1]; tp = M[m]['tipo']
    for k, v in OPERADOR.items():
        if k in tp: return f'{t} {v}'
    return t
def tags(m):
    c = CURTO[m]; base = ['minicargadora', 'skid steer', 'minicarregadeira', 'cargadora compacta', 'bobcat', 'pala', 'balde', m.lower(), m.lower().replace('-', '')]
    base += ['orugas'] if 'rugas' in c[0] else []
    base += ['ruedas'] if 'uedas' in c[0] else []
    base += {'pie': ['mini loader', 'stand on', 'compacta'], 'techo': ['asiento', 'techo'], 'cabina': ['cabina', 'obra']}[c[3]]
    mo = (motor(M[m]) or '').lower()
    for w in ['kubota', 'briggs', 'rato', 'xinchai', 'runtong', 'yanmar', 'diesel', 'diésel']:
        if w in mo: base.append(w.replace('é', 'e'))
    return list(dict.fromkeys(base))

SECOES = [
 ('Motor y potencia', [('motores', 'Motor'), ('motor', 'Motor'), ('pot', 'Potencia nominal'), ('rpm', 'Régimen (rpm)'), ('cilindros', 'Cilindros'),
                       ('admision', 'Admisión'), ('emisiones', 'Norma de emisiones'), ('ruido', 'Nivel de ruido')]),
 ('Capacidades y desempeño', [('carga', 'Carga operativa'), ('carga_max', 'Carga máxima'), ('vuelco', 'Carga de vuelco'), ('fuerza', 'Fuerza máxima de elevación'),
                       ('arranque', 'Fuerza máxima de arranque'), ('traccion', 'Fuerza de tracción'), ('cucharon', 'Capacidad del balde'),
                       ('peso', 'Peso operativo'), ('vel', 'Velocidad de desplazamiento'), ('vel_atras', 'Velocidad marcha atrás'),
                       ('pendiente', 'Capacidad de ascenso'), ('ciclo', 'Tiempos de ciclo'), ('autonomia', 'Autonomía'),
                       ('presion_suelo', 'Presión sobre el suelo')]),
 ('Sistema hidráulico', [('presion', 'Presión'), ('caudal', 'Caudal'), ('caudal_trasl', 'Caudal bomba de traslación'), ('caudal_repos', 'Caudal bomba de reposición'),
                       ('caudal_trabajo', 'Caudal del sistema de trabajo'), ('bomba', 'Capacidad de la bomba'), ('alivio', 'Presión de alivio')]),
 ('Dimensiones', [('alt_trab', 'Altura máxima de trabajo'), ('alt_pas', 'Altura máxima del pasador'), ('alt_carga', 'Altura máxima de carga'),
                  ('alt_desc', 'Altura máxima de descarga'), ('dist_desc', 'Alcance de descarga'), ('ang_desc', 'Ángulo máximo de descarga'),
                  ('giro_cuch', 'Ángulo de giro del balde'), ('ang_salida', 'Ángulo de salida'), ('alt_total', 'Altura total'),
                  ('alt_cabina', 'Altura hasta el techo de la cabina'), ('suelo', 'Distancia al suelo'), ('entre_ejes', 'Distancia entre ejes'),
                  ('trocha', 'Ancho de vía'), ('long_sin', 'Longitud sin balde'), ('long_con', 'Longitud con balde'),
                  ('long_pedal', 'Longitud sin balde, pedal plegado'), ('cola', 'Longitud de la cola'), ('contacto', 'Longitud de contacto de la oruga'),
                  ('ancho', 'Ancho total'), ('ancho_cuch', 'Ancho del balde'), ('radio_giro', 'Radio de giro delantero'),
                  ('dims', 'Dimensiones generales (L × A × H)')]),
 ('Rodado', [('neumatico', 'Neumáticos'), ('oruga', 'Oruga')]),
 ('Depósitos', [('comb', 'Combustible'), ('aceite', 'Aceite de motor'), ('hidr', 'Aceite hidráulico')]),
 ('Equipamiento', [('equipo', 'Equipamiento listado en el catálogo')]),
]
def secoes(m):
    d = M[m]; out = [('General', [('Modelo', m), ('Configuración', d['tipo'][0].upper() + d['tipo'][1:])])]
    for t, campos in SECOES:
        rows = [(lab, val(d, k)) for k, lab in campos if k in d]
        if rows: out.append((t, rows))
    return out
def tabela_html(m):
    rows = []
    for t, rs in secoes(m):
        rows.append(f'<tr><th colspan="2" style="text-align:left;background:#fff3ea;color:#14213D">{esc(t)}</th></tr>')
        rows += [f'<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>' for a, b in rs]
    return f'<table><thead><tr><th>Parámetro</th><th>{esc(m)}</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
def H_modelo(m):
    d = M[m]; c = CURTO[m]; r = [['Configuración', c[0]]]
    if motor(d): r.append(['Motor', motor(d)])
    r += [['Potencia', c[2]], ['Carga operativa', c[1]]]
    for k, lab in [('cucharon', 'Balde'), ('peso', 'Peso operativo'), ('alt_desc', 'Altura de descarga')]:
        if k in d: r.append([lab, d[k]])
    return dict(h=['Parámetro', m], r=r[:7])
def kpis(m):
    d = M[m]; c = CURTO[m]
    k = [(c[1], 'Carga operativa')] + ([(d['cucharon'], 'Balde')] if 'cucharon' in d else []) + [(c[2], 'Potencia')]
    k += [(d['peso'], 'Peso operativo')] if 'peso' in d else ([(d['alt_desc'], 'Altura de descarga')] if 'alt_desc' in d else [])
    return k[:4]

# ---------- 1. fotos ----------
def encaixa(im, larg, alt, margem=0.035):
    im = im.convert('RGBA'); bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox(); im = im.crop(bb)
    e = min(larg*(1-2*margem)/im.width, alt*(1-2*margem)/im.height); w, h = max(1, round(im.width*e)), max(1, round(im.height*e))
    r, g, b, a = im.split(); pre = Image.merge('RGB', [ImageChops.multiply(c, a) for c in (r, g, b)]).resize((w, h), Image.LANCZOS); a = a.resize((w, h), Image.LANCZOS)
    pa = np.array(pre).astype(np.int32); aa = np.array(a).astype(np.int32)
    rgb = np.where(aa[..., None] > 0, np.minimum(255, pa*255//np.maximum(aa[..., None], 1)), 0).astype(np.uint8)
    tela = Image.new('RGBA', (larg, alt), (0, 0, 0, 0)); tela.paste(Image.fromarray(np.dstack([rgb, aa.astype(np.uint8)]), 'RGBA'), ((larg-w)//2, (alt-h)//2)); return tela
def salva_png(rgba, dst): rgba.quantize(colors=255, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG).save(dst, optimize=True)
for m in MODELOS:
    (NU/'img/prod'/f'{slug(m)}.png').write_bytes((AQUI/'img'/f'{m}.png').read_bytes())
dst_impl = NU/'img/prod/implementos'; dst_impl.mkdir(exist_ok=True)
IMPL_IT = [(en, es, g, ua(es)) for en, (es, g) in IMPL.items()]
for _, _, _, s in IMPL_IT:
    (dst_impl/f'{s}.jpg').write_bytes((AQUI/'img/implementos'/f'{s}.jpg').read_bytes())
def branco_para_alfa(p):
    a = np.array(Image.open(p).convert('RGB')).astype(int); mn = a.min(axis=2)
    al = np.clip((250 - mn) * 255 // 25, 0, 255).astype(np.uint8)
    return Image.fromarray(np.dstack([a.astype(np.uint8), al]), 'RGBA')
colag = Image.new('RGBA', (800, 600), (0, 0, 0, 0))
for i, s in enumerate(['balde-4-en-1', 'martillo-hidraulico', 'hoyadora', 'horquilla-portapallets', 'zanjadora', 'escoba-angular']):
    cel = encaixa(branco_para_alfa(AQUI/'img/implementos'/f'{s}.jpg'), 262, 290, 0.06)
    colag.alpha_composite(cel, (5 + (i % 3)*264, 10 + (i // 3)*290))
salva_png(colag, NU/'img/prod'/FOTO_IMPL)
print('fotos ok:', len(MODELOS), 'modelos,', len(IMPL_IT), 'implementos')

# ---------- 2. páginas ----------
BASE = (NU/'ventas/central-de-concreto-jbts20/index.html').read_text(encoding='utf-8')
CSS_PROD = BASE.split('<style>')[1].split('</style>')[0]
HEADER = ('<header><div class="in"><a href="/">GNH</a>\n<nav style="display:inline"><a href="/ventas/">Catálogo</a><a href="/institucional/">Institucional</a></nav></div></header>')
FOOTER = BASE.split('<footer>')[1].split('</footer>')[0]
def head(title, desc, url, img, ld, css=CSS_PROD, tipo='product'):
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{tipo}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ":"))}</script>
<style>{css}</style>
</head>
<body>
{HEADER}
'''
def bc_ld(nome_, url):
    return {"@context": "https://schema.org/", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": "https://gnhorizons.com/"},
        {"@type": "ListItem", "position": 2, "name": "Ventas", "item": "https://gnhorizons.com/ventas/"},
        {"@type": "ListItem", "position": 3, "name": CAT_NOME, "item": f"https://gnhorizons.com/ventas/{CAT_SLUG}/"},
        {"@type": "ListItem", "position": 4, "name": nome_, "item": url}]}
def escreve(sl, html):
    d = NU/'ventas'/sl; d.mkdir(parents=True, exist_ok=True); (d/'index.html').write_text(html, encoding='utf-8')
BC = f'<p class="bc"><a href="/">Inicio</a> › <a href="/ventas/">Ventas</a> › <a href="/ventas/{CAT_SLUG}/">{CAT_NOME}</a> › '

for m in MODELOS:
    s = slug(m); url = f'https://gnhorizons.com/ventas/{s}/'; n = nome(m); desc = note(m)
    ld = [{"@context": "https://schema.org/", "@type": "Product", "name": n, "model": m, "brand": {"@type": "Brand", "name": MARCA},
           "category": CAT_NOME, "image": [f"https://gnhorizons.com/img/prod/{s}.png"], "description": desc, "url": url,
           "additionalProperty": [{"@type": "PropertyValue", "name": a, "value": b} for a, b in H_modelo(m)['r']]}, bc_ld(n, url)]
    html = head(f'{n} {MARCA} | GNH Paraguay', desc, url, f'https://gnhorizons.com/img/prod/{s}.png', ld) + f'''<main>
  {BC}{esc(n)}</p>
  <span class="cat">Equipos · {CAT_NOME}</span>
  <h1>{esc(n)}</h1>
  <p class="lead">{esc(lead(m))}</p>
  <figure><img src="/img/prod/{s}.png" alt="{esc(n)} {MARCA}" loading="lazy" width="560" height="420"></figure>
  <a class="cta" href="{wa('Hola, me interesa: ' + n)}" target="_blank" rel="noopener">Consultar por WhatsApp</a>

  <h2>Especificaciones técnicas</h2>
  <div style="overflow-x:auto">{tabela_html(m)}</div>
  <p class="nota">Datos del catálogo del fabricante ({MARCA}). Confirmá configuración, motor y disponibilidad antes de la compra.
  · <a href="/fichas/{s}.html"><strong>Ficha técnica</strong></a>
  · <a href="/fichas/pdf/{s}.pdf" download><strong>Descargar PDF ⬇</strong></a></p>

  <h2>Para qué sirve</h2>
  <p>{esc(uso(m))}</p>

  <h2>Implementos</h2>
  <p>La {esc(m)} trabaja con los <a href="/ventas/{IMPL_SLUG}/"><strong>implementos de la línea</strong></a>: baldes, horquillas, hoyadora, zanjadora, martillo, barredoras y más de 80 opciones. La compatibilidad depende del caudal hidráulico y del enganche de cada modelo: consultanos antes de elegir el implemento.</p>

  <h2>Dentro de la línea</h2>
  <p>Este modelo forma parte de la <a href="/ventas/{LINHA_SLUG}/"><strong>línea de minicargadoras {MARCA}</strong></a>: 20 modelos, de 250 a 1.500 kg de carga operativa, sobre ruedas u orugas.</p>

  <h2>Disponibilidad y asesoramiento</h2>
  <p>GNH importa y entrega el equipo en Paraguay con asesoramiento técnico para elegir el modelo según el acceso a la obra, el terreno y la carga a mover. Atendemos en español y portugués.</p>
  <p><a class="cta alt" href="{wa('Hola, quiero cotizar: ' + n)}" target="_blank" rel="noopener">Pedir cotización</a></p>
  <p class="tags">También buscado como: {esc(', '.join(tags(m)))}.</p>
</main>
<footer>{FOOTER}</footer>
</body>
</html>'''
    escreve(s, html)
print('páginas de modelo ok')

# página de la línea
CSS_LINHA = '''
  .fam{padding:16px 0;border-bottom:1px solid var(--line)}.fam:last-child{border-bottom:0}
  .fam h3{margin:0 0 6px;font-size:19px;color:var(--navy)}.fam p{margin:0 0 6px}.fam .mods{font-size:14.5px;color:var(--mut)}
  .fam .mods a{color:var(--navy)}
  .igrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin:10px 0 6px}
  .igrid figure{margin:0;border:1.5px solid #C5CBD5;border-radius:10px;overflow:hidden;background:#fff}
  .igrid img{width:100%;height:auto;display:block;border:0;border-radius:0;max-width:none}
  .igrid figcaption{font-size:13px;padding:7px 10px;color:var(--ink);border-top:1px solid var(--line);line-height:1.3}
  .igrid figcaption small{display:block;color:var(--mut);font-size:11.5px}
  td a{color:var(--navy);font-weight:600}
  table.wrap{display:table}table.wrap td,table.wrap th{white-space:normal;vertical-align:top}table.wrap td:first-child{white-space:nowrap;font-weight:600;color:var(--navy)}
'''
fams = {'pie': [], 'techo': [], 'cabina': []}
for m in MODELOS: fams[CURTO[m][3]].append(m)
FAM_TIT = {'pie': 'Compactas', 'techo': 'Con asiento y techo', 'cabina': 'Skid steer con cabina'}
def faixa(ms):
    cs = [int(CURTO[m][1].replace('.', '').split()[0]) for m in ms]
    return f'{min(cs):,} a {max(cs):,} kg'.replace(',', '.') if min(cs) != max(cs) else f'{cs[0]} kg'
fam_html = ''.join(f'''
  <div class="fam"><h3>{FAM_TIT[f]} <small style="font-weight:400;color:var(--mut)">· {len(ms)} modelo{"s" if len(ms) > 1 else ""} · {faixa(ms)} de carga operativa</small></h3>
    <p>{esc(FAMILIA[f][1])}</p>
    <p class="mods">{" · ".join(f'<a href="/ventas/{slug(m)}/">{m}</a>' for m in ms)}</p></div>''' for f, ms in fams.items())
tab_rows = ''.join(f'<tr><td><a href="/ventas/{slug(m)}/">{m}</a></td><td>{esc(CURTO[m][0])}</td><td>{esc(CURTO[m][1])}</td><td>{esc(CURTO[m][2])}</td><td>{esc(M[m].get("peso", "—"))}</td></tr>' for m in MODELOS)
amostra = ['balde-4-en-1', 'horquilla-portapallets', 'hoyadora', 'zanjadora', 'martillo-hidraulico', 'barredora-frontal', 'desbrozadora', 'hoja-topadora']
por_slug = {s: (en, es) for en, es, g, s in IMPL_IT}
def fig_impl(s):
    en, es = por_slug[s]
    return f'<figure><img src="/img/prod/implementos/{s}.jpg" alt="{esc(es)} para minicargadora" loading="lazy" width="320" height="240"><figcaption>{esc(es)}<small>{esc(en)}</small></figcaption></figure>'
url = f'https://gnhorizons.com/ventas/{LINHA_SLUG}/'
ld = [{"@context": "https://schema.org/", "@type": "Product", "name": LINHA_NOME, "brand": {"@type": "Brand", "name": MARCA}, "category": CAT_NOME,
       "image": [f"https://gnhorizons.com/img/prod/{FOTO_LINHA}"], "description": LINHA_NOTE, "url": url}, bc_ld(LINHA_NOME, url)]
escreve(LINHA_SLUG, head(f'{LINHA_NOME} (Skid Steer) {MARCA} | GNH Paraguay', LINHA_NOTE, url, f'https://gnhorizons.com/img/prod/{FOTO_LINHA}', ld, CSS_PROD + CSS_LINHA) + f'''<main>
  {BC}{LINHA_NOME}</p>
  <span class="cat">Equipos · {CAT_NOME}</span>
  <h1>{LINHA_NOME} (Skid Steer)</h1>
  <p class="lead">Veinte modelos de minicargadora {MARCA}, desde compactas de 250 kg con operador de pie, que entran por un portón, hasta skid steer con cabina de 1.500 kg de carga operativa y 103 kW. Sobre ruedas u orugas, con más de 80 implementos para cargar, excavar, cortar, nivelar y limpiar.</p>
  <figure><img src="/img/prod/{FOTO_LINHA}" alt="Minicargadora compacta sobre orugas" loading="lazy" width="560" height="420"></figure>
  <a class="cta" href="{wa('Hola, me interesa la línea de minicargadoras')}" target="_blank" rel="noopener">Consultar por WhatsApp</a>

  <h2>Tres formatos</h2>
  {fam_html}

  <h2>Cómo elegir</h2>
  <table class="wrap">
    <thead><tr><th>Dato</th><th>Por qué manda</th></tr></thead>
    <tbody>
      <tr><td>Acceso a la obra</td><td>Si hay que entrar por un portón, un pasillo o un patio, la compacta con operador de pie (de 900 a 1.200 mm de ancho) es la que pasa.</td></tr>
      <tr><td>Terreno</td><td>Ruedas en piso firme y pavimento; orugas en barro, arena, pasto terminado y pendiente, donde reparten el peso y marcan menos el suelo.</td></tr>
      <tr><td>Carga y altura de descarga</td><td>Para cargar camiones hace falta altura: los modelos con cabina descargan a 2.000 mm o más; las compactas, entre 1.376 y 1.730 mm.</td></tr>
      <tr><td>Implementos</td><td>Martillo, zanjadora y fresadora piden caudal hidráulico: conviene elegir la máquina pensando en el implemento más exigente.</td></tr>
    </tbody>
  </table>

  <h2>Todos los modelos</h2>
  <div style="overflow-x:auto"><table>
    <thead><tr><th>Modelo</th><th>Configuración</th><th>Carga operativa</th><th>Potencia</th><th>Peso operativo</th></tr></thead>
    <tbody>{tab_rows}</tbody>
  </table></div>
  <p class="nota">Datos del catálogo del fabricante ({MARCA}). Cada modelo tiene su página con la ficha técnica completa y el PDF para descargar.</p>

  <h2>Implementos</h2>
  <p>Más de 80 implementos para la misma máquina: de baldes y horquillas a hoyadora, zanjadora, martillo hidráulico, fresadora de pavimento, barredoras y desbrozadoras.</p>
  <div class="igrid">{"".join(fig_impl(s) for s in amostra)}</div>
  <p><a href="/ventas/{IMPL_SLUG}/"><strong>Ver los implementos para minicargadora →</strong></a></p>

  <h2>Disponibilidad y asesoramiento</h2>
  <p>GNH importa y entrega las minicargadoras en Paraguay, con asesoramiento técnico para elegir el modelo y los implementos según la obra. Atendemos en español y portugués.</p>
  <p><a class="cta alt" href="{wa('Hola, quiero cotizar una minicargadora')}" target="_blank" rel="noopener">Pedir cotización</a></p>
  <p class="tags">También buscado como: minicargadora, skid steer, minicarregadeira, mini cargadora, cargadora compacta, bobcat, mini loader, pala cargadora pequeña.</p>
</main>
<footer>{FOOTER}</footer>
</body>
</html>''')

# página de implementos
url = f'https://gnhorizons.com/ventas/{IMPL_SLUG}/'
grupos_html = ''
for gi, g in enumerate(GRUPOS_IMPL):
    it = [s for en, es, gg, s in IMPL_IT if gg == gi]
    grupos_html += f'\n  <h2>{esc(g)} <small style="font-weight:400;color:var(--mut);font-size:15px">· {len(it)}</small></h2>\n  <div class="igrid">{"".join(fig_impl(s) for s in it)}</div>'
ld = [{"@context": "https://schema.org/", "@type": "CollectionPage", "name": IMPL_NOME, "description": IMPL_NOTE, "url": url,
       "mainEntity": {"@type": "ItemList", "numberOfItems": len(IMPL_IT),
                      "itemListElement": [{"@type": "ListItem", "position": i+1, "name": es} for i, (_, es, _, _) in enumerate(IMPL_IT)]}}, bc_ld(IMPL_NOME, url)]
escreve(IMPL_SLUG, head(f'{IMPL_NOME} (Skid Steer) | GNH Paraguay', IMPL_NOTE, url, f'https://gnhorizons.com/img/prod/{FOTO_IMPL}', ld, CSS_PROD + CSS_LINHA, 'website') + f'''<main>
  {BC}{IMPL_NOME}</p>
  <span class="cat">Equipos · {CAT_NOME}</span>
  <h1>{IMPL_NOME}</h1>
  <p class="lead">{len(IMPL_IT)} implementos para convertir la minicargadora en la herramienta de cada etapa de la obra: cargar, excavar, perforar, cortar, nivelar, compactar, mezclar, limpiar y desmalezar.</p>
  <a class="cta" href="{wa('Hola, quiero consultar por implementos para minicargadora')}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
  <p class="nota" style="margin-top:14px">La compatibilidad depende del caudal hidráulico y del enganche de cada minicargadora. El catálogo del fabricante no trae especificaciones por implemento: confirmamos medidas, caudal requerido y plazo al cotizar. Debajo de cada nombre va el nombre original del catálogo.</p>
  {grupos_html}

  <h2>Las máquinas</h2>
  <p>Los implementos trabajan con la <a href="/ventas/{LINHA_SLUG}/"><strong>línea de minicargadoras {MARCA}</strong></a>: 20 modelos, compactos con operador de pie o skid steer con cabina, sobre ruedas u orugas.</p>
  <p><a class="cta alt" href="{wa('Hola, quiero cotizar implementos para minicargadora')}" target="_blank" rel="noopener">Pedir cotización</a></p>
  <p class="tags">También buscado como: implementos para minicargadora, accesorios skid steer, implementos bobcat, balde 4 en 1, hoyadora, zanjadora, martillo para minicargadora, horquilla para minicargadora, acessórios minicarregadeira.</p>
</main>
<footer>{FOOTER}</footer>
</body>
</html>''')

# categoría
base_cat = (NU/'ventas/movimiento-de-suelo/index.html').read_text(encoding='utf-8')
css_cat = base_cat.split('<style>')[1].split('</style>')[0]
cat_url = f'https://gnhorizons.com/ventas/{CAT_SLUG}/'
cat_desc = 'Minicargadoras (skid steer) sobre ruedas u orugas: 20 modelos, de compactas de 250 kg con operador de pie a skid steer con cabina de 1.500 kg, y más de 80 implementos. Fichas técnicas y cotización por WhatsApp.'
itens = [(LINHA_NOME, LINHA_SLUG, LINHA_NOTE), (IMPL_NOME, IMPL_SLUG, IMPL_NOTE)] + [(nome(m), slug(m), note(m)) for m in MODELOS]
li = ''.join(f'<li><a href="/ventas/{s}/"><strong>{esc(n)}</strong></a><br><span>{esc(t)}</span></li>' for n, s, t in itens)
(NU/'ventas'/CAT_SLUG).mkdir(exist_ok=True)
(NU/'ventas'/CAT_SLUG/'index.html').write_text(f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{CAT_NOME} (Skid Steer · Minicarregadeiras) | GNH Paraguay</title>
<meta name="description" content="{esc(cat_desc)}">
<link rel="canonical" href="{cat_url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{CAT_NOME} (Skid Steer) | GNH">
<meta property="og:description" content="{esc(cat_desc)}">
<meta property="og:url" content="{cat_url}">
<meta property="og:image" content="https://gnhorizons.com/img/prod/{FOTO_LINHA}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org/", "@type": "CollectionPage", "name": CAT_NOME, "description": cat_desc, "url": cat_url}, ensure_ascii=False)}</script>
<style>{css_cat}</style>
</head>
<body>
{HEADER}
<main>
  <p class="bc"><a href="/">Inicio</a> › <a href="/ventas/">Ventas</a> › {CAT_NOME}</p>
  <h1>{CAT_NOME} (Skid Steer · Minicarregadeiras)</h1>
  <p class="lead">Línea completa de minicargadoras {MARCA}: compactas con operador de pie, con asiento y techo, y skid steer con cabina, sobre ruedas u orugas. De 250 a 1.500 kg de carga operativa, con más de 80 implementos.</p>
  <div class="ayuda"><p><strong>¿Compacta o con cabina?</strong> La compacta entra por un portón y trabaja en patios y jardines; la de cabina carga camiones y hace la jornada completa de obra.</p></div>
  <h2>Equipos disponibles</h2>
  <ul class="prods">{li}</ul>
  <h2>Disponibilidad y asesoramiento</h2>
  <p>GNH importa y entrega minicargadoras en Paraguay, con asesoramiento técnico para elegir el modelo y los implementos según la obra. Atendemos en español y portugués.</p>
  <p><a class="cta" href="{wa('Hola, quiero consultar sobre minicargadoras')}" target="_blank" rel="noopener">Consultar por WhatsApp</a></p>
</main>
<footer>{FOOTER}</footer>
</body>
</html>''', encoding='utf-8')

# URL vieja -> línea
(NU/'ventas'/URL_VELHA).mkdir(exist_ok=True)
(NU/'ventas'/URL_VELHA/'index.html').write_text(f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{LINHA_NOME} | GNH Paraguay</title>
<link rel="canonical" href="https://gnhorizons.com/ventas/{LINHA_SLUG}/">
<meta name="robots" content="noindex,follow">
<meta http-equiv="refresh" content="0; url=/ventas/{LINHA_SLUG}/">
</head>
<body><p>La minicargadora ahora tiene su línea completa: <a href="/ventas/{LINHA_SLUG}/">{LINHA_NOME}</a>.</p></body>
</html>''', encoding='utf-8')

# Movimiento de Suelo: la tarjeta vieja pasa a apuntar a la línea
ms = NU/'ventas/movimiento-de-suelo/index.html'; t = ms.read_text(encoding='utf-8')
t = re.sub(r'<a href="/ventas/(?:minicargadora-skid-steer|linea-de-minicargadoras)/"><strong>[^<]*</strong></a>\s*<br><span>[^<]*</span>',
           f'<a href="/ventas/{LINHA_SLUG}/"><strong>Minicargadoras (Skid Steer)</strong></a>\n      <br><span>{esc(LINHA_NOTE)}</span>', t)
assert f'/ventas/{LINHA_SLUG}/' in t; ms.write_text(t, encoding='utf-8')
print('línea, implementos, categoría, redirección ok')

# ---------- 3. fichas HTML + PDF ----------
fb = (NU/'fichas/camion-volquete-orugas.html').read_text(encoding='utf-8')
css_ficha = fb.split('<style>')[1].split('</style>')[0]
LOGO = b64(NU/'img/logo-ficha-sola.png')
CSSP = (REPO/'gen-fichas-plataformas.py').read_text(encoding='utf-8').split('CSS = """')[1].split('"""')[0]
CSSP = CSSP.replace('@page{size:A4;margin:0}', '@page{size:A4;margin:0 0 16mm 0}')
CSSP += '\n.photo img{max-height:185pt}\ntd.g{font-weight:700;color:#14213D;background:#fff3ea !important;width:auto}\n'
FOOTER_PDF = '<div style="width:100%;font-size:7pt;color:#8a93a3;text-align:center;font-family:Arial">gnhorizons.com &middot; WhatsApp +595 995 360060 &middot; P&aacute;gina <span class="pageNumber"></span> de <span class="totalPages"></span></div>'
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=CHROME); pg = br.new_page()
    for m in MODELOS:
        s = slug(m); n = nome(m); chip = f'Minicargadoras · {CURTO[m][0]}'
        kv = ''.join(f'<tr><th colspan="2" style="background:#fff3ea;color:#14213D">{esc(t_)}</th></tr>' + ''.join(f'<tr><th>{esc(a)}</th><td>{esc(b)}</td></tr>' for a, b in rs) for t_, rs in secoes(m))
        ficha = f'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(n)} {MARCA} — Ficha Técnica | GNH</title>
<meta name="description" content="{esc(note(m))}">
<link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&f[]=general-sans@400,500,600&display=swap" rel="stylesheet">
<style>{css_ficha}</style>
</head><body>
<div class="sheet">
  <div class="top">
    <div class="brand-row">
      <img src="data:image/png;base64,{LOGO}" alt="GNH" style="height:58px;width:auto">
      <div class="doc-tag"><span class="dt">Ficha Técnica</span><span class="fam">{esc(chip)}</span></div>
    </div>
    <div class="rule"></div>
    <div class="title-block">
      <h1>{esc(n)}</h1>
      <p class="sub">{esc(note(m))}</p>
      <div class="actions"><a class="btn btn-pdf" href="pdf/{s}.pdf" download>⬇ PDF ficha técnica</a>
        <a class="btn btn-wa" href="{wa('Hola, quiero consultar sobre: ' + n)}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
        <a class="btn btn-back" href="../ventas/{s}/">← Volver al producto</a>
      </div>
    </div>
  </div>
  <div class="body">
    <figure style="margin:18px 0 6px"><img src="../img/prod/{s}.png" alt="{esc(n)}" loading="lazy" style="width:100%;max-width:520px;height:auto;border:1px solid var(--hair)"></figure>
    <div class="lead"><p>{esc(lead(m))}</p></div>
    <h2>Para qué sirve</h2><p>{esc(uso(m))}</p>
    <h2>Especificaciones técnicas</h2><table class="kv">{kv}</table>
    <p class="kv-extra">Datos del catálogo del fabricante ({MARCA}). Sujetos a confirmación de configuración, motor y disponibilidad antes de la compra.</p>
  </div>
</div>
</body>
</html>'''
        (NU/'fichas'/f'{s}.html').write_text(ficha, encoding='utf-8')
        kp = ''.join(f'<div><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in kpis(m))
        rows_pdf = ''.join(f'<tr><td class="g" colspan="2">{esc(t_)}</td></tr>' + ''.join(f'<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>' for a, b in rs) for t_, rs in secoes(m))
        html_pdf = f'''<div class="head"><img src="data:image/png;base64,{LOGO}" alt="GNH">
<div class="r"><div class="ft">FICHA T&Eacute;CNICA</div><span class="chip">{esc(chip).upper()}</span></div></div>
<h1>{esc(n).upper()}</h1>
<p class="sub">{esc(note(m))}</p>
<div class="kpis">{kp}</div>
<div class="photo"><img src="data:image/png;base64,{b64(NU/'img/prod'/f'{s}.png')}" alt=""></div>
<h2>Descripci&oacute;n</h2><p class="eq">{esc(lead(m))} {esc(uso(m))}</p>
<h2>Especificaciones t&eacute;cnicas</h2><table>{rows_pdf}</table>
<div class="final">
 <b>GNH — Generando Nuevos Horizontes</b> &middot; Av. Rep&uacute;blica del Per&uacute; km 7, Ciudad del Este &middot; Acceso Sur, &Ntilde;emby, Paraguay<br>
 WhatsApp <b>+595 995 360060</b> &middot; comercial@gnhorizons.com &middot; gnhorizons.com
 <div class="disc">Datos transcritos del cat&aacute;logo del fabricante {MARCA}. Sujetos a cambio sin previo aviso; confirm&aacute; configuraci&oacute;n, motor, plazos y disponibilidad con nuestro equipo t&eacute;cnico antes de la compra.</div></div>'''
        pg.set_content(f'<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><style>{CSSP}</style></head><body>{html_pdf}</body></html>')
        out = NU/'fichas/pdf'/f'{s}.pdf'
        pg.pdf(path=str(out), format='A4', print_background=True, display_header_footer=True, header_template='<span></span>', footer_template=FOOTER_PDF, margin={'top': '0mm', 'bottom': '16mm'})
    br.close()
print('fichas ok:', len(MODELOS))

# ---------- 4. bundle ----------
def js(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':'))
idx = NU/'ventas/index.html'; ih = idx.read_text(encoding='utf-8')
atual = re.search(r'assets/(ventas-[A-Za-z0-9_-]+\.js)', ih).group(1); bp = NU/'assets'/atual; s0 = bp.read_text(encoding='utf-8'); s = s0
# 4a. saca la tarjeta vieja de Movimiento de Suelo y su tabla H
s = re.sub(r'\{name:"' + re.escape(NOME_VELHO) + r'",brand:"[^"]*",img:"[^"]*",note:"[^"]*",tags:\[[^\]]*\]\},?', '', s)
s = re.sub(r'"' + re.escape(NOME_VELHO) + r'":\{h:\[[^\]]*\],r:\[(?:\[[^\]]*\],?)*\]\},', '', s)
# 4b. saca el grupo si ya existía (re-ejecución) y lo vuelve a escribir
s = re.sub(r'\{title:"' + GRUPO + r'",products:\[.*?\]\},(?=\{title:"Áridos y Trituración")', '', s, flags=re.S)
todos = [LINHA_NOME, IMPL_NOME] + [nome(m) for m in MODELOS]
for n in todos:
    s = re.sub(r'"' + re.escape(n) + r'":\{h:\[[^\]]*\],r:\[(?:\[[^\]]*\],?)*\]\},', '', s)
def entrada(n, img, nt, tg): return '{name:%s,brand:%s,img:%s,note:%s,tags:%s}' % (js(n), js(MARCA), js(img), js(nt), js(tg))
ents = [entrada(LINHA_NOME, f'../img/prod/{FOTO_LINHA}', LINHA_NOTE, ['minicargadora', 'skid steer', 'minicarregadeira', 'linea', 'cargadora compacta', 'bobcat', 'orugas', 'ruedas', 'cabina', 'implementos']),
        entrada(IMPL_NOME, f'../img/prod/{FOTO_IMPL}', IMPL_NOTE, ['implementos', 'accesorios', 'minicargadora', 'skid steer', 'balde', 'hoyadora', 'zanjadora', 'martillo', 'horquilla', 'barredora'])]
ents += [entrada(nome(m), f'../img/prod/{slug(m)}.png', note(m), tags(m)) for m in MODELOS]
alvo = '{title:"Áridos y Trituración",products:['; assert s.count(alvo) == 1
s = s.replace(alvo, '{title:%s,products:[%s]},' % (js(GRUPO), ','.join(ents)) + alvo, 1)
H_L = dict(h=['Modelo', 'Configuración', 'Carga operativa'], r=[[f'<a href="/ventas/{slug(m)}/">{m}</a>', CURTO[m][0], CURTO[m][1]] for m in ['HY320T', 'HYS382T', 'HY-V1000', 'HYSL390', 'HYS25', 'HYS50', 'HYS75', 'HYS125']]
           + [[f'<a href="/ventas/{LINHA_SLUG}/">Ver los 20 modelos</a>', '', '']])
cont = {}
for en, es, g, sl in IMPL_IT: cont.setdefault(g, []).append(es)
H_I = dict(h=['Grupo', 'Implementos'], r=[[GRUPOS_IMPL[g], f'{len(v)} · ' + ', '.join(v[:3]).lower() + '…'] for g, v in sorted(cont.items())]
           + [[f'<a href="/ventas/{IMPL_SLUG}/">Ver los {len(IMPL_IT)} implementos</a>', '']])
hmap = f'{js(LINHA_NOME)}:{{h:{js(H_L["h"])},r:{js(H_L["r"])}}},{js(IMPL_NOME)}:{{h:{js(H_I["h"])},r:{js(H_I["r"])}}},'
hmap += ''.join('%s:{h:%s,r:%s},' % (js(nome(m)), js(H_modelo(m)['h']), js(H_modelo(m)['r'])) for m in MODELOS)
assert s.count('H={') == 1; s = s.replace('H={', 'H={' + hmap, 1)
assert NOME_VELHO not in s and s.count(f'title:{js(GRUPO)}') == 1
if s != s0:
    novo = 'ventas-' + hashlib.md5(s.encode()).hexdigest()[:8] + '.js'
    (NU/'assets'/novo).write_text(s, encoding='utf-8')
    if novo != atual: bp.unlink()
    assert ih.count(atual) == 1; idx.write_text(ih.replace(atual, novo), encoding='utf-8')
else: novo = atual
print('bundle', atual, '->', novo)

# ---------- 5. sitemap ----------
sm = NU/'sitemap.xml'; x = sm.read_text(encoding='utf-8')
x = re.sub(r'\s*<url><loc>https://gnhorizons\.com/ventas/' + URL_VELHA + r'/</loc>.*?</url>', '', x)
urls = [f'https://gnhorizons.com/ventas/{u}/' for u in [CAT_SLUG, LINHA_SLUG, IMPL_SLUG] + [slug(m) for m in MODELOS]] + [f'https://gnhorizons.com/fichas/{slug(m)}.html' for m in MODELOS]
novos = ''.join(f'  <url><loc>{u}</loc><changefreq>monthly</changefreq><priority>{"0.7" if "/fichas/" in u else "0.8"}</priority></url>\n' for u in urls if u not in x)
sm.write_text(x.replace('</urlset>', novos + '</urlset>'), encoding='utf-8')
print('sitemap +', novos.count('<url>'))
