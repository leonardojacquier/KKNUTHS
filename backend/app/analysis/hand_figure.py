"""Figura da mesa de poker — o spot do quiz como imagem, não só texto.

Desenho determinístico (PIL): custo zero de LLM, ~ms de CPU — o mesmo tipo de
render dos gráficos de range e do quadro do torneio. Mesa oval em feltro, seus
hole cards, o board da street atual, os vilões ativos com posição e stack, o
pote e o preço a pagar em destaque. Assina com a marca KKNuths.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from app.analysis.branding import GOLD, draw_brand

FELT = (30, 107, 74)
FELT_DK = (16, 58, 40)
RAIL = (54, 38, 24)
RAIL_HI = (120, 92, 52)
INK = (20, 26, 22)
CREAM = (238, 240, 234)
CARD_BG = (247, 248, 244)
RED = (192, 46, 46)
BLACK = (26, 30, 34)
CHIP = (208, 165, 92)

W, H = 900, 620
_DEJAVU = "/usr/share/fonts/truetype/dejavu/"

_SUIT = {"s": ("♠", BLACK), "c": ("♣", BLACK), "h": ("♥", RED), "d": ("♦", RED)}


def _font(size: int, bold: bool = True):
    from PIL import ImageFont

    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(_DEJAVU + name, size)
    except Exception:
        return ImageFont.load_default()


def _center(d, xy, text, font, fill):
    w = d.textlength(text, font=font)
    d.text((xy[0] - w / 2, xy[1]), text, font=font, fill=fill)


def _card(d, cx, cy, code, w=54, h=74, small=False):
    """Desenha uma carta (código tipo 'Ah'). cx,cy = canto superior esquerdo."""
    if not code or len(code) < 2:
        return
    rank, suit = code[0].upper().replace("T", "10"), code[1].lower()
    sym, col = _SUIT.get(suit, ("?", BLACK))
    d.rounded_rectangle([cx, cy, cx + w, cy + h], radius=7, fill=CARD_BG,
                        outline=(200, 204, 196), width=2)
    fr = _font(int(h * 0.42))
    fs = _font(int(h * 0.40))
    d.text((cx + 6, cy + 3), rank, font=fr, fill=col)
    sw = d.textlength(sym, font=fs)
    d.text((cx + w - sw - 5, cy + h - int(h * 0.46)), sym, font=fs, fill=col)


def _back(d, cx, cy, w=44, h=62):
    """Carta virada (vilão)."""
    d.rounded_rectangle([cx, cy, cx + w, cy + h], radius=6, fill=(58, 78, 120),
                        outline=(34, 48, 78), width=2)
    for i in range(3, w, 9):
        d.line([cx + i, cy + 4, cx + i, cy + h - 4], fill=(48, 66, 104), width=2)


def render_hand_figure(spot: dict) -> bytes:
    """`spot`: {hero_cards, board, position, stack_bb, pot_bb, to_call_bb,
    street, blinds, villains:[{pos, stack_bb, folded}], title}."""
    img = Image.new("RGB", (W, H), FELT_DK)
    d = ImageDraw.Draw(img)

    # rail + feltro oval
    pad = 46
    d.ellipse([pad - 10, pad - 10, W - pad + 10, H - 150 + 10],
              fill=RAIL, outline=RAIL_HI, width=6)
    ex0, ey0, ex1, ey1 = pad, pad, W - pad, H - 150
    d.ellipse([ex0, ey0, ex1, ey1], fill=FELT, outline=FELT_DK, width=4)
    cx, cy = (ex0 + ex1) / 2, (ey0 + ey1) / 2

    f_title = _font(24)
    f_pos = _font(17)
    f_small = _font(14, bold=False)
    f_pot = _font(22)

    # título
    _center(d, (W / 2, 12), spot.get("title") or "♠ Quiz — sua vez", f_title, CREAM)

    # board no centro
    board = spot.get("board") or []
    if board:
        bw, gap = 54, 10
        total = len(board) * bw + (len(board) - 1) * gap
        bx = cx - total / 2
        for c in board:
            _card(d, bx, cy - 78, c, w=bw, h=74)
            bx += bw + gap
    else:
        _center(d, (cx, cy - 40), "pré-flop", f_small, (210, 224, 216))

    # pote
    d.ellipse([cx - 70, cy + 14, cx + 70, cy + 52], fill=FELT_DK,
              outline=CHIP, width=2)
    _center(d, (cx, cy + 20), f"POTE {spot.get('pot_bb', 0):g} bb", f_pos, CHIP)

    # vilões ativos ao redor (arco superior)
    villains = [v for v in (spot.get("villains") or []) if not v.get("folded")][:6]
    n = len(villains)
    for i, v in enumerate(villains):
        ang = math.pi * (0.15 + 0.7 * (i / max(1, n - 1))) if n > 1 else math.pi / 2
        vx = cx - math.cos(ang) * (ex1 - ex0) * 0.40
        vy = ey0 + 30 + math.sin(ang) * 20
        _back(d, vx - 22, vy)
        d.rounded_rectangle([vx - 46, vy + 66, vx + 46, vy + 96], radius=8,
                            fill=FELT_DK, outline=(90, 120, 104), width=1)
        _center(d, (vx, vy + 69), v.get("pos") or "?", f_pos, CREAM)
        _center(d, (vx, vy + 88), f"{v.get('stack_bb', '?')}bb", f_small,
                (190, 206, 198))

    # HERÓI embaixo, no centro
    hx, hy = cx, ey1 - 30
    hc = spot.get("hero_cards") or []
    cw, cgap = 60, 12
    tot = len(hc) * cw + (len(hc) - 1) * cgap
    x0 = hx - tot / 2
    for c in hc:
        _card(d, x0, hy - 40, c, w=cw, h=82)
        x0 += cw + cgap
    d.rounded_rectangle([hx - 70, hy + 46, hx + 70, hy + 78], radius=9,
                        fill=GOLD, outline=(120, 92, 40), width=2)
    _center(d, (hx, hy + 50), f"VOCÊ · {spot.get('position') or '?'} · "
            f"{spot.get('stack_bb', '?')}bb", f_pos, INK)

    # rodapé: street + preço a pagar
    foot_y = H - 96
    street = (spot.get("street") or "").upper()
    blinds = spot.get("blinds") or ""
    _center(d, (W / 2, foot_y), f"{street}  ·  blinds {blinds}", f_small, CREAM)
    to_call = spot.get("to_call_bb")
    if to_call:
        req = spot.get("required_eq")
        txt = f"▶  pagar {to_call:g}bb"
        if req:
            txt += f"  (precisa de ~{req * 100:.0f}%)"
        d.rounded_rectangle([W / 2 - 190, foot_y + 26, W / 2 + 190, foot_y + 62],
                            radius=10, fill=(150, 40, 40), outline=CREAM, width=2)
        _center(d, (W / 2, foot_y + 32), txt, f_pot, CREAM)
    else:
        _center(d, (W / 2, foot_y + 30), "▶  sua vez — check ou bet?", f_pot, CHIP)

    draw_brand(d, H - 26, right=W - 20, size=15)

    import io

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def spot_from_drill(drill: dict) -> dict:
    """Converte o dict do /treino (build_drill) na spec da figura."""
    return {
        "title": "♠ Quiz — sua vez",
        "hero_cards": drill.get("cards") or [],
        "board": drill.get("board") or [],
        "position": drill.get("position"),
        "stack_bb": drill.get("stack_bb"),
        "pot_bb": drill.get("pot_bb"),
        "to_call_bb": drill.get("to_call_bb"),
        "required_eq": drill.get("required_eq"),
        "street": drill.get("street"),
        "blinds": drill.get("blinds"),
        "villains": drill.get("villains") or [],
    }
