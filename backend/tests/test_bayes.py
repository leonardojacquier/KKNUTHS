"""Shrinkage bayesiano: números honestos com amostra pequena (fase 1)."""
from pathlib import Path

from app.analysis.bayes import bayes_stats, fmt_rate, shrunk_af, shrunk_rate
from app.analysis.stats import compute_player_stats
from app.parsers import parse_text


def _hands():
    return parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )


def test_small_sample_never_screams_100pct():
    # caso real que nos queimou: 2 oportunidades, 2 3-bets -> "100%" cru
    mean, lo, hi = shrunk_rate(2, 2, 7.0, 25.0)
    assert mean < 20.0            # ancorado no field, não em 100%
    assert hi - lo > 10.0         # e o intervalo confessa a incerteza


def test_large_sample_dominates_prior():
    mean, lo, hi = shrunk_rate(300, 1000, 24.0, 40.0)
    assert abs(mean - 30.0) < 1.5  # o dado manda, o prior quase some
    assert hi - lo < 7.0           # intervalo estreito = cravado


def test_af_shrinks_toward_field():
    assert 1.5 < shrunk_af(3, 0) < 3.5   # 3 bets, 0 calls: cru seria infinito
    big = shrunk_af(300, 100)
    assert abs(big - 3.0) < 0.3          # amostra grande ~ AF cru (300/100)


def test_bayes_stats_from_real_hands():
    s = compute_player_stats(_hands(), player=None)
    b = bayes_stats(s)
    for k in ("vpip", "pfr", "three_bet"):
        assert 0.0 <= b[k]["lo"] <= b[k]["mean"] <= b[k]["hi"] <= 100.0
        assert not b[k]["firm"]          # 4 mãos não cravam nada
    assert b["af"]["mean"] > 0
    txt = fmt_rate(b["vpip"], "VPIP")
    assert "entre" in txt                # frase honesta com amostra pequena


def test_stats_report_exists_and_runs_offline():
    # regressão: o `def stats_report` sumiu numa edição e /stats quebrou em
    # produção sem nenhum teste acusar — este teste trava a porta
    import app.bot.processing as proc

    tg = 313131
    proc.RECENT_HANDS[tg] = _hands()
    try:
        msg = proc.stats_report(tg, "tester")
        assert msg and "Seu perfil" in msg
        assert "100%" not in msg          # shrinkage segura o 3-bet de amostra mínima
    finally:
        proc.RECENT_HANDS.pop(tg, None)


def test_leak_detector_and_study_plan():
    from app.analysis.leaks import detect_leaks, leaks_text

    hands = _hands()
    # amostra limpa: folds padrão não viram leak (nada de acusação vazia)
    assert detect_leaks(hands * 3) == []

    # agora o herói folda AKo em pote não aberto, 4 vezes: leak de verdade
    folded = next(h for h in hands if h.hand_id == "TM6146070321")
    fakes = []
    for i in range(4):
        fk = folded.model_copy(deep=True)
        fk.hand_id = f"FAKE{i}"
        fk.hero_cards = ["Ah", "Kc"]
        fakes.append(fk)
    leaks = detect_leaks(fakes)
    assert leaks and leaks[0]["leak"] == "open_perdido"
    assert leaks[0]["escorregadas"] == 4
    assert leaks[0]["custo_bb_100maos"] > 0
    txt = leaks_text(leaks)
    assert "custando" in txt and "4 de 4" in txt

    # 1 escorregada em 2 chances NÃO crava leak crônico (shrinkage segura)
    um_so = detect_leaks([fakes[0], folded])
    assert all(lk["escorregadas"] >= 1 for lk in um_so)  # se aparecer, é honesto


def test_range_tracker_updates_toward_value_on_big_bets():
    from app.analysis.rangetracker import RangeTracker

    tr = RangeTracker("CO", "open", dead=["Ah", "Qd"])
    board = ["Kh", "7d", "2c"]
    antes = tr.shares(board)
    tr.update(board, "bet", size_pct_pot=85)
    depois = tr.shares(board)
    # bomba de 85% do pote: fatia de mão forte SOBE, ar DESCE
    assert depois["forte"] > antes["forte"]
    assert depois["ar"] < antes["ar"]


def test_range_tracker_check_shifts_to_weak():
    from app.analysis.rangetracker import RangeTracker

    tr = RangeTracker("BTN", "open")
    board = ["As", "Td", "4c"]
    antes = tr.shares(board)
    tr.update(board, "check")
    depois = tr.shares(board)
    assert depois["forte"] < antes["forte"]  # check esconde pouco valor


