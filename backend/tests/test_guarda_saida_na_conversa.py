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


def test_o_guarda_de_FATOS_nao_roda_na_conversa(conversa, monkeypatch):
    """LACUNA CONHECIDA, fixada como teste para não ser esquecida.

    `conferir_dominancia` e `corrigir_showdown` rodam só na análise de
    upload. Na conversa livre — onde "só perde para QQ" é mais provável
    ainda, porque o aluno pergunta exatamente sobre mãos — nenhum guarda de
    FATO de poker roda; só o de saída, que trata pedido não atendido.

    Se um dia isso mudar, este teste quebra e a mudança é deliberada. Ele
    NÃO está aqui para dizer que está certo — está para impedir que a
    lacuna volte a ser invisível.
    """
    import inspect

    fonte = inspect.getsource(proc.process_followup)
    assert "conferir_dominancia" not in fonte, (
        "o guarda de fatos passou a rodar na conversa — ótimo. Apague este "
        "teste, escreva um de comportamento no lugar, e tire a lacuna do "
        "METODO.md")
