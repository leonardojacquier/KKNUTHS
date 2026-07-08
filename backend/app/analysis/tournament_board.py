"""Quadro-resumo do torneio — o "scorecard" visual de um campeonato enviado.

Cabeçalho com os KPIs (mãos, resultado, all-ins, VPIP no torneio) e a CURVA DO
STACK do herói em BB ao longo das mãos — a história do campeonato num olhar.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

from app.models.canonical import ActionType, CanonicalHand, StreetName

W, H = 900, 704
PAD_L, PAD_R = 64, 24
KPI_Y, KPI_H = 96, 84
KPI2_Y = 192
CHART_Y, CHART_H = 336, 240

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

    # stats estilo PokerCraft/HUD para o quadro
    from app.analysis.stats import compute_player_stats

    st = compute_player_stats(hands, player=None)
    tbet, af = st.three_bet, st.af
    from app.config import get_settings
    if get_settings().bayes_stats:
        # taxa por oportunidade com meia duzia de casos mente ("3-bet 100%");
        # o quadro usa a estimativa corrigida, como o resto do produto
        from app.analysis.bayes import bayes_stats
        b = bayes_stats(st)
        tbet, af = b["three_bet"]["mean"], b["af"]["mean"]
    pre_raises = 0
    wtsd = wsd = 0
    for h, a in zip(hands, per):
        pre = h.street(StreetName.PREFLOP)
        if pre and any(x.actor == h.hero and x.type == ActionType.RAISE
                       for x in pre.actions):
            pre_raises += 1
        hero_folded = any(
            x.actor == h.hero and x.type == ActionType.FOLD
            for stt in h.streets for x in stt.actions
        )
        if len(h.final_board) == 5 and not hero_folded and a["pot_total"]:
            wtsd += 1
            if a["net_bb"] > 0:
                wsd += 1

    return {
        "pfr": st.pfr, "three_bet": tbet, "af": af,
        "pre_raises": pre_raises, "wtsd": wtsd, "wsd": wsd,
        "maior_pote_bb": round(biggest[-1]["net_bb"], 1) if biggest else 0,
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
    row1 = [
        (f"{s['hands']}", "mãos"),
        (f"{s['net_bb']:+.1f}", "resultado (BB)"),
        (f"{s['vpip_pct']:.0f}%", "VPIP"),
        (f"{s['pfr']:.0f}%", "PFR"),
        (f"{s['three_bet']:.0f}%", "3-bet"),
    ]
    row2 = [
        (f"{s['af']:g}", "agressão (AF)"),
        (f"{s['pre_raises']}", "raises pré"),
        (f"{s['allins']}", "all-ins"),
        (f"{s['wsd']}/{s['wtsd']}", "showdowns (ganhou/foi)"),
        (f"{s['maior_pote_bb']:+.1f}", "maior pote (BB)"),
    ]
    for row_i, kpis in enumerate((row1, row2)):
        y0 = KPI_Y if row_i == 0 else KPI2_Y
        box_w = (W - PAD_L - PAD_R - 4 * 12) / 5
        for i, (val, lab) in enumerate(kpis):
            x = PAD_L + i * (box_w + 12)
            d.rectangle([x, y0, x + box_w, y0 + KPI_H], fill=CARD, outline=GRID)
            color = INK
            if lab.startswith("resultado") or lab.startswith("maior"):
                ref = s["net_bb"] if lab.startswith("resultado") else s["maior_pote_bb"]
                color = GREEN if ref >= 0 else RED
            d.text((x + 14, y0 + 14), val, fill=color, font=f_kpi)
            d.text((x + 14, y0 + 52), lab, fill=GREY_TEXT, font=f_kpi_l)

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

        # zona de perigo (<10bb) — rótulo à esquerda para não brigar com o fim
        # da curva
        if ymax > 10:
            y10 = CHART_Y + CHART_H - (10 / ymax) * CHART_H
            d.line([PAD_L, y10, W - PAD_R, y10], fill=(224, 190, 186), width=2)
            d.text((PAD_L + 6, y10 - 16), "zona de shove", fill=RED, font=f_lab)

        pts = [
            (PAD_L + plot_w * (xi - x0) / max(x1 - x0, 1),
             CHART_Y + CHART_H - (v / ymax) * CHART_H)
            for xi, v in pts_data
        ]
        # área sob a curva; com muitas mãos os marcadores viram poluição —
        # mostra 1 a cada N e o ponto final
        poly = pts + [(pts[-1][0], CHART_Y + CHART_H), (pts[0][0], CHART_Y + CHART_H)]
        d.polygon(poly, fill=(208, 228, 218))
        d.line(pts, fill=FELT_DARK, width=3)
        step = max(1, len(pts) // 36)
        for i, p in enumerate(pts):
            if i % step == 0 or i == len(pts) - 1:
                d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=FELT)
        lbl_y = pts[-1][1] - 22 if pts[-1][1] > CHART_Y + 26 else pts[-1][1] + 10
        d.text((min(pts[-1][0] - 40, W - PAD_R - 52), lbl_y),
               f"{ys_v[-1]:.0f}bb", fill=FELT_DARK, font=_font(13))
        d.text((PAD_L, CHART_Y + CHART_H + 8), "mão 1", fill=GREY_TEXT, font=f_lab)
        d.text((W - PAD_R - 60, CHART_Y + CHART_H + 8),
               f"mão {s['hands']}", fill=GREY_TEXT, font=f_lab)
    else:
        d.text((PAD_L, CHART_Y + 40), "stack indisponível nas mãos enviadas",
               fill=GREY_TEXT, font=f_sub)

    # --------------------- melhores/piores momentos (lado a lado) ----------
    y = CHART_Y + CHART_H + 42
    if s["best"] and s["worst"]:
        best, worst = s["best"], s["worst"]
        d.text((PAD_L, y),
               f"▲ melhor mão: {' '.join(best.get('hero_cards') or ['?'])} "
               f"({best['net_bb']:+.1f} BB)", fill=GREEN, font=_font(14))
        d.text((W // 2 + 10, y),
               f"▼ pior mão: {' '.join(worst.get('hero_cards') or ['?'])} "
               f"({worst['net_bb']:+.1f} BB)", fill=RED, font=_font(14))

    from app.analysis.branding import draw_brand

    draw_brand(d, H - 30, left=PAD_L)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    cap = (
        f"♠ Torneio #{s['tournament_id'] or '?'}: {s['hands']} mãos, "
        f"{s['net_bb']:+.1f} BB · VPIP {s['vpip_pct']:.0f}% · PFR {s['pfr']:.0f}% · "
        f"3-bet {s['three_bet']:.0f}% · AF {s['af']:g} · {s['pre_raises']} raises pré · "
        f"showdowns {s['wsd']}/{s['wtsd']} · maior pote {s['maior_pote_bb']:+.1f}bb"
    )
    return buf.getvalue(), cap
