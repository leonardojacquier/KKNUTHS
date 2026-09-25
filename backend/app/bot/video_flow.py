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


# ------------------------------------------------------------- YouTube -----
# react no YouTube não precisa caber nos 20MB do Telegram: o LINK basta —
# o servidor baixa o vídeo inteiro sozinho (yt-dlp) e corta o que precisar.
# Teto de duração: prova de meia hora já são ~US$0.18 de Whisper; acima
# disso o certo é o dono apontar o trecho, não o servidor engolir tudo.
DURACAO_MAXIMA_S = 30 * 60

_RE_YOUTUBE = None


def link_do_youtube(texto: str) -> str | None:
    """A URL do YouTube dentro do texto, ou None. Puro e testável."""
    import re

    global _RE_YOUTUBE
    if _RE_YOUTUBE is None:
        _RE_YOUTUBE = re.compile(
            r"https?://(?:www\.|m\.)?"
            r"(?:youtube\.com/(?:watch\?[^ ]*v=|shorts/|live/)"
            r"|youtu\.be/)[\w-]{6,}[^\s]*", re.IGNORECASE)
    m = _RE_YOUTUBE.search(texto or "")
    return m.group(0) if m else None


def baixar_youtube(url: str, pasta: str) -> tuple[str, int] | str:
    """(caminho, duração_s) no sucesso; STRING com o que explicar ao aluno
    no insucesso — a mesma regra do dossiê: erro explicado, não engolido."""
    try:
        import yt_dlp
    except ImportError:
        return ("O leitor de YouTube ainda não está instalado no servidor "
                "— o Leo já foi avisado.")
    opts = {"quiet": True, "no_warnings": True,
            "format": "mp4[height<=480]/best[height<=480]/best",
            "outtmpl": str(Path(pasta) / "youtube.%(ext)s"),
            "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            dur = int(info.get("duration") or 0)
            if dur > DURACAO_MAXIMA_S:
                return (f"Esse vídeo tem {dur // 60} minutos — meu teto é "
                        f"{DURACAO_MAXIMA_S // 60}. Me manda o link com o "
                        f"timestamp do trecho da mão (botão Compartilhar → "
                        f"'a partir de') ou um recorte.")
            ydl.download([url])
        arquivos = sorted(Path(pasta).glob("youtube.*"))
        if not arquivos:
            return "O download veio vazio — tenta de novo em uns minutos."
        return str(arquivos[0]), dur
    except Exception:
        return ("Não consegui baixar esse vídeo (o YouTube às vezes barra "
                "servidor). Alternativa que sempre funciona: grava a tela "
                "do trecho da mão e me manda o vídeo direto.")


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
