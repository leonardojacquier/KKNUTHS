"""Shrinkage bayesiano das estatísticas — números honestos com amostra pequena.

Beta-binomial: cada taxa (VPIP, PFR, 3-bet) começa ancorada no prior da
população de MTT e cada observação puxa a estimativa na direção do dado real.
Com 30 mãos o prior segura o número (evita "3-bet 100%" de amostra mínima);
com 3.000 mãos ele praticamente desaparece. O coach mostra o intervalo de
credibilidade quando a amostra ainda não crava.

Sempre ligado por baixo do capô (flag interna BAYES_STATS só para rollout);
o usuário nunca vê a palavra "bayesiano" — vê "entre 22 e 33%".
"""
from __future__ import annotations

from app.analysis.stats import PlayerStats

# Priors da população de MTT (literatura/HUDs públicos; quando a nossa base
# tiver volume, passam a ser recalculados dela):
# taxa -> (média da população em %, força do prior em observações-equivalentes)
PRIORS = {
    "vpip": (24.0, 40.0),
    "pfr": (17.0, 40.0),
    "three_bet": (7.0, 25.0),
}
# AF = (bets+raises)/calls não é proporção; shrink por pseudo-contagens:
# (AF médio do field, calls-equivalentes de força)
AF_PRIOR = (2.0, 12.0)


# z do intervalo. 1.96 = IC95, 2.576 = IC99. O segundo existe para o caso de
# COMPARAÇÕES MÚLTIPLAS: varrer 15 códigos e escolher o pior é procurar o
# extremo, e a IC95 erra 1 em 20 por desenho — 15 testes garantem falso
# positivo. Quem escolhe o pior de muitos tem que usar régua mais dura.
Z95, Z99 = 1.96, 2.576


def shrunk_rate(successes: float, trials: float, prior_mean_pct: float,
                prior_strength: float, z: float = Z95) -> tuple[float, float, float]:
    """Posterior Beta(a, b): (média, IC baixo, IC alto), tudo em %.

    IC por aproximação normal da Beta — erro irrelevante para coaching e
    dispensa scipy no VPS.
    """
    p = prior_mean_pct / 100.0
    a = successes + p * prior_strength
    b = (trials - successes) + (1.0 - p) * prior_strength
    n = a + b
    mean = a / n
    sd = (a * b / (n * n * (n + 1.0))) ** 0.5
    lo = max(0.0, mean - z * sd)
    hi = min(1.0, mean + z * sd)
    return round(100 * mean, 1), round(100 * lo, 1), round(100 * hi, 1)


def shrunk_af(bets_raises: float, calls: float) -> float:
    af_p, k = AF_PRIOR
    return round((bets_raises + af_p * k) / (calls + k), 2)


def is_firm(lo: float, hi: float, spread_pct: float = 10.0) -> bool:
    """A amostra já crava o número? (IC mais estreito que spread_pct pontos)"""
    return (hi - lo) <= spread_pct


def bayes_stats(s: PlayerStats) -> dict:
    """Versão corrigida das stats de um PlayerStats, com intervalos.

    Retorna {"vpip": {"mean", "lo", "hi", "firm"}, ..., "af": {"mean", "firm"}}.
    Reconstrói as contagens a partir das taxas e do detail (o cálculo original
    é determinístico, então a reconstrução é exata a menos de arredondamento).
    """
    n = s.hands
    out: dict = {}
    counts = {
        "vpip": (round(s.vpip * n / 100.0), n),
        "pfr": (round(s.pfr * n / 100.0), n),
        "three_bet": (
            round(s.three_bet * s.detail.get("three_bet_opps", 0) / 100.0),
            s.detail.get("three_bet_opps", 0),
        ),
    }
    for key, (succ, trials) in counts.items():
        prior_mean, strength = PRIORS[key]
        mean, lo, hi = shrunk_rate(succ, trials, prior_mean, strength)
        out[key] = {"mean": mean, "lo": lo, "hi": hi, "firm": is_firm(lo, hi)}

    br = s.detail.get("post_bets", 0) + s.detail.get("post_raises", 0)
    calls = s.detail.get("post_calls", 0)
    out["af"] = {"mean": shrunk_af(br, calls), "firm": (br + calls) >= 40}
    return out


def fmt_rate(b: dict, label: str) -> str:
    """Frase de coach para uma taxa: cravada ou com intervalo honesto."""
    if b["firm"]:
        return f"{label} {b['mean']:.0f}%"
    return f"{label} ~{b['mean']:.0f}% (entre {b['lo']:.0f} e {b['hi']:.0f}% — amostra ainda pequena)"
