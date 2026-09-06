"""Regressão do caso real (beta): torneio GG colado no chat do Telegram.

O paste real chega mutilado de três formas — e o parser precisa aguentar todas:
1. valores com separador de milhar ("raises 1,000 to 1,400", "(8,200 in chips)");
2. header de nível com ante: "Level8(200/400(50))" — antes caía como CASH;
3. Telegram converte "*** FLOP ***" em "* FLOP *" (asteriscos viram negrito) e o
   texto começa com o rabo da mão anterior (fragmento antes do primeiro header).
"""
from pathlib import Path

from app.models.canonical import ActionType, HandFormat
from app.parsers import detect_site, parse_text

PASTE = (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()


def test_detects_gg_despite_leading_fragment():
    # o texto NÃO começa com "Poker Hand #" — começa com o resumo da mão anterior
    assert not PASTE.startswith("Poker Hand #")
    assert detect_site(PASTE) == "GGPoker"


def test_parses_all_four_hands_as_tournament():
    hands = parse_text(PASTE)
    assert len(hands) == 4
    for h in hands:
        assert h.format == HandFormat.TOURNAMENT
        assert h.tournament_id == "295746366"
        assert h.stakes.small_blind == 200 and h.stakes.big_blind == 400
        assert h.stakes.ante == 50
        assert h.stakes.buyin == 10.0
        assert len(h.players) == 8


def test_thousand_separators_in_amounts():
    h = parse_text(PASTE)[0]  # TM6146070388 — a mão do A3o no BB
    hero = next(p for p in h.players if p.is_hero)
    assert hero.stack == 10850            # "(10,850 in chips)"
    assert h.total_pot == 17600           # "Total pot 17,600 | Rake 0 | ..."
    assert h.collected["Hero"] == 17600   # "Hero collected 17,600 from pot"
    pre = h.streets[0]
    raise_a = next(a for a in pre.actions if a.type == ActionType.RAISE)
    assert raise_a.amount == 1000 and raise_a.to_amount == 1400


def test_streets_survive_telegram_asterisks():
    h = parse_text(PASTE)[0]
    assert [s.name.value for s in h.streets] == ["preflop", "flop", "turn", "river"]
    assert h.final_board == ["Jh", "6d", "Ac", "8d", "2d"]


def test_positions_and_hero():
    hands = parse_text(PASTE)
    by_id = {h.hand_id: h for h in hands}
    hero_pos = {
        hid: next(p.position for p in h.players if p.is_hero)
        for hid, h in by_id.items()
    }
    assert hero_pos["TM6146070388"] == "BB"      # defendeu A3o vs open do SB
    assert by_id["TM6146070388"].hero_cards == ["3c", "Ad"]


def test_all_in_with_comma_amount():
    h = next(x for x in parse_text(PASTE) if x.hand_id == "TM6146070228")
    river = h.streets[-1]
    jam = next(a for a in river.actions if a.type == ActionType.BET)
    assert jam.amount == 2144 and jam.all_in


def test_paste_reassembly_stash_take():
    from app.bot.processing import stash_paste, take_paste

    stash_paste(999001, "parte 1")
    assert take_paste(999001) == ("parte 1", 1)
    assert take_paste(999001) == ("", 0)  # consumido

    # expirado -> descartado
    import app.bot.processing as proc

    stash_paste(999001, "velho", parts=3)
    text, ts, parts = proc.PENDING_PASTE[999001]
    proc.PENDING_PASTE[999001] = (text, ts - proc._PASTE_TTL - 1, parts)
    assert take_paste(999001) == ("", 0)


def test_split_paste_parses_when_recombined():
    # simula o corte do Telegram no meio de "Seat 7: c2b002e0 (28,951 in / chips)"
    cut = PASTE.index("chips)\nSeat 8: 7adfdc5b (12,784")
    part1, part2 = PASTE[:cut], PASTE[cut:]
    assert detect_site(part1) == "GGPoker"
    assert detect_site(part2) == "GGPoker"  # fragmento no início, headers depois
    assert len(parse_text(part1 + part2)) == 4


# ------------- achados da revisão adversarial (regressões) -------------
def test_blinds_recovered_from_posts_when_header_incomplete():
    # header de torneio SEM nível entre parênteses: o regex completo falha, o
    # fallback marca torneio e o corpo recupera os blinds dos posts (não 0)
    from app.models.canonical import HandFormat

    exotic = PASTE.split("\n\n")[1].replace(
        "Level8(200/400(50))", "Level8 200/400"
    )
    (h,) = parse_text(exotic)
    assert h.format == HandFormat.TOURNAMENT
    assert h.stakes.small_blind == 200 and h.stakes.big_blind == 400


def test_question_is_not_a_paste_continuation():
    from app.bot.handlers import _hh_fragment

    # perguntas ao coach falam de poker mas NÃO têm linha com formato de HH
    assert not _hh_fragment("devo dar fold no river nesse pot?")
    assert not _hh_fragment("should I fold or raise the turn here?")
    assert not _hh_fragment("e se o vilão der all-in no river?")
    # fragmentos reais de HH têm
    assert _hh_fragment("Seat 3: Hero (button) won (58,200)")
    assert _hh_fragment("609c9948: raises 1,000 to 1,400\nHero: calls 1,000")
    assert _hh_fragment("chips)\nSeat 8: 7adfdc5b (12,784 in chips)\nHero: folds")


def test_join_paste_reconstructs_midline_and_midnumber_cut():
    from app.bot.handlers import _join_paste

    # corte no meio do número: "raises 1," + "000 to 1,400"
    cut = PASTE.index("000 to 1,400")
    joined = _join_paste(PASTE[:cut], PASTE[cut:])
    assert joined == PASTE
    h = next(x for x in parse_text(joined) if x.hand_id == "TM6146070388")
    raise_a = next(a for s in h.streets for a in s.actions if a.type.value == "raise")
    assert raise_a.amount == 1000 and raise_a.to_amount == 1400

    # corte exatamente numa quebra de linha: a nova parte começa com linha de
    # HH válida -> emenda com \n normal
    cut2 = PASTE.index("Hero: calls 1,000")
    joined2 = _join_paste(PASTE[:cut2].rstrip("\n"), PASTE[cut2:])
    assert len(parse_text(joined2)) == 4


def test_reprocess_picks_most_complete_version():
    import importlib.util
    from pathlib import Path as P

    spec = importlib.util.spec_from_file_location(
        "reprocess_uploads",
        P(__file__).parent.parent / "scripts" / "reprocess_uploads.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    complete = parse_text(PASTE)
    # fragmento: a última mão cortada no meio (sem ações/summary)
    truncated_txt = PASTE[: PASTE.index("bb50544: folds\n609c9948: folds")]
    truncated = parse_text(truncated_txt)
    assert any(h.hand_id == "TM6146070194" for h in truncated)

    # fragmento visto PRIMEIRO não pode vencer a versão completa
    best = mod.pick_best(truncated + complete)
    winner = best["TM6146070194"]
    assert sum(len(s.actions) for s in winner.streets) > 0
    assert winner.collected.get("Hero") == 1400
