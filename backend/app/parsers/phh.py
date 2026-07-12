"""Parser do formato PHH (Poker Hand History, .phh/.phhs) — padrão aberto TOML.

É o formato dos datasets públicos (mãos do WSOP etc.). Suportamos as
variantes de Texas Hold'em ('NT' no-limit, 'PT' pot-limit, 'FT' fixed);
as demais (stud, razz, omaha…) são reconhecidas e NOMEADAS na resposta —
"mão de Seven Card Stud; por enquanto analiso Hold'em" é honesto,
"não consegui ler" é mentira.
"""
from __future__ import annotations

import re

from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    HandFormat,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)

# nomes amigáveis das variantes PHH que NÃO analisamos (prefixo do variant)
_VARIANTES = {
    "F7S": "Seven Card Stud",
    "FR": "Razz",
    "FO": "Omaha Hi-Lo",
    "PO": "Pot-Limit Omaha",
    "FB": "Badugi",
    "F2L1D": "2-7 Lowball",
    "N2L1D": "2-7 Lowball",
    "FD": "Five Card Draw",
    "NS": "Short Deck",
}

_HOLDEM = {"NT", "PT", "FT"}  # no-limit / pot-limit / fixed-limit hold'em


def looks_like_phh(text: str) -> bool:
    return bool(re.match(r"^\s*(\[\d+\]\s*\n)?\s*variant\s*=", text or ""))


def _cards(s: str) -> list[str]:
    """'7d2dTs' -> ['7d','2d','Ts'] (ignora '??' de carta oculta)."""
    out = []
    for i in range(0, len(s) - 1, 2):
        c = s[i:i + 2]
        if c != "??":
            out.append(c[0].upper() + c[1].lower())
    return out


def _variant_name(variant: str) -> str | None:
    """Nome amigável de variante não-hold'em; None quando é hold'em."""
    v = (variant or "").upper()
    if v in _HOLDEM:
        return None
    for prefix, nome in sorted(_VARIANTES.items(), key=lambda x: -len(x[0])):
        if v.startswith(prefix):
            return nome
    return f"variante '{variant}'"


def parse_phh(text: str) -> tuple[list[CanonicalHand], str]:
    """Retorna (mãos hold'em parseadas, nota). Nota explica variantes puladas."""
    try:
        import tomllib  # py3.11+
    except ModuleNotFoundError:
        import tomli as tomllib  # VPS em py3.10

    try:
        data = tomllib.loads(text)
    except Exception as exc:
        return [], f"PHH inválido: {exc}"

    # .phhs = várias mãos em tabelas numeradas; .phh = uma mão na raiz
    tables = ([data[k] for k in sorted(data, key=lambda x: int(x))
               if isinstance(data[k], dict)]
              if data and all(k.isdigit() for k in data) else [data])

    hands: list[CanonicalHand] = []
    skipped: list[str] = []
    for t in tables:
        nome = _variant_name(str(t.get("variant") or ""))
        if nome is not None:
            skipped.append(nome)
            continue
        try:
            h = _parse_one(t)
            if h is not None:
                hands.append(h)
        except Exception:
            skipped.append("mão ilegível")
    note = ""
    if skipped:
        note = ("mão de " + ", ".join(sorted(set(skipped))) +
                " — por enquanto analiso Texas Hold'em")
    return hands, note


