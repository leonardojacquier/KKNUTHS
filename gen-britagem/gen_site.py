#!/usr/bin/env python3
"""Gera no repo a linha de trituracao HONSN: fotos, paginas, categoria, fichas HTML/PDF, bundle e sitemap.

Fonte: catalogo geral HONSN (Hongxing) 2026, chines/ingles, 108 paginas, texto vetorizado —
as tabelas foram transcritas a mao das paginas (numeros em dados_parte1/2.py, com a pagina de
origem em cada bloco). O PDF do catalogo NAO esta no repo (23 MB); os recortes de produto
usados nas fotos estao em img/ (sao os rasters embutidos no proprio catalogo, ~300-450 px).

Rodar de novo e seguro: sobrescreve fotos/paginas/fichas, pula o bundle se o grupo ja existe
e so acrescenta ao sitemap o que falta.  Uso:  python3 gen-britagem/gen_site.py
"""
import base64, hashlib, html as H_, importlib.util, io, json, pathlib, re, unicodedata
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parent
NU = REPO / 'assets/nuevo'
def carga(nome, attr):
    s = importlib.util.spec_from_file_location(nome, AQUI / f'{nome}.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return getattr(m, attr)
DADOS = {**carga('dados_parte1', 'DADOS'), **carga('dados_parte2', 'DADOS2')}
PRODUTOS = carga('contenido', 'PRODUTOS'); MARCA = carga('contenido', 'MARCA')
WA_N = '595995360060'
CAT_SLUG = 'aridos-y-trituracion'; CAT_NOME = 'Áridos y Trituración'; GRUPO = 'Áridos y Trituración'

def ua(a):  # identico ao slug do bundle
    a = unicodedata.normalize('NFD', a); a = ''.join(c for c in a if not unicodedata.combining(c)).lower()
    a = re.sub(r'[()./]', ' ', a); a = re.sub(r'[^a-z0-9]+', '-', a); return a.strip('-')
def esc(s): return H_.escape(s, quote=True)
def wa(msg): return f'https://wa.me/{WA_N}?text=' + __import__('urllib.parse').parse.quote(msg)
def b64(p): return base64.b64encode(pathlib.Path(p).read_bytes()).decode()
for p in PRODUTOS: p['slug'] = ua(p['nome'])
LINHA = PRODUTOS[0]; EQUIPOS = PRODUTOS[1:]

# ---------- 1. fotos ----------
def encaixa(im, larg, alt, margem=0.035):
    im = im.convert('RGBA'); bb = im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox(); im = im.crop(bb)
    esc_ = min(larg*(1-2*margem)/im.width, alt*(1-2*margem)/im.height)
    w, h = max(1, round(im.width*esc_)), max(1, round(im.height*esc_))
    r, g, b, a = im.split(); pre = Image.merge('RGB', [ImageChops.multiply(c, a) for c in (r, g, b)]).resize((w, h), Image.LANCZOS); a = a.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (w, h)); sp = out.load(); pp = pre.load(); ap = a.load()
    for y in range(h):
        for x in range(w):
            av = ap[x, y]; sp[x, y] = (0, 0, 0, 0) if av == 0 else tuple(min(255, c*255//av) for c in pp[x, y]) + (av,)
    tela = Image.new('RGBA', (larg, alt), (0, 0, 0, 0)); tela.paste(out, ((larg-w)//2, (alt-h)//2)); return tela
def salva_png(rgba, dst): rgba.quantize(colors=255, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG).save(dst, optimize=True)
for p in PRODUTOS:
    src = Image.open(AQUI / 'img' / p['img'])
    salva_png(encaixa(src, 800, 600), NU / 'img/prod' / f"{p['slug']}.png")
salva_png(encaixa(Image.open(AQUI / 'img' / LINHA['img']), 1400, 560, 0.02), NU / 'img/prod/linea-de-trituracion-esquema.png')
print('fotos ok')

# ---------- helpers de tabela ----------
def tabelas_html(chaves, cls='', wrap=True):
    if chaves is None: return ''
    if isinstance(chaves, str): chaves = (chaves,)
    out = []
    for k in chaves:
        d = DADOS[k]; ncol = len(d['cols'])
        rows = []
        for titulo, rs in d['grupos']:
            if titulo: rows.append(f'<tr><th colspan="{ncol}" style="text-align:left;background:#fff3ea;color:#14213D">{esc(titulo)}</th></tr>')
            rows += ['<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>' for r in rs]
        t = (f'<table class="{cls}"><thead><tr>' + ''.join(f'<th>{esc(c)}</th>' for c in d['cols']) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>')
        if len(chaves) > 1: t = f'<h3 style="margin:18px 0 6px;font-size:17px;color:var(--navy)">{esc(d["nome"])}</h3>' + t
        if d.get('nota'): t += f'<p class="nota">{esc(d["nota"])}</p>'
        out.append(f'<div style="overflow-x:auto">{t}</div>' if wrap else t)
    return ''.join(out)
def resumo_H(p):
    """tabela compacta do card: 3 colunas-chave, ate 8 modelos, link para a pagina."""
    if p is LINHA:
        return dict(h=['Etapa', 'Equipo', 'Serie HONSN'], r=[
            ['1 · Alimentación', f'<a href="/ventas/{EQUIPOS[0]["slug"]}/">Alimentador vibratorio</a>', 'GZD · ZSW'],
            ['2 · Primaria', f'<a href="/ventas/{EQUIPOS[1]["slug"]}/">Mandíbulas</a>', 'PE · PEX · HJ'],
            ['3 · Secundaria', f'<a href="/ventas/{EQUIPOS[3]["slug"]}/">Cono</a> / <a href="/ventas/{EQUIPOS[4]["slug"]}/">impacto</a>', 'SC · PF · CI'],
            ['4 · Arena', f'<a href="/ventas/{EQUIPOS[6]["slug"]}/">Eje vertical</a>', 'VSI7A'],
            ['5 · Cribado', f'<a href="/ventas/{EQUIPOS[7]["slug"]}/">Criba circular</a>', 'HX · HX-D'],
            ['6 · Transporte', f'<a href="/ventas/{EQUIPOS[8]["slug"]}/">Cintas</a>', 'TD · móvil'],
            ['Formatos', f'<a href="/ventas/{EQUIPOS[9]["slug"]}/">Orugas</a> · <a href="/ventas/{EQUIPOS[10]["slug"]}/">Neumáticos</a> · <a href="/ventas/{EQUIPOS[11]["slug"]}/">Modular</a>', 'WOTETRACK · MTF/MTN · KJ']])
    k = p['dados'] if isinstance(p['dados'], str) else p['dados'][0]; d = DADOS[k]
    quer = ['Modelo', 'Capacidad', 'Potencia', 'Equipo principal', 'Alimentación máx', 'Ancho de banda', 'Caudal en trituración']
    idx = [i for i, c in enumerate(d['cols']) if any(c.startswith(q) for q in quer)][:3]
    todas = [r for _, rs in d['grupos'] for r in rs]
    passo = max(1, len(todas)//7); amostra = todas[::passo][:8]
    r = [[row[i] for i in idx] for row in amostra]
    r.append([f'<a href="/ventas/{p["slug"]}/">Ver los {len(todas)} modelos</a>'] + [''] * (len(idx)-1))
    return dict(h=[d['cols'][i] for i in idx], r=r)

# ---------- 2. paginas de produto ----------
CSS_PROD = (NU / 'ventas/central-de-concreto-jbts20/index.html').read_text(encoding='utf-8').split('<style>')[1].split('</style>')[0]
HEADER = ('<header><div class="in"><a href="/">GNH</a>\n<nav style="display:inline"><a href="/ventas/">Catálogo</a><a href="/institucional/">Institucional</a></nav></div></header>')
FOOTER = (NU / 'ventas/central-de-concreto-jbts20/index.html').read_text(encoding='utf-8').split('<footer>')[1].split('</footer>')[0]
def head(title, desc, url, img, ld):
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="product">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ":"))}</script>
<style>{CSS_PROD}</style>
</head>
<body>
{HEADER}
'''
def ld_produto(p, url):
    return [{"@context": "https://schema.org/", "@type": "Product", "name": p['nome'], "brand": {"@type": "Brand", "name": MARCA}, "category": CAT_NOME, "image": [f"https://gnhorizons.com/img/prod/{p['slug']}.png"], "description": p['note'], "url": url},
            {"@context": "https://schema.org/", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Inicio", "item": "https://gnhorizons.com/"},
                {"@type": "ListItem", "position": 2, "name": "Ventas", "item": "https://gnhorizons.com/ventas/"},
                {"@type": "ListItem", "position": 3, "name": CAT_NOME, "item": f"https://gnhorizons.com/ventas/{CAT_SLUG}/"},
                {"@type": "ListItem", "position": 4, "name": p['nome'], "item": url}]}]
def pagina_produto(p):
    url = f'https://gnhorizons.com/ventas/{p["slug"]}/'; slug = p['slug']
    title = f'{p["nome"]} {MARCA} | GNH Paraguay'; desc = p['note']
    vent = ''.join(f'<li>{esc(v)}</li>' for v in p.get('ventajas', []))
    ficha = f'/fichas/{slug}.html'; pdf = f'/fichas/pdf/{slug}.pdf'
    body = f'''<main>
  <p class="bc"><a href="/">Inicio</a> › <a href="/ventas/">Ventas</a> › <a href="/ventas/{CAT_SLUG}/">{CAT_NOME}</a> › {esc(p['nome'])}</p>
  <span class="cat">Equipos · {CAT_NOME}</span>
  <h1>{esc(p['nome'])}</h1>
  <p class="lead">{esc(p['lead'])}</p>
  <figure><img src="/img/prod/{slug}.png" alt="{esc(p['nome'])} {MARCA}" loading="lazy" width="560" height="420"></figure>
  <a class="cta" href="{wa('Hola, me interesa: ' + p['nome'])}" target="_blank" rel="noopener">Consultar por WhatsApp</a>

  <h2>Ventajas</h2>
  <ul>{vent}</ul>

  <h2>Modelos y especificaciones técnicas</h2>
  {tabelas_html(p['dados'])}
  <p class="nota">Datos del catálogo del fabricante ({MARCA}). La capacidad varía con el material y la granulometría de entrada; confirmá configuración y disponibilidad antes de la compra.
  · <a href="{ficha}"><strong>Ficha técnica</strong></a>
  · <a href="{pdf}" download><strong>Descargar PDF ⬇</strong></a></p>

  <h2>Dentro de la línea</h2>
  <p>Este equipo forma parte de la <a href="/ventas/{LINHA['slug']}/"><strong>línea completa de trituración</strong></a>: alimentación, trituración primaria y secundaria, fabricación de arena, cribado y transporte. GNH la entrega completa —fija, modular o móvil— o por equipos, para ampliar una planta existente.</p>

  <h2>Disponibilidad y asesoramiento</h2>
  <p>GNH importa y entrega el equipo en Paraguay con asesoramiento técnico para dimensionarlo según el material, la producción objetivo y las fracciones a producir. Atendemos en español y portugués.</p>
  <p><a class="cta alt" href="{wa('Hola, quiero cotizar: ' + p['nome'])}" target="_blank" rel="noopener">Pedir cotización</a></p>
  <p class="tags">También buscado como: {esc(', '.join(p['tags']))}.</p>
</main>
<footer>{FOOTER}</footer>
</body>
</html>'''
    d = NU / 'ventas' / slug; d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(head(title, desc, url, f'https://gnhorizons.com/img/prod/{slug}.png', ld_produto(p, url)) + body, encoding='utf-8')
for p in EQUIPOS: pagina_produto(p)
print('paginas de produto ok')

# ---------- 3. pagina da linha ----------
ETAPAS = [
 ('1', 'Alimentación', 'Alimentador vibratorio con parrilla', EQUIPOS[0],
  'Recibe la descarga de la pala o del camión y entrega material a caudal constante a la primaria. La parrilla separa el fino y la tierra antes de la boca: material que no necesita trituración no debe gastar mandíbula.',
  'El tamaño del balde que descarga y la granulometría de entrada.'),
 ('2', 'Trituración primaria', 'Trituradora de mandíbulas', EQUIPOS[1],
  'Reduce el bloque de cantera a un tamaño manejable. Es el equipo que define la capacidad de toda la línea: nada aguas abajo procesa más de lo que la primaria entrega. Serie PE para plantas convencionales, serie HJ para trabajo pesado.',
  'La boca de entrada (el bloque mayor que se puede alimentar) y la abertura de salida, que fija la reducción.'),
 ('3', 'Trituración secundaria', 'Trituradora de cono o de impacto', EQUIPOS[3],
  'Lleva el material al tamaño comercial. El cono (SC) rinde más en roca abrasiva y dura —basalto, granito— con menor costo de desgaste. El impacto (PF, CI) da mejor forma de grano y más fino, y es el camino en caliza y en reciclado de hormigón.',
  'El material de entrada decide entre cono e impacto, no el presupuesto.'),
 ('4', 'Fabricación de arena', 'Trituradora de eje vertical (VSI)', EQUIPOS[6],
  'Etapa terciaria opcional: produce arena manufacturada y cubica el agregado. Se agrega cuando la planta vende arena o cuando el pliego exige forma de grano.',
  'El caudal de la secundaria y el porcentaje de arena que se quiere producir.'),
 ('5', 'Clasificación', 'Criba vibratoria circular', EQUIPOS[7],
  'Separa el producto en las fracciones que se venden y devuelve a la secundaria lo que quedó grueso. El circuito cerrado de retorno es lo que sostiene la granulometría estable a lo largo del turno.',
  'La cantidad de fracciones y el área de tamizado por tonelada.'),
 ('6', 'Transporte', 'Cintas transportadoras', EQUIPOS[8],
  'Unen los equipos y forman las pilas de producto terminado. Suelen ser lo último que se especifica y lo primero que limita la planta: ancho, ángulo e inclinación mal elegidos derraman material y obligan a bajar el ritmo.',
  'El caudal en t/h, la distancia y el desnivel a vencer.'),
]
etapas_html = ''.join(f'''
  <div class="etapa"><div class="num">{n}</div><div class="txt">
    <span class="et">Etapa {n} · {esc(t)}</span>
    <h3><a href="/ventas/{eq['slug']}/">{esc(e)}</a></h3>
    <p>{esc(tx)}</p>
    <p class="dim"><b>Qué lo dimensiona:</b> {esc(dim)}</p>
  </div></div>''' for n, t, e, eq, tx, dim in ETAPAS)
formatos = ''.join(f'<li><a href="/ventas/{eq["slug"]}/"><strong>{esc(eq["nome"])}</strong></a><br><span>{esc(eq["note"])}</span></li>' for eq in EQUIPOS[9:12])
CSS_LINHA = '''
  .etapa{display:grid;grid-template-columns:54px 1fr;gap:16px;padding:18px 0;border-bottom:1px solid var(--line)}
  .etapa:last-child{border-bottom:0}
  .etapa .num{width:44px;height:44px;border-radius:50%;display:grid;place-items:center;background:var(--navy);color:#fff;font-weight:700;font-size:17px}
  .etapa .et{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--orange);font-weight:700}
  .etapa h3{margin:3px 0 7px;font-size:19px}.etapa h3 a{color:var(--navy);text-decoration:none}.etapa h3 a:hover{text-decoration:underline}
  .etapa p{margin:0 0 6px}.etapa .dim{font-size:14px;color:var(--mut)}
  ul.prods{list-style:none;padding:0}ul.prods li{padding:10px 0;border-bottom:1px solid var(--line)}ul.prods span{color:var(--mut);font-size:14.5px}
  @media(max-width:640px){.etapa{grid-template-columns:1fr}.etapa .num{display:none}}
'''
url = f'https://gnhorizons.com/ventas/{LINHA["slug"]}/'
ld = ld_produto(LINHA, url); ld[0]['@type'] = 'Product'
pg = head(f'{LINHA["nome"]} — planta de áridos {MARCA} | GNH Paraguay', LINHA['note'], url, 'https://gnhorizons.com/img/prod/linea-de-trituracion-esquema.png', ld).replace('</style>', CSS_LINHA + '</style>') + f'''<main>
  <p class="bc"><a href="/">Inicio</a> › <a href="/ventas/">Ventas</a> › <a href="/ventas/{CAT_SLUG}/">{CAT_NOME}</a> › {esc(LINHA['nome'])}</p>
  <span class="cat">Equipos · {CAT_NOME}</span>
  <h1>{esc(LINHA['nome'])}</h1>
  <p class="lead">{esc(LINHA['lead'])}</p>
  <figure><img src="/img/prod/linea-de-trituracion-esquema.png" alt="Línea de trituración móvil HONSN: pala, primaria, secundaria y criba en tren" loading="lazy" width="1400" height="560" style="max-width:100%"></figure>
  <a class="cta" href="{wa('Hola, me interesa: Línea completa de trituración')}" target="_blank" rel="noopener">Consultar por WhatsApp</a>

  <h2>Cómo se compone la línea</h2>
  {etapas_html}

  <h2>Tres formatos de planta</h2>
  <ul class="prods">{formatos}</ul>

  <h2>Cómo se dimensiona</h2>
  <p>Tres datos definen la línea completa, y conviene tenerlos antes de mirar modelos:</p>
  <table>
    <thead><tr><th>Dato</th><th>Por qué manda</th></tr></thead>
    <tbody>
      <tr><td>Material de entrada</td><td>Basalto y granito son abrasivos y empujan hacia cono en la secundaria; caliza y hormigón reciclado admiten impacto, con mejor forma de grano.</td></tr>
      <tr><td>Producción objetivo (t/h)</td><td>Fija la primaria, y la primaria fija todo lo demás: ninguna etapa posterior procesa más de lo que ella entrega.</td></tr>
      <tr><td>Fracciones a producir</td><td>Determinan los pisos de la criba y el circuito de retorno a la secundaria.</td></tr>
    </tbody>
  </table>

  <h2>Equipos de la línea</h2>
  <ul class="prods">{''.join(f'<li><a href="/ventas/{eq["slug"]}/"><strong>{esc(eq["nome"])}</strong></a><br><span>{esc(eq["note"])}</span></li>' for eq in EQUIPOS[:9])}</ul>

  <h2>Disponibilidad y asesoramiento</h2>
  <p>GNH importa y distribuye equipos de trituración {MARCA} en Paraguay, con asesoramiento técnico para dimensionar la línea según el material y la producción objetivo. Atendemos en español y portugués.</p>
  <p><a class="cta alt" href="{wa('Hola, quiero cotizar una línea de trituración')}" target="_blank" rel="noopener">Pedir cotización</a></p>
  <p class="tags">También buscado como: {esc(', '.join(LINHA['tags']))}.</p>
</main>
<footer>{FOOTER}</footer>
</body>
</html>'''
d = NU / 'ventas' / LINHA['slug']; d.mkdir(exist_ok=True); (d / 'index.html').write_text(pg, encoding='utf-8')

# ---------- 4. pagina de categoria ----------
base = (NU / 'ventas/movimiento-de-suelo/index.html').read_text(encoding='utf-8')
css_cat = base.split('<style>')[1].split('</style>')[0]
cat_desc = 'Línea completa de trituración HONSN: alimentadores, trituradoras de mandíbulas, cono e impacto, areneras VSI, cribas vibratorias, cintas y plantas móviles o modulares. Distribuido por GNH en Paraguay — fichas técnicas y cotización por WhatsApp.'
cat_url = f'https://gnhorizons.com/ventas/{CAT_SLUG}/'
itens = ''.join(f'<li><a href="/ventas/{p["slug"]}/"><strong>{esc(p["nome"])}</strong></a><br><span>{esc(p["note"])}</span></li>' for p in PRODUTOS)
cat = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{CAT_NOME} (Britagem y Chancado) | GNH Paraguay</title>
<meta name="description" content="{esc(cat_desc)}">
<link rel="canonical" href="{cat_url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{CAT_NOME} (Britagem y Chancado) | GNH">
<meta property="og:description" content="{esc(cat_desc)}">
<meta property="og:url" content="{cat_url}">
<meta property="og:image" content="https://gnhorizons.com/img/logo-oficial-sola.png">
<script type="application/ld+json">{json.dumps({"@context":"https://schema.org/","@type":"CollectionPage","name":CAT_NOME,"description":cat_desc,"url":cat_url}, ensure_ascii=False)}</script>
<style>{css_cat}</style>
</head>
<body>
{HEADER}
<main>
  <p class="bc"><a href="/">Inicio</a> › <a href="/ventas/">Ventas</a> › {CAT_NOME}</p>
  <h1>{CAT_NOME} (Britagem y Chancado)</h1>
  <p class="lead">Línea completa de trituración {MARCA}: alimentadores, trituradoras de mandíbulas, cono e impacto, areneras de eje vertical, cribas vibratorias, cintas transportadoras y plantas móviles o modulares, de 25 a 2.000 t/h.</p>
  <div class="ayuda"><p><strong>¿Cono o impacto en la secundaria?</strong> Basalto y granito son abrasivos: cono, con menor costo de desgaste. Caliza y hormigón reciclado: impacto, con mejor forma de grano y más fino.</p></div>
  <h2>Equipos disponibles</h2>
  <ul class="prods">{itens}</ul>
  <h2>Disponibilidad y asesoramiento</h2>
  <p>GNH importa y distribuye equipos de trituración en Paraguay, con asesoramiento técnico para dimensionar la línea según el material, la producción objetivo y las fracciones a producir. Atendemos en español y portugués.</p>
  <p><a class="cta" href="{wa('Hola, quiero consultar sobre equipos de trituración')}" target="_blank" rel="noopener">Consultar por WhatsApp</a></p>
</main>
<footer>{FOOTER}</footer>
</body>
</html>'''
d = NU / 'ventas' / CAT_SLUG; d.mkdir(exist_ok=True); (d / 'index.html').write_text(cat, encoding='utf-8')
print('linha + categoria ok')

# ---------- 5. fichas HTML + PDF ----------
fb = (NU / 'fichas/camion-volquete-orugas.html').read_text(encoding='utf-8')
css_ficha = fb.split('<style>')[1].split('</style>')[0] + '\ntable.multi{width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0 4px}table.multi th,table.multi td{border-bottom:1px solid var(--hair);padding:6px 8px;text-align:left;vertical-align:top}table.multi th{background:#f4f6fa;color:var(--navy);font-size:11.5px}\n'
LOGO_FICHA = b64(NU / 'img/logo-ficha-sola.png')
CSSP = (REPO / 'gen-fichas-plataformas.py').read_text(encoding='utf-8').split('CSS = """')[1].split('"""')[0]
CSSP = CSSP.replace('@page{size:A4;margin:0}','@page{size:A4;margin:0 0 16mm 0}')
CSSP += '\ntable.multi td,table.multi th{font-size:7.6pt;padding:3pt 4pt;text-align:left;vertical-align:top}table.multi th{background:#f4f6fa;color:#14213D;border-bottom:1pt solid #14213D}table.multi td:first-child{width:auto;font-weight:400;background:none;color:#1e2733}table.multi td.g{font-weight:700;color:#14213D;background:#fff3ea}\n.photo img{max-height:170pt}\nh3{font-size:9pt;color:#14213D;margin:10pt 0 3pt}\n'
def tabelas_pdf(chaves):
    if isinstance(chaves, str): chaves = (chaves,)
    out = []
    for k in chaves:
        d = DADOS[k]; ncol = len(d['cols']); rows = []
        for titulo, rs in d['grupos']:
            if titulo: rows.append(f'<tr><td class="g" colspan="{ncol}">{esc(titulo)}</td></tr>')
            rows += ['<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in r) + '</tr>' for r in rs]
        t = f'<table class="multi"><thead><tr>' + ''.join(f'<th>{esc(c)}</th>' for c in d['cols']) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
        if len(chaves) > 1: t = f'<h3>{esc(d["nome"])}</h3>' + t
        if d.get('nota'): t += f'<p class="eq" style="font-size:8pt;color:#5b6472">{esc(d["nota"])}</p>'
        out.append(t)
    return ''.join(out)
FOOTER_PDF = ('<div style="width:100%;font-size:7pt;color:#8a93a3;text-align:center;font-family:Arial">gnhorizons.com &middot; WhatsApp +595 995 360060 &middot; P&aacute;gina <span class="pageNumber"></span> de <span class="totalPages"></span></div>')
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome'); pg_ = br.new_page()
    for p in EQUIPOS:
        slug = p['slug']; vent = ''.join(f'<li>{esc(v)}</li>' for v in p.get('ventajas', []))
        ficha = f'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(p['nome'])} {MARCA} | Ficha Técnica GNH</title>
<meta name="description" content="{esc(p['note'])}">
<link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&f[]=general-sans@400,500,600&display=swap" rel="stylesheet">
<style>{css_ficha}</style>
</head><body>
<div class="sheet">
  <div class="top">
    <div class="brand-row">
      <img src="data:image/png;base64,{LOGO_FICHA}" alt="GNH" style="height:58px;width:auto">
      <div class="doc-tag"><span class="dt">Ficha Técnica</span><span class="fam">{esc(p['chip'])}</span></div>
    </div>
    <div class="rule"></div>
    <div class="title-block">
      <h1>{esc(p['nome'])}</h1>
      <p class="sub">{esc(p['note'])}</p>
      <div class="actions"><a class="btn btn-pdf" href="pdf/{slug}.pdf" download>⬇ PDF ficha técnica</a>
        <a class="btn btn-wa" href="{wa('Hola, quiero consultar sobre: ' + p['nome'])}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
        <a class="btn btn-back" href="../ventas/{slug}/">← Volver al producto</a>
      </div>
    </div>
  </div>
  <div class="body">
    <figure style="margin:18px 0 6px"><img src="../img/prod/{slug}.png" alt="{esc(p['nome'])}" loading="lazy" style="width:100%;max-width:520px;height:auto;border:1px solid var(--hair)"></figure>
    <div class="lead"><p>{esc(p['lead'])}</p></div>
    <h2>Ventajas</h2><ul>{vent}</ul>
    <h2>Modelos y especificaciones</h2>{tabelas_html(p['dados'], cls='multi')}
    <p class="kv-extra">Datos del catálogo del fabricante ({MARCA}). La capacidad varía con el material y la granulometría de entrada. Sujetos a confirmación de configuración y disponibilidad antes de la compra.</p>
  </div>
</div>
</body>
</html>'''
        (NU / 'fichas' / f'{slug}.html').write_text(ficha, encoding='utf-8')
        kp = ''.join(f'<div><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in p['kpis'])
        foto = b64(NU / 'img/prod' / f'{slug}.png')
        html_pdf = f'''<div class="head"><img src="data:image/png;base64,{LOGO_FICHA}" alt="GNH">
<div class="r"><div class="ft">FICHA T&Eacute;CNICA</div><span class="chip">{esc(p['chip']).upper()}</span></div></div>
<h1>{esc(p['nome']).upper()}</h1>
<p class="sub">{esc(p['note'])}</p>
<div class="kpis">{kp}</div>
<div class="photo"><img src="data:image/png;base64,{foto}" alt=""></div>
<h2>Descripci&oacute;n</h2><p class="eq">{esc(p['lead'])}</p>
<h2>Ventajas</h2><p class="eq">{esc(' · '.join(v.rstrip('.') for v in p.get('ventajas', [])))}.</p>
<h2>Modelos y especificaciones</h2>{tabelas_pdf(p['dados'])}
<div class="final">
 <b>GNH — Generando Nuevos Horizontes</b> &middot; Av. Rep&uacute;blica del Per&uacute; km 7, Ciudad del Este &middot; Acceso Sur, &Ntilde;emby, Paraguay<br>
 WhatsApp <b>+595 995 360060</b> &middot; comercial@gnhorizons.com &middot; gnhorizons.com
 <div class="disc">Datos transcritos del cat&aacute;logo del fabricante {MARCA}. La capacidad var&iacute;a con el material y la granulometr&iacute;a de entrada. Sujetos a cambio sin previo aviso; confirm&aacute; configuraci&oacute;n, plazos y disponibilidad con nuestro equipo t&eacute;cnico antes de la compra.</div></div>'''
        pg_.set_content(f'<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><style>{CSSP}</style></head><body>{html_pdf}</body></html>')
        out = NU / 'fichas/pdf' / f'{slug}.pdf'
        pg_.pdf(path=str(out), format='A4', print_background=True, display_header_footer=True, header_template='<span></span>', footer_template=FOOTER_PDF, margin={'top': '0mm', 'bottom': '16mm'})
        print(f'  ficha {slug:40} pdf {out.stat().st_size//1024} KB')
    br.close()

# ---------- 6. bundle ----------
idx = NU / 'ventas/index.html'; ih = idx.read_text(encoding='utf-8')
atual = re.search(r'assets/(ventas-[A-Za-z0-9_-]+\.js)', ih).group(1); bp = NU / 'assets' / atual; s = bp.read_text(encoding='utf-8')
if 'Áridos y Trituración' in s:
    print('bundle já tem o grupo — pulando'); novo=atual
else:
    def js(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    entradas = ','.join('{name:%s,brand:%s,img:%s,note:%s,tags:%s}' % (js(p['nome']), js(MARCA), js(f'../img/prod/{p["slug"]}.png'), js(p['note']), js(p['tags'])) for p in PRODUTOS)
    grupo = '{title:%s,products:[%s]},' % (js(GRUPO), entradas)
    alvo = '{title:"Industria",products:['; assert s.count(alvo) == 1; s = s.replace(alvo, grupo + alvo)
    hmap = ''.join('%s:{h:%s,r:%s},' % (js(p['nome']), js(resumo_H(p)['h']), js(resumo_H(p)['r'])) for p in PRODUTOS)
    assert s.count('H={') == 1; s = s.replace('H={', 'H={' + hmap, 1)
    novo = 'ventas-' + hashlib.md5(s.encode()).hexdigest()[:8] + '.js'
    (NU / 'assets' / novo).write_text(s, encoding='utf-8'); bp.unlink()
    assert ih.count(atual) == 1; idx.write_text(ih.replace(atual, novo), encoding='utf-8')
print('bundle', atual, '->', novo)

# ---------- 7. sitemap ----------
sm = NU / 'sitemap.xml'; x = sm.read_text(encoding='utf-8')
urls = [f'https://gnhorizons.com/ventas/{CAT_SLUG}/'] + [f'https://gnhorizons.com/ventas/{p["slug"]}/' for p in PRODUTOS] + [f'https://gnhorizons.com/fichas/{p["slug"]}.html' for p in EQUIPOS]
novos = ''.join(f'  <url><loc>{u}</loc><changefreq>monthly</changefreq><priority>{"0.7" if "/fichas/" in u else "0.8"}</priority></url>\n' for u in urls if u not in x)
sm.write_text(x.replace('</urlset>', novos + '</urlset>'), encoding='utf-8')
print('sitemap +', novos.count('<url>'))
