"""A mão INTEIRA e a LEITURA nas escuras do dossiê.

O dono pediu duas coisas com todas as letras, e a recusa anterior tinha
jogado fora a legítima junto com a ilegítima:

  1. a mão completa, rua a rua — a linha resumida escondia o resto da mesa;
  2. "uma projeção do que ele provavelmente tinha, como RECOMENDAÇÃO".

O que continua proibido é a TAXA ("blefa X%", que exigiria showdown — e
showdown só existe quando alguém paga). O que entrou é a LEITURA: pende
para blefe/valor/polarizada, com as razões citadas uma a uma, rotulada
"leitura de coach, não medição". Estes testes prendem a fronteira: leitura
presente, percentual ausente.
"""
from __future__ import annotations

import pytest

from app.analysis.leitura_vilao import ler_linha
from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)

BOARD_DRAW_PERDIDO = ["Qh", "7h", "2d", "9c", "3s"]   # duas copas que não vieram


# ---- a leitura --------------------------------------------------------------

def test_draw_perdido_e_perfil_solto_pendem_para_blefe():
    lt = ler_linha(("o flush draw do flop não bateu",), BOARD_DRAW_PERDIDO,
                   rotulo="solto")
    assert lt.inclinacao == "blefe"
    assert len(lt.razoes) == 2
    assert any("não chegou" in r for r in lt.razoes)
    assert "pague mais leve" in lt.conselho


def test_perfil_passivo_pende_para_valor():
    """Agressão de passivo é honesta — e a razão sai citada."""
    lt = ler_linha((), BOARD_DRAW_PERDIDO[:5], rotulo="passivo")
    assert lt.inclinacao == "valor"
    assert any("costuma ter" in r for r in lt.razoes)
    assert "aguenta showdown" in lt.conselho


def test_o_que_ele_JA_mostrou_pesa():
    """A única evidência que é DELE: mostrou blefe antes -> pende blefe;
    só mostrou valor -> pende valor."""
    blefou = ler_linha((), BOARD_DRAW_PERDIDO, ja_mostrou_blefe=True)
    assert blefou.inclinacao == "blefe"
    honesto = ler_linha((), BOARD_DRAW_PERDIDO, ja_mostrou_valor=True)
    assert honesto.inclinacao == "valor"
    # mostrou os dois: o valor mostrado não anula o blefe mostrado
    ambos = ler_linha((), BOARD_DRAW_PERDIDO, ja_mostrou_blefe=True,
                      ja_mostrou_valor=True)
    assert ambos.inclinacao == "blefe"


def test_sem_evidencia_a_leitura_e_polarizada_e_diz_o_que_fazer():
    lt = ler_linha((), BOARD_DRAW_PERDIDO)
    assert lt.inclinacao == "polarizada"
    assert lt.razoes == ()
    assert "bluff-catcher" in lt.conselho


def test_empate_com_overbet_ganha_o_aviso_do_polarizado():
    lt = ler_linha(("overbet (1.4× pote)",), BOARD_DRAW_PERDIDO)
    assert "ou muito, ou nada" in lt.conselho


def test_a_linha_representa_maos_deste_board():
    lt = ler_linha(("o flush draw do flop não bateu",), BOARD_DRAW_PERDIDO)
    assert "pares de Q para cima" in lt.representa
    assert "♥" in lt.representa, "o naipe do draw perdido tem que estar nomeado"


def test_leitura_nunca_carrega_percentual():
    """A fronteira inteira em um assert: leitura fala em "pende", nunca em
    número de probabilidade."""
    for rotulo in ("", "solto", "passivo", "fechado-passivo"):
        lt = ler_linha(("o flush draw do flop não bateu", "três barris"),
                       BOARD_DRAW_PERDIDO, rotulo=rotulo)
        tudo = " ".join((lt.inclinacao, lt.representa, lt.conselho)
                        + lt.razoes)
        assert "%" not in tudo, tudo


# ---- no documento -----------------------------------------------------------

