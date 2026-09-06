"""O limiar de call na bolha tem que incluir o pote morto.

Achado da auditoria de matemática (07/08). `icm_call_threshold` devolvia
bf/(1+bf) — fórmula que só vale num all-in SEM pote morto e SEM blind
postado, situação que não existe numa mesa. A ressalva estava só no
docstring; a descrição entregue ao coach dizia "threshold = bf/(1+bf)", e o
número saía para o aluno como "você precisa de X% pra pagar".

Medido com bf=1.545 (stacks 5000/3000/2000, payouts 50/30/20), BB pagando
shove com ante 12.5%:

    stack efetivo   correto   a fórmula dizia
        5bb          42.5%        60.7%     (+18.2 pontos)
       10bb          51.1%        60.7%      (+9.6)
       20bb          55.8%        60.7%      (+4.9)

Sempre na direção de foldar demais, e na bolha, onde errar é mais caro. É o
número mais perigoso do sistema porque o coach cita ele literalmente.
"""
from __future__ import annotations

import pytest

from app.analysis.icm import bubble_factor, icm_call_threshold

STACKS = [5000, 3000, 2000]
PAYOUTS = [50, 30, 20]
# BB paga o shove numa mesa de 9 com ante 12.5% do bb
DEAD, POST = 1.375, 1.125


def _bf() -> float:
    return bubble_factor(STACKS, PAYOUTS, 1, 0)


@pytest.mark.parametrize("stack,esperado", [(5, 42.5), (10, 51.1), (20, 55.8)])
def test_o_limiar_bate_com_a_conta_a_mao(stack, esperado):
    """eq > (s*bf - post*bf) / (s + dead + s*bf)"""
    thr = icm_call_threshold(STACKS, PAYOUTS, 1, 0, stack, DEAD, POST)
    assert thr is not None
    assert thr * 100 == pytest.approx(esperado, abs=0.15)


def test_a_formula_antiga_pedia_equity_demais():
    """Guarda contra a volta do atalho: bf/(1+bf) é sempre mais tight."""
    bf = _bf()
    atalho = bf / (1 + bf)
    assert atalho * 100 == pytest.approx(60.7, abs=0.1)
    for stack in (5, 10, 20):
        certo = icm_call_threshold(STACKS, PAYOUTS, 1, 0, stack, DEAD, POST)
        assert certo < atalho, (
            f"{stack}bb: o limiar tem que ser MENOR que o atalho — se ficou "
            "maior, a conta voltou a mandar foldar demais")


def test_sem_contexto_do_pote_devolve_None_em_vez_de_chutar():
    """Número errado dito com confiança é pior que número ausente."""
    assert icm_call_threshold(STACKS, PAYOUTS, 1, 0) is None
    assert icm_call_threshold(STACKS, PAYOUTS, 1, 0, 10, None, POST) is None
    assert icm_call_threshold(STACKS, PAYOUTS, 1, 0, 0, DEAD, POST) is None


def test_a_ferramenta_do_coach_explica_a_ausencia():
    """Sem o limiar, o coach precisa saber POR QUE — senão inventa um."""
    from app.agent.llm import _dispatch

    sem = _dispatch("bubble_factor", {"stacks": STACKS, "payouts": PAYOUTS,
                                      "hero_idx": 1, "villain_idx": 0})
    assert sem["min_call_equity"] is None
    assert "18 pontos" in sem["por_que_sem_limiar"]
    assert "foldar demais" in sem["por_que_sem_limiar"]

    com = _dispatch("bubble_factor",
                    {"stacks": STACKS, "payouts": PAYOUTS, "hero_idx": 1,
                     "villain_idx": 0, "stack_bb": 10, "dead_bb": DEAD,
                     "post_bb": POST})
    assert com["min_call_equity"] * 100 == pytest.approx(51.1, abs=0.15)
    assert "51.1%" in com["como_citar"]


def test_a_descricao_da_tool_proibe_o_atalho():
    """O prompt não podia continuar ensinando a fórmula errada."""
    from app.agent.llm import TOOLS

    d = next(t["description"] for t in TOOLS if t["name"] == "bubble_factor")
    assert "bf/(1+bf)" in d and "18 PONTOS" in d
    assert "stack_bb" in d and "dead_bb" in d and "post_bb" in d


def test_bf_infinito_continua_pedindo_tudo():
    """Herói coberto e eliminado = precisa de 100%: caso de borda intacto."""
    assert icm_call_threshold([1000, 0, 0], [50, 30, 20], 0, 1) in (1.0, None)


def test_chip_ev_puro_da_50_por_cento():
    """Winner-take-all é o caso onde ICM = chip-EV: bf=1. Sem pote morto e
    sem blind postado, o limiar volta ao clássico 50% — a prova de que a
    fórmula nova não distorceu o caso simples."""
    assert bubble_factor([1000, 1000], [100, 0], 0, 1) == pytest.approx(1.0)
    thr = icm_call_threshold([1000, 1000], [100, 0], 0, 1, 10, 0.0, 0.0)
    assert thr == pytest.approx(0.5, abs=0.01)


def test_pote_morto_afrouxa_o_limiar():
    """O que o atalho ignorava: quanto mais dinheiro morto no meio, MENOS
    equity o call precisa. É a direção inteira do bug."""
    anterior = 1.0
    for dead in (0.0, 1.5, 3.0, 6.0):
        thr = icm_call_threshold(STACKS, PAYOUTS, 1, 0, 10, dead, POST)
        assert thr < anterior, f"dead={dead} não afrouxou"
        anterior = thr


# ---- o segundo achado da auditoria de matemática: bf alto degenera ----

def test_bf_alto_avisa_em_vez_de_mandar_empurrar_tudo():
    """Com bf>=2 o solver devolve "empurre 100% do range" a 10bb, e em bf=3
    o 32o marca EV POSITIVO.

    Investiguei: NÃO é erro de conta nem de convergência (o auditor atribuiu
    à linearização do custo do fold — tirar o bf do fold não muda nada, os
    dois vão a 100%). É o equilíbrio CORRETO deste modelo: com bf=3 o BB só
    paga 4.7%, e contra quem folda 95% das vezes empurrar qualquer duas
    cartas ganha 1.125bb sem disputa contra os 0.625bb do fold.

    O defeito é o MODELO — bf simétrico nos dois lados. Como não dá para
    corrigir sem stacks+payouts dentro do solver, ele passa a AVISAR."""
    from app.analysis.jam_fold_solver import solve_jam_fold

    for bf in (1.0, 1.5, 1.6):
        assert solve_jam_fold(10.0, bf, 0.125)["aviso"] is None, \
            f"bf={bf} é utilizável, não pode avisar"

    for bf in (2.0, 3.0):
        s = solve_jam_fold(10.0, bf, 0.125)
        assert s["aviso"] is not None, f"bf={bf} degenera e não avisou"
        assert "NÃO cite" in s["aviso"]
        # e o range degenerado de fato está lá, para quem quiser inspecionar
        jam = sum(1 for v in s["sb_jam"].values() if v > 0.5) / 169
        assert jam >= 0.99


def test_o_aviso_descreve_o_que_realmente_acontece():
    """Números do aviso batem com o solver — se divergirem, o coach repassa
    um diagnóstico errado."""
    from app.analysis.jam_fold_solver import solve_jam_fold

    s = solve_jam_fold(10.0, 3.0, 0.125)
    call = 100 * sum(1 for v in s["bb_call"].values() if v > 0.5) / 169
    assert f"call {call:.0f}%" in s["aviso"]
