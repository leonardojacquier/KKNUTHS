"""Solver de OPEN-SHOVE em mesa cheia — EV por mão de qualquer posição.

O solver jam/fold do projeto é heads-up (SB empurra, BB paga). Mas em MTT de
9 lugares o spot de stack curto mais comum é o open-shove de UTG/MP/CO/BTN
com N jogadores atrás — e para esse o aluno não tinha EV por mão nenhum.

Fictitious play sobre a MESMA matriz de equity 169×169 do jam/fold, agora
com o nó multiway:

  herói empurra S ──┬─ todos largam           → ganha o dinheiro morto
                    └─ o primeiro a pagar     → all-in heads-up vs a faixa
                                                de call daquele jogador

PREMISSAS (declaradas na figura — é modelo, não verdade revelada):
  - o PRIMEIRO que paga fecha a ação (sem overcall). Overcall é raro e, sem
    ele, a faixa de call sai igual para todos os jogadores atrás — o que
    diferencia as posições é a fold equity do herói (quantos faltam agir),
    que é o efeito dominante;
  - stacks efetivos iguais (o herói está curto e é coberto);
  - mesa de 9 com ante de todos.

Uma tentativa anterior usava faixa de call FIXA calibrada pelo range de
shove da tabela: descartada porque a relação não é monotônica e o alvo era
inalcançável. Aqui a faixa de call é RESOLVIDA junto com a do herói — as
duas estratégias se ajustam uma à outra até o equilíbrio, que é o único
jeito de a recomendação e o EV não se contradizerem.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.analysis.jam_fold_solver import _matrix

_ITERS = 1500

# ordem de ação numa mesa de 9 e quantos agem DEPOIS de cada posição
_ORDEM = ["UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
_ALIAS = {"UTG+2": "MP", "MP+1": "LJ"}
_BLIND = {"SB": 0.5, "BB": 1.0}


def available() -> bool:
    return _matrix() is not None


def _posicoes_atras(position: str) -> list[str]:
    pos = _ALIAS.get((position or "").upper(), (position or "").upper())
    if pos not in _ORDEM:
        pos = "MP"
    return _ORDEM[_ORDEM.index(pos) + 1:]


@lru_cache(maxsize=64)
def solve_open_shove(position: str, stack_bb: float, bf: float = 1.0,
                     ante_bb: float = 0.125) -> dict | None:
    """Equilíbrio do open-shove de `position` com `stack_bb`, mesa de 9.

    Retorna {hands, shove (freq por mão), ev (EV do shove por mão),
    fold_ev, call_range (faixa de call de quem está atrás), atras,
    shove_pct, call_pct, premissas} — ou None sem a matriz de equity.
    """
    data = _matrix()
    if data is None:
        return None
    hands, E, W = data
    n = len(hands)

    pos = _ALIAS.get((position or "").upper(), (position or "").upper())
    if pos not in _ORDEM:
        pos = "MP"
    atras = _posicoes_atras(pos)
    if not atras:                      # BB não tem open-shove (ninguém atrás)
        return None

    s = float(stack_bb)
    a = max(0.0, float(ante_bb))
    total_posts = 1.5 + 9 * a
    heroi_post = a + _BLIND.get(pos, 0.0)
    posts_atras = [a + _BLIND.get(p, 0.0) for p in atras]

    # peso de combos de cada mão (card removal do próprio herói)
    peso_total = np.maximum(W.sum(axis=1), 1e-12)

    heroi_fold = -heroi_post * bf
    shove = np.ones(n)          # começa empurrando tudo
    call = np.zeros(n)          # e ninguém pagando
    avg_shove, avg_call = shove.copy(), call.copy()

    dead_medio = total_posts - heroi_post - float(np.mean(posts_atras))
    uncontested = total_posts - heroi_post

    def _eq_contra(freq: np.ndarray) -> np.ndarray:
        """Equity de cada mão (linha) contra a distribuição `freq` (coluna),
        ponderada por card removal. NUNCA transpor E (bug conhecido do
        jam/fold: inverte a estratégia inteira)."""
        reach = W * freq[None, :]
        denom = np.maximum(reach.sum(axis=1), 1e-12)
        return (reach * E).sum(axis=1) / denom

    def _ev_shove(freq_call: np.ndarray) -> np.ndarray:
        """EV do all-in por mão do herói. A probabilidade de UM oponente
        pagar é calculada POR MÃO (card removal: com um A na mão, é menos
        provável que alguém tenha A pra pagar → mais fold equity). Sem isso
        o EV divergia ~0.5bb do solver heads-up na validação."""
        reach = W * freq_call[None, :]
        p_call = reach.sum(axis=1) / peso_total          # por mão do herói
        p_largam = np.clip(1.0 - p_call, 0.0, 1.0) ** len(atras)
        eq = _eq_contra(freq_call) if freq_call.sum() > 1e-9 else np.full(n, 0.5)
        ev_pago = eq * (s + dead_medio) - (1 - eq) * s * bf
        return p_largam * uncontested + (1 - p_largam) * ev_pago

    for t in range(1, _ITERS + 1):
        # --- melhor resposta de QUEM ESTÁ ATRÁS (paga o all-in do herói) ---
        eq_call = _eq_contra(avg_shove)
        # dead money que sobra pro caller: tudo menos o post dele e o do herói
        # (usa o post médio dos que estão atrás — a diferença entre eles é o
        # blind, tratada abaixo no EV do herói)
        br_call = np.zeros(n)
        for post_i in posts_atras:
            dead_i = total_posts - heroi_post - post_i
            ev_call = eq_call * (s + dead_i) - (1 - eq_call) * s * bf
            br_call += (ev_call > -post_i * bf).astype(float)
        br_call /= len(posts_atras)     # média das melhores respostas

        # --- melhor resposta do HERÓI (empurra ou larga) ---
        ev_shove = _ev_shove(avg_call)
        br_shove = (ev_shove > heroi_fold).astype(float)

        avg_shove += (br_shove - avg_shove) / t
        avg_call += (br_call - avg_call) / t

    # EV final contra as estratégias de equilíbrio
    ev_shove = _ev_shove(avg_call)

    def _pct(freq: np.ndarray) -> float:
        return round(100 * float((freq * peso_total).sum() / peso_total.sum()), 1)

    return {
        "hands": list(hands),
        "position": pos,
        "stack": s,
        "bf": bf,
        "ante": a,
        "atras": len(atras),
        "shove": {h: round(float(f), 3) for h, f in zip(hands, avg_shove)},
        "ev": {h: round(float(e), 3) for h, e in zip(hands, ev_shove)},
        "call_range": {h: round(float(f), 3) for h, f in zip(hands, avg_call)},
        "fold_ev": round(heroi_fold, 3),
        "shove_pct": _pct(avg_shove),
        "call_pct": _pct(avg_call),
        "premissas": (
            f"premissas: mesa de 9 · {len(atras)} atrás · equilíbrio "
            f"resolvido (herói e callers se ajustam) · primeiro que paga "
            f"fecha a ação (sem overcall) · stacks iguais {s:g}bb · ante "
            f"{a*100:g}% do bb · bubble factor {bf:g}"),
    }
