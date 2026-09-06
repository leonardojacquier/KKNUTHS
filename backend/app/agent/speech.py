"""Transcrição de voz (Whisper/OpenAI) — o usuário fala com o coach por áudio.

A Anthropic não transcreve áudio; usamos a mesma chave OpenAI dos embeddings.
Sem chave/erro, retorna None (o bot orienta a escrever).
"""
from __future__ import annotations

import io
import logging

from app.config import get_settings

log = logging.getLogger("speech")


def transcribe_audio(content: bytes, filename: str = "voice.ogg") -> str | None:
    s = get_settings()
    if not s.openai_api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=s.openai_api_key)
        buf = io.BytesIO(content)
        buf.name = filename  # o SDK usa a extensão para o content-type
        result = client.audio.transcriptions.create(
            model="whisper-1", file=buf, language="pt"
        )
        text = (result.text or "").strip()
        return text or None
    except Exception as exc:
        log.warning("transcrição falhou: %s", exc)
        return None
