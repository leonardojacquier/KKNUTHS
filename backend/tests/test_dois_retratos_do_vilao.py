"""Os dois retratos do vilão, as cartas prováveis e a figura centrada NELE.

O dono confirmou o defeito e pediu as três coisas de uma vez:

1. A figura do dossiê mostrava "VOCÊ" e as cartas do HERÓI numa mão que era
   do vilão — "ele mostra o que eu vejo e não o que o vilão V". O header
   agora é do vilão; o herói vira uma linha de contexto.
2. "Prováveis cartas que ele tinha": CONTAGEM de combos de um range SUPOSTO
   (top-PFR% medido), com a suposição escrita na frase — nunca "X% de chance".
3. "Considerando showdown o perfil é um; pela linha o perfil é Y": dois
   retratos com os vieses declarados, e a DIVERGÊNCIA só quando Wilson
   sustenta.
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

BOARD_PAREADO = ["8d", "Qs", "6h", "9s", "9h"]     # o board da mão real
BOARD_DRAW = ["Qh", "7h", "2d", "9c", "3s"]


def _mao(hid, mostra=None, board=None, ate_river=False):
    """v1 abre o pré e c-beta o flop; com `mostra` vai até o showdown."""
    board = board or BOARD_DRAW
    longa = bool(mostra) or ate_river
    streets = [
        Street(name=StreetName.PREFLOP, actions=[
            Action(actor="Hero", type=ActionType.FOLD),
            Action(actor="v1", type=ActionType.RAISE, amount=250,
                   to_amount=250),
            Action(actor="outro", type=ActionType.CALL, amount=250)]),
        Street(name=StreetName.FLOP, board=board[:3], actions=[
            Action(actor="outro", type=ActionType.CHECK),
            Action(actor="v1", type=ActionType.BET, amount=300),
            Action(actor="outro",
                   type=ActionType.CALL if longa else ActionType.FOLD,
                   amount=300 if longa else 0)])]
    if longa:
        streets += [
            Street(name=StreetName.TURN, actions=[
                Action(actor="outro", type=ActionType.CHECK),
                Action(actor="v1", type=ActionType.BET, amount=800),
                Action(actor="outro", type=ActionType.CALL, amount=800)]),
            Street(name=StreetName.RIVER, actions=[
                Action(actor="outro", type=ActionType.CHECK),
                Action(actor="v1", type=ActionType.BET, amount=2000),
                Action(actor="outro", type=ActionType.CALL, amount=2000)])]
    return CanonicalHand(
        hand_id=hid, site="GGPoker", tournament_id="t1", hero="Hero",
        stakes=Stakes(big_blind=100, small_blind=50),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=12000, position="BTN"),
                 PlayerSeat(seat=3, name="outro", stack=5000)],
        hero_cards=["7s", "2c"], final_board=board,
        shown_cards=({"v1": mostra} if mostra else {}),
        collected=({} if mostra else {"v1": 900.0}),
        streets=streets)


# ---- a figura é do VILÃO ----------------------------------------------------

def test_o_spec_da_figura_e_do_vilao_e_nao_do_heroi():
    """O defeito que o dono vetou: as cartas grandes eram as DELE (herói)."""
    from app.analysis.dossie_html import espec_do_vilao

    spec = espec_do_vilao(_mao("h1"), "v1", "Mão #1 — v1", "")
    assert spec["hero_cards"] == [], \
        "sem showdown não há carta do vilão para mostrar"
    assert spec["cards_note"] == "cartas não vistas"
    assert spec["subtitle"].startswith("v1")
    assert "VOCÊ" not in spec["subtitle"]
    assert "BTN" in spec["subtitle"] and "120bb" in spec["subtitle"]
    assert "blinds 50/100" in spec["subtitle"]


def test_com_showdown_as_cartas_do_header_sao_as_DELE():
    from app.analysis.dossie_html import espec_do_vilao

    spec = espec_do_vilao(_mao("h1", mostra=["Qs", "Qd"]), "v1", "t", "n")
    assert spec["hero_cards"] == ["Qs", "Qd"]
    assert spec["cards_note"] == ""


def test_o_heroi_vira_linha_de_contexto():
    """"você: 7♠ 2♣ — largou no pré" — informação, não protagonista."""
    from app.analysis.dossie_html import espec_do_vilao

    tag = espec_do_vilao(_mao("h1"), "v1", "t", "")["tagline"]
    assert tag.startswith("você:")
    assert "7♠" in tag and "2♣" in tag
    assert "largou no pré" in tag


def test_a_figura_renderiza_com_o_header_do_vilao():
    """subtitle/tagline/cards_note atravessam o PIL sem quebrar."""
    from app.analysis.dossie_html import espec_do_vilao
    from app.analysis.hand_figure import render_hand_strip

    png = render_hand_strip(espec_do_vilao(_mao("h1"), "v1", "t", ""))
    assert png[:4] == b"\x89PNG"


# ---- as cartas prováveis (combos) -------------------------------------------

def test_ranking_tem_169_maos_unicas_e_ordem_sana():
    from app.analysis.combos import RANKING_169

    assert len(RANKING_169) == 169
    assert len(set(RANKING_169)) == 169
    assert RANKING_169[0] == "AA"
    assert RANKING_169.index("AKs") < RANKING_169.index("AQs")
    assert RANKING_169[-1] == "32o"


def test_range_top_corta_por_peso_de_combos():
    """AA+KK são 12 dos 1326 combos: pct exato inclui, um fio a menos não."""
    from app.analysis.combos import range_top

    assert range_top(0.0) == []
    assert range_top(12 / 1326) == ["AA", "KK"]
    assert range_top(11 / 1326) == ["AA"]
    # fronteira EXATA (1.0*1326 é float exato): a última mão entra —
    # um `>=` no corte deixaria 32o de fora e o range de 100% com 168 mãos
    assert len(range_top(1.0)) == 169


def test_pesos_dos_combos():
    from app.analysis.combos import _combos_da_mao

    assert len(_combos_da_mao("AA")) == 6
    assert len(_combos_da_mao("AKs")) == 4
    assert len(_combos_da_mao("AKo")) == 12


@pytest.mark.parametrize("combo,esperado", [
    (("5s", "5c"), "fraca"),    # "dois pares" com o par do BOARD = underpair
    (("As", "Ac"), "forte"),    # overpair
    (("Ah", "Qd"), "media"),    # par topo apoiado no board pareado
    (("Tc", "9c"), "forte"),    # trinca com o 9 do board
    (("Jh", "Th"), "forte"),    # straight Q-J-T-9-8
    (("As", "Ks"), "fraca"),    # ar
])
def test_classificacao_relativa_ao_board_pareado(combo, esperado):
    """A régua absoluta mentia aqui: em board 99, até 55 virava 'dois
    pares'. Valor é o que é DELE, não o que o board dá para todo mundo."""
    from app.analysis.combos import _classificar

    assert _classificar(combo, BOARD_PAREADO) == esperado


