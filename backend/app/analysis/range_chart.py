"""Gráfico de range 13×13 — a matriz clássica do estudo de poker, em PNG.

Desenha qualquer range (estático ou com frequências mistas, como o equilíbrio
Nash calculado) no formato universal: pares na diagonal, suited acima,
offsuit abaixo. Cor = frequência da ação (verde-feltro; cinza = fora do range).
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

RANKS = "AKQJT98765432"

CELL = 58
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
            d.text((x + 6, y + 8), hand, fill=text_col, font=f_cell)
            if 0.005 < freq < 0.995:
                d.text((x + 6, y + CELL - 22), f"{freq*100:.0f}%",
                       fill=text_col, font=f_pct)

    pct = 100 * in_range / total_combos
    d.text(
        (MARGIN, top + size - MARGIN + 6),
        f"{pct:.1f}% dos combos no range  ·  KKNuths ♠  t.me/KKNUts_BOT",
        fill=GREY_TEXT, font=f_sub,
    )

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
    except Exception:
        return None
    return None


def chart_for_query(kind: str, arg: str | None = None) -> tuple[bytes, str] | None:
    """Resolve um pedido de chart. kind: posição de open, ou 'sb'/'bb' + stack.

    Retorna (png, legenda) ou None se não reconhecido.
    """
    from app.analysis.nash_pushfold import _table, available
    from app.analysis.ranges import OPEN_RANGES, parse_range

    kind = kind.upper()

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
