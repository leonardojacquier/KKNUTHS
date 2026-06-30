"""Interface comum de parsers de hand history."""
from __future__ import annotations

from typing import Protocol

from app.models.canonical import CanonicalHand


class HandParser(Protocol):
    """Um parser converte texto bruto de uma sala em uma lista de mãos canônicas."""

    site: str

    def matches(self, raw_text: str) -> bool:
        """Retorna True se este parser reconhece o formato do texto."""
        ...

    def parse(self, raw_text: str) -> list[CanonicalHand]:
        """Converte o texto (pode conter várias mãos) em mãos canônicas."""
        ...


def assign_positions(seats: list[int], button_seat: int) -> dict[int, str]:
    """Mapeia seat -> posição (BTN, SB, BB, UTG, ..., CO) a partir do botão.

    `seats` são os assentos ocupados (em qualquer ordem). A ordem de ação no
    pós-flop começa no SB (assento seguinte ao botão, sentido horário). Posições
    intermediárias recebem rótulos de uma cauda padrão (UTG primeiro a agir).
    """
    if not seats:
        return {}
    ordered = sorted(seats)
    n = len(ordered)

    # rotação horária começando logo após o botão
    if button_seat in ordered:
        start = ordered.index(button_seat)
    else:  # botão "morto": pega o maior assento <= button
        start = max((i for i, s in enumerate(ordered) if s <= button_seat), default=n - 1)
    rotated = ordered[start + 1:] + ordered[: start + 1]  # SB ... BTN (botão por último)

    if n == 2:  # heads-up: botão é o SB
        return {button_seat: "BTN", rotated[0]: "BB"}

    # rotated está na ordem SB, BB, ..., BTN (botão por último).
    # Estrutura: [SB, BB] + meio + (CO se n>=4) + [BTN]
    tail = ["UTG", "UTG+1", "UTG+2", "MP", "MP+1", "LJ", "HJ"]
    has_co = n >= 4
    middle_count = n - 3 - (1 if has_co else 0)

    labels: list[str] = ["SB", "BB"]
    labels += tail[:middle_count]
    if has_co:
        labels.append("CO")
    labels.append("BTN")

    return {seat: labels[i] for i, seat in enumerate(rotated)}
