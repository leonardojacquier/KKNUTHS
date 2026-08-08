"""O incidente do VPIP 94% — o conserto estrutural.

O coach disse ao Ricardo, no meio de uma análise: "seu VPIP tá em 93,6%,
joga MUITO lixo". O VPIP real dele, em 406.639 mãos, é 26%. O número saiu de
53 replays que ELE escolheu mandar.

Isso NÃO foi amostra pequena. Foi viés de seleção: com 53 replays escolhidos
por ele dá 94%; com 5.000 replays escolhidos por ele TAMBÉM daria 94%.
Amostra maior não conserta viés — o estimador converge para o valor errado.
São duas doenças diferentes e esta é a pior.

O cálculo foi consertado em 07/08. Mas a LINHA velha continuou em
`player_stats` — e seguiu sendo injetada como `perfil_do_jogador` no
contexto do coach a cada pergunta aberta do aluno. Conferido no banco de
produção em 08/08: `hands=53, vpip=94.3, label='LAG'`. Ou seja: consertar a
conta não bastou, porque ninguém relê uma tabela.

Por isso o portão está em TRÊS lugares, e o do meio é o que faltava:
  1. no cálculo   — `amostra_completa` descarta replay/print
  2. na ESCRITA   — taxa que a amostra não sustenta não é gravada
  3. na leitura   — `perfil_que_pode_ser_dito` e o `taxa()` do portal
"""
from __future__ import annotations

import pytest

from app.analysis.stats import (AmostraCurada, PlayerStats,
                                exigir_amostra_completa, margem_de_erro_pp)


class _Mao:
    def __init__(self, fonte):
        self.source_format = fonte


# ---- o portão que ESTOURA --------------------------------------------------

def test_frequencia_sobre_replay_levanta_excecao():
    """Não é aviso: é exceção. 'Tomar cuidado ao usar' foi o que existia, e
    o número errado foi para a tela do aluno mesmo assim."""
    with pytest.raises(AmostraCurada) as e:
        exigir_amostra_completa([_Mao("pppoker_replay")] * 53, "VPIP")
    assert "53 de 53" in str(e.value)


def test_uma_mao_curada_no_meio_ja_contamina():
    """Frequência é sobre a distribuição inteira — uma mão escolhida a dedo
    no meio de 99 já enviesa o denominador."""
    with pytest.raises(AmostraCurada):
        exigir_amostra_completa([_Mao("txt")] * 99 + [_Mao("image")], "VPIP")


def test_sessao_inteira_passa():
    exigir_amostra_completa([_Mao("txt")] * 50 + [_Mao("csv")] * 10, "VPIP")


def test_o_portao_nao_atrapalha_analise_de_mao():
    """Replay avulso continua sendo dado legítimo para analisar AQUELA mão —
    a conta é sobre a mão, não sobre a distribuição do jogo do aluno. Se o
    portão pegasse esse caminho, a ferramenta perdia a função principal."""
    import inspect

    from app.analysis import stats

    doc = inspect.getdoc(stats.exigir_amostra_completa)
    assert "não vale para análise da mão" in doc.lower()


# ---- a margem que impede a promessa de precisão ----------------------------

@pytest.mark.parametrize("n,esperado", [(53, 11.9), (150, 7.1), (3000, 1.6)])
def test_margem_de_erro(n, esperado):
    assert margem_de_erro_pp(n) == pytest.approx(esperado, abs=0.2)


def test_amostra_curta_tem_margem_enorme():
    """Com 1 mão a margem cobre o intervalo inteiro — é o jeito aritmético
    de dizer 'não sei'. (O ANTONIO PIRES estava no banco com VPIP 100% e
    hands=1.)"""
    assert margem_de_erro_pp(1) > 50


# ---- o rótulo de estilo é afirmação sobre QUEM a pessoa é ------------------

def test_rotulo_de_estilo_exige_amostra_que_o_sustente():
    """'calling station' cola no aluno. Com 57 mãos o VPIP tem ±11pp — o
    rótulo pode ser outro. O NÚMERO sai (com a margem); o rótulo não."""
    from app.analysis.stats import _label

    curto = PlayerStats(player="hero", hands=57, vpip=42.1, pfr=17.5, af=1.2)
    assert "curta" in _label(curto)
    assert "station" not in _label(curto)

    longo = PlayerStats(player="hero", hands=305, vpip=42.1, pfr=17.5, af=1.2)
    assert "station" in _label(longo)


