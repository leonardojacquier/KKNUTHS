"""O juiz ganha contadores novos, e a NOTA continua a mesma régua."""
from __future__ import annotations

import inspect

import scripts.output_judge as juiz


def test_a_nota_nao_passou_a_considerar_voz():
    """Se problemas_de_voz entrar em _nota_uma ou judge_answer, a série de
    7 dias muda de significado no meio e o antes/depois perde o sentido."""
    for fn in (juiz.judge_answer, juiz._nota_uma):
        assert "problemas_de_voz" not in inspect.getsource(fn), \
            f"{fn.__name__} passou a medir voz — a régua da nota mudou"


def test_o_juiz_conta_voz_em_algum_lugar():
    assert "problemas_de_voz" in inspect.getsource(juiz.main), \
        "o juiz não conta os defeitos de voz"


def test_contadores_de_voz_e_funcao_pura_testavel():
    linha = juiz.resumo_de_voz([
        "✅ Você jogou bem\n\nA conta que mais pesa: com 12bb é jam.",
        "✅ Você jogou bem\n\nCom 12bb é jam.",
    ])
    assert linha["analisadas"] == 2
    assert linha["com_titulo_fixo"] == 1
