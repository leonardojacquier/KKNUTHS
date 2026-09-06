"""Crédito zerado não é "me embananei".

Em 2026-07-27 os créditos da API acabaram, toda chamada virou 400 «credit
balance is too low», e o bot dizia ao aluno *"Opa, me embananei aqui"*. O
aluno leva a culpa implícita (o coach se confundiu) e o dono não fica
sabendo — ele descobriu xingando, não sendo avisado.
"""
from app.agent import saude

ERRO_REAL = (
    "BadRequestError: Error code: 400 - {'type': 'error', 'error': "
    "{'type': 'invalid_request_error', 'message': 'Your credit balance is "
    "too low to access the Anthropic API. Please go to Plans & Billing to "
    "upgrade or purchase credits.'}}")


def setup_function():
    saude._ultimo_aviso.clear()
    saude._ultima = None


# ------------------------------------------------------------- classificar
def test_reconhece_o_erro_REAL_de_credito():
    tipo, recado = saude.classificar(ERRO_REAL)
    assert tipo == "sem_credito"
    assert "recarga" in recado and "suporte" in recado
    # e NÃO culpa o aluno nem sugere que o coach se confundiu
    assert "embananei" not in recado.lower()


def test_separa_os_tipos_que_exigem_gente():
    assert saude.classificar("authentication_error: invalid x")[0] == "chave"
    assert saude.classificar("rate_limit_error")[0] == "limite"
    assert saude.classificar("Overloaded")[0] == "sobrecarga"
    assert "sem_credito" in saude._URGENTE and "chave" in saude._URGENTE
    assert "limite" not in saude._URGENTE   # passa sozinho, não acorda ninguém


def test_erro_que_nao_e_de_infra_devolve_None():
    """Aí o "me embananei" continua CERTO — o problema é mesmo do modelo."""
    assert saude.classificar("KeyError: 'hero'") is None
    assert saude.classificar("") is None
    assert saude.classificar(None) is None


# ------------------------------------------------------------------ alerta
def test_alerta_do_admin_diz_o_que_fazer():
    t = saude.texto_do_alerta("sem_credito", ERRO_REAL)
    assert "CRÉDITO DA API ACABOU" in t
    assert "Plans & Billing" in t
    assert "sem deploy" in t          # volta na hora, é bom saber


def test_admin_nao_e_metralhado_a_cada_chamada():
    """Alarme que repete por chamada é alarme que se desliga."""
    enviados = []
    original = saude._avisar_admin
    saude._avisar_admin = enviados.append
    try:
        for t in (0.0, 10.0, 60.0, 300.0):
            saude.registrar(ERRO_REAL, agora=t)
        assert len(enviados) == 1, "avisou mais de uma vez na janela"
        saude.registrar(ERRO_REAL, agora=5000.0)   # passou a janela
        assert len(enviados) == 2
    finally:
        saude._avisar_admin = original


# ------------------------------------------------------------------ aluno
def test_recado_ao_aluno_vale_por_pouco_tempo():
    """Culpar a infra por um erro de meia hora atrás seria trocar uma
    explicação errada por outra."""
    original = saude._avisar_admin
    saude._avisar_admin = lambda _t: None
    try:
        saude.registrar(ERRO_REAL, agora=100.0)
        assert saude.recado_recente(agora=110.0)          # dentro da janela
        assert saude.recado_recente(agora=100.0 + saude.JANELA_RECADO + 1) is None
    finally:
        saude._avisar_admin = original


def test_sem_falha_nenhuma_nao_ha_recado():
    assert saude.recado_recente() is None


def test_registrar_nunca_levanta():
    """É chamada de dentro do tratamento de erro: uma exceção aqui apagaria
    a falha original."""
    assert saude.registrar(object()) is None


def test_processing_usa_o_recado_antes_do_embananei():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing)
    for trecho in ("recado_recente() or", "me embananei"):
        assert trecho in fonte
    # o recado vem ANTES do fallback genérico nas duas ocorrências
    assert fonte.count("recado_recente() or") == 2


def test_create_avisa_a_saude_ao_falhar():
    """O erro real só é visível no `_create`; se ele não avisar, ninguém vê."""
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm._create)
    assert "saude.registrar(exc)" in fonte
