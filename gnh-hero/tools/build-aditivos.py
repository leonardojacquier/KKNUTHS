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

# ---------- plantilla de ficha HTML (hoja técnica clara, membrete GNH) ----------
FICHA_TPL = """<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Ficha Técnica | GNH</title>
<meta name="description" content="{meta}">
<link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&f[]=general-sans@400,500,600&display=swap" rel="stylesheet">
<style>
:root{{--navy:#14213D;--ink:#1e2733;--orange:#F26D21;--gold:#C9A961;--line:#D8DEE8;--hair:#E6EAF0;--fam:{color}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'General Sans','Liberation Sans','Helvetica Neue',Arial,sans-serif;color:var(--ink);background:#EEF1F5;line-height:1.6}}
.sheet{{max-width:860px;margin:0 auto;background:#fff;min-height:100vh;box-shadow:0 30px 80px -40px rgba(15,23,42,.3)}}
.top{{background:#fff;padding:30px 46px 0}}
.brand-row{{display:flex;align-items:center;justify-content:space-between;gap:18px;padding-bottom:18px}}
.brand-row img{{height:58px;width:auto}}
.doc-tag{{text-align:right}}
.doc-tag .dt{{display:block;font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-weight:800;font-size:17px;letter-spacing:.24em;text-transform:uppercase;color:var(--navy)}}
.doc-tag .fam{{display:inline-flex;align-items:center;gap:7px;margin-top:7px;font-size:10.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:#5B6472;border:1px solid var(--line);border-radius:3px;padding:3px 10px}}
.doc-tag .fam::before{{content:'';width:8px;height:8px;border-radius:50%;background:var(--fam)}}
.rule{{height:2px;background:var(--navy);position:relative}}
.rule::after{{content:'';position:absolute;left:0;top:2px;height:1px;width:100%;background:var(--gold)}}
.title-block{{padding:24px 0 20px;border-bottom:1px solid var(--line)}}
h1{{font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-weight:800;font-size:clamp(24px,4vw,34px);letter-spacing:-.01em;text-transform:uppercase;color:var(--navy);line-height:1.06}}
.sub{{color:#5B6472;margin-top:6px;font-size:15.5px}}
.actions{{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap;padding-bottom:8px}}
.btn{{display:inline-flex;align-items:center;gap:8px;min-height:42px;padding:9px 20px;border-radius:6px;font-weight:700;font-size:13.5px;text-decoration:none;font-family:'Satoshi','Liberation Sans',Arial,sans-serif}}
.btn-pdf{{background:var(--navy);color:#fff}}
.btn-wa{{background:#22c15e;color:#fff}}
.btn-back{{background:#fff;color:var(--navy);border:1.5px solid var(--line)}}
.body{{padding:6px 46px 26px}}
.body h2{{font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-size:12px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--navy);margin:26px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--hair);display:flex;align-items:center;gap:10px}}
.body h2::before{{content:'';width:3px;height:13px;background:var(--navy);flex-shrink:0}}
.body p{{font-size:13.2px;color:#3c4657;line-height:1.7;margin:0 0 10px}}
.body .lead p{{font-size:14px;color:#2c3646;line-height:1.75}}
.body ul{{list-style:none;margin:2px 0 12px;padding:0}}
.body li{{position:relative;padding-left:17px;margin-bottom:7px;font-size:13.2px;color:#3c4657;line-height:1.6}}
.body li::before{{content:'';position:absolute;left:0;top:8px;width:5px;height:5px;background:var(--navy)}}
.data{{border:1px solid var(--hair);border-top:2px solid var(--navy)}}
.dr{{padding:6px 16px;font-size:12.8px;color:#3c4657;border-bottom:1px solid var(--hair)}}
.dr:nth-child(odd){{background:#F7F9FB}}
.dr:last-child{{border-bottom:0}}
table.kv{{width:100%;border-collapse:collapse;border:1px solid var(--hair);border-top:2px solid var(--navy)}}
.kv th{{width:31%;text-align:left;font-weight:600;color:var(--navy);background:#F4F6FA;padding:8px 18px;font-size:12.6px;border-bottom:1px solid var(--hair);border-right:1px solid var(--hair);vertical-align:top}}
.kv td{{padding:8px 18px;font-size:12.8px;color:#3c4657;border-bottom:1px solid var(--hair)}}
.kv tr:last-child th,.kv tr:last-child td{{border-bottom:0}}
.kv-extra{{font-size:11.5px;color:#8a93a3;margin-top:6px;font-style:italic}}
.meta{{display:flex;gap:18px;margin-top:10px;font-size:12.5px;color:#7c8698}}
.meta b{{color:var(--navy);font-weight:600}}
pre.raw{{white-space:pre-wrap;font:13.2px/1.65 'General Sans',sans-serif;color:#3c4657;background:#FAFBFD;border:1px solid var(--line);border-left:3px solid var(--navy);padding:18px 22px}}
.foot{{padding:18px 46px 22px;border-top:2px solid var(--navy);font-size:11.5px;color:#5B6472}}
.foot-grid{{display:grid;grid-template-columns:1.1fr 1.3fr 1.1fr;gap:28px;align-items:start}}
.f-col .f-label{{font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-size:9.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#9aa3b2;margin-bottom:7px}}
.f-left img{{height:32px;width:auto}}
.f-left .excl{{font-family:'Satoshi','Liberation Sans',Arial,sans-serif;font-weight:700;color:var(--navy);font-size:11.5px;line-height:1.45;margin-top:7px}}
.f-mid{{font-size:11px;line-height:1.65}}
.f-mid b{{color:var(--navy)}}
.f-right{{text-align:right;font-size:10.5px;line-height:1.5}}
.f-right img{{height:26px;width:auto;margin-bottom:7px}}
.foot .note{{font-style:italic;color:#8a93a3;font-size:10.5px;margin-top:12px;padding-top:9px;border-top:1px solid var(--hair);text-align:center}}
.foot b{{color:var(--navy)}}
@media print{{
  body{{background:#fff}} .sheet{{box-shadow:none;max-width:none}} .actions{{display:none}}
  .top{{padding:0 4px}} .body{{padding:4px 4px 10px}}
  .rule{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  .doc-tag .fam{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  pre.raw{{background:#fff;border:1px solid var(--line);border-left:3px solid var(--navy);font-size:12.6px}}
  .foot{{padding:14px 4px 0}}
  .body h2{{page-break-after:avoid}}
  .body li,.dr{{page-break-inside:avoid}}
  .data,table.kv{{page-break-inside:avoid;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  .kv th{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  .body h2::before,.body li::before{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
}}
@media(max-width:640px){{ .top,.body,.foot{{padding-left:20px;padding-right:20px}} .brand-row img{{height:44px}} }}
</style></head><body>
<div class="sheet">
  <header class="top">
    <div class="brand-row">
      {logo_html}
      <div class="doc-tag"><span class="dt">Ficha Técnica</span><span class="fam">{family_label}</span></div>
    </div>
    <div class="rule"></div>
    <div class="title-block">
      <h1>{name}</h1>
      {sub_html}
      {meta_html}
    </div>
    <div class="actions">
      <a class="btn btn-pdf" href="pdf/{slug}.pdf" download>⬇ Descargar PDF</a>
      <a class="btn btn-wa" href="https://wa.me/595995360060?text={wa}" target="_blank" rel="noopener">Consultar por WhatsApp</a>
      <a class="btn btn-back" href="../ventas/">← Volver al catálogo</a>
    </div>
  </header>
  <main class="body">
    {body_html}
  </main>
  <footer class="foot">
    <div class="foot-grid">
      <div class="f-col f-left">
        <p class="f-label">Distribuidor exclusivo</p>
        {logo_foot}
        <p class="excl">Distribuidores exclusivos de<br>Camargo Química en Paraguay</p>
      </div>
      <div class="f-col f-mid">
        <p class="f-label">Contacto</p>
        <p>Av. República del Perú km 7, Ciudad del Este<br>Acceso Sur, Ñemby — Paraguay</p>
        <p>WhatsApp <b>+595 995 360060</b><br>comercial@gnhorizons.com &nbsp;·&nbsp; gnhorizons.com</p>
      </div>
      <div class="f-col f-right">
        <p class="f-label" style="text-align:right">Fabricante</p>
        {camargo_html}
        <p>Información técnica proporcionada<br>por el fabricante — Camargo Química</p>
      </div>
    </div>
    <p class="note">Documento orientativo. Realice pruebas preliminares y consulte a nuestro equipo técnico antes de la aplicación.</p>
  </footer>
</div>
</body></html>
"""

