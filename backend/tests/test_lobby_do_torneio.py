"""A estrutura lida do lobby, conferida contra as mãos do aluno.

Tudo aqui usa UM caso real: os dois prints do "MonsterStackHyperTur" do clube
PDQ Online, mandados pelo dono em 09/08. Números como estão na tela:

    fichas iniciais 100K · nível de 15 min · late reg no nível 5
    pausa 5 min a cada 55 · rebuy 3× · sem add-on · faixa 5–200
    escada: 25/50 · 50/100 · 100/200(25) · … · 15K/30K(4000)

E a conferência que motivou o módulo: as mãos daquele mesmo clube no banco
têm blinds 40K/80K(10K) … 1M/2M(300K) — a MESMA escada ×100, 11 de 11 níveis
com blind e ante batendo. Leitura de tela erra; escada de blinds é
conferível; erro pego antes de virar plano de jogo.

O nome do torneio, aliás, diz "Hyper" e o nível é de 15 minutos com 2.000 bb
de stack inicial. Ler o rótulo perde para medir.
"""
from __future__ import annotations

import pytest

from app.analysis.lobby import (
    Lobby,
    Nivel,
    conferir_com_maos,
    fator_mediano,
    linha_do_tempo,
    meia_vida_min,
    minuto_do_nivel,
    quando_vira_push_fold,
    stack_no_fim_do_late_reg,
    texto,
)
from app.models.canonical import CanonicalHand, Stakes

# a tabela EXATA do print
ESCADA = ((1, 25, 50, 0), (2, 50, 100, 0), (3, 100, 200, 25),
          (4, 200, 400, 50), (5, 300, 600, 75), (6, 400, 800, 100),
          (7, 500, 1000, 100), (8, 700, 1400, 200), (9, 1000, 2000, 300),
          (10, 1500, 3000, 400), (11, 2000, 4000, 500), (12, 3000, 6000, 800),
          (13, 4000, 8000, 1000), (14, 5000, 10000, 1500),
          (15, 7000, 14000, 2000), (16, 10000, 20000, 3000),
          (17, 15000, 30000, 4000))

# os big blinds REAIS das mãos daquele clube, tirados do banco de produção
BLINDS_DAS_MAOS = (5000, 10000, 20000, 80000, 100000, 140000, 200000, 300000,
                   400000, 600000, 800000, 1000000, 1400000, 2000000)


@pytest.fixture
def lobby():
    return Lobby(niveis=tuple(Nivel(*n) for n in ESCADA),
                 nome="MonsterStackHyperTur", buyin=85.0, taxa=15.0,
                 fichas_iniciais=100_000, minutos_por_nivel=15,
                 late_reg_nivel=5, pausa_min=5, pausa_cada_min=55,
                 rebuy="3 Vezes/1×", addon="Não", jogadores=3, faixa_max=200)


def maos_do_clube(blinds=BLINDS_DAS_MAOS):
    return [CanonicalHand(hand_id=str(bb), site="PPPoker · MonsterStack",
                          stakes=Stakes(big_blind=bb), players=[], streets=[])
            for bb in blinds]


# ---- a conta ----------------------------------------------------------------

def test_o_stack_inicial_em_bb_e_o_que_o_aluno_precisa_saber(lobby):
    """100.000 fichas com blind 50 = 2.000 bb. "Monster stack" não é figura
    de linguagem, e muda o plano do early inteiro."""
    assert linha_do_tempo(lobby)[0].stack_bb == 2000


def test_o_crescimento_do_blind_e_mediana_e_nao_media(lobby):
    """A escada começa DOBRANDO (25→50→100→200) e depois assenta em ~1,4. A
    média seria puxada por três níveis que duram 45 minutos e somem."""
    assert 1.40 <= fator_mediano(lobby) <= 1.45
    bbs = [n[2] for n in ESCADA]
    media = sum(b / a for a, b in zip(bbs, bbs[1:])) / (len(bbs) - 1)
    assert media > fator_mediano(lobby) + 0.05, (
        "sem o começo dobrado este teste não estaria medindo nada")


def test_a_meia_vida_sai_da_escada_e_do_relogio(lobby):
    """×1,43 a cada 15 min => metade do stack em bb a cada ~29 min."""
    assert 28 <= meia_vida_min(lobby) <= 30


