#!/usr/bin/env python3
"""Gera o informe técnico comparativo Cielo Azul / GNH / Camargo Química.

Os gráficos são SVG calculado, não imagem: o PDF é vetorial e os números saem
exatos. O gráfico original do cliente tinha dois eixos Y no mesmo plano
(resistência em MPa à esquerda, água e assentamento à direita) — isso faz o
leitor enxergar correlação onde ela não está medida, então aqui cada grandeza
tem o seu próprio plano.

Uso:  python3 build-informe-cielo-azul.py  &&  node render-pdf.cjs
"""
import base64, pathlib

BASE = pathlib.Path(__file__).resolve().parent
RAIZ = BASE.parent.parent

# ---------------------------------------------------------------- dados
# Ensayo en planta, 10/06/2026. Misma dosificación (1,2%) en los dos tratamientos.
T1 = {'nombre': 'Pennsylvania', 'dos': '1,2 %', 'R3': 10.8, 'R7': 18.0, 'R28': 25.4,
      'agua': 249, 'ini': 195, 'm15': 170}
T2 = {'nombre': 'Camargo Química PN797', 'dos': '1,2 %', 'R3': 12.1, 'R7': 21.2, 'R28': 32.1,
      'agua': 232, 'ini': 200, 'm15': 160}

# paleta de séries validada com scripts/validate_palette.js (skill dataviz):
# banda de luminosidade, piso de croma, separação sob daltonismo e contraste — tudo PASS
C1, C2 = '#2a78d6', '#d1571a'
TINTA, TINTA2, TINTA3 = '#0F172A', '#475569', '#94A3B8'
NARANJA, ROYAL = '#F26D21', '#1E3A8A'
LINEA = '#E2E8F0'


def b64(p):
    f = RAIZ / p
    return base64.b64encode(f.read_bytes()).decode() if f.exists() else ''


LOGO = b64('gnh-hero/public/img/logo-oficial.png')
LOGO_BLANCA = b64('gnh-hero/public/img/logo-blanca.png')
LOGO_CAMARGO = b64('gnh-hero/public/img/logo-camargo.png')


def pct(a, b):
    return (b / a - 1) * 100


def num(v, dec=1):
    return f'{v:.{dec}f}'.replace('.', ',')


# ---------------------------------------------------------- gráfico 1
def grafico_resistencia():
    """Barras agrupadas. Una sola escala: MPa."""
    W, H = 690, 306
    ml, mr, mt, mb = 46, 14, 26, 54
    pw, ph = W - ml - mr, H - mt - mb
    ymax = 35
    ejes = ['R3', 'R7', 'R28']
    rot = {'R3': '3 días', 'R7': '7 días', 'R28': '28 días'}

    def y(v):
        return mt + ph - (v / ymax) * ph

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
         f'aria-label="Resistencia a compresión en MPa a 3, 7 y 28 días">']
    # rejilla recessiva + marcas del eje
    for v in range(0, ymax + 1, 5):
        s.append(f'<line x1="{ml}" y1="{y(v):.1f}" x2="{ml+pw}" y2="{y(v):.1f}" '
                 f'stroke="{LINEA}" stroke-width="1"/>')
        s.append(f'<text x="{ml-10}" y="{y(v)+4:.1f}" text-anchor="end" font-size="11" '
                 f'fill="{TINTA3}">{v}</text>')
    s.append(f'<text x="{ml-10}" y="{mt-12}" text-anchor="end" font-size="10.5" '
             f'fill="{TINTA3}" font-weight="700">MPa</text>')

    gw = pw / len(ejes)
    bw, gap = 62, 3          # 2-3px de respiro entre barras vecinas
    for i, k in enumerate(ejes):
        cx = ml + gw * i + gw / 2
        for j, (d, col) in enumerate(((T1, C1), (T2, C2))):
            v = d[k]
            x = cx - bw - gap / 2 + j * (bw + gap)
            alt = ph - (y(v) - mt)
            s.append(f'<path d="M{x:.1f} {mt+ph} v{-(alt-4):.1f} a4 4 0 0 1 4 -4 '
                     f'h{bw-8} a4 4 0 0 1 4 4 v{alt-4:.1f} z" fill="{col}"/>')
            # en papel no hay hover: el valor va impreso sobre la barra
            s.append(f'<text x="{x+bw/2:.1f}" y="{y(v)-9:.1f}" text-anchor="middle" '
                     f'font-size="13" font-weight="700" fill="{TINTA}">{num(v)}</text>')
        # o replace de ponto por vírgula tem que ficar SÓ no número: aplicado à
        # string inteira, ele reescreve as coordenadas do SVG e quebra o desenho
        g = f'{pct(T1[k], T2[k]):+.1f}'.replace('.', ',')
        s.append(f'<text x="{cx:.1f}" y="{mt+ph+22}" text-anchor="middle" font-size="12" '
                 f'font-weight="700" fill="{TINTA}">{rot[k]}</text>')
        s.append(f'<text x="{cx:.1f}" y="{mt+ph+41}" text-anchor="middle" font-size="11.5" '
                 f'font-weight="700" fill="{C2}">{g} %</text>')
    s.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="{TINTA3}" stroke-width="1"/>')
    s.append('</svg>')
    return ''.join(s)


