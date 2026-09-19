"""O dossiê do vilão: as mãos que ele mostrou, e o que fez em cada uma.

O `/vilao` entregava frequência — VPIP, PFR, AF, com intervalo. É a resposta
certa para "que tipo de jogador é ele" e a errada para o que o aluno pergunta
de verdade: "o que esse cara aposta no river?".

Medido na base antes de escrever o módulo, dentro de UM torneio (GG
303773218): 28 vilões mostraram mão, 192 showdowns, o maior deles com 26
mãos de cartas abertas. Não é amostra — é prova.

O que estes testes prendem, em ordem de importância:

  1. a classificação é pela LINHA, não pelo resultado. Quem agride o river
     com J-high blefou tendo ganhado ou não. Classificar por resultado é o
     raciocínio que o projeto inteiro combate, e aqui viraria "ele blefa
     muito" toda vez que o vilão perdesse um pote;
  2. não se inventa frequência de blefe: o vilão só mostra quando alguém
     paga, então qualquer % sairia enviesada pelo comportamento de quem
     pagou — e o texto tem que DIZER isso;
  3. vilão que nunca mostrou dá None, não um dossiê vazio com cara de
     dossiê.
"""
from __future__ import annotations

import pytest

from app.analysis.dossie import Dossie, ler_mao, montar, forca, texto
from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)

BOARD = ["Qs", "7h", "2d", "9c", "3s"]
VILAO = "b6b7cbae"          # apelido anonimizado do GG, como vem de verdade


def _rua(nome, acoes):
    return Street(name=nome, actions=[
        Action(actor=a, type=t, amount=v, to_amount=v) for a, t, v in acoes])


def mao(hand_id, cartas, river, flop=None, board=None, mostra=True):
    flop = flop or [("Hero", ActionType.CHECK, 0), (VILAO, ActionType.BET, 300),
                    ("Hero", ActionType.CALL, 300)]
    return CanonicalHand(
        hand_id=hand_id, site="GGPoker", stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, position="BB"),
                 PlayerSeat(seat=2, name=VILAO, stack=5000, position="BTN")],
        hero_cards=["Ah", "Kd"],
        final_board=BOARD if board is None else board,
        shown_cards=({VILAO: cartas} if mostra else {}),
        streets=[_rua(StreetName.PREFLOP,
                      [(VILAO, ActionType.RAISE, 200),
                       ("Hero", ActionType.CALL, 200)]),
                 _rua(StreetName.FLOP, flop),
                 _rua(StreetName.RIVER, river)])


APOSTA_RIVER = [("Hero", ActionType.CHECK, 0), (VILAO, ActionType.BET, 900),
                ("Hero", ActionType.CALL, 900)]
PAGOU_RIVER = [("Hero", ActionType.BET, 900), (VILAO, ActionType.CALL, 900)]


# ---- 1) a régua de força ----------------------------------------------------

@pytest.mark.parametrize("cartas,esperado", [
    (["Jd", "Th"], "fraca"),     # carta alta
    (["7c", "6d"], "fraca"),     # par de 7 num board com Q — par de baixo
    (["Qc", "Td"], "media"),     # par topo
    (["Qh", "9d"], "forte"),     # dois pares
    (["9s", "9h"], "forte"),     # trinca
])
def test_a_fronteira_do_valor_e_o_par_TOPO(cartas, esperado):
    """Par de baixo apostado contra quem pagou é blefe (ou valor tão fino que
    dá no mesmo para decidir). Par topo é valor fino. Dois pares é valor."""
    assert forca(cartas, BOARD) == esperado


def test_forca_sem_board_completo_nao_chuta():
    assert forca(["Jd", "Th"], ["Qs", "7h"]) == "desconhecida"
    assert forca([], BOARD) == "desconhecida"


# ---- 2) a classificação é pela LINHA ---------------------------------------

@pytest.mark.parametrize("cartas,papel", [
    (["Jd", "Th"], "blefe"), (["Qc", "Td"], "valor fino"),
    (["Qh", "9d"], "valor"),
])
def test_quem_agride_o_river_e_lido_pelo_que_TINHA(cartas, papel):
    assert ler_mao(mao("h1", cartas, APOSTA_RIVER), VILAO).papel == papel


def test_o_RESULTADO_da_mao_nao_muda_a_leitura():
    """O caso que importa: mesmo blefe, uma vez perdendo e outra ganhando.

    Se a classificação olhasse o resultado, a mesma jogada apareceria como
    "blefe" quando ele perde e como outra coisa quando ganha — e o dossiê
    viraria um espelho da sorte dele."""
    perdeu = mao("h-perdeu", ["Jd", "Th"], APOSTA_RIVER)
    ganhou = mao("h-ganhou", ["Jd", "Th"], APOSTA_RIVER)
    ganhou.collected = {VILAO: 2400.0}
    perdeu.collected = {"Hero": 2400.0}
    assert ler_mao(perdeu, VILAO).papel == ler_mao(ganhou, VILAO).papel == "blefe"


