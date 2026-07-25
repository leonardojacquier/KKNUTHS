"""Regenera app/api/assets/KKNuths-Manual.pdf a partir do manual_design.html.

Uso (na raiz do backend): python scripts/build_manual_pdf.py
Requer Chromium headless (no dev remoto: /opt/pw-browsers/chromium-*/chrome-linux/chrome).

O print-fix é obrigatório: o HTML tem @page margin:0 (corta as laterais na
impressão) — aqui entram margens reais e o zoom calibrado pra fechar em
7 páginas A4 sem página-fantasma no fim. Depois de mexer no HTML, confira
o total de páginas e a última página (sobra de rodapé = diminuir o zoom).
"""
from __future__ import annotations

import glob
import pathlib
import subprocess
import sys
import tempfile

ZOOM = 0.845   # 0.865 estourou pra 8ª página após o card de procedência
FIX = ("<style>@page{size:210mm 297mm;margin:9mm 11mm}"
       f"html{{zoom:{ZOOM}}}</style>")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "app/api/assets/manual_design.html"
OUT = ROOT / "app/api/assets/KKNuths-Manual.pdf"


def chrome_bin() -> str:
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                "/usr/bin/chromium", "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome"):
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    sys.exit("chromium não encontrado")


def main() -> None:
    html = SRC.read_text().replace("</head>", FIX + "</head>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        tmp = f.name
    subprocess.run([chrome_bin(), "--headless", "--disable-gpu",
                    "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT}", f"file://{tmp}"], check=True)
    try:
        import fitz

        doc = fitz.open(str(OUT))
        tail = len(doc[-1].get_text())
        print(f"{OUT.name}: {len(doc)} páginas (última com {tail} chars)")
        if tail < 400:
            print("⚠️  última página quase vazia — diminua o ZOOM")
    except ImportError:
        print(f"{OUT.name} gerado (pymupdf ausente; confira as páginas na mão)")


if __name__ == "__main__":
    main()