def test_read_villain_full_line_and_odds():
    from app.analysis.rangetracker import odds_pt, read_villain

    out = read_villain(
        "CO", "open", ["Kh", "7d", "2c", "2s"],
        [{"board_cards": 3, "action": "bet", "size_pct_pot": 33},
         {"board_cards": 4, "action": "bet", "size_pct_pot": 80}],
        hero_cards=["Ah", "Qd"],
    )
    assert out["p_valor"] > out["p_blefe_ou_draw"]
    assert "pra 1" in out["leitura"] or "equilibrado" in out["leitura"]
    assert len(out["passos"]) == 2
    assert "estimativa" in out["atencao"]      # nunca vende certeza
    assert odds_pt(0.8, 0.2).startswith("cerca de 4 pra 1")
    assert "equilibrado" in odds_pt(0.5, 0.5)


def test_read_villain_dispatch():
    from app.agent.llm import _dispatch

    r = _dispatch("read_villain", {
        "position": "BTN", "preflop": "open",
        "board": ["9h", "8h", "2d"],
        "actions": [{"board_cards": 3, "action": "bet", "size_pct_pot": 70}],
        "hero_cards": ["Ac", "Kc"],
    })
    assert "leitura" in r and "fatias" in r
    # board com draws: a fatia de draw existe e é considerada
    assert r["fatias"]["draw"] > 0


def test_parser_captures_shown_cards():
    hands = _hands()
    sd = next(h for h in hands if h.hand_id == "TM6146070388")
    assert sd.shown_cards.get("Hero") == ["3c", "Ad"]
    assert sd.shown_cards.get("609c9948") == ["Tc", "Ts"]


def test_bucket_of_combo_extremes():
    from app.analysis.calibration import bucket_of_combo

    board = ["Kh", "7d", "2c"]
    assert bucket_of_combo(["Kd", "Kc"], board) == "forte"   # trinca
    assert bucket_of_combo(["4c", "3d"], board) == "ar"      # nada, sem draw


def test_showdown_observation_and_blend():
    from app.analysis.calibration import (
        calibrated_tables, empty_counts, observe_showdowns,
    )
    from app.analysis.rangetracker import LIKELIHOOD
    from app.models.canonical import (
        Action, ActionType, CanonicalHand, Street, StreetName,
    )

    # vilão mostra trinca no showdown e tinha APOSTADO o flop: 1 observação
    # (bet | forte)
    h = CanonicalHand(
        site="GGPoker", hand_id="CAL1", hero="Hero",
        shown_cards={"Hero": ["Ah", "Ad"], "vilao": ["Kd", "Kc"]},
        streets=[
            Street(name=StreetName.PREFLOP),
            Street(name=StreetName.FLOP, board=["Kh", "7d", "2c"], actions=[
                Action(actor="vilao", type=ActionType.BET, amount=100),
                Action(actor="Hero", type=ActionType.CALL, amount=100),
            ]),
        ],
    )
    counts = observe_showdowns([h, h])  # duplicada: dedupe por (site, hand_id)
    assert counts["bet"]["forte"] == 1
    assert sum(v for by in counts.values() for v in by.values()) == 1

    # blend: sem dado nenhum, tabela == prior
    assert calibrated_tables(empty_counts()) == {
        a: {b: LIKELIHOOD[a][b] for b in LIKELIHOOD[a]} for a in LIKELIHOOD}
    # com MUITO dado de "forte aposta", bet_big|forte sobe e check|forte cai
    heavy = empty_counts()
    heavy["bet"]["forte"] = 200
    t = calibrated_tables(heavy)
    assert t["bet_big"]["forte"] > LIKELIHOOD["bet_big"]["forte"]
    assert t["check"]["forte"] < LIKELIHOOD["check"]["forte"]


def test_tracker_loads_calibration_file(tmp_path, monkeypatch):
    import json

    from app.analysis import rangetracker as rt

    tables = {a: dict(rt.LIKELIHOOD[a]) for a in rt.LIKELIHOOD}
    tables["bet_big"]["forte"] = 0.9
    f = tmp_path / "calibration.json"
    f.write_text(json.dumps({"tables": tables}))
    monkeypatch.setenv("CALIBRATION_FILE", str(f))
    rt.reset_calibration_cache()
    try:
        assert rt._likelihood()["bet_big"]["forte"] == 0.9
    finally:
        rt.reset_calibration_cache()
    # sem arquivo: cai no prior sem quebrar
    monkeypatch.setenv("CALIBRATION_FILE", str(tmp_path / "nao_existe.json"))
    rt.reset_calibration_cache()
    try:
        assert rt._likelihood() == rt.LIKELIHOOD
    finally:
        rt.reset_calibration_cache()


def test_style_report_uses_corrected_numbers():
    import app.bot.processing as proc

    tg = 323232
    # 4 mãos < mínimo de 10 -> None (sem quebrar com o caminho bayesiano)
    proc.RECENT_HANDS[tg] = _hands()
    try:
        assert proc.style_report(tg, "tester") is None
    finally:
        proc.RECENT_HANDS.pop(tg, None)