def _b64img(path, height, alt) -> str:
    import base64
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" style="height:{height}px;width:auto">'

def logo_html() -> str:
    """Logo GNH oficial del membrete (public/img/logo-oficial.png embebida en base64)."""
    png = ROOT / 'public' / 'img' / 'logo-oficial.png'
    if png.exists():
        return _b64img(png, 58, 'GNH — Generando Nuevos Horizontes')
    return '<strong style="font-family:Satoshi,Arial;font-size:28px;color:#14213D">GNH</strong>'

def camargo_html() -> str:
    """Logo Camargo Química del pie (public/img/logo-camargo.png embebida)."""
    png = ROOT / 'public' / 'img' / 'logo-camargo.png'
    if png.exists():
        return _b64img(png, 30, 'Camargo Química')
    return ''

def clean_raw(text: str) -> str:
    body = text
    fence = re.search(r'```(.*)```', text, re.S)
    if fence: body = fence.group(1)
    body = re.sub(r'^\s*FICHA T[EÉ]CNICA\s*$', '', body, flags=re.M | re.I)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return body.replace('&', '&amp;').replace('<', '&lt;')

# ---------- parser estructural: del volcado OCR a secciones limpias ----------
_esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;')
_JUNK = [
    re.compile(r'^FICHA T[EÉ]CNICA$', re.I),
    re.compile(r'P[aá]gina:?\s*\d+\s*de\s*\d+', re.I),
    re.compile(r'^[-–_]{2,}$'),
    re.compile(r'^\*\*Fuente', re.I),
    re.compile(r'^https?://', re.I),
    re.compile(r'^#'),
]

