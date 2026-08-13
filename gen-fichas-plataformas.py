# Gera as fichas técnicas em PDF das plataformas, lendo os dados do próprio
# gnh-redesign.html (via navegador) para que PDF e site nunca divirjam.
from playwright.sync_api import sync_playwright
import base64, html, mimetypes, os, pathlib

REPO = pathlib.Path(__file__).resolve().parent
OUT = REPO / 'assets/nuevo/fichas/pdf'
LOGO = base64.b64encode((REPO / 'assets/nuevo/img/logo-ficha.png').read_bytes()).decode()

ORDER_DIM = ['workHeight', 'platHeight', 'reach', 'platSize', 'lenStore', 'lenTrans',
             'width', 'height', 'wheelbase']
ORDER_PERF = ['cap', 'weight', 'speedStore', 'speedUp', 'boomRange', 'turret',
              'platRot', 'tail', 'turnRadius', 'grade', 'gradeUp', 'gradeDown', 'sideGrade']
ORDER_PW = ['battery', 'engine', 'enginePower', 'fuelTank', 'powerUnit', 'driveMotor',
            'aux', 'drive', 'hydTank', 'charger']

CSS = """
@page{size:A4;margin:0}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'DejaVu Sans',Arial,sans-serif;color:#1e2733;font-size:10.5pt;line-height:1.5;padding:34pt 40pt 30pt}
.head{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2.5pt solid #14213D;padding-bottom:12pt;margin-bottom:16pt}
.head img{height:44pt}
.head .r{text-align:right}
.head .ft{font-size:12pt;font-weight:700;letter-spacing:.25em;color:#14213D}
.chip{display:inline-block;margin-top:5pt;font-size:7.5pt;font-weight:700;letter-spacing:.18em;color:#14213D;border:.75pt solid #dbe2ec;border-radius:3pt;padding:2.5pt 7pt}
.chip::before{content:'● ';color:#F26D21}
h1{font-size:19pt;color:#14213D;letter-spacing:-.01em;margin-bottom:4pt}
.trow{display:flex;justify-content:space-between;align-items:flex-start;gap:14pt}
.trow svg{flex:0 0 auto;margin-top:2pt}
.sub{color:#5b6472;font-size:10pt;margin-bottom:14pt}
.kpis{display:flex;gap:26pt;border-top:.75pt solid #dbe2ec;border-bottom:.75pt solid #dbe2ec;padding:10pt 0;margin-bottom:14pt}
.kpis b{display:block;font-size:15.5pt;color:#F26D21}
.kpis span{font-size:7pt;letter-spacing:.14em;color:#5b6472;text-transform:uppercase}
h2{font-size:9.5pt;letter-spacing:.2em;color:#14213D;text-transform:uppercase;border-left:3pt solid #F26D21;padding-left:7pt;margin:14pt 0 7pt;page-break-after:avoid}
table{width:100%;border-collapse:collapse;page-break-inside:auto}
tr{page-break-inside:avoid}
td{border-bottom:.6pt solid #e6ebf3;padding:4.5pt 8pt;vertical-align:top}
td:first-child{width:42%;font-weight:700;color:#14213D;background:#f4f6fa}
tr:first-child td{border-top:1.4pt solid #14213D}
p.eq{font-size:9.5pt;color:#39434f;margin-top:2pt}
.final{margin-top:16pt;border-top:1.2pt solid #14213D;padding-top:8pt;font-size:8.5pt;color:#39434f}
.final .disc{margin-top:6pt;font-style:italic;color:#5b6472;font-size:8pt}
"""

TPL = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="head">
  <img src="data:image/png;base64,{logo}" alt="GNH">
  <div class="r"><div class="ft">FICHA T&Eacute;CNICA</div><span class="chip">PLATAFORMAS ELEVADORAS</span></div>
</div>
<div class="trow"><div><h1>{tipo} {sz}</h1>
<p class="sub">{subt}</p></div>{icon}</div>
<div class="kpis">
  <div><b>{kAlt}</b><span>Altura de trabajo</span></div>
  <div><b>{kCap}</b><span>Capacidad</span></div>
  <div><b>{kAlc}</b><span>Alcance horizontal</span></div>
  <div><b>{kPeso}</b><span>Peso total</span></div>
