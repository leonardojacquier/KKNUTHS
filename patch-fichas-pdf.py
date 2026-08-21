#!/usr/bin/env python3
"""Troca, DENTRO dos PDFs já publicados, o logo GNH com o slogan pelo logo só
com as três letras, e as fotos de produto que foram substituídas no site (o
mapa FOTOS diz quais).

Por que patch e não regerar
---------------------------
Cada ficha PDF nasceu de um script ad-hoc (Chromium print-to-PDF de um HTML com
as imagens em base64). Só existem os scripts dos produtos publicados nesta
sessão — regerar as 102 exigiria reescrever a maioria deles, com risco de mudar
texto e paginação. Substituir o XObject de imagem pelo xref mantém o retângulo
de posicionamento, o texto e a paginação intactos.

Como o logo é trocado sem mexer no layout
-----------------------------------------
O logo com slogan e o logo só tem proporções diferentes (2,08 vs 2,72), então
não dá para trocar um pelo outro: o PDF esticaria a imagem no mesmo retângulo.
A saída é montar a substituta na MESMA dimensão em pixels do original e colar
a versão sem slogan na posição onde a marca já está — o slogan simplesmente sai
e o "GNH" fica exatamente onde estava. Os offsets vêm do bbox de alpha dos dois
arquivos: (15,15) no par 2000x957 e (2,2) no par 300x144, e a conferência
pixel a pixel do trecho de cima acusa <1% de diferença (antialias).

O que NÃO se toca
-----------------
O logo 276x107 das fichas cq-* é da CAMARGO QUÍMICA, não nosso. As demais
imagens são fotos de produto de outros equipamentos.
"""
import io
import os
import pathlib
import re
import shutil
import sys
import tempfile

import pymupdf
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parent
IMG = REPO / 'assets/nuevo/img'
PDFS = REPO / 'assets/nuevo/fichas/pdf'
TMP = pathlib.Path(tempfile.mkdtemp(prefix='fichas-pdf-'))

# (largura, altura) do XObject  ->  (arquivo sem slogan, offset da colagem)
LOGOS = {
    (2000, 957): ('logo-oficial-sola.png', (15, 15)),
    (300, 144): ('logo-ficha-sola.png', (2, 2)),
}

# fichas cujas fotos de produto mudaram: (arquivo, dimensao do XObject) -> foto nova
FOTOS = {
    ('regla-laser-ws940.pdf', (800, 600)): 'prod/ws940.png',
    ('regla-laser-ws940.pdf', (1147, 860)): 'prod/ws940c.jpg',
    ('alisadora-vs836.pdf', (1000, 896)): 'prod/alisadora-vs836.jpg',
    ('alisadora-vs836h.pdf', (1000, 938)): 'prod/alisadora-vs836h.jpg',
}

NAVY_MAX = 160  # luminancia media dos pixels opacos; acima disso e o logo branco


def luminancia_media(img):
    a, rgb = img.getchannel('A'), img.convert('RGB')
    tot = n = 0
    for y in range(0, img.height, 5):
        for x in range(0, img.width, 5):
            if a.getpixel((x, y)) > 200:
                r, g, b = rgb.getpixel((x, y))
                tot += (r + g + b) / 3
                n += 1
    return tot / max(n, 1)


def ja_sem_slogan(doc, info):
    """True se o logo desse XObject ja e a versao sem slogan.

    Sem isso, rodar o script duas vezes recodifica as fotos de novo (perda de
    qualidade a cada passagem). O teste e a faixa de baixo da mascara de alpha:
    no logo com slogan ela tem tinta, no logo so ela e transparente."""
    dim = (info[2], info[3])
    smask = info[1]
    if not smask:
        return False
    a = Image.open(io.BytesIO(doc.extract_image(smask)['image'])).convert('L')
    if a.size != dim:
        a = a.resize(dim)
    corte = LOGOS[dim][1][1] + Image.open(IMG / LOGOS[dim][0]).height
    return a.crop((0, corte, dim[0], dim[1])).getextrema()[1] <= 8


def logo_sem_slogan(dim):
    """logo só, montado na dimensao exata do original — o retangulo do PDF nao muda."""
    nome, off = LOGOS[dim]
    sola = Image.open(IMG / nome).convert('RGBA')
    tela = Image.new('RGBA', dim, (0, 0, 0, 0))
    tela.paste(sola, off)
    caminho = TMP / f'logo-{dim[0]}x{dim[1]}.png'
    tela.save(caminho)
    return caminho


def ja_e_a_foto_nova(doc, xref, rel, dim):
    """True se o XObject ja carrega a foto nova — mesma razao da guarda do logo:
    cada passagem recodifica o JPEG e perde qualidade."""
    try:
        atual = Image.open(io.BytesIO(doc.extract_image(xref)['image'])).convert('RGB')
    except Exception:
        return False
    nova = Image.open(IMG / rel)
    fundo = Image.new('RGB', nova.size, (255, 255, 255))
    fundo.paste(nova, mask=nova.getchannel('A') if nova.mode == 'RGBA' else None)
    p = (64, 48)
    a, b = atual.resize(p, Image.LANCZOS), fundo.resize(p, Image.LANCZOS)
    dif = sum(abs(x - y) for pa, pb in zip(a.getdata(), b.getdata()) for x, y in zip(pa, pb))
    return dif / (p[0] * p[1] * 3) < 6