# ---------------------------------------------------------- gráfico 2
def grafico_agua():
    """Barras horizontales. Escala propia: litros por m³."""
    W, H = 330, 128
    ml, mr, mt = 8, 66, 30
    pw = W - ml - mr
    xmax = 260

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
         f'aria-label="Agua final por metro cúbico">']
    for j, (d, col, et) in enumerate(((T1, C1, 'T1'), (T2, C2, 'T2'))):
        yy = mt + j * 44
        ancho = d['agua'] / xmax * pw
        s.append(f'<path d="M{ml} {yy} h{ancho-4:.1f} a4 4 0 0 1 4 4 v{22-8} '
                 f'a4 4 0 0 1 -4 4 H{ml} z" fill="{col}"/>')
        s.append(f'<text x="{ml+ancho+9:.1f}" y="{yy+16}" font-size="13" font-weight="700" '
                 f'fill="{TINTA}">{d["agua"]} L</text>')
        s.append(f'<text x="{ml}" y="{yy-6}" font-size="10.5" font-weight="700" '
                 f'fill="{TINTA2}">{et} · {d["nombre"]}</text>')
    s.append(f'<text x="{ml}" y="{H-8}" font-size="11.5" font-weight="700" fill="{C2}">'
             f'−17 L/m³  ·  −6,8 %</text>')
    s.append('</svg>')
    return ''.join(s)


# ---------------------------------------------------------- gráfico 3
def grafico_asentamiento():
    """Pendiente: dos puntos en el tiempo, que es exactamente lo que se midió."""
    W, H = 330, 178
    ml, mr, mt, mb = 52, 52, 26, 40
    pw, ph = W - ml - mr, H - mt - mb
    lo, hi = 140, 215

    def y(v):
        return mt + ph - (v - lo) / (hi - lo) * ph

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
         f'aria-label="Asentamiento inicial y a los 15 minutos">']
    for v in (150, 175, 200):
        s.append(f'<line x1="{ml}" y1="{y(v):.1f}" x2="{ml+pw}" y2="{y(v):.1f}" '
                 f'stroke="{LINEA}" stroke-width="1"/>')
    def apartar(va, vb):
        """Devuelve el desplazamiento vertical de cada etiqueta.

        195 y 200 mm distan 5 mm: en esta escala son 7 px y las dos etiquetas
        se pisan. Cuando están más cerca que una línea de texto, se separan."""
        sep = abs(y(va) - y(vb))
        if sep >= 15:
            return 0, 0
        d = (15 - sep) / 2
        return (-d, d) if va > vb else (d, -d)

    dz_ini = apartar(T1['ini'], T2['ini'])
    dz_m15 = apartar(T1['m15'], T2['m15'])
    for k, (d, col) in enumerate(((T1, C1), (T2, C2))):
        s.append(f'<line x1="{ml}" y1="{y(d["ini"]):.1f}" x2="{ml+pw}" y2="{y(d["m15"]):.1f}" '
                 f'stroke="{col}" stroke-width="2"/>')
        for x, v in ((ml, d['ini']), (ml + pw, d['m15'])):
            s.append(f'<circle cx="{x}" cy="{y(v):.1f}" r="5" fill="{col}" '
                     f'stroke="#fff" stroke-width="2"/>')
        s.append(f'<text x="{ml-11}" y="{y(d["ini"])+4+dz_ini[k]:.1f}" text-anchor="end" '
                 f'font-size="12" font-weight="700" fill="{col}">{d["ini"]}</text>')
        s.append(f'<text x="{ml+pw+11}" y="{y(d["m15"])+4+dz_m15[k]:.1f}" font-size="12" '
                 f'font-weight="700" fill="{col}">{d["m15"]}</text>')
    s.append(f'<text x="{ml}" y="{H-16}" text-anchor="middle" font-size="10.5" '
             f'fill="{TINTA2}">inicial</text>')
    s.append(f'<text x="{ml+pw}" y="{H-16}" text-anchor="middle" font-size="10.5" '
             f'fill="{TINTA2}">15 min</text>')
    s.append(f'<text x="{ml-10}" y="{mt-10}" text-anchor="end" font-size="10.5" '
             f'fill="{TINTA3}" font-weight="700">mm</text>')
    s.append('</svg>')
    return ''.join(s)


