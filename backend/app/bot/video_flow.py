"""Passo ZERO do vídeo: receber, extrair quadros, deduplicar — e PROVAR.

O dono mandou um vídeo e ele morreu no `on_unsupported`, em silêncio. Antes
de gastar um centavo de visão, este módulo faz só a parte de custo zero:
ffmpeg tira 1 quadro por segundo, um comparador determinístico joga fora os
quadros em que a tela não mudou, e o bot DEVOLVE as telas distintas para o
dono conferir — "é exatamente isto que a análise veria". A visão só entra
depois desse aceite, calibrada nos exemplos dele (o mesmo caminho da foto
do lobby: 14/14 conferido antes de ligar).

Números medidos aqui (quadros totais, telas distintas) são também o custo
futuro: cada tela distinta será ~1.4k tokens de visão por passe. Sem este
passo, qualquer orçamento seria chute.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# diff médio de cinza (0-255) para dizer que a tela MUDOU. Abaixo disso é
# ruído de compressão/relógio; acima, carta virada, aposta nova, tela nova.
LIMIAR_DE_MUDANCA = 6.0
# lado da assinatura: 64px preserva layout e mata ruído fino
LADO_DA_ASSINATURA = 64
# teto do que volta ao Telegram (álbuns de 10; 24 = 3 álbuns no máximo)
MAXIMO_DE_FRAMES = 24
# a API de bots só baixa até 20 MB — acima disso nem tentamos
MAXIMO_MB = 20


class FfmpegAusente(RuntimeError):
    """ffmpeg não está no PATH — o oneshot de deploy ainda não rodou."""


def comando_ffmpeg(video: str, pasta: str, fps: int = 1) -> list[str]:
    """O comando, puro e testável: 1 quadro/segundo, qualidade de leitura."""
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video,
            "-vf", f"fps={fps}", "-qscale:v", "3",
            str(Path(pasta) / "quadro-%04d.jpg")]


def extrair_frames(video: str, pasta: str, fps: int = 1) -> list[str]:
    """Extrai os quadros. Levanta FfmpegAusente com mensagem acionável."""
    if shutil.which("ffmpeg") is None:
        raise FfmpegAusente("ffmpeg não instalado neste servidor")
    Path(pasta).mkdir(parents=True, exist_ok=True)
    subprocess.run(comando_ffmpeg(video, pasta, fps), check=True, timeout=120)
    return sorted(str(p) for p in Path(pasta).glob("quadro-*.jpg"))


def _assinatura(caminho: str):
    from PIL import Image

    with Image.open(caminho) as im:
        pequena = im.convert("L").resize(
            (LADO_DA_ASSINATURA, LADO_DA_ASSINATURA))
        return list(pequena.tobytes())


def diferenca(a: list, b: list) -> float:
    """Diff médio absoluto entre duas assinaturas (0-255)."""
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def frames_distintos(caminhos: list[str]) -> list[str]:
    """Os quadros em que a tela MUDOU — comparando com o último MANTIDO.

    Contra o último mantido, não contra o anterior: um replay que muda
    devagar (barra de tempo, stack pingando) nunca cruzaria o limiar
    quadro a quadro, e a mão inteira viraria um quadro só. A deriva
    acumula até cruzar o limiar e a tela nova entra.
    """
    mantidos: list[str] = []
    ultima = None
    for c in caminhos:
        assin = _assinatura(c)
        if ultima is None or diferenca(assin, ultima) >= LIMIAR_DE_MUDANCA:
            mantidos.append(c)
            ultima = assin
    return mantidos


def processar_video(video: str, pasta: str) -> tuple[list[str], int]:
    """(telas distintas — no teto —, total de quadros extraídos)."""
    todos = extrair_frames(video, pasta)
    distintos = frames_distintos(todos)
    return distintos[:MAXIMO_DE_FRAMES], len(todos)


def comando_ffmpeg_audio(video: str, destino: str) -> list[str]:
    """Só a trilha de áudio, mono 64kbps — o que o Whisper precisa e nada
    mais (react de 10min vira ~5MB, longe do teto de 25MB da API)."""
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video,
            "-vn", "-ac", "1", "-b:a", "64k", destino]


def audio_do_video(video: str, pasta: str) -> bytes | None:
    """A trilha de áudio em mp3, ou None (sem áudio / sem ffmpeg).

    Num REACT a mão está na NARRAÇÃO, não nos quadros — o dono mandou um
    react do YouTube e as telas sozinhas seriam a metade errada da prova.
    Falha aqui não derruba nada: os quadros seguem valendo."""
    if shutil.which("ffmpeg") is None:
        return None
    destino = str(Path(pasta) / "narracao.mp3")
    try:
        subprocess.run(comando_ffmpeg_audio(video, destino), check=True,
                       timeout=120)
        dados = Path(destino).read_bytes()
        return dados or None
    except Exception:
        return None


def resumo(total: int, distintos: int, truncado: bool,
           transcricao_ok: bool | None = None,
           segundos: int = 0) -> str:
    """O texto da prova — com o custo DECLARADO, medido e não prometido."""
    linhas = [f"🎞 {total} quadros extraídos → {distintos} telas distintas.",
              "É exatamente isto que a análise por visão receberia — "
              "confere se a mão está toda aí."]
    if truncado:
        linhas.insert(1, f"(mostrando as {MAXIMO_DE_FRAMES} primeiras)")
    if transcricao_ok:
        custo = (segundos / 60) * 0.006
        linhas.append(f"🎙 Narração transcrita ({segundos // 60}m"
                      f"{segundos % 60:02d}s — custo real ~US$ {custo:.3f}, "
                      f"Whisper). Nenhuma outra IA rodou.")
    elif transcricao_ok is False:
        linhas.append("🎙 Sem transcrição: o vídeo não tem trilha de áudio "
                      "legível ou a chave de voz não respondeu.")
    else:
        linhas.append("Custo desta etapa: zero (nenhuma IA rodou).")
    return "\n".join(linhas)
