"""Pedido em texto + arquivo logo depois são UMA coisa só.

21/09: o alvgomes19 (único aluno externo ativo) escreveu "analise o hand
history abaixo e dê uma nota de 1 a 10" e mandou o arquivo 20 s depois (149
mãos, PokerStars). O texto virou conversa — o coach respondeu "não recebi
nenhum histórico" — e o arquivo foi analisado sem o pedido. Nada ligava os
dois.
"""
from __future__ import annotations

import inspect

import pytest

from app.bot import pedido_recente as P


@pytest.fixture(autouse=True)
def _limpo():
    P.PEDIDOS.clear()
    yield
    P.PEDIDOS.clear()


@pytest.mark.parametrize("texto", [
    "analise o hand history abaixo e dê uma nota de 1 a 10",
    "vou te mandar o histórico do torneio de ontem, quero saber onde errei",
    "segue o arquivo das mãos, me diz as certas e as erradas",
    "Vou enviar um print da mão, olha o river",
    "analisa essas mãos que vou mandar agora",
])
def test_reconhece_pedido_que_anuncia_o_arquivo(texto):
    assert P.anuncia_arquivo(texto)


@pytest.mark.parametrize("texto", [
    "por que o call do river foi erro?",
    "obrigado",
    "e se eu tivesse dado fold no turn?",
    "qual é o range de abertura do UTG?",
])
def test_conversa_comum_nao_vira_pedido(texto):
    assert not P.anuncia_arquivo(texto)


def test_pedido_vira_legenda_do_upload_seguinte():
    P.registrar(1, "analise o hand history abaixo e dê uma nota de 1 a 10")
    assert P.legenda_do_upload(1, None) == \
        "analise o hand history abaixo e dê uma nota de 1 a 10"
    # consumido: o segundo arquivo não herda o pedido do primeiro
    assert P.legenda_do_upload(1, None) is None


def test_legenda_propria_ganha_e_o_pedido_soma():
    P.registrar(1, "quero nota de 1 a 10")
    leg = P.legenda_do_upload(1, "torneio de domingo")
    assert "torneio de domingo" in leg and "nota de 1 a 10" in leg


def test_pedido_vencido_nao_contamina(monkeypatch):
    agora = P.time.time()
    P.registrar(1, "analise o histórico abaixo")
    monkeypatch.setattr(P.time, "time", lambda: agora + P.JANELA_S + 1)
    assert P.legenda_do_upload(1, None) is None


def test_um_aluno_nao_herda_o_pedido_do_outro():
    P.registrar(1, "analise o histórico abaixo")
    assert P.legenda_do_upload(2, None) is None


def test_os_handlers_ligam_texto_e_arquivo():
    """O texto que anuncia registra (e não vai pro LLM dizer 'não recebi');
    arquivo, foto e histórico colado usam o pedido como legenda."""
    from app.bot import handlers

    rota = inspect.getsource(handlers._route_text)
    assert "anuncia_arquivo" in rota and "registrar" in rota
    assert "legenda_do_upload" in rota          # histórico colado
    assert "legenda_do_upload" in inspect.getsource(handlers.on_document)
    assert "legenda_do_upload" in inspect.getsource(handlers.on_photo)


def test_resposta_ao_anuncio_nao_diz_que_nao_recebeu():
    assert "não recebi" not in P.RESPOSTA_AO_ANUNCIO.lower()
    assert "manda" in P.RESPOSTA_AO_ANUNCIO.lower()


def test_o_pedido_chega_ao_coach_como_pedido():
    """Não basta a legenda existir: a instrução tem que dizer ao coach que
    um relato pode ser um PEDIDO de formato (nota, certas × erradas)."""
    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "PEDIDO" in fonte and "nota de 1 a 10" in fonte
    # e o pedido não vira 'narração da mão' para o extrator de texto
    assert "anuncia_arquivo(caption)" in fonte
