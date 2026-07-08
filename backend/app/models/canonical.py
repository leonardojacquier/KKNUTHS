"""Formato canônico de mão.

Todos os parsers (txt, csv, pdf, imagem) convergem para `CanonicalHand`. Isso isola o
resto do sistema da variedade de formatos das salas. O campo `confidence` indica a
qualidade do parse (1.0 = hand history nativa; <1.0 = visão/OCR/inferência).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

RANKS = "23456789TJQKA"
SUITS = "cdhs"


class GameType(str, Enum):
    NLHE = "NLHE"
    PLO = "PLO"
    LHE = "LHE"
    OTHER = "OTHER"


class HandFormat(str, Enum):
    TOURNAMENT = "tournament"
    SNG = "sng"
    CASH = "cash"


class StreetName(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class ActionType(str, Enum):
    POST = "post"        # blinds / antes
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"


def _validate_card(card: str) -> str:
    card = card.strip()
    if len(card) != 2 or card[0] not in RANKS or card[1] not in SUITS:
        raise ValueError(f"carta inválida: {card!r} (esperado ex. 'As', 'Td', '9c')")
    return card


class Stakes(BaseModel):
    buyin: Optional[float] = None
    currency: str = "USD"
    small_blind: float = 0
    big_blind: float = 0
    ante: float = 0
    level: Optional[str] = None  # ex. "V (30/60)" em torneio


class PlayerSeat(BaseModel):
    seat: int
    name: str
    stack: float
    position: Optional[str] = None  # BTN, SB, BB, UTG, CO...
    is_hero: bool = False
    bounty: Optional[float] = None


class Action(BaseModel):
    actor: str
    type: ActionType
    amount: float = 0          # valor adicionado nesta ação
    to_amount: float = 0       # total apostado na street (para raises)
    all_in: bool = False
    post_type: Optional[str] = None  # 'sb' | 'bb' | 'ante' (quando type == POST)


class Street(BaseModel):
    name: StreetName
    board: list[str] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)

    @field_validator("board")
    @classmethod
    def _check_board(cls, v: list[str]) -> list[str]:
        return [_validate_card(c) for c in v]


class CanonicalHand(BaseModel):
    hand_id: str
    site: str
    game: GameType = GameType.NLHE
    format: HandFormat = HandFormat.CASH
    stakes: Stakes = Field(default_factory=Stakes)

    max_seats: int = 9
    button_seat: Optional[int] = None
    tournament_id: Optional[str] = None

    hero: Optional[str] = None
    hero_cards: list[str] = Field(default_factory=list)

    players: list[PlayerSeat] = Field(default_factory=list)
    streets: list[Street] = Field(default_factory=list)

    total_pot: Optional[float] = None
    rake: float = 0
    collected: dict[str, float] = Field(default_factory=dict)  # name -> chips ganhos
    # aposta não paga devolvida ("Uncalled bet (X) returned to Y") — sem isso o
    # resultado líquido de toda mão ganha sem showdown sai errado
    uncalled: dict[str, float] = Field(default_factory=dict)
    # resultado líquido do herói quando a fonte já o traz pronto (CSV de tracker,
    # que não tem ações para reconstruir) — inclusive negativo
    net_won: Optional[float] = None
    final_board: list[str] = Field(default_factory=list)
    # cartas viradas no showdown (jogador -> 2 cartas): dado rotulado que
    # calibra as likelihoods do range tracker com o field real da base
    shown_cards: dict[str, list[str]] = Field(default_factory=dict)

    played_at: Optional[str] = None  # ISO string
    confidence: float = 1.0
    source_format: str = "txt"       # txt | csv | pdf | image

    @field_validator("hero_cards", "final_board")
    @classmethod
    def _check_cards(cls, v: list[str]) -> list[str]:
        return [_validate_card(c) for c in v]

    # ---- conveniências usadas pela análise ----
    def street(self, name: StreetName) -> Optional[Street]:
        for s in self.streets:
            if s.name == name:
                return s
        return None

    def hero_seat(self) -> Optional[PlayerSeat]:
        for p in self.players:
            if p.is_hero:
                return p
        return None
