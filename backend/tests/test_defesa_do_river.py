"""Sem showdown não há "provavelmente blefou" — há a SUA defesa, exata.

O pedido era marcar onde o vilão "provavelmente blefou" nas mãos sem
showdown. Medido na base antes de escrever o módulo: nas 39 mãos em que um
vilão apostou o river e FOI PAGO, mão fraca em 2 (5% ± 7pp). Mas essas 39
são as mãos em que alguém pagou; as 88 escuras são as em que todos largaram.
A seleção incide exatamente sobre a coisa a estimar — paga-se quando se
desconfia — então qualquer taxa transportada dali seria invenção com cara
de medida.

O que estes testes prendem:

  1. a conta do teorema: aposta `b` em pote `p` lucra como blefe se o herói
     folda mais que b/(p+b). Com 0,65× pote, 39% — NÃO 61% (61% é a defesa
     mínima; confundir os dois inverte o veredito);
  2. o veredito de overfold sai pelo PISO de Wilson, não pela média — média
     alta com intervalo largo é relato, não acusação;
  3. o texto das mãos escuras carrega fatos (linha, tamanho, sua resposta)
     e NENHUMA probabilidade;
  4. pote antes do river: raise conta "até" (to_amount), não "mais".
"""
from __future__ import annotations

import pytest

from app.analysis.defesa import (
    MINIMO_PARA_VEREDITO,
    _pote_antes_do_river,
    _wilson_lo,
    aposta_enfrentada,
    medir,
    nao_vistas,
    texto,
)
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


def mao(hid, resposta, mostra=False, bet=650.0, vilao="v1"):
    """Pré 200+200, flop 300+300 => pote 1000 no river. Vilão aposta `bet`."""
    riv = [Action(actor="Hero", type=ActionType.CHECK),
           Action(actor=vilao, type=ActionType.BET, amount=bet)]
    if resposta is not None:
        riv.append(Action(actor="Hero", type=resposta,
                          amount=bet if resposta == ActionType.CALL else 0))
    return CanonicalHand(
        hand_id=hid, site="GG", stakes=Stakes(big_blind=100), hero="Hero",
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name=vilao, stack=5000)],
        hero_cards=["Ah", "Kd"], final_board=BOARD,
        shown_cards={vilao: ["Jd", "Th"]} if mostra else {},
        streets=[Street(name=StreetName.PREFLOP, actions=[
                     Action(actor=vilao, type=ActionType.RAISE,
                            amount=200, to_amount=200),
                     Action(actor="Hero", type=ActionType.CALL, amount=200)]),
                 Street(name=StreetName.FLOP, actions=[
                     Action(actor="Hero", type=ActionType.CHECK),
                     Action(actor=vilao, type=ActionType.BET, amount=300),
                     Action(actor="Hero", type=ActionType.CALL, amount=300)]),
                 Street(name=StreetName.RIVER, actions=riv)])


# ---- 1) a conta -------------------------------------------------------------

def test_o_pote_antes_do_river_soma_as_streets_anteriores():
    assert _pote_antes_do_river(mao("h", ActionType.FOLD)) == 1000.0


def test_raise_conta_ATE_e_nao_MAIS():
    """3-bet pré com to_amount: somar `amount` de novo infla o pote e
    derruba a fração — o limiar sai errado para baixo."""
    h = mao("h", ActionType.FOLD)
    h.streets[0].actions.insert(1, Action(
        actor="Hero", type=ActionType.RAISE, amount=600, to_amount=600))
    h.streets[0].actions[2] = Action(actor="v1", type=ActionType.RAISE,
                                     amount=1400, to_amount=1400)
    h.streets[0].actions.append(Action(actor="Hero", type=ActionType.CALL,
                                       amount=800))
    # v1: 200 depois até 1400 = 1400; Hero: 600 + 800 = 1400; flop 600
    assert _pote_antes_do_river(h) == 3400.0


def test_a_fracao_e_o_limiar_do_teorema():
    """0,65× pote => blefe lucra a partir de 39% de fold — não 61%."""
    e = aposta_enfrentada(mao("h", ActionType.FOLD))
    assert e.fracao_do_pote == 0.65
    d = medir([mao(f"h{i}", ActionType.FOLD) for i in range(10)], "v1")
    assert d.limiar_fold == pytest.approx(0.394, abs=0.001)
    assert not (0.60 <= d.limiar_fold <= 0.62), (
        "o limiar virou a defesa mínima (1-b/(p+b)) — inverteria o veredito")


