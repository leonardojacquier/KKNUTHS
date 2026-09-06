"""Compartilhou o link do clube? A mão está no LINK — a imagem é propaganda.

O `test_replay_na_legenda.py` já prendeu o caso simples (foto + legenda com
UM link). Este prende os dois furos que sobraram e que o dono viu na prática:

  1. A legenda do PPPoker traz DOIS links — o de baixar o app primeiro, o do
     replay depois. O detector olhava só a PRIMEIRA url do texto:
       · "https://pppoker.onelink.me/..." é host de pppoker sem shareKey ->
         respondia "não consegui ler o link" com o replay inteiro ali do lado;
       · "https://onelink.me/..." não é host de replay -> devolvia None e a
         foto ia pra VISÃO. É exatamente o sintoma relatado: "ele acaba
         tentando interpretar essa imagem".

  2. A mesma imagem promocional chega como DOCUMENTO quando o app (ou o
     Telegram Desktop) manda sem compressão. O `on_document` não olhava
     legenda nenhuma: baixava e mandava pra visão, gastando cota.

Regra: varrer TODAS as urls e ficar com a que ABRE. Só depois desistir.
"""
from __future__ import annotations

import inspect

import pytest

from app.bot import handlers
from app.bot.processing import replay_link_info

_CHAVE = "abc123XYZdef456uvw"
_REPLAY = f"https://replay.pppoker.net/index.html?shareKey={_CHAVE}&lang=pt"


# ---- 1) a legenda com dois links -------------------------------------------

@pytest.mark.parametrize("antes", [
    # host de pppoker, mas é o link de DOWNLOAD: não tem shareKey
    "https://pppoker.onelink.me/dl/abc",
    # host que não é de replay nenhum: o detector parava aqui e devolvia None
    "https://onelink.me/dl/abc",
    "https://apps.apple.com/br/app/pppoker/id1234567890",
])
def test_o_link_que_abre_ganha_do_link_de_download(antes):
    legenda = (f"Venha ver esta mão incrível que joguei no PPPoker! "
               f"Baixe o app e jogue você também: {antes}  Replay: {_REPLAY}")
    rl = replay_link_info(legenda, legenda=True)
    assert rl is not None, "desistiu na primeira url e jogou a foto pra visão"
    assert rl["site"] == "pppoker"
    assert rl["share_key"] == _CHAVE, "achou um link de replay que não abre"


def test_link_de_clube_sem_chave_continua_reconhecido():
    """Quando NÃO há link que abre, o reconhecido-porém-ilegível ainda vale:
    é ele que produz a resposta 'esse clube eu não puxo sozinho'."""
    rl = replay_link_info("Olha: https://pppoker.onelink.me/dl/abc",
                          legenda=True)
    assert rl is not None and rl["share_key"] is None


def test_a_ordem_nao_inverte_quando_o_bom_vem_primeiro():
    legenda = f"Mão boa: {_REPLAY} — baixe em https://onelink.me/dl/abc"
    rl = replay_link_info(legenda, legenda=True)
    assert rl and rl["share_key"] == _CHAVE


def test_texto_digitado_longo_com_dois_links_continua_ignorado():
    """A trava anti-falso-positivo do texto DIGITADO não pode ter sido
    afrouxada pela varredura: link citado no meio de uma pergunta não é
    pedido de análise."""
    pergunta = ("Ontem vi https://onelink.me/dl/abc e também "
                f"{_REPLAY} mas minha dúvida é outra: com AKo em UTG num "
                "torneio de 100 jogadores, com 40bb, abro 2.2 ou 2.5? "
                "E contra 3-bet, qual o plano?")
    assert replay_link_info(pergunta) is None


def test_texto_sem_link_de_clube_nenhum_continua_none():
    assert replay_link_info("https://google.com/foo bar", legenda=True) is None


# ---- 2) a imagem promocional que chega como arquivo ------------------------

def test_on_document_olha_a_legenda_antes_de_baixar():
    fonte = inspect.getsource(handlers.on_document)
    assert "replay_link_info" in fonte, (
        "documento com link na legenda ia direto pra visão")
    assert fonte.index("replay_link_info") < fonte.index("process_upload"), (
        "o link tem que ser tratado ANTES de gastar visão/cota com o arquivo")
    assert "_tratar_replay" in fonte, (
        "o tratamento tem que ser o mesmo dos outros dois caminhos")


def test_o_desvio_do_documento_vale_so_para_imagem():
    """Hand history de verdade é DADO, não propaganda: um .txt com o link
    citado na legenda continua sendo analisado como arquivo."""
    assert handlers._documento_e_imagem("print.jpg", "image/jpeg") is True
    assert handlers._documento_e_imagem("mesa.PNG", None) is True
    assert handlers._documento_e_imagem("sessao.txt", "text/plain") is False
    assert handlers._documento_e_imagem("torneio.hh", None) is False
    assert handlers._documento_e_imagem(None, None) is False
