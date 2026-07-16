"""Gráfico de range 13×13 — a matriz clássica do estudo de poker, em PNG.

Desenha qualquer range (estático ou com frequências mistas, como o equilíbrio
Nash calculado) no formato universal: pares na diagonal, suited acima,
offsuit abaixo. Cor = frequência da ação (verde-feltro; cinza = fora do range).
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

RANKS = "AKQJT98765432"

CELL = 66
MARGIN = 16
TITLE_H = 54
LEGEND_H = 40

# paleta do produto
FELT = (30, 107, 74)
FELT_DARK = (16, 58, 40)
GOLD = (166, 126, 53)
PAPER = (250, 250, 247)
INK = (27, 33, 29)
GREY = (225, 228, 223)
GREY_TEXT = (130, 138, 132)


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


def _cell_hand(row: int, col: int) -> str:
    r1, r2 = RANKS[row], RANKS[col]
    if row == col:
        return r1 + r2
    if row < col:          # acima da diagonal = suited
        return r1 + r2 + "s"
    return r2 + r1 + "o"   # abaixo = offsuit


def _blend(freq: float) -> tuple[int, int, int]:
    """0 -> cinza; 0..1 -> verde-feltro cada vez mais intenso."""
    if freq <= 0.005:
        return GREY
    t = min(freq, 1.0)
    light = (168, 214, 192)
    return tuple(int(light[k] + (FELT_DARK[k] - light[k]) * t) for k in range(3))


def render_range_png(
    freqs: dict[str, float],
    title: str,
    subtitle: str = "",
) -> bytes:
    """Renderiza o range como PNG. `freqs`: mão canônica -> frequência (0..1)."""
    size = MARGIN * 2 + CELL * 13
    height = TITLE_H + size + LEGEND_H
    img = Image.new("RGB", (size, height), PAPER)
    d = ImageDraw.Draw(img)

    f_title = _font(24)
    f_sub = _font(14, bold=False)
    f_cell = _font(15)
    f_pct = _font(11, bold=False)

    d.text((MARGIN, 10), title, fill=INK, font=f_title)
    if subtitle:
        d.text((MARGIN, 36), subtitle, fill=GREY_TEXT, font=f_sub)

    top = TITLE_H
    total_combos = in_range = 0.0
    for row in range(13):
        for col in range(13):
            hand = _cell_hand(row, col)
            freq = float(freqs.get(hand, 0.0))
            combos = 6 if row == col else (4 if row < col else 12)
            total_combos += combos
            in_range += combos * freq

            x = MARGIN + col * CELL
            y = top + row * CELL
            d.rectangle([x, y, x + CELL - 2, y + CELL - 2], fill=_blend(freq))
            text_col = PAPER if freq > 0.45 else (INK if freq > 0.005 else GREY_TEXT)
            has_pct = 0.005 < freq < 0.995
            hy = y + (10 if has_pct else (CELL - 16) // 2)
            w = d.textlength(hand, font=f_cell)
            d.text((x + (CELL - 2 - w) / 2, hy), hand, fill=text_col, font=f_cell)
            if has_pct:
                t = f"{freq*100:.0f}%"
                w = d.textlength(t, font=f_pct)
                d.text((x + (CELL - 2 - w) / 2, y + CELL - 22), t,
                       fill=text_col, font=f_pct)

    pct = 100 * in_range / total_combos
    d.text((MARGIN, top + size - MARGIN + 6),
           f"{pct:.1f}% dos combos no range", fill=GREY_TEXT, font=f_sub)
    # "como ler" — a âncora que faltava pra quem nunca viu a matriz
    d.text((MARGIN, top + size - MARGIN + 22),
           "verde = joga (tom escuro = sempre; % = frequência) · cinza = fold · "
           "s = mesmo naipe, o = naipes diferentes",
           fill=GREY_TEXT, font=_font(11, bold=False))
    from app.analysis.branding import draw_brand, paste_logo

    draw_brand(d, top + size - MARGIN + 4, right=size - MARGIN)
    paste_logo(img, size - MARGIN, 6, 48)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


RED = (168, 58, 46)
RED_LIGHT = (232, 180, 172)


def _ev_color(ev: float, fold_ev: float, scale: float) -> tuple[int, int, int]:
    """Diverge em torno do EV do fold: melhor que foldar = verde; pior = vermelho."""
    delta = ev - fold_ev
    t = max(-1.0, min(1.0, delta / max(scale, 1e-9)))
    if t >= 0:
        base, strong = (200, 226, 212), FELT_DARK
    else:
        base, strong, t = RED_LIGHT, RED, -t
    return tuple(int(base[k] + (strong[k] - base[k]) * t) for k in range(3))


def render_ev_range_png(
    evs: dict[str, float], fold_ev: float, title: str, subtitle: str,
    premises: str = "",
) -> bytes:
    """Grade 13×13 colorida pelo EV da ação vs fold, com o valor em BB na célula.

    `premises`: linha de premissas do cálculo no rodapé ("HU SB vs BB · sem
    ante · bf 1.5") — protege contra "esse número tá errado" sem contexto."""
    size = MARGIN * 2 + CELL * 13
    height = TITLE_H + size + LEGEND_H
    img = Image.new("RGB", (size, height), PAPER)
    d = ImageDraw.Draw(img)

    f_title = _font(24)
    f_sub = _font(14, bold=False)
    f_cell = _font(14)
    f_ev = _font(11, bold=False)

    d.text((MARGIN, 10), title, fill=INK, font=f_title)
    d.text((MARGIN, 36), subtitle, fill=GREY_TEXT, font=f_sub)

    deltas = [abs(evs.get(_cell_hand(r, c), fold_ev) - fold_ev)
              for r in range(13) for c in range(13)]
    scale = max(sorted(deltas)[int(len(deltas) * 0.9)], 0.1)  # p90 evita outliers

    top = TITLE_H
    for row in range(13):
        for col in range(13):
            hand = _cell_hand(row, col)
            ev = float(evs.get(hand, fold_ev))
            x = MARGIN + col * CELL
            y = top + row * CELL
            delta = ev - fold_ev
            # célula NEUTRA quando é empate na prática: some o "+0.0 vs -0.0"
            neutral = abs(delta) < 0.05
            color = GREY if neutral else _ev_color(ev, fold_ev, scale)
            d.rectangle([x, y, x + CELL - 2, y + CELL - 2], fill=color)
            luminous = sum(color) / 3
            text_col = PAPER if luminous < 140 else INK
            w = d.textlength(hand, font=f_cell)
            d.text((x + (CELL - 2 - w) / 2, y + 9), hand, fill=text_col, font=f_cell)
            t = "0.0" if neutral else f"{delta:+.1f}"
            w = d.textlength(t, font=f_ev)
            d.text((x + (CELL - 2 - w) / 2, y + CELL - 22), t,
                   fill=text_col, font=f_ev)

    d.text((MARGIN, top + size - MARGIN + 6),
           "célula = EV da ação MENOS o EV do fold, em BB (verde: agir; "
           "vermelho: foldar; cinza: tanto faz)", fill=GREY_TEXT, font=f_sub)
    if premises:
        d.text((MARGIN, top + size - MARGIN + 24), premises,
               fill=GREY_TEXT, font=_font(11, bold=False))
    from app.analysis.branding import draw_brand, paste_logo

    draw_brand(d, top + size - MARGIN + 4, right=size - MARGIN, link=False)
    paste_logo(img, size - MARGIN, 6, 48)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_spec(spec: tuple) -> tuple[bytes, str] | None:
    """Renderiza uma spec coletada do coach: ("range", notacao, titulo) ou
    ("nash", role, stack_bb). Retorna (png, legenda) ou None."""
    from app.analysis.ranges import parse_range

    try:
        if spec[0] == "range":
            _, notation, title = spec
            hands = parse_range(notation)
            png = render_range_png({h: 1.0 for h in hands}, title, notation[:70])
            return png, f"📊 {title}: {notation}"
        if spec[0] == "nash":
            _, role, stack = spec
            return chart_for_query(role, str(stack))
        if spec[0] == "nashmode":
            _, role, stack, mode, bf = spec
            return chart_for_query(
                role, str(stack), mode if mode in ("ev", "icm") else None, bf
            )
    except Exception:
        return None
    return None


def chart_for_query(
    kind: str, arg: str | None = None,
    mode: str | None = None, bf: float = 1.5,
) -> tuple[bytes, str] | None:
    """Resolve um pedido de chart. kind: posição de open, ou 'sb'/'bb' + stack.

    mode: None (frequências) | 'ev' (EV chip) | 'icm' (EV sob bubble factor bf).
    Retorna (png, legenda) ou None se não reconhecido.
    """
    from app.analysis.nash_pushfold import _table, available
    from app.analysis.ranges import OPEN_RANGES, parse_range

    kind = kind.upper()

    # grade de EV por mão (equilíbrio re-resolvido; chip-EV ou ICM)
    if kind in ("SB", "BB") and arg and mode in ("ev", "icm"):
        from app.analysis.jam_fold_solver import available as solver_ok
        from app.analysis.jam_fold_solver import solve_jam_fold

        if not solver_ok():
            return None
        try:
            stack = float(arg.replace("bb", ""))
        except ValueError:
            return None
        use_bf = bf if mode == "icm" else 1.0
        sol = solve_jam_fold(round(stack, 1), round(use_bf, 2))
        if sol is None:
            return None
        evs = sol["sb_ev"] if kind == "SB" else sol["bb_ev"]
        fold_ev = sol["sb_fold_ev"] if kind == "SB" else sol["bb_fold_ev"]
        action = "all-in" if kind == "SB" else "call de all-in"
        # sem emoji no título: DejaVu não tem o glifo e renderiza tofu (⧠)
        badge = "chip-EV" if mode == "ev" else f"ICM (bubble factor {use_bf:g})"
        png = render_ev_range_png(
            evs, fold_ev,
            f"EV do {action} — {kind} · {stack:g}bb · {badge}",
            "EV em BB vs fold · equilíbrio re-resolvido nesta utilidade",
            premises=(f"premissas: heads-up SB vs BB · stack efetivo "
                      f"{stack:g}bb · sem ante · bubble factor {use_bf:g}"),
        )
        cap = (
            f"♠ EV de cada mão no {action} do {kind} com {stack:g}bb — {badge}. "
            "Verde = a ação rende mais que foldar; vermelho = fold é melhor. "
        )
        if mode == "icm":
            cap += (f"Sob ICM (perder fichas custa {use_bf:g}x mais), o range aperta — "
                    "compare com a versão chip-EV.")
        return png, cap

    # Nash jam/fold calculado (SB empurra / BB paga) por stack
    if kind in ("SB", "BB") and arg:
        if not available():
            return None
        try:
            stack = float(arg.replace("bb", ""))
        except ValueError:
            return None
        table = _table()["stacks"]
        key = min(table.keys(), key=lambda s: abs(float(s) - stack))
        entry = table[key]["sb_jam" if kind == "SB" else "bb_call"]
        action = "all-in (shove)" if kind == "SB" else "call de all-in"
        png = render_range_png(
            entry,
            f"Nash {kind} — {action} · {key}bb",
            "Equilíbrio calculado · heads-up SB vs BB · % = frequência mista",
        )
        return png, (
            f"♠ Range Nash de {action} do {kind} com {key}bb — equilíbrio "
            f"calculado, não aproximação. Células com % jogam de forma mista."
        )

    # charts de open-raise por posição
    if kind in OPEN_RANGES:
        hands = parse_range(OPEN_RANGES[kind])
        png = render_range_png(
            {h: 1.0 for h in hands},
            f"Open-raise — {kind}",
            "Range de referência ~100bb · ajuste pela dinâmica da mesa",
        )
        return png, f"♠ Range de referência de open-raise em {kind} (~100bb)."

    return None
