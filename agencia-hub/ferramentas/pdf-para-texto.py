#!/usr/bin/env python3
"""Extrai o texto de um PDF, página por página, e renderiza cada página em PNG para leitura.

Uso: python3 ferramentas/pdf-para-texto.py arquivo.pdf pasta-saida [--dpi 140]

Gera texto.txt (com "===== PÁGINA N" entre páginas) e pNN.png. Quando as tabelas do PDF
são imagem, o texto sai vazio: leia os PNG e transcreva à mão (não confie em OCR para números).
Instalar: pip install pymupdf
"""
import sys, pathlib
import pymupdf

if len(sys.argv) < 3: sys.exit(__doc__)
pdf, out = sys.argv[1], pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
dpi = int(sys.argv[sys.argv.index('--dpi') + 1]) if '--dpi' in sys.argv else 140
d = pymupdf.open(pdf); partes = []
for i, p in enumerate(d):
    t = p.get_text(); partes.append(f'===== PÁGINA {i + 1} ({len(t)} caracteres, {len(p.get_images())} imagens)\n{t}')
    p.get_pixmap(dpi=dpi).save(out / f'p{i + 1:02d}.png')
(out / 'texto.txt').write_text('\n'.join(partes), encoding='utf-8')
print(f'{len(d)} páginas -> {out}/texto.txt e p01..p{len(d):02d}.png')
