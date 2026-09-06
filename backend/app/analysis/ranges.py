"""Ranges de poker: parser de notação padrão, charts pré-flop e equity vs range.

Este módulo eleva a análise de "equity vs mão aleatória" para "equity vs range" —
como um profissional pensa. Suporta a notação universal:

    "22+, A2s+, KTs+, QJs, ATo+, KQo, 76s"      (lista de mãos/famílias)
    "top 15%"                                    (percentil do ranking de mãos)

`+` em pares: do par para cima (77+ = 77,88,...,AA).
`+` em não-pares: kicker para cima com o mesmo high card (KTs+ = KTs,KJs,KQs).
`X-Y` em pares: intervalo (22-66).
"""
from __future__ import annotations

import re

from app.analysis.pushfold import HAND_RANKING

RANK_ORDER = "23456789TJQKA"
SUITS = "cdhs"

# ---------------------------------------------------------------- parser ----


_COMBOS_TOTAL = 1326


def _combos_of(hand: str) -> int:
    return 6 if len(hand) == 2 else (4 if hand.endswith("s") else 12)


def parse_range(spec: str) -> list[str]:
    """Converte a notação em lista de mãos canônicas ('AKs', 'QQ', 'T9o')."""
    spec = spec.strip()
    m = re.match(r"^top\s*([\d.]+)\s*%$", spec, re.I)
    if m:
        # percentil medido em COMBOS (padrão da indústria), não em classes de
        # mão — pares valem 6, suited 4, offsuit 12
        target = max(1.0, float(m.group(1)) / 100 * _COMBOS_TOTAL)
        out: list[str] = []
        acc = 0
        for h in HAND_RANKING:
            out.append(h)
            acc += _combos_of(h)
            if acc >= target:
                break
        return out

    hands: set[str] = set()
    for token in re.split(r"[,;]\s*", spec):
        token = token.strip()
        if not token:
            continue
        hands.update(_parse_token(token))
    return sorted(hands, key=lambda h: HAND_RANKING.index(h) if h in HAND_RANKING else 999)


def _parse_token(token: str) -> list[str]:
    t = token.replace(" ", "")
    # par com intervalo: 22-66
    m = re.match(r"^([2-9TJQKA])\1-([2-9TJQKA])\2$", t)
    if m:
        lo, hi = sorted((RANK_ORDER.index(m.group(1)), RANK_ORDER.index(m.group(2))))
        return [RANK_ORDER[i] * 2 for i in range(lo, hi + 1)]
    # não-par com intervalo: 'A5s-A2s' (mesmo high card, kicker desce) ou
    # '76s-32s' (conectores/gappers descem mantendo o gap)
    m = re.match(r"^([2-9TJQKA])([2-9TJQKA])([so])-([2-9TJQKA])([2-9TJQKA])\3$", t)
    if m:
        h1, l1, suit, h2, l2 = m.groups()
        hi1, lo1 = RANK_ORDER.index(h1), RANK_ORDER.index(l1)
        hi2, lo2 = RANK_ORDER.index(h2), RANK_ORDER.index(l2)
        if hi1 == hi2:  # A5s-A2s
            a, b = sorted((lo1, lo2))
            return [f"{h1}{RANK_ORDER[k]}{suit}" for k in range(a, b + 1)]
        if hi1 - lo1 == hi2 - lo2:  # 76s-32s (gap constante)
            gap = hi1 - lo1
            top, bot = max(hi1, hi2), min(hi1, hi2)
            return [f"{RANK_ORDER[k]}{RANK_ORDER[k - gap]}{suit}"
                    for k in range(bot, top + 1)]
        raise ValueError(f"intervalo de range inválido: {token!r}")
    # par (com ou sem +): 88, TT+
    m = re.match(r"^([2-9TJQKA])\1(\+?)$", t)
    if m:
        start = RANK_ORDER.index(m.group(1))
        if m.group(2):
            return [RANK_ORDER[i] * 2 for i in range(start, len(RANK_ORDER))]
        return [m.group(1) * 2]
    # não-par sem sufixo: 'AK' / 'AQ+' = suited E offsuit
    m = re.match(r"^([2-9TJQKA])([2-9TJQKA])(\+?)$", t)
    if m and m.group(1) != m.group(2):
        base = m.group(1) + m.group(2)
        plus = m.group(3)
        return _parse_token(f"{base}s{plus}") + _parse_token(f"{base}o{plus}")
    # não-par: AKs, A2s+, QTo+, KQo
    m = re.match(r"^([2-9TJQKA])([2-9TJQKA])([so])(\+?)$", t)
    if m:
        hi, lo, suit, plus = m.groups()
        hi_i, lo_i = RANK_ORDER.index(hi), RANK_ORDER.index(lo)
        if hi_i < lo_i:
            hi_i, lo_i = lo_i, hi_i
            hi = RANK_ORDER[hi_i]
        if not plus:
            return [f"{hi}{RANK_ORDER[lo_i]}{suit}"]
        # kicker sobe até uma abaixo do high card
        return [f"{hi}{RANK_ORDER[k]}{suit}" for k in range(lo_i, hi_i)]
    raise ValueError(f"token de range inválido: {token!r}")


