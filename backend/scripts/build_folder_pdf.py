"""Regenera app/api/assets/KKNuths-Folder.pdf a partir do folder_page.py.

Uso (na raiz do backend): python scripts/build_folder_pdf.py

O folder é DUAS páginas A4 (frente e verso) e o HTML já traz @page com
margem 0 e .page de altura fixa — então aqui não entra zoom nem margem, só
a impressão. Se sair uma 3ª página, alguma caixa cresceu além do A4: é
conteúdo demais, não é o print-fix.
"""
from __future__ import annotations

import glob
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "app/api/assets/KKNuths-Folder.pdf"


def chrome_bin() -> str:
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                "/usr/bin/chromium", "/usr/bin/chromium-browser",
                "/usr/bin/google-chrome"):
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    sys.exit("chromium não encontrado")


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from app.api.folder_page import build_folder_html

    html = build_folder_html()
    if "t.me/" in html:
        sys.exit("ERRO: o folder do piloto não pode sair com link do bot")
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        tmp = f.name
    subprocess.run([chrome_bin(), "--headless", "--disable-gpu",
                    "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT}", f"file://{tmp}"], check=True)
    try:
        import fitz

        doc = fitz.open(str(OUT))
        print(f"{OUT.name}: {len(doc)} páginas "
              f"({OUT.stat().st_size/1000:.0f} kB)")
        if len(doc) != 2:
            print("⚠️  o folder deveria ter 2 páginas (frente e verso)")
    except ImportError:
        print(f"{OUT.name} gerado (pymupdf ausente; confira na mão)")


if __name__ == "__main__":
    main()
