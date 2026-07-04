"""Regressões da caçada de bugs (5 investigadores, 2026-07-04).

Cada teste referencia um bug REAL demonstrado com repro executado — se algum
voltar a falhar, é regressão de um problema que já mordeu (ou quase mordeu)
usuário de verdade.
"""
from pathlib import Path

import pytest

from app.models.canonical import GameType, HandFormat
from app.parsers import detect_site, parse_text

GG_PASTE = (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()

PS_CASH = """PokerStars Hand #250000000001: Hold'em No Limit ($0.05/$0.10 USD) - 2026/07/01 20:00:00 ET
Table 'Aludra II' 6-max Seat #1 is the button
Seat 1: Alice ($10.00 in chips)
Seat 2: Bob ($9.55 in chips)
Seat 3: Hero ($12.30 in chips)
Alice: posts small blind $0.05
Bob: posts big blind $0.10
*** HOLE CARDS ***
Dealt to Hero [Ah Kh]
Hero: raises $0.20 to $0.30
Alice: folds
Bob: calls $0.20
*** FLOP *** [Kd 7s 2c]
Bob: checks
Hero: bets $0.40
Bob: folds
Uncalled bet ($0.40) returned to Hero
Hero collected $0.62 from pot
*** SUMMARY ***
Total pot $0.65 | Rake $0.03
Seat 3: Hero collected ($0.62)
"""


# ----------------------- parsers: cash real com $/€ -----------------------
def test_ps_cash_dollar_amounts():
    (h,) = parse_text(PS_CASH)
    assert h.stakes.small_blind == 0.05 and h.stakes.big_blind == 0.10
    assert len(h.players) == 3
    hero = next(p for p in h.players if p.is_hero)
    assert hero.stack == 12.30
    raise_a = next(a for s in h.streets for a in s.actions if a.type.value == "raise")
    assert raise_a.amount == 0.20 and raise_a.to_amount == 0.30
    assert h.collected["Hero"] == 0.62
    assert h.total_pot == 0.65 and h.rake == 0.03
    assert h.uncalled["Hero"] == 0.40


def test_ps_cash_euro_amounts():
    (h,) = parse_text(PS_CASH.replace("$", "€").replace(" USD", " EUR"))
    assert h.stakes.big_blind == 0.10 and len(h.players) == 3


def test_ps_zoom_detected():
    zoom = PS_CASH.replace("PokerStars Hand #", "PokerStars Zoom Hand #")
    assert detect_site(zoom) == "PokerStars"
    assert len(parse_text(zoom)) == 1


def test_posts_small_and_big_blinds():
    txt = PS_CASH.replace(
        "Bob: posts big blind $0.10",
        "Bob: posts big blind $0.10\nCarol2: posts small & big blinds $0.15",
    )
    (h,) = parse_text(txt)
    posts = [a for a in h.streets[0].actions if a.type.value == "post"]
    assert any(a.actor == "Carol2" and a.amount == 0.15 for a in posts)


def test_plo_labeled():
    plo = PS_CASH.replace("Hold'em No Limit", "Omaha Pot Limit")
    (h,) = parse_text(plo)
    assert h.game == GameType.PLO


# --------------------- resultado líquido com uncalled ---------------------
def test_net_result_with_uncalled_bet():
    from app.agent.analyzer import analyze_hand

    (h,) = parse_text(PS_CASH)
    a = analyze_hand(h)
    # herói投 0.30 pré + 0.40 flop, 0.40 devolvido, coletou 0.62:
    # net = 0.62 - (0.70 - 0.40) = +0.32 (mão GANHA não pode sair negativa)
    assert a["net_chips"] == pytest.approx(0.32)
    assert a["pot_total"] == pytest.approx(0.65)  # sem o uncalled


# ----------------------- paste misto de duas salas -----------------------
def test_mixed_site_paste_routes_per_hand():
    first_gg = GG_PASTE.split("\n\n")[1]
    mixed = PS_CASH + "\n\n" + first_gg
    hands = parse_text(mixed)
    sites = {h.site for h in hands}
    assert sites == {"PokerStars", "GGPoker"}
    ps = next(h for h in hands if h.site == "PokerStars")
    assert ps.collected["Hero"] == 0.62  # o pote do GG não pode vazar para cá


# ------------------------- solver: BB não invertido ------------------------
def test_jam_fold_bb_not_inverted():
    solver = pytest.importorskip("app.analysis.jam_fold_solver")
    nash = pytest.importorskip("app.analysis.nash_pushfold")
    if not solver.available() or not nash.available():
        pytest.skip("tabelas não geradas")
    sol = solver.solve_jam_fold(10.0, 1.0)
    assert sol["bb_call"]["AA"] > 0.5 and sol["bb_ev"]["AA"] > 0
    assert sol["bb_call"]["72o"] < 0.5 and sol["bb_ev"]["72o"] < sol["bb_fold_ev"]
    # ranges runtime ~= tabela de referência (mãos marginais mistas toleradas)
    table = nash._table()["stacks"]["10"]
    run_call = {h for h, f in sol["bb_call"].items() if f > 0.5}
    assert len(run_call ^ set(table["bb_call"])) <= 4


# ------------------------------ stats: 3-bet ------------------------------
def test_three_bet_counts_opportunities():
    from app.analysis.stats import compute_player_stats
    from app.models.canonical import (
        Action, ActionType, CanonicalHand, PlayerSeat, Street, StreetName,
    )

    def hand_facing_open(hero_action: ActionType) -> CanonicalHand:
        return CanonicalHand(
            hand_id=f"x{hero_action.value}", site="T", hero="H",
            players=[PlayerSeat(seat=1, name="V", stack=100),
                     PlayerSeat(seat=2, name="H", stack=100, is_hero=True)],
            streets=[Street(name=StreetName.PREFLOP, actions=[
                Action(actor="V", type=ActionType.RAISE, amount=3, to_amount=3),
                Action(actor="H", type=hero_action, amount=3, to_amount=9),
            ])],
        )

    hands = [hand_facing_open(ActionType.FOLD) for _ in range(9)]
    hands.append(hand_facing_open(ActionType.RAISE))
    s = compute_player_stats(hands, player="H")
    assert s.detail["three_bet_opps"] == 10
    assert s.three_bet == pytest.approx(10.0)


# ------------------------------ ranges novos ------------------------------
def test_range_spans_and_builtin_constants():
    from app.analysis.ranges import THREEBET_RANGES, parse_range

    assert set(parse_range("A5s-A2s")) == {"A5s", "A4s", "A3s", "A2s"}
    assert set(parse_range("76s-54s")) == {"76s", "65s", "54s"}
    # a própria constante do produto usa span — tem que parsear sem erro
    for spec in THREEBET_RANGES.values():
        assert parse_range(spec)


# --------------------------- camada LLM / tools ---------------------------
def test_evaluate_line_has_collect_charts_param():
    import inspect

    from app.agent.llm import evaluate_line

    assert "collect_charts" in inspect.signature(evaluate_line).parameters


def test_send_range_chart_validates_args():
    from app.agent.llm import _dispatch

    assert "error" in _dispatch("send_range_chart", {})
    assert "error" in _dispatch("send_range_chart", {"range_notation": "banana, AA-xx"})
    ok = _dispatch("send_range_chart", {"range_notation": "22+, A2s+"})
    assert ok.get("ok")
    # stack como string "10bb" é coagido
    r = _dispatch("send_range_chart", {"role": "sb", "stack_bb": "10bb", "mode": "freq"})
    assert r.get("ok") or "indisponível" in r.get("error", "")


def test_dispatch_coerces_model_sloppiness():
    from app.agent.llm import _dispatch

    # cartas como string única + '10h' -> Th
    r = _dispatch("equity", {"hero_cards": "10h, Ad", "num_opponents": "1"})
    assert isinstance(r, float) and 0.5 < r < 0.8
    # pot_odds sem aposta: erro claro em vez de divisão sem sentido
    assert "error" in _dispatch("pot_odds", {"pot": 100, "to_call": 0})
    assert "error" in _dispatch("spr", {"effective_stack": 100, "pot": 0})


def test_solve_river_rejects_short_board():
    from app.analysis.river_solver import solve_river

    with pytest.raises(ValueError):
        solve_river(["Ah", "7c", "2d"], "AA", "QQ", pot=100, stack=100)


def test_norm_card_unicode():
    from app.agent.llm import _norm_card

    assert _norm_card("A♥") == "Ah"
    assert _norm_card("10♠") == "Ts"


def test_vision_snapshot_no_fabricated_streets():
    from app.agent.llm import _snapshot_to_canonical

    hand = _snapshot_to_canonical({
        "hero_cards": ["Ah", "Kd"],
        "board": {"flop": ["2h", "7c", "9d"]},
        "actions": {"flop": [{"actor": "Hero", "action": "bet", "amount": 10}]},
    })
    names = [s.name.value for s in hand.streets]
    assert "turn" not in names and "river" not in names


# --------------------------- quota fail-closed ---------------------------
def test_quota_fails_closed_when_db_errors():
    from app.quota import check_quota

    class _Boom:
        enabled = True

        @property
        def client(self):
            raise RuntimeError("db down")

    q = check_quota(1, {"id": "u1", "plan": "free"}, _Boom())
    assert not q.allowed and q.degraded

    # banco ligado mas usuário não veio: também degraded (não cai na memória)
    q2 = check_quota(1, None, _Boom())
    assert not q2.allowed and q2.degraded


# ------------------------------- CSV tracker -------------------------------
def test_csv_network_column_and_losses():
    from app.parsers.csv_tracker import parse_tracker_csv

    csv_text = (
        "Hand ID,Network,Hole Cards,Net Won\n"
        "1,GGNetwork,As Kd,12.50\n"
        "2,GGNetwork,7h 2c,-8.25\n"
    )
    hands = parse_tracker_csv(csv_text)
    assert hands[0].net_won == 12.50 and hands[0].collected["Hero"] == 12.50
    assert hands[1].net_won == -8.25 and not hands[1].collected
    assert hands[0].site == "GGNetwork"


def test_csv_loss_reaches_net_bb():
    from app.agent.analyzer import analyze_hand
    from app.parsers.csv_tracker import parse_tracker_csv

    hands = parse_tracker_csv("Hand ID,Hole Cards,Net Won\n1,As Kd,-5.0\n")
    assert analyze_hand(hands[0])["net_chips"] == -5.0


# --------------------------- paste: emenda segura ---------------------------
def test_join_paste_survives_any_cut_position():
    from app.bot.handlers import _join_paste

    # varre uma janela em torno do pior caso ('Hero: raises 1,000') + amostra
    # esparsa do arquivo inteiro: a emenda tem que reconstituir o texto exato
    hot = GG_PASTE.index("609c9948: raises 1,000")
    cuts = list(range(max(1, hot - 60), hot + 90)) + list(range(1, len(GG_PASTE), 97))
    bad = [i for i in cuts if _join_paste(GG_PASTE[:i], GG_PASTE[i:]) != GG_PASTE]
    assert not bad, f"emenda corrompeu nos cortes {bad[:5]}"


def test_question_with_action_shape_not_continuation():
    from app.bot.handlers import _hh_fragment

    assert not _hh_fragment("meu oponente: calls qualquer aposta no flop, como ajusto?")
    assert _hh_fragment("Seat 3: Hero (button) won (58,200)")  # rabo genuíno


# --------------------------- poker-text heuristic ---------------------------
def test_poker_text_heuristic_pt_false_positives():
    from app.ingestion.pipeline import _looks_like_poker_text

    assert not _looks_like_poker_text("As soon as possible, please send the invoice as")
    assert not _looks_like_poker_text("Ola! Manda o resumo da semana as 5h, e depois as 8")
    assert _looks_like_poker_text("I had A♠ K♦ on the button and lost to J♥ J♣")
    assert _looks_like_poker_text("paguei o flop com Kd Qd e ele foldou o river")


# ------------------------------- posições -------------------------------
def test_assign_positions_survives_12_seats():
    from app.parsers.base import assign_positions

    pos = assign_positions(list(range(1, 13)), 1)
    assert len(pos) == 12 and pos[1] == "BTN"
