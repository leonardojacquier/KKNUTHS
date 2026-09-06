"""Gráfico de range 13×13 — a matriz clássica do estudo de poker, em PNG.

Desenha qualquer range (estático ou com frequências mistas, como o equilíbrio
Nash calculado) no formato universal: pares na diagonal, suited acima,
offsuit abaixo. Cor = frequência da ação (verde-feltro; cinza = fora do range).
"""
from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

RANKS = "AKQJT98765432"

CELL = 66
MARGIN = 16
TITLE_H = 54
LEGEND_H = 40

# ante por jogador em bb no equilíbrio jam/fold (100/200(25) -> 0.125).
# Torneio real TEM ante; sem ele o range sai sistematicamente tight.
ANTE_PADRAO = 0.125

# paleta do produto — TEMA ESCURO unificado (mesma identidade da mesa e do
# storyboard; no dark mode do Telegram as peças claras davam "flashbang").
# As CÉLULAS continuam claras — cartas sobre o feltro — o que preserva o
# contraste do texto dentro delas.
FELT = (30, 107, 74)
FELT_DARK = (16, 58, 40)
GOLD = (208, 168, 92)
DARK_BG = (18, 40, 32)          # canvas (mesmo BG da mesa)
CREAM = (240, 242, 236)         # títulos
MUTED = (150, 168, 158)         # subtítulos/legendas
PAPER = (250, 250, 247)         # texto sobre célula escura
INK = (27, 33, 29)              # texto sobre célula clara
GREY = (225, 228, 223)          # célula de fold (clara, como carta virada)
GREY_TEXT = (130, 138, 132)     # texto na célula de fold


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
    img = Image.new("RGB", (size, height), DARK_BG)
    d = ImageDraw.Draw(img)

    f_title = _font(24)
    f_sub = _font(14, bold=False)
    f_cell = _font(15)
    f_pct = _font(11, bold=False)

    d.text((MARGIN, 10), title, fill=CREAM, font=f_title)
    if subtitle:
        d.text((MARGIN, 36), subtitle, fill=MUTED, font=f_sub)

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
            # % SÓ nas frequências mistas: "100%" em toda célula era ruído
            # ("o que é o 100%?") — sempre-joga fica só com a cor cheia
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
           f"{pct:.1f}% dos combos no range", fill=MUTED, font=f_sub)
    # "como ler" — a âncora que faltava pra quem nunca viu a matriz
    d.text((MARGIN, top + size - MARGIN + 22),
           "verde cheio = joga sempre · % = mistura (joga essa fração das "
           "vezes) · cinza = fold · s = mesmo naipe, o = naipes diferentes",
           fill=MUTED, font=_font(11, bold=False))
    from app.analysis.branding import draw_brand, paste_logo

    draw_brand(d, top + size - MARGIN + 4, right=size - MARGIN, light=True)
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
    premises: str = "", legend: str = "",
) -> bytes:
    """Grade 13×13 colorida pelo EV da ação vs fold, com o valor em BB na célula.

    `premises`: linha de premissas do cálculo no rodapé ("HU SB vs BB · sem
    ante · bf 1.5") — protege contra "esse número tá errado" sem contexto."""
    size = MARGIN * 2 + CELL * 13
    height = TITLE_H + size + LEGEND_H
    img = Image.new("RGB", (size, height), DARK_BG)
    d = ImageDraw.Draw(img)

    f_title = _font(24)
    f_sub = _font(14, bold=False)
    f_cell = _font(14)
    f_ev = _font(11, bold=False)

    d.text((MARGIN, 10), title, fill=CREAM, font=f_title)
    d.text((MARGIN, 36), subtitle, fill=MUTED, font=f_sub)

    deltas = [abs(evs.get(_cell_hand(r, c), fold_ev) - fold_ev)
              for r in range(13) for c in range(13)]
    scale = max(sorted(deltas)[int(len(deltas) * 0.9)], 0.1)  # p90 evita outliers

    top = TITLE_H
    for row in range(13):
        for col in range(13):
            hand = _cell_hand(row, col)
            crua = evs.get(hand)
            fora = crua is None          # mão que nem está no range
            ev = float(fold_ev if fora else crua)
            x = MARGIN + col * CELL
            y = top + row * CELL
            delta = ev - fold_ev
            # célula NEUTRA quando é empate na prática: some o "+0.0 vs -0.0"
            neutral = fora or abs(delta) < 0.05
            color = GREY if neutral else _ev_color(ev, fold_ev, scale)
            d.rectangle([x, y, x + CELL - 2, y + CELL - 2], fill=color)
            luminous = sum(color) / 3
            text_col = PAPER if luminous < 140 else INK
            w = d.textlength(hand, font=f_cell)
            d.text((x + (CELL - 2 - w) / 2, y + 9), hand, fill=text_col, font=f_cell)
            t = "" if fora else ("0.0" if neutral else f"{delta:+.1f}")
            if t:
                w = d.textlength(t, font=f_ev)
                d.text((x + (CELL - 2 - w) / 2, y + CELL - 22), t,
                       fill=text_col, font=f_ev)

    texto_legenda = legend or ("célula = EV da ação MENOS o EV do fold, em BB "
                               "(verde: agir; vermelho: foldar; cinza: tanto "
                               "faz)")
    # a legenda longa do pós-flop batia na marca do canto: corta no espaço
    # que sobra ANTES da assinatura, em vez de escrever por cima dela
    limite = size - MARGIN * 2 - 150
    while (d.textlength(texto_legenda, font=f_sub) > limite
           and " " in texto_legenda):
        texto_legenda = texto_legenda.rsplit(" ", 1)[0]
    d.text((MARGIN, top + size - MARGIN + 6), texto_legenda,
           fill=MUTED, font=f_sub)
    if premises:
        d.text((MARGIN, top + size - MARGIN + 24), premises,
               fill=MUTED, font=_font(11, bold=False))
    from app.analysis.branding import draw_brand, paste_logo

    draw_brand(d, top + size - MARGIN + 4, right=size - MARGIN, link=False, light=True)
    paste_logo(img, size - MARGIN, 6, 48)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_spec(spec: tuple) -> tuple[bytes, str] | None:
    """Renderiza uma spec do coach: ("range", notacao, titulo),
    ("nash", role, stack), ("nashmode", role, stack, mode, bf) ou
    ("nashpos", position, stack, mode). Retorna (png, legenda) ou None."""
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
        if spec[0] == "posflop":      # solver pós-flop: valor/frequência
            _, board, oop, ip, pot, stack, player, mode = spec
            return chart_postflop(list(board), oop, ip, float(pot),
                                  float(stack), player, mode)
        if spec[0] == "spot":         # motor unificado de all-in pré-flop
            _, kind, hero, stack, mode, vil, ob, pg = spec
            return chart_allin_spot(kind, hero, float(stack), mode, vil,
                                    float(ob), int(pg))
        if spec[0] == "nashpos":      # open-shove por posição (mesa de 9)
            _, pos, stack, mode = spec
            return chart_for_query(pos, str(stack),
                                   mode if mode == "ev" else None)
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
        sol = solve_jam_fold(round(stack, 1), round(use_bf, 2), ANTE_PADRAO)
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
                      f"{stack:g}bb · ante {ANTE_PADRAO*100:g}% do bb (padrão "
                      f"de torneio) · bubble factor {use_bf:g}"),
        )
        cap = (
            f"♠ EV de cada mão no {action} do {kind} com {stack:g}bb — {badge}. "
            "Verde = a ação rende mais que foldar; vermelho = fold é melhor. "
        )
        if mode == "icm":
            cap += (f"Sob ICM (perder fichas custa {use_bf:g}x mais), pagar fica "
                    "mais caro pro vilão — ele desiste mais, e empurrar mãos "
                    "marginais passa a valer; por isso algumas células ficam "
                    "MAIS verdes que no chip-EV.")
        return png, cap

    # Nash jam/fold calculado (SB empurra / BB paga) por stack — resolvido em
    # runtime COM ante (a tabela estática era sem ante: range saía tight)
    if kind in ("SB", "BB") and arg:
        try:
            stack = float(arg.replace("bb", ""))
        except ValueError:
            return None
        from app.analysis.jam_fold_solver import available as solver_ok
        from app.analysis.jam_fold_solver import solve_jam_fold

        entry = None
        if solver_ok():
            sol = solve_jam_fold(round(stack, 1), 1.0, ANTE_PADRAO)
            if sol:
                entry = sol["sb_jam" if kind == "SB" else "bb_call"]
                key = f"{stack:g}"
                sub = (f"Equilíbrio calculado · heads-up SB vs BB · ante "
                       f"{ANTE_PADRAO*100:g}% do bb · % = frequência mista")
        if entry is None:
            if not available():
                return None
            table = _table()["stacks"]
            key = min(table.keys(), key=lambda s: abs(float(s) - stack))
            entry = table[key]["sb_jam" if kind == "SB" else "bb_call"]
            sub = "Equilíbrio calculado · heads-up SB vs BB · % = frequência mista"
        action = "all-in (shove)" if kind == "SB" else "call de all-in"
        png = render_range_png(
            entry,
            f"Nash {kind} — {action} · {key}bb",
            sub,
        )
        return png, (
            f"♠ Range Nash de {action} do {kind} com {key}bb — equilíbrio "
            f"calculado, não aproximação. Células com % jogam de forma mista."
        )

    # OPEN-SHOVE por posição em mesa cheia (UTG..BTN) com stack curto:
    # equilíbrio resolvido pelo solver multiway — frequências ou EV por mão.
    # Era o buraco: EV por mão só existia em SB vs BB heads-up.
    if arg and kind not in ("SB", "BB"):
        from app.analysis.open_shove_solver import solve_open_shove
        try:
            stack = float(str(arg).replace("bb", ""))
        except ValueError:
            stack = None
        if stack and stack <= 20:
            sol = solve_open_shove(kind, round(stack, 1), 1.0, ANTE_PADRAO)
            if sol:
                if mode == "ev":
                    png = render_ev_range_png(
                        sol["ev"], sol["fold_ev"],
                        f"EV do all-in — {kind} · {stack:g}bb · chip-EV",
                        f"EV em BB vs foldar · {sol['atras']} jogadores atrás",
                        premises=sol["premissas"])
                    return png, (
                        f"♠ EV de cada mão no all-in de {kind} com {stack:g}bb "
                        f"(mesa de 9, {sol['atras']} atrás). Verde = empurrar "
                        "rende mais que foldar; vermelho = fold é melhor.")
                png = render_range_png(
                    sol["shove"],
                    f"Nash {kind} — all-in (shove) · {stack:g}bb",
                    f"Equilíbrio resolvido · {sol['atras']} atrás · ante "
                    f"{ANTE_PADRAO*100:g}% do bb · % = frequência mista")
                return png, (
                    f"♠ Range de all-in do {kind} com {stack:g}bb — "
                    f"equilíbrio resolvido com {sol['atras']} jogadores atrás "
                    f"({sol['shove_pct']:g}% das mãos).")

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


