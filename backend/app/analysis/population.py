"""Motor explorativo — tendências agregadas da população de oponentes.

A base de todo exploit: com que frequência O FIELD folda para agressão em cada
street. Cruzando com breakeven_bluff, o coach recomenda desvios lucrativos do
equilíbrio ("o field folda 62% pro bet de turn; blefe de 2/3 pote precisa de 40%
— aposte"). Alimentado pelas mãos armazenadas; fica mais preciso a cada upload.
Este é o dado proprietário que nenhum solver de prateleira tem.
"""
from __future__ import annotations

from app.models.canonical import ActionType, CanonicalHand, StreetName

_AGGRO = (ActionType.BET, ActionType.RAISE)
_RESPONSE = (ActionType.FOLD, ActionType.CALL, ActionType.RAISE)


def population_tendencies(hands: list[CanonicalHand]) -> dict:
    """Frequências de resposta à agressão, por street, sobre todas as mãos.

    Conta cada resposta imediata a uma aposta/raise (fold/call/raise). Retorna
    também o tamanho da amostra — o coach deve ser cauteloso com N pequeno.
    """
    streets = {
        s: {"fold": 0, "call": 0, "raise": 0}
        for s in ("preflop", "flop", "turn", "river")
    }

    for hand in hands:
        for st in hand.streets:
            facing = False
            for a in st.actions:
                if a.type == ActionType.POST:
                    continue
                if facing and a.type in _RESPONSE:
                    streets[st.name.value][a.type.value] += 1
                if a.type in _AGGRO:
                    facing = True
                elif a.type == ActionType.FOLD and not facing:
                    facing = False

    out: dict = {"hands_sample": len(hands), "streets": {}}
    for name, c in streets.items():
        total = sum(c.values())
        if total == 0:
            out["streets"][name] = {"sample": 0}
            continue
        out["streets"][name] = {
            "sample": total,
            "fold_vs_aggression_pct": round(100 * c["fold"] / total, 1),
            "call_pct": round(100 * c["call"] / total, 1),
            "raise_pct": round(100 * c["raise"] / total, 1),
        }
    return out


def exploit_hints(tendencies: dict, pot: float = 100.0) -> list[str]:
    """Traduz tendências em desvios acionáveis (comparando com o breakeven)."""
    from app.analysis.tools import breakeven_bluff

    hints: list[str] = []
    for street, t in tendencies.get("streets", {}).items():
        if t.get("sample", 0) < 30:
            continue  # amostra pequena demais para exploit confiável
        fold = t.get("fold_vs_aggression_pct", 0) / 100
        be_66 = breakeven_bluff(pot * 0.66, pot)   # blefe 2/3 pote
        if fold > be_66 + 0.08:
            hints.append(
                f"{street}: o field folda {fold*100:.0f}% contra agressão — blefe de "
                f"2/3 pote precisa de só {be_66*100:.0f}% ⇒ blefe MAIS nessa street"
            )
        elif fold < be_66 - 0.08:
            hints.append(
                f"{street}: o field só folda {fold*100:.0f}% ⇒ blefe MENOS e aposte "
                f"mais fino por valor nessa street"
            )
    return hints
