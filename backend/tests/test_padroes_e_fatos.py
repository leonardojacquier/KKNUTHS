"""Fatos por mão, padrões ENTRE mãos e a variação do conselho.

A pergunta do dono foi "como melhoramos as análises — precisa por IA?".
Não precisa: o que faltava era (1) extrair fatos que a narrativa deixava na
mesa (check-raise, stack comprometido, textura, posição), (2) cruzar as mãos
entre si ("é a 3ª vez que ele overbeta o river", "este sizing foge da
mediana DELE") e (3) não repetir a mesma frase vinte vezes no documento.
Tudo determinístico, custo zero de modelo — e cada régua com fronteira presa
por teste.
"""
from __future__ import annotations

import pytest

from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)


def _mao_check_raise(hid="cr1", stack_vilao=10000, river_bet=2900.0,
                     mostra=None, board=None):
    """v1 paga o pré, dá CHECK-RAISE no flop e barrela até o river."""
    board = board or ["Qh", "7h", "2d", "9c", "3s"]
    return CanonicalHand(
        hand_id=hid, site="GGPoker", tournament_id="t1", hero="Hero",
        stakes=Stakes(big_blind=100, small_blind=50),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=stack_vilao,
                            position="BB"),
                 PlayerSeat(seat=3, name="outro", stack=8000,
                            position="BTN")],
        hero_cards=["7s", "2c"], final_board=board,
        shown_cards=({"v1": mostra} if mostra else {}),
        collected=({} if mostra else {"v1": 5000.0}),
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                Action(actor="Hero", type=ActionType.FOLD),
                Action(actor="outro", type=ActionType.RAISE, amount=250,
                       to_amount=250),
                Action(actor="v1", type=ActionType.CALL, amount=150)]),
            Street(name=StreetName.FLOP, board=board[:3], actions=[
                Action(actor="v1", type=ActionType.CHECK),
                Action(actor="outro", type=ActionType.BET, amount=300),
                Action(actor="v1", type=ActionType.RAISE, amount=900,
                       to_amount=900),
                Action(actor="outro", type=ActionType.CALL, amount=600)]),
            Street(name=StreetName.TURN, actions=[
                Action(actor="v1", type=ActionType.BET, amount=1200),
                Action(actor="outro", type=ActionType.CALL, amount=1200)]),
            Street(name=StreetName.RIVER, actions=[
                Action(actor="v1", type=ActionType.BET, amount=river_bet),
                Action(actor="outro",
                       type=ActionType.CALL if mostra else ActionType.FOLD,
                       amount=river_bet if mostra else 0)])])


# ---- fatos por mão ----------------------------------------------------------

def test_fatos_check_raise_stack_e_posicao():
    from app.analysis.leitura_vilao import fatos_da_mao

    f = fatos_da_mao(_mao_check_raise(), "v1")
    assert f.check_raise_em == "flop"
    # ele pôs 150+900+1200+2900 = 5150 de um stack de 10000
    assert f.comprometeu == 0.52
    assert f.posicao_no_flop == "fora de posição"
    assert not f.multiway, "só v1 e outro agiram no flop"
    assert not f.acordou_no_river, "ele agrediu desde o flop"


def test_fatos_overbet_river_e_acordou():
    from app.analysis.leitura_vilao import fatos_da_mao

    h = CanonicalHand(
        hand_id="ac1", site="GG", hero="Hero",
        stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=9000)],
        hero_cards=["7s", "2c"],
        final_board=["Qh", "7h", "2d", "9c", "3s"], shown_cards={},
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                Action(actor="v1", type=ActionType.CALL, amount=100),
                Action(actor="Hero", type=ActionType.CHECK)]),
            Street(name=StreetName.FLOP, actions=[
                Action(actor="Hero", type=ActionType.CHECK),
                Action(actor="v1", type=ActionType.CHECK)]),
            Street(name=StreetName.TURN, actions=[
                Action(actor="Hero", type=ActionType.CHECK),
                Action(actor="v1", type=ActionType.CHECK)]),
            Street(name=StreetName.RIVER, actions=[
                Action(actor="Hero", type=ActionType.CHECK),
                Action(actor="v1", type=ActionType.BET, amount=300),
                Action(actor="Hero", type=ActionType.FOLD)])])
    f = fatos_da_mao(h, "v1")
    assert f.acordou_no_river, "check, check, e a aposta só no river"
    assert f.overbet_river, "300 num pote de 200 é overbet"


@pytest.mark.parametrize("flop,esperado", [
    (["Qh", "7h", "2h"], "monotone e seco"),
    (["Qh", "7h", "2d"], "dois naipes e seco"),
    (["9c", "8d", "7s"], "arco-íris e conectado"),
    (["9c", "9d", "2s"], "arco-íris e pareado"),
])
def test_textura_do_flop(flop, esperado):
    from app.analysis.leitura_vilao import _textura

    assert _textura(flop) == esperado


def test_narrativa_diz_check_raise_e_stack_comprometido():
    """check-raise não é um 'aumentou' qualquer — e meio stack no pote é
    fato que muda a leitura."""
    from app.analysis.leitura_vilao import narrar_mao

    frases = narrar_mao(_mao_check_raise(), "v1")
    flop = next(f for f in frases if f.startswith("flop"))
    assert "check-raise:" in flop
    river = next(f for f in frases if f.startswith("river"))
    assert "já comprometeu 52% do stack" in river


