"""Quadro-resumo do torneio — o "scorecard" visual de um campeonato enviado.

Cabeçalho com os KPIs (mãos, resultado, all-ins, VPIP no torneio) e a CURVA DO
STACK do herói em BB ao longo das mãos — a história do campeonato num olhar.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from app.models.canonical import ActionType, CanonicalHand, StreetName

W, H = 900, 560
PAD_L, PAD_R = 64, 24
KPI_Y, KPI_H = 96, 84
CHART_Y, CHART_H = 236, 240

PAPER = (250, 250, 247)
CARD = (241, 243, 239)
INK = (27, 33, 29)
GREY_TEXT = (130, 138, 132)
GRID = (225, 228, 223)
FELT = (30, 107, 74)
FELT_DARK = (16, 58, 40)
GOLD = (166, 126, 53)
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


def _hero_stack_bb(hand: CanonicalHand) -> float | None:
    seat = hand.hero_seat()
    bb = hand.stakes.big_blind or 0
    if seat is None or not bb:
        return None
    return seat.stack / bb


def tournament_summary(hands: list[CanonicalHand]) -> dict:
    """Números do campeonato (determinístico, sem LLM)."""
    from app.agent.analyzer import analyze_hand

    hands = sorted(hands, key=lambda h: h.played_at or "")
    per = [analyze_hand(h) for h in hands]
    net = round(sum(a["net_bb"] for a in per), 1)
    allins = sum(
        1 for a in per if any(s.get("all_in") for s in a["spots"])
    )
    vol = 0
    for h in hands:
        pre = h.street(StreetName.PREFLOP)
        if pre and any(
            a.actor == h.hero and a.type in
            (ActionType.CALL, ActionType.BET, ActionType.RAISE)
            for a in pre.actions
        ):
            vol += 1

    stacks: list[tuple[int, float]] = []
    for i, h in enumerate(hands):
        s = _hero_stack_bb(h)
        if s is not None:
            stacks.append((i, s))
    # ponto final: stack da última mão +/- o resultado dela
    if stacks and hands:
        last = hands[-1]
        s = _hero_stack_bb(last)
        if s is not None:
            stacks.append((len(hands), max(0.0, s + per[-1]["net_bb"])))

    biggest = sorted(per, key=lambda a: a["net_bb"])
    return {
        "site": hands[0].site if hands else "?",
        "tournament_id": hands[0].tournament_id if hands else None,
        "buyin": hands[0].stakes.buyin if hands else None,
        "hands": len(hands),
        "net_bb": net,
        "allins": allins,
        "vpip_pct": round(100 * vol / len(hands), 1) if hands else 0.0,
        "stacks_bb": stacks,
        "best": biggest[-1] if biggest else None,
        "worst": biggest[0] if biggest else None,
        "levels": f"{hands[0].stakes.level or '?'} → {hands[-1].stakes.level or '?'}"
        if hands else "?",
    }


def render_tournament_board(hands: list[CanonicalHand]) -> tuple[bytes, str]:
    """Renderiza o quadro. Retorna (png, legenda para o Telegram)."""
    s = tournament_summary(hands)
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    f_title = _font(24)
    f_sub = _font(13, bold=False)
    f_kpi = _font(26)
    f_kpi_l = _font(11, bold=False)
    f_lab = _font(12, bold=False)

    buyin = f" · buy-in ${s['buyin']:g}" if s.get("buyin") else ""
    d.text((PAD_L, 18), f"♠ Torneio #{s['tournament_id'] or '?'} — {s['site']}",
           fill=INK, font=f_title)
    d.text((PAD_L, 48), f"níveis {s['levels']}{buyin}", fill=GREY_TEXT, font=f_sub)

    # ------------------------------- KPIs -------------------------------
    kpis = [
        (f"{s['hands']}", "mãos"),
        (f"{s['net_bb']:+.1f}", "resultado (BB)"),
        (f"{s['vpip_pct']:.0f}%", "VPIP no torneio"),
        (f"{s['allins']}", "all-ins do herói"),
    ]
    box_w = (W - PAD_L - PAD_R - 3 * 12) / 4
    for i, (val, lab) in enumerate(kpis):
        x = PAD_L + i * (box_w + 12)
        d.rectangle([x, KPI_Y, x + box_w, KPI_Y + KPI_H], fill=CARD,
                    outline=GRID)
        color = INK
        if lab.startswith("resultado"):
            color = GREEN if s["net_bb"] >= 0 else RED
        d.text((x + 14, KPI_Y + 14), val, fill=color, font=f_kpi)
        d.text((x + 14, KPI_Y + 52), lab, fill=GREY_TEXT, font=f_kpi_l)

    # --------------------------- curva do stack ---------------------------
    d.text((PAD_L, CHART_Y - 24), "Stack do herói ao longo do torneio (BB)",
           fill=GREY_TEXT, font=f_lab)
    pts_data = s["stacks_bb"]
    if len(pts_data) >= 2:
        xs_i = [p[0] for p in pts_data]
        ys_v = [p[1] for p in pts_data]
        ymax = max(ys_v) * 1.15 or 1
        x0, x1 = min(xs_i), max(xs_i)
        plot_w = W - PAD_L - PAD_R

        for frac in (0, 0.5, 1.0):
            y = CHART_Y + CHART_H - frac * CHART_H
            d.line([PAD_L, y, W - PAD_R, y], fill=GRID)
            d.text((16, y - 7), f"{ymax*frac:.0f}", fill=GREY_TEXT, font=f_lab)

        # zona de perigo (<10bb)
        if ymax > 10:
            y10 = CHART_Y + CHART_H - (10 / ymax) * CHART_H
            d.line([PAD_L, y10, W - PAD_R, y10], fill=(224, 190, 186), width=2)
            d.text((W - PAD_R - 96, y10 - 16), "zona de shove", fill=RED, font=f_lab)

        pts = [
            (PAD_L + plot_w * (xi - x0) / max(x1 - x0, 1),
             CHART_Y + CHART_H - (v / ymax) * CHART_H)
            for xi, v in pts_data
        ]
        # área sob a curva
        poly = pts + [(pts[-1][0], CHART_Y + CHART_H), (pts[0][0], CHART_Y + CHART_H)]
        d.polygon(poly, fill=(208, 228, 218))
        d.line(pts, fill=FELT_DARK, width=3)
        for p in pts:
            d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=FELT)
        d.text((pts[-1][0] - 40, pts[-1][1] - 22),
               f"{ys_v[-1]:.0f}bb", fill=FELT_DARK, font=_font(13))
        d.text((PAD_L, CHART_Y + CHART_H + 8), "mão 1", fill=GREY_TEXT, font=f_lab)
        d.text((W - PAD_R - 60, CHART_Y + CHART_H + 8),
               f"mão {s['hands']}", fill=GREY_TEXT, font=f_lab)
    else:
        d.text((PAD_L, CHART_Y + 40), "stack indisponível nas mãos enviadas",
               fill=GREY_TEXT, font=f_sub)

    # ----------------------- melhores/piores momentos -----------------------
    y = CHART_Y + CHART_H + 40
    if s["best"] and s["worst"]:
        best, worst = s["best"], s["worst"]
        d.text((PAD_L, y),
               f"▲ melhor mão: {' '.join(best.get('hero_cards') or ['?'])} "
               f"({best['net_bb']:+.1f} BB)", fill=GREEN, font=_font(14))
        d.text((PAD_L, y + 24),
               f"▼ pior mão: {' '.join(worst.get('hero_cards') or ['?'])} "
               f"({worst['net_bb']:+.1f} BB)", fill=RED, font=_font(14))

    d.text((PAD_L, H - 26), "KKNuths ♠  t.me/KKNUts_BOT", fill=GREY_TEXT, font=f_lab)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    cap = (
        f"♠ Quadro do torneio #{s['tournament_id'] or '?'}: {s['hands']} mãos, "
        f"{s['net_bb']:+.1f} BB, {s['allins']} all-in(s), VPIP {s['vpip_pct']:.0f}%. "
        "Pergunte ao coach sobre qualquer momento da curva!"
    )
    return buf.getvalue(), cap
