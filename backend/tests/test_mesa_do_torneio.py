"""A mesa do torneio: rótulo só com intervalo, ordem só com evidência.

Os números de referência são os REAIS do torneio GG 303773218, medidos por
SQL antes do módulo existir:

    b6b7cbae  258 mãos  VPIP 34,1%  PFR 22,5%   (solto)
    cf5b672d  254       29,1%       14,2%       (gap 15pp — o explorável)
    fdd4b32d  258       20,2%       12,4%
    78f4f672  252       19,0%        7,9%       (gap 11pp)
    841a8ae4   60       36,7%       26,7%       (margem ±12 — só direção)

O que se prende:

  * o rótulo obedece ao INTERVALO: VPIP 29% de média não vira "solto"
    porque o piso fica abaixo de 28 — e o quadro mostra números sem rótulo
    em vez de esticar;
  * a ordem é pelo PISO do gap: 60 mãos com gap 10pp não passam à frente de
    254 mãos com gap 15pp por ruído;
  * abaixo de 20 mãos a linha não existe — vira contador no rodapé;
  * o gap é proporção dentro do MESMO jogador (vpip_n − pfr_n sobre seen):
    não há comparação entre vilões, logo não há correção múltipla a dever.
"""
from __future__ import annotations

import pytest

from app.analysis.mesa import (
    MINIMO_PARA_LINHA,
    MINIMO_PARA_ROTULO,
    Linha,
    Mesa,
    medir,
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


def gerar(specs: dict, com_showdown: dict | None = None) -> list:
    """specs: nome -> (seen, vpip_n, pfr_n); uma mão por observação."""
    com_showdown = com_showdown or {}
    maos = []
    for nome, (seen, vn, pn) in specs.items():
        for i in range(seen):
            if i < pn:
                acao = Action(actor=nome, type=ActionType.RAISE,
                              amount=200, to_amount=200)
            elif i < vn:
                acao = Action(actor=nome, type=ActionType.CALL, amount=100)
            else:
                acao = Action(actor=nome, type=ActionType.FOLD)
            maos.append(CanonicalHand(
                hand_id=f"{nome}-{i}", site="GG", hero="Hero",
                stakes=Stakes(big_blind=100),
                players=[PlayerSeat(seat=1, name="Hero", stack=1,
                                    is_hero=True),
                         PlayerSeat(seat=2, name=nome, stack=1)],
                shown_cards=({nome: ["As", "Kd"]}
                             if i < com_showdown.get(nome, 0) else {}),
                streets=[Street(name=StreetName.PREFLOP,
                                actions=[Action(actor="Hero",
                                                type=ActionType.FOLD),
                                         acao])]))
    return maos


TORNEIO_REAL = {
    "b6b7cbae": (258, 88, 58),
    "cf5b672d": (254, 74, 36),
    "fdd4b32d": (258, 52, 32),
    "78f4f672": (252, 48, 20),
    "841a8ae4": (60, 22, 16),
    "raro": (8, 3, 1),
}


@pytest.fixture
def mesa_real():
    return medir(gerar(TORNEIO_REAL, com_showdown={"cf5b672d": 3}))


# ---- rótulo pelo intervalo --------------------------------------------------

def test_media_do_lado_certo_com_piso_do_lado_errado_NAO_rotula(mesa_real):
    """cf5b672d: VPIP 29,1% — acima da fronteira de 28. O piso (~24%) não.
    O rótulo "solto" esticaria a evidência; sai só "passivo", que o gap
    de 15pp sustenta."""
    linha = next(li for li in mesa_real.linhas if li.nome == "cf5b672d")
    assert linha.rotulo == "passivo", linha
    assert "solto" not in linha.rotulo


def test_solto_com_evidencia_e_rotulado(mesa_real):
    linha = next(li for li in mesa_real.linhas if li.nome == "b6b7cbae")
    assert linha.rotulo == "solto"
    assert "blefar" in linha.exploit


def test_fechado_exige_o_TETO_abaixo_da_fronteira():
    """19% em 252 mãos tem teto ~24% > 22%: honestamente ainda não é
    "fechado". Em 1000 mãos o teto cai para ~21,6% e o rótulo entra."""
    m1 = medir(gerar({"x": (252, 48, 20)}))
    assert m1.linhas[0].rotulo in ("", "passivo")
    m2 = medir(gerar({"x": (1000, 190, 80)}))
    assert "fechado" in m2.linhas[0].rotulo


def test_amostra_entre_20_e_39_sai_com_numeros_e_sem_rotulo():
    m = medir(gerar({"x": (30, 15, 3)}))   # gap 40pp — e mesmo assim
    li = m.linhas[0]
    assert li.maos == 30 and li.rotulo == ""
    assert li.gap == pytest.approx(0.4)


# ---- a ordem ----------------------------------------------------------------

def test_a_ordem_e_pelo_piso_do_gap_nao_pela_media(mesa_real):
    """841a8ae4 tem gap de 10pp em 60 mãos (piso ~4%); 78f4f672 tem 11pp em
    252 (piso ~8%). A média quase empata; o piso não."""
    nomes = [li.nome for li in mesa_real.linhas]
    assert nomes[0] == "cf5b672d", "o gap 15pp em 254 mãos lidera"
    assert nomes.index("78f4f672") < nomes.index("841a8ae4")


def test_gap_grande_em_amostra_pequena_nao_fura_a_fila():
    """A: 25 mãos com gap de 20pp (piso ~9%). B: 300 mãos com gap de 15pp
    (piso ~11%). Pela MÉDIA, A lidera; pela evidência, B. A fila é de
    evidência — senão o topo do quadro vira loteria de amostra curta."""
    m = medir(gerar({"A": (25, 10, 5), "B": (300, 105, 60)}))
    assert [li.nome for li in m.linhas] == ["B", "A"], (
        [(li.nome, li.gap, li.gap_lo) for li in m.linhas])


# ---- quem entra -------------------------------------------------------------

def test_abaixo_de_20_maos_vira_contador_e_nao_linha(mesa_real):
    assert all(li.nome != "raro" for li in mesa_real.linhas)
    assert mesa_real.amostra_curta == 1
    assert "1 vilão fica" in texto(mesa_real)


def test_o_heroi_nao_e_vilao_de_si_mesmo(mesa_real):
    assert all(li.nome != "Hero" for li in mesa_real.linhas)


def test_mesa_vazia_da_None_e_texto_vazio():
    assert medir([]) is None
    assert texto(None) == ""
    assert texto(Mesa(linhas=(), vilaos=0, observacoes=0,
                      amostra_curta=0)) == ""


def test_blind_postado_nao_conta_como_vpip():
    maos = gerar({"x": (25, 0, 0)})
    for h in maos:
        h.streets[0].actions.insert(0, Action(
            actor="x", type=ActionType.POST, amount=100, post_type="bb"))
    m = medir(maos)
    assert m.linhas[0].vpip == 0.0, "postar blind virou entrada voluntária"


# ---- o gap é do próprio jogador ---------------------------------------------

def test_o_gap_e_proporcao_dentro_do_jogador():
    """seen 100, vpip 40, pfr 10 => gap 30/100. Não depende de nenhum outro
    vilão — é por isso que não há correção múltipla a dever aqui."""
    m = medir(gerar({"x": (100, 40, 10)}))
    assert m.linhas[0].gap == pytest.approx(0.30)


# ---- o texto ----------------------------------------------------------------

def test_o_texto_traz_margem_gap_e_ponte_para_o_dossie(mesa_real):
    t = texto(mesa_real)
    assert "VPIP 29% ±6" in t and "gap 15pp" in t
    assert "/vilao cf5b672d" in t, "quem mostrou mão merece a ponte pro dossiê"
    assert "amostra curta não vira rótulo" in t


def test_o_corte_avisa_quantos_ficaram():
    specs = {f"v{i}": (50, 20, 5) for i in range(9)}
    t = texto(medir(gerar(specs)), limite=6)
    assert "e mais 3 com 20+ mãos" in t


# ---- a ligação --------------------------------------------------------------

def test_o_torneio_entrega_a_mesa_junto_da_leitura(monkeypatch):
    import app.bot.processing as P

    maos = gerar({"cf5b672d": (254, 74, 36)})
    monkeypatch.setattr(P, "maos_do_ultimo_torneio", lambda tg: maos)

    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    saida = P.estrategia_do_torneio(7)
    assert "A mesa deste torneio" in saida
    assert "cf5b672d" in saida
