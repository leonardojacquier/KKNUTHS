"""O manual em HTML/PDF gerado A PARTIR do MANUAL.md.

Antes daqui existiam DOIS manuais: o `MANUAL.md` (que a gente edita) e o
`manual_design.html` (um export de 1,5 MB que virava o PDF). Documento e
documento, sem nada amarrando um ao outro — em 22/08 o markdown anunciava
"100 análises/mês" contra as 50 que o código aplica, e não citava /dossie.
Corrigir o markdown não corrigia o PDF, que é justamente o que o aluno lê.

Agora o markdown é a fonte e o PDF é derivado: divergir deixa de ser
possível. O visual é o mesmo do folder (app/api/folder_page.py) — mesma
paleta, mesma família tipográfica — para os dois materiais lerem como um
sistema só.

DUAS RESTRIÇÕES herdadas do folder, pelo mesmo motivo:
  1. FONTES DO SISTEMA, nunca @import de Google Fonts: o gerador de PDF roda
     sem rede e a fonte cai em silêncio.
  2. print-color-adjust:exact em tudo que tem fundo colorido, senão o PDF
     sai com os blocos brancos.

Aqui NÃO se mede página em mm como no folder: o manual flui em quantas
páginas precisar, e o CSS só cuida de não quebrar título longe do texto dele.
"""
from __future__ import annotations

import pathlib
import re

from app.api.manual_page import _img

_RAIZ = pathlib.Path(__file__).resolve().parents[3]
_MD = _RAIZ / "MANUAL.md"

_CSS = """
*{box-sizing:border-box}
:root{
  --papel:#FBFAF6;--carta:#FFFFFF;--tinta:#16211A;--mut:#5A665E;
  --feltro:#124A30;--feltro2:#0D3A25;--ouro:#B38D24;--ouro-claro:#F1D9A7;
  --ouro-tenue:#F6EEDC;--linha:#E2E6E0;
  --serif:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
  --mono:'SF Mono',ui-monospace,'DejaVu Sans Mono','Courier New',monospace;
}
@page{size:A4;margin:14mm 0}
body{margin:0;background:var(--papel);color:var(--tinta);
font-family:system-ui,-apple-system,'Segoe UI',sans-serif;
font-size:12.5px;line-height:1.62;print-color-adjust:exact;
-webkit-print-color-adjust:exact}
.env{max-width:170mm;margin:0 auto;padding:0 14mm}

/* ── capa ──────────────────────────────────────────────────────────── */
.capa{background:linear-gradient(150deg,var(--feltro),var(--feltro2));
color:#EAF2EC;padding:26mm 14mm 20mm;text-align:center;
print-color-adjust:exact;page-break-after:always}
.capa img{width:82px;height:82px;border-radius:50%;
box-shadow:0 2px 10px rgba(0,0,0,.35);margin-bottom:14px}
.capa h1{font-family:var(--serif);font-size:40px;margin:0 0 6px;
font-weight:400;letter-spacing:-.01em;color:#fff}
.capa .tag{color:var(--ouro-claro);font-size:14px;letter-spacing:.04em}
.capa .link{font-family:var(--mono);font-size:13px;color:#BFD3C6;
margin-top:16px}
.capa .tese{font-family:var(--serif);font-size:19px;color:var(--ouro-claro);
margin-top:22px;font-style:italic}

/* ── títulos ───────────────────────────────────────────────────────── */
h1,h2,h3{font-family:var(--serif);font-weight:400;
page-break-after:avoid;break-after:avoid}
h2{font-size:25px;margin:26px 0 10px;padding-bottom:6px;
border-bottom:2px solid var(--ouro);letter-spacing:-.01em}
h3{font-size:17px;margin:20px 0 7px;color:var(--feltro)}
p{margin:0 0 10px}
strong{font-weight:700}
em{font-style:italic}
a{color:var(--ouro);text-decoration:none}
hr{border:0;border-top:1px solid var(--linha);margin:22px 0}

/* ── listas ────────────────────────────────────────────────────────── */
ul,ol{margin:0 0 12px;padding-left:20px}
li{margin-bottom:4px}
li::marker{color:var(--ouro)}

/* ── tabelas: onde moram os comandos ───────────────────────────────── */
table{width:100%;border-collapse:collapse;margin:12px 0 18px;
font-size:11.5px;page-break-inside:auto}
th{background:var(--feltro);color:var(--ouro-claro);text-align:left;
padding:7px 10px;font-size:10.5px;letter-spacing:.1em;
text-transform:uppercase;font-weight:600;print-color-adjust:exact}
td{border-bottom:1px solid var(--linha);padding:7px 10px;
vertical-align:top;background:var(--carta);print-color-adjust:exact}
tr{page-break-inside:avoid}
tbody tr:nth-child(even) td{background:#FCFBF7}
td:first-child{white-space:nowrap;width:1%}

/* ── código: os comandos ───────────────────────────────────────────── */
code{font-family:var(--mono);font-size:.92em;background:var(--ouro-tenue);
color:#6B5C3C;border:1px solid var(--linha);border-radius:4px;
padding:1px 5px;print-color-adjust:exact;white-space:nowrap}
td code{font-weight:600}
pre{background:var(--feltro);color:#EAF2EC;border-radius:8px;padding:10px 13px;
overflow-x:auto;print-color-adjust:exact}
pre code{background:none;border:0;color:inherit;white-space:pre}

/* ── citação ───────────────────────────────────────────────────────── */
blockquote{margin:12px 0;padding:9px 14px;background:var(--carta);
border-left:3px solid var(--ouro);border-radius:0 8px 8px 0;
color:var(--mut);font-style:italic;print-color-adjust:exact}
blockquote p{margin:0}

/* ── rodapé ────────────────────────────────────────────────────────── */
.pe{margin-top:26px;padding:14px;background:var(--feltro);color:#BFD3C6;
border-radius:10px;text-align:center;font-size:11px;
print-color-adjust:exact;page-break-inside:avoid}
.pe b{color:var(--ouro-claro)}
"""


