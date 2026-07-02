"""Roteia texto bruto para o parser de sala correto."""
from __future__ import annotations

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


def detect_site(raw_text: str) -> str | None:
    for p in _PARSERS:
        if p.matches(raw_text):
            return p.site
    return None


def parse_text(raw_text: str) -> list[CanonicalHand]:
    """Detecta a sala e retorna as mãos canônicas.

    Levanta `ValueError` se nenhum parser determinístico reconhecer o formato —
    nesse ponto o orquestrador deve cair no fluxo de LLM (visão/inferência).
    """
    for p in _PARSERS:
        if p.matches(raw_text):
            return p.parse(raw_text)
    raise ValueError(
        "formato não reconhecido por parser determinístico; "
        "encaminhar para o fluxo de inferência por LLM"
    )
