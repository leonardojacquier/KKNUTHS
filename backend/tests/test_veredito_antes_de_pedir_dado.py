"""Pedir dado sem entregar veredito é resposta vazia.

Juiz da saída, 14/09 (pior nota 3.5: "pede mais informações") e 21/09 (3.5:
"não deixa claro… NENHUMA das 5 mãos"). O aluno manda a mão, falta um dado
(o stack do vilão, o sizing), e a resposta inteira vira uma pergunta. O
coach humano faz o contrário: "se ele tinha 20bb é call; com 40bb, fold —
quanto ele tinha?". O aluno já sai com a regra, e a pergunta vira detalhe.
"""
from __future__ import annotations

from tests.test_prompt_nao_briga_consigo import PT


def test_falta_dado_primeiro_vem_o_veredito_condicional():
    baixo = PT.lower()
    i_veredito = baixo.find("veredito condicional")
    assert i_veredito >= 0, "o prompt não manda dar o veredito condicional"
    # a pergunta vem DEPOIS, na mesma regra — a ordem é a regra
    trecho = baixo[i_veredito:i_veredito + 200]
    assert "pergunte" in trecho, trecho
    # com um exemplo de condicional de verdade (dois cenários, dois vereditos)
    assert "com 20bb é call" in baixo and "fold" in trecho


def test_a_regra_antiga_de_so_perguntar_nao_voltou():
    assert "se faltar mesmo, pergunte o dado exato" not in PT.lower()
