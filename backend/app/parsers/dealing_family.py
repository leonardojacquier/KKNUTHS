"""Parsers da família "Dealing": PartyPoker e 888poker.

Os dois compartilham a mesma linhagem de formato: streets como
'** Dealing Flop ** [ Ah, 7c, 2d ]', valores entre colchetes ('[$0.30 USD]',
'[$0.30]' ou '[300]' em torneio) e ações 'Player raises [$0.30 USD]'.
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

_SEAT = re.compile(r"^Seat (?P<seat>\d+): (?P<name>.+?) \( ?\$?(?P<stack>[\d.,]+)(?: USD)? ?\)")
_BUTTON = re.compile(r"^Seat (?P<btn>\d+) is the button")
_PLAYERS = re.compile(r"Total number of players : (?P<n>\d+)")
_POST = re.compile(
    r"^(?P<name>.+?) posts (?P<what>small blind|big blind|ante)"
    r"(?: \[?\$?(?P<amt>[\d.,]+)(?: USD)?\]?)?"
)
_DEALT = re.compile(r"^Dealt to (?P<name>.+?) \[ ?(?P<cards>[^\]]+?) ?\]")
_ACTION = re.compile(
    r"^(?P<name>.+?) (?P<verb>folds|checks|calls|bets|raises|is all-In|is all-in)"
    r"(?: \[?\$?(?P<amt>[\d.,]+)(?: USD)?\]?)?"
)
_STREET = re.compile(
    r"\*\* Dealing (?P<name>Flop|Turn|River) \*\*(?: \[ ?(?P<cards>[^\]]+?) ?\])?",
    re.IGNORECASE,
)
_WIN = re.compile(
    r"^(?P<name>.+?) (?:wins|collected) \[? ?\$?(?P<amt>[\d.,]+)(?: USD)? ?\]?"
)
_BLINDS_CASH = re.compile(r"\$?(?P<sb>[\d.,]+)/\$?(?P<bb>[\d.,]+)")
_BLINDS_TRNY = re.compile(r"Blinds\s*\( ?(?P<sb>[\d.,]+)/(?P<bb>[\d.,]+) ?\)", re.IGNORECASE)

_VERBS = {
    "folds": ActionType.FOLD, "checks": ActionType.CHECK, "calls": ActionType.CALL,
    "bets": ActionType.BET, "raises": ActionType.RAISE,
}
_POSTS = {"small blind": "sb", "big blind": "bb", "ante": "ante"}


def _num(s: str | None) -> float:
    return float(s.replace(",", "")) if s else 0.0


def _cards(s: str) -> list[str]:
    return [c.strip() for c in re.split(r"[,\s]+", s.strip()) if c.strip()]


class _DealingBase:
    site = "?"
    _split_re: re.Pattern
    _id_re: re.Pattern

    def parse(self, raw_text: str) -> list[CanonicalHand]:
        hands = []
        for block in self._split_re.split(raw_text.strip()):
            block = block.strip()
            if not block or not self._id_re.search(block):
                continue
            try:
                hands.append(self._parse_one(block))
            except Exception:
                continue
        return hands

    def _parse_one(self, block: str) -> CanonicalHand:
        lines = block.splitlines()
        idm = self._id_re.search(block)
        head = "\n".join(lines[:6])

        is_tourney = bool(re.search(r"Trny[:\s]|Tournament", head, re.IGNORECASE))
        stakes = Stakes(currency="USD")
        bm = _BLINDS_TRNY.search(head) or _BLINDS_CASH.search(head)
        if bm:
            stakes.small_blind = _num(bm.group("sb"))
            stakes.big_blind = _num(bm.group("bb"))

        hand = CanonicalHand(
            hand_id=idm.group("hid"),
            site=self.site,
            game=GameType.NLHE,
            format=HandFormat.TOURNAMENT if is_tourney else HandFormat.CASH,
            stakes=stakes,
            source_format="txt",
            confidence=1.0,
        )

        streets: dict[StreetName, Street] = {StreetName.PREFLOP: Street(name=StreetName.PREFLOP)}
        order = [StreetName.PREFLOP]
        current = StreetName.PREFLOP
        prev_board: list[str] = []

        for line in lines:
            line = line.strip().rstrip(".")
            b = _BUTTON.match(line)
            if b:
                hand.button_seat = int(b.group("btn"))
                continue
            n = _PLAYERS.search(line)
            if n:
                hand.max_seats = max(hand.max_seats, int(n.group("n")))
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
                name = {"flop": StreetName.FLOP, "turn": StreetName.TURN,
                        "river": StreetName.RIVER}[st.group("name").lower()]
                cards = _cards(st.group("cards")) if st.group("cards") else []
                board = cards if name == StreetName.FLOP else prev_board + cards
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
                if p.group("what") == "ante" and amt:
                    hand.stakes.ante = amt
                continue
            a = _ACTION.match(line)
            if a and a.group("verb"):
                verb = a.group("verb").lower()
                amt = _num(a.group("amt"))
                if verb.startswith("is all"):
                    streets[current].actions.append(Action(
                        actor=a.group("name"), type=ActionType.RAISE,
                        amount=amt, to_amount=amt, all_in=True,
                    ))
                else:
                    streets[current].actions.append(Action(
                        actor=a.group("name"), type=_VERBS[verb],
                        amount=amt, to_amount=amt, all_in=False,
                    ))
                continue
            w = _WIN.match(line)
            if w:
                hand.collected[w.group("name")] = (
                    hand.collected.get(w.group("name"), 0.0) + _num(w.group("amt"))
                )

        if hand.button_seat is not None and hand.players:
            pos = assign_positions([p.seat for p in hand.players], hand.button_seat)
            for pl in hand.players:
                pl.position = pos.get(pl.seat)
        for pl in hand.players:
            pl.is_hero = pl.name == hand.hero

        hand.streets = [streets[n] for n in order if n in streets]
        if StreetName.RIVER in streets:
            hand.final_board = list(streets[StreetName.RIVER].board)
        elif order and order[-1] in streets:
            hand.final_board = list(streets[order[-1]].board)
        return hand


class PartyPokerParser(_DealingBase):
    site = "PartyPoker"
    _split_re = re.compile(r"\n\s*\n(?=\*{5} Hand History)")
    _id_re = re.compile(r"\*{5} Hand History for Game (?P<hid>\d+)")

    def matches(self, raw_text: str) -> bool:
        head = raw_text.lstrip()[:300]
        return "Hand History for Game" in head and "888poker" not in head


class Poker888Parser(_DealingBase):
    site = "888poker"
    _split_re = re.compile(r"\n\s*\n(?=#Game No|\*{5} 888poker)")
    _id_re = re.compile(r"(?:#Game No\s*:\s*|888poker Hand History for Game )(?P<hid>\d+)")

    def matches(self, raw_text: str) -> bool:
        head = raw_text.lstrip()[:300]
        return "888poker" in head or head.startswith("#Game No")
