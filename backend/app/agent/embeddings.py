"""Embeddings para a base de conhecimento (RAG).

A Anthropic não oferece endpoint de embeddings, então usamos um provedor dedicado:
Voyage (recomendado pela Anthropic) ou OpenAI. Sem chave configurada, `embed_text`
retorna None — a análise é salva sem vetor e a busca semântica fica inativa até
configurar (degradação graciosa, sem quebrar o fluxo).

IMPORTANTE: a dimensão do modelo deve casar com `vector(N)` no schema (default 1536).
"""
from __future__ import annotations

import logging

from app.config import get_settings

log = logging.getLogger("embeddings")


def embed_text(text: str) -> list[float] | None:
    """Gera o embedding de um texto. None se nenhum provedor estiver configurado."""
    if not text:
        return None
    text = text[:24000]  # limite do provedor (~8191 tokens); estourar = análise sem vetor
    s = get_settings()
    try:
        if s.voyage_api_key:
            return _voyage(text, s.voyage_api_key, s.embedding_model)
        if s.openai_api_key:
            return _openai(text, s.openai_api_key, s.embedding_model)
    except Exception as exc:  # falha de rede/SDK não derruba a análise
        log.warning("embedding falhou: %s", exc)
    return None


def _voyage(text: str, api_key: str, model: str) -> list[float]:
    import voyageai  # lazy import

    client = voyageai.Client(api_key=api_key)
    model = model if model.startswith("voyage") else "voyage-large-2"
    result = client.embed([text], model=model, input_type="document")
    return result.embeddings[0]


def _openai(text: str, api_key: str, model: str) -> list[float]:
    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=api_key)
    model = model if not model.startswith("voyage") else "text-embedding-3-small"
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


def embed_query(query: str) -> list[float] | None:
    """Embedding de uma consulta (mesma representação; input_type difere no Voyage)."""
    if not query:
        return None
    s = get_settings()
    try:
        if s.voyage_api_key:
            import voyageai

            client = voyageai.Client(api_key=s.voyage_api_key)
            model = s.embedding_model if s.embedding_model.startswith("voyage") else "voyage-large-2"
            return client.embed([query], model=model, input_type="query").embeddings[0]
        if s.openai_api_key:
            return _openai(query, s.openai_api_key, s.embedding_model)
    except Exception as exc:
        log.warning("embedding de query falhou: %s", exc)
    return None
