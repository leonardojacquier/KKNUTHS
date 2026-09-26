#!/usr/bin/env python3
"""
Gera uma página estática por marca a partir do productos.json.

Por que existe: o catálogo (1.018 produtos) vive num JSON carregado por
JavaScript — nenhum crawler lê. No HTML servido "Portinari" aparece 1 vez;
no JSON, 3.480. Estas páginas põem os NOMES dos produtos em HTML de verdade,
que é o que o Google e as IAs conseguem indexar.

Uso:  python3 build-marcas.py ../../assets/kasteller2
Idempotente: reescreve as páginas e o sitemap do zero a cada execução.
"""
import json, os, re, sys, unicodedata
from html import escape

BASE = 'https://kasteller.com.py'
WA = 'https://wa.me/595985869600'

# Uma linha por marca: como ela se apresenta e o que faz dela diferente.
# Sem isso as páginas viram texto repetido — que o Google trata como conteúdo raso.
PERFIL = {
    'Portinari': 'Marca brasileña de porcelanatos de alto padrón, referencia en diseño '
                 'y en reproducción de mármoles y piedras naturales.',
    'Ceusa':     'Fábrica brasileña conocida por sus revestimientos de autor y por las '
                 'colaboraciones con estudios de arquitectura y diseño.',
    'Castelli':  'Porcelanatos brasileños con foco en formatos grandes y acabados '
                 'técnicos para obra residencial y comercial.',
    'Roca':      'Marca de cerámica y porcelanato con presencia global, línea completa '
                 'para pisos y paredes.',
    'Incepa':    'Revestimientos cerámicos brasileños, tradición en baños y cocinas.',
    'Castelatto':'Especialista en piedras y revestimientos artesanales de hormigón, '
                 'con textura y relieve para paredes de carácter.',
}

def slug(s):
    s = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')

def topo(counter, n=6):
    return [k for k, _ in sorted(counter.items(), key=lambda kv: -kv[1]) if k][:n]

