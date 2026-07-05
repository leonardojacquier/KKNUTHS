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
