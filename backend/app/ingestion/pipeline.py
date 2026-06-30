"""Pipeline de ingestão multi-formato.

Converge qualquer input para `list[CanonicalHand]`:
  - txt  -> parser determinístico (preciso, barato)
  - csv  -> mapeamento de tracker (a implementar por tracker)
  - pdf  -> extração de texto; se for PDF-imagem, cai no fluxo de visão
  - image-> visão do LLM (a conectar) com confidence < 1.0

Aqui implementamos o caminho de texto (o de maior valor imediato) e deixamos os
demais como pontos de extensão explícitos.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.canonical import CanonicalHand
from app.parsers import detect_site, parse_text


@dataclass
class IngestResult:
    hands: list[CanonicalHand]
    site: str | None
    source_format: str
    confidence: float
    needs_review: bool = False
    note: str = ""


def ingest(content: bytes | str, source_format: str = "txt", filename: str = "") -> IngestResult:
    fmt = (source_format or "").lower()

    if fmt in ("txt", "text") or (isinstance(content, str)):
        text = content.decode("utf-8", "ignore") if isinstance(content, bytes) else content
        site = detect_site(text)
        if site:
            hands = parse_text(text)
            return IngestResult(hands, site, "txt", confidence=1.0)
        # texto não reconhecido -> LLM de inferência (a conectar)
        return IngestResult([], None, "txt", confidence=0.0, needs_review=True,
                            note="formato de texto não reconhecido; encaminhar ao LLM")

    if fmt == "pdf":
        text = _pdf_to_text(content)
        if text and detect_site(text):
            return IngestResult(parse_text(text), detect_site(text), "pdf", confidence=0.95)
        # PDF-imagem (sem texto): cai no fluxo de visão
        return _vision_ingest(content, "pdf")

    if fmt in ("image", "png", "jpg", "jpeg"):
        media = "image/jpeg" if fmt in ("jpg", "jpeg") else "image/png"
        return _vision_ingest(content, "image", media)

    if fmt == "csv":
        return IngestResult([], None, "csv", confidence=0.0, needs_review=True,
                            note="mapeamento de CSV de tracker ainda não conectado")

    return IngestResult([], None, fmt, confidence=0.0, needs_review=True,
                        note=f"formato '{fmt}' não suportado")


def _vision_ingest(content: bytes | str, fmt: str, media: str = "image/png") -> IngestResult:
    """Extrai um snapshot de mão via visão do Claude (confidence < 1.0)."""
    from app.agent.llm import extract_from_image

    if isinstance(content, str):
        content = content.encode()
    hand = extract_from_image(content, media)
    if hand is None:
        return IngestResult([], None, fmt, confidence=0.0, needs_review=True,
                            note="visão indisponível (sem ANTHROPIC_API_KEY) ou extração falhou")
    return IngestResult([hand], hand.site, fmt, confidence=hand.confidence,
                        needs_review=hand.confidence < 0.9,
                        note="snapshot extraído por visão; confira os valores")


def _pdf_to_text(content: bytes | str) -> str:
    if isinstance(content, str):
        return content
    try:
        import io

        import pdfplumber  # lazy import

        out = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                out.append(page.extract_text() or "")
        return "\n".join(out)
    except Exception:
        return ""
