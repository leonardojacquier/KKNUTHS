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
    assert take_paste(999001) == "parte 1"
    assert take_paste(999001) == ""  # consumido

    # expirado -> descartado
    import app.bot.processing as proc

    stash_paste(999001, "velho")
    text, ts = proc.PENDING_PASTE[999001]
    proc.PENDING_PASTE[999001] = (text, ts - proc._PASTE_TTL - 1)
    assert take_paste(999001) == ""


def test_split_paste_parses_when_recombined():
    # simula o corte do Telegram no meio de "Seat 7: c2b002e0 (28,951 in / chips)"
    cut = PASTE.index("chips)\nSeat 8: 7adfdc5b (12,784")
    part1, part2 = PASTE[:cut], PASTE[cut:]
    assert detect_site(part1) == "GGPoker"
    assert detect_site(part2) == "GGPoker"  # fragmento no início, headers depois
    assert len(parse_text(part1 + part2)) == 4
