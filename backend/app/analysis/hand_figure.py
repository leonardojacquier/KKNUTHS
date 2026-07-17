"""Figura da mesa de poker — o spot do quiz como imagem, não só texto.

Desenho determinístico (PIL): custo zero de LLM, ~ms de CPU — o mesmo tipo de
render dos gráficos de range e do quadro do torneio. Mesa oval com os assentos
nas posições reais, botão do dealer, board no centro, pote em fichas, herói
destacado embaixo, vilões (ativos/foldados) ao redor. Assina KKNuths.
"""
from __future__ import annotations

import io
import math
import os

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

W, H = 980, 840
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


def _bet_marker(d, x, y, bet_bb, s):
    """Fichas + '⬆ X bb' de uma aposta, centradas em (x, y) — coords do canvas."""
    for i, col in enumerate((CHIP_BLU, CHIP_RED, GOLD)):
        yy = y - i * 4 * s
        d.ellipse([x - 15 * s, yy - 8 * s, x + 15 * s, yy + 8 * s], fill=col,
                  outline=(18, 22, 20), width=max(1, s))
    f = _font(int(18 * s))
    txt = f"aposta {bet_bb:g}bb"
    tw = d.textlength(txt, font=f)
    d.rounded_rectangle([x - tw / 2 - 10 * s, y + 12 * s,
                         x + tw / 2 + 10 * s, y + 12 * s + 30 * s],
                        radius=9 * s, fill=(158, 44, 44), outline=CREAM,
                        width=max(1, s))
    _center(d, x, y + 15 * s, txt, f, CREAM)


def _seat(d, x, y, pos, stack_bb, *, hero=False, folded=False, cards=None,
          to_act=False, bet_bb=None, s=2, bet_below=True):
    """Plaque de um assento centrado em (x, y), já em coords do canvas s×.
    Todas as dimensões escalam por `s` — sem isso o assento sai na metade."""
    pw, ph = ((156, 58) if hero else (128, 52))
    pw, ph = pw * s, ph * s
    fill = GOLD if hero else (PLAQUE_FOLD if folded else PLAQUE)
    edge = GOLD_DK if hero else (RAIL_HI if to_act else (60, 84, 70))
    d.rounded_rectangle([x - pw / 2, y - ph / 2, x + pw / 2, y + ph / 2],
                        radius=12 * s, fill=fill, outline=edge,
                        width=(4 if (hero or to_act) else 1) * s)
    ftop = _font(int((22 if hero else 19) * s))
    fbot = _font(int((18 if hero else 16) * s), bold=False)
    tcol = (26, 30, 24) if hero else (MUTED if folded else CREAM)
    scol = (60, 50, 24) if hero else (110, 124, 116) if folded else GOLD
    label = ("VOCÊ · " + (pos or "?")) if hero else (pos or "?")
    _center(d, x, y - ph / 2 + 8 * s, label, ftop, tcol)
    sub = "fold" if folded else f"{stack_bb:g}bb" if stack_bb is not None else ""
    _center(d, x, y + 3 * s, sub, fbot, scol)

    # cartas acima do plaque: herói mostra as cartas; vilão ATIVO mostra o
    # verso (2 cartas fechadas); vilão que foldou não mostra nada (só "fold")
    if hero and cards:
        cw = 70 * s
        for i, c in enumerate(cards[:2]):
            _card(d, x - (len(cards[:2]) - 1) * (cw + 10 * s) / 2 + i * (cw + 10 * s),
                  y - ph / 2 - 58 * s, c, w=cw, h=cw * 1.4)
    elif not hero and not folded:
        for i in range(2):
            _card_back(d, x - 19 * s + i * 22 * s, y - ph / 2 - 27 * s,
                       w=34 * s, h=46 * s)

    # aposta do vilão: fichas na frente (em direção ao centro = abaixo do plaque)
    if bet_bb and not hero:
        _bet_marker(d, x, y + ph / 2 + 18 * s, bet_bb, s)


def _dealer_button(d, x, y, s):
    """Disco 'D' do dealer ao lado do assento do BTN."""
    r = 13 * s
    d.ellipse([x - r, y - r, x + r, y + r], fill=BTN_BG,
              outline=(120, 110, 80), width=max(1, s))
    f = _font(int(15 * s))
    w = d.textlength("D", font=f)
    d.text((x - w / 2, y - 9 * s), "D", font=f, fill=(60, 50, 20))


