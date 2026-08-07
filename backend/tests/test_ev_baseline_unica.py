"""UM baseline de EV — o texto e o gráfico não podem discordar.

Caso real (07/08, print do dono): a mesma mensagem trazia "o call rende
+7.6bb de EV comparado a foldar" e, logo acima, um gráfico marcando +8.2 na
mão KK do mesmo spot. Os dois números estavam CERTOS: +7.57 é o EV absoluto
do call e +8.19 é o EV contra foldar (fold_ev = -0.62). O erro foi de
baseline — o motor devolvia só o absoluto, o gráfico desenhava a diferença,
e a frase do coach dizia "comparado a foldar" no número errado.

O mesmo engano quebrava a lista "na fronteira" do /spot: indiferença é
ev == ev do fold (que é NEGATIVO), não ev perto de zero.
"""
from __future__ import annotations

import pytest

from app.analysis.allin_engine import available, solve_spot

pytestmark = pytest.mark.skipif(not available(),
                                reason="matriz de equity indisponível")

# o spot exato do print: SB paga o all-in do CO com 11.9bb
SPOT = ("call_shove", "SB", 11.9, 0.125, 1.0, "CO", 2.2, 0)


def test_ev_vs_fold_e_a_diferenca_e_o_grafico_desenha_ela():
    sol = solve_spot(*SPOT)
    f = sol["fold_ev"]
    assert f < 0, "o fold custa blind+ante: se der >= 0 a conta mudou"
    for mao in ("AA", "KK", "QQ", "AKs", "72o"):
        assert sol["ev_vs_fold"][mao] == pytest.approx(
            sol["ev"][mao] - f, abs=0.011), mao
    # os dois números do print, cada um no seu campo
    assert sol["ev"]["KK"] == pytest.approx(7.57, abs=0.05)
    assert sol["ev_vs_fold"]["KK"] == pytest.approx(8.19, abs=0.05)


def test_a_ferramenta_do_coach_entrega_o_numero_do_grafico():
    """O coach citava ev_da_mao_bb (absoluto) escrevendo 'comparado a
    foldar'. Agora o campo que ele deve citar tem o nome do que ele é."""
    from app.agent.llm import _dispatch

    out = _dispatch("ev_allin", {"spot": "call_shove", "hero_pos": "SB",
                                 "stack_bb": 11.9, "vilao_pos": "CO",
                                 "cards": ["Kh", "Kd"]})
    assert out["mao"] == "KK"
    assert out["ev_vs_fold_bb"] == pytest.approx(8.19, abs=0.05)
    assert out["ev_absoluto_bb"] == pytest.approx(7.57, abs=0.05)
    # o campo antigo, ambíguo, não existe mais
    assert "ev_da_mao_bb" not in out
    assert "vs foldar" in out["como_citar"] or \
           "comparado a foldar" in out["como_citar"]
    # o topo do range também vem em vs-fold, igual ao gráfico
    assert out["melhores_vs_fold"]["AA"] == pytest.approx(10.54, abs=0.05)


def test_fronteira_do_spot_e_indiferenca_de_verdade():
    """KTs aparecia como 'quase indiferente' valendo +0.95bb a mais que
    foldar — um call óbvio no meio da lista de mãos marginais."""
    sol = solve_spot(*SPOT)
    fronteira = [h for h, v in sol["ev_vs_fold"].items() if abs(v) <= 0.2]
    assert fronteira, "nenhuma mão indiferente? a conta mudou"
    for h in fronteira:
        assert abs(sol["ev_vs_fold"][h]) <= 0.2
    # as que o critério antigo (0 <= ev_absoluto <= 0.4) pegava não são
    # indiferentes: estão bem acima do fold
    antigas = [h for h, v in sol["ev"].items() if 0 <= v <= 0.4]
    for h in antigas:
        assert sol["ev_vs_fold"][h] > 0.5, f"{h} não é fronteira"


def test_spot_mostra_vs_fold_e_nao_o_absoluto():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing.texto_do_spot) \
        if hasattr(processing, "texto_do_spot") else ""
    if not fonte:                      # nome interno mudou: busca no módulo
        fonte = inspect.getsource(processing)
    assert 'sorted(sol["ev_vs_fold"].items()' in fonte
    assert "bb a mais que foldar" in fonte
    assert "tanto faz agir ou foldar" in fonte
