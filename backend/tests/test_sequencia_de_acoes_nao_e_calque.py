"""'sequência' é calque quando quer dizer STRAIGHT, não quando quer dizer ORDEM.

A vigia foi criada com razão: em julho 'sequência' apareceu 7x querendo dizer
*straight* ("fechou a sequência", "board fecha sequência"). Esse uso é calque
e tem que continuar sendo acusado.

Mas o português tem a palavra para OUTRA coisa, e o coach usa as duas:

    "quando você aperta, alguém sobe, e um TERCEIRO ainda sobe de novo —
     essa é a sequência de 3-bets que define o spot"

Isso é português normal. `app/agent/termos.py` já documenta a decisão de NÃO
trocar esse caso ("'sequência de 3-bets' é português normal"), e o corretor
determinístico obedece — mas o juiz acusava assim mesmo, e a acusação entrava
como "problema de forma" no relatório do dia. Dois relatórios seguidos
gastaram a única linha de problema com esse falso positivo, escondendo o que
importava.

Regra: só acusa se sobrar alguma ocorrência FORA das colocações legítimas.
Mesmo desenho do `_RIO_LUGAR` no guarda_termos (rio-o-lugar x rio-a-street).
"""
from __future__ import annotations

import pytest

from scripts.output_judge import judge_answer

_CABECA = "✅ *Pré* — abriu 2.5bb com AKo no CO. "


def _calques(texto: str) -> list[str]:
    return [p for p in judge_answer(texto) if "calque" in p]


# ---- português normal: não acusa -------------------------------------------

@pytest.mark.parametrize("frase", [
    "essa é a sequência de 3-bets que define o spot",
    "a sequência de ações mostra agressão real",
    "olha a sequência de decisões dele no turn",
    "não é a sequência de apostas que eu esperava",
    "a sequência de mãos foi ruim, mas o jogo estava certo",
    "essa sequência de jogadas custou 4bb",
])
def test_ordem_de_acontecimentos_nao_e_calque(frase):
    achados = _calques(_CABECA + frase)
    assert not any("'sequência'" in a for a in achados), (
        f"acusou português normal: {achados}")


# ---- straight disfarçado: continua acusando --------------------------------

@pytest.mark.parametrize("frase", [
    "você fechou a sequência no river",
    "o board completa a sequência até o A",
    "tinha 8 outs pra sequência",
    "o board fecha sequência com qualquer 9",
])
def test_straight_em_portugues_continua_acusado(frase):
    achados = _calques(_CABECA + frase)
    assert any("'sequência'" in a for a in achados), (
        f"deixou passar o calque de verdade: {frase}")


def test_sequencia_de_cor_continua_sendo_straight_flush():
    """A exceção não pode ter aberto buraco no calque irmão."""
    achados = _calques(_CABECA + "ele tinha sequência de cor")
    assert any("sequência de cor" in a for a in achados)


# ---- o teste que impede a exceção de virar anistia -------------------------

def test_um_uso_legitimo_nao_absolve_o_calque_na_mesma_resposta():
    """Se a resposta tem os DOIS usos, o calque tem que continuar acusado —
    senão bastaria escrever 'sequência de ações' uma vez para se blindar."""
    texto = (_CABECA + "a sequência de ações foi essa, e no river "
             "você fechou a sequência com o 9")
    achados = _calques(texto)
    assert any("'sequência'" in a for a in achados), (
        "o uso legítimo anistiou o calque de verdade na mesma resposta")
