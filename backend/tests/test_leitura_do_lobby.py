"""A visão transcreve o lobby; a conta continua sendo do código.

Os dois prints reais do "MonsterStackHyperTur" (PDQ Online) são o gabarito.
O que se prende aqui não é a acurácia do modelo — isso a conferência contra
as mãos do aluno resolve, em `test_lobby_do_torneio.py` — e sim o que
acontece com o que ele devolve:

  * "100K" tem que virar 100000, e "1,000" tem que virar mil, não um;
  * a 2ª passada MANDA nos campos em que discorda da 1ª, e a divergência
    fica registrada em vez de sumir;
  * campo que a tela não mostra volta null, e não um padrão inventado;
  * sem tabela de blinds não há lobby nenhum.

O modelo é dublê em todos: chamada de verdade custa dinheiro e não é
determinística, e o que se está testando é o encanamento.
"""
from __future__ import annotations

import json

import pytest

import app.agent.llm as llm

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64

# a tabela como está no print
NIVEIS = [{"nivel": 1, "sb": 25, "bb": 50, "ante": 0},
          {"nivel": 2, "sb": 50, "bb": 100, "ante": 0},
          {"nivel": 3, "sb": 100, "bb": 200, "ante": 25},
          {"nivel": 4, "sb": 200, "bb": 400, "ante": 50},
          {"nivel": 5, "sb": 300, "bb": 600, "ante": 75},
          {"nivel": 6, "sb": 400, "bb": 800, "ante": 100}]

LEITURA = {"nome": "MonsterStackHyperTur", "buyin": 85, "taxa": 15,
           "fichas_iniciais": "100K", "minutos_por_nivel": 15,
           "late_reg_nivel": 5, "pausa_min": 5, "pausa_cada_min": 55,
           "rebuy": "3 Vezes/1×", "addon": "Não", "jogadores": 3,
           "faixa_max": 200, "niveis": NIVEIS}


class _Bloco:
    type = "text"

    def __init__(self, texto):
        self.text = texto


class _Resp:
    def __init__(self, payload):
        self.content = [_Bloco(json.dumps(payload, ensure_ascii=False))]


@pytest.fixture
def visao(monkeypatch):
    """Instala as respostas das duas passadas e conta as chamadas."""
    monkeypatch.setattr(llm, "set_tarefa", lambda *a, **k: None)

    class _S:
        anthropic_api_key = "chave-de-teste"
        analysis_model = "modelo"

    monkeypatch.setattr(llm, "get_settings", lambda: _S())
    monkeypatch.setitem(__import__("sys").modules, "anthropic",
                        type("m", (), {"Anthropic": lambda **k: object()}))

    def _instalar(primeira, segunda=None):
        respostas = [primeira, segunda if segunda is not None
                     else {"confere": True, "divergencias": [], "correcao": {}}]
        chamadas = []

        def _create(_client, **kw):
            chamadas.append(kw)
            return _Resp(respostas[min(len(chamadas) - 1, 1)])

        monkeypatch.setattr(llm, "_create", _create)
        return chamadas
    return _instalar


# ---- transcrição -> números -------------------------------------------------

def test_o_print_vira_lobby_com_as_unidades_certas(visao):
    visao(LEITURA)
    lobby = llm.extract_lobby_from_image(PNG)
    assert lobby.fichas_iniciais == 100_000, "'100K' não virou cem mil"
    assert lobby.minutos_por_nivel == 15
    assert lobby.late_reg_nivel == 5
    assert (lobby.pausa_min, lobby.pausa_cada_min) == (5, 55)
    assert lobby.buyin == 85 and lobby.taxa == 15
    assert len(lobby.niveis) == 6
    assert lobby.niveis[0].bb == 50 and lobby.niveis[2].ante == 25


def test_separador_de_milhar_nao_vira_decimal(visao):
    """"1,000/2,000" com ante "1,000" é mil — não um. É o erro que
    transformaria o nível 9 em blind 1 e o plano inteiro em lixo."""
    visao({"niveis": [{"nivel": 9, "sb": "1,000", "bb": "2,000",
                       "ante": "300"},
                      {"nivel": 14, "sb": "5,000", "bb": "10K",
                       "ante": "1,500"}],
           "fichas_iniciais": "1.000.000"})
    lobby = llm.extract_lobby_from_image(PNG)
    assert [n.bb for n in lobby.niveis] == [2000.0, 10000.0]
    assert lobby.niveis[0].ante == 300 and lobby.niveis[1].ante == 1500
    assert lobby.fichas_iniciais == 1_000_000


def test_campo_ausente_volta_null_e_nao_um_padrao(visao):
    """O print da ABA DE BLINDS mostra só a tabela. Preencher o resto com
    padrão é inventar em silêncio — e a conta lá na frente já cala sozinha."""
    visao({"niveis": NIVEIS})
    lobby = llm.extract_lobby_from_image(PNG)
    assert lobby.minutos_por_nivel is None
    assert lobby.fichas_iniciais is None
    assert lobby.late_reg_nivel is None
    assert len(lobby.niveis) == 6

    from app.analysis.lobby import quando_vira_push_fold, texto

    assert quando_vira_push_fold(lobby) is None
    assert "push/fold" not in texto(lobby)