def test_draw_morto_flush_e_oesd():
    from app.analysis.combos import _e_draw

    assert _e_draw(("Ah", "Kh"), BOARD_DRAW)          # 2 copas no flop, não veio
    assert _e_draw(("Jc", "Td"), ["9h", "8d", "2s", "2c", "Ah"])  # OESD JT98
    assert not _e_draw(("Ah", "Kd"), BOARD_DRAW)      # sem draw nenhum


def test_contagem_soma_e_bloqueadores():
    from app.analysis.combos import contar

    c = contar(0.225, BOARD_PAREADO, ["2h", "7s"], "PFR 22%, 41 mãos")
    assert c.valor + c.marginal + c.draws + c.ar == c.total
    assert "PFR 22%, 41 mãos" in c.suposicao
    assert "top 22%" in c.suposicao
    # bloqueador morde: um Ás fora do baralho mata 3 dos 6 combos de AA
    com_as = contar(12 / 1326, BOARD_DRAW, [], "x")
    sem_as = contar(12 / 1326, BOARD_DRAW, ["As"], "x")
    assert com_as.total == 12 and sem_as.total == 9


def test_board_incompleto_marca_draws_vivos():
    from app.analysis.combos import contar, linhas

    c5 = contar(0.5, BOARD_DRAW, [], "x")
    c3 = contar(0.5, BOARD_DRAW[:3], [], "x")
    assert not c5.draws_vivos and c3.draws_vivos
    assert any("não bateram" in l for l in linhas(c5))
    assert any("ainda vivos" in l for l in linhas(c3))


def test_sem_board_ou_sem_range_nao_ha_contagem():
    from app.analysis.combos import contar

    assert contar(0.2, [], [], "x") is None
    assert contar(0.0, BOARD_DRAW, [], "x") is None


# ---- os dois retratos -------------------------------------------------------

def test_retrato_A_rotulos():
    from app.analysis.dossie import montar as montar_dossie
    from app.analysis.perfil_duplo import perfil_showdown

    honesto = perfil_showdown(montar_dossie(
        [_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(3)], "v1"))
    assert honesto.rotulo == "honesto no que mostrou"
    assert (honesto.n, honesto.valor, honesto.blefes) == (3, 3, 0)

    curto = perfil_showdown(montar_dossie(
        [_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(2)], "v1"))
    assert curto.rotulo == "amostra curta", "2 < MINIMO_SHOWDOWN"

    misto = perfil_showdown(montar_dossie(
        [_mao("a", mostra=["Qs", "Qd"]), _mao("b", mostra=["Qs", "Qd"]),
         _mao("c", mostra=["5s", "4c"])], "v1"))
    assert misto.rotulo == "misto no que mostrou"
    assert misto.blefes == 1