_SPOT_NOME = {
    "open_shove": "all-in de abertura", "reshove": "re-shove sobre o open",
    "squeeze": "squeeze all-in", "call_shove": "call de all-in",
    "overcall": "overcall de all-in",
}


def chart_allin_spot(kind: str, hero: str, stack: float,
                     mode: str | None = None, vilao: str | None = None,
                     open_bb: float = 2.2, pagaram: int = 0,
                     bf: float = 1.0) -> tuple[bytes, str] | None:
    """Gráfico (frequência ou EV) de QUALQUER all-in pré-flop, pelo motor."""
    from app.analysis.allin_engine import solve_spot

    sol = solve_spot(kind, hero, round(float(stack), 1), ANTE_PADRAO, bf,
                     vilao, float(open_bb), int(pagaram))
    if not sol:
        return None
    nome = _SPOT_NOME.get(kind, kind)
    vs = f" vs {sol['vilao_pos']}" if sol.get("vilao_pos") else ""
    if mode == "ev":
        png = render_ev_range_png(
            sol["ev"], sol["fold_ev"],
            f"EV — {nome} · {hero}{vs} · {stack:g}bb",
            f"EV em BB vs foldar · pote morto {sol['dead']:g}bb",
            premises=sol["premissas"])
        return png, (
            f"\u2660 EV de cada mão no {nome} do {hero}{vs} com {stack:g}bb. "
            "Verde = a ação rende mais que foldar; vermelho = fold é melhor.")
    png = render_range_png(
        sol["acao"], f"{nome} — {hero}{vs} · {stack:g}bb",
        f"Equilíbrio resolvido · pote morto {sol['dead']:g}bb · "
        f"% = frequência mista")
    return png, (
        f"\u2660 Range de {nome} do {hero}{vs} com {stack:g}bb — equilíbrio "
        f"resolvido ({sol['acao_pct']:g}% das mãos).")


