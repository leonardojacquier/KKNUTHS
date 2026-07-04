"""Parser determinístico de hand history do PokerStars (torneio + cash).

Cobre o formato texto exportado. Cai bem em NLHE 6/9-max. Campos não reconhecidos
são ignorados com segurança — o objetivo é produzir um `CanonicalHand` confiável
para a camada de análise.
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

# "Zoom Hand" e "Home Game Hand" são variantes do mesmo formato
_HEADER = re.compile(
    r"PokerStars (?:Zoom |Home Game )?(?:Hand|Game) #(?P<hid>\d+):\s+"
    r"(?P<rest>.*?)\s+-\s+(?P<date>\d{4}/\d{2}/\d{2} \d{1,2}:\d{2}:\d{2})"
)
# valores podem vir com separador de milhar ("1,000") e, em cash real,
# prefixo de moeda ("$0.25", "€1.50") — GG/PS compartilham o corpo
_NUM = r"[\$€£]?[\d][\d,]*(?:\.\d+)?"
_TOURNEY = re.compile(
    r"Tournament #(?P<tid>\d+),\s+(?P<buyin>[^ ]+)\s+(?P<cur>[A-Z]{3})?.*?"
    rf"Level\s+(?P<level>[^(]+)\((?P<sb>{_NUM})/(?P<bb>{_NUM})"
    rf"(?:\((?P<ante>{_NUM})\))?\)"
)
_CASH = re.compile(rf"\((?P<sb>{_NUM})/(?P<bb>{_NUM})\s+(?P<cur>[A-Z]{{3}})?\)")
_TABLE = re.compile(
    r"Table '(?P<name>[^']+)'\s+(?P<max>\d+)-max\s+Seat #(?P<btn>\d+) is the button"
)
_SEAT = re.compile(rf"Seat (?P<seat>\d+): (?P<name>.+?) \((?P<stack>{_NUM}) in chips\)")
_POST_SB = re.compile(rf"^(?P<name>.+?): posts small blind (?P<amt>{_NUM})")
_POST_BB = re.compile(rf"^(?P<name>.+?): posts big blind (?P<amt>{_NUM})")
_POST_ANTE = re.compile(rf"^(?P<name>.+?): posts (?:the )?ante (?P<amt>{_NUM})")
# jogador voltando à mesa: "posts small & big blinds 300"
_POST_BOTH = re.compile(rf"^(?P<name>.+?): posts small & big blinds? (?P<amt>{_NUM})")
_DEALT = re.compile(r"^Dealt to (?P<name>.+?) \[(?P<cards>[^\]]+)\]")
_ACTION = re.compile(
    r"^(?P<name>.+?): (?P<verb>folds|checks|calls|bets|raises)"
    rf"(?:\s+(?P<a1>{_NUM})(?:\s+to\s+(?P<a2>{_NUM}))?)?"
    r"(?P<allin>\s+and is all-in)?"
)
_COLLECT = re.compile(rf"^(?P<name>.+?) collected (?P<amt>{_NUM}) from")
_UNCALLED = re.compile(rf"^Uncalled bet \((?P<amt>{_NUM})\) returned to (?P<name>.+)")
# Telegram converte "*** FLOP ***" em "* FLOP *" (asteriscos viram negrito),
# então os marcadores de street aceitam de 1 a 3 asteriscos
_FLOP = re.compile(r"\*{1,3} FLOP \*{1,3} \[(?P<b>[^\]]+)\]")
_TURN = re.compile(r"\*{1,3} TURN \*{1,3} \[[^\]]+\] \[(?P<c>[^\]]+)\]")
_RIVER = re.compile(r"\*{1,3} RIVER \*{1,3} \[[^\]]+\] \[(?P<c>[^\]]+)\]")
_BOARD = re.compile(r"^Board \[(?P<b>[^\]]+)\]")
_TOTAL_POT = re.compile(rf"^Total pot (?P<pot>{_NUM})(?:.*?\|\s+Rake (?P<rake>{_NUM}))?")


def _num(s: str) -> float:
    """'1,400' -> 1400.0 ; '$0.25' -> 0.25."""
    return float(s.lstrip("$€£").replace(",", ""))

_VERB_MAP = {
    "folds": ActionType.FOLD,
    "checks": ActionType.CHECK,
    "calls": ActionType.CALL,
    "bets": ActionType.BET,
    "raises": ActionType.RAISE,
}


class PokerStarsParser:
    site = "PokerStars"

    def matches(self, raw_text: str) -> bool:
        # o header pode não estar na 1ª linha (paste do Telegram costuma começar
        # com o rabo da mão anterior)
        return bool(re.search(
            r"(?m)^PokerStars (?:Zoom |Home Game )?(?:Hand|Game) #", raw_text
        ))

    def parse(self, raw_text: str) -> list[CanonicalHand]:
        hands: list[CanonicalHand] = []
        # cada bloco começa no header (pastes podem perder as linhas em branco);
        # fragmento antes do primeiro header é descartado no _parse_one
        blocks = re.split(
            r"\n(?=PokerStars (?:Zoom |Home Game )?(?:Hand|Game) #)", raw_text.strip()
        )
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            try:
                hands.append(self._parse_one(block))
            except Exception:
                # uma mão malformada não derruba o lote inteiro
                continue
        return hands

    # ------------------------------------------------------------------
    def _parse_one(self, block: str) -> CanonicalHand:
        lines = block.splitlines()
        header = lines[0]
        m = _HEADER.search(header)
        if not m:
            raise ValueError("header não reconhecido")

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
            stakes.currency = tm.group("cur") or "USD"
            stakes.buyin = _parse_buyin(tm.group("buyin"))
        else:
            cm = _CASH.search(header)
            if cm:
                stakes.small_blind = _num(cm.group("sb"))
                stakes.big_blind = _num(cm.group("bb"))
                stakes.currency = cm.group("cur") or "USD"

        game = GameType.PLO if "omaha" in m.group("rest").lower() else GameType.NLHE
        hand = CanonicalHand(
            hand_id=m.group("hid"),
            site=self.site,
            game=game,
            format=fmt,
            stakes=stakes,
            tournament_id=tournament_id,
            played_at=_iso_date(m.group("date")),
            source_format="txt",
            confidence=1.0,
        )
        return parse_body(lines, hand)


def parse_body(lines: list[str], hand: CanonicalHand) -> CanonicalHand:
    """Parseia o corpo de uma mão (mesa, assentos, streets, ações, summary).

    O formato do corpo é o padrão usado por PokerStars/GGPoker e outras salas, então
    é compartilhado entre parsers — cada parser só precisa montar o header e o `hand`.
    """
    # tabela / botão
    for line in lines[1:4]:
        t = _TABLE.search(line)
        if t:
            hand.max_seats = int(t.group("max"))
            hand.button_seat = int(t.group("btn"))
            break

    # assentos
    for line in lines:
        s = _SEAT.match(line)
        if s:
            hand.players.append(
                PlayerSeat(
                    seat=int(s.group("seat")),
                    name=s.group("name"),
                    stack=_num(s.group("stack")),
                )
            )
        elif line.startswith("*") or line.startswith("Dealt"):
            break

    # posições
    if hand.button_seat is not None and hand.players:
        pos = assign_positions([p.seat for p in hand.players], hand.button_seat)
        for p in hand.players:
            p.position = pos.get(p.seat)

    # streets
    streets: dict[StreetName, Street] = {StreetName.PREFLOP: Street(name=StreetName.PREFLOP)}
    order: list[StreetName] = [StreetName.PREFLOP]
    current = StreetName.PREFLOP

    for line in lines:
        line = line.strip()

        if _FLOP.search(line):
            board = _FLOP.search(line).group("b").split()
            streets[StreetName.FLOP] = Street(name=StreetName.FLOP, board=board)
            order.append(StreetName.FLOP)
            current = StreetName.FLOP
            continue
        if _TURN.search(line):
            card = _TURN.search(line).group("c")
            prev = list(streets[StreetName.FLOP].board)
            streets[StreetName.TURN] = Street(name=StreetName.TURN, board=prev + [card])
            order.append(StreetName.TURN)
            current = StreetName.TURN
            continue
        if _RIVER.search(line):
            card = _RIVER.search(line).group("c")
            prev = list(streets[StreetName.TURN].board)
            streets[StreetName.RIVER] = Street(name=StreetName.RIVER, board=prev + [card])
            order.append(StreetName.RIVER)
            current = StreetName.RIVER
            continue

        # hero cards
        d = _DEALT.match(line)
        if d:
            hand.hero = d.group("name")
            hand.hero_cards = d.group("cards").split()
            for p in hand.players:
                p.is_hero = p.name == hand.hero
            continue

        # blinds / antes (sempre na preflop)
        for rx, atype in ((_POST_SB, "sb"), (_POST_BB, "bb"), (_POST_ANTE, "ante"),
                          (_POST_BOTH, "bb")):
            pm = rx.match(line)
            if pm:
                amt = _num(pm.group("amt"))
                streets[StreetName.PREFLOP].actions.append(
                    Action(
                        actor=pm.group("name"),
                        type=ActionType.POST,
                        amount=amt,
                        post_type=atype,
                    )
                )
                if atype == "ante":
                    hand.stakes.ante = amt
                break
        else:
            # ações de jogo
            am = _ACTION.match(line)
            if am:
                verb = am.group("verb")
                a1 = _num(am.group("a1")) if am.group("a1") else 0.0
                a2 = _num(am.group("a2")) if am.group("a2") else 0.0
                streets[current].actions.append(
                    Action(
                        actor=am.group("name"),
                        type=_VERB_MAP[verb],
                        amount=a1,
                        to_amount=a2 or a1,
                        all_in=bool(am.group("allin")),
                    )
                )
                continue

        # summary
        c = _COLLECT.match(line)
        if c:
            hand.collected[c.group("name")] = (
                hand.collected.get(c.group("name"), 0.0) + _num(c.group("amt"))
            )
        u = _UNCALLED.match(line)
        if u:
            name = u.group("name").strip()
            hand.uncalled[name] = hand.uncalled.get(name, 0.0) + _num(u.group("amt"))
        b = _BOARD.match(line)
        if b:
            hand.final_board = b.group("b").split()
        tp = _TOTAL_POT.match(line)
        if tp:
            hand.total_pot = _num(tp.group("pot"))
            if tp.group("rake"):
                hand.rake = _num(tp.group("rake"))

    hand.streets = [streets[name] for name in order]
    if not hand.final_board and StreetName.RIVER in streets:
        hand.final_board = list(streets[StreetName.RIVER].board)

    # header sem blinds (formato exótico): recupera dos posts — a análise em BB
    # depende de big_blind correto. Atenção: o default do modelo é 0 (não None).
    if not hand.stakes.big_blind:
        for a in streets[StreetName.PREFLOP].actions:
            if a.type == ActionType.POST:
                if a.post_type == "sb" and not hand.stakes.small_blind:
                    hand.stakes.small_blind = a.amount
                elif a.post_type == "bb":
                    hand.stakes.big_blind = a.amount
    return hand


def _parse_buyin(token: str) -> float | None:
    """'$20+$2' -> 22.0 ; '$5.00' -> 5.0 ; 'Freeroll' -> 0."""
    if token.lower().startswith("free"):
        return 0.0
    nums = re.findall(r"[\d.]+", token.replace("$", ""))
    if not nums:
        return None
    return round(sum(float(n) for n in nums), 2)


def _iso_date(s: str) -> str:
    """'2023/01/15 20:00:00' -> '2023-01-15T20:00:00'."""
    date, time = s.split(" ")
    return f"{date.replace('/', '-')}T{time}"
