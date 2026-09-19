"""ICM (Independent Chip Model) — Malmuth-Harville.

Converte stacks de fichas em equity de dinheiro real dado a estrutura de payout.
É o coração da decisão profissional em MTT: perto do bubble/FT, fichas ganhas
valem menos do que fichas perdidas — o `bubble_factor` quantifica isso.
"""
from __future__ import annotations

from functools import lru_cache


def icm_equity(stacks: list[float], payouts: list[float]) -> list[float]:
    """$EV de cada jogador (Malmuth-Harville).

    P(jogador i termina em 1º) = stack_i / total.
    P(i termina em k) condiciona nos que terminaram acima (recursão).
    Payouts além do número de jogadores são ignorados; jogadores além dos
    payouts recebem 0 pelo excedente.
    """
    n = len(stacks)
    if n == 0:
        return []
    if any(s < 0 for s in stacks):
        raise ValueError("stack negativo")
    pay = tuple(payouts[:n])
    stacks_t = tuple(float(s) for s in stacks)

    @lru_cache(maxsize=None)
    def share(remaining: tuple[int, ...]) -> dict[int, float]:
        """P(cada jogador de `remaining` terminar em 1º entre os restantes)."""
        total = sum(stacks_t[i] for i in remaining)
        return {i: stacks_t[i] / total if total else 1 / len(remaining) for i in remaining}

    equities = [0.0] * n

    def walk(remaining: tuple[int, ...], depth: int, prob: float) -> None:
        if depth >= len(pay) or prob < 1e-12 or not remaining:
            return
        probs = share(remaining)
        for i in remaining:
            p_i = probs[i] * prob
            equities[i] += p_i * pay[depth]
            if depth + 1 < len(pay):
                rest = tuple(j for j in remaining if j != i)
                walk(rest, depth + 1, p_i)

    walk(tuple(range(n)), 0, 1.0)
    return [round(e, 4) for e in equities]


def bubble_factor(
    stacks: list[float], payouts: list[float], hero_idx: int, villain_idx: int
) -> float:
    """Razão entre o $ que o herói PERDE ao perder um all-in contra o vilão e o
    $ que GANHA ao vencê-lo (stack efetivo). >1 = pressão de ICM; 1 = chip-EV puro.
    """
    if hero_idx == villain_idx:
        raise ValueError("herói e vilão devem ser diferentes")
    base = icm_equity(stacks, payouts)[hero_idx]
    eff = min(stacks[hero_idx], stacks[villain_idx])

    win = list(stacks)
    win[hero_idx] += eff
    win[villain_idx] -= eff
    gain = icm_equity(win, payouts)[hero_idx] - base

    lose = list(stacks)
    lose[hero_idx] -= eff
    lose[villain_idx] += eff
    loss = base - icm_equity(lose, payouts)[hero_idx]

    if gain <= 0:
        return float("inf")
    return round(loss / gain, 3)


def icm_call_threshold(
    stacks: list[float], payouts: list[float], hero_idx: int, villain_idx: int,
    stack_bb: float | None = None, dead_bb: float | None = None,
    post_bb: float | None = None,
) -> float | None:
    """Equity mínima para o call de all-in ser +$EV, COM o pote morto.

    Fórmula até 07/08: bf/(1+bf). Ela só vale num all-in sem pote morto e sem
    blind já postado — situação que não existe numa mesa. A ressalva estava
    só no docstring; a descrição entregue ao coach dizia apenas "threshold =
    bf/(1+bf)", e o número saía formatado como "você precisa de X% pra pagar".

    Auditoria mediu o estrago (bf=1.545, BB paga shove, ante 12.5%):

        stack ef.   correto   a fórmula dizia
           5bb       42.5%        60.7%     (+18.2 pontos)
          10bb       51.1%        60.7%      (+9.6)
          20bb       55.8%        60.7%      (+4.9)

    Sempre na direção de foldar demais, e justamente na bolha, onde o erro é
    mais caro. Um aluno que seguiu isso largou mão que era call.

    A conta certa vem de exigir que pagar bata foldar:
        eq*(s + dead) - (1-eq)*s*bf  >  -post*bf
        eq > (s*bf - post*bf) / (s + dead + s*bf)

    Sem o contexto do pote devolve None DE PROPÓSITO: número errado dito com
    confiança é pior que número ausente — quem chama tem que dizer que não
    sabe, não chutar.
    """
    bf = bubble_factor(stacks, payouts, hero_idx, villain_idx)
    if bf == float("inf"):
        return 1.0
    if stack_bb is None or dead_bb is None or post_bb is None:
        return None
    s, dead, post = float(stack_bb), float(dead_bb), float(post_bb)
    if s <= 0:
        return None
    denom = s + dead + s * bf
    if denom <= 0:
        return None
    return round(max(0.0, min(1.0, (s * bf - post * bf) / denom)), 4)
