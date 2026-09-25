"""Pedir mais precisão tem que ENTREGAR mais precisão.

A chave do `_CACHE` do `solve_river` era
`board|oop|ip|pot|stack|player` — sem `iterations`. Quem resolvesse um spot a
400 iterações e depois pedisse 6.400 recebia o resultado velho **em silêncio**:
o parâmetro existia, era aceito, e não fazia nada.

É o pior formato de defeito que existe neste projeto — o número sai com cara
de mais exato sem ser. Vale a mesma regra do METODO: não ter é melhor que ter
errado.
"""
from __future__ import annotations

from app.analysis import river_solver as R

_BOARD = ["Ah", "Kd", "7c", "2s", "9h"]
_OOP = "AA,KK,77,22,99,AK,AQ,AJ,KQ,QJ,JT,T9,98,87,76,65"
_IP = "AK,AQ,AJ,ATs,KQ,KJs,QJs,JTs,T9s,99,77,22,A5s,A4s"


def _freqs(r: dict) -> dict:
    return {k: v["freq_pct"] for k, v in r["actions"].items()}


def test_mais_iteracoes_nao_devolve_o_resultado_velho():
    R._CACHE.clear()
    baixo = _freqs(R.solve_river(_BOARD, _OOP, _IP, 20.0, 60.0, "oop",
                                 iterations=200))
    alto = _freqs(R.solve_river(_BOARD, _OOP, _IP, 20.0, 60.0, "oop",
                                iterations=4000))
    assert baixo != alto, (
        "200 e 4.000 iterações devolveram o MESMO resultado — o cache "
        "ignorou o pedido de precisão")


def test_a_chave_do_cache_carrega_as_iteracoes():
    """Mesmo spot em duas precisões = duas entradas, não uma."""
    R._CACHE.clear()
    R.solve_river(_BOARD, _OOP, _IP, 20.0, 60.0, "oop", iterations=200)
    assert len(R._CACHE) == 1
    R.solve_river(_BOARD, _OOP, _IP, 20.0, 60.0, "oop", iterations=4000)
    assert len(R._CACHE) == 2, (
        "a segunda precisão sobrescreveu ou reusou a primeira")


def test_repetir_o_mesmo_pedido_continua_batendo_no_cache():
    """O conserto não pode ter matado o cache: o solver é caro."""
    R._CACHE.clear()
    a = R.solve_river(_BOARD, _OOP, _IP, 20.0, 60.0, "oop", iterations=200)
    b = R.solve_river(_BOARD, _OOP, _IP, 20.0, 60.0, "oop", iterations=200)
    assert a is b, "mesmo pedido resolveu duas vezes — o cache parou de valer"
    assert len(R._CACHE) == 1
