"""O relatório mão a mão analisa a mão INTEIRA, street por street, e chama
cada ação pelo nome.

Caso real: torneio #303773218 (GGPoker, 165 mãos, 47 jogadas). O dono leu o
HTML e respondeu *"Análise tá uma merda analisa só o pre-flop… tem que
analisar todas as mãos street por street"*. Três defeitos, todos no texto
determinístico `played_fallback_verdict` (as 47 mãos caíram nele):

    #7  9♣7♣ BB — "No flop você pagou 2bb … No turn você apostou 4.5bb"
                  (o preflop sumiu: só as 2 PRIMEIRAS decisões viravam texto)
    #10 Q♥J♥ CO — "No preflop você pagou 1bb … No flop você apostou 1.9bb"
                  (1bb era a BB que ele ENFRENTOU ao abrir de raise — ele não
                   pagou nada; e a mão para no flop)

Medido nas fixtures de `tests/sample_hands` (41 mãos jogadas, 81 decisões com
número, média 1,98 por mão):

  - 23 decisões (28%) ficavam FORA do texto pelo teto `numbers[:2]`, e
    14 mãos (34%) têm 3 ou mais decisões;
  - 34 decisões (42%) eram RAISE com preço na frente — todas escritas como
    "você pagou X bb", que é o preço de PAGAR aplicado a quem aumentou;
  -  2 decisões eram FOLD com preço na frente — 100% invisíveis, porque o
    texto só escrevia a linha quando havia equity medida, e o fold é gravado
    com `equity_vs_aleatoria: None` de propósito.

O que estes testes prendem:

  1. toda street com decisão aparece — não só as duas primeiras;
  2. a street em que o herói largou aparece com o preço que estava na frente
     e o pote, e SEM veredito (sem equity medida não se crava nada —
     `docs/METODO.md`, "o que a ferramenta se recusa a afirmar");
  3. raise não é call: quem aumentou não "pagou", e o veredito de preço
     ("o preço estava bom" / "pagou mais caro") só vale para quem pagou;
  4. a nota da IMAGEM (limitada em 260 chars para a altura no PDF) recebe uma
     versão curta pelas decisões mais caras, em vez de virar "…" em toda mão.
"""
from __future__ import annotations

import pytest

from app.analysis.handreport import (
    NOTA_IMG_MAX,
    build_report_html,
    played_facts,
    played_fallback_verdict,
)
from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    HandFormat,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)

SB = Action(actor="sb", type=ActionType.POST, amount=50, post_type="sb")
BBP = Action(actor="bb", type=ActionType.POST, amount=100, post_type="bb")
FOLD_BLINDS = [Action(actor="sb", type=ActionType.FOLD),
               Action(actor="bb", type=ActionType.FOLD)]


def _mesa(hid: str, streets: list[Street], cards: list[str],
          board: list[str]) -> CanonicalHand:
    """Mesa de 4 com blinds 50/100 — o resto muda por teste."""
    return CanonicalHand(
        hand_id=hid, site="GG", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=50, big_blind=100), hero="Hero",
        played_at="2026-08-10T20:00:00",
        players=[
            PlayerSeat(seat=1, name="Hero", stack=10000, position="CO",
                       is_hero=True),
            PlayerSeat(seat=2, name="v1", stack=10000, position="UTG"),
            PlayerSeat(seat=3, name="sb", stack=10000, position="SB"),
            PlayerSeat(seat=4, name="bb", stack=10000, position="BB")],
        hero_cards=cards, final_board=board, streets=streets)


def mao_tres_decisoes() -> CanonicalHand:
    """Preflop CALL, flop RAISE, turn FOLD — as três com preço na frente.

    É a mão que o relatório de #303773218 não sabia contar: hoje sai só o
    preflop e o flop, o flop sai como "pagou 3bb" (ele aumentou para 9bb) e o
    fold do turn não existe.
    """
    return _mesa(
        "TM-TRES", cards=["Ah", "Kc"], board=["Kd", "9s", "2c", "7h"],
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                SB, BBP,
                Action(actor="v1", type=ActionType.RAISE, amount=250,
                       to_amount=250),
                Action(actor="Hero", type=ActionType.CALL, amount=250),
                *FOLD_BLINDS]),
            Street(name=StreetName.FLOP, board=["Kd", "9s", "2c"], actions=[
                Action(actor="v1", type=ActionType.BET, amount=300),
                Action(actor="Hero", type=ActionType.RAISE, amount=900,
                       to_amount=900),
                Action(actor="v1", type=ActionType.CALL, amount=600)]),
            Street(name=StreetName.TURN, board=["Kd", "9s", "2c", "7h"],
                   actions=[
                Action(actor="v1", type=ActionType.BET, amount=1200),
                Action(actor="Hero", type=ActionType.FOLD)])])


