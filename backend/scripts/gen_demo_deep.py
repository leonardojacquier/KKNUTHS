"""Gera as mãos DEEP do torneio-demo (níveis iniciais, ~100bb, multi-street).

O demo original era push/fold-heavy (145/150 mãos com 1 decisão) — o treino
virava só "shove ou fold". Estas mãos acontecem nos níveis iniciais do MESMO
torneio (timestamps ANTERIORES às mãos existentes) e trazem decisões de
flop/turn/river: c-bet, enfrentar 3-bet, check-raise, bluff-catch de river.

Uso: PYTHONPATH=. python scripts/gen_demo_deep.py   (appenda no demo e valida)
"""
from __future__ import annotations

from pathlib import Path

VILL = ["a1b2c3d4", "e5f6a7b8", "c9d0e1f2", "b3c4d5e6", "f7a8b9c0"]
DEMO = Path(__file__).resolve().parent.parent / "tests" / "sample_hands" / \
    "demo_kknuths_tournament.txt"


def fmt(n: float) -> str:
    return f"{int(round(n)):,}"


class Hand:
    """Constrói uma mão no formato do demo com a matemática do pote fechada."""

    def __init__(self, hid, time, btn_seat, hero_cards, stacks=None):
        self.names = ["Hero"] + VILL          # seat i = names[i-1]
        stacks = stacks or [10000, 9800, 10200, 9900, 10100, 9700]
        self.lines = [
            f"Poker Hand #TM70000001{hid}: Tournament #300777888, KKN Demo $22 "
            f"Hold'em No Limit - Level2(50/100(10)) - 2026/07/08 {time}",
            f"Table '3' 6-max Seat #{btn_seat} is the button",
        ]
        for i, (name, st) in enumerate(zip(self.names, stacks), 1):
            self.lines.append(f"Seat {i}: {name} ({fmt(st)} in chips)")
        self.pot = 0
        self.contrib: dict[str, int] = {}
        for name in self.names:
            self.lines.append(f"{name}: posts the ante 10")
            self.pot += 10
        seat = lambda s: self.names[(s - 1) % 6]
        self.sb_name, self.bb_name = seat(btn_seat + 1), seat(btn_seat + 2)
        self.lines.append(f"{self.sb_name}: posts small blind 50")
        self.lines.append(f"{self.bb_name}: posts big blind 100")
        self.contrib = {self.sb_name: 50, self.bb_name: 100}
        self.pot += 150
        self.lines.append("* HOLE CARDS *")
        self.lines.append(f"Dealt to Hero [{hero_cards}]")
        for v in VILL:
            self.lines.append(f"Dealt to {v}")

    def street(self, name, cards):
        self.contrib = {}
        self.lines.append(f"* {name} * {cards}")

    def fold(self, who):
        self.lines.append(f"{who}: folds")

    def check(self, who):
        self.lines.append(f"{who}: checks")

    def bet(self, who, amt):
        self.lines.append(f"{who}: bets {fmt(amt)}")
        self.contrib[who] = amt
        self.pot += amt

    def call(self, who):
        due = max(self.contrib.values()) - self.contrib.get(who, 0)
        self.lines.append(f"{who}: calls {fmt(due)}")
        self.contrib[who] = self.contrib.get(who, 0) + due
        self.pot += due

    def raise_to(self, who, to):
        add = to - self.contrib.get(who, 0)
        self.lines.append(
            f"{who}: raises {fmt(to - max(self.contrib.values()))} to {fmt(to)}")
        self.contrib[who] = to
        self.pot += add

    def win_uncalled(self, who):
        others = [c for n, c in self.contrib.items() if n != who]
        extra = self.contrib.get(who, 0) - (max(others) if others else 0)
        if extra > 0:
            self.lines.append(f"Uncalled bet ({fmt(extra)}) returned to {who}")
            self.pot -= extra
        self.lines.append(f"{who} collected {fmt(self.pot)} from pot")
        self.lines.append("* SUMMARY *")
        return "\n".join(self.lines) + "\n"

    def showdown(self, winner):
        self.lines.append(f"{winner} collected {fmt(self.pot)} from pot")
        self.lines.append("* SUMMARY *")
        return "\n".join(self.lines) + "\n"