def parse_sections(raw: str):
    """divide el texto en (título, líneas) usando los encabezados en MAYÚSCULAS;
    quita basura de paginación. Devuelve (secciones, fecha_emisión)."""
    body = raw
    fence = re.search(r'```(.*)```', raw, re.S)
    if fence: body = fence.group(1)
    sections, cur, cur_title, emis = [], [], None, None
    def flush():
        nonlocal cur
        if any(l.strip() for l in cur): sections.append((cur_title, cur))
        cur = []
    for l in body.splitlines():
        s = l.strip()
        if not s: cur.append(''); continue
        if any(rx.search(s) for rx in _JUNK): continue
        m = re.search(r'(Emitido|Emisi[oó]n):\s*([0-9][0-9/.\-]+)', s)
        if m: emis = emis or m.group(2)
        if re.search(r'(Emitido|Emisi[oó]n|Edici[oó]n):', s) and len(s) < 100: continue
        if re.fullmatch(r'(?i)datos\s+t[eé]cnicos:?', s):
            flush(); cur_title = 'Datos Técnicos'; continue
        if (s == s.upper() and 6 <= len(s) <= 64 and not s.startswith('•')
                and re.fullmatch(r"[A-ZÁÉÍÓÚÑÜ0-9 ,.\-–/()':]+", s) and any(c.isalpha() for c in s)):
            flush(); cur_title = s.capitalize(); continue
        cur.append(s)
    flush()
    return sections, emis

# atributos conocidos de las tablas técnicas (para reconstruir clave→valor del OCR)
_KV_KEYS = ['base química', 'base quimica', 'punto de congelación', 'punto de congelacion',
            'contenido de sólidos', 'contenido de solidos', 'función', 'funcion', 'aspecto',
            'densidad', 'viscosidad', 'apariencia', 'olor', 'validez', 'caducidad', 'solubilidad',
            'embalaje', 'envase', 'presentación', 'presentacion', 'rendimiento', 'dosificación',
            'dosificacion', 'dosis', 'color', 'ph']