# ---- o portão na ESCRITA (o que faltava) ----------------------------------

class _Upsert:
    def __init__(self, capturado):
        self.capturado = capturado

    def upsert(self, payload, on_conflict=None):
        self.capturado.append(payload)
        return self

    def insert(self, payload):
        self.capturado.append(payload)
        return self

    def execute(self):
        return type("R", (), {"data": [], "count": 0})()


def _repo(capturado):
    from app.db.repository import Repository

    class _Cli:
        def table(self, nome):
            return _Upsert(capturado)

    r = Repository.__new__(Repository)
    r.enabled = True
    r._url = r._key = "x"
    r._client = _Cli()
    return r


def test_taxa_que_a_amostra_nao_sustenta_nao_e_gravada():
    """O caso do Ricardo, exatamente: 53 mãos, todas curadas."""
    cap: list = []
    s = PlayerStats(player="hero", hands=53, vpip=94.3, pfr=50.9, af=3.0,
                    detail={"amostra_viesada": True})
    assert s.publicavel is False
    _repo(cap).upsert_player_stats("u-1", s)

    gravado = cap[0]
    assert gravado["vpip"] is None and gravado["pfr"] is None
    assert gravado["hands"] == 53, "o volume é honesto e deve ficar"
    assert gravado["detail"]["publicavel"] is False


def test_perfil_bom_e_gravado_inteiro():
    cap: list = []
    s = PlayerStats(player="hero", hands=305, vpip=23.3, pfr=16.7, af=1.8)
    _repo(cap).upsert_player_stats("u-1", s)
    assert cap[0]["vpip"] == 23.3 and cap[0]["detail"]["publicavel"] is True


def test_evolucao_nao_desenha_o_que_o_stats_se_recusa_a_dizer():
    """Sem isto, o /evolucao plotava a linha do tempo de um número que o
    /stats não fala — o mesmo jogador se contradizendo entre comandos."""
    cap: list = []
    ruim = PlayerStats(player="hero", hands=53, vpip=94.3,
                       detail={"amostra_viesada": True})
    _repo(cap).snapshot_player_stats("u-1", ruim, net_bb=-3.0)
    assert cap == [], "gravou ponto de evolução sobre amostra curada"


# ---- o portão na LEITURA (por onde chegava ao aluno) ----------------------

def test_o_coach_nao_recebe_frequencia_de_amostra_curada():
    from app.bot.processing import perfil_que_pode_ser_dito

    p = perfil_que_pode_ser_dito(
        {"hands": 53, "vpip": 94.3, "detail": {"publicavel": False}})
    assert p["frequencias"] is None
    assert "PROIBIDO" in p["por_que_sem_perfil"]
    assert "94" not in str(p), "o número vazou para o contexto do coach"


def test_o_coach_sabe_que_o_aluno_existe_mesmo_sem_perfil():
    """Devolver None faria o coach tratar o Ricardo como aluno novo — ele
    mandou 92 mãos, só que pelo canal errado."""
    from app.bot.processing import perfil_que_pode_ser_dito

    p = perfil_que_pode_ser_dito(
        {"hands": 53, "vpip": None, "detail": {"publicavel": False}})
    assert p["maos_na_amostra"] == 53


def test_perfil_bom_chega_com_a_margem_junto():
    from app.bot.processing import perfil_que_pode_ser_dito

    p = perfil_que_pode_ser_dito({"hands": 305, "vpip": 23.3, "detail": {}})
    assert p["vpip"] == 23.3
    assert "margem" in p["instrucao_margem"]


def test_o_portal_mostra_travessao_e_nao_zero():
    """`p.get('vpip') or 0` virava 'VPIP 0%' — outra mentira, e a mais fácil
    de acreditar porque parece um número."""
    from app.api.admin import taxa

    assert taxa(None) == "—"
    assert "±" in taxa(23.3, 305)
    assert taxa(0.0) == "0.0", "zero de verdade continua sendo zero"