</div>
<h2>Dimensiones</h2><table>{dim}</table>
<h2>Rendimiento</h2><table>{perf}</table>
<h2>Fuente de energ&iacute;a</h2><table>{pw}</table>
<h2>Equipamiento est&aacute;ndar</h2><p class="eq">{std}</p>
<h2>Equipamiento opcional</h2><p class="eq">{opt}</p>
<div class="final">
  <b>GNH — Generando Nuevos Horizontes</b> &middot; Av. Rep&uacute;blica del Per&uacute; km 7, Ciudad del Este &middot; Acceso Sur, &Ntilde;emby, Paraguay<br>
  WhatsApp <b>+595 995 360060</b> &middot; comercial@gnhorizons.com &middot; gnhorizons.com
  <div class="disc">Datos transcritos del cat&aacute;logo del fabricante (ZS). Sujetos a cambio sin previo aviso; confirm&aacute; configuraci&oacute;n,
  plazos y disponibilidad con nuestro equipo t&eacute;cnico antes de la compra. En la l&iacute;nea telesc&oacute;pica, capacidad: 300 kg sin restricci&oacute;n de alcance / 460 kg con restricci&oacute;n.</div>
</div>
</body></html>"""

ICON_TELE = """<svg width="86" height="58" viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="18" y="50" width="56" height="12" rx="2.5" fill="#14213D"/>
<circle cx="30" cy="66" r="8" fill="none" stroke="#14213D" stroke-width="4"/>
<circle cx="62" cy="66" r="8" fill="none" stroke="#14213D" stroke-width="4"/>
<rect x="38" y="42" width="16" height="9" rx="2" fill="#14213D"/>
<path d="M46 46 L100 16" stroke="#14213D" stroke-width="6" stroke-linecap="round"/>
<path d="M60 43 L74 35" stroke="#F26D21" stroke-width="6" stroke-linecap="round"/>
<rect x="97" y="6" width="16" height="13" rx="2" fill="none" stroke="#F26D21" stroke-width="3.5"/>
</svg>"""
ICON_ART = """<svg width="86" height="58" viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="12" y="50" width="52" height="12" rx="2.5" fill="#14213D"/>
<circle cx="23" cy="66" r="8" fill="none" stroke="#14213D" stroke-width="4"/>
<circle cx="53" cy="66" r="8" fill="none" stroke="#14213D" stroke-width="4"/>
<path d="M40 50 L52 24" stroke="#14213D" stroke-width="6" stroke-linecap="round"/>
<path d="M52 24 L80 10" stroke="#14213D" stroke-width="6" stroke-linecap="round"/>
<path d="M80 10 L97 26" stroke="#F26D21" stroke-width="6" stroke-linecap="round"/>
<rect x="93" y="24" width="16" height="13" rx="2" fill="none" stroke="#F26D21" stroke-width="3.5"/>
</svg>"""

def photo_or_icon(d, art):
    # Foto real do modelo quando existe; senão, a silhueta do tipo.
    ph = d.get('photo')
    if ph and (REPO / ph).exists():
        mime = mimetypes.guess_type(ph)[0] or 'image/png'
        b64 = base64.b64encode((REPO / ph).read_bytes()).decode()
        return (f'<img src="data:{mime};base64,{b64}" alt="" '
                'style="width:118pt;max-height:80pt;object-fit:contain">')
    return ICON_ART if art else ICON_TELE


FOOTER = ('<div style="width:100%;font-size:7pt;color:#8a93a3;text-align:center;'
          'font-family:Arial">gnhorizons.com &middot; WhatsApp +595 995 360060 &middot; '
          'P&aacute;gina <span class="pageNumber"></span> de <span class="totalPages"></span></div>')


def rows(d, labels, order):
    out = []
    for k in order:
        if k in d:
            out.append(f'<tr><td>{html.escape(labels[k])}</td><td>{html.escape(d[k])}</td></tr>')
    return ''.join(out)


def fmt_m(mm):  # '20.500 mm' -> '20,5 m' (valores já em metros passam direto)
    if 'mm' not in mm:
        return mm
    n = int(mm.replace('.', '').replace(' mm', ''))
    v = n / 1000
    return (f'{v:.2f}'.rstrip('0').rstrip('.')).replace('.', ',') + ' m'


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROMIUM', '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'))
    pg = b.new_page()
    pg.goto('file://' + str(REPO / 'gnh-redesign.html'))
    data = pg.evaluate('({PLAT, L: PLAT_L.es, STD: PLAT_STD.es, STD3: PLAT_STD3.es, STD_ART: PLAT_STD_ART.es, OPT: PLAT_OPT.es})')
    PLAT, L, STD, STD3, STD_ART, OPT = data['PLAT'], data['L'], data['STD'], data['STD3'], data['STD_ART'], data['OPT']

    OUT.mkdir(parents=True, exist_ok=True)
    for z, d in PLAT.items():
        art = bool(d.get('art'))
        sparse = art and not d['pw']
        if art and not sparse:
            # Articulada com catálogo completo do fabricante (Q16M-LI / Q16M-Do)
            tipo = 'PLATAFORMA ARTICULADA'
            energia = ('motor di&eacute;sel' if 'engine' in d['pw']
                       else 'el&eacute;ctrica de litio ' + d['pw']['battery'].split(' /')[0])
            subt = ('Plataforma de trabajo a&eacute;reo de brazo articulado &middot; ' + energia +
                    ' &middot; c&oacute;digo de f&aacute;brica ' + z)
            kAlc = fmt_m(d['dim']['reach'])
            dim_rows = rows(d['dim'], L, ORDER_DIM)
            pw_rows = rows(d['pw'], L, ORDER_PW)
            std_txt = html.escape(STD_ART.replace('180°', '360°') if d.get('art360') else STD_ART)
            opt_txt = html.escape(OPT)
        elif art:
            # Línea articulada: solo datos publicados por GNH; el resto "Consultar",
            # siguiendo el patrón de las fichas existentes (p.ej. SJYL0.22-12).
            tipo = 'PLATAFORMA ARTICULADA'
            subt = 'Plataforma de trabajo a&eacute;reo de brazo articulado &middot; l&iacute;nea ZS'
            energia = ''
            kAlc = 'Consultar'
            dim_rows = rows(d['dim'], L, ORDER_DIM) + (
                '<tr><td>Tama&ntilde;o de plataforma</td><td>Consultar</td></tr>'
                '<tr><td>Dimensiones de transporte</td><td>Consultar por modelo</td></tr>')
            pw_rows = '<tr><td>Alimentaci&oacute;n</td><td>Consultar &mdash; se confirma seg&uacute;n configuraci&oacute;n</td></tr>'
            std_txt = ('Ficha t&eacute;cnica completa del fabricante disponible a pedido &mdash; '
                       'consultanos por WhatsApp y te la enviamos junto con la cotizaci&oacute;n.')
            opt_txt = 'Consultar accesorios y opcionales disponibles para la l&iacute;nea articulada.'
        else:
            tipo = 'PLATAFORMA TELESC&Oacute;PICA'
            energia = ('motor di&eacute;sel' if 'engine' in d['pw']
                       else 'el&eacute;ctrica de litio ' + d['pw']['battery'].split(' /')[0])
            subt = ('Plataforma de trabajo a&eacute;reo de brazo recto &middot; ' + energia +
                    ' &middot; c&oacute;digo de f&aacute;brica ' + z)
            kAlc = fmt_m(d['dim']['reach'])
            dim_rows = rows(d['dim'], L, ORDER_DIM)
            pw_rows = rows(d['pw'], L, ORDER_PW)
            std_txt = html.escape(STD.replace('plataforma de doble entrada', STD3) if d.get('three') else STD)
            opt_txt = html.escape(OPT)
        page_html = TPL.format(
            css=CSS, logo=LOGO, tipo=tipo, sz=d['sz'], subt=subt,
            icon=photo_or_icon(d, art),
            kAlt=fmt_m(d['dim']['workHeight']), kAlc=kAlc,
            kPeso=d['perf']['weight'], kCap=d['perf']['cap'],
            dim=dim_rows, perf=rows(d['perf'], L, ORDER_PERF),
            pw=pw_rows, std=std_txt, opt=opt_txt)
        pg.set_content(page_html)
        out = OUT / f"plataforma-{d['sz'].lower()}.pdf"
        pg.pdf(path=str(out), format='A4', print_background=True,
               display_header_footer=True, header_template='<span></span>',
               footer_template=FOOTER, margin={'top': '0mm', 'bottom': '12mm'})
        print(f'{out.name}  ({out.stat().st_size // 1024} KB)')
    b.close()
