"""As imagens contam a mesma história que o texto?

Três defeitos que só apareciam olhando o PNG entregue:

1. o azulejo "SUA EQUITY" era VERDE sempre. 20% num pote que pedia 35% saía
   com a mesma cor de 80% num que pedia 20% — e verde na tela quer dizer
   "você está bem". Pior no caso da conta fraca: equity contra mão QUALQUER
   (A♥T♥ dá 43.6% vs aleatória e ~4% contra o range que dá check-raise e
   jam) saía grande e verde, com a ressalva em cinza de 15px embaixo de um
   número de 31px — duas vezes menor que a coisa que ela desmente.
2. no quadro de torneio, a "zona de shove (<10bb)" era desenhada ANTES da
   área sob a curva, que preenche do gráfico até a base. Com stack acima de
   10bb — quase sempre — a linha e o rótulo ficavam por baixo do verde: a
   única referência estratégica do quadro só aparecia quando já não servia.
3. no gráfico de evolução, as datas do eixo X caíam em y=478 e a marca em
   y=474: "06-10" saía por baixo do logo. E a última data, centrada no ponto
   final, vazava pela borda direita.

Os testes olham o PIXEL e a geometria, não o fonte.
"""
from __future__ import annotations

import pytest
from PIL import Image

from app.analysis.hand_figure import BAD, CREAM, MIX, OK, cor_da_equity


# ---- 1) a cor do azulejo de equity é um veredito --------------------------

@pytest.mark.parametrize("eq,need,esperado,porque", [
    (0.72, 0.28, OK, "favorito folgado"),
    (0.20, 0.35, BAD, "atrás do preço — era verde antes"),
    (0.29, 0.28, MIX, "no fio não é vitória"),
    (0.31, 0.28, MIX, "3 pontos de margem ainda é fio"),
    (0.32, 0.28, OK, "acima da margem"),
])
def test_a_cor_sai_da_comparacao_com_o_preco(eq, need, esperado, porque):
    assert cor_da_equity(eq, need) == esperado, porque


def test_equity_vs_mao_qualquer_nunca_e_verde():
    """43.6% vs aleatória parece ótimo e não sustenta veredito nenhum."""
    assert cor_da_equity(0.436, 0.28, fraca=True) == MIX
    assert cor_da_equity(0.90, 0.10, fraca=True) == MIX


def test_sem_preco_na_mesa_a_cor_e_neutra():
    """Sem 'precisa de', não há com o que comparar — pintar de verde é
    inventar um veredito."""
    assert cor_da_equity(0.62, None) == CREAM


def _pixels(png: bytes):
    return Image.open(__import__("io").BytesIO(png)).convert("RGB")


def _tem_cor(img, cor, tol=12, regiao=None) -> int:
    """Quantos pixels batem (aprox.) com a cor. Região = (x0,y0,x1,y1)."""
    px = img.crop(regiao) if regiao else img
    n = 0
    for r, g, b in px.getdata():
        if abs(r - cor[0]) <= tol and abs(g - cor[1]) <= tol \
                and abs(b - cor[2]) <= tol:
            n += 1
    return n


_SPOT = {
    "title": "Treino", "hero_cards": ["Ah", "Td"], "position": "BB",
    "stack_bb": 30,
    "streets": [{"name": "flop", "board": ["9h", "7s", "3d"],
                 "lines": ["Vilão apostou 8bb"], "pot_bb": 12}],
    "verdict": "mista", "verdict_text": "texto", "correct": "Depende",
}


def test_o_numero_atras_do_preco_sai_vermelho_na_imagem():
    """Pixel, não fonte: 20% contra 35% pedido tem que APARECER errado.

    Diferencial de propósito — as duas imagens só diferem na equity, então o
    resto (inclusive o verde do rodapé "DECISÃO CERTA") se cancela. Contar
    verde na imagem inteira mediria o rodapé, não o azulejo.
    """
    from app.analysis.hand_figure import render_hand_strip

    def _render(eq, need):
        return _pixels(render_hand_strip(
            {**_SPOT, "math": {"equity": eq, "need": need,
                               "note": "call precisa de X%"}}))

    atras = _render(0.20, 0.35)
    frente = _render(0.72, 0.28)

    assert _tem_cor(atras, BAD) - _tem_cor(frente, BAD) > 200, \
        "estar atrás do preço não pintou nada de vermelho"
    assert _tem_cor(frente, OK) - _tem_cor(atras, OK) > 200, \
        "estar na frente não pintou nada de verde"


def test_antes_as_duas_pontas_saiam_iguais():
    """Guarda do teste acima: se um dia a cor voltar a ser fixa, os dois
    lados voltam a ter a MESMA contagem e o diferencial vira zero."""
    from app.analysis.hand_figure import render_hand_strip

    fixo = _pixels(render_hand_strip(
        {**_SPOT, "math": {"equity": 0.20, "need": None,
                           "note": "sem preço na mesa"}}))
    # sem preço a cor é neutra: nem verde nem vermelho no azulejo
    assert _tem_cor(fixo, CREAM) > 500, "o número neutro sumiu"