def _parse_one(t: dict) -> CanonicalHand | None:
    names = [str(n) for n in (t.get("players") or [])]
    stacks = [float(s) for s in (t.get("starting_stacks") or [])]
    n = max(len(names), len(stacks))
    if n < 2:
        return None
    names = names or [f"p{i + 1}" for i in range(n)]
    blinds = [float(b) for b in (t.get("blinds_or_straddles") or [])]
    antes = [float(a) for a in (t.get("antes") or [])]
    sb = blinds[0] if len(blinds) > 0 else 0.0
    bb = blinds[1] if len(blinds) > 1 else 0.0
    ante = max(antes) if antes else 0.0

    hole: dict[str, list[str]] = {}
    shown: dict[str, list[str]] = {}
    streets: list[Street] = [Street(name=StreetName.PREFLOP, actions=[])]
    board: list[str] = []
    order = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN,
             StreetName.RIVER]
    committed: dict[str, float] = {}
    street_bet = bb

    def pname(tok: str) -> str:
        idx = int(tok[1:]) - 1
        return names[idx] if idx < len(names) else tok

    # posts de blinds/antes na abertura do preflop
    for i, amt in enumerate(antes):
        if amt > 0 and i < len(names):
            streets[0].actions.append(Action(
                actor=names[i], type=ActionType.POST, amount=amt,
                post_type="ante"))
    for i, amt in enumerate(blinds):
        if amt > 0 and i < len(names):
            kind = "sb" if i == 0 else "bb"
            streets[0].actions.append(Action(
                actor=names[i], type=ActionType.POST, amount=amt,
                post_type=kind))
            committed[names[i]] = amt

    for raw in (t.get("actions") or []):
        parts = str(raw).split()
        if not parts:
            continue
        if parts[0] == "d":
            if parts[1] == "dh" and len(parts) >= 4:
                hole[pname(parts[2])] = _cards(parts[3])
            elif parts[1] == "db" and len(parts) >= 3:
                cards = _cards("".join(parts[2:]))
                board += cards
                if len(streets) < 4:
                    streets.append(Street(name=order[len(streets)],
                                          actions=[], board=cards))
                    committed = {}
                    street_bet = 0.0
            continue
        actor = pname(parts[0])
        verb = parts[1] if len(parts) > 1 else ""
        cur = streets[-1]
        if verb == "f":
            cur.actions.append(Action(actor=actor, type=ActionType.FOLD))
        elif verb == "cc":
            owed = street_bet - committed.get(actor, 0.0)
            if owed > 0:
                cur.actions.append(Action(actor=actor, type=ActionType.CALL,
                                          amount=owed, to_amount=street_bet))
                committed[actor] = street_bet
            else:
                cur.actions.append(Action(actor=actor, type=ActionType.CHECK))
        elif verb == "cbr" and len(parts) >= 3:
            to = float(parts[2])
            kind = ActionType.RAISE if street_bet > 0 else ActionType.BET
            cur.actions.append(Action(
                actor=actor, type=kind, amount=to - committed.get(actor, 0.0),
                to_amount=to))
            committed[actor] = to
            street_bet = to
        elif verb == "sm" and len(parts) >= 3:
            shown[actor] = _cards(parts[2])

    # herói: quem tem as cartas conhecidas (dado de broadcast tem várias — o
    # aluno pode dizer "eu sou o X" na legenda e o coach usa o relato)
    hero = next((p for p in names if hole.get(p)), None)

    players = [PlayerSeat(seat=i + 1, name=names[i],
                          stack=stacks[i] if i < len(stacks) else 0.0,
                          is_hero=(names[i] == hero)) for i in range(n)]
    played_at = None
    if t.get("year"):
        played_at = (f"{int(t['year']):04d}-{int(t.get('month') or 1):02d}-"
                     f"{int(t.get('day') or 1):02d}")

    return CanonicalHand(
        site=str(t.get("event") or "PHH")[:80],
        hand_id=f"phh-{t.get('hand') or abs(hash(str(t))) % 10 ** 8}",
        format=HandFormat.TOURNAMENT if t.get("event") else HandFormat.CASH,
        stakes=Stakes(small_blind=sb, big_blind=bb, ante=ante),
        hero=hero,
        players=players,
        hero_cards=hole.get(hero, []) if hero else [],
        streets=streets,
        final_board=board,
        shown_cards=shown,
        played_at=played_at,
        source_format="phh",
        confidence=0.95,
    )
