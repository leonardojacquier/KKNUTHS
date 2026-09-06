"""Assinatura de marca desenhada nos gráficos — o lockup da identidade.

Mesmo desenho do manual/folder: espada DOURADA + "KKNuths" em serifa escura
+ link discreto. Uma função só; todos os gráficos (ranges, quadro do torneio,
evolução, estilo) assinam igual.
"""
from __future__ import annotations

import os

from PIL import ImageFont

GOLD = (166, 126, 53)
INK = (27, 33, 29)
GREY = (130, 138, 132)

_DEJAVU = "/usr/share/fonts/truetype/dejavu/"
_LOGO = os.path.join(os.path.dirname(__file__), "..", "api", "assets",
                     "logo_avatar.png")


def paste_logo(img, right: float, top: float, size: int = 46) -> None:
    """Cola o emblema KKNuths (avatar) ancorado pela borda DIREITA em (right,
    top). Silencioso se o asset sumir. Todo gráfico leva a marca."""
    try:
        from PIL import Image

        logo = Image.open(_LOGO).convert("RGBA").resize(
            (int(size), int(size)), Image.LANCZOS)
        img.paste(logo, (int(right - size), int(top)), logo)
    except Exception:
        pass


def _font(name: str, size: int):
    try:
        return ImageFont.truetype(_DEJAVU + name, size)
    except Exception:
        return ImageFont.load_default()


def draw_brand(d, y: float, *, left: float | None = None,
               right: float | None = None, size: int = 15,
               link: bool = True, light: bool = False) -> None:
    """Desenha "♠ KKNuths · t.me/KKNUts_BOT" ancorado à esquerda OU à direita.

    `size` é a altura do nome; espada e link escalam junto.
    `light=True` para fundos ESCUROS (mesa/storyboard): nome creme e espada
    dourada clara — senão a marca some no verde escuro.
    """
    f_spade = _font("DejaVuSans-Bold.ttf", size + 2)
    f_name = _font("DejaVuSerif-Bold.ttf", size + 1)
    f_link = _font("DejaVuSans.ttf", max(10, size - 4))
    c_spade = (208, 168, 92) if light else GOLD
    c_name = (240, 242, 236) if light else INK
    c_link = (150, 168, 158) if light else GREY

    spade, name = "♠ ", "KKNuths"
    tail = "  ·  t.me/KKNUts_BOT" if link else ""
    total = (d.textlength(spade, font=f_spade) +
             d.textlength(name, font=f_name) +
             (d.textlength(tail, font=f_link) if tail else 0))
    x = (right - total) if right is not None else (left or 0)

    d.text((x, y - 1), spade, fill=c_spade, font=f_spade)
    x += d.textlength(spade, font=f_spade)
    d.text((x, y), name, fill=c_name, font=f_name)
    x += d.textlength(name, font=f_name)
    if tail:
        d.text((x, y + (size - max(10, size - 4)) / 2 + 1), tail,
               fill=c_link, font=f_link)
