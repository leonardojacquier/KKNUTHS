#!/usr/bin/env python3
"""Recorta o fundo de uma foto de produto e salva no padrão do catálogo (PNG 800×600, transparente).

Uso:
    python3 ferramentas/recortar-fundo.py foto.jpg saida.png
    python3 ferramentas/recortar-fundo.py foto.jpg saida.png --branco   # só limiar de branco (foto de estúdio)

Sem --branco usa o modelo BiRefNet (rembg), bom para foto em cena (pátio, galpão, céu).
Instalar: pip install rembg onnxruntime pillow numpy scipy
Rode UMA imagem por vez: o BiRefNet pode derrubar o Python na segunda inferência do mesmo processo.
"""
import sys
import numpy as np
from PIL import Image, ImageChops, ImageFilter
from scipy import ndimage

def alfa_branco(im, nucleo=253, halo=240):
    a = np.array(im.convert('RGB')).astype(int); mn = a.min(axis=2)
    fundo = ndimage.binary_propagation(mn >= nucleo, mask=mn >= halo)
    al = np.where(fundo, 0, 255).astype(np.uint8)
    al = np.array(Image.fromarray(al).filter(ImageFilter.GaussianBlur(1.2)))
    return Image.fromarray(np.dstack([a.astype(np.uint8), al]), 'RGBA')

def maior_bloco(im):
    a = np.array(im.getchannel('A')) > 20
    lab, n = ndimage.label(ndimage.binary_dilation(a, iterations=6))
    if n <= 1: return im
    k = int(np.argmax(ndimage.sum(a, lab, range(1, n + 1)))) + 1
    arr = np.array(im); arr[..., 3] = np.where((lab == k) & a, arr[..., 3], 0)
    return Image.fromarray(arr)

def encaixa(im, larg=800, alt=600, margem=0.035):
    im = im.convert('RGBA'); im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
    e = min(larg * (1 - 2 * margem) / im.width, alt * (1 - 2 * margem) / im.height)
    w, h = max(1, round(im.width * e)), max(1, round(im.height * e))
    r, g, b, a = im.split()
    pre = Image.merge('RGB', [ImageChops.multiply(c, a) for c in (r, g, b)]).resize((w, h), Image.LANCZOS); a = a.resize((w, h), Image.LANCZOS)
    pa = np.array(pre).astype(np.int32); aa = np.array(a).astype(np.int32)
    rgb = np.where(aa[..., None] > 0, np.minimum(255, pa * 255 // np.maximum(aa[..., None], 1)), 0).astype(np.uint8)
    tela = Image.new('RGBA', (larg, alt), (0, 0, 0, 0))
    tela.paste(Image.fromarray(np.dstack([rgb, aa.astype(np.uint8)]), 'RGBA'), ((larg - w) // 2, (alt - h) // 2))
    return tela

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    im = Image.open(src)
    if '--branco' in sys.argv:
        rgba = alfa_branco(im)
    elif im.mode == 'RGBA' and np.array(im.getchannel('A')).min() < 250:
        rgba = im  # já tem transparência
    else:
        from rembg import remove, new_session
        rgba = remove(im.convert('RGB'), session=new_session('birefnet-general'))
    out = encaixa(maior_bloco(rgba.convert('RGBA')))
    out.quantize(colors=255, method=Image.FASTOCTREE, dither=Image.FLOYDSTEINBERG).save(dst, optimize=True)
    print('ok:', dst)