def render_hand_figure(spot: dict) -> bytes:
    """`spot`: hero_cards, board, position, stack_bb, pot_bb, to_call_bb,
    required_eq, street, blinds, villains:[{pos, stack_bb, folded, to_act,
    bet_bb}]."""
    # supersample 2x para bordas suaves
    S = 2
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)

    def sc(v):
        return v * S

    def F(sz, bold=True):        # fonte no tamanho REAL (escala com o supersample)
        return _font(int(sz * S), bold)

    # rail + feltro
    m = 66
    rx0, ry0, rx1, ry1 = m - 16, 104, W - m + 16, H - 196
    d.rounded_rectangle([sc(rx0), sc(ry0), sc(rx1), sc(ry1)], radius=sc(230),
                        fill=RAIL, outline=RAIL_HI, width=sc(5))
    fx0, fy0, fx1, fy1 = m, 120, W - m, H - 212
    d.rounded_rectangle([sc(fx0), sc(fy0), sc(fx1), sc(fy1)], radius=sc(210),
                        fill=FELT, outline=FELT_RIM, width=sc(6))
    d.rounded_rectangle([sc(fx0 + 26), sc(fy0 + 22), sc(fx1 - 26), sc(fy1 - 22)],
                        radius=sc(185), outline=FELT_HI, width=sc(2))
    cx = (fx0 + fx1) / 2

    _center(d, sc(W / 2), sc(22), spot.get("title") or "Quiz — sua vez",
            F(30), CREAM)

    # BANDAS VERTICAIS FIXAS (sem sobreposição): vilões no topo, board no meio,
    # pote abaixo, herói embaixo. y explícito — nada de colisão aposta×board.
    VILL_Y = fy0 + 82      # linha dos vilões (deixa espaço p/ o verso das cartas)
    BOARD_Y = fy0 + 250    # centro das cartas do board
    POT_Y = fy0 + 320      # topo da chapa do pote

    # vilões: faixa rasa da esquerda p/ direita; a aposta desce SEM tocar o
    # board, que fica bem abaixo
    villains = list(spot.get("villains") or [])[:8]
    n = len(villains)
    if n:
        spanx = (fx1 - fx0) * (0.70 if n <= 4 else 0.82)
        for i, v in enumerate(villains):
            frac = 0.5 if n == 1 else i / (n - 1)
            vx = cx + (frac - 0.5) * spanx
            vy = VILL_Y + abs(frac - 0.5) * 34   # pontas levemente mais baixas
            _seat(d, sc(vx), sc(vy), v.get("pos"), v.get("stack_bb"),
                  folded=bool(v.get("folded")), to_act=bool(v.get("to_act")),
                  bet_bb=v.get("bet_bb"), s=S)
            if (v.get("pos") or "").upper() == "BTN":
                _dealer_button(d, sc(vx + 82), sc(vy + 8), S)
    # dealer button do herói (quando VOCÊ é o botão)
    if (spot.get("position") or "").upper() == "BTN":
        _dealer_button(d, sc(cx + 110), sc(fy1 - 14), S)

    # board — com respiro entre flop | turn | river (lê a street no desenho)
    board = spot.get("board") or []
    if board:
        bw, gap, street_gap = 74, 12, 30
        gaps = [(street_gap if i in (3, 4) else gap) for i in range(1, len(board))]
        total = len(board) * bw + sum(gaps)
        bx = cx - total / 2 + bw / 2
        for i, c in enumerate(board):
            _card(d, sc(bx), sc(BOARD_Y), c, w=sc(bw), h=sc(bw * 1.4))
            if i < len(board) - 1:
                bx += bw + gaps[i]
    else:
        _center(d, sc(cx), sc(BOARD_Y - 14), "PRÉ-FLOP", F(26), (200, 220, 210))

    # pote — chapa central grande e legível
    pot_txt = f"POTE  {spot.get('pot_bb', 0):g} bb"
    fp = F(24)
    pw = d.textlength(pot_txt, font=fp)
    d.rounded_rectangle([sc(cx) - pw / 2 - sc(26), sc(POT_Y),
                         sc(cx) + pw / 2 + sc(26), sc(POT_Y) + sc(44)],
                        radius=sc(18), fill=FELT_RIM, outline=GOLD_DK, width=sc(2))
    _center(d, sc(cx), sc(POT_Y + 10), pot_txt, fp, GOLD)

    # herói embaixo (cartas acima do plaque) — com HALO dourado: bate o olho
    # e sabe quem é você (pedido do conselho)
    hero_y = fy1 - 6
    for i, glow in enumerate(((96, 84, 48), (140, 118, 62), (184, 152, 80))):
        r = 3 - i
        d.ellipse([sc(cx - 150 - r * 8), sc(hero_y - 96 - r * 6),
                   sc(cx + 150 + r * 8), sc(hero_y + 40 + r * 4)],
                  outline=glow, width=sc(2))
    _seat(d, sc(cx), sc(hero_y), spot.get("position"), spot.get("stack_bb"),
          hero=True, cards=spot.get("hero_cards"), s=S)

    # rodapé: street/blinds + o preço da decisão (grande)
    fy = H - 172
    street = (spot.get("street") or "").upper()
    blinds = spot.get("blinds") or ""
    _center(d, sc(W / 2), sc(fy), f"{street}   ·   blinds {blinds}",
            F(18, bold=False), MUTED)
    to_call = spot.get("to_call_bb")
    by = fy + 34
    if to_call:
        req = spot.get("required_eq")
        txt = f"PAGAR {to_call:g} bb"
        if req:
            txt += f"   ·   precisa de ~{req * 100:.0f}%"
        ft = F(27)
        tw = d.textlength(txt, font=ft)
        half = max(tw / 2 + sc(30), sc(240))
        d.rounded_rectangle([sc(W / 2) - half, sc(by), sc(W / 2) + half, sc(by + 56)],
                            radius=sc(16), fill=(158, 44, 44), outline=CREAM,
                            width=sc(2))
        _center(d, sc(W / 2), sc(by + 12), txt, ft, CREAM)
    else:
        ft = F(27)
        txt = "SUA VEZ — check ou bet?"
        tw = d.textlength(txt, font=ft)
        half = max(tw / 2 + sc(30), sc(220))
        d.rounded_rectangle([sc(W / 2) - half, sc(by), sc(W / 2) + half, sc(by + 56)],
                            radius=sc(16), fill=FELT_RIM, outline=GOLD, width=sc(2))
        _center(d, sc(W / 2), sc(by + 12), txt, ft, GOLD)

    # downsample (antialias) e marca (emblema + assinatura clara p/ fundo escuro)
    img = img.resize((W, H), Image.LANCZOS)
    d2 = ImageDraw.Draw(img)
    draw_brand(d2, H - 32, right=W - 22, size=16, light=True)
    from app.analysis.branding import paste_logo
    paste_logo(img, 84, 22, 56)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "api", "assets",
                          "logo_avatar.png")