def test_valores_ausentes_nao_viram_fracao_inventada():
    e = aposta_enfrentada(mao("h", ActionType.FOLD, bet=0.0))
    assert e is None or e.fracao_do_pote is None


# ---- 2) o veredito pelo piso, não pela média --------------------------------

def test_overfold_so_quando_o_PISO_passa_o_limiar():
    """8 folds em 10 a 0,65×: piso de Wilson 49% > 39% => overfold."""
    maos = ([mao(f"f{i}", ActionType.FOLD) for i in range(8)]
            + [mao(f"c{i}", ActionType.CALL) for i in range(2)])
    d = medir(maos, "v1")
    assert d.veredito == "overfold"
    assert d.fold_lo > d.limiar_fold


def test_media_alta_com_intervalo_largo_NAO_acusa():
    """6 folds em 8: média 75%, mas o piso (~41%) fica abaixo do limiar de
    uma aposta grande — relato sim, acusação não."""
    maos = ([mao(f"f{i}", ActionType.FOLD, bet=1500.0) for i in range(6)]
            + [mao(f"c{i}", ActionType.CALL, bet=1500.0) for i in range(2)])
    d = medir(maos, "v1")
    assert d.fold_taxa == 0.75
    assert d.veredito == "ok", (d.fold_lo, d.limiar_fold)


def test_amostra_curta_relata_sem_veredito():
    maos = [mao(f"f{i}", ActionType.FOLD) for i in range(MINIMO_PARA_VEREDITO - 1)]
    d = medir(maos, "v1")
    assert d.veredito == "amostra_curta"
    assert "veredito não" in texto(d, [], "v1")


def test_wilson_e_piso_de_verdade():
    assert _wilson_lo(8, 10) == pytest.approx(0.49, abs=0.02)
    assert _wilson_lo(0, 0) == 0.0
    assert _wilson_lo(10, 10) < 1.0, "10/10 com certeza absoluta não existe"


# ---- 3) o que entra e o que não entra ---------------------------------------

def test_so_conta_quando_o_heroi_DECIDIU():
    """Vilão apostou e a mão acabou sem resposta do herói (ele já estava
    fora): não houve defesa para medir."""
    assert aposta_enfrentada(mao("h", None)) is None


def test_aposta_do_HEROI_nao_e_defesa():
    h = mao("h", ActionType.FOLD)
    h.streets[2].actions = [Action(actor="Hero", type=ActionType.BET, amount=650),
                            Action(actor="v1", type=ActionType.CALL, amount=650)]
    assert aposta_enfrentada(h) is None


def test_bet_do_heroi_com_raise_do_vilao_mede_a_defesa_contra_o_RAISE():
    """Herói aposta, vilão dá raise, herói folda. A agressão enfrentada é a
    do VILÃO — sem o filtro de ator, a primeira ação agressiva do river é a
    do próprio herói e o "vilão" do evento viraria "Hero" (e o `medir` sem
    filtro contaria o herói se defendendo de si mesmo)."""
    h = mao("h", None)
    h.streets[2].actions = [
        Action(actor="Hero", type=ActionType.BET, amount=500),
        Action(actor="v1", type=ActionType.RAISE, amount=1500, to_amount=1500),
        Action(actor="Hero", type=ActionType.FOLD)]
    e = aposta_enfrentada(h)
    assert e is not None and e.vilao == "v1", e
    assert e.resposta == "fold"
    d = medir([h])
    assert d.apostas == 1 and d.folds == 1


def test_filtro_por_vilao_e_por_todos():
    maos = ([mao(f"a{i}", ActionType.FOLD, vilao="v1") for i in range(3)]
            + [mao(f"b{i}", ActionType.FOLD, vilao="v2") for i in range(2)])
    assert medir(maos, "v1").apostas == 3
    assert medir(maos, "v2").apostas == 2
    assert medir(maos).apostas == 5
    assert medir(maos, "ninguem") is None
    assert medir([], "v1") is None


def test_nao_vistas_exclui_showdown():
    maos = [mao("f1", ActionType.FOLD),                 # escura
            mao("c1", ActionType.CALL, mostra=True)]    # vista
    escuras = nao_vistas(maos, "v1")
    assert [e.hand_id for e in escuras] == ["f1"]


# ---- 4) os sinais da linha (fatos, nunca veredito) --------------------------

