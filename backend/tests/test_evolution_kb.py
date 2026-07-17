"""Base de conhecimento do jogador: evolução, caderno do coach e estilos pró."""
from app.analysis.evolution_chart import evolution_text, render_evolution_png
from app.analysis.pro_styles import ARCHETYPES, match_pro_style

HIST = [
    {"created_at": "2026-06-14T10:00", "hands": 60, "vpip": 34.0, "pfr": 12.0,
     "three_bet": 4.0, "af": 1.1, "net_bb": -18.0, "label": "loose-passive"},
    {"created_at": "2026-06-28T10:00", "hands": 260, "vpip": 27.0, "pfr": 18.0,
     "three_bet": 8.0, "af": 2.1, "net_bb": 25.0, "label": "TAG"},
]


def test_evolution_chart_renders():
    png = render_evolution_png(HIST)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_evolution_text_reads_deltas():
    txt = evolution_text(HIST)
    assert "VPIP ↓" in txt and "PFR ↑" in txt
    assert "+7.0 BB" in txt  # -18 + 25


def test_style_matcher_archetypes():
    assert "TAG" in match_pro_style(23, 18, 2.5, 8)["estilo"]
    assert "calling station" in match_pro_style(40, 8, 0.9, 2)["estilo"]
    assert "LAG" in match_pro_style(31, 25, 3.3, 12)["estilo"]
    assert "Nit" in match_pro_style(13, 9, 1.3, 3)["estilo"]


def test_style_matcher_has_br_and_intl_pros():
    todos = " ".join(n for a in ARCHETYPES for n, _ in a["pros"])
    assert "Dzivielevski" in todos and "Akkari" in todos       # BR
    assert "Dwan" in todos and "Negreanu" in todos             # internacional


def test_style_transition_path():
    m = match_pro_style(13, 9, 1.2, 3, desired="lag")
    assert m["transicao_para"].startswith("LAG")
    assert any("VPIP ↑" in x for x in m["ajustes_numericos"])
    assert m["caminho"]


def test_note_tool_and_collector():
    from app.agent.llm import _dispatch, charts_from_tool_call

    r = _dispatch("record_student_note", {"kind": "leak", "note": "abre A6o de UTG"})
    assert r.get("ok")
    spec = charts_from_tool_call("record_student_note",
                                 {"kind": "leak", "note": "abre A6o de UTG"}, r)
    assert spec == ("note", "leak", "abre A6o de UTG")
    assert "error" in _dispatch("record_student_note", {"kind": "leak", "note": " "})


def test_stash_separates_notes_from_charts():
    from app.bot import processing as proc

    proc.PENDING_CHARTS.pop(424242, None)
    # nota não vira gráfico pendente (e sem banco, só é ignorada com segurança)
    proc._stash_charts(424242, [("note", "leak", "x")], user_id=None)
    assert proc.pop_charts(424242) == []


def test_compare_style_tool_dispatch():
    from app.agent.llm import _dispatch

    r = _dispatch("compare_style_to_pros",
                  {"vpip": 23, "pfr": 18, "af": 2.5, "three_bet": 8, "desired": "gto"})
    assert "estilo" in r and r["jogadores_parecidos"]
    assert "transicao_para" in r


def test_tournament_board_from_real_hands():
    from pathlib import Path

    from app.analysis.tournament_board import (
        render_tournament_board, tournament_summary,
    )
    from app.parsers import parse_text

    hands = parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )
    png, cap = render_tournament_board(hands)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert "295746366" in cap
    s = tournament_summary(hands)
    assert s["hands"] == 4 and s["net_bb"] > 20
    # curva do stack: começa ~25bb e termina ~49.5bb (pote grande do A3o)
    assert abs(s["stacks_bb"][0][1] - 25.0) < 0.5
    assert abs(s["stacks_bb"][-1][1] - 49.5) < 1.0


def test_indicator_charts_render():
    from app.analysis.evolution_chart import render_indicator_png

    hist = [
        {"created_at": "2026-06-14", "vpip": 34.0, "pfr": 12.0, "three_bet": 4.0,
         "af": 1.1, "net_bb": -18.0},
        {"created_at": "2026-07-04", "vpip": 25.0, "pfr": 19.0, "three_bet": 9.0,
         "af": 2.4, "net_bb": 14.0},
    ]
    for ind in ("vpip", "pfr", "3bet", "af", "bb"):
        png = render_indicator_png(hist, ind)
        assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    assert render_indicator_png(hist, "xyz") is None
    assert render_indicator_png(hist[:1], "vpip") is None


def test_style_card_renders():
    from app.analysis.style_chart import render_style_png

    png = render_style_png(23.0, 18.0, 2.5, 8.0)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    png2 = render_style_png(40.0, 8.0, 0.9, 2.0)  # calling station
    assert png2[:8] == b"\x89PNG\r\n\x1a\n"


def test_manual_pdf_asset_exists():
    from pathlib import Path

    pdf = Path(__file__).parent.parent / "app" / "api" / "assets" / "KKNuths-Manual.pdf"
    assert pdf.exists() and pdf.stat().st_size > 100_000
    assert pdf.read_bytes()[:5] == b"%PDF-"


