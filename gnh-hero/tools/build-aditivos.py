#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Aditivos GNH
Lê os .md de gnh-hero/content/{fichas,paginas}/ (exportados do Drive) e gera:
  1. gnh-hero/public/fichas/<slug>.html   — ficha técnica con marca GNH (imprimible)
  2. gnh-hero/src/aditivos-data.ts        — catálogo + índice de búsqueda (client-side)
Los PDFs se generan aparte con tools/make-pdfs.js (Chromium print).
"""
import json, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # gnh-hero/
CONTENT = ROOT / 'content'
OUT_FICHAS = ROOT / 'public' / 'fichas'
OUT_TS = ROOT / 'src' / 'aditivos-data.ts'

# ---------- famílias: regras de classificação + visual ----------
FAMILIES = [
    # (key, label, color, test-regex sobre título+subtítulo+texto)
    ('fibras',            'Fibras',                       '#F59E0B', r'\bfibra'),
    ('pigmentos',         'Pigmentos',                    '#EC4899', r'pigment|ferrox'),
    ('pisos',             'Pisos industriales',           '#94A3B8', r'endurecedor|hardfloor|litio|lithium|densificador de piso|siltop'),
    ('impermeabilizantes','Impermeabilizantes',           '#14B8A6', r'impermeabiliz|cristaliz|seal|admix|impermix|estanque'),
    ('cura',              'Cura del concreto',            '#22C55E', r'\bcura\b|curador|curamix|membrana de cura|curado'),
    ('desmoldantes',      'Desmoldantes',                 '#64748B', r'desmold|desform'),
    ('control-fraguado',  'Aceleradores y retardadores',  '#8B5CF6', r'acelerador|accelera|retardador|stabilizer|estabilizador|fraguado'),
    ('selladores',        'Selladores y PU',              '#F26D21', r'\bpu\b|poliuretano|sellador|mastique'),
    ('limpieza',          'Limpieza y removedores',       '#10B981', r'\bbio\s?\d|remover|removedor|limpieza|desincrustante|acido bio'),
    ('plastificantes',    'Plastificantes',               '#3B82F6', r'plastificante|superplast|polifuncional|reductor de agua|vibroprensado|press.?mix|flow|plast'),
]
FAMILY_FALLBACK = ('otros', 'Especialidades', '#A78BFA')

# correcciones manuales (auditoría): el texto engaña a las reglas en estos casos
FAMILY_OVERRIDE = {
    'cq-robust-79': 'plastificantes',        # superplastificante 3ª gen (menciona fibras en el texto)
    'cq-robust-81': 'plastificantes',
    'cq-acryltop-hyper': 'pisos',            # resina acrílica de acabado de pisos
    'cq-acryltop-plus': 'pisos',
    'cq-admix-mv-100': 'plastificantes',     # modificador de viscosidad
    'cq-admix-n-20': 'plastificantes',       # desincorporador de aire
    'cq-sil-55': 'pisos',                    # silicato densificador de pisos
    'maturix': 'otros',                      # sensores de monitoreo (no es cura química)
    'cq-cola-35': 'otros',                   # adhesivo
}
NAME_OVERRIDE = {
    'q-flow-ultratech-90': 'CQ Flow Ultratech 90',
    'maturix': 'Maturix — Monitoreo de curado',
    'pigmentos-ferrox-color': 'Pigmentos Ferrox Color',
}
# páginas genéricas/duplicadas detectadas en la auditoría
DROP_SLUGS = {'tecnologias', 'authenty-piso', 'cq-concreto-seco-press-mix', 'cq-flow-ultratech',
              'cq-construcao', 'pu-cq-40-cinza-branco', 'cq-ferrox-color'}

# sinónimos ES → expanden las keywords de búsqueda
SYNONYMS = {
    'impermeabilizantes': ['humedad', 'infiltracion', 'filtracion', 'goteras', 'estanqueidad', 'tanque', 'cisterna', 'subsuelo'],
    'fibras': ['fisura', 'grieta', 'rajadura', 'retraccion', 'malla', 'refuerzo'],
    'pisos': ['piso industrial', 'galpon', 'pulido', 'brillo', 'polvo', 'desgaste', 'trafico'],
    'cura': ['curado', 'secado', 'proteccion', 'sol', 'viento', 'evaporacion'],
    'desmoldantes': ['molde', 'encofrado', 'desmolde', 'formaleta', 'prefabricado'],
    'control-fraguado': ['calor', 'verano', 'frio', 'invierno', 'tiempo de trabajo', 'transporte largo', 'rapido', 'lento'],
    'plastificantes': ['trabajabilidad', 'bombeo', 'fluidez', 'reduccion de agua', 'resistencia', 'hormigon', 'bloques', 'paver', 'adoquin', 'premoldado'],
    'selladores': ['junta', 'sellado', 'dilatacion', 'grieta estructural'],
    'pigmentos': ['color', 'colorear', 'rojo', 'negro', 'amarillo', 'ocre'],
    'limpieza': ['limpiar', 'concreto endurecido', 'residuo', 'mixer', 'betonera', 'hormigonera', 'equipo sucio', 'biodegradable'],
}

def norm(s: str) -> str:
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()

def unescape_md(t: str) -> str:
    return re.sub(r'\\([#*`\-\[\]().!_|>+])', r'\1', t)

def slugify(title: str) -> str:
    s = norm(title)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

def base_slug(slug: str) -> str:
    """agrupa variantes: -ficha-tecnica, -ficha-tecnica-01, sufijo -1 de duplicado.
    OJO: no cortar números de producto (superplast-1000 debe conservarse)."""
    s = re.sub(r'-ficha-tecnica(-\d+)?$', '', slug)
    s = re.sub(r'^ficha-tecnica-', '', s)
    s = re.sub(r'-\d$', '', s)          # solo un dígito final (duplicados tipo -1)
    return s

def product_name(text: str, fallback: str) -> str:
    # 1ª línea "# Nombre —/- Ficha Técnica" o título del PDF dentro del fence
    m = re.search(r'^#\s*(.+?)(?:\s*[-–—]\s*Ficha T[eé]cnica)?\s*$', text, re.M | re.I)
    n = ''
    if m:
        n = m.group(1).strip()
        if n.lower().startswith('ficha'):
            n = ''
    if not n:
        n = fallback.replace('-', ' ').upper()
    # título tipo slug ("cq-green-seal-ficha-tecnica-01") → nombre presentable
    if re.fullmatch(r'[a-z0-9][a-z0-9-]+', n):
        n = base_slug(slugify(n)).replace('-', ' ')
        n = ' '.join(w.upper() if (len(w) <= 3 or w.isdigit()) else w.capitalize() for w in n.split())
    # títulos largos de páginas ("Aditivo para X - CQ Stable - Línea…") → toma el segmento con el nombre comercial
    n_norm = n.replace(' – ', ' - ').replace(' — ', ' - ')
    if len(n_norm) > 28 and ' - ' in n_norm:
        parts = [p.strip() for p in n_norm.split(' - ')]
        cq = [p for p in parts if re.match(r'^(CQ|Q|PU|BIO)\b', p, re.I)]
        n = cq[0] if cq else min(parts, key=len)
    return n

def subtitle_of(text: str) -> str:
    """línea bajo el nombre en el bloque FICHA TÉCNICA (ej.: 'Densificador Superplastificante')."""
    m = re.search(r'FICHA T[EÉ]CNICA\s*\n+\s*.+?Emitido.*?\n\s*([^\n]{4,60}?)\s+P[aá]gina', text, re.S | re.I)
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip()
    return ''

def description_of(text: str) -> str:
    """primer párrafo descriptivo (después del encabezado del fence)."""
    body = text
    fence = re.search(r'```(.*)```', text, re.S)
    if fence:
        body = fence.group(1)
    paras, cur = [], []
    for line in body.splitlines():
        l = line.strip()
        if not l:
            if cur: paras.append(' '.join(cur)); cur = []
            continue
        if re.match(r'^(FICHA T|Emitido|Emisi[oó]n|Edici[oó]n|P[aá]gina|\*\*Fuente|https?://|#)', l, re.I): continue
        if re.search(r'P[aá]gina:?\s*\d+\s*de\s*\d+', l, re.I): continue
        if re.match(r'^[A-ZÁÉÍÓÚÑ ]{8,}$', l): break        # llegó a una sección en MAYÚSCULAS
        cur.append(l)
    if cur: paras.append(' '.join(cur))
    for p in paras:
        if len(p) > 90 and not re.search(r'P[aá]gina|Emitido|Edici[oó]n', p, re.I):
            return re.sub(r'\s+', ' ', p)[:420]
    return ''

def classify(name, subtitle, text):
    # 1º intento: solo nombre + subtítulo (más preciso); 2º: texto completo
    for probe in (norm(f'{name} {subtitle}'), norm(text[:1500])):
        for key, label, color, rx in FAMILIES:
            if re.search(rx, probe):
                return key, label, color
    return FAMILY_FALLBACK

def keywords_of(name, subtitle, text, fam_key):
    stop = {'producto','aplicacion','tecnica','ficha','camargo','quimica','camargoquimica','utiliza',
            'recomendamos','cuando','sobre','entre','despues','antes','desde','hasta','donde','pueden',
            'puede','condiciones','informacion','realizar','pruebas','manos','este','esta','para',
            'content','uploads','https','fuente','emitido','emision','edicion','pagina','consumidor',
            'boletin','deben','decir','cuales','cuanto','cuatro','darle','demas','anadir','anadirse',
            'agregue','ambos','busca','ayudar','aportar','actua','actuar','compara','comparativo'}
    # orden de relevancia: sinónimos de la familia → nombre → subtítulo → texto (sin orden alfabético)
    ordered = []
    def push(w):
        if w and w not in ordered and w not in stop: ordered.append(w)
    for w in SYNONYMS.get(fam_key, []): push(w)
    for w in re.findall(r'[a-z0-9]{3,}', norm(name)): push(w)
    for w in re.findall(r'[a-záéíóúñ]{5,}', norm(subtitle)): push(w)
    for w in re.findall(r'[a-záéíóúñ]{5,}', norm(text[:2500])): push(w)
    return ordered[:60]

def initials_of(name: str) -> str:
    """rótulo corto para el icono (nombre sin prefijo CQ, máx 16 chars)."""
    short = re.sub(r'^CQ\s+', '', name.strip(), flags=re.I).upper()
    return (short[:15] + '…') if len(short) > 16 else short

# ---------- plantilla de ficha HTML (marca GNH, imprimible) ----------
FICHA_TPL = """<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Ficha Técnica | GNH</title>
<meta name="description" content="{meta}">
<link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&f[]=general-sans@400,500,600&display=swap" rel="stylesheet">
<style>
:root{{--navy:#0F172A;--orange:#F26D21;--gold1:#F7E7B4;--gold2:#D4AF37;--gold3:#8C6A1D;--fam:{color}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'General Sans',system-ui,sans-serif;color:#1e2733;background:#F4F6F9;line-height:1.62}}
.sheet{{max-width:860px;margin:0 auto;background:#fff;min-height:100vh;box-shadow:0 30px 80px -40px rgba(15,23,42,.35)}}
.top{{background:linear-gradient(135deg,#0B1120,#13213f 55%,#0F172A);color:#fff;padding:34px 44px 28px;position:relative;overflow:hidden}}
.top::after{{content:'';position:absolute;left:0;right:0;bottom:0;height:3px;background:linear-gradient(90deg,var(--gold3),var(--gold2),var(--gold1),var(--gold2),var(--gold3))}}
.brand{{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:22px}}
.brand img{{height:40px;width:auto}}
.brand .tagline{{font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:rgba(255,255,255,.55);font-weight:600}}
.fam{{display:inline-flex;align-items:center;gap:8px;font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#fff;background:color-mix(in srgb,var(--fam) 32%,transparent);border:1px solid var(--fam);border-radius:100px;padding:5px 14px;margin-bottom:14px}}
h1{{font-family:'Satoshi',sans-serif;font-weight:800;font-size:clamp(26px,4.5vw,40px);letter-spacing:-.01em;text-transform:uppercase;line-height:1.04}}
.sub{{color:rgba(255,255,255,.72);margin-top:8px;font-size:16px}}
.actions{{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}}
.btn{{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:10px 22px;border-radius:100px;font-weight:700;font-size:14px;text-decoration:none;font-family:'Satoshi',sans-serif}}
.btn-pdf{{background:linear-gradient(135deg,var(--gold2),#c39b2a);color:#151515}}
.btn-wa{{background:#22c15e;color:#fff}}
.btn-back{{background:rgba(255,255,255,.1);color:#fff;border:1px solid rgba(255,255,255,.25)}}
.body{{padding:38px 44px 30px}}
.body h2{{font-family:'Satoshi',sans-serif;font-size:15px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--navy);border-left:4px solid var(--gold2);padding-left:12px;margin:28px 0 10px}}
.body p,.body li{{font-size:15px;color:#3c4657}}
.body ul{{padding-left:22px;display:grid;gap:5px}}
pre.raw{{white-space:pre-wrap;font:13.5px/1.65 'General Sans',sans-serif;color:#3c4657;background:#F8FAFC;border:1px solid #E5EAF1;border-radius:14px;padding:20px 22px}}
.foot{{padding:22px 44px 34px;border-top:1px solid #E5EAF1;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:12.5px;color:#7c8698}}
.foot b{{color:var(--navy)}}
@media print{{ body{{background:#fff}} .sheet{{box-shadow:none;max-width:none}} .actions{{display:none}} .top{{-webkit-print-color-adjust:exact;print-color-adjust:exact}} }}
@media(max-width:640px){{ .top,.body,.foot{{padding-left:22px;padding-right:22px}} }}
</style></head><body>
<div class="sheet">
  <header class="top">
    <div class="brand">
      <img src="https://gnhorizons.com/assets/images/logo_b.png" alt="GNH" onerror="this.style.display='none'">
      <span class="tagline">Generando Nuevos Horizontes</span>
    </div>
    <span class="fam">{family_label}</span>
    <h1>{name}</h1>
    {sub_html}
    <div class="actions">
      <a class="btn btn-pdf" href="pdf/{slug}.pdf" download>⬇ Descargar PDF</a>
      <a class="btn btn-wa" href="https://wa.me/595995360060?text={wa}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
      <a class="btn btn-back" href="../ventas/">← Volver al catálogo</a>
    </div>
  </header>
  <main class="body">
    <h2>Ficha técnica</h2>
    <pre class="raw">{raw}</pre>
  </main>
  <footer class="foot">
    <span><b>GNH — Generando Nuevos Horizontes E.A.S.</b> · Av. República del Perú km 7, Ciudad del Este · Acceso Sur, Ñemby · Paraguay</span>
    <span>WhatsApp +595 995 360060 · Documento orientativo; consulte a nuestro equipo técnico.</span>
  </footer>
</div>
</body></html>
"""

def clean_raw(text: str) -> str:
    body = text
    fence = re.search(r'```(.*)```', text, re.S)
    if fence: body = fence.group(1)
    body = re.sub(r'^\s*FICHA T[EÉ]CNICA\s*$', '', body, flags=re.M | re.I)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return body.replace('&', '&amp;').replace('<', '&lt;')

def main():
    fichas_dir, paginas_dir = CONTENT / 'fichas', CONTENT / 'paginas'
    OUT_FICHAS.mkdir(parents=True, exist_ok=True)

    groups = {}
    for folder, kind in ((fichas_dir, 'ficha'), (paginas_dir, 'pagina')):
        if not folder.exists(): continue
        for f in sorted(folder.glob('*.md')):
            slug = slugify(f.stem)
            if slug in ('fica-tecnica-teste', 'catalogo-online', 'catalogo-online-1', 'ebook-camargo-cura-de-concreto'): continue
            raw = unescape_md(f.read_text(encoding='utf-8', errors='replace'))
            b = base_slug(slug)
            key = b.replace('-', '')       # funde variantes de grafía: micro-fiber ↔ microfiber
            g = groups.setdefault(key, {'ficha': None, 'pagina': None, 'extra': [], 'slug': b})
            target = 'ficha' if 'ficha-tecnica' in slug else ('pagina' if kind == 'pagina' else 'ficha')
            if g[target] is None:
                g[target] = raw
                if target == 'ficha': g['slug'] = b   # el slug canónico sigue a la ficha
            else:
                g['extra'].append(raw)

    products, pages_meta = [], []
    for _key, g in sorted(groups.items()):
        b = g['slug']
        src = g['ficha'] or g['pagina'] or (g['extra'][0] if g['extra'] else '')
        if not src: continue
        if b in DROP_SLUGS: continue
        name = NAME_OVERRIDE.get(b) or product_name(src, b)
        sub = subtitle_of(src)
        desc = description_of(g['pagina'] or src) or sub
        fam_key, fam_label, color = classify(name, sub, src)
        if b in FAMILY_OVERRIDE:
            fk = FAMILY_OVERRIDE[b]
            match = [f for f in FAMILIES if f[0] == fk]
            fam_key, fam_label, color = match[0][:3] if match else FAMILY_FALLBACK
        kws = keywords_of(name, sub, src, fam_key)
        has_ficha = bool(g['ficha'])
        slug = b
        if has_ficha:
            wa = f'Hola, quiero consultar sobre {name}'
            html = FICHA_TPL.format(
                name=name, meta=(desc or sub)[:150], color=color, family_label=fam_label,
                sub_html=f'<p class="sub">{sub}</p>' if sub else '',
                slug=slug, wa=wa.replace(' ', '%20'),
                raw=clean_raw(g['ficha']))
            (OUT_FICHAS / f'{slug}.html').write_text(html, encoding='utf-8')
        products.append({
            'slug': slug, 'name': name, 'sub': sub, 'desc': desc[:260],
            'family': fam_key, 'familyLabel': fam_label, 'color': color,
            'initials': initials_of(name), 'kw': kws, 'ficha': has_ficha,
        })

    # descarta las páginas "de línea" (genéricas): describen la familia entera y
    # conviven con productos específicos (cq-desform vs cq-desform-a-435, etc.)
    slugs = {p['slug'] for p in products}
    def is_line_page(p):
        has_children = any(s != p['slug'] and s.startswith(p['slug'] + '-') for s in slugs)
        la_linea = bool(re.match(r'^la l[ií]nea', norm(p['desc'] or '')))
        return has_children and (la_linea or not p['ficha'])
    dropped = [p['name'] for p in products if is_line_page(p)]
    products = [p for p in products if not is_line_page(p)]
    if dropped: print('descartadas páginas de línea:', ', '.join(dropped))

    products.sort(key=lambda p: (p['familyLabel'], p['name']))
    ts = ('// GENERADO por tools/build-aditivos.py — no editar a mano\n'
          'export interface Aditivo { slug: string; name: string; sub: string; desc: string; family: string; familyLabel: string; color: string; initials: string; kw: string[]; ficha: boolean }\n'
          f'export const ADITIVOS: Aditivo[] = {json.dumps(products, ensure_ascii=False, indent=1)}\n')
    OUT_TS.write_text(ts, encoding='utf-8')

    fams = {}
    for p in products: fams[p['familyLabel']] = fams.get(p['familyLabel'], 0) + 1
    print(f'productos: {len(products)}  fichas html: {sum(1 for p in products if p["ficha"])}')
    for k, v in sorted(fams.items()): print(f'  {k}: {v}')

if __name__ == '__main__':
    main()
