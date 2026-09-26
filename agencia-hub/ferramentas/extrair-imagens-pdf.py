#!/usr/bin/env python3
"""Extrai as imagens de um PDF (com transparência, quando o PDF tem máscara) para uma pasta.

Uso: python3 ferramentas/extrair-imagens-pdf.py catalogo.pdf pasta-saida [--min 300]

Salva p<página>_x<xref>.png e imprime tamanho e posição na página, para escolher a foto
principal de cada produto. Instalar: pip install pymupdf
"""
import sys, pathlib
import pymupdf

if len(sys.argv) < 3: sys.exit(__doc__)
pdf, out = sys.argv[1], pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
minimo = int(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else 300
d = pymupdf.open(pdf)
for i, p in enumerate(d):
    for im in p.get_images(full=True):
        xref, smask = im[0], im[1]
        try:
            pix = pymupdf.Pixmap(d, xref)
            if pix.alpha: pix = pymupdf.Pixmap(pix, 0)
            if pix.colorspace and pix.colorspace.n != 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            if smask: pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(d, smask))
            if max(pix.width, pix.height) < minimo: continue
            fn = out / f'p{i + 1:02d}_x{xref}.png'; pix.save(fn)
            r = p.get_image_rects(xref)
            print(fn.name, f'{pix.width}x{pix.height}', 'transparente' if smask else '', [round(v) for v in r[0]] if r else '')
        except Exception as e:
            print(f'p{i + 1} x{xref}: erro {e}')