def test_professional_quiz_drill():
    import random

    from pathlib import Path

    import app.bot.processing as proc
    from app.parsers import parse_text

    random.seed(4)
    hands = parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )
    proc.RECENT_HANDS[999777] = hands
    try:
        drill = proc.build_drill(999777)
        assert drill and drill.get("story"), "quiz sem história da mão"
        msg = proc.drill_message(drill)
        # contexto profissional: formato, jogadores, pote e a vez do herói
        assert "blinds" in msg and "jogadores" in msg
        assert "pote:" in msg and "Sua vez" in msg
        # spot interessante: tem preço a pagar (não fold trivial pré-flop)
        assert drill["to_call_bb"] > 0 and drill["required_eq"]
        # gabarito com matemática e ação real com sizing
        reveal = proc.reveal_drill(drill, "call")
        assert "A conta" in reveal and "equity" in reveal
        assert "Na mão real" in reveal
        # menu em dois passos: principal = ação; submenu = tamanhos em bb
        btns = [b["text"] for row in proc.drill_buttons(drill) for b in row]
        blob = " ".join(btns)
        assert "Fold" in blob and "Call" in blob and "Raise" in blob
        sub = " ".join(b["text"]
                       for row in proc.drill_size_buttons(drill) for b in row)
        assert "3x" in sub and "All-in" in sub and "Voltar" in sub
        # o choice do botão de tamanho normaliza pra ação base
        assert proc.drill_action("raise3x") == ("raise", "RAISE 3x")
        assert proc.drill_action("allin")[0] == "raise"
    finally:
        proc.RECENT_HANDS.pop(999777, None)


def test_analysis_carries_stack_context():
    # caso real: coach disse "12bb" quando o aluno tinha 58bb — o 12 era o BB.
    # A análise agora entrega os stacks; o prompt proíbe estimar.
    from pathlib import Path

    from app.agent.analyzer import analyze_hand
    from app.parsers import parse_text

    hands = parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )
    a = analyze_hand(hands[0])  # A3o no BB, stack 10.850 / bb 400
    assert a["hero_stack_bb"] == 27.1
    assert a["blinds"].startswith("200/400")
    assert a["players"] == 8
    assert a["effective_bb"] == 27.1  # tem vilão maior que o herói
    assert "BB" in a["stacks_bb"] and a["stacks_bb"]["BB"] == 27.1
    # spots em BB também
    spot = a["spots"][0]
    assert "pot_bb" in spot and "to_call_bb" in spot


def test_search_hands_patterns():
    from pathlib import Path

    from app.analysis.handsearch import search_hands
    from app.parsers import parse_text

    hands = parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )
    folds = search_hands(hands, "fold", street="preflop")
    assert folds and all("linha_do_heroi" in f for f in folds)
    assert all(f["hero_stack_bb"] for f in folds)
    raises = search_hands(hands, "raise")
    assert raises  # A3o (raise no turn) e 78s (open)
    assert search_hands(hands, "cbet") == []  # herói nunca c-betou nesse lote


def test_search_hands_dispatch_needs_user():
    from app.agent.llm import _dispatch, set_tool_user

    set_tool_user(None)
    assert "error" in _dispatch("search_hands", {"pattern": "fold"})
    assert "error" in _dispatch("get_hand", {"query": "A3o"})


def test_find_hand_by_number_and_cards():
    # promessa feita ao beta: "me diga as cartas ou o Nº da mão que eu abro"
    from pathlib import Path

    from app.analysis.handsearch import _classes_from_query, find_hand
    from app.parsers import parse_text

    hands = parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )
    # pelo Nº da sala (como aparece no relatório mão a mão), até parcial
    got = find_hand(hands, "TM6146070388")
    assert len(got) == 1 and got[0]["classe"] == "A3o"
    assert got[0]["historia"] and got[0]["numeros_calculados"] is not None
    assert got[0]["hero_stack_bb"] and got[0]["blinds"]
    assert find_hand(hands, "6146070388")[0]["hand_id"] == "TM6146070388"
    # pelas cartas: classe exata, ambígua ('A3') e naipes exatos
    assert find_hand(hands, "a3o")[0]["hand_id"] == "TM6146070388"
    assert find_hand(hands, "A3")[0]["hand_id"] == "TM6146070388"
    # notação com 10: 'A10o' -> 'ATo'
    assert _classes_from_query("A10o") == {"ATo"}
    assert _classes_from_query("kk") == {"KK"}
    assert _classes_from_query("98") == {"98s", "98o"}
    assert _classes_from_query("xyz") == set()
    assert find_hand(hands, "") == []


def test_hand_by_hand_report():
    from pathlib import Path

    from app.analysis.handreport import build_report_html
    from app.parsers import parse_text

    hands = parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )
    html = build_report_html(
        hands, "leitura do coach aqui",
        per_hand_analysis={"TM6146070388": "análise específica do A3o"},
    )
    assert "Análise mão a mão" in html and "295746366" in html
    # mãos jogadas viram cards com análise; folds viram tabela com veredito
    assert html.count("class=hand") == 2
    assert "análise específica do A3o" in html
    assert "fold padrão" in html            # veredito técnico em TODO fold
    assert "TM6146070321" in html           # Nº da mão identifica cada linha
    assert "leitura do coach aqui" in html
    # NUNCA "pergunte ao coach" como veredito
    assert "pergunte ao coach para abrir" not in html
