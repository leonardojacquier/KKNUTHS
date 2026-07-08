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


def test_style_report_uses_corrected_numbers():
    import app.bot.processing as proc

    tg = 323232
    # 4 mãos < mínimo de 10 -> None (sem quebrar com o caminho bayesiano)
    proc.RECENT_HANDS[tg] = _hands()
    try:
        assert proc.style_report(tg, "tester") is None
    finally:
        proc.RECENT_HANDS.pop(tg, None)
