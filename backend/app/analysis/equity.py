"""Cálculo de equity. Usa `treys` se disponível; caso contrário, Monte Carlo próprio.

Mantido isolado para que o resto do sistema (e os testes de parser/math) não dependa
de bibliotecas de avaliação de mão.
"""
from __future__ import annotations

import itertools
import random

RANKS = "23456789TJQKA"
SUITS = "cdhs"
_FULL_DECK = [r + s for r in RANKS for s in SUITS]


def _rank_value(rank: str) -> int:
    return RANKS.index(rank)


def equity_vs_random(
    hero_cards: list[str],
    board: list[str] | None = None,
    num_opponents: int = 1,
    iterations: int = 10000,
    seed: int | None = None,
) -> float:
    """Equity do herói contra `num_opponents` mãos aleatórias, via Monte Carlo.

    Tenta usar `treys` para avaliação rápida e correta; se ausente, usa um
    avaliador interno simples (mais lento, mas sem dependências).
    """
    board = board or []
    rng = random.Random(seed)
    try:
        return _equity_treys(hero_cards, board, num_opponents, iterations, rng)
    except ImportError:
        return _equity_naive(hero_cards, board, num_opponents, iterations, rng)


def _equity_treys(hero, board, num_opponents, iterations, rng) -> float:
    from treys import Card, Evaluator  # type: ignore

    evaluator = Evaluator()
    hero_c = [Card.new(c) for c in hero]
    board_c = [Card.new(c) for c in board]
    dead = set(hero) | set(board)
    deck = [c for c in _FULL_DECK if c not in dead]

    wins = ties = 0
    for _ in range(iterations):
        rng.shuffle(deck)
        idx = 0
        opp_hands = []
        for _o in range(num_opponents):
            opp_hands.append([Card.new(deck[idx]), Card.new(deck[idx + 1])])
            idx += 2
        need = 5 - len(board)
        sim_board = board_c + [Card.new(deck[idx + i]) for i in range(need)]
        hero_score = evaluator.evaluate(sim_board, hero_c)
        best_opp = min(evaluator.evaluate(sim_board, oh) for oh in opp_hands)
        if hero_score < best_opp:
            wins += 1
        elif hero_score == best_opp:
            ties += 1
    return (wins + ties / 2) / iterations


def _equity_naive(hero, board, num_opponents, iterations, rng) -> float:
    """Avaliador interno (sem treys). Suficiente para fallback/testes."""
    dead = set(hero) | set(board)
    deck = [c for c in _FULL_DECK if c not in dead]
    wins = ties = 0
    for _ in range(iterations):
        rng.shuffle(deck)
        idx = 0
        opp_hands = []
        for _o in range(num_opponents):
            opp_hands.append([deck[idx], deck[idx + 1]])
            idx += 2
        need = 5 - len(board)
        sim_board = board + [deck[idx + i] for i in range(need)]
        hero_score = _best_hand_score(hero + sim_board)
        best_opp = max(_best_hand_score(oh + sim_board) for oh in opp_hands)
        if hero_score > best_opp:
            wins += 1
        elif hero_score == best_opp:
            ties += 1
    return (wins + ties / 2) / iterations


def _best_hand_score(cards7: list[str]) -> tuple:
    """Melhor pontuação de 5 entre 7 cartas. Tupla comparável (maior = melhor)."""
    return max(_score5(list(combo)) for combo in itertools.combinations(cards7, 5))


_NOME_PT = "2 3 4 5 6 7 8 9 10 J Q K A".split()


def describe_hand(hole: list[str], board: list[str]) -> str | None:
    """Leitura DETERMINÍSTICA da mão feita, em português de mesa.

    'dois pares (J e 10), kicker K' — é o gabarito do que o jogador fez no
    board; o coach usa isto em vez de recontar de cabeça (que rendeu uma
    'trinca de J' inexistente numa mão real). None sem 5+ cartas."""
    cards = list(hole or []) + list(board or [])
    if not hole or len(set(cards)) < 5:
        return None
    sc = _best_hand_score(cards)

    def rn(v: int) -> str:
        return _NOME_PT[v]

    cat = sc[0]
    if cat == 8:
        return f"straight flush até {rn(sc[1])}"
    if cat == 7:
        return f"quadra de {rn(sc[1])}"
    if cat == 6:
        return f"full house ({rn(sc[1])} cheio de {rn(sc[2])})"
    if cat == 5:
        return f"flush, maior carta {rn(sc[1])}"
    if cat == 4:
        return f"sequência até {rn(sc[1])}"
    if cat == 3:
        return f"trinca de {rn(sc[1])}"
    if cat == 2:
        return f"dois pares ({rn(sc[1])} e {rn(sc[2])}), kicker {rn(sc[3])}"
    if cat == 1:
        return f"par de {rn(sc[1])}, kicker {rn(sc[2])}"
    return f"carta alta {rn(sc[1])}"


def _score5(cards: list[str]) -> tuple:
    ranks = sorted((_rank_value(c[0]) for c in cards), reverse=True)
    suits = [c[1] for c in cards]
    counts: dict[int, int] = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    # ordena por (frequência, rank)
    by_freq = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    freq_pattern = tuple(c for _, c in by_freq)
    ordered_ranks = tuple(r for r, _ in by_freq)

    is_flush = len(set(suits)) == 1
    distinct = sorted(set(ranks), reverse=True)
    is_straight, straight_high = _straight_high(distinct)

    if is_straight and is_flush:
        return (8, straight_high)
    if freq_pattern == (4, 1):
        return (7,) + ordered_ranks
    if freq_pattern == (3, 2):
        return (6,) + ordered_ranks
    if is_flush:
        return (5,) + tuple(ranks)
    if is_straight:
        return (4, straight_high)
    if freq_pattern == (3, 1, 1):
        return (3,) + ordered_ranks
    if freq_pattern == (2, 2, 1):
        return (2,) + ordered_ranks
    if freq_pattern == (2, 1, 1, 1):
        return (1,) + ordered_ranks
    return (0,) + tuple(ranks)


def _straight_high(distinct_desc: list[int]) -> tuple[bool, int]:
    if len(distinct_desc) < 5:
        # wheel: A-2-3-4-5
        pass
    s = set(distinct_desc)
    # roda (A baixo): A=12, 5=3,4=2,3=1,2=0
    if {12, 0, 1, 2, 3}.issubset(s):
        # checa se não há sequência maior
        for high in range(12, 3, -1):
            if all((high - i) in s for i in range(5)):
                return True, high
        return True, 3  # straight ao 5 (high = '5' -> rank 3)
    for high in range(12, 3, -1):
        if all((high - i) in s for i in range(5)):
            return True, high
    return False, -1