def test_sem_tabela_de_blinds_nao_ha_lobby(visao):
    visao({"nome": "Torneio X", "minutos_por_nivel": 15, "niveis": []})
    assert llm.extract_lobby_from_image(PNG) is None


def test_linha_ilegivel_e_descartada_e_nao_vira_zero(visao):
    """Nível com bb nulo não pode entrar valendo 0 — dividir stack por zero
    mais adiante, ou pior, virar "blind zero" no texto."""
    visao({"niveis": NIVEIS + [{"nivel": 7, "sb": None, "bb": None,
                                "ante": None}]})
    lobby = llm.extract_lobby_from_image(PNG)
    assert len(lobby.niveis) == 6
    assert all(n.bb > 0 for n in lobby.niveis)


def test_a_escada_sai_ordenada_por_nivel(visao):
    baguncado = list(reversed(NIVEIS))
    visao({"niveis": baguncado})
    lobby = llm.extract_lobby_from_image(PNG)
    assert [n.nivel for n in lobby.niveis] == [1, 2, 3, 4, 5, 6]


# ---- a segunda passada ------------------------------------------------------

def test_a_segunda_passada_corrige_a_primeira(visao):
    """O ponto da conferência: um blind lido errado no meio da escada não
    PARECE errado. Quem olha de novo sabendo o que conferir tem tarefa mais
    fácil, então a 2ª leitura manda no que ela discorda."""
    errada = dict(LEITURA, minutos_por_nivel=45)
    visao(errada, {"confere": False,
                   "divergencias": ["minutos_por_nivel: li 15, a 1ª diz 45"],
                   "correcao": {"minutos_por_nivel": 15}})
    lobby = llm.extract_lobby_from_image(PNG)
    assert lobby.minutos_por_nivel == 15, "a correção da 2ª passada foi ignorada"
    assert llm.LAST_LOBBY_CHECK["conferido"] is False
    assert llm.LAST_LOBBY_CHECK["divergencias"]


def test_divergencia_sem_correcao_ainda_fica_registrada(visao):
    """"AMBÍGUO: a linha do nível 12 está cortada" não tem conserto, mas o
    coach precisa saber para perguntar em vez de seguir calado."""
    visao(LEITURA, {"confere": False,
                    "divergencias": ["AMBÍGUO: nível 12 cortado na tela"],
                    "correcao": {}})
    lobby = llm.extract_lobby_from_image(PNG)
    assert lobby is not None
    assert llm.LAST_LOBBY_CHECK == {
        "divergencias": ["AMBÍGUO: nível 12 cortado na tela"],
        "conferido": False}


def test_conferencia_que_explode_nao_derruba_a_leitura(visao, monkeypatch):
    """CONTRATO HONESTO: se a 2ª chamada falhar (rede, cota), fica a 1ª
    leitura — sem conferência é pior que com, e melhor que nada."""
    chamadas = []

    def _create(_c, **kw):
        chamadas.append(kw)
        if len(chamadas) == 1:
            return _Resp(LEITURA)
        raise RuntimeError("sem cota")

    visao(LEITURA)
    monkeypatch.setattr(llm, "_create", _create)
    lobby = llm.extract_lobby_from_image(PNG)
    assert lobby is not None and lobby.minutos_por_nivel == 15
    assert llm.LAST_LOBBY_CHECK["conferido"] is True


def test_a_leitura_sao_DUAS_chamadas_e_nao_uma(visao):
    chamadas = visao(LEITURA)
    llm.extract_lobby_from_image(PNG)
    assert len(chamadas) == 2, "a conferência não aconteceu"
    assert chamadas[0]["temperature"] == 0.0, "transcrição tem que ser fria"


def test_sem_chave_devolve_None_em_vez_de_explodir(monkeypatch):
    monkeypatch.setattr(llm, "set_tarefa", lambda *a, **k: None)

    class _S:
        anthropic_api_key = ""
        analysis_model = "m"

    monkeypatch.setattr(llm, "get_settings", lambda: _S())
    assert llm.extract_lobby_from_image(PNG) is None


def test_o_extrator_nao_faz_conta_nenhuma():
    """A divisão é clara e vale prender: visão transcreve, código calcula.
    Se um dia alguém puser meia-vida ou push/fold aqui dentro, os dois
    caminhos passam a poder discordar."""
    import inspect

    fonte = inspect.getsource(llm.extract_lobby_from_image) + \
        inspect.getsource(llm._lobby_do_json)
    for proibido in ("meia_vida", "push_fold", "linha_do_tempo", "math.log"):
        assert proibido not in fonte, f"conta vazou para o extrator: {proibido}"
