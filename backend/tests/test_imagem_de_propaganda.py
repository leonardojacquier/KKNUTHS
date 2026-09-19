"""A imagem de propaganda do PPPoker chega SOZINHA, antes do link.

Em 23/08 o desvio cobriu o caso "foto + link na MESMA mensagem". O fluxo
real do Compartilhar manda DUAS mensagens: primeiro a arte da mesa vazia,
sem legenda; 30-90 segundos depois, o link. Medido no banco em 19/09: 8 das
10 fotos desde 20/08 tiveram um link de replay do mesmo aluno logo depois.

Cada uma dessas fotos ia pra visão, que ALUCINAVA uma mão (conf 0,5), o
coach escrevia 600 chars de "sem imagem legível", o juiz dava 3,5, e o
aluno gastava uma unidade de cota + ~US$0,15 pra ouvir isso. Em 14/09 foram
QUATRO em 90 minutos — o dia inteiro do juiz caiu pra 5,8 por causa delas.

Não dá pra segurar a foto esperando o link (30-90 s de atraso em todo print
legítimo). Não dá pra fingerprint de antemão (o container não alcança o
bucket). O que dá é aprender: a imagem é SEMPRE a mesma arte, então basta
reconhecê-la pelo hash perceptual depois da primeira vez — e a primeira vez
se anuncia sozinha, pelo link que chega em seguida.
"""
from __future__ import annotations

import inspect
import io
import time

import pytest
from PIL import Image

from app.bot import imagem_de_propaganda as P


def _png(desenho, tamanho=(320, 200), qualidade=None) -> bytes:
    img = Image.new("RGB", tamanho)
    px = img.load()
    for x in range(tamanho[0]):
        for y in range(tamanho[1]):
            px[x, y] = desenho(x, y)
    buf = io.BytesIO()
    if qualidade:
        img.save(buf, "JPEG", quality=qualidade)
    else:
        img.save(buf, "PNG")
    return buf.getvalue()


