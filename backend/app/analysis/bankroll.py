"""Gestão de banca — risco de ruína e downswing esperado em MTT.

Monte Carlo com modelo top-heavy de premiação de torneio (a realidade do
MTT: você não caixa 85% das vezes e os prêmios grandes são raros), com os
multiplicadores ESCALADOS para a média bater com o ROI informado. Seed
fixa: a mesma pergunta dá sempre a mesma resposta (consistência de coach).
"""
from __future__ import annotations

import random

# distribuição condicional de prêmio (em buy-ins), dado que caixou:
# min-cash frequente, mesa final rara — formato clássico de MTT de campo médio
_MULT = [1.5, 2.0, 3.0, 5.0, 8.0, 15.0, 30.0]
_PESO = [30, 25, 20, 12, 8, 4, 1]


def risk_of_ruin(bankroll_buyins: float, roi_pct: float = 10.0,
                 itm_pct: float = 15.0, torneios: int = 1000,
                 sims: int = 3000, seed: int = 20260721) -> dict:
    """Simula `sims` carreiras de `torneios` torneios cada.

    Ruína = banca cair abaixo de 1 buy-in (não consegue mais jogar).
    Retorna risco de ruína, downswing típico e pior razoável (p95)."""
    if bankroll_buyins < 1:
        raise ValueError("banca precisa de pelo menos 1 buy-in")
    if not 0 < itm_pct < 100:
        raise ValueError("itm_pct entre 0 e 100")
    itm = itm_pct / 100.0
    base_media = sum(m * w for m, w in zip(_MULT, _PESO)) / sum(_PESO)
    # escala os multiplicadores pra fechar: itm * media_cond = 1 + roi
    escala = (1.0 + roi_pct / 100.0) / (itm * base_media)
    mult = [m * escala for m in _MULT]

    rng = random.Random(seed)
    ruinas = 0
    downswings: list[float] = []
    for _ in range(sims):
        banca = float(bankroll_buyins)
        pico = banca
        pior_queda = 0.0
        for _ in range(torneios):
            banca -= 1.0
            if rng.random() < itm:
                banca += rng.choices(mult, weights=_PESO)[0]
            pico = max(pico, banca)
            pior_queda = max(pior_queda, pico - banca)
            if banca < 1.0:
                ruinas += 1
                break
        downswings.append(pior_queda)

    downswings.sort()
    n = len(downswings)
    return {
        "banca_buyins": bankroll_buyins,
        "roi_assumido_pct": roi_pct,
        "risco_de_ruina_pct": round(100 * ruinas / sims, 1),
        "downswing_tipico_bi": round(downswings[n // 2], 1),
        "downswing_p95_bi": round(downswings[int(n * 0.95)], 1),
        "horizonte_torneios": torneios,
        "nota": (
            f"Monte Carlo ({sims} carreiras) com premiação top-heavy de MTT "
            f"(ITM {itm_pct:g}%, prêmios de {mult[0]:.1f} a {mult[-1]:.0f} "
            "buy-ins) escalada pro ROI informado. Downswing típico = mediana "
            "da pior queda pico-a-vale; p95 = pior razoável. ROI real "
            "incerto: rode também com ROI 0% pra ver o cenário neutro."
        ),
    }
