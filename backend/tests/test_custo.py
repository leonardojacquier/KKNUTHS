"""O custo medido tem que bater com a conta feita à mão.

Isto não é teste de fumaça: se o cálculo errar, o preço do produto sai
errado junto — e o erro só apareceria na fatura, meses depois.
"""
from types import SimpleNamespace

from app.agent import custo


class _Usage:
    def __init__(self, i=0, o=0, cr=0, cw=0):
        self.input_tokens = i
        self.output_tokens = o
        self.cache_read_input_tokens = cr
        self.cache_creation_input_tokens = cw


def _resp(**kw):
    return SimpleNamespace(usage=_Usage(**kw))


# ------------------------------------------------------------------ preços
def test_preco_aceita_sufixo_de_data():
    # o .env de produção usa 'claude-haiku-4-5-20251001'
    assert custo.preco_do_modelo("claude-haiku-4-5-20251001") == (1.0, 5.0)
    assert custo.preco_do_modelo("claude-opus-4-8") == (5.0, 25.0)


def test_modelo_desconhecido_nao_vira_zero():
    """Custo falso é pior que custo nenhum: parece medição."""
    assert custo.preco_do_modelo("gpt-qualquer-coisa") is None
    assert custo.custo_usd("gpt-qualquer-coisa", 1000, 1000) is None


def test_conta_de_dolar_bate_na_mao():
    # Opus 4.8: 1M entrada = $5, 1M saída = $25
    assert custo.custo_usd("claude-opus-4-8", 1_000_000, 0) == 5.0
    assert custo.custo_usd("claude-opus-4-8", 0, 1_000_000) == 25.0
    # 20k entrada + 2k saída = 0,10 + 0,05
    assert custo.custo_usd("claude-opus-4-8", 20_000, 2_000) == 0.15


def test_cache_muda_o_custo_em_ordem_de_grandeza():
    """Ignorar o cache daria um número inventado — ele já está ligado."""
    cheio = custo.custo_usd("claude-opus-4-8", 100_000, 0)
    lido = custo.custo_usd("claude-opus-4-8", 0, 0, cache_leitura=100_000)
    escrito = custo.custo_usd("claude-opus-4-8", 0, 0, cache_escrita=100_000)
    assert lido == round(cheio * 0.10, 6)      # leitura 0,1x
    assert escrito == round(cheio * 1.25, 6)   # escrita 1,25x (TTL 5 min)


# ------------------------------------------------------------------- medir
def test_medir_le_os_quatro_campos():
    reg = custo.medir(_resp(i=1000, o=500, cr=20_000, cw=3_000),
                      "claude-opus-4-8", "analise")
    assert reg["entrada"] == 1000 and reg["saida"] == 500
    assert reg["cache_leitura"] == 20_000 and reg["cache_escrita"] == 3_000
    assert reg["tarefa"] == "analise"
    esperado = custo.custo_usd("claude-opus-4-8", 1000, 500, 20_000, 3_000)
    assert reg["usd"] == esperado


def test_resposta_sem_usage_nao_inventa_registro():
    assert custo.medir(SimpleNamespace(), "claude-opus-4-8") is None
    assert custo.medir(_resp(), "claude-opus-4-8") is None


def test_registrar_nunca_levanta():
    """Contabilidade não pode derrubar a resposta do aluno."""
    assert custo.registrar(object(), "claude-opus-4-8", "analise") is None


# ------------------------------------------------------------------- somar
def _ev(tg, usd, tarefa="analise", entrada=0, saida=0):
    return {"telegram_id": tg,
            "detail": {"usd": usd, "tarefa": tarefa,
                       "entrada": entrada, "saida": saida}}


def test_somar_quebra_por_tarefa_e_por_pessoa():
    agr = custo.somar([_ev(1, 0.30), _ev(1, 0.20, "conversa"), _ev(2, 0.90)])
    assert agr["usd"] == 1.4
    assert agr["por_tarefa"] == {"analise": 1.2, "conversa": 0.2}
    assert list(agr["por_pessoa"]) == [2, 1]   # ordenado pelo maior gasto
    assert agr["chamadas_sem_preco"] == 0


def test_somar_avisa_quando_o_total_esta_subestimado():
    agr = custo.somar([_ev(1, 0.30), _ev(1, None)])
    assert agr["usd"] == 0.3
    assert agr["chamadas_sem_preco"] == 1
    assert "SUBESTIMADO" in custo.texto_do_mes(agr)


def test_somar_conta_todos_os_tokens_de_entrada():
    """input_tokens é só o resto NÃO cacheado — somar só ele esconde o volume."""
    agr = custo.somar([{"telegram_id": 1, "detail": {
        "usd": 0.1, "tarefa": "analise", "entrada": 1000, "saida": 200,
        "cache_leitura": 20_000, "cache_escrita": 4_000}}])
    assert agr["tokens_entrada"] == 25_000
    assert agr["tokens_saida"] == 200


# ------------------------------------------------------------------- texto
def test_texto_mostra_custo_por_analise():
    agr = custo.somar([_ev(7, 1.50)])
    txt = custo.texto_do_mes(agr, nomes={7: "leo"}, usos={7: 3})
    assert "leo" in txt and "US$ 0.50/análise" in txt


def test_texto_sem_dados_e_honesto():
    txt = custo.texto_do_mes(custo.somar([]))
    assert "Nenhuma chamada registrada" in txt


# ------------------------------------------------------------------ ligação
def test_create_registra_o_custo_com_a_tarefa_certa():
    """O módulo pode estar perfeito e não estar LIGADO — foi assim que o
    gráfico de EV existiu por semanas sem nunca ser chamado."""
    from app.agent import llm

    vistos = []

    class _Fake:
        class messages:
            @staticmethod
            def create(**kw):
                return _resp(i=100, o=50)

    original = custo.registrar
    custo.registrar = lambda *a, **k: vistos.append(a)
    try:
        llm.set_tarefa("conversa")
        llm.set_tool_chat(4242)
        llm._create(_Fake(), model="claude-opus-4-8", messages=[])
    finally:
        custo.registrar = original
        llm.set_tarefa("outro")
        llm.set_tool_chat(None)

    assert len(vistos) == 1
    _resposta, modelo, tarefa, chat, _user = vistos[0]
    assert (modelo, tarefa, chat) == ("claude-opus-4-8", "conversa", 4242)


def test_toda_chamada_do_produto_passa_pelo_porteiro():
    """Canário: uma `messages.create` fora do `_create` gasta dinheiro que
    a contabilidade nunca vê. Regra que varre o diretório, não lista fixa —
    a lista fixa é whitelist e não pega o arquivo novo."""
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parent.parent / "app"
    fora = []
    for arq in raiz.rglob("*.py"):
        for n, linha in enumerate(arq.read_text().splitlines(), 1):
            if "messages.create(" not in linha:
                continue
            if arq.name == "llm.py" and "client.messages.create(**kw)" in linha:
                continue  # o porteiro em pessoa
            fora.append(f"{arq.relative_to(raiz)}:{n}")
    assert not fora, ("chamada ao modelo fora de llm._create (custo invisível): "
                      + ", ".join(fora))
