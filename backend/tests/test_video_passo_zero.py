"""O passo zero do vídeo: extrair, deduplicar, provar — sem gastar visão.

O vídeo do dono morreu no on_unsupported em silêncio (11/08). Antes de
qualquer custo de modelo, o bot passa a devolver as TELAS DISTINTAS do
vídeo para o dono conferir. Estes testes prendem o comparador (o limiar, o
"compara com o último MANTIDO", o teto de frames) e o roteamento do
handler — as fronteiras que decidem o custo futuro.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.bot import video_flow as V


def _quadro(pasta, nome, cinza, mancha=None):
    """Um quadro sintético uniforme; `mancha` pinta um retângulo (a "carta
    virada") para simular mudança localizada."""
    im = Image.new("L", (360, 640), cinza)
    if mancha is not None:
        im.paste(mancha, (40, 40, 200, 240))
    p = str(Path(pasta) / nome)
    im.convert("RGB").save(p)
    return p


# ---- o comparador -----------------------------------------------------------

def test_tela_igual_cai_tela_mudada_fica(tmp_path):
    a = _quadro(tmp_path, "a.jpg", 100)
    b = _quadro(tmp_path, "b.jpg", 100)          # nada mudou
    c = _quadro(tmp_path, "c.jpg", 100, mancha=220)  # "carta virada"
    assert V.frames_distintos([a, b, c]) == [a, c]


def test_o_limiar_e_a_fronteira(tmp_path):
    """Diff uniforme de 5 fica abaixo de LIMIAR_DE_MUDANCA=6 (cai); de 12,
    acima (fica). Prende o limiar exato — mudar a constante quebra aqui."""
    a = _quadro(tmp_path, "a.jpg", 100)
    quase = _quadro(tmp_path, "b.jpg", 105)
    passou = _quadro(tmp_path, "c.jpg", 112)
    assert V.frames_distintos([a, quase]) == [a]
    assert V.frames_distintos([a, passou]) == [a, passou]


def test_deriva_lenta_compara_com_o_ultimo_MANTIDO(tmp_path):
    """Replay que muda devagar: quadro a quadro o diff é 4 (< limiar), mas
    a deriva acumula. Contra o anterior, sobraria 1 quadro e a mão inteira
    sumiria; contra o último mantido, a tela nova entra quando a soma
    cruza o limiar."""
    quadros = [_quadro(tmp_path, f"q{i}.jpg", 100 + 4 * i) for i in range(5)]
    mantidos = V.frames_distintos(quadros)
    assert len(mantidos) >= 2, "a deriva acumulada tem que cruzar o limiar"
    assert mantidos[0] == quadros[0]


def test_teto_de_frames(tmp_path, monkeypatch):
    """30 telas distintas -> devolve MAXIMO_DE_FRAMES (24). O teto protege
    o Telegram (álbuns) e o custo futuro de visão."""
    quadros = [_quadro(tmp_path, f"q{i:02d}.jpg", (i * 37) % 200)
               for i in range(30)]
    monkeypatch.setattr(V, "extrair_frames", lambda *a, **k: quadros)
    distintos, total = V.processar_video("x.mp4", str(tmp_path))
    assert total == 30
    # o literal, não a constante: comparar com V.MAXIMO_DE_FRAMES passaria
    # com QUALQUER teto (tautologia) — uma mutação provou
    assert len(distintos) == 24


# ---- ffmpeg -----------------------------------------------------------------

def test_comando_ffmpeg_e_um_quadro_por_segundo():
    cmd = V.comando_ffmpeg("v.mp4", "/tmp/x", fps=1)
    assert cmd[0] == "ffmpeg"
    assert "fps=1" in " ".join(cmd)
    assert cmd[-1].endswith("quadro-%04d.jpg")


def test_sem_ffmpeg_levanta_erro_acionavel(monkeypatch, tmp_path):
    monkeypatch.setattr(V.shutil, "which", lambda _: None)
    with pytest.raises(V.FfmpegAusente):
        V.extrair_frames("v.mp4", str(tmp_path))


# ---- o texto da prova -------------------------------------------------------

def test_resumo_declara_custo_zero_e_truncamento():
    t = V.resumo(42, 17, truncado=False)
    assert "42 quadros" in t and "17 telas" in t
    assert "zero" in t
    assert "primeiras" not in t
    assert "primeiras" in V.resumo(90, 24, truncado=True)


def test_resumo_com_transcricao_declara_o_custo_REAL():
    """React de 10min: o Whisper custa 10 × $0.006 = $0.060 — o número sai
    impresso, medido, não prometido."""
    t = V.resumo(600, 24, truncado=True, transcricao_ok=True, segundos=600)
    assert "10m00s" in t
    assert "US$ 0.060" in t
    assert "zero" not in t.lower().split("whisper")[0].split("custo real")[0]
    sem = V.resumo(600, 24, truncado=True, transcricao_ok=False)
    assert "Sem transcrição" in sem


def test_comando_de_audio_e_mono_sem_video():
    cmd = V.comando_ffmpeg_audio("v.mp4", "/tmp/a.mp3")
    junto = " ".join(cmd)
    assert "-vn" in junto and "-ac 1" in junto
    assert cmd[-1].endswith(".mp3")


def test_audio_do_video_degrada_para_None(monkeypatch, tmp_path):
    """Sem ffmpeg (ou vídeo sem trilha) o áudio vira None e os QUADROS
    continuam valendo — a prova não pode morrer pela metade que faltou."""
    monkeypatch.setattr(V.shutil, "which", lambda _: None)
    assert V.audio_do_video("v.mp4", str(tmp_path)) is None


# ---- roteamento no bot ------------------------------------------------------

def test_video_nao_cai_mais_no_unsupported():
    """O handler de vídeo existe e é registrado ANTES do on_document e do
    on_unsupported — senão mp4 'como arquivo' vira hand history e vídeo
    normal volta a morrer em silêncio."""
    import inspect

    from app.bot import handlers as H

    assert hasattr(H, "on_video")
    src = inspect.getsource(H)
    registro = src[src.find("def build_application"):]
    i_video = registro.find("on_video")
    assert i_video != -1
    assert i_video < registro.find("on_document")
    assert "~filters.VIDEO" in registro, \
        "on_unsupported precisa excluir vídeo explicitamente"