def foto(rel, dim):
    """A foto nova nas dimensoes EXATAS do XObject que ela substitui.

    O retangulo no PDF tem a proporcao do XObject antigo, entao um resize
    direto esticaria a maquina (a foto nova da alisadora e 4:3 e o quadro
    antigo era 1,12). Encaixa preservando a proporcao e completa com branco —
    e o mesmo fundo da pagina, entao a faixa nao aparece.
    """
    im = Image.open(IMG / rel)
    if im.mode == 'RGBA' or 'transparency' in im.info:
        rgba = im.convert('RGBA')
        im = Image.new('RGB', rgba.size, (255, 255, 255))
        im.paste(rgba, mask=rgba.getchannel('A'))
    else:
        im = im.convert('RGB')
    if im.size != dim:
        esc = min(dim[0] / im.width, dim[1] / im.height)
        encaixe = im.resize((max(1, round(im.width * esc)), max(1, round(im.height * esc))),
                            Image.LANCZOS)
        im = Image.new('RGB', dim, (255, 255, 255))
        im.paste(encaixe, ((dim[0] - encaixe.width) // 2, (dim[1] - encaixe.height) // 2))
    caminho = TMP / ('foto-' + rel.replace('/', '-'))
    if caminho.suffix == '.jpg':
        im.save(caminho, 'JPEG', quality=88, optimize=True)
    else:
        im.save(caminho)
    return caminho



def limpa_xobjects_orfaos(doc, pagina):
    """replace_image deixa um segundo nome (fzImgN) apontando para uma copia da
    imagem nova no dicionario de recursos. O fluxo de conteudo nao desenha esse
    nome, mas o xref fica referenciado e o arquivo carrega a imagem duas vezes.
    Some com os nomes que nenhum operador `Do` usa; o garbage do save leva os
    xrefs junto."""
    usados = {m.decode() for m in re.findall(rb'/([A-Za-z0-9_.#-]+)\s+Do\b', pagina.read_contents())}
    tipo, valor = doc.xref_get_key(pagina.xref, 'Resources/XObject')
    if tipo == 'xref':
        dono, prefixo = int(valor.split()[0]), ''
    elif tipo == 'dict':
        dono, prefixo = pagina.xref, 'Resources/XObject/'
    else:
        return 0
    sobrando = [n for n in doc.xref_get_keys(dono) if n not in usados] if not prefixo \
        else [n for n in re.findall(r'/([A-Za-z0-9_.#-]+)', valor.split('>>')[0]) if n not in usados]
    for nome in sobrando:
        doc.xref_set_key(dono, prefixo + nome, 'null')
    return len(sobrando)


def main(so_conferir=False, apenas=None):
    TMP.mkdir(parents=True, exist_ok=True)
    prontos = {dim: logo_sem_slogan(dim) for dim in LOGOS}
    trocas = brancos = 0
    arquivos = sorted(f for f in os.listdir(PDFS) if f.endswith('.pdf'))
    if apenas:
        arquivos = [f for f in arquivos if f in apenas]

    for nome in arquivos:
        origem = PDFS / nome
        doc = pymupdf.open(origem)
        feitas = []
        vistos = set()
        for pagina in doc:
            for info in pagina.get_images(full=True):
                xref, dim = info[0], (info[2], info[3])
                if xref in vistos:
                    continue
                if dim in LOGOS:
                    if ja_sem_slogan(doc, info):
                        continue         # ja trocado numa passagem anterior
                    bruto = Image.open(io.BytesIO(doc.extract_image(xref)['image'])).convert('RGBA')
                    if luminancia_media(bruto) > NAVY_MAX:
                        brancos += 1     # versao branca: outro fundo, nao mexer
                        continue
                    vistos.add(xref)
                    pagina.replace_image(xref, filename=str(prontos[dim]))
                    feitas.append(f'logo {dim[0]}x{dim[1]}')
                elif (nome, dim) in FOTOS:
                    if ja_e_a_foto_nova(doc, xref, FOTOS[(nome, dim)], dim):
                        continue
                    vistos.add(xref)
                    pagina.replace_image(xref, filename=str(foto(FOTOS[(nome, dim)], dim)))
                    feitas.append('foto ' + FOTOS[(nome, dim)])
        if feitas:
            for pagina in doc:
                limpa_xobjects_orfaos(doc, pagina)
            trocas += len(feitas)
            if not so_conferir:
                saida = TMP / nome
                doc.save(saida, garbage=4, deflate=True)
                doc.close()
                shutil.copyfile(saida, origem)
            else:
                doc.close()
            print(f'{nome:38} {", ".join(feitas)}')
        else:
            doc.close()
            print(f'{nome:38} — nada a trocar')
    print(f'\n{trocas} substituicoes; {brancos} logo(s) branco(s) preservado(s)')


if __name__ == '__main__':
    main(so_conferir='--conferir' in sys.argv,
         apenas=set(a for a in sys.argv[1:] if a.endswith('.pdf')) or None)