def mao_quatro_decisoes() -> CanonicalHand:
    """Quatro streets com decisão — preflop CALL, flop CALL, turn BET,
    river CALL. O texto completo passa dos 260 chars da imagem."""
    return _mesa(
        "TM-QUATRO", cards=["Ah", "Kc"], board=["Kd", "9s", "2c", "7h", "3d"],
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                SB, BBP,
                Action(actor="v1", type=ActionType.RAISE, amount=250,
                       to_amount=250),
                Action(actor="Hero", type=ActionType.CALL, amount=250),
                *FOLD_BLINDS]),
            Street(name=StreetName.FLOP, board=["Kd", "9s", "2c"], actions=[
                Action(actor="v1", type=ActionType.BET, amount=300),
                Action(actor="Hero", type=ActionType.CALL, amount=300)]),
            Street(name=StreetName.TURN, board=["Kd", "9s", "2c", "7h"],
                   actions=[
                Action(actor="Hero", type=ActionType.BET, amount=600),
                Action(actor="v1", type=ActionType.CALL, amount=600)]),
            Street(name=StreetName.RIVER,
                   board=["Kd", "9s", "2c", "7h", "3d"], actions=[
                Action(actor="v1", type=ActionType.BET, amount=2400),
                Action(actor="Hero", type=ActionType.CALL, amount=2400)])])


def mao_open_raise() -> CanonicalHand:
    """A #10 do torneio: o herói ABRE de CO e só a BB está na frente.

    `to_call_bb` = 1bb (a big blind), e o texto antigo escrevia
    "No preflop você pagou 1bb" para quem não pagou — abriu.
    """
    return _mesa(
        "TM-OPEN", cards=["Qh", "Jh"], board=[],
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                SB, BBP,
                Action(actor="v1", type=ActionType.FOLD),
                Action(actor="Hero", type=ActionType.RAISE, amount=250,
                       to_amount=250),
                *FOLD_BLINDS])])


def texto(h: CanonicalHand, **kw) -> str:
    return played_fallback_verdict(h, played_facts(h), **kw)


def frase(txt: str, street: str) -> str:
    """A frase daquela street — '' se o texto não fala dela."""
    for parte in txt.split(". "):
        if parte.startswith(f"No {street} "):
            return parte
    return ""


# ---- 1) a mão inteira, street por street ------------------------------------

def test_toda_street_com_decisao_vira_texto():
    """O defeito da #7: com o teto `numbers[:2]` a terceira decisão sumia."""
    txt = texto(mao_tres_decisoes())

    for street in ("preflop", "flop", "turn"):
        assert frase(txt, street), f"a {street} não virou texto: {txt}"


def test_quatro_streets_saem_todas_e_na_ordem_da_mao():
    txt = texto(mao_quatro_decisoes())
    ordem = [s for s in ("preflop", "flop", "turn", "river") if frase(txt, s)]

    assert ordem == ["preflop", "flop", "turn", "river"], txt


# ---- 2) o fold é decisão e aparece, sem veredito inventado -------------------

def test_a_street_do_fold_aparece_com_o_preco_e_o_pote():
    """`played_facts` grava o fold de propósito ("O FOLD TAMBÉM É
    OPORTUNIDADE"); o texto o ignorava por não ter equity medida."""
    turn = frase(texto(mao_tres_decisoes()), "turn")

    assert "largou" in turn, f"o fold do turn não aparece: {turn!r}"
    assert "25%" in turn, f"o preço que estava na frente sumiu: {turn!r}"
    assert "36.5bb" in turn, f"o pote da decisão sumiu: {turn!r}"