SW = 1000  # largura do storyboard
BAND = (24, 52, 40)       # faixa de street
BAND_ALT = (20, 46, 36)   # zebra
MATH_BG = (14, 34, 27)
FOOT_BG = (16, 30, 24)
OK = (78, 176, 108)
BAD = (206, 74, 74)
MIX = (214, 168, 74)


def _logo(size: int):
    try:
        im = Image.open(_LOGO_PATH).convert("RGBA")
        return im.resize((size, size), Image.LANCZOS)
    except Exception:
        return None


def _wrap(d, text, font, max_w):
    """Quebra `text` em linhas que cabem em max_w px."""
    out, line = [], ""
    for word in (text or "").split():
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out or [""]


def _mini_card(d, x0, y0, code, w, h):
    """Carta pequena com canto superior-esquerdo (rank+naipe)."""
    if not code or len(code) < 2:
        return
    rank = code[0].upper().replace("T", "10")
    sym, col = _SUIT.get(code[1].lower(), ("?", BLACK))
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(w * 0.14),
                        fill=CARD_BG, outline=CARD_EDGE, width=2)
    fr = _font(int(h * 0.42))
    d.text((x0 + int(w * 0.12), y0 + int(h * 0.06)), rank, font=fr, fill=col)
    fs = _font(int(h * 0.40))
    _center(d, x0 + w * 0.5, y0 + h * 0.5, sym, fs, col)