# maxsize=2: um solve de flop resolvido ocupa ~80 MB de RAM (matrizes do
# CFR+). O VPS é compartilhado — guardar 4 spots custaria mais memória do
# que o bot inteiro. Dois basta: o par de gráficos sai do mesmo.
@lru_cache(maxsize=2)
def _solve_posflop(board: tuple, oop_range: str, ip_range: str,
                   pot: float, stack: float):
    """Um spot pós-flop resolvido UMA vez. O par de gráficos (valor por mão +
    frequência de agressão) sai do MESMO equilíbrio — sem o cache, pedir os
    dois pagava o CFR+ duas vezes (no flop isso é ~35s cada)."""
    from app.analysis.river_solver import RiverSolver

    return RiverSolver(list(board), oop_range, ip_range, pot, stack).solve()


def _valores_posflop(board: tuple, oop_range: str, ip_range: str,
                     pot: float, stack: float, player: str):
    return _solve_posflop(board, oop_range, ip_range, pot,
                          stack).hand_values(player)


def chart_postflop(board: list[str], oop_range: str, ip_range: str,
                   pot: float, stack: float, player: str = "oop",
                   mode: str | None = None) -> tuple[bytes, str] | None:
    """Range view PÓS-FLOP: quanto cada mão VALE no spot (mode='ev') ou com
    que frequência ela agride (mode=None). Sai do mesmo CFR+ do solve_river.

    No equilíbrio as ações do suporte valem o mesmo, então mostrar
    'EV(aposta) − EV(check)' daria ~0 em tudo — o que informa é o VALOR da
    mão e a frequência, igual à range view dos solvers."""
    try:
        hv = _valores_posflop(tuple(board), oop_range, ip_range,
                              float(pot), float(stack), player)
    except Exception:
        return None
    if not hv:
        return None

    from app.analysis.equity import pretty_cards

    quem = "você" if player == "oop" else "o vilão"
    cartas = pretty_cards(list(board))
    street = {3: "FLOP", 4: "TURN", 5: "RIVER"}.get(len(board), "spot")
    prem = (f"premissas: CFR+ range vs range · pote {pot:g} · stack {stack:g} · "
            f"sizings 50%/100%/all-in, uma raise por street"
            + ("" if len(board) == 5 else " · próxima carta amostrada"))
    if mode == "ev":
        png = render_ev_range_png(
            hv["ev"], hv["ev_medio"],
            f"Valor de cada mão — {street} {cartas}",
            f"em fichas · média do range {hv['ev_medio']:+.1f} · {quem} age",
            premises=prem,
            legend=("verde = acima da média do range · vermelho = abaixo · "
                    "célula vazia = mão fora do range"))
        return png, (
            f"\u2660 Quanto cada mão do seu range VALE neste {street.lower()} "
            f"({cartas}), em fichas. Verde = acima da média do range "
            f"({hv['ev_medio']:+.1f}); vermelho = abaixo.")
    png = render_range_png(
        hv["freq"], f"Agressão — {street} {cartas}",
        f"frequência de apostar/pagar no equilíbrio · pote {pot:g} · {quem} age")
    return png, (
        f"\u2660 Com que frequência cada mão APOSTA (ou paga) no equilíbrio "
        f"deste {street.lower()} ({cartas}).")
