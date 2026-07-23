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


def equity_vs_hand(hero: list[str], villain: list[str],
                   board: list[str] | None = None) -> float | None:
    """Equity EXATA do herói contra UMA mão conhecida (do showdown), enumerando
    as cartas que faltam no board. Determinística, barata (river=1 combo,
    turn=45, flop≈990). None se faltar carta ou houver sobreposição.

    É o número do replayer: 'no flop, contra a mão que ele tinha, você tinha
    X%'. No river vira 100/50/0 — a mão está decidida."""
    hero = [c for c in (hero or []) if c]
    villain = [c for c in (villain or []) if c]
    board = [c for c in (board or []) if c]
    if len(hero) != 2 or len(villain) != 2:
        return None
    dead = hero + villain + board
    if len(set(dead)) != len(dead):
        return None
    remaining = [c for c in _FULL_DECK if c not in dead]
    need = 5 - len(board)
    if need < 0:
        return None

    # comparador decidido UMA vez: treys (menor score = melhor) ou o avaliador
    # interno (_best_hand_score: maior tupla = melhor)
    try:
        from treys import Card, Evaluator  # type: ignore

        ev = Evaluator()
        hc = [Card.new(c) for c in hero]
        vc = [Card.new(c) for c in villain]

        def hero_beats(full):
            bc = [Card.new(c) for c in full]
            hs, vs_ = ev.evaluate(bc, hc), ev.evaluate(bc, vc)
            return (hs < vs_) - (hs > vs_)   # 1 herói, -1 vilão, 0 empate
    except ImportError:
        def hero_beats(full):
            hs = _best_hand_score(hero + full)
            vs_ = _best_hand_score(villain + full)
            return (hs > vs_) - (hs < vs_)

    # enumeração EXATA só quando é barato (pós-flop: need<=2 -> <=~1000 combos).
    # com o board muito aberto (pré-flop: C(48,5)≈1,7M) cai em Monte Carlo
    # seeded — rápido e preciso (±~0,7%), sem travar a análise.
    import math as _math

    total_combos = _math.comb(len(remaining), need) if need else 1
    wins = ties = total = 0
    if total_combos <= 2000:
        for extra in itertools.combinations(remaining, need):
            r = hero_beats(board + list(extra))
            total += 1
            wins += r > 0
            ties += r == 0
    else:
        rng = random.Random(20240501)
        for _ in range(6000):
            extra = rng.sample(remaining, need)
            r = hero_beats(board + extra)
            total += 1
            wins += r > 0
            ties += r == 0
    return (wins + ties / 2) / total if total else None


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


_SUIT_ICON = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}


def pretty_card(card: str) -> str:
    """'Th' -> '10♥' — rank de mesa + ícone do naipe (pedido do aluno: cartas
    nas descrições sempre com o ícone, nunca 'Kh' nem 'K de copas')."""
    if not card or len(card) < 2:
        return card or ""
    rank = "10" if card[0].upper() == "T" else card[0].upper()
    return rank + _SUIT_ICON.get(card[1].lower(), card[1])


def pretty_cards(cards: list[str]) -> str:
    return " ".join(pretty_card(c) for c in (cards or []))


def board_texture(board: list[str]) -> dict:
    """Textura DETERMINÍSTICA do board: quantas cartas do mesmo naipe e se
    flush é possível. Âncora anti-'fechou flush' em board de duas copas."""
    suits: dict[str, int] = {}
    for c in board or []:
        if len(c) >= 2:
            suits[c[1].lower()] = suits.get(c[1].lower(), 0) + 1
    most = max(suits.values(), default=0)
    naipe = max(suits, key=suits.get) if suits else ""
    icon = _SUIT_ICON.get(naipe, naipe)
    if most >= 3:
        nota = f"flush POSSÍVEL em {icon} ({most} cartas de {icon} no board)"
    else:
        nota = (f"flush IMPOSSÍVEL neste board — só {most} carta(s) do mesmo "
                f"naipe (ninguém tem flush aqui)")
    return {"cartas_do_mesmo_naipe": most, "flush_possivel": most >= 3,
            "nota": nota}


def _fill_suits(hole: list[str], board: list[str]) -> tuple[list[str], str | None]:
    """Completa naipes de cartas hipotéticas dadas só por rank ('QJ'): naipes
    DIFERENTES entre si e raros no board — leitura OFFSUIT, sem inventar um
    flush que o aluno não perguntou. Devolve (cartas completas, nota)."""
    taken = {c for c in (board or []) if len(c) == 2}
    on_board: dict[str, int] = {}
    for c in board or []:
        if len(c) >= 2:
            on_board[c[1]] = on_board.get(c[1], 0) + 1
    suit_pref = sorted(SUITS, key=lambda s: on_board.get(s, 0))
    filled, used_suits, guessed = [], set(), False
    for raw in hole or []:
        c = (raw or "").strip().replace("10", "T")
        if len(c) == 2:
            filled.append(c[0].upper() + c[1].lower())
            taken.add(filled[-1])
            used_suits.add(c[1].lower())
            continue
        if len(c) != 1:
            filled.append(c)
            continue
        guessed = True
        rank = c.upper()
        pick = next((s for s in suit_pref
                     if rank + s not in taken and s not in used_suits),
                    suit_pref[0])
        filled.append(rank + pick)
        taken.add(rank + pick)
        used_suits.add(pick)
    nota = ("naipes não informados — li a mão como OFFSUIT (sem flush); "
            "para o combo suited, repita com os naipes") if guessed else None
    return filled, nota


def hand_on_board(hole: list[str], board: list[str]) -> dict:
    """O que UMA mão (real ou hipotética) faz num board, street a street, mais
    a textura. Leitura calculada — a resposta oficial para 'e se ele tivesse
    QJ?' ('QJ fechou flush' num board de duas copas foi erro real; era
    sequência)."""
    hole, nota_naipes = _fill_suits(hole, board)
    out: dict = {
        "mao": pretty_cards(hole),
        "board": pretty_cards(board),
        "por_street": {},
    }
    if nota_naipes:
        out["nota_naipes"] = nota_naipes
    for st, n in (("flop", 3), ("turn", 4), ("river", 5)):
        if len(board or []) >= n:
            d = describe_hand(hole, board[:n])
            if d:
                out["por_street"][st] = d
    out["textura_do_board"] = board_texture(board)
    return out


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