def test_retrato_B_conta_a_linha_toda():
    from app.analysis.perfil_duplo import perfil_linha

    hands = ([_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(3)]
             + [_mao(f"e{i}") for i in range(9)])
    b = perfil_linha(hands, "v1")
    assert b.agressoes == 12, "showdowns INCLUSOS — A é subconjunto de B"
    assert b.sem_showdown == 9
    assert b.levou_sem_mostrar == 9
    assert (b.cbet_k, b.cbet_n) == (12, 12)
    assert (b.barrela_k, b.barrela_n) == (3, 3)


def test_fracao_media_e_do_pote_DAQUELE_momento():
    """300 no pote de 500 do flop = 60% — não uma fração do pote final."""
    from app.analysis.perfil_duplo import perfil_linha

    b = perfil_linha([_mao("s1", mostra=["Qs", "Qd"])], "v1")
    assert b.fracao_media["flop"] == 0.6
    assert b.fracao_media["turn"] == 0.73      # 800/1100
    assert b.fracao_media["river"] == 0.74     # 2000/2700


def test_rotulo_do_retrato_B_exige_wilson():
    """9 escuras em 12 (75%) não sustentam 'agride e não mostra' — o piso
    de Wilson fica abaixo de 0.5. Em 20 de 22 sustenta."""
    from app.analysis.perfil_duplo import perfil_linha

    fraco = perfil_linha([_mao(f"s{i}", mostra=["Qs", "Qd"])
                          for i in range(3)]
                         + [_mao(f"e{i}") for i in range(9)], "v1")
    assert fraco.rotulo == ""
    forte = perfil_linha([_mao(f"s{i}", mostra=["Qs", "Qd"])
                          for i in range(2)]
                         + [_mao(f"e{i}") for i in range(20)], "v1")
    assert forte.rotulo == "agride e não mostra"


def test_divergencia_so_sai_sustentada_e_diz_a_frase_certa():
    from app.analysis.dossie import montar as montar_dossie
    from app.analysis.perfil_duplo import montar

    # honesto no showdown + 20/23 às escuras: a divergência É o produto
    hands = ([_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(3)]
             + [_mao(f"e{i}") for i in range(20)])
    p = montar(hands, "v1", montar_dossie(hands, "v1"))
    assert p.divergencia is not None
    assert "parece honesto" in p.divergencia
    assert "sem showdown" in p.divergencia
    assert "%" not in p.divergencia, "divergência é contagem, nunca taxa"

    # amostra que não sustenta: sem divergência, não meia-divergência
    poucas = ([_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(3)]
              + [_mao(f"e{i}") for i in range(9)])
    assert montar(poucas, "v1", montar_dossie(poucas, "v1")).divergencia \
        is None


def test_os_retratos_estao_no_documento_com_vieses_declarados():
    from app.analysis.dossie_html import build_dossie_html

    hands = ([_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(3)]
             + [_mao(f"e{i}") for i in range(20)])
    html = build_dossie_html("v1", hands, {"site": "GGPoker"})
    assert "O mesmo jogador, dois retratos" in html
    assert "Retrato A — showdown" in html
    assert "Retrato B — linha" in html
    assert "amostra das mãos PAGAS" in html, "o viés do showdown, declarado"
    assert "Onde os retratos divergem" in html


def test_as_cartas_provaveis_estao_nas_escuras_do_documento():
    """23 mãos ≥ MINIMO_PARA_LINHA: o PFR medido existe e a contagem sai,
    com a suposição na frase."""
    from app.analysis.dossie_html import build_dossie_html

    hands = ([_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(3)]
             + [_mao(f"e{i}") for i in range(20)])
    html = build_dossie_html("v1", hands, {"site": "GGPoker"})
    assert "Cartas prováveis" in html
    assert "supondo que ele entra com o top" in html
    assert "PFR medido" in html
    assert "combos possíveis neste board" in html


def test_sem_amostra_de_mesa_nao_ha_cartas_provaveis():
    """Abaixo de 20 mãos não há PFR medido — e sem medida não há suposição
    disfarçada de padrão."""
    from app.analysis.dossie_html import build_dossie_html

    html = build_dossie_html("v1", [_mao(f"e{i}") for i in range(5)],
                             {"site": "GGPoker"})
    assert "Cartas prováveis" not in html
