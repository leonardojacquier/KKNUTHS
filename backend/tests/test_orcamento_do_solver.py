"""Quanto trabalho o solver gasta — por street, e com teto de relógio.

Medido em 25/08 (mesmo spot, ranges de ~130 combos), com o piso de
convergência que o próprio solver publica:

           400 iter          1.600 iter         6.400 iter
  river    0,7s / 0,71pp     2,2s / 0,50pp      9,1s / 0,31pp
  turn     5,0s / 1,55pp    12,9s / 0,85pp     53,2s / 0,84pp
  flop    15,4s / 1,51pp    24,3s / 0,94pp     74,9s / 0,91pp

A leitura que decide tudo: no RIVER mais iteração compra precisão. No turn e
no flop o piso EMPACA em ~0,9pp — lá o limite é a carta AMOSTRADA, não a
iteração, e 4x mais trabalho compra 0,01pp. Gastar 53s para não melhorar nada
é pior que não gastar.

Por isso o orçamento é por street. E por isso existe também um TETO DE
RELÓGIO: os números acima são desta máquina; a do deploy é mais lenta, e um
orçamento só em iterações vira espera imprevisível lá. Com teto, o aluno
espera no máximo X segundos em qualquer máquina — e a medida de convergência
diz o que deu para comprar nesse tempo.
"""
from __future__ import annotations

import time

from app.analysis import river_solver as R

_OOP = "AA,KK,77,22,99,AK,AQ,AJ,KQ,QJ,JT,T9,98,87,76,65"
_IP = "AK,AQ,AJ,ATs,KQ,KJs,QJs,JTs,T9s,99,77,22,A5s,A4s"
_RIVER = ["Ah", "Kd", "7c", "2s", "9h"]


def test_o_river_ganha_o_maior_orcamento_de_iteracoes():
    """É a única street onde mais iteração vira mais precisão."""
    assert R._ORCAMENTO[5] >= 6400
    assert R._ORCAMENTO[5] > R._ORCAMENTO[4]
    assert R._ORCAMENTO[5] > R._ORCAMENTO[3]


def test_turn_e_flop_nao_pagam_alem_do_platô():
    """Acima de ~1.600 o piso empaca em ~0,9pp: o limite é a amostragem da
    carta. Orçar 6.400 lá seria 4x o tempo por 0,01pp."""
    assert R._ORCAMENTO[4] <= 2000, "turn orçado além do platô medido"
    assert R._ORCAMENTO[3] <= 2000, "flop orçado além do platô medido"


def test_sem_pedido_explicito_usa_o_orcamento_da_street():
    R._CACHE.clear()
    r = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop")
    assert r["convergencia"]["iteracoes"] > 400, (
        "continuou nas 400 iterações antigas")


def test_quem_pede_um_numero_manda_nele():
    """O orçamento é padrão, não prisão: quem chama pode pedir menos."""
    R._CACHE.clear()
    r = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop", iterations=200)
    assert r["convergencia"]["iteracoes"] == 200


# ---- teto de relógio -------------------------------------------------------

def test_o_teto_de_relogio_corta_antes_de_estourar_a_paciencia():
    """Com teto de 1s o solver tem que parar MUITO antes das 50.000."""
    R._CACHE.clear()
    t = time.monotonic()
    r = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop",
                      iterations=50000, teto_segundos=1.0)
    gasto = time.monotonic() - t
    assert gasto < 12.0, f"ignorou o teto de relógio: {gasto:.1f}s"
    assert r["convergencia"]["iteracoes"] < 50000, (
        "disse ter feito as 50.000 que o relógio não deixou fazer")


def test_o_corte_por_tempo_se_declara():
    R._CACHE.clear()
    r = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop",
                      iterations=50000, teto_segundos=1.0)
    assert r["convergencia"].get("cortado_por_tempo") is True
    assert "tempo" in r["nota"].lower()


def test_solve_que_cabe_no_tempo_nao_se_diz_cortado():
    R._CACHE.clear()
    r = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop",
                      iterations=200, teto_segundos=600.0)
    assert not r["convergencia"].get("cortado_por_tempo")
    assert "cortad" not in r["nota"].lower()


def test_o_corte_por_tempo_ainda_mede_convergencia():
    """Parar cedo não pode virar resposta SEM medida — é justamente quando a
    medida importa mais."""
    R._CACHE.clear()
    r = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop",
                      iterations=50000, teto_segundos=1.0)
    conv = r["convergencia"]
    assert conv["desvio_medio_pp"] >= 0
    assert conv["desvio_max_pp"] >= conv["desvio_medio_pp"]


def test_o_teto_tambem_entra_na_chave_do_cache():
    """Mesmo motivo do `iterations`: dois tetos são dois resultados."""
    R._CACHE.clear()
    R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop", iterations=200,
                  teto_segundos=1.0)
    R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop", iterations=200,
                  teto_segundos=600.0)
    assert len(R._CACHE) == 2