def expand_combos(hands: list[str], dead: set[str] | None = None) -> list[tuple[str, str]]:
    """Mãos canônicas -> combos concretos (excluindo cartas mortas)."""
    dead = dead or set()
    combos: list[tuple[str, str]] = []
    for h in hands:
        if len(h) == 2:  # par
            r = h[0]
            cards = [r + s for s in SUITS if r + s not in dead]
            combos += [(a, b) for i, a in enumerate(cards) for b in cards[i + 1:]]
        else:
            r1, r2, kind = h[0], h[1], h[2]
            for s1 in SUITS:
                c1 = r1 + s1
                if c1 in dead:
                    continue
                for s2 in SUITS:
                    c2 = r2 + s2
                    if c2 in dead or c2 == c1:
                        continue
                    if kind == "s" and s1 != s2:
                        continue
                    if kind == "o" and s1 == s2:
                        continue
                    combos.append((c1, c2))
    # dedup (pares o/s geram simetrias)
    return list({tuple(sorted(c)): c for c in combos}.values())


# --------------------------------------------------- charts pré-flop --------
# Ranges de open-raise padrão ~100bb, 6-9max (consenso de charts publicados).
# Referência para o LLM, não lei — ajustar por dinâmica de mesa.
OPEN_RANGES: dict[str, str] = {
    "UTG": "77+, ATs+, KQs, QJs, JTs, AJo+, KQo",
    "UTG+1": "66+, A9s+, KJs+, QJs, JTs, T9s, ATo+, KQo",
    "MP": "55+, A7s+, KTs+, QTs+, J9s+, T9s, 98s, ATo+, KJo+",
    "HJ": "44+, A4s+, K9s+, Q9s+, J9s+, T8s+, 97s+, 87s, A9o+, KTo+, QJo",
    "CO": "22+, A2s+, K7s+, Q8s+, J8s+, T7s+, 96s+, 86s+, 75s+, 65s, A7o+, K9o+, Q9o+, JTo",
    "BTN": "22+, A2s+, K2s+, Q4s+, J6s+, T6s+, 95s+, 84s+, 74s+, 63s+, 53s+, A2o+, K7o+, Q8o+, J8o+, T8o+, 98o",
    "SB": "22+, A2s+, K5s+, Q7s+, J7s+, T7s+, 96s+, 86s+, 75s+, 65s, A4o+, K9o+, Q9o+, J9o+, T9o",
}

THREEBET_RANGES: dict[str, str] = {
    "vs_EP": "QQ+, AKs, AKo, A5s",
    "vs_MP": "JJ+, AQs+, A5s, AKo",
    "vs_CO": "TT+, AJs+, KQs, A5s, A4s, AQo+",
    "vs_BTN": "99+, ATs+, KJs+, A5s-A2s, AJo+, KQo",
}


