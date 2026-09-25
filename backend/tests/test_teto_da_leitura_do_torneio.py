"""A "Leitura do coach" de um TORNEIO tem teto e tamanho próprios.

Caso real de 18/08 22:25-22:33 UTC (torneio de 192 mãos, medido em
`bot_events`/`custo_llm`):

    chamada principal .... entrada 9.050 tokens (as 192 mãos),
                           saída 4.000 = MAX_TOKENS_ANALISE, cortada
    resgate .............. saída 2.500 = MAX_TOKENS_CONCLUSAO, cortada
    entregue ............. plano C — o resumo determinístico de UMA linha
                           ("Torneio…: 192 mãos, +44.8 BB") no lugar da
                           leitura de padrões

A leitura de torneio é a MESMA função `coach()` da análise de mão avulsa (o
sinal é `key_hands`), e herdava dela os dois tetos. Só que ela não é a mesma
coisa: a entrada é o torneio inteiro, e a saída vai para o HTML do relatório
— não para o Telegram, onde o limite de 4.096 chars é que manda.

Duas mãos, porque teto sozinho é convite a ensaio (docs/METODO.md, *"regra é
pedido; conferência é garantia"*):

(a) PEDIDO — a instrução do torneio não pedia tamanho NENHUM. A leitura de
    padrões útil tem ~600-900 tokens; sem alvo, o modelo escreve até o teto.
(b) GARANTIA — teto próprio, maior que o da mão (6.000), e resgate com folga
    na mesma proporção (4.000).

O guarda de corte de 16/08 continua valendo em cima disso: texto que a API
marcou como `stop_reason='max_tokens'` NUNCA é entregue, nem com selo. Com
(a) e (b) o corte vira raridade; ele não deixa de ser tratado.

Tudo determinístico: o cliente é falso, `_create` é capturado, zero rede.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

# A medição de 18/08 22:25, como constantes, para o teste cobrar o DADO.
ENTRADA_MEDIDA = 9050            # tokens de entrada (as 192 mãos do torneio)
SAIDA_CORTADA_NA_PRINCIPAL = 4000    # = MAX_TOKENS_ANALISE, o teto herdado
SAIDA_CORTADA_NO_RESGATE = 2500      # = MAX_TOKENS_CONCLUSAO, idem
ALVO_DE_TAMANHO = (600, 900)     # tokens úteis de uma leitura de padrões

LEITURA_INTEIRA = ("✅ Você jogou bem — a leitura inteira do torneio, "
                   "com os padrões que decidiram o resultado.")

# O parcial que a API marcou como cortado: COMEÇA com selo (é isso que fura
# a checagem de `_tem_selo`) e para no meio da segunda frase.
LEITURA_CORTADA = ("🟡 Dava pra jogar melhor — o padrão do torneio foi\n\n"
                   "No nível 4 você abriu 2.2bb de UTG com")

KEY_HANDS = [{"hand_id": "H1", "position": "BTN", "net_bb": -40.0},
             {"hand_id": "H2", "position": "BB", "net_bb": 18.5}]


def _bloco(tipo, **kw):
    return SimpleNamespace(type=tipo, **kw)


class _Repo:
    enabled = True

    def __init__(self):
        self.eventos: list[tuple[str, dict]] = []

    def log_event(self, tid, user, event, detail):
        self.eventos.append((event, detail))


@pytest.fixture
def repo(monkeypatch):
    r = _Repo()
    monkeypatch.setattr("app.db.get_repository", lambda: r)
    return r


@pytest.fixture
def llm(monkeypatch):
    from app.agent import llm as modulo

    monkeypatch.setattr(
        modulo, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m",
                               "cheap_model": "barato"})())
    return modulo


def _create_que_anota(pedidos: list[dict], respostas=None):
    """Captura o kwargs de CADA chamada — é o pedido que sai para a API."""
    fila = iter(respostas or [])

    def _create(client, **kw):
        pedidos.append(kw)
        try:
            return next(fila)
        except StopIteration:
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[_bloco("text", text=LEITURA_INTEIRA)])

    return _create


def _texto_do_pedido(kw: dict) -> str:
    """O que o aluno-modelo leu: o conteúdo da mensagem de usuário."""
    return "\n".join(
        m["content"] if isinstance(m["content"], str) else str(m["content"])
        for m in kw["messages"] if m["role"] == "user")


def _identidade_da_conferencia(*a, **k):
    """`_conferir_numeros(...)` neutralizado: a reescrita dele mandaria uma
    chamada a mais e embaralharia a contagem de pedidos."""
    return a[4]


def test_a_leitura_do_torneio_tem_teto_proprio_maior_que_o_da_mao(
        llm, monkeypatch, repo):
    """O teto de 4.000 cortou a leitura de 192 mãos em 18/08. Ele é o teto da
    análise de UMA mão, que vai para o Telegram; a leitura vai para o HTML do
    relatório, onde não existe limite de 4.096 chars."""
    pedidos: list[dict] = []
    monkeypatch.setattr(llm, "_create", _create_que_anota(pedidos))
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)

    llm.coach({"summary": "Torneio…: 192 mãos, +44.8 BB"}, None,
              key_hands=KEY_HANDS)

    assert pedidos, "a leitura do torneio nem chamou o modelo"
    assert pedidos[0]["max_tokens"] > SAIDA_CORTADA_NA_PRINCIPAL, \
        "a leitura de torneio continua no teto que a cortou em 18/08"
    assert pedidos[0]["max_tokens"] >= 6000


def test_a_analise_de_mao_avulsa_nao_herda_o_teto_do_torneio(
        llm, monkeypatch, repo):
    """A mão avulsa vai para o Telegram (4.096 chars) e tem teto MEDIDO em 30
    dias. Ela não pode subir de carona no conserto do torneio."""
    pedidos: list[dict] = []
    monkeypatch.setattr(llm, "_create", _create_que_anota(pedidos))
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)

    llm.coach({"summary": "PLANO C"}, None)

    assert pedidos[0]["max_tokens"] == llm.MAX_TOKENS_ANALISE


def test_a_instrucao_do_torneio_pede_um_tamanho_alvo(llm, monkeypatch, repo):
    """Teto sem pedido é convite a ensaio: o modelo escreve até onde deixarem.
    A instrução do torneio não pedia tamanho NENHUM — a leitura de padrões
    tem ~600-900 tokens úteis, e é isso que o pedido tem de dizer."""
    pedidos: list[dict] = []
    monkeypatch.setattr(llm, "_create", _create_que_anota(pedidos))
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)

    llm.coach({"summary": "Torneio…: 192 mãos, +44.8 BB"}, None,
              key_hands=KEY_HANDS)

    texto = _texto_do_pedido(pedidos[0])
    assert "TAMANHO" in texto, "o pedido do torneio não fala de tamanho"
    baixo, alto = ALVO_DE_TAMANHO
    assert str(baixo) in texto and str(alto) in texto, \
        f"o alvo medido ({baixo}-{alto} tokens) não chegou ao modelo"


def test_a_mao_avulsa_nao_recebe_o_alvo_de_tamanho_do_torneio(
        llm, monkeypatch, repo):
    """O alvo é da LEITURA de padrões. Colá-lo na análise de mão mexeria no
    tamanho de um texto que já cabe no teto medido."""
    pedidos: list[dict] = []
    monkeypatch.setattr(llm, "_create", _create_que_anota(pedidos))
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)

    llm.coach({"summary": "PLANO C"}, None)

    assert "TAMANHO" not in _texto_do_pedido(pedidos[0])


def test_o_resgate_da_leitura_do_torneio_ganha_folga_junto(
        llm, monkeypatch, repo):
    """Em 18/08 o resgate cortou EM SEGUIDA, nos 2.500 da conclusão de mão.
    Resgate cortado é plano C — o teto dele sobe na mesma proporção."""
    pedidos: list[dict] = []
    cortada = SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("text", text=LEITURA_CORTADA)])
    resgatada = SimpleNamespace(
        stop_reason="end_turn",
        content=[_bloco("text", text=LEITURA_INTEIRA)])
    monkeypatch.setattr(llm, "_create",
                        _create_que_anota(pedidos, [cortada, resgatada]))
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)

    out = llm.coach({"summary": "Torneio…: 192 mãos, +44.8 BB"}, None,
                    key_hands=KEY_HANDS)

    assert out == LEITURA_INTEIRA
    assert len(pedidos) == 2, "o resgate não rodou"
    assert pedidos[1]["max_tokens"] > SAIDA_CORTADA_NO_RESGATE, \
        "o resgate do torneio continua no teto que o cortou em 18/08"
    assert pedidos[1]["max_tokens"] >= 4000


def test_o_resgate_da_mao_avulsa_continua_no_teto_medido(
        llm, monkeypatch, repo):
    """A outra ponta do mesmo cuidado: a conclusão de resgate da mão avulsa
    tem teto medido (2.500) e não sobe junto."""
    pedidos: list[dict] = []
    cortada = SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("text", text=LEITURA_CORTADA)])
    resgatada = SimpleNamespace(
        stop_reason="end_turn",
        content=[_bloco("text", text=LEITURA_INTEIRA)])
    monkeypatch.setattr(llm, "_create",
                        _create_que_anota(pedidos, [cortada, resgatada]))
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)

    llm.coach({"summary": "PLANO C"}, None)

    assert pedidos[1]["max_tokens"] == llm.MAX_TOKENS_CONCLUSAO


def test_o_guarda_de_corte_continua_valendo_no_torneio(llm, monkeypatch, repo):
    """Teto maior reduz a chance; não elimina. Se a leitura cortar mesmo com
    6.000 e o resgate não vier, o aluno lê o resumo honesto — nunca a meia
    frase — e o corte vira evento contável."""
    cortada = SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("text", text=LEITURA_CORTADA)])
    monkeypatch.setattr(llm, "_create", lambda *a, **k: cortada)
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)
    monkeypatch.setattr(llm, "_force_text", lambda *a, **k: None)

    out = llm.coach({"summary": "Torneio…: 192 mãos, +44.8 BB"}, None,
                    key_hands=KEY_HANDS)

    assert out == "Torneio…: 192 mãos, +44.8 BB"
    assert "No nível 4" not in out, "meia leitura foi entregue ao aluno"
    nomes = [e for e, _ in repo.eventos]
    assert "analise_cortada" in nomes and "plano_c" in nomes
