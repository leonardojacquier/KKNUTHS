"""O guarda da saída roda na CONVERSA, e o texto remediado é o que sai.

O último item da bateria do guarda de saída era:

    assert "conferir_e_remediar" in inspect.getsource(P.process_followup)

Isso confere que o nome aparece no arquivo. Não confere que a função é
chamada, nem — o que importa aqui — que o RETORNO dela substitui a resposta.
E este caso tem uma armadilha a mais que os outros: a chamada mora dentro de
um `try/except Exception` que só loga aviso. Se o guarda quebrar, a resposta
evasiva vai ao aluno em silêncio e o teste por substring continua verde.

O caso é o real: o aluno pergunta o range de EV do turn e o modelo devolve
"Vou te explicar o conceito. Qual dos dois você quer?" — pergunta de volta
em vez de responder.
"""
from __future__ import annotations

import pytest

from app.bot import processing as proc

_TG = 991001
_EVASIVA = "Vou te explicar o conceito. Qual dos dois você quer?"


class _Repo:
    enabled = True

    def __init__(self):
        self.eventos: list = []

    def log_event(self, telegram_id, username, event, detail=None):
        self.eventos.append(event)

    def __getattr__(self, _n):
        return lambda *a, **k: None


@pytest.fixture
def conversa(monkeypatch):
    """Contexto de conversa em memória + LLM falso, com `followup` trocado no
    módulo de ORIGEM (o import é local, dentro da função)."""
    repo = _Repo()
    monkeypatch.setattr(proc, "get_repository", lambda: repo)
    monkeypatch.setattr(proc, "persist_conversation", lambda *a, **k: None)

    import app.agent.llm as llm

    def _instalar(resposta_do_modelo: str):
        monkeypatch.setattr(llm, "followup", lambda *a, **k: resposta_do_modelo)
        proc.lembrar(proc.LAST_ANALYSIS, _TG, {
            "context": {"mao": {"hero_cards": ["Ah", "Kd"]}},
            "history": [], "user_id": None})
        return repo

    yield _instalar
    for mapa in (proc.LAST_ANALYSIS, proc.PENDING_CHARTS):
        mapa.pop(_TG, None)


def test_a_resposta_evasiva_e_remediada_antes_de_sair(conversa, monkeypatch):
    """A asserção que a substring não fazia: o texto que o aluno recebe é o
    do guarda, não o do modelo."""
    repo = conversa(_EVASIVA)

    import app.bot.guarda_saida as gs

    monkeypatch.setattr(gs, "conferir_e_remediar",
                        lambda tg, q, a, tem: ("TEXTO REMEDIADO", []))

    saida = proc.process_followup(_TG, "tester", "Qual o range de EV do turn?")
    assert saida == "TEXTO REMEDIADO", (
        f"a resposta do modelo saiu sem passar pelo guarda: {saida!r}")


def test_o_guarda_recebe_a_pergunta_e_a_resposta_de_verdade(conversa,
                                                            monkeypatch):
    """Passar os argumentos errados é a outra forma de o guarda existir e não
    servir — ele decide comparando o PEDIDO com a ENTREGA."""
    conversa(_EVASIVA)
    visto: dict = {}

    import app.bot.guarda_saida as gs

    def _espiao(tg, pergunta, resposta, tem_grafico):
        visto.update(tg=tg, pergunta=pergunta, resposta=resposta,
                     tem_grafico=tem_grafico)
        return (resposta, [])

    monkeypatch.setattr(gs, "conferir_e_remediar", _espiao)
    proc.process_followup(_TG, "tester", "Qual o range de EV do turn?")

    assert visto.get("tg") == _TG
    assert visto.get("pergunta") == "Qual o range de EV do turn?"
    assert visto.get("resposta") == _EVASIVA, (
        "o guarda recebeu outra coisa em vez da resposta do modelo")
    assert visto.get("tem_grafico") is False


def test_guarda_que_explode_nao_derruba_a_conversa(conversa, monkeypatch):
    """CONTRATO HONESTO: a chamada mora num `try/except Exception` que só
    loga. É decisão deliberada — conversa que morre é pior que conversa não
    remediada — mas tem que estar escrita, porque é também o motivo de o
    teste por substring nunca ter notado nada.
    """
    conversa(_EVASIVA)

    import app.bot.guarda_saida as gs

    def _quebrado(*a, **k):
        raise RuntimeError("guarda quebrado")

    monkeypatch.setattr(gs, "conferir_e_remediar", _quebrado)
    saida = proc.process_followup(_TG, "tester", "Qual o range de EV do turn?")

    assert saida == _EVASIVA, (
        "o guarda explodiu e derrubou a conversa — o aluno merece a resposta "
        "não remediada em vez de erro")


def test_o_guarda_de_FATOS_agora_roda_na_conversa():
    """Esta era a LACUNA CONHECIDA, fixada como teste em 09/08 com a
    instrução "se um dia isso mudar, apague este teste e escreva um de
    comportamento no lugar". Mudou no mesmo dia, e é isso que está abaixo.

    O que fica aqui é só o vínculo: se alguém remover a chamada do
    `process_followup`, o teste de comportamento logo abaixo é quem falha.
    """
    import inspect

    fonte = inspect.getsource(proc.process_followup)
    assert "_conferir_fatos_da_conversa" in fonte


def test_a_dominancia_falsa_e_corrigida_NA_CONVERSA(conversa, monkeypatch):
    """Fim a fim pelo `process_followup`, e não pela função isolada.

    O guarda de fatos vivia num caminho só — a análise do upload. A conversa
    livre entregava texto novo, do modelo, sem nenhuma conferência de fato de
    poker. E é nela que o aluno pergunta justamente sobre mãos.
    """
    repo = conversa("Aqui você só perde para QQ, então pode pagar tranquilo.")
    proc.lembrar(proc.LAST_ANALYSIS, _TG, {
        "context": {"mao": {"hero_cards": ["Kh", "Kd"], "final_board": []}},
        "history": [], "user_id": None})

    import app.bot.guarda_saida as gs

    monkeypatch.setattr(gs, "conferir_e_remediar",
                        lambda tg, q, a, tem: (a, []))

    saida = proc.process_followup(_TG, "tester", "KK contra 4-bet, pago?")
    assert "QQ" not in saida, (
        f"a dominância falsa chegou ao aluno na conversa: {saida!r}")
    assert "AA" in saida, "corrigiu apagando em vez de pôr a verdade"
    assert any(ev == "fato_corrigido" for ev in repo.eventos)
