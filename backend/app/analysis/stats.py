"""Estatísticas de estilo do jogador, calculadas de forma determinística.

VPIP, PFR, 3-bet%, fator de agressão (AF) e um rótulo de estilo. Recalculável
incrementalmente a cada novo lote de mãos.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.canonical import ActionType, CanonicalHand, StreetName


@dataclass
class PlayerStats:
    player: str
    hands: int = 0
    vpip: float = 0.0      # % voluntariamente colocou fichas pré-flop
    pfr: float = 0.0       # % raise pré-flop
    three_bet: float = 0.0  # % 3-bet pré-flop (sobre oportunidades)
    af: float = 0.0        # fator de agressão pós-flop = (bets+raises)/calls
    label: str = "amostra insuficiente"
    detail: dict = field(default_factory=dict)


def compute_player_stats(hands: list[CanonicalHand], player: str | None = None) -> PlayerStats:
    """Stats de `player`; com player=None usa o herói de cada mão — correto para
    histórico cumulativo, onde o nick do herói varia entre salas."""
    n = 0
    vpip_h = pfr_h = three_bet_h = 0
    three_bet_opps = 0
    post_bets = post_raises = post_calls = 0

    for h in hands:
        target = player if player is not None else h.hero
        if not target or target not in {p.name for p in h.players}:
            continue
        n += 1

        pre = h.street(StreetName.PREFLOP)
        voluntarily = raised = three_bet = False
        had_3bet_opp = False

        if pre:
            seen_raise = 0
            for a in pre.actions:
                if a.type == ActionType.POST:
                    continue
                if a.actor == target:
                    if a.type in (ActionType.CALL, ActionType.BET, ActionType.RAISE):
                        voluntarily = True
                    if a.type == ActionType.RAISE:
                        raised = True
                    # oportunidade de 3-bet: QUALQUER decisão do jogador diante
                    # de exatamente 1 raise (o open) — inclusive fold/call, senão
                    # o denominador só conta as mãos em que ele 3-betou e a
                    # estatística vira ~100%. Raise diante de 2+ é 4-bet, não 3-bet.
                    if seen_raise == 1:
                        had_3bet_opp = True
                        if a.type == ActionType.RAISE:
                            three_bet = True
                if a.type == ActionType.RAISE:
                    seen_raise += 1

            if had_3bet_opp:
                three_bet_opps += 1

        vpip_h += int(voluntarily)
        pfr_h += int(raised)
        three_bet_h += int(three_bet)

        # agressão pós-flop
        for street_name in (StreetName.FLOP, StreetName.TURN, StreetName.RIVER):
            st = h.street(street_name)
            if not st:
                continue
            for a in st.actions:
                if a.actor != target:
                    continue
                if a.type == ActionType.BET:
                    post_bets += 1
                elif a.type == ActionType.RAISE:
                    post_raises += 1
                elif a.type == ActionType.CALL:
                    post_calls += 1

    stats = PlayerStats(player=player or "hero", hands=n)
    if n == 0:
        return stats

    stats.vpip = round(100 * vpip_h / n, 1)
    stats.pfr = round(100 * pfr_h / n, 1)
    stats.three_bet = round(100 * three_bet_h / three_bet_opps, 1) if three_bet_opps else 0.0
    stats.af = round((post_bets + post_raises) / post_calls, 2) if post_calls else float(post_bets + post_raises)
    stats.label = _label(stats)
    stats.detail = {
        "post_bets": post_bets,
        "post_raises": post_raises,
        "post_calls": post_calls,
        "three_bet_opps": three_bet_opps,
    }
    return stats


def _label(s: PlayerStats) -> str:
    """Rótulo heurístico (refinado pelo LLM com contexto na produção)."""
    if s.hands < 20:
        return "amostra insuficiente"
    loose = s.vpip >= 28
    aggressive = s.pfr >= 18 and s.af >= 2.0
    gap = s.vpip - s.pfr

    if loose and aggressive:
        return "LAG (loose-aggressive)"
    if not loose and aggressive:
        return "TAG (tight-aggressive)"
    if loose and not aggressive:
        return "calling station / loose-passive"
    if gap <= 6 and s.vpip < 18:
        return "nit (tight-passive)"
    return "tight-passive"
