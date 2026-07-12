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

    # PHH (padrão aberto TOML, .phh/.phhs — datasets do WSOP etc.): pela
    # extensão OU pelo cheiro do conteúdo ('variant = ...')
    if fmt in ("phh", "phhs") or (
        fmt in ("txt", "text") and isinstance(content, (str, bytes))
    ):
        text_probe = (content.decode("utf-8", "ignore")
                      if isinstance(content, bytes) else content)
        from app.parsers.phh import looks_like_phh, parse_phh

        if fmt in ("phh", "phhs") or looks_like_phh(text_probe):
            hands, note = parse_phh(text_probe)
            if hands:
                return IngestResult(hands, hands[0].site, "phh",
                                    confidence=0.95, note=note)
            return IngestResult([], None, "phh", confidence=0.0,
                                needs_review=True,
                                note=note or "PHH sem mão de hold'em")

    if fmt in ("txt", "text", "csv") or (isinstance(content, str) and fmt != "pdf"):
        text = content.decode("utf-8", "ignore") if isinstance(content, bytes) else content
        site = detect_site(text)
        if site:
            hands = parse_text(text)
            return IngestResult(hands, site, "txt", confidence=1.0)
        # CSV de tracker (por extensão ou por cheiro do conteúdo)
        from app.parsers.csv_tracker import looks_like_tracker_csv, parse_tracker_csv

        if fmt == "csv" or looks_like_tracker_csv(text):
            hands = parse_tracker_csv(text)
            if hands:
                return IngestResult(
                    hands, hands[0].site, "csv", confidence=0.9, needs_review=False,
                    note="mãos-resumo de tracker (sem ação street a street)",
                )
            return IngestResult([], None, "csv", confidence=0.0, needs_review=True,
                                note="CSV sem colunas reconhecíveis (hand id/cartas)")
        # formato desconhecido: fallback por IA — mas só se o texto PARECE poker
        # (evita alucinar mão a partir de texto qualquer e economiza tokens)
        from app.agent.llm import extract_from_hand_text

        hand = extract_from_hand_text(text) if _looks_like_poker_text(text) else None
        if hand is not None:
            return IngestResult(
                [hand], hand.site if hand.site != "unknown" else None, "txt",
                confidence=hand.confidence, needs_review=True,
                note="mão extraída por IA de formato não padronizado — confira os valores",
            )
        return IngestResult([], None, "txt", confidence=0.0, needs_review=True,
                            note="formato não reconhecido")

    if fmt == "pdf":
        text = _pdf_to_text(content)
        if text and detect_site(text):
            return IngestResult(parse_text(text), detect_site(text), "pdf", confidence=0.95)
        # PDF-imagem (sem texto): cai no fluxo de visão
        return _vision_ingest(content, "pdf")

    if fmt in ("image", "png", "jpg", "jpeg"):
        media = "image/jpeg" if fmt in ("jpg", "jpeg") else "image/png"
        return _vision_ingest(content, "image", media)

    return IngestResult([], None, fmt, confidence=0.0, needs_review=True,
                        note=f"formato '{fmt}' não suportado")


def _looks_like_poker_text(text: str) -> bool:
    """Heurística barata: o texto tem sinais de mão de poker?

    Protege o fallback de IA contra texto aleatório (alucinação + custo).
    Cartas só contam na notação exata (rank maiúsculo + naipe minúsculo, ou
    naipe unicode): 'Kd', 'A♥'. Tokens que colidem com português corrente
    ('As' = artigo; '5h' = horário) não bastam sozinhos.
    """
    import re

    cards = re.findall(r"\b(?:10|[AKQJT2-9])[shdc]\b", text)
    cards += re.findall(r"(?:10|[AKQJT2-9])[♠♥♦♣](?!\w)", text)
    ambiguous = {"As", "2h", "3h", "4h", "5h", "6h", "7h", "8h", "9h", "10h"}
    strong = [c for c in cards if c not in ambiguous]

    keywords = ("flop", "turn", "river", "blind", "all-in", "allin", "pot",
                "raise", "fold", "showdown", "dealer", "button", "ante")
    hits = sum(1 for k in keywords if k in text.lower())

    if len(strong) >= 2:
        return True
    if len(cards) >= 2 and hits >= 1:
        return True
    return hits >= 2


def _vision_ingest(content: bytes | str, fmt: str, media: str = "image/png") -> IngestResult:
    """Extrai um snapshot de mão via visão do Claude (confidence < 1.0)."""
    from app.agent.llm import extract_from_image

    if isinstance(content, str):
        content = content.encode()
    hand = extract_from_image(content, media)
    if hand is None:
        from app.agent import llm as _llm

        why = _llm.LAST_VISION_ERROR or "sem ANTHROPIC_API_KEY ou JSON sem mão"
        return IngestResult([], None, fmt, confidence=0.0, needs_review=True,
                            note=f"visão falhou: {why}")
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