def test_a_ressalva_da_conta_fraca_nao_e_letra_miuda():
    """Ela desmente o número grande — não pode ser 2× menor que ele. Aqui
    isso vira altura: a imagem com ressalva longa PRECISA ser mais alta."""
    from app.analysis.hand_figure import render_hand_strip

    curta = _pixels(render_hand_strip(
        {**_SPOT, "math": {"equity": 0.44, "need": 0.28, "note": "curta"}}))
    longa = _pixels(render_hand_strip(
        {**_SPOT, "math": {"equity": 0.44, "need": 0.28, "fraca": True,
                           "note": "⚠️ 44% é contra mão QUALQUER — ele "
                           "apostou, e quem aposta não aposta com mão "
                           "qualquer. Contra o range dele a equity cai "
                           "muito; o preço de 28% não decide sozinho."}}))
    assert longa.height > curta.height, \
        "a ressalva longa foi espremida no espaço fixo de antes"


# ---- 2) a zona de shove aparece --------------------------------------------

def _torneio(curva):
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      HandFormat, PlayerSeat, Stakes, Street,
                                      StreetName)

    return [CanonicalHand(
        site="Demo", hand_id=f"t{i}", hero="Hero",
        format=HandFormat.TOURNAMENT, tournament_id="T1",
        played_at=f"2026-08-01T{i:02d}:00:00+00:00",
        stakes=Stakes(small_blind=500, big_blind=1000),
        players=[PlayerSeat(seat=1, name="Hero", stack=v * 1000,
                            position="BB", is_hero=True),
                 PlayerSeat(seat=2, name="V", stack=40000, position="BTN")],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="Hero", type=ActionType.POST, amount=1000,
                   post_type="bb"),
            Action(actor="V", type=ActionType.FOLD)])],
        collected={"Hero": 1500}, total_pot=1500)
        for i, v in enumerate(curva)]


def _dentro_do_grafico():
    """Só a moldura da curva. Fora dela mora o '▼ pior mão' em vermelho —
    contar a imagem inteira dava teste verde com a zona apagada (conferido
    por mutação)."""
    from app.analysis import tournament_board as tb

    return (tb.PAD_L, tb.CHART_Y, tb.W - tb.PAD_R, tb.CHART_Y + tb.CHART_H)


def test_a_zona_de_shove_sobrevive_a_area_sob_a_curva():
    """O defeito exato: a área sob a curva pintava por cima da linha de 10bb.
    Com o stack todo acima de 10bb, a zona sumia inteira."""
    from app.analysis.tournament_board import RED, render_tournament_board

    png, _ = render_tournament_board(
        _torneio([50, 52, 48, 55, 60, 44, 38, 42, 35, 30, 33, 28]))
    img = _pixels(png)
    assert _tem_cor(img, RED, tol=10, regiao=_dentro_do_grafico()) > 150, \
        "a linha da zona de shove não chegou à imagem"


def test_torneio_inteiro_curto_tambem_diz_que_e_zona_de_shove():
    """Com teto do eixo ≤10bb a linha ficaria fora da moldura, e o quadro
    não dizia nada — justamente para quem mais precisa da informação."""
    from app.analysis.tournament_board import RED, render_tournament_board

    png, _ = render_tournament_board(_torneio([9, 8, 7, 8, 6, 5, 4, 3]))
    img = _pixels(png)
    assert _tem_cor(img, RED, tol=10, regiao=_dentro_do_grafico()) > 60


# ---- 3) o rodapé do gráfico de evolução ------------------------------------

def test_a_data_do_eixo_nao_divide_espaco_com_a_marca():
    """Invariante de moldura: onde a última linha do eixo X termina tem que
    ser ANTES de onde a marca começa. Era 492 vs 474."""
    from app.analysis import evolution_chart as ec

    bot_y1 = ec.PAD_T + ec.TOP_H + ec.GAP + ec.BOT_H
    fim_das_datas = bot_y1 + 8 + 14      # baseline + altura da fonte 12
    topo_da_marca = ec.H - 26
    assert fim_das_datas <= topo_da_marca, (
        f"as datas terminam em {fim_das_datas} e a marca começa em "
        f"{topo_da_marca}")


def _historia(n=8):
    return [{"vpip": 28 + i, "pfr": 18 + i, "three_bet": 6 + i * 0.4,
             "af": 2.1, "net_bb": (-40 if i % 3 else 60), "hands": 200 * (i + 1),
             "created_at": f"2026-06-{10 + i:02d}T10:00:00+00:00"}
            for i in range(n)]


def test_a_ultima_data_cabe_dentro_da_imagem():
    """Centrada no ponto final, ela vazava pela borda direita ('07-17'
    cortado no meio). O teste olha a coluna de pixels da borda."""
    from app.analysis.evolution_chart import W, render_evolution_png

    img = _pixels(render_evolution_png(_historia()))
    borda = img.crop((W - 3, 0, W, img.height))
    fundo = img.getpixel((2, img.height - 2))
    assert all(p == fundo for p in borda.getdata()), \
        "tem tinta encostando na borda direita — texto cortado"


def test_o_indicador_avulso_tambem_prende_a_data():
    from app.analysis.evolution_chart import render_indicator_png

    png = render_indicator_png(_historia(), "bb")
    img = _pixels(png)
    borda = img.crop((img.width - 3, 0, img.width, img.height))
    fundo = img.getpixel((2, img.height - 2))
    assert all(p == fundo for p in borda.getdata())
