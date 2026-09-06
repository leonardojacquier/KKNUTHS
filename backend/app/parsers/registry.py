"""Roteia texto bruto para o parser de sala correto."""
from __future__ import annotations

import re

from app.models.canonical import CanonicalHand
from app.parsers.dealing_family import PartyPokerParser, Poker888Parser
from app.parsers.ggpoker import GGPokerParser
from app.parsers.pokerstars import PokerStarsParser
from app.parsers.winamax import WinamaxParser

# parsers determinísticos disponíveis (ordem importa: o primeiro que casar vence;
# 888 antes do Party porque o header do 888 também contém "Hand History for Game")
_PARSERS = [
    PokerStarsParser(),
    GGPokerParser(),
    WinamaxParser(),
    Poker888Parser(),
    PartyPokerParser(),
]

# início de mão de QUALQUER sala conhecida — para segmentar pastes mistos
_ANY_HEADER = re.compile(
    r"(?m)(?=^PokerStars (?:Zoom |Home Game )?(?:Hand|Game) #"
    r"|^Poker Hand #"
    r"|^Winamax Poker - "
    r"|^\*{5} Hand History"
    r"|^#Game No"
    r"|^\*{5} 888poker)"
)


def detect_site(raw_text: str) -> str | None:
    for p in _PARSERS:
        if p.matches(raw_text):
            return p.site
    return None


def parse_text(raw_text: str) -> list[CanonicalHand]:
    """Detecta a(s) sala(s) e retorna as mãos canônicas.

    Um paste pode misturar salas (ex.: PS + GG copiados juntos): nesse caso o
    texto é segmentado por header e cada mão vai ao seu parser — um parser só
    nunca deve "engolir" as linhas da mão de outra sala.

    Levanta `ValueError` se nenhum parser determinístico reconhecer o formato —
    nesse ponto o orquestrador deve cair no fluxo de LLM (visão/inferência).
    """
    matching = [p for p in _PARSERS if p.matches(raw_text)]
    if not matching:
        raise ValueError(
            "formato não reconhecido por parser determinístico; "
            "encaminhar para o fluxo de inferência por LLM"
        )
    if len(matching) == 1:
        return matching[0].parse(raw_text)

    hands: list[CanonicalHand] = []
    for segment in _ANY_HEADER.split(raw_text):
        if not segment.strip():
            continue
        for p in _PARSERS:
            if p.matches(segment):
                hands.extend(p.parse(segment))
                break
    return hands
