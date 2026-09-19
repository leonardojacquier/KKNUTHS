"""O teto de saída da análise, medido — não escolhido por preferência.

Em 16/08 19:19 um aluno recebeu 150 caracteres: o selo, a linha do pré-flop e
um '🟡 *' solto no meio da segunda linha do placar. A chamada saiu com
exatamente 1.500 tokens de saída, que era o `max_tokens` da análise.

A medição de 30 dias (`bot_events`/`custo_llm`, tarefa=analise, 380 chamadas):

    mediana  355
    p90      1.193
    p99      1.500   <- censurado: é o próprio teto
    máximo   1.500   <- idem
    no teto  12 de 380 (3,2%)

p99 e máximo colados no teto porque era ELE que os censurava — a distribuição
acima de 1.500 é desconhecida. Então a folga se mede contra o p90, o último
percentil que o teto não distorce. O placar novo (com o conceito explicado
dentro de cada linha) é legitimamente mais longo que o antigo.

Custo: tokens de saída só são cobrados quando gerados. Subir o teto não
encarece as ~90% de chamadas que ficam abaixo de 1.200.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

# Os números da medição, como constantes, para o teste cobrar o DADO.
P90_MEDIDO = 1193
TETO_ANTIGO_DA_ANALISE = 1500      # o teto que cortou a análise de 16/08
TETO_ANTIGO_DA_CONCLUSAO = 1200    # o teto do `_force_text`

ANALISE_INTEIRA = "✅ Você jogou bem — a análise inteira, do pré ao river."


def _bloco(tipo, **kw):
    return SimpleNamespace(type=tipo, **kw)


@pytest.fixture
def llm(monkeypatch):
    from app.agent import llm as modulo

    monkeypatch.setattr(
        modulo, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m",
                               "cheap_model": "barato"})())
    return modulo


def _create_que_anota(pedidos: list[int]):
    def _create(client, **kw):
        pedidos.append(kw["max_tokens"])
        return SimpleNamespace(stop_reason="end_turn",
                               content=[_bloco("text", text=ANALISE_INTEIRA)])

    return _create


def test_teto_da_analise_deixa_folga_sobre_o_p90_medido(llm, monkeypatch):
    """Um teto colado no p99 é um teto colado nele mesmo: o p99 medido É o
    teto. A folga tem de ser medida contra o p90, que ele não censura."""
    pedidos: list[int] = []
    monkeypatch.setattr(llm, "_create", _create_que_anota(pedidos))
    monkeypatch.setattr(llm, "_conferir_numeros", lambda *a: a[4])

    llm.coach({"summary": "PLANO C"}, None)

    assert pedidos, "a análise nem chamou o modelo"
    assert pedidos[0] > TETO_ANTIGO_DA_ANALISE
    assert pedidos[0] >= 3 * P90_MEDIDO, \
        "sem ~3x o p90 medido não há folga para a cauda que o teto censurava"


def test_teto_da_conclusao_de_resgate_sobe_junto(llm, monkeypatch):
    """`_force_text` escreve a conclusão de resgate e a reescrita da
    conferência de números. Cortar ALI produz o mesmo defeito de 16/08, só
    que no plano B — então o teto dele sobe na mesma proporção."""
    pedidos: list[int] = []
    monkeypatch.setattr(llm, "_create", _create_que_anota(pedidos))

    assert llm._force_text(None, "m", [], []) == ANALISE_INTEIRA
    assert pedidos[0] > TETO_ANTIGO_DA_CONCLUSAO
    assert pedidos[0] >= 2 * P90_MEDIDO