def _capa(titulo: str, subtitulo: str) -> str:
    """A capa não vem do markdown: o `# título` do MD vira ela."""
    return f"""<div class="capa">
  <img src="{_img('logo_avatar.png')}" alt="KKNuths">
  <h1>{titulo}</h1>
  <div class="tag">{subtitulo}</div>
  <div class="link">t.me/KKNUts_BOT</div>
  <div class="tese">A IA n&atilde;o faz a conta.<br>Quem calcula &eacute; a matem&aacute;tica.</div>
</div>"""


def _corpo_md() -> tuple[str, str, str]:
    """Devolve (título, subtítulo, markdown sem o cabeçalho da capa)."""
    texto = _MD.read_text(encoding="utf-8")
    linhas = texto.splitlines()
    titulo = subtitulo = ""
    corte = 0
    for i, ln in enumerate(linhas[:6]):
        if ln.startswith("# ") and not titulo:
            titulo = ln[2:].strip()
            corte = i + 1
        elif ln.startswith("### ") and titulo and not subtitulo:
            subtitulo = ln[4:].strip()
            corte = i + 1
    # o '---' logo abaixo do cabeçalho viraria um <hr> solto no topo
    while corte < len(linhas) and linhas[corte].strip() in ("", "---"):
        corte += 1
    return titulo, subtitulo, "\n".join(linhas[corte:])


def build_manual_html_from_md() -> str:
    """MANUAL.md -> HTML com a identidade do folder. Fonte única de verdade."""
    import markdown as _markdown

    titulo, subtitulo, corpo = _corpo_md()
    html = _markdown.markdown(
        corpo, extensions=["tables", "fenced_code", "sane_lists"])
    # o markdown transforma o link do bot em texto cru; deixa clicável
    html = re.sub(r"(?<!\")(https://t\.me/[\w?=]+)",
                  r'<a href="\1">\1</a>', html)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KKNuths &#9824; — Manual do Jogador</title>
<style>{_CSS}</style>
</head>
<body>
{_capa(titulo.replace("♠️", "").strip(), subtitulo)}
<div class="env">
{html}
<div class="pe">KKNuths &#9824; · <b>pare de achar, calcule</b> ·
an&aacute;lise p&oacute;s-sess&atilde;o, sem RTA · t.me/KKNUts_BOT</div>
</div>
</body>
</html>"""
