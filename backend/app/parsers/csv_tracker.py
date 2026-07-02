"""Importa CSV exportado de trackers (Hold'em Manager, PokerTracker, etc.).

CSVs de tracker são RESUMOS por mão (sem a ação street a street), então geram
"mãos-resumo": cartas do herói, resultado e data — suficientes para volume,
resultado ao longo do tempo e relatório semanal; não alimentam o replay/simulador.

Detecção de colunas é flexível (nomes em EN/PT variam por tracker/versão).
Naipes aceitos como letras (AsKd) ou símbolos (A♠ K♦).
"""
from __future__ import annotations

import csv
import io
import re

from app.models.canonical import CanonicalHand, HandFormat

_SUIT_SYMBOLS = {"♠": "s", "♥": "h", "♦": "d", "♣": "c"}

_COLUMN_HINTS: dict[str, list[str]] = {
    "hand_id": ["hand id", "hand #", "hand#", "handid", "id da mao", "game id", "game #"],
    "cards": ["hole cards", "cards", "holecards", "cartas", "hole"],
    "net": ["net won", "amount won", "net", "profit", "won", "resultado", "ganho", "my c won"],
    "bb_won": ["bb won", "bbs won", "bb/100", "big blinds won"],
    "date": ["date", "datetime", "time", "data", "played", "timestamp"],
    "site": ["site", "sala", "room", "network"],
    "stakes": ["stakes", "limit", "blinds", "level"],
    "position": ["position", "pos", "posicao", "seat"],
    "tourney": ["tournament", "tourney", "torneio", "trny"],
}


def _find_columns(header: list[str]) -> dict[str, int]:
    """Mapeia campo lógico -> índice da coluna, por correspondência tolerante."""
    cols: dict[str, int] = {}
    norm = [h.strip().lower() for h in header]
    for field, hints in _COLUMN_HINTS.items():
        for i, name in enumerate(norm):
            if any(hint in name for hint in hints):
                cols[field] = i
                break
    return cols


def _parse_cards(raw: str) -> list[str]:
    if not raw:
        return []
    s = raw.strip()
    for sym, letter in _SUIT_SYMBOLS.items():
        s = s.replace(sym, letter)
    s = s.replace("10", "T")
    tokens = re.findall(r"[2-9TJQKAtjqka][shdcSHDC]", s)
    out = []
    for t in tokens[:2]:
        out.append(t[0].upper() + t[1].lower())
    return out


def _num(raw: str) -> float | None:
    if not raw:
        return None
    s = re.sub(r"[^\d.,\-]", "", raw.strip())
    if not s:
        return None
    # "1.234,56" (pt) vs "1,234.56" (en)
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rindex(".") > s.rindex(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def looks_like_tracker_csv(text: str) -> bool:
    """Heurística: primeira linha tem separador e ao menos 2 colunas conhecidas."""
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    if first.count(",") < 1 and first.count(";") < 1 and first.count("\t") < 1:
        return False
    delim = ";" if first.count(";") > first.count(",") else ("\t" if "\t" in first else ",")
    cols = _find_columns(first.split(delim))
    return len(cols) >= 2 and ("cards" in cols or "hand_id" in cols)


def parse_tracker_csv(text: str) -> list[CanonicalHand]:
    """CSV -> mãos-resumo canônicas. Linhas ilegíveis são puladas."""
    text = text.lstrip("﻿")
    first = text.splitlines()[0]
    delim = ";" if first.count(";") > first.count(",") else ("\t" if "\t" in first else ",")

    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = list(reader)
    if len(rows) < 2:
        return []
    cols = _find_columns(rows[0])
    if not cols:
        return []

    def get(row: list[str], field: str) -> str:
        i = cols.get(field)
        return row[i].strip() if i is not None and i < len(row) else ""

    hands: list[CanonicalHand] = []
    for k, row in enumerate(rows[1:]):
        if not any(cell.strip() for cell in row):
            continue
        try:
            hand_id = get(row, "hand_id") or f"csv-{k+1}"
            net = _num(get(row, "net"))
            is_tourney = bool(get(row, "tourney"))
            hand = CanonicalHand(
                hand_id=hand_id,
                site=get(row, "site") or "tracker-csv",
                format=HandFormat.TOURNAMENT if is_tourney else HandFormat.CASH,
                hero="Hero",
                hero_cards=_parse_cards(get(row, "cards")),
                played_at=get(row, "date") or None,
                source_format="csv",
                confidence=0.9,
            )
            if net and net > 0:
                hand.collected["Hero"] = net
            hands.append(hand)
        except Exception:
            continue
    return hands