def build_all() -> list[str]:
    out = []
    A, B, C, D, E = VILL

    # 150 — Hero BTN AhKh: open, c-bet, barrel, value no river (todos pagam,
    # river fold do vilão). Linha de valor clássica.
    h = Hand("50", "19:20:00", 1, "Ah Kh")     # btn=1: SB=A, BB=B; UTG=C
    h.fold(C); h.fold(D); h.fold(E)
    h.raise_to("Hero", 230)
    h.fold(A); h.call(B)
    h.street("FLOP", "[Kd 7s 2c]")
    h.check(B); h.bet("Hero", 300); h.call(B)
    h.street("TURN", "[Kd 7s 2c] [5h]")
    h.check(B); h.bet("Hero", 750); h.call(B)
    h.street("RIVER", "[Kd 7s 2c 5h] [Qs]")
    h.check(B); h.bet("Hero", 1500); h.fold(B)
    out.append(h.win_uncalled("Hero"))

    # 151 — Hero BB 8h8c: defesa, check-raise no flop com set no ar, barrels.
    h = Hand("51", "19:23:00", 5, "8h 8c")     # btn=5(D): SB=E, BB=Hero; UTG=A
    h.raise_to(A, 250)
    h.fold(B); h.fold(C); h.fold(D); h.fold(E)
    h.call("Hero")
    h.street("FLOP", "[Js 8d 3h]")
    h.check("Hero"); h.bet(A, 300); h.raise_to("Hero", 900); h.call(A)
    h.street("TURN", "[Js 8d 3h] [2c]")
    h.bet("Hero", 1400); h.call(A)
    h.street("RIVER", "[Js 8d 3h 2c] [Kh]")
    h.bet("Hero", 3000); h.fold(A)
    out.append(h.win_uncalled("Hero"))

    # 152 — Hero CO QsQd: open, pagar 3-bet do BTN, check-fold no flop com A.
    h = Hand("52", "19:26:00", 2, "Qs Qd")     # btn=2(A): SB=B, BB=C; UTG=D
    h.fold(D); h.fold(E)
    h.raise_to("Hero", 220)
    h.raise_to(A, 700)
    h.fold(B); h.fold(C)
    h.call("Hero")
    h.street("FLOP", "[Ad 7c 2s]")
    h.check("Hero"); h.bet(A, 800); h.fold("Hero")
    out.append(h.win_uncalled(A))

    # 153 — Hero SB 6s5s: completa, acerta a sequência no turn, raise-war, showdown.
    h = Hand("53", "19:29:00", 6, "6s 5s")     # btn=6(E): SB=Hero, BB=A; UTG=B
    h.fold(B); h.call(C); h.fold(D); h.fold(E)
    h.call("Hero"); h.check(A)
    h.street("FLOP", "[7d 4c 3h]")
    h.bet("Hero", 250); h.call(A); h.fold(C)
    h.street("TURN", "[7d 4c 3h] [8s]")
    h.bet("Hero", 700); h.raise_to(A, 2100); h.raise_to("Hero", 5600); h.call(A)
    h.street("RIVER", "[7d 4c 3h 8s] [2d]")
    h.bet("Hero", 4000); h.call(A)
    out.append(h.showdown("Hero"))

    # 154 — Hero MP AdQc: open, top pair, duas streets de valor, bluff-catch river.
    h = Hand("54", "19:32:00", 3, "Ad Qc")     # btn=3(B): SB=C, BB=D; UTG=E
    h.fold(E)
    h.raise_to("Hero", 225)
    h.fold(A); h.call(B); h.fold(C); h.fold(D)
    h.street("FLOP", "[Qh 9h 4c]")
    h.bet("Hero", 300); h.call(B)
    h.street("TURN", "[Qh 9h 4c] [2s]")
    h.bet("Hero", 900); h.call(B)
    h.street("RIVER", "[Qh 9h 4c 2s] [9s]")
    h.check("Hero"); h.bet(B, 1800); h.call("Hero")
    out.append(h.showdown("Hero"))

    # 155 — Hero BTN 7d6d: open, pagar 3-bet do SB, flutuar o flop, raise no turn.
    h = Hand("55", "19:35:00", 1, "7d 6d")     # btn=1: SB=A, BB=B; UTG=C
    h.fold(C); h.fold(D); h.fold(E)
    h.raise_to("Hero", 230)
    h.raise_to(A, 800)
    h.fold(B)
    h.call("Hero")
    h.street("FLOP", "[9d 8d 2c]")
    h.bet(A, 900); h.call("Hero")
    h.street("TURN", "[9d 8d 2c] [Ts]")
    h.bet(A, 2200); h.raise_to("Hero", 5500); h.fold(A)
    out.append(h.win_uncalled("Hero"))

    return out


def main() -> None:
    text = DEMO.read_text()
    if "TM7000000150" in text:
        print("mãos deep já presentes — nada a fazer")
        return
    hands = build_all()
    DEMO.write_text(text.rstrip() + "\n\n" + "\n".join(hands))

    # validação: o parser precisa aceitar e as decisões multi-street existir
    from app.parsers import parse_text
    from app.bot.processing import _walk_hand

    parsed = parse_text(DEMO.read_text())
    new = [p for p in parsed if p.hand_id.startswith("TM700000015")]
    assert len(new) == 6, f"esperava 6 mãos novas, parser achou {len(new)}"
    for p in new:
        _, decs = _walk_hand(p)
        streets = {d["street"] for d in decs}
        print(f"{p.hand_id}: {len(decs)} decisões · streets {sorted(streets)} · "
              f"pos {p.hero_seat().position if p.hero_seat() else '?'}")
        assert len(decs) >= 3, f"{p.hand_id} tem só {len(decs)} decisões"
    print(f"OK — demo agora com {len(parsed)} mãos")


if __name__ == "__main__":
    main()