def _mao_com_linha(hid, board, bet=650.0, flop_bet=True, turn_bet=True):
    """Vilão com linha controlável rua a rua, herói folda o river."""
    ruas = [Street(name=StreetName.PREFLOP, actions=[
                Action(actor="v1", type=ActionType.RAISE, amount=200,
                       to_amount=200),
                Action(actor="Hero", type=ActionType.CALL, amount=200)])]
    for nome, agrediu in ((StreetName.FLOP, flop_bet),
                          (StreetName.TURN, turn_bet)):
        acoes = [Action(actor="Hero", type=ActionType.CHECK)]
        if agrediu:
            acoes += [Action(actor="v1", type=ActionType.BET, amount=150),
                      Action(actor="Hero", type=ActionType.CALL, amount=150)]
        else:
            acoes.append(Action(actor="v1", type=ActionType.CHECK))
        ruas.append(Street(name=nome, actions=acoes))
    ruas.append(Street(name=StreetName.RIVER, actions=[
        Action(actor="Hero", type=ActionType.CHECK),
        Action(actor="v1", type=ActionType.BET, amount=bet),
        Action(actor="Hero", type=ActionType.FOLD)]))
    return CanonicalHand(
        hand_id=hid, site="GG", stakes=Stakes(big_blind=100), hero="Hero",
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=5000)],
        hero_cards=["Ah", "Kd"], final_board=board, shown_cards={},
        streets=ruas)


def test_sinais_do_blefe_classico_draw_perdido_e_tres_barris():
    """A linha que todo coach aponta: draw de copas no flop que NÃO bate,
    três barris, overbet no fim."""
    e = aposta_enfrentada(_mao_com_linha(
        "h", ["Qh", "7h", "2d", "9c", "3s"], bet=1400.0))
    assert "três barris" in e.sinais
    assert "o flush draw do flop não bateu" in e.sinais
    assert any(s.startswith("overbet") for s in e.sinais)
    assert "o river fechou flush possível" not in e.sinais


def test_sinais_do_river_que_fecha_o_flush_e_do_acordou_tarde():
    e = aposta_enfrentada(_mao_com_linha(
        "h", ["Qh", "7h", "2d", "9c", "3h"], flop_bet=False, turn_bet=False))
    assert "acordou só no river" in e.sinais
    assert "o river fechou flush possível" in e.sinais
    assert "o flush draw do flop não bateu" not in e.sinais, (
        "o draw BATEU — marcar como perdido inverte a leitura")
    assert "três barris" not in e.sinais


def test_linha_comum_nao_ganha_sinal_inventado():
    """Aposta de meio pote, um barril, board seco: nenhum sinal. Sinal em
    toda mão é o mesmo que sinal em nenhuma."""
    e = aposta_enfrentada(_mao_com_linha(
        "h", ["Qs", "7h", "2d", "9c", "3s"], bet=500.0, turn_bet=False))
    assert e.sinais == (), e.sinais


def test_dois_barris_nao_sao_tres():
    e = aposta_enfrentada(_mao_com_linha(
        "h", ["Qs", "7h", "2d", "9c", "3s"], bet=500.0, flop_bet=True,
        turn_bet=False))
    assert "três barris" not in e.sinais
    assert "acordou só no river" not in e.sinais


def test_os_sinais_aparecem_no_texto_com_a_bandeira_e_o_aviso():
    maos = [_mao_com_linha("h", ["Qh", "7h", "2d", "9c", "3s"], bet=1400.0)]
    t = texto(medir(maos, "v1"), nao_vistas(maos, "v1"), "v1")
    assert "⚑" in t and "três barris" in t
    assert "não veredito" in t, "a bandeira sem o aviso vira acusação"


# ---- 5) o texto -------------------------------------------------------------

def test_as_escuras_saem_com_fatos_e_SEM_probabilidade():
    maos = ([mao(f"f{i}", ActionType.FOLD) for i in range(9)]
            + [mao("c0", ActionType.CALL, mostra=True)])
    t = texto(medir(maos, "v1"), nao_vistas(maos, "v1"), "v1", limite=3)
    assert "ninguém viu" in t and "e mais 6" in t
    assert "aumenta pré · aposta flop · aposta river" in t
    assert "0.65× pote" in t
    assert "provavelmente" not in t.replace(
        'não existe "provavelmente blefou"', ""), (
        "apareceu um 'provavelmente' fora da negação")
    assert "blefou X" not in t


