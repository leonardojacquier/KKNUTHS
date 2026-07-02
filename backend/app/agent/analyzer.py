"""Agente de análise.

A camada determinística (este módulo) extrai os spots e métricas objetivas de cada
mão/torneio usando as tools de `app.analysis`. O texto final em linguagem natural pode
ser gerado por um LLM (Claude) recebendo este dicionário estruturado como contexto —
ver `llm_summary()`. Mantendo a parte cara (LLM) opcional, todo o resto roda offline.
"""
from __future__ import annotations

from app.analysis.tools import pot_odds
from app.models.canonical import ActionType, CanonicalHand, StreetName

_STREET_ORDER = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN, StreetName.RIVER]


def analyze_hand(hand: CanonicalHand) -> dict:
    """Análise estruturada de uma mão (sem LLM).

    Reconstrói o pote street a street, identifica as decisões do herói e calcula
    pot odds nos pontos de call. Retorna um dicionário pronto para virar texto.
    """
    hero = hand.hero
    spots: list[dict] = []
    pot = 0.0
    contributed: dict[str, float] = {}

    for sname in _STREET_ORDER:
        st = hand.street(sname)
        if not st:
            continue
        street_contrib: dict[str, float] = {}
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                # 'raises X to Y': o total da street já investido é descontado
                add = a.to_amount - street_contrib.get(a.actor, 0.0)

            # antes vão ao pote, mas NÃO contam como aposta da street (não entram
            # no street_contrib usado para o cálculo do 'raise to').
            counts_as_wager = a.type != ActionType.POST or a.post_type in ("sb", "bb")

            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET, ActionType.RAISE):
                # pot odds no momento do call do herói (antes de adicionar a ficha)
                if a.actor == hero and a.type == ActionType.CALL and add > 0:
                    req = pot_odds(pot, add)
                    spots.append(
                        {
                            "street": sname.value,
                            "decision": "call",
                            "to_call": round(add, 2),
                            "pot_before": round(pot, 2),
                            "required_equity": round(req, 3),
                        }
                    )
                if a.actor == hero and a.type in (ActionType.BET, ActionType.RAISE):
                    spots.append(
                        {
                            "street": sname.value,
                            "decision": "aggression",
                            "type": a.type.value,
                            "amount": round(add, 2),
                            "pot_before": round(pot, 2),
                            "all_in": a.all_in,
                        }
                    )
                pot += add
                if counts_as_wager:
                    street_contrib[a.actor] = street_contrib.get(a.actor, 0.0) + add
                contributed[a.actor] = contributed.get(a.actor, 0.0) + add

    won = hand.collected.get(hero or "", 0.0)
    invested = contributed.get(hero or "", 0.0)
    net = round(won - invested, 2)

    bb = hand.stakes.big_blind or 1
    return {
        "hand_id": hand.hand_id,
        "site": hand.site,
        "format": hand.format.value,
        "hero": hero,
        "hero_cards": hand.hero_cards,
        "position": _hero_position(hand),
        "final_board": hand.final_board,
        "pot_total": round(pot, 2),
        "net_chips": net,
        "net_bb": round(net / bb, 2),
        "spots": spots,
        "summary": _deterministic_summary(hand, spots, net, bb),
    }


def analyze_tournament(hands: list[CanonicalHand]) -> dict:
    """Agrega mãos de um mesmo torneio num relatório."""
    if not hands:
        return {"hands": 0}
    hero = next((h.hero for h in hands if h.hero), None)
    per_hand = [analyze_hand(h) for h in hands]
    net_bb = round(sum(a["net_bb"] for a in per_hand), 2)
    biggest = sorted(per_hand, key=lambda a: a["net_bb"])
    all_ins = [a for a in per_hand if any(s.get("all_in") for s in a["spots"])]

    return {
        "hero": hero,
        "tournament_id": hands[0].tournament_id,
        "buyin": hands[0].stakes.buyin,
        "hands": len(hands),
        "net_bb": net_bb,
        "biggest_loss": biggest[0] if biggest else None,
        "biggest_win": biggest[-1] if biggest else None,
        "all_in_spots": len(all_ins),
        "summary": (
            f"Torneio {hands[0].tournament_id or ''}: {len(hands)} mãos, "
            f"resultado líquido {net_bb:+.1f} BB, {len(all_ins)} spot(s) de all-in."
        ),
    }


def select_key_hands(hands: list[CanonicalHand], k: int = 5) -> list[dict]:
    """Seleciona as mãos decisivas de um torneio para coaching individual.

    Critério: todos os all-ins do herói + maiores |resultado em BB|, deduplicado,
    limitado a k — controla o custo de LLM cobrindo o que definiu o torneio.
    """
    analyses = [analyze_hand(h) for h in hands]
    allins = [a for a in analyses if any(s.get("all_in") for s in a["spots"])]
    by_swing = sorted(analyses, key=lambda a: abs(a["net_bb"]), reverse=True)

    seen: set[str] = set()
    key: list[dict] = []
    for a in allins + by_swing:
        if a["hand_id"] in seen:
            continue
        seen.add(a["hand_id"])
        key.append(a)
        if len(key) >= k:
            break
    return key


def _hero_position(hand: CanonicalHand) -> str | None:
    seat = hand.hero_seat()
    return seat.position if seat else None


def _deterministic_summary(hand: CanonicalHand, spots: list[dict], net: float, bb: float) -> str:
    cards = " ".join(hand.hero_cards) if hand.hero_cards else "?"
    pos = _hero_position(hand) or "?"
    parts = [f"{hand.hero or 'Herói'} ({cards}) em {pos}."]
    for s in spots:
        if s["decision"] == "call":
            parts.append(
                f"No {s['street']}: pagou {s['to_call']:.0f} num pote de "
                f"{s['pot_before']:.0f} — equity necessária {s['required_equity']*100:.1f}%."
            )
        else:
            tag = "all-in" if s.get("all_in") else s["type"]
            parts.append(
                f"No {s['street']}: {tag} de {s['amount']:.0f} "
                f"(pote {s['pot_before']:.0f})."
            )
    parts.append(f"Resultado: {net/bb:+.1f} BB.")
    return " ".join(parts)


def llm_summary(structured: dict, stats: dict | None = None, lang: str = "pt") -> str:
    """Coaching em linguagem natural via Claude (com tools determinísticas).

    Recebe a análise estruturada e as stats do jogador; o LLM julga e explica usando
    os números já calculados. Sem ANTHROPIC_API_KEY, cai no resumo determinístico.
    """
    from app.agent.llm import coach

    return coach(structured, stats, lang)
