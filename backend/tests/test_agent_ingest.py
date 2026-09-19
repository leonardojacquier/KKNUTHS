from pathlib import Path

from app.agent import analyze_hand, analyze_tournament
from app.ingestion import ingest

SAMPLE = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"


def test_ingest_txt():
    res = ingest(SAMPLE.read_text(), "txt")
    assert res.site == "PokerStars"
    assert res.confidence == 1.0
    assert len(res.hands) == 2
    assert res.needs_review is False


def test_ingest_unknown_format_flags_review():
    # texto sem NENHUM sinal de poker: a heurística barra antes do LLM —
    # determinístico em qualquer ambiente, com ou sem chave de API
    res = ingest("relatório de vendas do trimestre, nada a ver com cartas", "txt")
    assert res.hands == []
    assert res.needs_review is True


def test_poker_text_heuristic():
    from app.ingestion.pipeline import _looks_like_poker_text

    assert _looks_like_poker_text("hero tem As Kd no button") is True
    assert _looks_like_poker_text("no flop veio blank e ele foldou pro raise") is True
    assert _looks_like_poker_text("ata da reunião de condomínio") is False


def test_analyze_hand_pot_and_net():
    res = ingest(SAMPLE.read_text(), "txt")
    a = analyze_hand(res.hands[0])
    # 3-bet pré-flop: open de Villain4 era 120; pote antes do raise do Hero = 258
    pre = [s for s in a["spots"] if s["street"] == "preflop"][0]
    assert pre["amount"] == 390
    assert pre["pot_before"] == 258
    assert a["net_chips"] == 1384.0   # ganhou 2884, investiu 1500
    assert a["position"] == "SB"


def test_analyze_tournament_aggregates():
    res = ingest(SAMPLE.read_text(), "txt")
    rep = analyze_tournament(res.hands)
    assert rep["hands"] == 2
    assert rep["all_in_spots"] == 1
    assert rep["hero"] == "Hero"