def test_narrativa_sem_aviso_abaixo_de_meio_stack():
    """A fronteira é METADE do stack: 45% comprometido ainda não ganha o
    aviso — um limiar mais nervoso viraria alarme em toda mão."""
    from app.analysis.leitura_vilao import narrar_mao

    # 5150 postos num stack de 11500 = 44.8% — logo abaixo da fronteira
    frases = narrar_mao(_mao_check_raise(stack_vilao=11500), "v1")
    assert not any("comprometeu" in f for f in frases)


def test_raise_sem_check_antes_NAO_e_check_raise():
    from app.analysis.leitura_vilao import fatos_da_mao, narrar_mao

    board = ["Qh", "7h", "2d", "9c", "3s"]
    h = CanonicalHand(
        hand_id="r1", site="GG", hero="Hero", stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=90000),
                 PlayerSeat(seat=3, name="outro", stack=8000)],
        hero_cards=["7s", "2c"], final_board=board, shown_cards={},
        collected={"v1": 2000.0},
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                Action(actor="Hero", type=ActionType.FOLD),
                Action(actor="outro", type=ActionType.RAISE, amount=250,
                       to_amount=250),
                Action(actor="v1", type=ActionType.CALL, amount=250)]),
            Street(name=StreetName.FLOP, board=board[:3], actions=[
                Action(actor="outro", type=ActionType.BET, amount=300),
                Action(actor="v1", type=ActionType.RAISE, amount=900,
                       to_amount=900),
                Action(actor="outro", type=ActionType.FOLD)])])
    assert fatos_da_mao(h, "v1").check_raise_em is None
    flop = next(f for f in narrar_mao(h, "v1") if f.startswith("flop"))
    assert "aumentou:" in flop and "check-raise" not in flop


# ---- padrões entre mãos -----------------------------------------------------

def test_padroes_contam_e_mediana_exige_tres():
    from app.analysis.padroes import medir

    p = medir([_mao_check_raise(f"h{i}") for i in range(2)], "v1")
    assert p.check_raises == 2
    assert p.mediana_por_rua == {}, \
        "2 apostas por rua não fazem mediana (MINIMO_PARA_MEDIANA=3)"
    p3 = medir([_mao_check_raise(f"h{i}") for i in range(3)], "v1")
    assert "turn" in p3.mediana_por_rua


def test_padroes_leem_o_resultado_dos_check_raises_mostrados():
    """Check-raise que foi até showdown com dois pares = valor — pela
    LINHA (dossie.ler_mao), nunca pelo resultado."""
    from app.analysis.padroes import medir

    maos = [_mao_check_raise("s1", mostra=["Qs", "9h"]),
            _mao_check_raise("e1"), _mao_check_raise("e2")]
    p = medir(maos, "v1")
    assert p.check_raises == 3
    assert p.check_raises_valor == 1
    assert p.check_raises_blefe == 0


def test_contexto_so_compara_o_que_repete():
    """1 overbet não é padrão; 2+ são. E mão sem overbet não ganha a linha."""
    from app.analysis.leitura_vilao import fatos_da_mao
    from app.analysis.padroes import contexto, medir

    uma = medir([_mao_check_raise("h1", river_bet=6000)], "v1")
    f = fatos_da_mao(_mao_check_raise("h1", river_bet=6000), "v1")
    assert not any("overbetou o river" in c for c in contexto(uma, f))

    tres = medir([_mao_check_raise(f"h{i}", river_bet=6000)
                  for i in range(3)], "v1")
    assert any("overbetou o river 3×" in c for c in contexto(tres, f))


def test_contexto_sizing_fora_da_mediana_DELE():
    """A régua é a mediana DO VILÃO, não uma tabela: 1.1× pote só vira
    comentário porque ELE costuma apostar 0.4×."""
    from app.analysis.leitura_vilao import fatos_da_mao
    from app.analysis.padroes import contexto, medir

    normais = [_mao_check_raise(f"n{i}", river_bet=2000) for i in range(3)]
    grande = _mao_check_raise("g1", river_bet=6000)
    p = medir(normais + [grande], "v1")
    ctx = contexto(p, fatos_da_mao(grande, "v1"))
    assert any("foge do padrão dele" in c and "river" in c for c in ctx)
    # a mão com sizing igual à mediana NÃO ganha comentário de sizing
    ctx_normal = contexto(p, fatos_da_mao(normais[0], "v1"))
    assert not any("foge do padrão" in c for c in ctx_normal)


# ---- a variação do conselho -------------------------------------------------

def test_variacao_muda_a_frase_e_nunca_o_sentido():
    from app.analysis.leitura_vilao import _CONSELHOS, ler_linha

    board = ["Qh", "7h", "2d", "9c", "3s"]
    zero = ler_linha((), board, rotulo="passivo", variacao=0)
    um = ler_linha((), board, rotulo="passivo", variacao=1)
    assert zero.inclinacao == um.inclinacao == "valor"
    assert zero.conselho != um.conselho
    assert zero.conselho == _CONSELHOS["valor"][0], \
        "variação 0 é o texto original — nada que o cite quebra"


def test_o_documento_usa_padroes_e_varia_o_conselho():
    from app.analysis.dossie_html import build_dossie_html

    maos = [_mao_check_raise(f"h{i}", river_bet=6000) for i in range(3)]
    html = build_dossie_html("v1", maos, {"site": "GGPoker"})
    assert "📊" in html
    assert "overbetou o river 3×" in html
    assert "check-raise 3×" in html
    # 3 escuras iguais: as leituras saem com frases DIFERENTES
    from app.analysis.leitura_vilao import _CONSELHOS

    usadas = [fr for grupo in _CONSELHOS.values() for fr in grupo
              if fr in html]
    assert len(usadas) >= 2, "vinte mãos, uma frase só — era o defeito"
