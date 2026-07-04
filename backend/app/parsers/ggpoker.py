"""Parser determinístico de hand history do GGPoker.

O corpo (assentos, streets, ações, summary) segue o formato padrão e é compartilhado
com `pokerstars.parse_body`. Aqui tratamos apenas as diferenças de cabeçalho do GG:
prefixo "Poker Hand #", id alfanumérico, nome de torneio livre antes do buy-in e
nível no formato "Level10(150/300)".
"""
from __future__ import annotations

import re

from app.models.canonical import CanonicalHand, GameType, HandFormat, Stakes
from app.parsers.pokerstars import _NUM, _iso_date, _num, _parse_buyin, parse_body

_HEADER = re.compile(
    r"Poker Hand #(?P<hid>[A-Za-z0-9-]+):\s+"
    r"(?P<rest>.*?)\s+-\s+(?P<date>\d{4}/\d{2}/\d{2} \d{1,2}:\d{2}:\d{2})"
)
# nível pode trazer o ante: "Level8(200/400(50))"
_TOURNEY = re.compile(
    r"Tournament #(?P<tid>\d+),\s+(?P<name>.*?)"
    rf"Hold'em No Limit\s+-\s+Level\s*(?P<level>[^(]*)\((?P<sb>{_NUM})/(?P<bb>{_NUM})"
    rf"(?:\((?P<ante>{_NUM})\))?\)"
)
_CASH = re.compile(
    rf"Hold'em No Limit\s+\((?:[^)]*?[\$€£])?(?P<sb>{_NUM})/[\$€£]?(?P<bb>{_NUM})\)"
)


class GGPokerParser:
    site = "GGPoker"

    def matches(self, raw_text: str) -> bool:
        # "Poker Hand #" (não "PokerStars Hand #") em qualquer linha — paste do
        # Telegram costuma começar com o rabo da mão anterior
        return bool(re.search(r"(?m)^Poker Hand #", raw_text))

    def parse(self, raw_text: str) -> list[CanonicalHand]:
        hands: list[CanonicalHand] = []
        # cada bloco começa no header; fragmento antes do primeiro é descartado
        blocks = re.split(r"\n(?=Poker Hand #)", raw_text.strip())
        for block in blocks:
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
        header = lines[0]
        m = _HEADER.search(header)
        if not m:
            raise ValueError("header GG não reconhecido")

        stakes = Stakes()
        fmt = HandFormat.CASH
        tournament_id = None

        tm = _TOURNEY.search(header)
        if tm:
            fmt = HandFormat.TOURNAMENT
            tournament_id = tm.group("tid")
            stakes.level = tm.group("level").strip()
            stakes.small_blind = _num(tm.group("sb"))
            stakes.big_blind = _num(tm.group("bb"))
            if tm.group("ante"):
                stakes.ante = _num(tm.group("ante"))
            stakes.buyin = _parse_buyin(tm.group("name"))
        elif "Tournament #" in header:
            # header de torneio que o regex não pegou por completo: não deixar a
            # mão cair como cash (blinds ficam 0 e o corpo os recupera dos posts)
            fmt = HandFormat.TOURNAMENT
            tid = re.search(r"Tournament #(\d+)", header)
            tournament_id = tid.group(1) if tid else None
        else:
            cm = _CASH.search(header)
            if cm:
                stakes.small_blind = _num(cm.group("sb"))
                stakes.big_blind = _num(cm.group("bb"))

        hand = CanonicalHand(
            hand_id=m.group("hid"),
            site=self.site,
            game=GameType.NLHE,
            format=fmt,
            stakes=stakes,
            tournament_id=tournament_id,
            played_at=_iso_date(m.group("date")),
            source_format="txt",
            confidence=1.0,
        )
        return parse_body(lines, hand)
