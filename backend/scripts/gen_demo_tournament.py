"""Gera um torneio DEMO realista em formato GGPoker para teste de ponta a ponta.

Motor simples mas contábil: percentil da mão decide as ações pré-flop (com
jam/fold de stack curto), pós-flop um modelo bet/call/fold por força real da
mão (avaliador de 7 cartas), pote fechando certinho (uncalled devolvido),
blinds subindo, mesa repondo jogador eliminado. Determinístico por seed.

Uso: python scripts/gen_demo_tournament.py [seed] [alvo_de_maos] > arquivo.txt
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis.equity import _FULL_DECK, _best_hand_score  # noqa: E402
from app.analysis.pushfold import hand_percentile  # noqa: E402

LEVELS = [(100, 200, 25), (150, 300, 40), (200, 400, 50), (300, 600, 75),
          (400, 800, 100), (500, 1000, 125), (600, 1200, 150), (800, 1600, 200)]
HANDS_PER_LEVEL = 22
NAMES = ["a1b2c3d4", "e5f6a7b8", "c9d0e1f2", "b3c4d5e6", "f7a8b9c0",
         "d2e3f4a5", "e9f8a7b6", "c5d6e7f8", "b1c2d3e4"]


def fmt(n: float) -> str:
    return f"{int(n):,}"


def postflop_strength(cards, board, rng) -> float:
    """Força ~[0,1]: fração de combos aleatórios que a mão vence neste board."""
    dead = set(cards) | set(board)
    live = [c for c in _FULL_DECK if c not in dead]
    mine = _best_hand_score(list(cards) + list(board))
    wins = 0
    trials = 40
    for _ in range(trials):
        c1, c2 = rng.sample(live, 2)
        if mine >= _best_hand_score([c1, c2] + list(board)):
            wins += 1
    return wins / trials


class Gen:
    def __init__(self, seed: int, target: int):
        self.rng = random.Random(seed)
        self.target = target
        self.stacks: dict[str, int] = {"Hero": 10000}
        for n in NAMES[:5]:
            self.stacks[n] = self.rng.randrange(8000, 16000, 50)
        self.order = ["Hero"] + NAMES[:5]           # ordem dos assentos
        self.spawn_i = 5
        self.btn = 0
        self.out: list[str] = []
        self.t0 = 20 * 3600 + 60  # 20:01:00

    # ------------------------------------------------------------------ hand
    def play_hand(self, num: int) -> bool:
        rng = self.rng
        sb_v, bb_v, ante = LEVELS[min(num // HANDS_PER_LEVEL, len(LEVELS) - 1)]
        lvl = min(num // HANDS_PER_LEVEL, len(LEVELS) - 1) + 5
        players = [p for p in self.order if self.stacks[p] > 0]
        if "Hero" not in players or len(players) < 3:
            return False
        self.btn = (self.btn + 1) % len(players)
        btn_p = players[self.btn]
        # ordem a partir do SB
        idx = players.index(btn_p)
        ring = players[idx + 1:] + players[:idx + 1]   # SB, BB, ..., BTN
        sb_p, bb_p = ring[0], ring[1]

        seat_of = {p: self.order.index(p) + 1 for p in players}
        ts = self.t0 + num * 95
        hh, mm, ss = ts // 3600, (ts // 60) % 60, ts % 60
        L = self.out.append
        L(f"Poker Hand #TM70{num:08d}: Tournament #300777888, KKN Demo $22 "
          f"Hold'em No Limit - Level{lvl}({fmt(sb_v)}/{fmt(bb_v)}({fmt(ante)})) "
          f"- 2026/07/08 {hh:02d}:{mm:02d}:{ss:02d}")
        L(f"Table '3' 6-max Seat #{seat_of[btn_p]} is the button")
        for p in sorted(players, key=lambda x: seat_of[x]):
            L(f"Seat {seat_of[p]}: {p} ({fmt(self.stacks[p])} in chips)")

        contrib = {p: 0 for p in players}
        committed = {p: 0 for p in players}  # na rodada de apostas atual

        def pay(p, amt):
            amt = min(amt, self.stacks[p] - contrib[p])
            contrib[p] += amt
            committed[p] += amt
            return amt

        for p in players:
            pay(p, ante)
            committed[p] = 0
            L(f"{p}: posts the ante {fmt(ante)}")
        pay(sb_p, sb_v)
        L(f"{sb_p}: posts small blind {fmt(sb_v)}")
        pay(bb_p, bb_v)
        L(f"{bb_p}: posts big blind {fmt(bb_v)}")

        deck = _FULL_DECK[:]
        rng.shuffle(deck)
        hole = {p: (deck.pop(), deck.pop()) for p in players}
        board5 = [deck.pop() for _ in range(5)]

        L("* HOLE CARDS *")
        for p in sorted(players, key=lambda x: seat_of[x]):
            if p == "Hero":
                L(f"Dealt to Hero [{hole[p][0]} {hole[p][1]}]")
            else:
                L(f"Dealt to {p}")

        # -------------------------- pré-flop --------------------------
        active = list(players)
        cur_bet = bb_v
        allin = False
        order_pre = ring[2:] + ring[:2]  # UTG..BTN, SB, BB
        raiser = None

        def stack_bb(p):
            return (self.stacks[p] - contrib[p]) / bb_v

        for p in list(order_pre):
            if p not in active or allin and p != raiser:
                pass
            pct = hand_percentile(list(hole[p]))
            to_call = cur_bet - committed[p]
            if raiser is None:
                open_t = 0.18 if p not in (sb_p, bb_p) else 0.28
                if pct <= 0.045 or (stack_bb(p) <= 11 and pct <= 0.30) and p != bb_p:
                    # open-jam curto ou monstro protegido
                    if stack_bb(p) <= 11:
                        amt = self.stacks[p] - contrib[p]
                        pay(p, amt)
                        L(f"{p}: raises {fmt(committed[p] - to_call - (cur_bet - to_call))} "
                          f"to {fmt(committed[p])} and is all-in")
                        cur_bet = committed[p]
                        raiser = p
                        allin = True
                        continue
                if pct <= open_t:
                    target = int(2.3 * bb_v)
                    pay(p, target - committed[p])
                    L(f"{p}: raises {fmt(target - cur_bet)} to {fmt(target)}")
                    cur_bet = target
                    raiser = p
                elif p == bb_p and cur_bet == bb_v:
                    L(f"{p}: checks")
                elif p == sb_p and pct <= 0.40 and cur_bet == bb_v:
                    pay(p, to_call)
                    L(f"{p}: calls {fmt(to_call)}")
                else:
                    active.remove(p)
                    L(f"{p}: folds")
            else:
                # já tem raise na mesa
                if pct <= 0.035 or (stack_bb(p) <= 13 and pct <= 0.10):
                    amt = self.stacks[p] - contrib[p]
                    add = pay(p, amt)
                    L(f"{p}: raises {fmt(committed[p] - cur_bet)} to "
                      f"{fmt(committed[p])} and is all-in")
                    cur_bet = committed[p]
                    raiser = p
                    allin = True
                elif pct <= 0.13 and not allin:
                    pay(p, to_call)
                    L(f"{p}: calls {fmt(to_call)}")
                elif allin and pct <= 0.05:
                    pay(p, to_call)
                    tag = " and is all-in" if contrib[p] >= self.stacks[p] else ""
                    L(f"{p}: calls {fmt(min(to_call, self.stacks[p]))}{tag}")
                else:
                    active.remove(p)
                    L(f"{p}: folds")

        # quem não igualou a aposta final sai (simplificação: uma volta só)
        matched = [p for p in active if committed[p] >= cur_bet or
                   contrib[p] >= self.stacks[p]]
        pot = sum(contrib.values())

        def finish_uncontested(winner):
            ret = cur_bet - max((committed[p] for p in matched if p != winner),
                                default=bb_v if winner != bb_p else 0)
            ret = max(0, min(ret, committed[winner]))
            nonlocal pot
            if ret > 0:
                contrib[winner] -= ret
                pot -= ret
                L(f"Uncalled bet ({fmt(ret)}) returned to {winner}")
            L(f"{winner} collected {fmt(pot)} from pot")
            L("* SUMMARY *")
            L(f"Total pot {fmt(pot)} | Rake 0 | Jackpot 0 | Bingo 0 | Fortune 0 | Tax 0")
            L(f"Seat {seat_of[winner]}: {winner} collected ({fmt(pot)})")
            L("")
            self.stacks[winner] += pot
            for p in players:
                self.stacks[p] -= contrib[p]

        if len(matched) == 1:
            finish_uncontested(matched[0])
            return True

        # -------------------------- pós-flop / showdown --------------------
        active = matched
        streets = [("FLOP", board5[:3]), ("TURN", board5[:4]), ("RIVER", board5)]
        folded_river = False
        if not allin and all(contrib[p] < self.stacks[p] for p in active):
            agg = raiser or active[0]
            for si, (name, board) in enumerate(streets):
                shown = " ".join(board[:3])
                extra = f" [{board[3]}]" if name == "TURN" else (
                    f" [{board[4]}]" if name == "RIVER" else "")
                base = f"[{shown}]" if name == "FLOP" else \
                    f"[{' '.join(board[:len(board)-1])}]"
                L(f"* {name} * {base}{extra}" if name != "FLOP" else
                  f"* FLOP * [{shown}]")
                committed = {p: 0 for p in active}
                # ordem pós-flop: SB primeiro
                po = [p for p in ring if p in active]
                strengths = {p: postflop_strength(hole[p], board, rng)
                             for p in active}
                bettor = None
                for p in po:
                    if bettor is None:
                        want = strengths[p] > 0.62 or \
                            (p == agg and si == 0 and rng.random() < 0.55)
                        if want:
                            size = int(pot * (0.5 + 0.25 * rng.random()) // 25 * 25)
                            size = max(size, bb_v)
                            size = min(size, self.stacks[p] - contrib[p])
                            pay(p, size)
                            tag = " and is all-in" if contrib[p] >= self.stacks[p] else ""
                            L(f"{p}: bets {fmt(size)}{tag}")
                            bettor = p
                        else:
                            L(f"{p}: checks")
                    else:
                        to_call = committed[bettor] - committed[p]
                        if strengths[p] > 0.45:
                            add = pay(p, to_call)
                            tag = " and is all-in" if contrib[p] >= self.stacks[p] else ""
                            L(f"{p}: calls {fmt(add)}{tag}")
                        else:
                            active.remove(p)
                            L(f"{p}: folds")
                pot = sum(contrib.values())
                if len(active) == 1:
                    winner = active[0]
                    ret = committed[bettor] if bettor == winner and \
                        all(committed[q] < committed[bettor]
                            for q in matched if q != winner) else 0
                    if bettor == winner and ret:
                        contrib[winner] -= ret
                        pot -= ret
                        L(f"Uncalled bet ({fmt(ret)}) returned to {winner}")
                    L(f"{winner} collected {fmt(pot)} from pot")
                    L("* SUMMARY *")
                    L(f"Total pot {fmt(pot)} | Rake 0 | Jackpot 0 | Bingo 0 | "
                      f"Fortune 0 | Tax 0")
                    L(f"Board [{' '.join(board)}]")
                    L(f"Seat {seat_of[winner]}: {winner} collected ({fmt(pot)})")
                    L("")
                    self.stacks[winner] += pot
                    for p in players:
                        self.stacks[p] -= contrib[p]
                    return True
                if any(contrib[p] >= self.stacks[p] for p in active):
                    break  # all-in: vira as cartas
        else:
            # all-in pré: mostra e corre o board
            for p in active:
                L(f"{p}: shows [{hole[p][0]} {hole[p][1]}]")
            L(f"* FLOP * [{' '.join(board5[:3])}]")
            L(f"* TURN * [{' '.join(board5[:3])}] [{board5[3]}]")
            L(f"* RIVER * [{' '.join(board5[:4])}] [{board5[4]}]")

        # showdown
        pot = sum(contrib.values())
        scores = {p: _best_hand_score(list(hole[p]) + board5) for p in active}
        winner = max(active, key=lambda p: scores[p])
        if not allin:
            for p in active:
                L(f"{p}: shows [{hole[p][0]} {hole[p][1]}]")
        L("* SHOWDOWN *")
        L(f"{winner} collected {fmt(pot)} from pot")
        L("* SUMMARY *")
        L(f"Total pot {fmt(pot)} | Rake 0 | Jackpot 0 | Bingo 0 | Fortune 0 | Tax 0")
        L(f"Board [{' '.join(board5)}]")
        for p in active:
            verb = "won" if p == winner else "lost"
            tail = f" ({fmt(pot)})" if p == winner else ""
            L(f"Seat {seat_of[p]}: {p} showed [{hole[p][0]} {hole[p][1]}] and "
              f"{verb}{tail}")
        L("")
        self.stacks[winner] += pot
        for p in players:
            self.stacks[p] -= contrib[p]
        return True

    # ------------------------------------------------------------------ run
    def run(self) -> str:
        n = 0
        while n < self.target:
            if not self.play_hand(n):
                break
            n += 1
            # elimina quebrados e repõe a mesa (mesa nova chegando)
            for p, st in list(self.stacks.items()):
                if st <= 0 and p != "Hero":
                    del self.stacks[p]
                    self.order.remove(p)
            if self.stacks.get("Hero", 0) <= 0:
                break
            while len(self.stacks) < 6 and self.spawn_i < len(NAMES):
                novo = NAMES[self.spawn_i]
                self.spawn_i += 1
                self.stacks[novo] = self.rng.randrange(9000, 22000, 50)
                self.order.append(novo)
        return "\n".join(self.out)


def main() -> int:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    print(Gen(seed, target).run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
