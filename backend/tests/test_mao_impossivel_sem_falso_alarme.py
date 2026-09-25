"""O medidor de `mao_impossivel` acusava mãos que EXISTIAM.

Relido em 25/09 contra o banco: os 11 eventos desde 09/08 (os "7 casos" da
análise de 25/09 eram os de setembro) são TODOS falsos positivos. Dois
defeitos no medidor, nenhum no texto do coach:

  · contava as cartas de quem SEGURA o par contra o próprio par. Herói com
    K♠K♦ e K♥ no board → "KK impossível" em "abriu 2.5bb com KK no LJ";
  · contava em dobro a mão do herói quando ela também vem em shown_cards
    (replay de clube grava as duas) — A♦Q♦ + Q♥ do vilão virava três damas.

A análise de 25/09 pedia "corrigir em vez de só medir". Antes de corrigir
texto, conferir o medidor: não havia o que corrigir. A mão impossível de
verdade no showdown já é trocada por `corrigir_showdown`.
"""
from __future__ import annotations

import pytest

from app.analysis.historia import cita_mao_impossivel
from app.models.canonical import CanonicalHand, PlayerSeat, Stakes


def _h(hero, board, shown):
    return CanonicalHand(
        site="x", hand_id="m", hero="Hero",
        stakes=Stakes(small_blind=0.5, big_blind=1),
        players=[PlayerSeat(seat=1, name="Hero", stack=100, is_hero=True)],
        hero_cards=hero, final_board=board, shown_cards=shown, streets=[])


# casos reais do banco (bot_events.mao_impossivel + hand_analysis.summary)
CASOS_REAIS = [
    ("21/09", ["Ks", "Kd"], ["Qc", "8s", "9s", "Kh", "Js"],
     {"V1": ["6s", "Qs"], "V2": ["9d"]},
     "✅ *Pré* — abriu 2.5bb com KK no LJ: padrão, mão premium."),
    ("18/09", ["Js", "Jc"], ["2d", "9c", "6h", "Jh"], {"V1": ["6c"]},
     "✅ *Pré* — 3-bet JJ pra 6bb no BB contra abertura da UTG+1."),
    ("14/09", ["Qd", "Qs"], ["Qc", "5h", "8c", "Ac", "2c"],
     {"V1": ["4c", "4d"], "V2": ["Ad", "Kh"]},
     "você foi all-in com QQ, ficou 93% favorito no flop"),
    ("08/09", ["9h", "Qh"], ["Ah", "8s", "5h", "5c", "8h"],
     {"V1": ["Ac", "As"], "Hero": ["9h", "Qh"]},
     "pedia 21,1%, mas contra AA (o vilão virou full de A com 8)"),
    ("08/09b", ["6c", "6d"], ["2h", "Kc", "5c", "4d", "Ks"],
     {"Hero": ["6c", "6d"], "V1": ["3d", "3c"]},
     "✅ Você jogou bem — 66 virou dois pares e levou tranquilo"),
    ("09/08", ["Ad", "Qd"], ["Td", "5c", "4s", "5h", "Tc"],
     {"Hero": ["Ad", "Qd"], "V1": ["5s", "5d"], "V2": ["Qh", "Ac"]},
     "Contra o range de 4-bet dele (QQ+, AK) você tinha só ~30%"),
    ("09/08b", ["Kc", "Kh"], ["Qc", "6c", "7c", "Ad", "Ts"],
     {"V1": ["2c"], "V2": ["Qd", "Qs"]},
     "Foi cooler clássico, KK vs QQ set no flop."),
]


@pytest.mark.parametrize("quando,hero,board,shown,texto", CASOS_REAIS,
                         ids=[c[0] for c in CASOS_REAIS])
def test_mao_que_alguem_segurava_nao_e_impossivel(quando, hero, board, shown,
                                                  texto):
    assert cita_mao_impossivel(texto, _h(hero, board, shown)) is None


def test_a_mao_impossivel_de_verdade_continua_flagrada():
    """77 com 7♣7♥ no board e 7♠ na mão do herói: sobrou um sete."""
    h = _h(["As", "7s"], ["2c", "7c", "7h", "Ac", "Th"], {"V": ["7d", "2d"]})
    assert cita_mao_impossivel("o vilão apareceu com 77", h) == ["77"]


def test_carta_repetida_em_shown_e_hero_conta_uma_vez():
    h = _h(["Ad", "Qd"], ["2c", "7h", "9s"],
           {"Hero": ["Ad", "Qd"], "V": ["Qh", "3c"]})
    # duas damas vistas (Qd, Qh): sobram duas — QQ ainda cabe
    assert cita_mao_impossivel("ele pode ter QQ", h) is None