def preflop_range(position: str, action: str = "open") -> str | None:
    """Range de referência: action='open' por posição, ou '3bet' vs posição."""
    if action == "open":
        return OPEN_RANGES.get(position.upper())
    if action == "3bet":
        return THREEBET_RANGES.get(f"vs_{position.upper()}")
    return None


# ------------------------------------------------- equity vs range ----------


def equity_vs_range(
    hero_cards: list[str],
    villain_range: str,
    board: list[str] | None = None,
    iterations: int = 10000,
    seed: int | None = None,
    num_opponents: int = 1,
) -> dict:
    """Equity do herói contra `num_opponents` vilões, cada um com este range
    (Monte Carlo uniforme sobre os combos).

    `villain_range` aceita notação ("TT+, AQs+") ou "top X%".
    MULTIWAY (num_opponents>1): cada vilão saca um combo independente do
    range (sem carta repetida) e o herói só ganha se bater TODOS — a equity
    despenca com cada oponente a mais, e é por isso que range de call aperta
    em pote multiway. Empate divide o pote (conta a fração).
    """
    import random

    from app.analysis.equity import _FULL_DECK  # baralho compartilhado

    board = board or []
    n_opp = max(1, int(num_opponents))
    dead = set(hero_cards) | set(board)
    hands = parse_range(villain_range)
    combos = expand_combos(hands, dead)
    if not combos:
        raise ValueError("range vazio após remover cartas mortas")
    if len(combos) < n_opp:
        raise ValueError("range pequeno demais para tantos oponentes")

    rng = random.Random(seed)

    def _sortear_viloes():
        """N combos do range sem carta repetida entre eles (mão real na mesa
        não compartilha carta). Devolve None se não fechar — a amostra é
        descartada em vez de enviesar."""
        usadas, escolhidos = set(), []
        for _ in range(n_opp):
            for _tent in range(24):
                c = combos[rng.randrange(len(combos))]
                if c[0] not in usadas and c[1] not in usadas:
                    usadas.update(c)
                    escolhidos.append(c)
                    break
            else:
                return None
        return escolhidos

    try:
        from treys import Card, Evaluator  # type: ignore

        evaluator = Evaluator()
        hero_c = [Card.new(c) for c in hero_cards]
        board_c = [Card.new(c) for c in board]

        def _share(vils, extra_raw, board_sim):
            hs = evaluator.evaluate(board_sim, hero_c)
            scores = [evaluator.evaluate(board_sim, [Card.new(a), Card.new(b)])
                      for a, b in vils]
            melhor = min(scores)
            if hs < melhor:
                return 1.0
            if hs > melhor:
                return 0.0
            return 1.0 / (1 + sum(1 for s in scores if s == hs))

        def _board(rest, need):
            return board_c + [Card.new(rest[i]) for i in range(need)]
    except ImportError:
        from app.analysis.equity import _best_hand_score

        def _share(vils, extra_raw, board_sim):
            hs = _best_hand_score(hero_cards + board_sim)
            scores = [_best_hand_score([a, b] + board_sim) for a, b in vils]
            melhor = max(scores)
            if hs > melhor:
                return 1.0
            if hs < melhor:
                return 0.0
            return 1.0 / (1 + sum(1 for s in scores if s == hs))

        def _board(rest, need):
            return board + rest[:need]

    total_share = 0.0
    validas = 0
    need = 5 - len(board)
    for _ in range(iterations):
        vils = _sortear_viloes()
        if vils is None:
            continue
        mortas = dead.union(c for combo in vils for c in combo)
        rest = [c for c in _FULL_DECK if c not in mortas]
        rng.shuffle(rest)
        total_share += _share(vils, rest, _board(rest, need))
        validas += 1
    if not validas:
        raise ValueError("não consegui montar as mãos dos vilões nesse range")
    eq = total_share / validas

    out = {
        "equity": round(eq, 4),
        "range_hands": len(hands),
        "range_combos": len(combos),
        "range_used": villain_range,
        "oponentes": n_opp,
    }
    if n_opp > 1:
        out["nota"] = (f"equity contra {n_opp} vilões com esse range (precisa "
                       "bater TODOS) — por isso o range de call aperta em pote "
                       "multiway")
    return out
