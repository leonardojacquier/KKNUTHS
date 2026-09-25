"""Contador de progresso: silêncio longo é indistinguível de travamento.

Um torneio de 150 mãos leva minutos. O bot dizia "✅ Recebido" e sumia — o
aluno reenvia ou desiste. E o mesmo silêncio enganou a MIM: sem evento no
recebimento, o banco durante a análise fica igual ao de um bot morto.
"""
import asyncio

from app.bot import progresso


def setup_function():
    progresso._PASSO.clear()


# ------------------------------------------------------------------ texto
def test_texto_mostra_etapa_e_tempo():
    t = progresso.texto_do_contador("Calculando 150 mão(s)", 23)
    assert "Calculando 150 mão(s)" in t and "23s" in t


def test_minutos_aparecem_quando_passa_de_60s():
    assert "2min 05s" in progresso.texto_do_contador("x", 125)
    # abaixo de 45s não há a frase de conforto, que contém "minutos"
    assert "min" not in progresso.texto_do_contador("x", 30)


def test_espera_longa_ganha_frase_de_conforto():
    """Depois de 45s o aluno precisa saber que é normal, senão reenvia."""
    curto = progresso.texto_do_contador("x", 20)
    longo = progresso.texto_do_contador("x", 60)
    assert "alguns minutos" not in curto
    assert "alguns minutos" in longo and "eu aviso" in longo


def test_sem_etapa_usa_o_titulo():
    assert "Analisando" in progresso.texto_do_contador(None, 10, "Analisando")


# ------------------------------------------------------------------ marcar
def test_marcar_e_ler_a_etapa():
    progresso.marcar(42, "Lendo o arquivo")
    assert progresso.passo_atual(42) == "Lendo o arquivo"
    progresso.marcar(42, "Calculando")
    assert progresso.passo_atual(42) == "Calculando"
    progresso.limpar(42)
    assert progresso.passo_atual(42) is None


def test_marcar_nunca_estoura():
    """É chamado do meio da análise: não pode derrubar o trabalho de verdade."""
    progresso.marcar(None, "x")
    progresso.limpar(None)
    assert progresso.passo_atual(None) is None


# ------------------------------------------------------------------ tarefa
class _Msg:
    def __init__(self):
        self.edicoes = []
        self.apagada = False

    async def edit_text(self, texto, **kw):
        self.edicoes.append(texto)

    async def delete(self):
        self.apagada = True


def test_analise_rapida_nao_polui_com_contador():
    """Menos que o piso de tempo: nada é editado, e a mensagem some."""
    progresso.INTERVALO = 0.01
    progresso._MOSTRA_A_PARTIR_DE = 5.0
    m = _Msg()

    async def corpo():
        t = await progresso.acompanhar(m, 7)
        await asyncio.sleep(0.05)
        await progresso.encerrar(t, 7, m)

    asyncio.run(corpo())
    assert m.edicoes == []
    assert m.apagada, "o '⏳' não pode sobrar em cima da resposta pronta"


def test_contador_edita_a_MESMA_mensagem():
    """Editar, não mandar novas: senão o histórico do aluno vira uma parede
    de 'ainda estou trabalhando'."""
    progresso.INTERVALO = 0.01
    progresso._MOSTRA_A_PARTIR_DE = 0.0
    m = _Msg()

    async def corpo():
        progresso.marcar(7, "Lendo o arquivo")
        t = await progresso.acompanhar(m, 7)
        await asyncio.sleep(0.05)
        progresso.marcar(7, "Calculando 150 mão(s)")
        await asyncio.sleep(0.05)
        await progresso.encerrar(t, 7, m, final="✅ pronto")

    asyncio.run(corpo())
    assert len(m.edicoes) >= 2
    assert any("Lendo o arquivo" in e for e in m.edicoes)
    assert any("Calculando 150" in e for e in m.edicoes)
    assert m.edicoes[-1] == "✅ pronto"


def test_falha_ao_editar_nao_derruba_a_analise():
    """Aluno apaga a mensagem, rate limit, texto repetido — nada disso pode
    interromper o trabalho de verdade."""
    class _Ruim(_Msg):
        async def edit_text(self, texto, **kw):
            raise RuntimeError("message to edit not found")

    progresso.INTERVALO = 0.01
    progresso._MOSTRA_A_PARTIR_DE = 0.0
    m = _Ruim()

    async def corpo():
        t = await progresso.acompanhar(m, 7)
        await asyncio.sleep(0.05)
        await progresso.encerrar(t, 7, m)      # não levanta

    asyncio.run(corpo())


def test_handler_registra_o_upload_ANTES_de_analisar():
    """A causa do falso alarme: durante uma análise longa o banco ficava
    idêntico ao de um bot morto."""
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers.on_document)
    i_log = fonte.find("upload_recebido")
    i_proc = fonte.find("process_upload")
    assert i_log > 0, "on_document precisa logar o recebimento"
    assert i_log < i_proc, "o log tem que vir ANTES da análise"
