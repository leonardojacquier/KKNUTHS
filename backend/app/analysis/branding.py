"""Assinatura de marca desenhada nos gráficos — o lockup da identidade.

Mesmo desenho do manual/folder: espada DOURADA + "KKNuths" em serifa escura
+ link discreto. Uma função só; todos os gráficos (ranges, quadro do torneio,
evolução, estilo) assinam igual.
"""
from __future__ import annotations

from PIL import ImageFont

GOLD = (166, 126, 53)
INK = (27, 33, 29)
GREY = (130, 138, 132)

_DEJAVU = "/usr/share/fonts/truetype/dejavu/"


def _font(name: str, size: int):
    try:
        return ImageFont.truetype(_DEJAVU + name, size)
    except Exception:
        return ImageFont.load_default()


def draw_brand(d, y: float, *, left: float | None = None,
               right: float | None = None, size: int = 15,
               link: bool = True) -> None:
    """Desenha "♠ KKNuths · t.me/KKNUts_BOT" ancorado à esquerda OU à direita.

    `size` é a altura do nome; espada e link escalam junto.
    """
    f_spade = _font("DejaVuSans-Bold.ttf", size + 2)
    f_name = _font("DejaVuSerif-Bold.ttf", size + 1)
    f_link = _font("DejaVuSans.ttf", max(10, size - 4))

    spade, name = "♠ ", "KKNuths"
    tail = "  ·  t.me/KKNUts_BOT" if link else ""
    total = (d.textlength(spade, font=f_spade) +
             d.textlength(name, font=f_name) +
             (d.textlength(tail, font=f_link) if tail else 0))
    x = (right - total) if right is not None else (left or 0)

    d.text((x, y - 1), spade, fill=GOLD, font=f_spade)
    x += d.textlength(spade, font=f_spade)
    d.text((x, y), name, fill=INK, font=f_name)
    x += d.textlength(name, font=f_name)
    if tail:
        d.text((x, y + (size - max(10, size - 4)) / 2 + 1), tail,
               fill=GREY, font=f_link)
