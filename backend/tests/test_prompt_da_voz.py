"""O prompt pede a voz nova — e não briga com o que já pedia."""
from __future__ import annotations

import inspect

from app.agent import llm

PROMPT = llm._SYSTEM["pt"]


def test_a_instrucao_nao_planta_mais_o_titulo_fixo():
    """llm.py:1854 mandava 'Feche com A conta que mais pesa.' — o formulário
    que apareceu em 25% das análises era pedido nosso, por escrito."""
    fonte = inspect.getsource(llm.coach)
    assert "conta que mais pesa" not in fonte.lower(), \
        "a instrução do coach ainda planta o título fixo"


def test_o_prompt_proibe_o_titulo_fixo():
    assert "conta que mais pesa" in PROMPT.lower(), \
        "o prompt precisa NOMEAR o título para proibi-lo"


def test_o_prompt_proibe_repetir_numero_do_placar_no_fechamento():
    baixo = PROMPT.lower()
    assert "já apareceu no placar" in baixo or "repet" in baixo


def test_o_prompt_manda_explicar_o_conceito():
    assert "por que" in PROMPT.lower() or "porquê" in PROMPT.lower()


def test_o_prompt_permite_parentese_didatico_na_primeira_aparicao():
    """O V4 antigo PROIBIA parêntese didático na análise. O dono pediu
    conceito + termo explicados, então a proibição vira exceção regrada."""
    baixo = PROMPT.lower()
    assert "primeira aparição" in baixo or "primeira vez" in baixo


def test_o_selo_e_o_placar_continuam_obrigatorios():
    """Regra de ouro. Nenhuma mudança de voz pode afrouxá-la."""
    assert "R1 SELO NA 1ª LINHA" in PROMPT
    assert "R2 PLACAR STREET A STREET" in PROMPT


def test_o_prompt_nao_pede_e_proibe_a_mesma_coisa():
    """O V4 novo manda explicar; o R7 proíbe parágrafo longo. A saída é a
    explicação morar DENTRO do porquê curto do placar — se o prompt não
    disser onde, ele briga consigo."""
    assert "dentro do porquê" in PROMPT.lower() or \
           "no porquê da linha" in PROMPT.lower()
