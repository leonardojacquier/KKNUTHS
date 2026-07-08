"""Gráfico de evolução do jogador — a linha do tempo do /evolucao.

Duas faixas: em cima, VPIP/PFR/3-bet% ao longo dos snapshots (um ponto por
lote analisado); embaixo, o resultado acumulado em BB. Paleta do produto.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

W, H = 900, 500
PAD_L, PAD_R, PAD_T = 56, 20, 54
TOP_H = 250      # painel das linhas
GAP = 56
BOT_H = 110      # painel do net acumulado

PAPER = (250, 250, 247)
INK = (27, 33, 29)
GREY_TEXT = (130, 138, 132)
GRID = (225, 228, 223)
FELT = (30, 107, 74)
GOLD = (166, 126, 53)
BLUE = (70, 105, 150)
RED = (168, 58, 46)
GREEN = (46, 125, 91)


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


def render_evolution_png(history: list[dict], title: str = "Sua evolução") -> bytes:
    """`history`: snapshots em ordem cronológica (vpip/pfr/three_bet/net_bb/
    hands/created_at). Precisa de >=2 pontos."""
    n = len(history)
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    f_title = _font(22)
    f_lab = _font(12, bold=False)
    f_leg = _font(13)

    d.text((PAD_L, 12), title, fill=INK, font=f_title)
    d.text((PAD_L, 36), f"{n} snapshots · {history[-1].get('hands') or 0} mãos na amostra atual",
           fill=GREY_TEXT, font=f_lab)

    plot_w = W - PAD_L - PAD_R
    xs = [PAD_L + (plot_w * i / max(n - 1, 1)) for i in range(n)]

    # ------------- painel 1: linhas de estilo (0..teto dinâmico) -------------
    series = [
        ("VPIP%", FELT, [float(h.get("vpip") or 0) for h in history]),
        ("PFR%", GOLD, [float(h.get("pfr") or 0) for h in history]),
        ("3-bet%", BLUE, [float(h.get("three_bet") or 0) for h in history]),
    ]
    top_y0, top_y1 = PAD_T, PAD_T + TOP_H
    ymax = max(10.0, max(v for _, _, vals in series for v in vals) * 1.15)

    for frac in (0, 0.25, 0.5, 0.75, 1.0):
        y = top_y1 - frac * TOP_H
        d.line([PAD_L, y, W - PAD_R, y], fill=GRID)
        d.text((10, y - 7), f"{ymax*frac:.0f}", fill=GREY_TEXT, font=f_lab)

    for name, color, vals in series:
        pts = [(xs[i], top_y1 - (vals[i] / ymax) * TOP_H) for i in range(n)]
        if len(pts) > 1:
            d.line(pts, fill=color, width=3)
        for p in pts:
            d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=color)

    lx = PAD_L
    for name, color, vals in series:
        d.rectangle([lx, top_y1 + 12, lx + 14, top_y1 + 24], fill=color)
        label = f"{name} {vals[-1]:.0f}"
        d.text((lx + 20, top_y1 + 10), label, fill=INK, font=f_leg)
        lx += 24 + int(d.textlength(label, font=f_leg)) + 22

    # ------------- painel 2: resultado acumulado em BB -------------
    bot_y0 = top_y1 + GAP
    bot_y1 = bot_y0 + BOT_H
    d.text((PAD_L, bot_y0 - 20), "Resultado acumulado (BB)", fill=GREY_TEXT, font=f_lab)

    cum, acc = [], 0.0
    for h in history:
        acc += float(h.get("net_bb") or 0)
        cum.append(acc)
    lo, hi = min(cum + [0.0]), max(cum + [0.0])
    span = max(hi - lo, 1.0)

    zero_y = bot_y1 - ((0 - lo) / span) * BOT_H
    d.line([PAD_L, zero_y, W - PAD_R, zero_y], fill=GRID, width=2)
    d.text((10, zero_y - 7), "0", fill=GREY_TEXT, font=f_lab)

    pts = [(xs[i], bot_y1 - ((cum[i] - lo) / span) * BOT_H) for i in range(n)]
    if len(pts) > 1:
        d.line(pts, fill=GREEN if cum[-1] >= 0 else RED, width=3)
    for i, p in enumerate(pts):
        color = GREEN if cum[i] >= 0 else RED
        d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=color)
    d.text((W - PAD_R - 90, bot_y0 - 20), f"{cum[-1]:+.1f} BB",
           fill=GREEN if cum[-1] >= 0 else RED, font=f_leg)

    # eixo X: datas (primeira, meio, última)
    for i in (0, n // 2, n - 1):
        date = str(history[i].get("created_at") or "")[5:10]
        d.text((xs[i] - 14, bot_y1 + 8), date, fill=GREY_TEXT, font=f_lab)

    from app.analysis.branding import draw_brand

    draw_brand(d, H - 26, left=PAD_L)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


INDICATORS = {
    "vpip": ("VPIP%", FELT, False),
    "pfr": ("PFR%", GOLD, False),
    "3bet": ("3-bet%", BLUE, False),
    "af": ("Agressão (AF)", FELT, False),
    "bb": ("Resultado acumulado (BB)", GREEN, True),
}
_KEYMAP = {"vpip": "vpip", "pfr": "pfr", "3bet": "three_bet", "af": "af", "bb": "net_bb"}


def render_indicator_png(history: list[dict], indicator: str) -> bytes | None:
    """Um indicador só, em destaque. `indicator`: vpip|pfr|3bet|af|bb."""
    ind = indicator.lower().strip()
    if ind not in INDICATORS or len(history) < 2:
        return None
    label, color, cumulative = INDICATORS[ind]
    key = _KEYMAP[ind]

    vals = [float(h.get(key) or 0) for h in history]
    if cumulative:
        acc, out = 0.0, []
        for v in vals:
            acc += v
            out.append(acc)
        vals = out
        color = GREEN if vals[-1] >= 0 else RED

    n = len(history)
    Wi, Hi = 900, 420
    img = Image.new("RGB", (Wi, Hi), PAPER)
    d = ImageDraw.Draw(img)
    d.text((PAD_L, 14), label, fill=INK, font=_font(22))
    d.text((PAD_L, 40),
           f"{n} snapshots · atual: {vals[-1]:+.1f}" if cumulative
           else f"{n} snapshots · atual: {vals[-1]:.1f}",
           fill=GREY_TEXT, font=_font(12, bold=False))

    top, height = 84, 250
    lo = min(vals + ([0.0] if cumulative else []))
    hi = max(vals + ([0.0] if cumulative else []))
    span = max(hi - lo, 1.0)
    lo -= span * 0.08
    span *= 1.16

    plot_w = Wi - PAD_L - PAD_R
    xs = [PAD_L + plot_w * i / max(n - 1, 1) for i in range(n)]
    for frac in (0, 0.5, 1.0):
        y = top + height - frac * height
        d.line([PAD_L, y, Wi - PAD_R, y], fill=GRID)
        d.text((12, y - 7), f"{lo + span*frac:.0f}", fill=GREY_TEXT,
               font=_font(12, bold=False))
    if cumulative and lo < 0 < lo + span:
        zy = top + height - ((0 - lo) / span) * height
        d.line([PAD_L, zy, Wi - PAD_R, zy], fill=(200, 205, 200), width=2)

    pts = [(xs[i], top + height - ((vals[i] - lo) / span) * height)
           for i in range(n)]
    d.line(pts, fill=color, width=4)
    for p in pts:
        d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], fill=color)
    for i in (0, n - 1):
        date = str(history[i].get("created_at") or "")[5:10]
        d.text((xs[i] - 14, top + height + 10), date, fill=GREY_TEXT,
               font=_font(12, bold=False))

    from app.analysis.branding import draw_brand

    draw_brand(d, Hi - 28, left=PAD_L)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def evolution_text(history: list[dict]) -> str:
    """Leitura determinística da evolução (sem custo de LLM)."""
    first, last = history[0], history[-1]

    def dv(key):
        a, b = float(first.get(key) or 0), float(last.get(key) or 0)
        return b - a

    parts = [f"📈 *Sua evolução* — {len(history)} pontos, "
             f"{last.get('hands') or 0} mãos acumuladas.\n"]
    arrows = []
    for key, nome, bom_quando_cai in (("vpip", "VPIP", True), ("pfr", "PFR", False),
                                      ("three_bet", "3-bet", False)):
        delta = dv(key)
        if abs(delta) < 1:
            continue
        seta = "↓" if delta < 0 else "↑"
        arrows.append(f"{nome} {seta} {abs(delta):.0f}pp")
    if arrows:
        parts.append("Mudanças: " + " · ".join(arrows) + ".")
    else:
        parts.append("Estilo estável desde o início da amostra.")
    cum = sum(float(h.get("net_bb") or 0) for h in history)
    parts.append(f"Resultado acumulado: *{cum:+.1f} BB*.")
    parts.append(f"Estilo atual: *{last.get('label') or '—'}*.")
    return "\n".join(parts)