def test_overfold_no_texto_carrega_o_piso():
    maos = ([mao(f"f{i}", ActionType.FOLD) for i in range(8)]
            + [mao(f"c{i}", ActionType.CALL) for i in range(2)])
    t = texto(medir(maos, "v1"), [], "v1")
    assert "folda demais" in t and "≥49%" in t
    assert "39%" in t, "o limiar do teorema sumiu do texto"


def test_sem_nada_o_texto_e_vazio():
    assert texto(None, [], "v1") == ""


# ---- 6) as linhas escuras (a lista AMPLA) -----------------------------------

def _mao_contra_outro(hid, ruas_de_barril=("flop", "turn"), levou=True,
                      mostra=False):
    """Herói folda pré; vilão agride contra um TERCEIRO. Era a mão invisível:
    o recorte antigo só via aposta de river contra o herói, e o dossiê do
    dono saiu sem escura nenhuma."""
    st = [Street(name=StreetName.PREFLOP, actions=[
        Action(actor="Hero", type=ActionType.FOLD),
        Action(actor="v1", type=ActionType.RAISE, amount=250, to_amount=250),
        Action(actor="outro", type=ActionType.CALL, amount=250)])]
    for nome, enum in (("flop", StreetName.FLOP), ("turn", StreetName.TURN)):
        acoes = [Action(actor="outro", type=ActionType.CHECK)]
        if nome in ruas_de_barril:
            acoes += [Action(actor="v1", type=ActionType.BET, amount=300),
                      Action(actor="outro", type=ActionType.CALL
                             if nome != ruas_de_barril[-1]
                             else ActionType.FOLD, amount=300)]
        st.append(Street(name=enum, actions=acoes))
    return CanonicalHand(
        hand_id=hid, site="GG", tournament_id="t1", hero="Hero",
        stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=5000),
                 PlayerSeat(seat=3, name="outro", stack=5000)],
        hero_cards=["7h", "2c"], final_board=["Qs", "7s", "2d", "9c"],
        shown_cards={"v1": ["As", "Ad"]} if mostra else {},
        collected={"v1": 1900.0} if levou else {}, streets=st)


def test_agressao_contra_OUTROS_entra_nas_linhas_escuras():
    """O caso do dossiê vazio: herói fora da mão, vilão de barril contra um
    terceiro. É a maioria das mãos de um torneio real."""
    from app.analysis.defesa import linhas_escuras

    le = linhas_escuras([_mao_contra_outro("h1")], "v1")
    assert len(le) == 1
    e = le[0]
    assert e.rua == "turn"
    assert "aposta flop" in e.linha and "aposta turn" in e.linha
    assert e.levou_o_pote is True


def test_open_de_preflop_sozinho_NAO_e_linha_escura():
    """Open é rotina — o PFR já conta. Listar cada open afogaria as linhas
    que interessam em centenas de mãos de ruído."""
    from app.analysis.defesa import linhas_escuras

    so_open = _mao_contra_outro("h1", ruas_de_barril=())
    assert linhas_escuras([so_open], "v1") == []


def test_quem_mostrou_nao_e_escura():
    from app.analysis.defesa import linhas_escuras

    assert linhas_escuras([_mao_contra_outro("h1", mostra=True)], "v1") == []


def test_linha_escura_sem_pote_levado_e_registro_fiel():
    from app.analysis.defesa import linhas_escuras

    le = linhas_escuras([_mao_contra_outro("h1", levou=False)], "v1")
    assert le[0].levou_o_pote is False


def test_a_fracao_so_existe_quando_a_agressao_final_foi_no_river():
    """No flop/turn o denominador é outro — número de river numa aposta de
    turn seria fração errada com cara de certa."""
    from app.analysis.defesa import linhas_escuras

    le = linhas_escuras([_mao_contra_outro("h1")], "v1")
    assert le[0].fracao_do_pote is None


# ---- 7) a ligação -----------------------------------------------------------

def test_o_vilao_entrega_a_defesa_junto(monkeypatch):
    import app.bot.processing as P

    maos = ([mao(f"f{i}", ActionType.FOLD) for i in range(8)]
            + [mao(f"c{i}", ActionType.CALL, mostra=(i == 0))
               for i in range(2)])
    monkeypatch.setattr(P, "_user_hands", lambda *a, **k: maos)
    saida = P.villain_report(7, "v1")
    assert "Sua defesa contra a aposta de river" in saida
    assert "folda demais" in saida
    assert "ninguém viu" in saida
