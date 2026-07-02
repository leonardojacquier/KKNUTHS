"""Parser de hand history do Winamax (cash e torneio).

Formato francês, estrutura parecida com PokerStars: streets em '*** FLOP ***',
ações 'X raises 40 to 120'. Valores podem vir com '€' (cash) ou puros (torneio).
"""
from __future__ import annotations

import re

from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    GameType,
    HandFormat,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)
from app.parsers.base import assign_positions

_HEADER = re.compile(
    r"Winamax Poker - (?P<kind>CashGame|Tournament \"(?P<tname>[^\"]*)\".*?)"
    r"\s*-\s*HandId: #(?P<hid>[\d-]+)\s*-\s*Holdem no limit\s*"
    r"\((?:(?P<ante>[\d.,]+)€?/)?(?P<sb>[\d.,]+)€?/(?P<bb>[\d.,]+)€?\)"
    r"\s*-\s*(?P<date>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
)
_BUYIN = re.compile(r"buyIn: (?P<b1>[\d.,]+)€?(?:\s*\+\s*(?P<b2>[\d.,]+)€?)?")
_TABLE = re.compile(r"Table: '(?P<name>[^']+)' (?P<max>\d+)-max .*Seat #(?P<btn>\d+) is the button")
_SEAT = re.compile(r"^Seat (?P<seat>\d+): (?P<name>.+?) \((?P<stack>[\d.,]+)€?\)")
_POST = re.compile(r"^(?P<name>.+?) posts (?P<what>small blind|big blind|ante) (?P<amt>[\d.,]+)€?")
_DEALT = re.compile(r"^Dealt to (?P<name>.+?) \[(?P<cards>[^\]]+)\]")
_ACTION = re.compile(
    r"^(?P<name>.+?) (?P<verb>folds|checks|calls|bets|raises)"
    r"(?:\s+(?P<a1>[\d.,]+)€?(?:\s+to\s+(?P<a2>[\d.,]+)€?)?)?"
    r"(?P<allin>\s+and is all-in)?"
)
_STREET = re.compile(r"\*\*\* (?P<name>PRE-FLOP|FLOP|TURN|RIVER) \*\*\*(?: \[(?P<cards>[^\]]+)\])?(?: \[(?P<extra>[^\]]+)\])?")
_COLLECT = re.compile(r"^(?P<name>.+?) collected (?P<amt>[\d.,]+)€? from")
_BOARD = re.compile(r"^Board: \[(?P<b>[^\]]+)\]")
_POT = re.compile(r"^Total pot (?P<pot>[\d.,]+)€?")

_VERBS = {
    "folds": ActionType.FOLD, "checks": ActionType.CHECK, "calls": ActionType.CALL,
    "bets": ActionType.BET, "raises": ActionType.RAISE,
}
_POSTS = {"small blind": "sb", "big blind": "bb", "ante": "ante"}
_STREET_MAP = {
    "PRE-FLOP": StreetName.PREFLOP, "FLOP": StreetName.FLOP,
    "TURN": StreetName.TURN, "RIVER": StreetName.RIVER,
}


def _num(s: str | None) -> float:
    return float(s.replace(",", ".")) if s else 0.0


def _cards(s: str) -> list[str]:
    return [c.strip() for c in re.split(r"[,\s]+", s.strip()) if c.strip()]


class WinamaxParser:
    site = "Winamax"

    def matches(self, raw_text: str) -> bool:
        return raw_text.lstrip().startswith("Winamax Poker")

    def parse(self, raw_text: str) -> list[CanonicalHand]:
        hands = []
        for block in re.split(r"\n\s*\n(?=Winamax Poker)", raw_text.strip()):
            block = block.strip()
            if not block:
                continue
            try:
                hands.append(self._parse_one(block))
            except Exception:
                continue
        return hands

    def _parse_one(self, block: str) -> CanonicalHand:
        lines = block.splitlines()
        m = _HEADER.search(lines[0])
        if not m:
            raise ValueError("header Winamax não reconhecido")

        is_tourney = m.group("kind").startswith("Tournament")
        stakes = Stakes(
            small_blind=_num(m.group("sb")),
            big_blind=_num(m.group("bb")),
            ante=_num(m.group("ante")),
            currency="EUR",
        )
        if is_tourney:
            bm = _BUYIN.search(lines[0])
            if bm:
                stakes.buyin = round(_num(bm.group("b1")) + _num(bm.group("b2")), 2)

        hand = CanonicalHand(
            hand_id=m.group("hid"),
            site=self.site,
            game=GameType.NLHE,
            format=HandFormat.TOURNAMENT if is_tourney else HandFormat.CASH,
            stakes=stakes,
            played_at=m.group("date").replace("/", "-", 2).replace(" ", "T", 1),
            source_format="txt",
            confidence=1.0,
        )

        streets: dict[StreetName, Street] = {StreetName.PREFLOP: Street(name=StreetName.PREFLOP)}
        order = [StreetName.PREFLOP]
        current = StreetName.PREFLOP
        prev_board: list[str] = []

        for line in lines:
            line = line.strip()
            t = _TABLE.search(line)
            if t:
                hand.max_seats = int(t.group("max"))
                hand.button_seat = int(t.group("btn"))
                continue
            s = _SEAT.match(line)
            if s:
                hand.players.append(PlayerSeat(
                    seat=int(s.group("seat")), name=s.group("name"),
                    stack=_num(s.group("stack")),
                ))
                continue
            st = _STREET.search(line)
            if st:
                name = _STREET_MAP[st.group("name")]
                cards = _cards(st.group("cards")) if st.group("cards") else []
                extra = _cards(st.group("extra")) if st.group("extra") else []
                if name == StreetName.FLOP:
                    board = cards
                else:
                    board = prev_board + (extra or cards)
                if name != StreetName.PREFLOP:
                    streets[name] = Street(name=name, board=board)
                    order.append(name)
                    prev_board = board
                current = name
                continue
            d = _DEALT.match(line)
            if d:
                hand.hero = d.group("name")
                hand.hero_cards = _cards(d.group("cards"))
                continue
            p = _POST.match(line)
            if p:
                amt = _num(p.group("amt"))
                streets[StreetName.PREFLOP].actions.append(Action(
                    actor=p.group("name"), type=ActionType.POST,
                    amount=amt, post_type=_POSTS[p.group("what")],
                ))
                if p.group("what") == "ante":
                    hand.stakes.ante = amt
                continue
            a = _ACTION.match(line)
            if a and a.group("verb"):
                a1, a2 = _num(a.group("a1")), _num(a.group("a2"))
                streets[current].actions.append(Action(
                    actor=a.group("name"), type=_VERBS[a.group("verb")],
                    amount=a1, to_amount=a2 or a1, all_in=bool(a.group("allin")),
                ))
                continue
            c = _COLLECT.match(line)
            if c:
                hand.collected[c.group("name")] = (
                    hand.collected.get(c.group("name"), 0.0) + _num(c.group("amt"))
                )
            b = _BOARD.match(line)
            if b:
                hand.final_board = _cards(b.group("b"))
            pt = _POT.match(line)
            if pt:
                hand.total_pot = _num(pt.group("pot"))

        if hand.button_seat is not None and hand.players:
            pos = assign_positions([p.seat for p in hand.players], hand.button_seat)
            for pl in hand.players:
                pl.position = pos.get(pl.seat)
        for pl in hand.players:
            pl.is_hero = pl.name == hand.hero

        hand.streets = [streets[n] for n in order if n in streets]
        if not hand.final_board and StreetName.RIVER in streets:
            hand.final_board = list(streets[StreetName.RIVER].board)
        return hand
