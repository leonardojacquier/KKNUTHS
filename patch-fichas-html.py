#!/usr/bin/env python3
"""Troca o logo GNH embutido em base64 nas fichas HTML pela versao sem slogan.

As fichas de assets/nuevo/fichas/ carregam o logo como data:image/png;base64
dentro do proprio HTML — nao ha arquivo para trocar. A substituta e montada na
MESMA dimensao em pixels do original, com a versao sem slogan colada na posicao
onde a marca ja esta: o retangulo nao muda, o slogan sai, o "GNH" fica onde
estava. O logo 276x107 das fichas cq-* e da CAMARGO QUIMICA e nao se toca.
"""
import base64
import io
import pathlib

from PIL import Image

REPO = pathlib.Path(__file__).resolve().parent
IMG = REPO / 'assets/nuevo/img'
FICHAS = REPO / 'assets/nuevo/fichas'

# arquivo com slogan -> (arquivo so, offset da colagem)
PARES = {
    'logo-oficial.png': ('logo-oficial-sola.png', (15, 15)),
    'logo-ficha.png': ('logo-ficha-sola.png', (2, 2)),
}


def b64(caminho_ou_img):
    if isinstance(caminho_ou_img, Image.Image):
        buf = io.BytesIO()
        caminho_ou_img.save(buf, 'PNG', optimize=True)
        dados = buf.getvalue()
    else:
        dados = pathlib.Path(caminho_ou_img).read_bytes()
    return base64.b64encode(dados).decode()


def main():
    trocas = {}
    for com, (so, off) in PARES.items():
        base = Image.open(IMG / com)
        sola = Image.open(IMG / so).convert('RGBA')
        tela = Image.new('RGBA', base.size, (0, 0, 0, 0))
        tela.paste(sola, off)
        trocas[b64(IMG / com)] = (b64(tela), com)

    total = 0
    for f in sorted(FICHAS.glob('*.html')):
        s = original = f.read_text(encoding='utf-8')
        feitas = []
        for antigo, (novo, nome) in trocas.items():
            if antigo in s:
                feitas.append(f'{nome} x{s.count(antigo)}')
                s = s.replace(antigo, novo)
        if s != original:
            f.write_text(s, encoding='utf-8')
            total += 1
            print(f'{f.name:42} {", ".join(feitas)}')
    print(f'\n{total} fichas HTML atualizadas')


if __name__ == '__main__':
    main()