def test_a_pausa_entra_na_conta_do_relogio(lobby):
    """5 min a cada 55 empurram o nível 12 em 15 minutos. Quem ignora a pausa
    erra para MENOS — chega achando que tem mais tempo do que tem."""
    com = minuto_do_nivel(lobby, 12)
    sem = minuto_do_nivel(lobby._replace(pausa_min=None, pausa_cada_min=None), 12)
    assert sem == 165 and com == 180, (com, sem)


def test_o_push_fold_tem_nivel_E_hora(lobby):
    """O número que decide: sem ganhar nada, ele está em push/fold no nível
    12, três horas depois de sentar."""
    pf = quando_vira_push_fold(lobby)
    assert pf.nivel == 12
    assert 16 <= pf.stack_bb <= 17
    assert pf.minuto == 180


def test_o_late_reg_diz_com_quanto_se_entra_no_fim(lobby):
    """167 bb no último minuto do registro — entrar tarde aqui não é entrar
    curto, e isso muda a decisão."""
    assert round(stack_no_fim_do_late_reg(lobby)) == 167


def test_o_nome_do_torneio_mente_e_a_conta_nao(lobby):
    """"MonsterStackHyperTur": nível de 15 minutos e 2.000 bb de stack. O
    rótulo diz hyper; a estrutura é lenta."""
    from app.analysis.estrutura import _ritmo

    assert _ritmo(lobby.minutos_por_nivel) == "regular"
    assert "hyper" in lobby.nome.lower()


# ---- a conferência ----------------------------------------------------------

def test_a_escada_da_foto_bate_com_as_maos_reais_em_escala(lobby):
    """O caso que existiu antes do módulo: print em 25/50, mãos em
    2.500/5.000 — a mesma escada ×100."""
    batidos, total, escala = conferir_com_maos(lobby, maos_do_clube())
    assert (batidos, total) == (14, 14)
    assert escala == pytest.approx(100.0)


def test_leitura_errada_da_tela_e_PEGA(lobby):
    """Três níveis lidos com 15% de erro — o tipo de coisa que OCR faz com
    "1,500" e "1,600". Sem esta conferência, viraria plano de jogo."""
    ruim = [list(n) for n in ESCADA]
    for i in (8, 11, 13):
        ruim[i][2] *= 1.15
    torto = lobby._replace(niveis=tuple(Nivel(*n) for n in ruim))
    batidos, total, _ = conferir_com_maos(torto, maos_do_clube())
    assert batidos < total, "a escada corrompida passou como se estivesse certa"
    assert "⚠️" in texto(torto, conferir_com_maos(torto, maos_do_clube()))


def test_sem_maos_do_clube_a_conferencia_CALA(lobby):
    """Torneio novo, clube novo: não há com o que conferir. "Não sei" não
    pode virar nem aprovação nem alarme."""
    assert conferir_com_maos(lobby, []) == (0, 0, None)
    t = texto(lobby, conferir_com_maos(lobby, []))
    assert "⚠️" not in t and "conferida" not in t


# ---- o que falta na tela ----------------------------------------------------

def test_campo_que_a_sala_nao_mostra_nao_vira_invencao(lobby):
    """Sala diferente mostra campo diferente. Faltar é normal; preencher com
    palpite não é."""
    magro = Lobby(niveis=tuple(Nivel(*n) for n in ESCADA))
    assert linha_do_tempo(magro) == []
    assert quando_vira_push_fold(magro) is None
    assert stack_no_fim_do_late_reg(magro) is None
    assert meia_vida_min(magro) is None
    t = texto(magro)
    assert "push/fold" not in t and "Late reg" not in t
    assert fator_mediano(magro), "o que dá para saber pela escada continua saindo"


def test_escada_de_um_nivel_so_nao_quebra():
    magro = Lobby(niveis=(Nivel(1, 25, 50, 0),))
    assert fator_mediano(magro) is None
    assert meia_vida_min(magro) is None
    assert isinstance(texto(magro), str)


def test_o_texto_traz_os_numeros_da_decisao(lobby):
    t = texto(lobby, conferir_com_maos(lobby, maos_do_clube()))
    assert "2000 bb" in t
    assert "15 min" in t
    assert "nível 12" in t and "3h00" in t
    assert "167 bb" in t
    assert "Rebuy" in t, "rebuy muda o early e não pode ficar de fora"
    assert "14/14" in t
