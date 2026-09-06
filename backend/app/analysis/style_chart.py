"""Cartão visual de estilo — você vs o arquétipo dos grandes nomes.

Barras comparativas por eixo (VPIP, PFR, 3-bet, AF): as suas ao lado das do
arquétipo mais próximo, com os jogadores de referência no rodapé.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from app.analysis.pro_styles import ARCHETYPES, match_pro_style

W, H = 900, 560
PAD_L, PAD_R = 56, 36

# TEMA ESCURO unificado (mesma identidade da mesa/storyboard)
PAPER = (18, 40, 32)
CARD = (26, 52, 42)
INK = (240, 242, 236)
GREY_TEXT = (150, 168, 158)
GRID = (44, 66, 56)
FELT = (96, 190, 140)
GOLD = (208, 168, 92)


def _font(size: int, bold: bool = True):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def render_style_png(vpip: float, pfr: float, af: float, three_bet: float) -> bytes:
    """Cartão de estilo: barras 'você' vs 'arquétipo mais próximo'."""
    m = match_pro_style(vpip, pfr, af, three_bet)
    arch = next(a for a in ARCHETYPES if a["nome"] == m["estilo"])
    cv, cp, ca, c3 = arch["centro"]

    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    f_title = _font(24)
    f_sub = _font(13, bold=False)
    f_axis = _font(14)
    f_val = _font(13)
    f_leg = _font(13, bold=False)

    d.text((PAD_L, 18), "♠ Seu estilo de jogo", fill=INK, font=f_title)
    d.text((PAD_L, 48), f"mais próximo de: {m['estilo']}", fill=GOLD, font=_font(15))

    # eixos: (nome, valor_user, valor_arquetipo, escala_max)
    axes = [
        ("VPIP %", vpip, cv, 45),
        ("PFR %", pfr, cp, 35),
        ("3-bet %", three_bet, c3, 16),
        ("AF", af, ca, 4.5),
    ]
    top = 96
    row_h = 74
    bar_h = 18
    plot_w = W - PAD_L - PAD_R - 140

    for i, (nome, user_v, arch_v, scale) in enumerate(axes):
        y = top + i * row_h
        d.text((PAD_L, y + 6), nome, fill=INK, font=f_axis)
        x0 = PAD_L + 110
        # trilhas
        d.rectangle([x0, y, x0 + plot_w, y + bar_h], fill=CARD, outline=GRID)
        d.rectangle([x0, y + bar_h + 6, x0 + plot_w, y + 2 * bar_h + 6],
                    fill=CARD, outline=GRID)
        # você (feltro) e arquétipo (dourado)
        w_user = min(plot_w, plot_w * user_v / scale)
        w_arch = min(plot_w, plot_w * arch_v / scale)
        d.rectangle([x0, y, x0 + w_user, y + bar_h], fill=FELT)
        d.rectangle([x0, y + bar_h + 6, x0 + w_arch, y + 2 * bar_h + 6], fill=GOLD)
        d.text((x0 + max(w_user, 4) + 8, y + 1), f"{user_v:g}", fill=FELT, font=f_val)
        d.text((x0 + max(w_arch, 4) + 8, y + bar_h + 7), f"{arch_v:g}",
               fill=GOLD, font=f_val)

    # legenda
    ly = top + len(axes) * row_h + 4
    d.rectangle([PAD_L, ly, PAD_L + 16, ly + 14], fill=FELT)
    d.text((PAD_L + 22, ly - 1), "você", fill=INK, font=f_leg)
    d.rectangle([PAD_L + 92, ly, PAD_L + 108, ly + 14], fill=GOLD)
    d.text((PAD_L + 114, ly - 1), "referência do estilo", fill=INK, font=f_leg)

    # jogadores de referência
    py = ly + 34
    d.text((PAD_L, py), "Na linha de:", fill=GREY_TEXT, font=f_sub)
    for j, p in enumerate(m["jogadores_parecidos"][:3]):
        d.text((PAD_L, py + 22 + j * 22), f"• {p['nome']} — {p['por_que']}"[:110],
               fill=INK, font=f_leg)

    d.text((PAD_L, H - 26),
           "comparação qualitativa com perfis públicos",
           fill=GREY_TEXT, font=f_sub)
    from app.analysis.branding import draw_brand

    draw_brand(d, H - 30, right=W - 24, light=True)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
