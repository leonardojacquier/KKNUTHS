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
