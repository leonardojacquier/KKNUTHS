"""Testes das features de lançamento: push/fold, cota, mãos-chave, stats de herói,
pipeline de processamento. Herméticos (sem chaves, sem rede)."""
from pathlib import Path

import pytest

from app.agent.analyzer import select_key_hands
from app.analysis import compute_player_stats
from app.analysis.pushfold import canonical_hand, hand_percentile, push_fold
from app.bot.processing import RECENT_HANDS, build_drill, process_upload, reveal_drill
from app.config import get_settings
from app.parsers import parse_text
from app.quota import FREE_MONTHLY_ANALYSES, check_quota, consume_quota, reset_memory

PS = Path(__file__).parent / "sample_hands" / "pokerstars_tournament.txt"

_SECRET_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "VOYAGE_API_KEY",
    "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "STRIPE_SECRET_KEY", "TELEGRAM_BOT_TOKEN",
]


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    for var in _SECRET_VARS:
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    reset_memory()
    RECENT_HANDS.clear()
    yield
    get_settings.cache_clear()
    reset_memory()
    RECENT_HANDS.clear()


# ---------------------------- push/fold ----------------------------
def test_canonical_hand():
    assert canonical_hand(["As", "Kd"]) == "AKo"
    assert canonical_hand(["9s", "Ts"]) == "T9s"
    assert canonical_hand(["7h", "7d"]) == "77"


def test_pushfold_aa_always_push():
    for pos in ("UTG", "MP", "CO", "BTN", "SB"):
        r = push_fold(["As", "Ac"], 10, pos)
        assert r["applicable"] and r["decision"] == "push"


def test_pushfold_trash_folds_early_position():
    r = push_fold(["7s", "2d"], 15, "UTG")
    assert r["applicable"] and r["decision"] == "fold"


def test_pushfold_not_applicable_deep():
    r = push_fold(["As", "Kd"], 40, "BTN")
    assert r["applicable"] is False


def test_percentile_monotonic():
    assert hand_percentile(["As", "Ac"]) < hand_percentile(["7s", "2d"])


# ------------------------------ cota -------------------------------
def test_quota_memory_limit():
    tg = 999
    for _ in range(FREE_MONTHLY_ANALYSES):
        assert check_quota(tg, None).allowed
        consume_quota(tg, None)
    q = check_quota(tg, None)
    assert q.allowed is False and q.remaining == 0


def test_quota_unlimited_for_pro_plan():
    q = check_quota(1, {"plan": "pro"})
    assert q.allowed and q.remaining == -1


# --------------------------- mãos-chave ----------------------------
def test_select_key_hands_prioritizes_allins():
    hands = parse_text(PS.read_text())
    key = select_key_hands(hands, k=1)
    assert len(key) == 1
    # a mão 1 tem all-in e maior swing; a mão 2 é um fold pré-flop
    assert key[0]["hand_id"] == "243490000001"


# ------------------------- stats modo herói ------------------------
def test_stats_hero_mode_equals_named():
    hands = parse_text(PS.read_text())
    by_name = compute_player_stats(hands, "Hero")
    by_hero = compute_player_stats(hands, player=None)
    assert by_hero.hands == by_name.hands
    assert by_hero.vpip == by_name.vpip
    assert by_hero.pfr == by_name.pfr


# ------------------------- pipeline completo -----------------------
def test_process_upload_offline_returns_analysis():
    reply = process_upload(PS.read_text().encode(), "txt", 777, "tester")
    assert "2 mão(s)" in reply
    assert "restantes no mês" in reply.lower() or "restantes" in reply


def test_process_upload_consumes_quota():
    tg = 778
    before = check_quota(tg, None).remaining
    process_upload(PS.read_text().encode(), "txt", tg, "tester")
    after = check_quota(tg, None).remaining
    assert after == before - 1


def test_process_upload_blocks_over_quota():
    tg = 779
    for _ in range(FREE_MONTHLY_ANALYSES):
        consume_quota(tg, None)
    reply = process_upload(PS.read_text().encode(), "txt", tg, "tester")
    # bloqueia, e não num beco: diz a DATA da virada e o que continua de pé
    import re

    assert "acabaram" in reply.lower()
    assert re.search(r"renova .*\(01/\d{2}\)", reply), \
        "sem a data da virada é o mesmo beco de antes"
    assert "/treino" in reply, "cota trava o upload, não a ferramenta inteira"


def test_drill_flow():
    tg = 780
    process_upload(PS.read_text().encode(), "txt", tg, "tester")
    drill = build_drill(tg)
    assert drill is not None
    # o quiz v2 escolhe a decisão mais interessante — pode ser pós-flop
    assert drill["cards"]
    assert drill["actual"] in ("fold", "check", "call", "bet", "raise")
    text = reveal_drill(drill, "call")
    assert "Você escolheu" in text