_MESA = lambda x, y: (20, 90 + (x // 40) * 15, 40)           # "feltro" com faixas
_PRINT = lambda x, y: ((x * 7) % 256, (y * 13) % 256, (x ^ y) % 256)  # ruído


# ---- 1) o hash ---------------------------------------------------------------

def test_a_mesma_imagem_da_o_mesmo_hash():
    assert P.hash_da_imagem(_png(_MESA)) == P.hash_da_imagem(_png(_MESA))


def test_o_hash_sobrevive_a_recompressao_do_telegram():
    """O Telegram recomprime toda foto. Se o hash mudasse, a memória nunca
    reconheceria a segunda chegada da mesma arte."""
    original = P.hash_da_imagem(_png(_MESA))
    recomprimida = P.hash_da_imagem(_png(_MESA, qualidade=55))
    assert P.distancia(original, recomprimida) <= P.TOLERANCIA


def test_imagens_diferentes_ficam_longe():
    assert P.distancia(P.hash_da_imagem(_png(_MESA)),
                       P.hash_da_imagem(_png(_PRINT))) > P.TOLERANCIA * 2


def test_bytes_que_nao_sao_imagem_dao_none_sem_explodir():
    assert P.hash_da_imagem(b"isto nao e uma imagem") is None
    assert P.hash_da_imagem(b"") is None


# ---- 2) reconhecer -----------------------------------------------------------

@pytest.fixture
def memoria(monkeypatch):
    """Repositório falso: guarda eventos e devolve os de propaganda."""
    eventos: list[tuple] = []

    class _Q:
        def __init__(self, rows): self._rows = rows
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def order(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: data = [{"detail": {"hash": h}} for h in self._rows]
            return R()

    class _Repo:
        enabled = True
        def log_event(self, tg, user, evento, detail=None):
            eventos.append((tg, evento, detail or {}))
        class client:
            @staticmethod
            def table(nome):
                return _Q([d["hash"] for _, e, d in eventos
                           if e == P.EVENTO_APRENDIDA])

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    P._esquecer_tudo()
    return eventos


def test_imagem_nunca_vista_nao_e_propaganda(memoria):
    assert P.e_propaganda(P.hash_da_imagem(_png(_MESA))) is False


def test_depois_de_aprendida_a_mesma_arte_e_reconhecida(memoria):
    h = P.hash_da_imagem(_png(_MESA))
    P.registrar_foto(77, h)
    P.aprender_da_foto_recente(77)
    assert P.e_propaganda(P.hash_da_imagem(_png(_MESA, qualidade=55))) is True, \
        "aprendeu e mesmo assim não reconheceu a recompressão"


def test_aprender_persiste_no_banco_porque_o_processo_reinicia_a_cada_deploy(memoria):
    h = P.hash_da_imagem(_png(_MESA))
    P.registrar_foto(77, h)
    P.aprender_da_foto_recente(77)
    assert any(e == P.EVENTO_APRENDIDA and d.get("hash") == h
               for _, e, d in memoria), "aprendeu só na memória do processo"


def test_um_print_de_verdade_nao_vira_propaganda_por_engano(memoria):
    """Aprender só marca o hash daquela foto: um print real é único por mão
    e nunca se repete, então mesmo o pior caso (print + link em 3 min) não
    bloqueia nada no futuro. Mas outra imagem NÃO pode ser reconhecida."""
    P.registrar_foto(77, P.hash_da_imagem(_png(_MESA)))
    P.aprender_da_foto_recente(77)
    assert P.e_propaganda(P.hash_da_imagem(_png(_PRINT))) is False


def test_link_sem_foto_recente_nao_aprende_nada(memoria):
    P.aprender_da_foto_recente(77)
    assert not memoria


def test_foto_velha_demais_nao_e_associada_ao_link(memoria, monkeypatch):
    """A janela é a medida do fluxo real (30-90 s), com folga. Uma foto de
    ontem seguida de um link de hoje são duas coisas."""
    h = P.hash_da_imagem(_png(_MESA))
    P.registrar_foto(77, h)
    agora = time.time()
    monkeypatch.setattr(P.time, "time", lambda: agora + P.JANELA_S + 60)
    P.aprender_da_foto_recente(77)
    assert not memoria


def test_o_conhecimento_de_um_aluno_vale_para_todos(memoria):
    """A arte é a mesma pra todo mundo: o que o Leo ensinou o Ricardo usa."""
    P.registrar_foto(77, P.hash_da_imagem(_png(_MESA)))
    P.aprender_da_foto_recente(77)
    P._esquecer_tudo()          # outro processo, memória zerada
    assert P.e_propaganda(P.hash_da_imagem(_png(_MESA))) is True


# ---- 3) o que o aluno lê --------------------------------------------------

def test_a_resposta_e_curta_e_aponta_pro_link():
    """O juiz de 18/09: 'deveria ter pedido a imagem correta em 1-2 linhas'."""
    t = P.TEXTO_PROPAGANDA
    assert t.count("\n") <= 1
    assert "link" in t.lower()
    assert len(t) < 220


# ---- 4) ligado nos dois lugares --------------------------------------------

def test_on_photo_reconhece_ANTES_de_gastar_visao_e_cota():
    """Cobra a CHAMADA `propaganda.e_propaganda(`, não a palavra: o mutante
    que moveu o bloco pra depois da visão sobreviveu porque o comentário
    'Ver imagem_de_propaganda' contém o substring e ficou no lugar."""
    import re

    from app.bot import handlers

    fonte = inspect.getsource(handlers.on_photo)
    chamada = re.search(r"propaganda\.e_propaganda\(", fonte)
    registro = re.search(r"propaganda\.registrar_foto\(", fonte)
    assert chamada, "on_photo não consulta a memória de propaganda"
    assert registro, "sem registrar a foto, o link não ensina nada"
    assert chamada.start() < fonte.index('"print_recebido"'), \
        "reconhece só DEPOIS de já ter contado o print"
    assert chamada.start() < fonte.index("process_upload,"), \
        "reconhece só DEPOIS de já ter gasto visão e cota"


def test_o_link_de_replay_ensina():
    import re

    from app.bot import handlers

    fonte = inspect.getsource(handlers._tratar_replay)
    assert re.search(r"propaganda\.aprender_da_foto_recente\(", fonte)
