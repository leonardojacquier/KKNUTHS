"""Figura da mesa de poker — o spot do quiz como imagem, não só texto.

Desenho determinístico (PIL): custo zero de LLM, ~ms de CPU — o mesmo tipo de
render dos gráficos de range e do quadro do torneio. Mesa oval com os assentos
nas posições reais, botão do dealer, board no centro, pote em fichas, herói
destacado embaixo, vilões (ativos/foldados) ao redor. Assina KKNuths.
"""
from __future__ import annotations

import io
import math

from PIL import Image, ImageDraw, ImageFilter

from app.analysis.branding import draw_brand

# paleta
BG = (18, 40, 32)
FELT = (34, 116, 82)
FELT_HI = (44, 138, 100)
FELT_RIM = (18, 66, 48)
RAIL = (46, 32, 20)
RAIL_HI = (150, 116, 66)
CREAM = (240, 242, 236)
MUTED = (150, 168, 158)
CARD_BG = (248, 249, 245)
CARD_EDGE = (206, 210, 202)
RED = (198, 52, 52)
BLACK = (32, 36, 40)
GOLD = (208, 168, 92)
GOLD_DK = (150, 112, 46)
CHIP_RED = (176, 58, 58)
CHIP_BLU = (52, 84, 140)
PLAQUE = (22, 52, 40)
PLAQUE_FOLD = (26, 34, 30)
BTN_BG = (244, 242, 232)

W, H = 980, 700
_DEJAVU = "/usr/share/fonts/truetype/dejavu/"
_SUIT = {"s": ("♠", BLACK), "c": ("♣", BLACK), "h": ("♥", RED), "d": ("♦", RED)}


def _font(size: int, bold: bool = True):
    from PIL import ImageFont

    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(_DEJAVU + name, size)
    except Exception:
        return ImageFont.load_default()


def _center(d, cx, y, text, font, fill):
    d.text((cx - d.textlength(text, font=font) / 2, y), text, font=font, fill=fill)


def _card(d, cx, cy, code, w=58, h=80):
    """Carta centrada em (cx, cy). code tipo 'Ah'."""
    if not code or len(code) < 2:
        return
    x0, y0 = cx - w / 2, cy - h / 2
    rank = code[0].upper().replace("T", "10")
    sym, col = _SUIT.get(code[1].lower(), ("?", BLACK))
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8, fill=CARD_BG,
                        outline=CARD_EDGE, width=2)
    fr = _font(int(h * 0.40))
    d.text((x0 + 7, y0 + 4), rank, font=fr, fill=col)
    fs = _font(int(h * 0.34))
    sw = d.textlength(sym, font=fs)
    d.text((x0 + 7, y0 + h * 0.44), sym, font=fs, fill=col)
    fb = _font(int(h * 0.5))
    bw = d.textlength(sym, font=fb)
    d.text((x0 + w - bw - 6, y0 + h - int(h * 0.62)), sym, font=fb, fill=col)


def _card_back(d, cx, cy, w=30, h=42):
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=5, fill=(62, 86, 132),
                        outline=(30, 44, 76), width=2)
    d.rounded_rectangle([x0 + 4, y0 + 4, x0 + w - 4, y0 + h - 4], radius=3,
                        outline=(94, 120, 168), width=1)


def _chips(d, cx, cy):
    """Pilhazinha de fichas ao lado do pote."""
    for i, col in enumerate((CHIP_BLU, CHIP_RED, GOLD_DK)):
        yy = cy - i * 5
        d.ellipse([cx - 16, yy - 7, cx + 16, yy + 7], fill=col,
                  outline=(20, 24, 22), width=1)
    d.ellipse([cx - 16, cy - 5 * 2 - 7, cx + 16, cy - 5 * 2 + 7], fill=CREAM,
              outline=(20, 24, 22), width=1)


def _seat(d, x, y, pos, stack_bb, *, hero=False, folded=False, cards=None,
          to_act=False):
    """Plaque de um assento em (x, y) = centro do plaque."""
    pw, ph = (150, 52) if hero else (118, 46)
    fill = GOLD if hero else (PLAQUE_FOLD if folded else PLAQUE)
    edge = GOLD_DK if hero else (RAIL_HI if to_act else (60, 84, 70))
    d.rounded_rectangle([x - pw / 2, y - ph / 2, x + pw / 2, y + ph / 2],
                        radius=11, fill=fill, outline=edge,
                        width=3 if (hero or to_act) else 1)
    ftop = _font(19 if hero else 16)
    fbot = _font(15 if hero else 13, bold=False)
    tcol = (26, 30, 24) if hero else (MUTED if folded else CREAM)
    scol = (60, 50, 24) if hero else (110, 124, 116) if folded else GOLD
    label = ("VOCÊ · " + (pos or "?")) if hero else (pos or "?")
    _center(d, x, y - ph / 2 + (7 if hero else 6), label, ftop, tcol)
    sub = "fold" if folded else f"{stack_bb:g}bb" if stack_bb is not None else ""
    _center(d, x, y + (2 if hero else 1), sub, fbot, scol)

    # cartas acima do plaque
    if hero and cards:
        cw = 62
        for i, c in enumerate(cards[:2]):
            _card(d, x - (len(cards[:2]) - 1) * (cw + 8) / 2 + i * (cw + 8),
                  y - ph / 2 - 52, c, w=cw, h=86)
    elif not folded:
        for i in range(2):
            _card_back(d, x - 18 + i * 20, y - ph / 2 - 26)


