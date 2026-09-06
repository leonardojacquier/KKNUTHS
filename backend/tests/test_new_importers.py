"""Testes dos novos modos de importação: Winamax, PartyPoker, 888poker e CSV."""
from pathlib import Path

from app.agent import analyze_hand
from app.ingestion import ingest
from app.models.canonical import ActionType, StreetName
from app.parsers import detect_site, parse_text

SAMPLES = Path(__file__).parent / "sample_hands"


# ------------------------------- Winamax -------------------------------
def test_winamax_parses():
    raw = (SAMPLES / "winamax_cash.txt").read_text()
    assert detect_site(raw) == "Winamax"
    h = parse_text(raw)[0]
    assert h.hero == "Hero" and h.hero_cards == ["Qs", "Qd"]
    assert h.stakes.small_blind == 0.01 and h.stakes.big_blind == 0.02
    pos = {p.name: p.position for p in h.players}
    assert pos["Villain1"] == "BTN" and pos["Hero"] == "SB"
    assert h.street(StreetName.FLOP).board == ["8h", "5c", "2s"]
    assert h.street(StreetName.TURN).board == ["8h", "5c", "2s", "Jd"]
    # 3-bet do Hero: raises 0.14 to 0.20
    pre = h.street(StreetName.PREFLOP)
    hero_raise = [a for a in pre.actions if a.actor == "Hero" and a.type == ActionType.RAISE]
    assert hero_raise[0].to_amount == 0.20
    assert h.collected["Hero"] == 1.55
    assert h.total_pot == 1.55


def test_winamax_analyzable():
    h = parse_text((SAMPLES / "winamax_cash.txt").read_text())[0]
    a = analyze_hand(h)
    assert a["position"] == "SB" and a["spots"]


# ------------------------------ PartyPoker ------------------------------
def test_partypoker_parses():
    raw = (SAMPLES / "partypoker_cash.txt").read_text()
    assert detect_site(raw) == "PartyPoker"
    h = parse_text(raw)[0]
    assert h.hand_id == "23456789012"
    assert h.hero == "Hero" and h.hero_cards == ["Ah", "Qh"]
    assert h.stakes.small_blind == 0.05 and h.stakes.big_blind == 0.10
    assert h.street(StreetName.FLOP).board == ["Qc", "7d", "3s"]
    flop_raises = [a for a in h.street(StreetName.FLOP).actions
                   if a.actor == "Hero" and a.type == ActionType.RAISE]
    assert flop_raises and flop_raises[0].amount == 1.20
    assert h.collected["Hero"] == 1.48


# -------------------------------- 888poker -------------------------------
def test_888_parses():
    raw = (SAMPLES / "poker888_cash.txt").read_text()
    assert detect_site(raw) == "888poker"
    h = parse_text(raw)[0]
    assert h.hero_cards == ["Ts", "Td"]
    assert h.street(StreetName.RIVER).board == ["9c", "6h", "2d", "2c", "Kh"]
    assert h.final_board == ["9c", "6h", "2d", "2c", "Kh"]
    assert h.collected["Hero"] == 1.19
    pos = {p.name: p.position for p in h.players}
    assert pos["Villain3"] == "BTN"


# ------------------------------ CSV tracker ------------------------------
def test_csv_via_ingest():
    res = ingest((SAMPLES / "tracker_export.csv").read_text(), "csv")
    assert res.source_format == "csv" and len(res.hands) == 4
    assert res.needs_review is False
    h = res.hands[0]
    assert h.hero_cards == ["As", "Kd"] and h.collected.get("Hero") == 12.50
    # símbolos de naipe e '10' normalizados
    assert res.hands[2].hero_cards == ["Qs", "Js"]
    assert res.hands[3].hero_cards == ["Td", "Ts"]


def test_csv_sniffed_from_plain_text_upload():
    # mesmo sem extensão .csv, o conteúdo é reconhecido
    res = ingest((SAMPLES / "tracker_export.csv").read_text(), "txt")
    assert len(res.hands) == 4


def test_csv_unrecognized_columns():
    res = ingest("a;b;c\n1;2;3\n", "csv")
    assert res.hands == [] and res.needs_review is True
