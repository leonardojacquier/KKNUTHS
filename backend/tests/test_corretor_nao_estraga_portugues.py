"""O corretor de termos não pode estragar frase normal de jogador.

Achado da auditoria de 07/08: o regex que troca carta crua por ícone casava
QUALQUER rank seguido do naipe, e os ranks de dígito colidem com as unidades
mais faladas em português:

    "joguei 3h ontem"        -> "joguei 3♥ ontem"
    "o torneio começa 10h"   -> "o torneio começa 10♥"
    "fiquei 2h no tilt"      -> "fiquei 2♥ no tilt"
    "parei por 3d"           -> "parei por 3♦"
    "demorou 30s"            -> "demorou 30♠"

Ou seja: a peça que existe para o coach falar direito era ela mesma a fonte
do "você parece um maluco falando". Ranks de FACE (K/Q/J/T) são seguros —
não existem como unidade em português. Dígito só vira carta dentro de uma
sequência de cartas.
"""
from __future__ import annotations

import pytest

from app.agent.termos import corrigir

# frases que um aluno escreve e que NÃO podem ser tocadas
PORTUGUES = [
    "joguei 3h ontem e mais 6h hoje",
    "o torneio começa 10h da manhã",
    "fiquei 2h no tilt depois daquela mão",
    "parei por 3d e voltei pior",
    "demorou 30s pra responder",
    "o nível sobe a cada 8h de jogo",
    "entrei no 5c de buy-in",           # 'c' de centavos
]


@pytest.mark.parametrize("frase", PORTUGUES)
def test_frase_de_gente_fica_intacta(frase):
    assert corrigir(frase) == frase, "o corretor mexeu em português normal"


# cartas de verdade que PRECISAM virar ícone
@pytest.mark.parametrize("entrada,saida", [
    ("abriu Ah7h de UTG", "abriu A♥7♥ de UTG"),
    ("flop 7c 5s 5c", "flop 7♣ 5♠ 5♣"),
    ("o Kh no turn", "o K♥ no turn"),          # face solta é segura
    ("Qs e Jd", "Q♠ e J♦"),
    ("board 2c7c7h", "board 2♣7♣7♥"),
])
def test_carta_de_verdade_vira_icone(entrada, saida):
    assert corrigir(entrada) == saida


def test_o_as_continua_com_as_duas_excecoes():
    """'As' é artigo e 'Ah,' é interjeição — as duas guardas antigas seguem."""
    assert corrigir("As cartas na mesa") == "As cartas na mesa"
    assert corrigir("Ah, entendi agora") == "Ah, entendi agora"
    assert corrigir("tinha Ah no turn") == "tinha A♥ no turn"


def test_full_house_nao_gagueja():
    """A troca não absorvia o 'full house' que vem antes: o resultado saía
    'full house full de 7 com A' (entregue a aluno em 07/08)."""
    assert corrigir("full house 7 cheio de A") == "full de 7 com A"
    assert corrigir("7 cheio de A") == "full de 7 com A"
    assert corrigir("full house full de 7 com A") == "full house full de 7 com A"


def test_plural_de_high_card():
    """'suas cartas altas' virava 'suas high card' — pior português que o
    calque que se queria consertar."""
    assert corrigir("suas cartas altas não valem") == \
        "suas high cards não valem"
    assert corrigir("ficou com carta alta") == "ficou com high card"


def test_o_preco_do_conserto_esta_documentado():
    """Carta SOLTA de dígito não vira ícone — é a troca consciente: perder um
    ícone é cosmético, escrever 'fiquei 2♥ no tilt' é o coach parecendo
    maluco. Se um dia isso incomodar, o conserto é contexto, não regex."""
    assert corrigir("o 7h fechou o flush") == "o 7h fechou o flush"
    # mas dentro de sequência, converte
    assert corrigir("o 7h 2h fechou") == "o 7♥ 2♥ fechou"
