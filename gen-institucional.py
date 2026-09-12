#!/usr/bin/env python3
"""Gera assets/nuevo/institucional/index.html a partir de gnh-redesign.html.

Por que existe
--------------
O `gnh-redesign.html` é a página INSTITUCIONAL. Ela é servida em dois lugares,
com raízes diferentes, e por isso os caminhos precisam ser reescritos:

    gnh.vortex369.com.br/           root /opt/gnh                (preview)
    gnhorizons.com/institucional/   root /opt/gnh/assets/nuevo   (público)

No preview o arquivo vai para a raiz e os caminhos relativos
(`assets/video/...`, `assets/nuevo/img/...`) resolvem sozinhos. Publicado em
`/institucional/`, os mesmos caminhos apontariam para
`/institucional/assets/...`, que não existe — o vídeo do hero e as fotos das
plataformas morreriam.

Três regras dão conta, e são as mesmas que a versão publicada já usava:

    assets/video/   -> /assets/video/    (o bloco `handle /assets/video/*` do
    assets/img/     -> /assets/img/       Caddy serve os dois a partir de /opt/gnh)
    assets/nuevo/   -> /                 (a raiz do domínio JÁ é assets/nuevo)

Uso
---
    python3 gen-institucional.py

Rode sempre que mexer no gnh-redesign.html e faça commit do resultado — sem
isso a edição chega ao preview mas não ao gnhorizons.com/institucional/.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent
SRC = REPO / 'gnh-redesign.html'
DST = REPO / 'assets/nuevo/institucional/index.html'
CANONICAL = 'https://gnhorizons.com/institucional/'

# ordem importa: a forma absoluta de assets/nuevo tem de sair antes da relativa
REGRAS = [
    ('/assets/nuevo/', '/'),
    ('"assets/nuevo/', '"/'),
    ("'assets/nuevo/", "'/"),
    ('"assets/video/', '"/assets/video/'),
    ("'assets/video/", "'/assets/video/"),
    ('"assets/img/', '"/assets/img/'),
    ("'assets/img/", "'/assets/img/"),
]


def main() -> int:
    html = SRC.read_text(encoding='utf-8')
    if '</html>' not in html:
        print(f'ERRO: {SRC.name} parece truncado', file=sys.stderr)
        return 1

    for antes, depois in REGRAS:
        html = html.replace(antes, depois)

    # a página publicada é /institucional/, não a raiz do domínio
    html = html.replace('<link rel="canonical" href="https://gnhorizons.com/">',
                        f'<link rel="canonical" href="{CANONICAL}">')
    html = html.replace('<meta property="og:url" content="https://gnhorizons.com/">',
                        f'<meta property="og:url" content="{CANONICAL}">')

    # nenhum caminho relativo a assets/ pode sobrar: em /institucional/ eles
    # resolveriam para /institucional/assets/..., que não existe
    sobrou = sorted({m.group(1) for m in re.finditer(r'["\'](assets/[^"\']+)', html)})
    if sobrou:
        print('ERRO: caminhos relativos não reescritos:', file=sys.stderr)
        for s in sobrou:
            print('   ', s, file=sys.stderr)
        return 1

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(html, encoding='utf-8')
    print(f'{DST.relative_to(REPO)}  ({len(html) // 1024} KB)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