def _mao_escura(hid="h1", board=None):
    board = board or BOARD_DRAW_PERDIDO
    return CanonicalHand(
        hand_id=hid, site="GGPoker", tournament_id="t1", hero="Hero",
        stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=5000),
                 PlayerSeat(seat=3, name="outro", stack=5000)],
        hero_cards=["7h", "2c"], final_board=board,
        shown_cards={}, collected={"v1": 1900.0},
        streets=[Street(name=StreetName.PREFLOP, actions=[
                     Action(actor="Hero", type=ActionType.FOLD),
                     Action(actor="v1", type=ActionType.RAISE, amount=250,
                            to_amount=250),
                     Action(actor="outro", type=ActionType.CALL, amount=250)]),
                 Street(name=StreetName.FLOP, board=board[:3], actions=[
                     Action(actor="outro", type=ActionType.CHECK),
                     Action(actor="v1", type=ActionType.BET, amount=300),
                     Action(actor="outro", type=ActionType.FOLD)])])


def test_o_dossie_traz_a_mao_INTEIRA_e_a_leitura(monkeypatch):
    import app.analysis.dossie_html as DH
    from app.analysis.dossie_html import build_dossie_html

    # sem imagem, o filme em TEXTO é a mão inteira — o storyboard tem teste
    # próprio; aqui se prende o conteúdo do filme
    monkeypatch.setattr(DH, "_strip", lambda *a, **k: "")
    html = build_dossie_html("v1", [_mao_escura(f"h{i}") for i in range(3)],
                             {"site": "GGPoker", "data": "2026-08-01"})
    assert "*PREFLOP*" in html, "a mão inteira não está no documento"
    assert "aumenta para 2.5bb" in html
    assert "*FLOP*" in html and "Q♥" in html
    # a leitura, rotulada como recomendação
    assert "Leitura: pende para" in html
    assert "leitura de coach, não medição" in html
    assert "A linha representa:" in html
    assert "Recomendação:" in html


def test_a_leitura_do_documento_nao_vira_percentual():
    from app.analysis.dossie_html import build_dossie_html

    html = build_dossie_html("v1", [_mao_escura()], {})
    trecho = html[html.index("Agrediu e ninguém viu"):]
    import re

    # só o texto VISÍVEL: o CSS da imagem tem width:100% e não é prosa
    visivel = re.sub(r"<[^>]*>", " ", trecho)
    percentuais = re.findall(r"\d+\s*%", visivel)
    assert not percentuais, (
        f"percentual dentro da seção das escuras: {percentuais}")


def test_o_dossie_traz_o_STORYBOARD_igual_ao_relatorio():
    """O pedido do dono: as imagens das mãos, como no /relatorio. São PIL —
    custo zero de modelo — e entram nas mostradas E nas escuras."""
    from app.analysis.dossie_html import build_dossie_html

    com_showdown = _mao_escura("sd")
    com_showdown.shown_cards = {"v1": ["Jd", "Th"]}
    maos = [com_showdown] + [_mao_escura(f"e{i}") for i in range(2)]
    html = build_dossie_html("v1", maos, {})
    assert html.count("data:image/png;base64") == 3, (
        "cada mão (mostrada e escura) tem que carregar seu storyboard")


def test_imagem_que_falha_cai_para_o_filme_em_texto(monkeypatch):
    """PIL indisponível ou mão torta: o documento continua, com o filme em
    texto no lugar da imagem — nunca um buraco."""
    import app.analysis.dossie_html as DH
    from app.analysis.dossie_html import build_dossie_html

    monkeypatch.setattr(DH, "_strip", lambda *a, **k: "")
    html = build_dossie_html("v1", [_mao_escura()], {})
    assert "data:image/png" not in html
    assert "*PREFLOP*" in html, "sem imagem E sem filme em texto"


def test_filme_que_falha_nao_derruba_o_documento(monkeypatch):
    """Imagem E filme falhando numa mão torta não matam o dossiê — cai para
    a linha resumida daquela mão."""
    import app.analysis.dossie_html as DH
    import app.bot.processing as P
    from app.analysis.dossie_html import build_dossie_html

    def _explode(h):
        raise RuntimeError("mão torta")

    monkeypatch.setattr(DH, "_strip", lambda *a, **k: "")
    monkeypatch.setattr(P, "_walk_hand", _explode)
    html = build_dossie_html("v1", [_mao_escura()], {})
    assert html and "Agrediu e ninguém viu" in html
    assert "aumenta pré" in html, "nem a linha resumida sobrou"