def leyenda():
    return (f'<div class="leg">'
            f'<span><i style="background:{C1}"></i>T1 · Pennsylvania 1,2 %</span>'
            f'<span><i style="background:{C2}"></i>T2 · Camargo Química PN797 1,2 %</span>'
            f'</div>')


# ---------------------------------------------------------------- HTML
def fila(rot, v1, v2, unidad, dec=1, mejor='alto'):
    d = v2 - v1
    p = pct(v1, v2)
    bueno = (d > 0) if mejor == 'alto' else (d < 0)
    cls = 'up' if bueno else 'down'
    return (f'<tr><th>{rot}</th><td>{num(v1,dec)}</td><td class="hi">{num(v2,dec)}</td>'
            f'<td class="{cls}">{"+" if d>0 else "−"}{num(abs(d),dec)} {unidad}</td>'
            f'<td class="{cls}">{"+" if p>0 else "−"}{num(abs(p))} %</td></tr>')


html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Informe técnico comparativo — Cielo Azul · GNH · Camargo Química</title>
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Liberation Sans", Arial, sans-serif; color: {TINTA};
          -webkit-print-color-adjust: exact; print-color-adjust: exact;
          font-variant-numeric: tabular-nums; }}
  .pg {{ width: 210mm; height: 297mm; padding: 17mm 18mm 15mm; position: relative;
         page-break-after: always; overflow: hidden; }}
  .pg:last-child {{ page-break-after: auto; }}

  /* ---------- portada ---------- */
  .cover {{ background: linear-gradient(160deg, #16233f 0%, {TINTA} 55%, #070c1a 100%);
            color: #fff; padding: 24mm 18mm; }}
  .cover .rule {{ width: 54mm; height: 4px; background: {NARANJA}; margin: 11mm 0 9mm; }}
  .cover h1 {{ font-size: 33pt; line-height: 1.1; font-weight: 700; letter-spacing: -.5px; }}
  .cover h1 em {{ font-style: normal; color: #ff9a4d; }}
  .cover .sub {{ font-size: 12.5pt; color: #c7d0e0; margin-top: 7mm; max-width: 128mm;
                 line-height: 1.5; }}
  .cover .eyebrow {{ font-size: 9.5pt; letter-spacing: 3.4px; text-transform: uppercase;
                     color: #ff9a4d; font-weight: 700; }}
  .cover .meta {{ position: absolute; left: 18mm; right: 18mm; bottom: 22mm;
                  display: flex; justify-content: space-between; align-items: flex-end;
                  border-top: 1px solid rgba(255,255,255,.22); padding-top: 6mm; }}
  .cover .meta div {{ font-size: 9.5pt; color: #aab6cc; line-height: 1.65; }}
  .cover .meta b {{ display: block; color: #fff; font-size: 11pt; }}

  /* ---------- cabecera / pie ---------- */
  .hd {{ display: flex; justify-content: space-between; align-items: center;
         border-bottom: 1px solid {LINEA}; padding-bottom: 3.5mm; margin-bottom: 8mm; }}
  .hd .t {{ font-size: 8.5pt; letter-spacing: 2.2px; text-transform: uppercase;
            color: {TINTA2}; font-weight: 700; }}
  .hd img {{ height: 8.5mm; }}
  .ft {{ position: absolute; left: 18mm; right: 18mm; bottom: 10mm;
         border-top: 1px solid {LINEA}; padding-top: 2.5mm;
         display: flex; justify-content: space-between;
         font-size: 7.6pt; color: {TINTA3}; }}

  h2 {{ font-size: 19pt; line-height: 1.2; margin-bottom: 2mm; letter-spacing: -.3px; }}
  h2 .n {{ color: {NARANJA}; font-size: 11pt; vertical-align: super; margin-right: 2mm;
           font-weight: 700; }}
  .lead {{ font-size: 10.5pt; color: {TINTA2}; line-height: 1.6; max-width: 158mm;
           margin-bottom: 7mm; }}
  h3 {{ font-size: 10pt; letter-spacing: 1.6px; text-transform: uppercase;
        color: {ROYAL}; margin: 7mm 0 3mm; }}
  p {{ font-size: 10pt; line-height: 1.65; color: #1e293b; margin-bottom: 3mm; }}

  /* ---------- cifras ---------- */
  .kpis {{ display: flex; gap: 4mm; margin: 6mm 0 8mm; }}
  .kpi {{ flex: 1; border: 1px solid {LINEA}; border-top: 3px solid {NARANJA};
          padding: 5mm 5mm 4.5mm; }}
  .kpi .v {{ font-size: 27pt; font-weight: 700; line-height: 1; letter-spacing: -1px; }}
  .kpi .l {{ font-size: 8.6pt; color: {TINTA2}; margin-top: 2.5mm; line-height: 1.45; }}
  .kpi .c {{ font-size: 7.8pt; color: {TINTA3}; margin-top: 1.5mm; }}

  /* ---------- tablas ---------- */
  table {{ width: 100%; border-collapse: collapse; font-size: 9.6pt; }}
  thead th {{ font-size: 8pt; letter-spacing: 1.1px; text-transform: uppercase;
              color: {TINTA2}; text-align: right; padding: 0 3mm 2.5mm;
              border-bottom: 1.5px solid {TINTA}; font-weight: 700; }}
  thead th:first-child {{ text-align: left; }}
  tbody th {{ text-align: left; font-weight: 700; padding: 3mm; border-bottom: 1px solid {LINEA}; }}
  tbody td {{ text-align: right; padding: 3mm; border-bottom: 1px solid {LINEA}; }}
  tbody tr:nth-child(even) th, tbody tr:nth-child(even) td {{ background: #f8fafc; }}
  td.hi {{ font-weight: 700; }}
  td.up {{ color: #15803d; font-weight: 700; }}
  td.down {{ color: #b45309; font-weight: 700; }}

  .leg {{ display: flex; gap: 8mm; font-size: 9pt; color: {TINTA2}; margin-top: 3mm; }}
  .leg i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px;
            margin-right: 2.4mm; vertical-align: -1px; }}
  .cols {{ display: flex; gap: 9mm; }}
  .cols > div {{ flex: 1; }}
  .nota {{ font-size: 8.4pt; color: {TINTA3}; line-height: 1.55; margin-top: 3mm; }}
  .callout {{ border-left: 3px solid {NARANJA}; background: #fff7ed; padding: 4.5mm 5mm;
              margin: 5mm 0; }}
  .callout > b {{ display: block; margin-bottom: 1.5mm; font-size: 10pt; }}
  .callout p {{ font-size: 9.5pt; margin: 0; color: #4a3520; }}
  .flag {{ border-left: 3px solid {TINTA3}; background: #f8fafc; padding: 4.5mm 5mm; margin: 5mm 0; }}
  .flag > b {{ display: block; margin-bottom: 1.5mm; font-size: 10pt; }}
  .flag p {{ font-size: 9.5pt; margin: 0; color: {TINTA2}; }}
  ol {{ margin: 0 0 0 5mm; }}
  ol li {{ font-size: 10pt; line-height: 1.6; margin-bottom: 3mm; padding-left: 2mm; }}
</style></head><body>

<!-- ============================== PORTADA ============================== -->
<section class="pg cover">
  <img src="data:image/png;base64,{LOGO_BLANCA}" style="height:16mm" alt="GNH">
  <div class="rule"></div>
  <div class="eyebrow">Informe técnico comparativo</div>
  <h1>Aditivo superplastificante<br><em>PN797</em><br>Evaluación en planta</h1>
  <div class="sub">Ensayo comparativo con dosificación de 1,2 % sobre diseño de mezcla
    único. Determinación de resistencia a compresión a 3, 7 y 28 días, demanda de
    agua y retención de asentamiento.</div>
  <div class="meta">
    <div><b>Cielo Azul</b>Planta de hormigón · Ensayo comparativo</div>
    <div><b>10 de junio de 2026</b>GNH · Camargo Química</div>
    <div style="text-align:right"><b>Documento técnico</b>Uso comercial · Distribución controlada</div>
  </div>
</section>

<!-- ============================== RESUMEN ============================== -->
<section class="pg">
  <div class="hd"><span class="t">Resumen ejecutivo</span>
    <img src="data:image/png;base64,{LOGO}" alt="GNH"></div>

  <h2><span class="n">01</span>Síntesis de resultados</h2>
  <div class="lead">El tratamiento con PN797 registró valores superiores de resistencia
    en las tres edades ensayadas, con una demanda de agua 17 L/m³ inferior a la
    referencia. El diferencial aumenta con la edad del hormigón.</div>

  <div class="kpis">
    <div class="kpi"><div class="v" style="color:{C2}">+26,4 %</div>
      <div class="l">Resistencia a 28 días</div><div class="c">32,1 frente a 25,4 MPa</div></div>
    <div class="kpi"><div class="v" style="color:{C2}">−17 L</div>
      <div class="l">Agua por m³</div><div class="c">232 frente a 249 L/m³ · −6,8 %</div></div>
    <div class="kpi"><div class="v" style="color:{C2}">+17,8 %</div>
      <div class="l">Resistencia a 7 días</div><div class="c">21,2 frente a 18,0 MPa</div></div>
  </div>

  <h3>Condiciones del ensayo</h3>
  <p>Ambos tratamientos se ejecutaron el mismo día sobre idéntico diseño de mezcla,
  con <b>dosificación de 1,2 %</b> en los dos casos. El aditivo constituye la única
  variable entre T1 y T2, condición que permite atribuir el diferencial al producto.</p>

  <h3>Cuadro comparativo</h3>
  <table>
    <thead><tr><th>Parámetro</th><th>T1 · Pennsylvania</th><th>T2 · PN797</th>
      <th>Diferencia</th><th>Variación</th></tr></thead>
    <tbody>
      {fila('Resistencia 3 días (MPa)', T1['R3'], T2['R3'], 'MPa')}
      {fila('Resistencia 7 días (MPa)', T1['R7'], T2['R7'], 'MPa')}
      {fila('Resistencia 28 días (MPa)', T1['R28'], T2['R28'], 'MPa')}
      {fila('Agua final (L/m³)', T1['agua'], T2['agua'], 'L', 0, 'bajo')}
      {fila('Asentamiento inicial (mm)', T1['ini'], T2['ini'], 'mm', 0)}
      {fila('Asentamiento 15 min (mm)', T1['m15'], T2['m15'], 'mm', 0)}
    </tbody>
  </table>
  <div class="nota">Verde: favorable al PN797. Ámbar: favorable a la referencia.
    Asentamiento expresado en milímetros.</div>

  <div class="ft"><span>GNH · Generando Nuevos Horizontes — Distribución exclusiva
    Camargo Química en Paraguay</span><span>2 / 5</span></div>
</section>

<!-- ============================== RESISTENCIA ============================== -->
<section class="pg">
  <div class="hd"><span class="t">Resistencia a compresión</span>
    <img src="data:image/png;base64,{LOGO}" alt="GNH"></div>

  <h2><span class="n">02</span>Evolución de la resistencia</h2>
  <div class="lead">El diferencial a favor del PN797 se amplía con la edad del hormigón:
    12,0 % a 3 días, 17,8 % a 7 días y 26,4 % a 28 días.</div>

  {grafico_resistencia()}
  {leyenda()}

  <h3>Análisis</h3>
  <p>El mayor desarrollo a edad temprana reduce los tiempos de desmolde y de puesta
  en servicio. El incremento del diferencial hasta los 28 días resulta consistente
  con la menor demanda de agua registrada: <b>a igual contenido de cemento, una
  relación agua/cemento inferior determina mayor resistencia final</b>.</p>

  <div class="callout"><b>Incidencia sobre el costo de producción</b>
    <p>El excedente de 6,7 MPa sobre la referencia a 28 días admite reformulación del
    diseño de mezcla. Alcanzada la resistencia característica de proyecto con margen,
    ese margen es convertible en reducción del contenido de cemento. La cuantificación
    requiere ensayo de dosificación específico sobre el diseño vigente en planta.</p></div>

  <div class="ft"><span>Ensayo Cielo Azul · 10 de junio de 2026</span><span>3 / 5</span></div>
</section>

<!-- ============================== AGUA ============================== -->
<section class="pg">
  <div class="hd"><span class="t">Agua y trabajabilidad</span>
    <img src="data:image/png;base64,{LOGO}" alt="GNH"></div>

  <h2><span class="n">03</span>Demanda de agua y asentamiento</h2>
  <div class="lead">La reducción de la demanda de agua determina el comportamiento
    mecánico descrito. La retención de asentamiento a 15 minutos resulta favorable
    a la referencia.</div>

  <div class="cols">
    <div>
      <h3 style="margin-top:0">Agua final por m³</h3>
      {grafico_agua()}
      <p style="margin-top:4mm">Reducción de 17 L/m³ para igual objetivo de asentamiento.
      Constituye la variable determinante del comportamiento mecánico registrado a 3,
      7 y 28 días.</p>
    </div>
    <div>
      <h3 style="margin-top:0">Asentamiento: inicial y 15 min</h3>
      {grafico_asentamiento()}
      <p style="margin-top:4mm">Con asentamiento inicial 5 mm superior, el PN797 registra
      160 mm a los 15 minutos de agitación frente a 170 mm de la referencia.</p>
    </div>
  </div>

  <div class="flag"><b>Retención de asentamiento</b>
    <p>Pérdida registrada en 15 minutos de agitación: <b>40 mm (−20,0 %)</b> en el PN797
    contra <b>25 mm (−12,8 %)</b> en la referencia. En trayectos extensos o con espera en
    obra el parámetro requiere verificación. Corresponde a ajuste de dosificación y
    eventual incorporación de aditivo de mantenimiento. Se recomienda ensayo bajo las
    condiciones reales de entrega de la planta.</p></div>

  <div class="ft"><span>GNH · Generando Nuevos Horizontes</span><span>4 / 5</span></div>
</section>

<!-- ============================== CONCLUSIÓN ============================== -->
<section class="pg">
  <div class="hd"><span class="t">Conclusión y próximos pasos</span>
    <img src="data:image/png;base64,{LOGO}" alt="GNH"></div>

  <h2><span class="n">04</span>Conclusiones</h2>

  <p>Bajo condiciones controladas y dosificación idéntica, el <b>Camargo Química
  PN797</b> registró valores de resistencia superiores a la referencia de planta en
  las tres edades ensayadas, con una demanda de agua 17 L/m³ inferior. El
  comportamiento es uniforme en todo el rango de edades evaluado.</p>

  <p>La retención de asentamiento a 15 minutos resulta favorable a la referencia.
  Este parámetro define la verificación pendiente previa a una recomendación de
  sustitución en producción.</p>

  <h3>Ensayos complementarios recomendados</h3>
  <ol>
    <li><b>Determinación a 63 días.</b> Prevista en el registro del ensayo para el
      12/08. Completa la curva de resistencia a largo plazo.</li>
    <li><b>Retención de asentamiento en condiciones de entrega.</b> Reproducción del
      trayecto y del tiempo de espera habituales de la planta, para dimensionar la
      pérdida en operación y ajustar dosificación.</li>
    <li><b>Optimización del diseño de mezcla.</b> Conversión del excedente de 6,7 MPa
      a 28 días en reducción del contenido de cemento, manteniendo la resistencia
      característica de proyecto.</li>
  </ol>

  <div class="callout" style="margin-top:8mm"><b>Nota metodológica</b>
    <p>Valores correspondientes al registro de ensayo del 10/06/2026. Las variaciones
    porcentuales de resistencia constan en el registro original. La reducción de la
    demanda de agua y las pérdidas de asentamiento fueron calculadas sobre esos mismos
    valores. El registro rotula el asentamiento en centímetros; los valores
    corresponden a milímetros y se expresan como tales en este informe.</p></div>

  <div style="position:absolute;left:18mm;right:18mm;bottom:26mm;display:flex;
              justify-content:space-between;align-items:flex-end;
              border-top:1px solid {LINEA};padding-top:6mm">
    <div style="font-size:9pt;color:{TINTA2};line-height:1.7">
      <b style="color:{TINTA};font-size:10.5pt;display:block">GNH — Generando Nuevos Horizontes</b>
      Distribución exclusiva de Camargo Química en Paraguay<br>
      Av. República del Perú km 7, Ciudad del Este · +595 995 360060<br>
      gnhorizons.com
    </div>
    <img src="data:image/png;base64,{LOGO_CAMARGO}" style="height:13mm" alt="Camargo Química">
  </div>
  <div class="ft"><span>Informe técnico comparativo · Cielo Azul</span><span>5 / 5</span></div>
</section>
</body></html>"""

out = BASE / 'informe-cielo-azul.html'
out.write_text(html, encoding='utf-8')
print('HTML:', out, len(html), 'bytes')
