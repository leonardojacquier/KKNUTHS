"""A síntese por IA do dossiê — e a conferência que decide se ela existe.

O dono viu os dois retratos em produção e pediu: "ponha um pouco de IA que
ficou muito ruim". A IA entra onde ela acrescenta (a VOZ — a prosa de coach
que amarra os blocos), e a regra da casa fica: o modelo escreve, a
conferência garante. Estes testes prendem a fronteira: número inventado
descarta o texto INTEIRO, e o dossiê degrada para o determinístico de
sempre — nunca para um número falso na frente do aluno.
"""
from __future__ import annotations

import pytest

from app.bot import processing as P
from tests.test_dois_retratos_do_vilao import _mao


def _hands():
    return ([_mao(f"s{i}", mostra=["Qs", "Qd"]) for i in range(3)]
            + [_mao(f"e{i}") for i in range(20)])


# ---- a conferência ----------------------------------------------------------

def test_conferir_aprova_numeros_dos_fatos_e_reprova_conta_de_modelo():
    from app.analysis.sintese import conferir, fatos_do_dossie

    f = fatos_do_dossie("v1", _hands())
    assert conferir("Ele levou 20 de 23 potes sem showdown.", f) == []
    # 87% é conta do modelo (20/23) — exatamente o que não entra
    assert conferir("Ele leva 87% dos potes.", f) == ["87"]


def test_conferir_normaliza_virgula_e_zeros():
    from app.analysis.sintese import conferir

    fatos = {"sizing": 0.6, "n": 12}
    assert conferir("aposta de 0,60× pote em 12 mãos", fatos) == []
    assert conferir("aposta de 0,65× pote", fatos) == ["0,65"]


def test_numeros_dentro_de_strings_dos_fatos_valem():
    """A divergência e o '3 de 4' carregam números DENTRO de texto — a
    prosa pode citá-los."""
    from app.analysis.sintese import conferir

    fatos = {"cbet": "3 de 4", "nota": "levou 11 potes"}
    assert conferir("c-bet em 3 de 4; levou 11 potes", fatos) == []


def test_fatos_do_dossie_fecham_a_conta_do_showdown():
    from app.analysis.sintese import fatos_do_dossie

    f = fatos_do_dossie("v1", _hands())
    r = f["retrato_showdown"]
    assert (r["valor"] + r["blefes"] + r["so_pagou"]
            + r["mostrou_sem_agredir"]) == r["maos_que_ele_mostrou"]
    assert "divergencia_entre_retratos" in f


# ---- o retrato A agora soma na tela -----------------------------------------

def _mao_checkada(hid):
    """v1 (BB) dá check até o showdown e mostra — papel 'mostrou', o balde
    que faltava na tela."""
    from app.models.canonical import (
        Action,
        ActionType,
        CanonicalHand,
        PlayerSeat,
        Stakes,
        Street,
        StreetName,
    )

    board = ["Qh", "7h", "2d", "9c", "3s"]
    ck = lambda quem: Action(actor=quem, type=ActionType.CHECK)  # noqa: E731
    return CanonicalHand(
        hand_id=hid, site="GGPoker", tournament_id="t1", hero="Hero",
        stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v1", stack=5000)],
        hero_cards=["7s", "2c"], final_board=board,
        shown_cards={"v1": ["8c", "8d"]},
        streets=[Street(name=StreetName.PREFLOP,
                        actions=[ck("Hero"), ck("v1")])]
        + [Street(name=n, actions=[ck("Hero"), ck("v1")])
           for n in (StreetName.FLOP, StreetName.TURN, StreetName.RIVER)])


def test_texto_do_retrato_A_fecha_a_conta():
    """'2 valor · 0 blefe · 4 pagou' num retrato de 10 mãos não somava —
    o 'só mostrou' faltava e o dono estranhou (com razão)."""
    from app.analysis.dossie import montar as montar_dossie
    from app.analysis.perfil_duplo import montar, texto

    hands = _hands() + [_mao_checkada("ck1")]
    p = montar(hands, "v1", montar_dossie(hands, "v1"))
    assert p.a.outras == 1, "a mão checkada até o fim é 'só mostrou'"
    assert p.a.valor + p.a.blefes + p.a.pagou + p.a.outras == p.a.n
    assert "1 só mostrou" in texto(p)[0]


# ---- o documento ------------------------------------------------------------

def test_sintese_aparece_no_documento_com_o_selo_da_conferencia():
    from app.analysis.dossie_html import build_dossie_html

    html = build_dossie_html("v1", _hands(), {"site": "GG"},
                             sintese="Contra ele, pague mais leve no river.")
    assert "Leitura do coach" in html
    assert "pague mais leve no river" in html
    assert "conferido pelo código" in html


def test_sem_sintese_o_documento_sai_como_sempre():
    from app.analysis.dossie_html import build_dossie_html

    html = build_dossie_html("v1", _hands(), {"site": "GG"})
    assert "Leitura do coach" not in html


# ---- a fiação no /dossie ----------------------------------------------------

@pytest.fixture
def base(monkeypatch):
    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    monkeypatch.setattr(P, "RECENT_HANDS", {7: _hands()})


def test_dossie_doc_usa_sintese_conferida(base, monkeypatch):
    import app.agent.llm as llm

    monkeypatch.setattr(llm, "sintese_do_dossie",
                        lambda fatos: "Ele levou 20 de 23 potes agredindo — "
                                      "pague mais leve.")
    html = P.dossie_doc(7, "v1", 1)[0].decode("utf-8")
    assert "Leitura do coach" in html
    assert "pague mais leve" in html


def test_dossie_doc_descarta_sintese_com_numero_inventado(base, monkeypatch):
    """O modelo 'só resumiu' 20/23 em 87%? O texto INTEIRO cai e o dossiê
    sai determinístico — número falso nunca chega no aluno."""
    import app.agent.llm as llm

    monkeypatch.setattr(llm, "sintese_do_dossie",
                        lambda fatos: "Ele leva 87% dos potes — pague.")
    html = P.dossie_doc(7, "v1", 1)[0].decode("utf-8")
    assert "Leitura do coach" not in html
    assert "87%" not in html


def test_sem_api_key_a_sintese_e_None_e_nada_quebra(base, monkeypatch):
    """No container de teste não há ANTHROPIC_API_KEY: o caminho real
    inteiro (fatos -> llm -> None) roda e o documento sai sem a caixa."""
    doc = P.dossie_doc(7, "v1", 1)
    html = doc[0].decode("utf-8")
    assert "Leitura do coach" not in html
    assert "dois retratos" in html


def test_o_prompt_da_sintese_proibe_aritmetica():
    """A instrução mais importante: sem ela, a conferência descartaria
    quase toda síntese (modelo adora converter em %)."""
    import inspect

    import app.agent.llm as llm

    src = inspect.getsource(llm.sintese_do_dossie)
    assert "NUNCA some, divida, converta" in src
    assert "TERMOS_REGRA" in src