def test_quem_so_pagou_nao_vira_apostador():
    m = ler_mao(mao("h2", ["7c", "6d"], PAGOU_RIVER), VILAO)
    assert m.papel == "pagou"
    assert "paga river" in m.linha


def test_a_linha_inteira_aparece_e_o_blind_nao_conta_como_acao():
    """Postar blind é obrigação, não jogada — e poluiria toda linha."""
    m = mao("h3", ["Jd", "Th"], APOSTA_RIVER)
    m.streets[0].actions.insert(0, Action(actor=VILAO, type=ActionType.POST,
                                          amount=100, post_type="bb"))
    lida = ler_mao(m, VILAO)
    assert lida.linha == "aumenta pré · aposta flop · aposta river"
    assert lida.linha.count("·") == 2, (
        f"o blind entrou como jogada: {lida.linha}")


def test_agressao_que_nao_foi_na_ultima_rua_nao_vira_blefe_do_river():
    """Ele apostou o flop e passou o river. Chamar isso de "blefe no river"
    seria inventar uma jogada que não aconteceu."""
    m = ler_mao(mao("h4", ["Jd", "Th"],
                    [("Hero", ActionType.BET, 900),
                     (VILAO, ActionType.CALL, 900)]), VILAO)
    assert m.papel == "pagou"
    assert m.rua == "flop"


# ---- 3) o que NÃO se afirma -------------------------------------------------

def test_o_texto_avisa_do_vies_do_showdown():
    """O vilão só mostra quando alguém paga. A mão em que ele blefou e todos
    foldaram não está no dado — então "ele blefa X%" seria número enviesado
    com cara de medida."""
    t = texto(montar([mao("h1", ["Jd", "Th"], APOSTA_RIVER)], VILAO))
    assert "só mostra quando alguém paga" in t
    assert "%" not in t, "apareceu frequência num dado que não a sustenta"


def test_vilao_que_nunca_mostrou_da_NADA():
    sem = [mao("h1", ["Jd", "Th"], APOSTA_RIVER, mostra=False)]
    assert montar(sem, VILAO) is None
    assert montar([], VILAO) is None
    assert montar(sem, "outro-nome") is None


def test_mao_de_outro_vilao_nao_entra_no_dossie():
    m = mao("h1", ["Jd", "Th"], APOSTA_RIVER)
    m.shown_cards = {"outro": ["As", "Ad"], VILAO: ["Jd", "Th"]}
    d = montar([m], VILAO)
    assert d.showdowns == 1 and d.blefes[0].cartas == ("Jd", "Th")


# ---- 4) o dossiê montado ----------------------------------------------------

def test_o_dossie_separa_os_papeis_e_conta_certo():
    maos = [mao("b1", ["Jd", "Th"], APOSTA_RIVER),
            mao("b2", ["8d", "6h"], APOSTA_RIVER),
            mao("v1", ["Qh", "9d"], APOSTA_RIVER),
            mao("v2", ["Qc", "Td"], APOSTA_RIVER),
            mao("p1", ["7c", "6d"], PAGOU_RIVER)]
    d = montar(maos, VILAO)
    assert d.showdowns == 5
    assert len(d.blefes) == 2 and len(d.valor) == 2 and len(d.pagou) == 1
    t = texto(d)
    assert "Jd Th" in t and "dois pares" in t
    assert "2 mão" not in t.split("\n")[0], "cabeçalho conta showdowns, não blefes"
    assert "5 mão(s) que você VIU" in t


def test_o_texto_corta_a_lista_mas_diz_quantas_ficaram():
    """26 showdowns num torneio é comum. Cortar sem avisar dá a impressão de
    que só houve 4."""
    maos = [mao(f"b{i}", ["Jd", "Th"], APOSTA_RIVER) for i in range(9)]
    t = texto(montar(maos, VILAO), limite=4)
    assert "e mais 5" in t


# ---- 5) a ligação -----------------------------------------------------------

def test_o_vilao_entrega_o_dossie_junto_da_frequencia(monkeypatch):
    """Módulo que ninguém chama não existe: o dossiê tem que sair NO comando."""
    import app.bot.processing as P

    maos = [mao("b1", ["Jd", "Th"], APOSTA_RIVER),
            mao("v1", ["Qh", "9d"], APOSTA_RIVER)]
    monkeypatch.setattr(P, "_user_hands", lambda *a, **k: maos)

    saida = P.villain_report(7, VILAO)
    assert "VPIP" in saida, "a frequência sumiu"
    assert "que você VIU as cartas" in saida, "o dossiê não chegou ao aluno"
    assert "Jd Th" in saida