def render_hand_strip(spot: dict) -> bytes:
    """Storyboard da mão inteira numa imagem só — o filme do spot em quadros.

    `spot`:
      title, hero_cards:[c,c], position, stack_bb, blinds
      streets: [{name, board:[..], lines:[str,...], pot_bb, note}]
        (`note` = o que rolou com os vilões, opcional)
      math: {equity:0..1, need:0..1, ev_bb:float, note:str}
      verdict: 'boa'|'ruim'|'mista' ; verdict_text ; correct
    Render determinístico (PIL) — custo zero de LLM.
    """
    S = 2
    pad = 26
    line_h = 32
    streets = list(spot.get("streets") or [])
    math_d = spot.get("math") or {}
    has_math = math_d.get("equity") is not None
    verdict_text = spot.get("verdict_text") or ""
    correct = spot.get("correct") or ""

    # probe 1x para medir quebras de linha (razão idêntica em qualquer escala)
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    f_line = _font(22, bold=False)      # ações — fonte GRANDE
    f_foot = _font(21, bold=False)      # análise do coach
    line_x = pad + 12
    lines_w = SW - line_x - pad - 4

    # --- medir altura de cada street ---
    st_lines = []   # linhas já quebradas por street
    st_tops = []    # onde começam as ações (abaixo do board, se houver)
    st_heights = []
    for st in streets:
        wrapped = []
        for ln in (st.get("lines") or []):
            wrapped += _wrap(probe, ln, f_line, lines_w)
        st_lines.append(wrapped)
        top = 72 if (st.get("board")) else 50
        st_tops.append(top)
        h = top + len(wrapped) * line_h + 14
        if st.get("note"):
            h += line_h
        st_heights.append(max(h, 104))

    math_h = 160 if has_math else 0
    # rodapé do veredito só quando HÁ veredito (quiz/reveal). No filme puro
    # (mão inteira, sem decisão julgada) o selo "DECISÃO MISTA" era ruído.
    has_foot = bool(spot.get("verdict") or verdict_text or correct)
    foot_lines = _wrap(probe, verdict_text, f_foot, SW - 2 * pad - 20)
    corr_lines = _wrap(probe, correct, _font(21), SW - 2 * pad - 176) if correct else []
    if has_foot:
        foot_h = 78 + len(foot_lines) * 30
        if corr_lines:
            foot_h += len(corr_lines) * 32 + 30
        foot_h += 40
    else:
        foot_h = 44  # faixa fina só pra marca

    head_h = 176
    total_h = head_h + sum(st_heights) + math_h + foot_h

    # --- canvas 2x ---
    img = Image.new("RGB", (SW * S, total_h * S), BG)
    d = ImageDraw.Draw(img)

    def sc(v):
        return int(round(v * S))

    def DF(sz, bold=True):
        return _font(int(sz * S), bold)

    def box(x0, y0, x1, y1, *, radius=0, fill=None, outline=None, width=1):
        d.rounded_rectangle([sc(x0), sc(y0), sc(x1), sc(y1)], radius=sc(radius),
                            fill=fill, outline=outline, width=max(1, sc(width)))

    def left(x, ytop, text, sz, fill, bold=True):
        d.text((sc(x), sc(ytop)), text, font=DF(sz, bold), fill=fill)

    def ctr(cx, ytop, text, sz, fill, bold=True):
        f = DF(sz, bold)
        d.text((sc(cx) - d.textlength(text, font=f) / 2, sc(ytop)), text,
               font=f, fill=fill)

    def right(xr, ytop, text, sz, fill, bold=True):
        f = DF(sz, bold)
        d.text((sc(xr) - d.textlength(text, font=f), sc(ytop)), text,
               font=f, fill=fill)

    # ---------- HEADER ----------
    box(0, 0, SW, head_h, fill=(20, 46, 36))
    d.rectangle([0, sc(head_h - 3), sc(SW), sc(head_h)], fill=GOLD_DK)
    logo = _logo(sc(100))
    if logo:
        img.paste(logo, (sc(pad), sc(26)), logo)
    tx = pad + 122
    left(tx, 28, spot.get("title") or "Análise da mão", 30, CREAM)
    sub = f"VOCÊ · {spot.get('position') or '?'}"
    if spot.get("stack_bb") is not None:
        sub += f" · {spot['stack_bb']:g}bb"
    if spot.get("blinds"):
        sub += f" · blinds {spot['blinds']}"
    left(tx, 74, sub, 19, GOLD)
    left(tx, 106, "o filme da mão — quadro a quadro", 16, MUTED, bold=False)
    hc = spot.get("hero_cards") or []
    cw, ch = 76, 106
    hx = SW - pad - len(hc[:2]) * (cw + 10) + 10
    for i, c in enumerate(hc[:2]):
        _card(d, sc(hx + i * (cw + 10) + cw / 2), sc(head_h / 2), c,
              w=sc(cw), h=sc(ch))

    # ---------- STREETS ----------
    y = head_h
    for idx, st in enumerate(streets):
        h = st_heights[idx]
        box(0, y, SW, y + h, fill=BAND if idx % 2 == 0 else BAND_ALT)
        d.rectangle([0, sc(y), sc(6), sc(y + h)], fill=GOLD_DK)
        left(pad, y + 13, (st.get("name") or "").upper(), 22, GOLD)
        # board mini-cartas
        bx = pad + 150
        mw, mh = 40, 54
        for c in (st.get("board") or []):
            _mini_card(d, sc(bx), sc(y + 9), c, sc(mw), sc(mh))
            bx += mw + 7
        if st.get("pot_bb") is not None:
            right(SW - pad, y + 15, f"pote {st['pot_bb']:g}bb", 18, CREAM)
        ly = y + st_tops[idx]
        for wl in st_lines[idx]:
            bold = any(k in wl.lower() for k in ("você", "voce", "herói", "heroi"))
            left(line_x, ly, "▸ " + wl, 22, CREAM if bold else (206, 220, 212),
                 bold=bold)
            ly += line_h
        if st.get("note"):
            left(line_x, ly, "↳ " + st["note"], 17, MUTED, bold=False)
            ly += line_h
        y += h

    # ---------- MATEMÁTICA ----------
    if has_math:
        box(0, y, SW, y + math_h, fill=MATH_BG)
        left(pad, y + 14, "MATEMÁTICA DO SPOT", 20, GOLD)
        tiles = [
            ("SUA EQUITY", f"{math_d['equity'] * 100:.0f}%", OK),
            ("PRECISA DE", f"{(math_d.get('need') or 0) * 100:.0f}%", CREAM),
        ]
        ev = math_d.get("ev_bb")
        if ev is not None:
            tiles.append(("EV DO CALL", f"{ev:+.1f}bb", OK if ev >= 0 else BAD))
        tw = (SW - 2 * pad - (len(tiles) - 1) * 16) / len(tiles)
        ty = y + 54
        for i, (lbl, val, col) in enumerate(tiles):
            tx0 = pad + i * (tw + 16)
            box(tx0, ty, tx0 + tw, ty + 78, radius=14, fill=(22, 48, 38),
                outline=GOLD_DK, width=2)
            ctr(tx0 + tw / 2, ty + 13, lbl, 15, MUTED, bold=False)
            ctr(tx0 + tw / 2, ty + 34, val, 31, col)
        if math_d.get("note"):
            ctr(SW / 2, y + math_h - 24, math_d["note"], 15, MUTED, bold=False)
        y += math_h

    # ---------- RODAPÉ: veredito do coach (só quando há veredito) ----------
    box(0, y, SW, total_h, fill=FOOT_BG)
    d.rectangle([0, sc(y), sc(SW), sc(y + 3)], fill=GOLD_DK)
    if has_foot:
        verd = (spot.get("verdict") or "mista").lower()
        badge_col, badge_txt = {
            "boa": (OK, "✔ DECISÃO BOA"),
            "ruim": (BAD, "✘ DECISÃO RUIM"),
        }.get(verd, (MIX, "≈ DECISÃO MISTA"))
        box(pad, y + 18, pad + 250, y + 56, radius=12, fill=badge_col)
        ctr(pad + 125, y + 25, badge_txt, 20, (16, 24, 18))
        left(pad + 270, y + 27, "análise do coach", 17, MUTED, bold=False)
        fy = y + 70
        for wl in foot_lines:
            left(pad, fy, wl, 21, CREAM, bold=False)
            fy += 30
        if corr_lines:
            fy += 10
            bh = len(corr_lines) * 32 + 18
            box(pad, fy, SW - pad, fy + bh, radius=12, fill=(22, 50, 40),
                outline=OK, width=2)
            left(pad + 16, fy + 12, "DECISÃO CERTA", 17, OK)
            cy2, cx0 = fy + 12, pad + 176
            for wl in corr_lines:
                left(cx0, cy2, wl, 21, CREAM)
                cy2 += 32
                cx0 = pad + 16

    # downsample (antialias) + marca
    img = img.resize((SW, total_h), Image.LANCZOS)
    d2 = ImageDraw.Draw(img)
    draw_brand(d2, total_h - 26, right=SW - 20, size=14, light=True)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def render_share_card(spot: dict) -> bytes:
    """Card QUADRADO (1080×1080) pra compartilhar no grupo: o SPOT sem a
    resposta — "o que você faria?" — com o link do bot. CTA viral do conselho."""
    S = 2
    CW = 1080
    img = Image.new("RGB", (CW * S, CW * S), BG)
    d = ImageDraw.Draw(img)

    def sc(v):
        return int(v * S)

    def F(sz, bold=True):
        return _font(int(sz * S), bold)

    def ctr(cx, y, txt, f, fill):
        d.text((sc(cx) - d.textlength(txt, font=f) / 2, sc(y)), txt,
               font=f, fill=fill)

    # feltro de fundo
    d.rounded_rectangle([sc(50), sc(150), sc(CW - 50), sc(CW - 210)],
                        radius=sc(120), fill=FELT, outline=RAIL_HI, width=sc(8))
    ctr(CW / 2, 46, "VOCÊ AGUENTA ESSE SPOT?", F(52), GOLD)

    # cartas do herói GRANDES
    cards = spot.get("hero_cards") or []
    cw = 190
    x0 = CW / 2 - (len(cards[:2]) * (cw + 24) - 24) / 2 + cw / 2
    for i, c in enumerate(cards[:2]):
        _card(d, sc(x0 + i * (cw + 24)), sc(340), c, w=sc(cw), h=sc(cw * 1.4))

    # board (ou pré-flop)
    board = spot.get("board") or []
    if board:
        bw = 108
        bx = CW / 2 - (len(board) * (bw + 14) - 14) / 2 + bw / 2
        for c in board:
            _card(d, sc(bx), sc(620), c, w=sc(bw), h=sc(bw * 1.4))
            bx += bw + 14
    else:
        ctr(CW / 2, 590, "PRÉ-FLOP", F(44), (200, 220, 210))

    # contexto: posição/stack/pote
    info = (f"{spot.get('position') or '?'} · {spot.get('stack_bb') or '?'}bb · "
            f"pote {spot.get('pot_bb', 0):g}bb")
    ctr(CW / 2, 742, info, F(30, bold=False), CREAM)
    to_call = spot.get("to_call_bb")
    if to_call:
        txt = f"PAGAR {to_call:g}bb — precisa de ~{(spot.get('required_eq') or 0)*100:.0f}%"
        f = F(40)
        w = d.textlength(txt, font=f)
        d.rounded_rectangle([sc(CW / 2) - w / 2 - sc(34), sc(792),
                             sc(CW / 2) + w / 2 + sc(34), sc(792 + 76)],
                            radius=sc(20), fill=(158, 44, 44), outline=CREAM,
                            width=sc(3))
        ctr(CW / 2, 808, txt, f, CREAM)
    else:
        ctr(CW / 2, 806, "SUA VEZ — check ou bet?", F(40), GOLD)

    ctr(CW / 2, 926, "Responde e vê se acertou:", F(30, bold=False), MUTED)
    ctr(CW / 2, 972, "t.me/KKNUts_BOT", F(44), GOLD)

    img = img.resize((CW, CW), Image.LANCZOS)
    d2 = ImageDraw.Draw(img)
    draw_brand(d2, CW - 40, right=CW - 30, size=18, light=True)
    from app.analysis.branding import paste_logo
    paste_logo(img, 116, 24, 72)
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
