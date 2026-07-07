"""Busca estruturada no histórico de mãos do aluno — a tool search_hands.

Permite ao coach responder "analise todos os meus c-bets/folds/all-ins": filtra
as mãos canônicas por padrão de ação do herói e devolve resumos compactos em BB
(prontos para o modelo iterar sem estourar contexto).
"""
from __future__ import annotations

from app.models.canonical import ActionType, CanonicalHand, StreetName

_STREETS = {
    "preflop": StreetName.PREFLOP, "flop": StreetName.FLOP,
    "turn": StreetName.TURN, "river": StreetName.RIVER,
}


def _hero_line(h: CanonicalHand) -> list[tuple[str, str, float]]:
    """(street, verbo, valor_bb) de cada ação do herói."""
    bb = h.stakes.big_blind or 1
    out = []
    for st in h.streets:
        for a in st.actions:
            if a.actor == h.hero and a.type != ActionType.POST:
                out.append((st.name.value, a.type.value,
                            round(((a.to_amount or a.amount) / bb), 1)))
    return out


def _was_preflop_aggressor(h: CanonicalHand) -> bool:
    pre = h.street(StreetName.PREFLOP)
    if not pre:
        return False
    last_raiser = None
    for a in pre.actions:
        if a.type == ActionType.RAISE:
            last_raiser = a.actor
    return last_raiser == h.hero


def match_pattern(h: CanonicalHand, pattern: str, street: str | None = None) -> bool:
    """O herói executou o padrão? pattern: cbet|fold|call|raise|3bet|allin|
    bet|check|showdown|win|loss."""
    line = _hero_line(h)
    want_street = street.lower() if street else None

    def on_street(verb: str, st: str | None = None) -> bool:
        return any(v == verb and (st is None or s == st)
                   and (want_street is None or s == want_street)
                   for s, v, _ in line)

    p = pattern.lower()
    if p == "cbet":
        return _was_preflop_aggressor(h) and on_street("bet", "flop")
    if p == "3bet":
        pre = h.street(StreetName.PREFLOP)
        if not pre:
            return False
        seen = 0
        for a in pre.actions:
            if a.type == ActionType.RAISE:
                if a.actor == h.hero and seen == 1:
                    return True
                seen += 1
        return False
    if p == "allin":
        return any(a.all_in and a.actor == h.hero
                   for st in h.streets for a in st.actions)
    if p in ("fold", "call", "raise", "bet", "check"):
        return on_street(p)
    if p == "showdown":
        return bool(h.final_board) and not on_street("fold")
    if p in ("win", "loss"):
        from app.agent.analyzer import analyze_hand

        net = analyze_hand(h)["net_bb"]
        return net > 0 if p == "win" else net < 0
    return False


_RANK_ALIAS = {"10": "T"}


def _classes_from_query(q: str) -> set[str]:
    """'a3o'->{'A3o'}, 'kk'->{'KK'}, 'A10s'->{'ATs'}, 'Ah 3c'->{'A3o'};
    sem sufixo ('A3') casa suited E offsuit. Vazio se não é notação de mão."""
    import re

    from app.analysis.handreport import hand_class

    s = q.strip().replace("10", "T").upper()
    # duas cartas exatas com naipe: "AH 3C" / "AH3C"
    m = re.fullmatch(r"([2-9TJQKA][SHDC])\s*([2-9TJQKA][SHDC])", s)
    if m:
        cls = hand_class([m.group(1).capitalize(), m.group(2).capitalize()])
        return {cls} if cls else set()
    # classe: "A3O", "98S", "QQ", "A3" (ambíguo -> os dois)
    m = re.fullmatch(r"([2-9TJQKA])([2-9TJQKA])([SO])?", s)
    if not m:
        return set()
    r1, r2, suff = m.group(1), m.group(2), m.group(3)
    if r1 == r2:
        return {r1 + r2}
    base = hand_class([r1 + "h", r2 + "c"])[:2]  # ordem carta alta primeiro
    if suff:
        return {base + suff.lower()}
    return {base + "s", base + "o"}


def find_hand(hands: list[CanonicalHand], query: str, limit: int = 3) -> list[dict]:
    """Localiza mãos específicas pelo Nº da sala ou pelas cartas e devolve o
    DETALHE (história lance a lance + números calculados) — é o que abre a mão
    que o aluno citou do relatório mão a mão."""
    from app.analysis.handreport import hand_class, played_facts

    q = (query or "").strip()
    if not q:
        return []
    want_classes = _classes_from_query(q)
    q_id = q.lower()

    out = []
    for h in reversed(hands):  # mais recentes primeiro
        try:
            if not h.hero or not h.stakes.big_blind:
                continue
            by_id = len(q_id) >= 5 and q_id in (h.hand_id or "").lower()
            by_cards = bool(want_classes) and hand_class(h.hero_cards) in want_classes
            if not (by_id or by_cards):
                continue
            f = played_facts(h)
            a = f["analysis"]
            out.append({
                "hand_id": h.hand_id,
                "site": h.site,
                "torneio": h.tournament_id,
                "quando": h.played_at,
                "cards": h.hero_cards,
                "classe": hand_class(h.hero_cards),
                "position": a["position"],
                "blinds": a["blinds"],
                "hero_stack_bb": a["hero_stack_bb"],
                "effective_bb": a["effective_bb"],
                "stacks_bb": a["stacks_bb"],
                "board": h.final_board,
                "net_bb": a["net_bb"],
                "historia": f["story"],
                "numeros_calculados": f["numbers"],
            })
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out


def search_hands(hands: list[CanonicalHand], pattern: str,
                 street: str | None = None, limit: int = 12) -> list[dict]:
    """Filtra e resume. Resumo compacto por mão: tudo em BB."""
    from app.agent.analyzer import analyze_hand

    out = []
    for h in reversed(hands):  # mais recentes primeiro
        try:
            if not h.hero or not h.stakes.big_blind:
                continue
            if not match_pattern(h, pattern, street):
                continue
            a = analyze_hand(h)
            line = " → ".join(
                f"{s}:{v}" + (f" {amt:g}bb" if amt else "")
                for s, v, amt in _hero_line(h)
            )
            out.append({
                "hand_id": h.hand_id,
                "cards": h.hero_cards,
                "position": a["position"],
                "hero_stack_bb": a["hero_stack_bb"],
                "effective_bb": a["effective_bb"],
                "blinds": a["blinds"],
                "board": h.final_board,
                "linha_do_heroi": line,
                "net_bb": a["net_bb"],
            })
            if len(out) >= limit:
                break
        except Exception:
            continue
    return out