def render_hand_figure(spot: dict) -> bytes:
    """`spot`: hero_cards, board, position, stack_bb, pot_bb, to_call_bb,
    required_eq, street, blinds, villains:[{pos, stack_bb, folded, to_act}]."""
    # supersample 2x para bordas suaves
    S = 2
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)

    def sc(v):
        return v * S

    # rail + feltro
    m = 70
    rx0, ry0, rx1, ry1 = m - 16, 96, W - m + 16, H - 168
    d.rounded_rectangle([sc(rx0), sc(ry0), sc(rx1), sc(ry1)], radius=sc(230),
                        fill=RAIL, outline=RAIL_HI, width=sc(5))
    fx0, fy0, fx1, fy1 = m, 112, W - m, H - 184
    d.rounded_rectangle([sc(fx0), sc(fy0), sc(fx1), sc(fy1)], radius=sc(210),
                        fill=FELT, outline=FELT_RIM, width=sc(6))
    # brilho interno do feltro
    d.rounded_rectangle([sc(fx0 + 26), sc(fy0 + 22), sc(fx1 - 26), sc(fy1 - 22)],
                        radius=sc(185), outline=FELT_HI, width=sc(2))
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2

    f_title = _font(int(26))
    f_small = _font(int(15), bold=False)
    f_pot = _font(int(20))
    f_ask = _font(int(24))

    _center(d, sc(W / 2), sc(20), spot.get("title") or "Quiz — sua vez",
            _font(int(26)), CREAM)

    # board
    board = spot.get("board") or []
    if board:
        bw, gap = 60, 12
        total = len(board) * bw + (len(board) - 1) * gap
        bx = cx - total / 2 + bw / 2
        for c in board:
            _card(d, sc(bx), sc(cy - 34), c, w=sc(bw), h=sc(bw * 1.4))
            bx += bw + gap
    else:
        _center(d, sc(cx), sc(cy - 30), "PRÉ-FLOP", _font(int(20)), (200, 220, 210))

    # pote (fichas + label) abaixo do board
    _chips_xy = (cx - 96, cy + 52)
    for i, col in enumerate((CHIP_BLU, CHIP_RED, GOLD_DK, CREAM)):
        yy = _chips_xy[1] - i * 6
        d.ellipse([sc(_chips_xy[0] - 17), sc(yy - 7),
                   sc(_chips_xy[0] + 17), sc(yy + 7)], fill=col,
                  outline=(18, 22, 20), width=sc(1))
    d.rounded_rectangle([sc(cx - 66), sc(cy + 36), sc(cx + 112), sc(cy + 72)],
                        radius=sc(16), fill=FELT_RIM, outline=GOLD_DK, width=sc(2))
    _center(d, sc(cx + 23), sc(cy + 44),
            f"POTE  {spot.get('pot_bb', 0):g} bb", _font(int(19)), GOLD)

    # assentos ao redor: herói embaixo, vilões distribuídos no arco de cima
    villains = list(spot.get("villains") or [])[:7]
    a, b = (fx1 - fx0) / 2 * 0.98, (fy1 - fy0) / 2 * 1.06
    # herói no fundo
    _seat(d, sc(cx), sc(fy1 - 6), spot.get("position"), spot.get("stack_bb"),
          hero=True, cards=spot.get("hero_cards"))
    # vilões no ARCO SUPERIOR (270° = topo; espalha de 205° a 335°)
    n = len(villains)
    if n:
        lo, hi = 205, 335
        for i, v in enumerate(villains):
            t = (lo + (hi - lo) * (i / (n - 1))) if n > 1 else 270
            rad = math.radians(t)
            vx = cx + a * 0.92 * math.cos(rad)
            vy = cy + b * 0.98 * math.sin(rad)
            _seat(d, sc(vx), sc(vy), v.get("pos"), v.get("stack_bb"),
                  folded=bool(v.get("folded")), to_act=bool(v.get("to_act")))

    # rodapé: street/blinds + preço
    fy = H - 150
    street = (spot.get("street") or "").upper()
    blinds = spot.get("blinds") or ""
    _center(d, sc(W / 2), sc(fy), f"{street}   ·   blinds {blinds}",
            _font(int(15), bold=False), MUTED)
    to_call = spot.get("to_call_bb")
    by = fy + 30
    if to_call:
        req = spot.get("required_eq")
        txt = f"pagar {to_call:g} bb"
        if req:
            txt += f"   ·   precisa de ~{req * 100:.0f}%"
        d.rounded_rectangle([sc(W / 2 - 230), sc(by), sc(W / 2 + 230), sc(by + 46)],
                            radius=sc(14), fill=(158, 44, 44),
                            outline=CREAM, width=sc(2))
        _center(d, sc(W / 2), sc(by + 10), txt, _font(int(23)), CREAM)
    else:
        d.rounded_rectangle([sc(W / 2 - 210), sc(by), sc(W / 2 + 210), sc(by + 46)],
                            radius=sc(14), fill=FELT_RIM, outline=GOLD, width=sc(2))
        _center(d, sc(W / 2), sc(by + 10), "sua vez — check ou bet?",
                _font(int(23)), GOLD)

    # downsample (antialias) e marca
    img = img.resize((W, H), Image.LANCZOS)
    d2 = ImageDraw.Draw(img)
    draw_brand(d2, H - 30, right=W - 22, size=15)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def spot_from_drill(drill: dict) -> dict:
    """Converte o dict do /treino (build_drill) na spec da figura."""
    return {
        "title": "Quiz — sua vez",
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


def render_hand_strip(spec: dict) -> bytes:
    """Sequência da mão em UMA imagem (storyboard vertical): cabeçalho com as
    cartas do herói + uma faixa por street (board + ações + pote). Custo zero
    de LLM. spec: {title, hero_cards, position, stack_bb, blinds, result,
    streets:[{name, board, lines:[str], pot_bb}]}."""
    streets = spec.get("streets") or []
    SW = 820
    head_h = 174
    band_h = 132
    foot_h = 64
    SH = head_h + band_h * len(streets) + foot_h
    S = 2
    img = Image.new("RGB", (SW * S, SH * S), BG)
    d = ImageDraw.Draw(img)

    def sc(v):
        return v * S

    # cabeçalho
    d.rectangle([0, 0, sc(SW), sc(head_h)], fill=FELT_RIM)
    _center(d, sc(SW / 2), sc(16), spec.get("title") or "Sequência da mão",
            _font(int(24)), CREAM)
    hc = spec.get("hero_cards") or []
    cwid = 60
    x0 = SW / 2 - (len(hc) * cwid + (len(hc) - 1) * 10) / 2 + cwid / 2
    for c in hc:
        _card(d, sc(x0), sc(78), c, w=sc(cwid), h=sc(82))
        x0 += cwid + 10
    _center(d, sc(SW / 2), sc(head_h - 30),
            f"VOCÊ · {spec.get('position') or '?'} · "
            f"{spec.get('stack_bb', '?')}bb · blinds {spec.get('blinds') or ''}",
            _font(int(15), bold=False), GOLD)

    y = head_h
    for i, st in enumerate(streets):
        bg = FELT if i % 2 == 0 else FELT_HI
        d.rectangle([0, sc(y), sc(SW), sc(y + band_h)], fill=bg)
        d.line([0, sc(y), sc(SW), sc(y)], fill=FELT_RIM, width=sc(1))
        # coluna esquerda: nome + board
        _center(d, sc(120), sc(y + 12), (st.get("name") or "").upper(),
                _font(int(18)), CREAM)
        board = st.get("board") or []
        bw = 44
        bx = 120 - (len(board) * bw + (len(board) - 1) * 6) / 2 + bw / 2
        for c in board:
            _card(d, sc(bx), sc(y + band_h / 2 + 14), c, w=sc(bw), h=sc(bw * 1.4))
            bx += bw + 6
        if not board:
            _center(d, sc(120), sc(y + band_h / 2), "— sem board —",
                    _font(int(13), bold=False), (210, 226, 218))
        # divisória
        d.line([sc(238), sc(y + 14), sc(238), sc(y + band_h - 14)],
               fill=FELT_RIM, width=sc(1))
        # coluna direita: ações
        ly = y + 18
        for ln in (st.get("lines") or [])[:4]:
            d.text((sc(262), sc(ly)), "• " + ln, font=_font(int(16), bold=False),
                   fill=CREAM)
            ly += 24
        # pote da street
        pot = st.get("pot_bb")
        if pot is not None:
            _center(d, sc(SW - 78), sc(y + band_h - 30),
                    f"pote {pot:g}bb", _font(int(15)), GOLD)
        y += band_h

    # rodapé: resultado + marca
    d.rectangle([0, sc(y), sc(SW), sc(SH)], fill=FELT_RIM)
    if spec.get("result"):
        _center(d, sc(SW / 2), sc(y + 12), spec["result"], _font(int(16)), CREAM)

    img = img.resize((SW, SH), Image.LANCZOS)
    d2 = ImageDraw.Draw(img)
    draw_brand(d2, SH - 26, right=SW - 20, size=14)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
