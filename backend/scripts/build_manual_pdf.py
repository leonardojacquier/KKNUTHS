"""Regenera app/api/assets/KKNuths-Manual.pdf A PARTIR DO MANUAL.md.

Uso (na raiz do backend): python scripts/build_manual_pdf.py
Requer Chromium headless (no dev remoto: /opt/pw-browsers/chromium-*/chrome-linux/chrome).

Até 19/09 este script lia `manual_design.html` — um export congelado de 1,5 MB.
O `app/api/manual_md.py` já gerava o HTML do markdown desde 22/08, mas o PDF
que o `/manual` entrega continuava saindo do export velho: corrigir o
MANUAL.md não corrigia o que o aluno lê. Agora é uma fonte só.

O HTML do manual_md flui em quantas páginas precisar (não é o folder A4 de
página fixa), então não há zoom a calibrar: só margens de impressão.
"""
from __future__ import annotations

import glob
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "app/api/assets/KKNuths-Manual.pdf"

sys.path.insert(0, str(ROOT))

FIX = "<style>@page{size:210mm 297mm;margin:12mm 0}</style>"


def chrome_bin() -> str:
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                "/usr/bin/chromium", "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome"):
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    sys.exit("chromium não encontrado")


def main() -> None:
    from app.api.manual_md import build_manual_html_from_md

    html = build_manual_html_from_md().replace("</head>", FIX + "</head>")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as f:
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
    except ImportError:
        print(f"{OUT.name} gerado ({OUT.stat().st_size // 1024} kB; "
              "pymupdf ausente — confira as páginas na mão)")


if __name__ == "__main__":
    main()
