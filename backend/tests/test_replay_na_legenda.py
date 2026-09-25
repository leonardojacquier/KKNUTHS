"""Compartilhar do app do clube = imagem promocional + link na LEGENDA.

Caso real — o dono compartilhou o replay direto do PPPoker 3 vezes (17/07,
01/08 2x, 02/08). O Telegram entrega isso como FOTO com caption. O on_photo
nem olhava a legenda: mandava a imagem (mesa vazia, propaganda do clube)
pra visão, gastava uma análise da cota e respondia "a imagem não veio
legível" — com o replay inteiro a um parser de distância.
"""
import inspect

from app.bot import handlers
from app.bot.processing import replay_link_info

_LEGENDA_REAL = ("Venha ver esta mão incrível que joguei no PPPoker! "
                 "Baixe o app e jogue você também: "
                 "https://replay.pppoker.net/index.html?shareKey=abc123XYZdef456uvw"
                 "&lang=pt")


def test_legenda_promocional_do_app_e_reconhecida():
    """O texto em volta do link é do app, não do aluno — a regra da
    'mensagem é só o link' não pode valer aqui."""
    assert replay_link_info(_LEGENDA_REAL) is None, \
        "sem o modo legenda, o texto promocional mata a detecção"
    rl = replay_link_info(_LEGENDA_REAL, legenda=True)
    assert rl is not None
    assert rl["site"] == "pppoker"
    assert rl["share_key"]


def test_texto_longo_com_link_no_meio_continua_ignorado():
    """A regra anti-falso-positivo do texto digitado fica de pé: link citado
    no meio de uma pergunta longa não é pedido de análise."""
    pergunta = ("Ontem eu vi um replay replay.pppoker.net/index.html?share"
                "Key=abc mas a minha dúvida é outra: com AKo em UTG num "
                "torneio de 100 jogadores, com 40bb, você prefere abrir 2.2 "
                "ou 2.5? E contra 3-bet, qual o plano?")
    assert replay_link_info(pergunta) is None


def test_on_photo_olha_a_legenda_antes_da_visao():
    fonte = inspect.getsource(handlers.on_photo)
    assert "replay_link_info" in fonte
    assert "legenda=True" in fonte
    assert fonte.index("replay_link_info") < fonte.index("print_recebido"), \
        "o link tem que ser tratado ANTES de gastar visão/cota com a foto"


def test_caminho_do_replay_e_um_so():
    """Texto e legenda passam pela MESMA função — divergência entre os dois
    caminhos foi a causa deste defeito."""
    assert "_tratar_replay" in inspect.getsource(handlers.on_photo)
    assert "_tratar_replay" in inspect.getsource(handlers._route_text)
    fonte_route = inspect.getsource(handlers._route_text)
    assert "process_upload, rl[" not in fonte_route, \
        "o corpo do tratamento não pode viver duplicado no _route_text"


def test_foto_sem_legenda_segue_pra_visao():
    assert replay_link_info("", legenda=True) is None
    assert replay_link_info(None, legenda=True) is None