def parse_kv(lines):
    """reconstruye pares clave→valor: el OCR intercala las dos columnas de la tabla
    original (fragmentos sueltos tipo 'Comercializado', 'sobre de 870 gramos')."""
    pairs, extras = [], []
    for raw in lines:
        s = re.sub(r'\s+', ' ', raw).strip(' :;')
        if not s: continue
        ns = norm(s)
        hit = next((k for k in sorted(_KV_KEYS, key=len, reverse=True) if ns.startswith(k)), None)
        if hit:
            key = s[:len(hit)]
            val = s[len(hit):].strip(' :–—-')
            if norm(key).startswith('funcion'):
                val = re.sub(r'^(de |del )', '', val, flags=re.I)
            if val: val = val[0].upper() + val[1:]
            pairs.append([key if key[:1].isupper() else key.capitalize(), val])
        else:
            # fragmento suelto → al campo de embalaje si habla de envases; si no, al último vacío
            target = None
            if re.search(r'bombona|sobre|kg\b|litro|balde|tambor|granel|envase|comercializado|bolsa|caja|contenedor', ns):
                target = next((p for p in pairs if norm(p[0]).startswith(('embalaje', 'envase', 'presentacion'))), None)
            if target is None:
                empties = [p for p in pairs if not p[1]]
                target = empties[-1] if empties else (pairs[-1] if pairs else None)
            if target is not None:
                target[1] = (target[1] + ' ' + s).strip()
                if target[1]: target[1] = target[1][0].upper() + target[1][1:]
            else:
                extras.append(s)
    return [(k, v or '—') for k, v in pairs], extras

def sections_html(sections) -> str:
    out = []
    for title, lines in sections:
        is_data = title and re.search(r'(?i)datos t[eé]cnicos', title)
        if is_data:
            pairs, extras = parse_kv(lines)
            if len(pairs) >= 2:
                rows = ''.join(f'<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>' for k, v in pairs)
                extra_html = ''.join(f'<p class="kv-extra">{_esc(x)}</p>' for x in extras)
                out.append(f'<section><h2>{_esc(title)}</h2><table class="kv"><tbody>{rows}</tbody></table>{extra_html}</section>')
            else:
                rows = ''.join(f'<div class="dr">{_esc(l)}</div>' for l in lines if l.strip())
                out.append(f'<section><h2>{_esc(title)}</h2><div class="data">{rows}</div></section>')
            continue
        parts, para, ul = [], [], []
        def flush_para():
            nonlocal para
            if para: parts.append(f'<p>{_esc(" ".join(para))}</p>'); para = []
        def flush_ul():
            nonlocal ul
            if ul: parts.append('<ul>' + ''.join(f'<li>{_esc(x)}</li>' for x in ul) + '</ul>'); ul = []
        for l in lines:
            s = l.strip()
            if not s: flush_para(); continue
            if s.startswith('•') or re.match(r'^[-–]\s+', s):
                flush_para(); ul.append(re.sub(r'^[•\-–]\s*', '', s))
            else:
                flush_ul(); para.append(s)
        flush_para(); flush_ul()
        body_html = ''.join(parts)
        if title: out.append(f'<section><h2>{_esc(title)}</h2>{body_html}</section>')
        else: out.append(f'<section class="lead">{body_html}</section>')
    return ''.join(out)

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
            secs, emis = parse_sections(g['ficha'])
            if len(secs) >= 2:
                body_html = sections_html(secs)
            else:  # respaldo: texto plano si el parser no encontró estructura
                body_html = f'<h2>Información del producto</h2><pre class="raw">{clean_raw(g["ficha"])}</pre>'
            meta_html = f'<div class="meta"><span><b>Emisión:</b> {emis}</span><span><b>Origen:</b> Camargo Química — Brasil</span></div>' if emis \
                        else '<div class="meta"><span><b>Origen:</b> Camargo Química — Brasil</span></div>'
            html = FICHA_TPL.format(
                name=name, meta=(desc or sub)[:150], color=color, family_label=fam_label,
                sub_html=f'<p class="sub">{sub}</p>' if sub else '',
                meta_html=meta_html, body_html=body_html,
                slug=slug, wa=wa.replace(' ', '%20'), logo_html=logo_html(),
                logo_foot=logo_html().replace('height:58px', 'height:30px'),
                camargo_html=camargo_html())
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