def pagina(marca, prods, raiz):
    sl = slug(marca)
    url = f'{BASE}/marcas/{sl}/'
    total = len(prods)
    formatos = topo({p['formato']: sum(1 for x in prods if x['formato'] == p['formato'])
                     for p in prods if p.get('formato') and p['formato'] != 'VARIOS'})
    looks = topo({p['look']: sum(1 for x in prods if x['look'] == p['look'])
                  for p in prods if p.get('look') and p['look'] != 'otros'})
    acabados = topo({p['acabado']: sum(1 for x in prods if x['acabado'] == p['acabado'])
                     for p in prods if p.get('acabado')}, 5)

    desc = (f'{total} productos {marca} en Kasteller Revestimientos, Ciudad del Este. '
            + (f'Formatos {", ".join(formatos[:3])}. ' if formatos else '')
            + 'Consultá disponibilidad y precio por WhatsApp.')

    # JSON-LD: Brand + ItemList com os 30 primeiros (o suficiente para o Google
    # entender que é um catálogo, sem inflar o HTML com 580 entradas de dados)
    ld = {
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": f'{marca} — Kasteller Revestimientos', "url": url,
        "description": desc, "inLanguage": "es",
        "isPartOf": {"@type": "WebSite", "url": BASE + '/'},
        "about": {"@type": "Brand", "name": marca},
        "provider": {"@type": "HomeGoodsStore", "@id": BASE + '/#store'},
        "mainEntity": {"@type": "ItemList", "numberOfItems": total,
                       "itemListElement": [
                           {"@type": "ListItem", "position": i + 1, "name": p['nombre']}
                           for i, p in enumerate(prods[:30])]},
    }
    crumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": BASE + '/'},
        {"@type": "ListItem", "position": 2, "name": "Marcas", "item": BASE + '/marcas/'},
        {"@type": "ListItem", "position": 3, "name": marca, "item": url}]}

    cards = []
    for p in prods:
        meta = ' · '.join(x for x in [p.get('tipo'), p.get('acabado'),
                          p.get('formato') if p.get('formato') != 'VARIOS' else None] if x)
        img = (f'<img loading="lazy" decoding="async" src="../../{p["img"]}" alt="{escape(p["nombre"])} — {escape(marca)}">'
               if p.get('img') else '<span class="sinfoto">Consultar</span>')
        cards.append(
            f'<li class="p"><div class="ph">{img}</div>'
            f'<h3>{escape(p["nombre"])}</h3><p>{escape(meta)}</p></li>')

    otras = ''.join(f'<a href="../{slug(m)}/">{escape(m)}</a>' for m in raiz if m != marca)

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(marca)} en Paraguay — {total} productos | Kasteller Revestimientos</title>
<meta name="description" content="{escape(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:title" content="{escape(marca)} — Kasteller Revestimientos">
<meta property="og:description" content="{escape(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/og.jpg">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(crumb, ensure_ascii=False)}</script>
<link rel="stylesheet" href="../../fonts/fonts.css">
<style>
:root{{--black:#000;--white:#fff;--cream:#E8E1D7;--taupe:#544F4B}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',system-ui,sans-serif;background:var(--cream);color:var(--black);line-height:1.6}}
header{{background:var(--black);color:var(--cream);padding:18px 6vw}}
header a{{color:var(--cream);text-decoration:none;font-size:13px;letter-spacing:.18em;text-transform:uppercase}}
main{{max-width:1200px;margin:0 auto;padding:6vh 6vw 8vh}}
.bc{{font-size:12px;color:var(--taupe);margin-bottom:20px}}
.bc a{{color:var(--taupe)}}
h1{{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:clamp(34px,6vw,64px);line-height:1.05}}
.lead{{max-width:62ch;margin-top:14px;color:#3a3532;font-size:17px}}
.facts{{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0 8px}}
.facts span{{background:rgba(0,0,0,.06);padding:7px 14px;font-size:12px;letter-spacing:.06em;text-transform:uppercase}}
.cta{{display:inline-block;margin:22px 0 10px;background:var(--black);color:var(--cream);
  text-decoration:none;padding:15px 30px;font-size:12px;letter-spacing:.2em;text-transform:uppercase}}
h2{{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:30px;margin:44px 0 18px}}
ul.grid{{list-style:none;display:grid;gap:22px;
  grid-template-columns:repeat(auto-fill,minmax(190px,1fr))}}
.p .ph{{aspect-ratio:4/5;background:#ded6ca;overflow:hidden;display:grid;place-items:center}}
.p img{{width:100%;height:100%;object-fit:cover;display:block}}
.sinfoto{{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--taupe)}}
.p h3{{font-size:14px;font-weight:500;margin-top:10px}}
.p p{{font-size:12px;color:var(--taupe)}}
.otras{{margin-top:56px;padding-top:26px;border-top:1px solid rgba(0,0,0,.12)}}
.otras a{{display:inline-block;margin:0 16px 10px 0;color:var(--black);font-size:13px}}
footer{{background:var(--black);color:rgba(232,225,215,.6);padding:34px 6vw;font-size:12px}}
footer a{{color:var(--cream)}}
</style>
</head>
<body>
<header><a href="../../">← Kasteller Revestimientos</a></header>
<main>
  <p class="bc"><a href="../../">Inicio</a> › <a href="../../#buscador">Catálogo</a> › {escape(marca)}</p>
  <h1>{escape(marca)}</h1>
  <p class="lead">{escape(PERFIL.get(marca, ''))} En Kasteller trabajamos {total} productos
  de la marca, disponibles para proyectos en Paraguay y en la frontera con Brasil.</p>
  <div class="facts">
    <span>{total} productos</span>
    {''.join(f'<span>{escape(f)}</span>' for f in formatos[:4])}
    {''.join(f'<span>{escape(a)}</span>' for a in acabados[:3])}
  </div>
  <a class="cta" href="{WA}?text={escape('Hola, quiero información de los productos ' + marca)}"
     target="_blank" rel="noopener">Consultar por WhatsApp</a>

  <h2>Catálogo {escape(marca)}</h2>
  <ul class="grid">
{chr(10).join(cards)}
  </ul>

  <div class="otras"><strong>Otras marcas:</strong><br>{otras}</div>
</main>
<footer>
  <p><strong>Kasteller Revestimientos</strong> · Av. República del Perú km 7, Ciudad del Este, Paraguay ·
  WhatsApp <a href="{WA}">+595 985 869 600</a> · <a href="../../">Ver catálogo completo</a></p>
</footer>
</body>
</html>
'''

def main():
    raiz_dir = sys.argv[1] if len(sys.argv) > 1 else '../../assets/kasteller2'
    dados = json.load(open(os.path.join(raiz_dir, 'buscador/productos.json'), encoding='utf-8'))
    prods = dados['productos']

    marcas = {}
    for p in prods:
        marcas.setdefault(p['marca'], []).append(p)
    # marca sem produto viraria página vazia — conteúdo raso penaliza o site inteiro
    marcas = {m: v for m, v in sorted(marcas.items(), key=lambda kv: -len(kv[1])) if len(v) >= 5}

    urls = [f'{BASE}/']
    for marca, lista in marcas.items():
        d = os.path.join(raiz_dir, 'marcas', slug(marca))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(pagina(marca, lista, list(marcas)))
        urls.append(f'{BASE}/marcas/{slug(marca)}/')
        print(f'  /marcas/{slug(marca)}/  — {len(lista)} produtos')

    # índice das marcas
    os.makedirs(os.path.join(raiz_dir, 'marcas'), exist_ok=True)
    itens = ''.join(
        f'<li><a href="{slug(m)}/"><b>{escape(m)}</b><span>{len(v)} productos</span></a></li>'
        for m, v in marcas.items())
    ld = {"@context": "https://schema.org", "@type": "CollectionPage",
          "name": "Marcas — Kasteller Revestimientos", "url": f'{BASE}/marcas/',
          "hasPart": [{"@type": "Brand", "name": m} for m in marcas]}
    with open(os.path.join(raiz_dir, 'marcas', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marcas de porcelanato y revestimiento | Kasteller — Ciudad del Este</title>
<meta name="description" content="Las marcas que representamos en Kasteller Revestimientos: {escape(', '.join(marcas))}. {len(prods)} productos en catálogo, Ciudad del Este, Paraguay.">
<link rel="canonical" href="{BASE}/marcas/">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<link rel="stylesheet" href="../fonts/fonts.css">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',system-ui,sans-serif;background:#E8E1D7;color:#000;line-height:1.6}}
header{{background:#000;padding:18px 6vw}} header a{{color:#E8E1D7;text-decoration:none;font-size:13px;letter-spacing:.18em;text-transform:uppercase}}
main{{max-width:1000px;margin:0 auto;padding:8vh 6vw}}
h1{{font-family:'Cormorant Garamond',serif;font-weight:500;font-size:clamp(34px,6vw,60px)}}
ul{{list-style:none;display:grid;gap:14px;margin-top:34px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}}
a.card,li a{{display:flex;justify-content:space-between;align-items:baseline;background:#fff;
  padding:22px 24px;text-decoration:none;color:#000}}
li a b{{font-size:19px;font-weight:500}} li a span{{font-size:12px;color:#544F4B}}
</style></head><body>
<header><a href="../">← Kasteller Revestimientos</a></header>
<main>
<h1>Marcas que representamos</h1>
<p style="max-width:60ch;margin-top:12px">Porcelanatos y revestimientos de fábricas brasileñas de primera línea,
con {len(prods)} productos en catálogo. Showroom en Ciudad del Este.</p>
<ul>{itens}</ul>
</main></body></html>''')
    urls.insert(1, f'{BASE}/marcas/')

    with open(os.path.join(raiz_dir, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            pri = '1.0' if u.endswith('.py/') else '0.8'
            f.write(f'  <url><loc>{u}</loc><changefreq>weekly</changefreq><priority>{pri}</priority></url>\n')
        f.write('</urlset>\n')

    print(f'\nsitemap: {len(urls)} URLs (era 1)')

if __name__ == '__main__':
    main()
