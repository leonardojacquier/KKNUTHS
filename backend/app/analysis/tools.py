"""Ferramentas determinísticas de pôquer (funções puras).

São as "tools" que o agente LLM chama em vez de fazer conta de cabeça. Mantidas
puras e sem dependências externas para serem testáveis e baratas.
"""
from __future__ import annotations


def pot_odds(pot: float, to_call: float) -> float:
    """Fração do pote que você precisa pagar = to_call / (pot + to_call).

    Retorna a *equity mínima* necessária para o call ser neutro em EV.
    """
    if to_call <= 0:
        return 0.0
    return to_call / (pot + to_call)


# alias semântico: a equity necessária é exatamente a pot odds
required_equity = pot_odds


def ev_call(equity: float, pot: float, to_call: float) -> float:
    """EV (em fichas) de pagar uma aposta, dado a equity da sua mão.

    `pot` é o pote atual que você ganha ao vencer (já inclui a aposta a pagar);
    `to_call` é o que você arrisca. EV = equity * pot - (1 - equity) * to_call.
    No limiar de equity = pot_odds(pot, to_call) o EV é exatamente 0.
    """
    if not 0.0 <= equity <= 1.0:
        raise ValueError("equity deve estar entre 0 e 1")
    return equity * pot - (1 - equity) * to_call


def spr(effective_stack: float, pot: float) -> float:
    """Stack-to-pot ratio."""
    if pot <= 0:
        return float("inf")
    return effective_stack / pot


def mdf(pot: float, bet: float) -> dict:
    """MDF (minimum defense frequency) e alpha, enfrentando `bet` num pote `pot`.

    - MDF = pot/(pot+bet): fração MÍNIMA do range que você precisa defender
      para o vilão não lucrar blefando qualquer duas cartas.
    - alpha = bet/(pot+bet): quanto o VILÃO precisa que você folde para o
      blefe dele ser lucrativo (breakeven do blefe puro).
    """
    if pot <= 0 or bet <= 0:
        raise ValueError("pot e bet devem ser positivos")
    a = bet / (pot + bet)
    return {
        "mdf_pct": round(100 * (1 - a), 1),
        "alpha_pct": round(100 * a, 1),
        "leitura": (
            f"contra essa aposta você precisa defender ≥{100*(1-a):.0f}% do "
            f"range (foldar mais que {100*a:.0f}% = o vilão lucra blefando "
            "qualquer coisa); do lado dele, o blefe precisa que você folde "
            f"{100*a:.0f}%+ pra pagar sozinho"),
    }


def fmt_chips(v: float) -> str:
    """Número de fichas legível: 125000 -> '125k', 1250000 -> '1.25M'.

    Blinds de torneio de clube são gigantes ('blinds 125000/250000' ilegível
    na imagem); abaixo de 10k mantém o número puro (cash/stakes baixos)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(v) >= 1_000_000:
        s = f"{v / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{s}M"
    if abs(v) >= 10_000:
        s = f"{v / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return f"{v:g}"


def breakeven_bluff(bet: float, pot: float) -> float:
    """Frequência de fold necessária para um blefe de tamanho `bet` lucrar.

    = bet / (pot + bet)
    """
    if bet <= 0:
        return 0.0
    return bet / (pot + bet)
