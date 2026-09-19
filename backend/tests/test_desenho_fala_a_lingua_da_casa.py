"""O DESENHO não passa pelo corretor de termos — então tem que já nascer certo.

Caso real (07/08): o filme da mão escreveu "full house (7 cheio de 2)". Esse
calque de 'sevens full of twos' está PROIBIDO em TERMOS_REGRA desde antes, e
o corretor (`corrigir`) o reescreve automaticamente... no texto do MODELO. O
filme é renderizado direto no PIL e nunca passou por ele. Resultado: a camada
que sempre acerta os fatos era a única falando a língua errada — e o dono
reclamou de um termo que ele já tinha mandado tirar.

A invariante aqui é a defesa que dura: rodar o corretor na saída de
describe_hand tem que ser NO-OP. Se alguém escrever um calque novo nela, o
próprio corretor do projeto denuncia, sem precisar de lista nova.
"""
from __future__ import annotations

import pytest

from app.agent.termos import corrigir
from app.analysis.equity import describe_hand

# uma mão de cada categoria, do straight flush ao high card
CASOS = [
    (["9h", "8h"], ["7h", "6h", "5h", "2c", "3d"], "straight flush"),
    (["7s", "7d"], ["7c", "7h", "2c", "9d", "Jh"], "quadra"),
    (["As", "7s"], ["2c", "7c", "7h", "Ac", "Th"], "full"),
    (["Ah", "5h"], ["2h", "9h", "Kh", "3c", "7d"], "flush"),
    (["9c", "8d"], ["7h", "6s", "5c", "2d", "Kh"], "straight"),
    (["Qc", "Qd"], ["Qh", "2c", "7d", "9s", "Jh"], "trinca"),
    (["Ks", "Jd"], ["Kh", "Jc", "4d", "8s", "2h"], "dois pares"),
    (["Ah", "Kd"], ["As", "7c", "2d", "9s", "4h"], "par"),
    (["Ah", "Qd"], ["7s", "2c", "9d", "4h", "Jc"], "high"),
]


@pytest.mark.parametrize("hole,board,esperado", CASOS)
def test_o_corretor_nao_tem_o_que_consertar(hole, board, esperado):
    """A invariante: o que o desenho escreve já está no padrão da casa."""
    txt = describe_hand(hole, board)
    assert txt and esperado in txt
    assert corrigir(txt) == txt, (
        f"o corretor reescreveu '{txt}' -> '{corrigir(txt)}': o desenho está "
        "falando um termo que o projeto proíbe")


def test_os_tres_calques_que_estavam_no_desenho():
    """Os que o dono flagrou, um a um."""
    # 1) "7 cheio de 2" -> full de 7 com 2, e a TRINCA explícita. Foi num
    #    full CONTRA full que a leitura se perdeu: os dois têm trinca de 7
    #    (duas na mesa, uma de cada) e o que decide é o PAR que acompanha.
    board = ["2c", "7c", "7h", "Ac", "Th"]
    heroi = describe_hand(["As", "7s"], board)
    vilao = describe_hand(["2d", "7d"], board)
    assert heroi == "full de 7 com A (trinca de 7)"
    assert vilao == "full de 7 com 2 (trinca de 7)"
    assert "cheio de" not in heroi and "cheio de" not in vilao

    # o par de A ganha do par de 2 — e é isso que o nome agora deixa ver
    from app.analysis.equity import equity_vs_hands
    assert equity_vs_hands(["As", "7s"], [["2d", "7d"]], board) == 1.0

    # 2) "sequência" -> straight
    seq = describe_hand(["9c", "8d"], ["7h", "6s", "5c", "2d", "Kh"])
    assert "straight" in seq and "sequência" not in seq

    # 3) "carta alta" -> high card
    alta = describe_hand(["Ah", "Qd"], ["7s", "2c", "9d", "4h", "Jc"])
    assert alta == "A high" and "carta alta" not in alta


def test_o_filme_e_a_historia_usam_a_mesma_frase():
    """As duas camadas determinísticas saem de describe_hand — se uma mudar
    de língua sem a outra, o aluno vê dois nomes para o mesmo showdown."""
    from app.analysis.historia import historia_do_resultado
    from tests.test_historia_do_resultado import _mao_do_full
    from app.bot.processing import film_bands

    h = _mao_do_full()
    hist = historia_do_resultado(h)
    banda = [b for b in film_bands(h) if b.get("name") == "Resultado"][0]

    assert hist["sua_mao_final"] == "full de 7 com A (trinca de 7)"
    assert hist["mao_final_dos_viloes"]["arisn"] == \
        "full de 7 com 2 (trinca de 7)"
    assert any(hist["sua_mao_final"] in l for l in banda["lines"])
    revelado = {r["who"]: r["desc"] for r in banda["reveals"]}
    assert revelado["arisn (BTN) mostra"] == \
        hist["mao_final_dos_viloes"]["arisn"]
    assert corrigir(hist["sua_mao_final"]) == hist["sua_mao_final"]
