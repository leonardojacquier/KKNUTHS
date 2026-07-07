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