def test_fold_sem_equity_medida_nao_ganha_veredito():
    """Sem equity não há como dizer se largar foi certo — e a ferramenta se
    recusa a afirmar (docs/METODO.md)."""
    turn = frase(texto(mao_tres_decisoes()), "turn")

    assert "o preço estava bom" not in turn
    assert "pagou mais caro" not in turn
    assert "sem veredito" in turn, f"a recusa tem que ser explícita: {turn!r}"


# ---- 3) raise não é call ----------------------------------------------------

def test_raise_com_preco_na_frente_nao_vira_pagou():
    """A medição de 09/08 (24 mãos, 12 com raise, as 24 acusadas de call caro)
    virou o campo `acao` em `played_facts` — que o texto nunca leu."""
    flop = frase(texto(mao_tres_decisoes()), "flop")

    assert "aumentou" in flop, f"o raise do flop virou outra coisa: {flop!r}"
    assert "você pagou" not in flop, f"raise descrito como call: {flop!r}"
    assert "3bb" not in flop, \
        f"o preço de PAGAR não descreve quem aumentou: {flop!r}"


def test_o_veredito_de_preco_e_so_de_quem_pagou():
    """O call mantém o veredito (ele pagou); o raise não pode carregá-lo."""
    txt = texto(mao_tres_decisoes())

    assert "o preço estava bom" in frase(txt, "preflop"), \
        f"o call perdeu o veredito de preço: {txt}"
    for proibido in ("o preço estava bom", "pagou mais caro do que a mão valia"):
        assert proibido not in frase(txt, "flop"), \
            f"veredito de preço colado num raise: {txt}"


def test_open_raise_do_preflop_nao_vira_um_call_de_1bb():
    """A #10 Q♥J♥ CO de #303773218, exata: abriu 2.5bb enfrentando a BB."""
    txt = texto(mao_open_raise())

    assert "você pagou 1bb" not in txt, f"a #10 voltou: {txt}"
    assert "aumentou" in frase(txt, "preflop"), txt


# ---- 4) a imagem não vira reticências ---------------------------------------

def test_a_nota_da_imagem_e_curta_e_o_html_traz_a_mao_inteira(monkeypatch):
    """A imagem do PDF tem altura limitada, então recebe as decisões mais
    caras; o corte de 260 chars vira rede de segurança, não a regra."""
    capturado: dict = {}

    def _fake_render(spec):
        capturado["spec"] = spec
        return b"PNG-DE-TESTE"

    monkeypatch.setattr("app.analysis.hand_figure.render_hand_strip",
                        _fake_render)

    html = build_report_html([mao_quatro_decisoes()])

    nota = capturado["spec"]["verdict_text"]
    assert len(nota) <= NOTA_IMG_MAX
    assert not nota.endswith("…"), f"a imagem saiu reticente: {nota!r}"
    assert nota.count("No ") >= 1 and "Saldo da mão" in nota, nota
    for street in ("preflop", "flop", "turn", "river"):
        assert f"No {street}" in html, f"o HTML perdeu a {street}"


def test_a_versao_curta_fica_com_as_decisoes_mais_caras():
    """Quando não cabe tudo, fica o que valeu mais fichas — o pote da
    decisão manda, e a mais barata é a que sai."""
    h = mao_quatro_decisoes()
    f = played_facts(h)

    curta = played_fallback_verdict(h, f, max_chars=NOTA_IMG_MAX)

    assert len(curta) <= NOTA_IMG_MAX
    assert frase(curta, "river"), f"a decisão do maior pote saiu: {curta!r}"
    assert not frase(curta, "preflop"), \
        f"o pote menor ficou e o maior não: {curta!r}"
    assert "Saldo da mão" in curta


def test_sem_teto_de_caracteres_o_texto_sai_inteiro():
    """O HTML não tem limite de altura: nada de resumo lá."""
    h = mao_quatro_decisoes()
    f = played_facts(h)

    assert len(played_fallback_verdict(h, f)) > NOTA_IMG_MAX


@pytest.mark.parametrize("mao", [mao_tres_decisoes, mao_quatro_decisoes,
                                 mao_open_raise])
def test_o_saldo_da_mao_continua_fechando_o_texto(mao):
    """Regressão do que já funcionava: o saldo é a última frase, sempre."""
    assert texto(mao()).split(". ")[-1].startswith("Saldo da mão: ")
