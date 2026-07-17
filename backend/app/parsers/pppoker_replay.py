"""Parser de replay da PPPoker (link de clube).

O replayer da PPPoker é um jogo WebGL (Egret), mas a mão em si é um JSON
estático num CDN global da Alibaba: alicdn.pppoker.club/review_hand/<key>.json
(descoberto por captura de rede com browser headless). O `shareKey` do link
que o aluno cola É o nome do arquivo — extrair a mão vira um GET.

Formato (engenharia reversa de uma mão real):
- info.room: small_blind, ante, dealer_seatid, room_name, gameid, mtt
- info.players: user_name, seatid, hand_chips (stack), uid, isSelf (=herói)
- info.cards: as 2 cartas do herói (numéricas)
- flow.{pre_flop,flop,turn,river}: cards (board) + actions (seatid, chips,
  hand_chips, type) + pools + chips_back (aposta não paga devolvida)
- winning_info: vencedor e valor

Cartas: divmod(v, 256) = (naipe 1-4, rank 2-14). Ações: código `type`.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request

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

log = logging.getLogger("pppoker")

_CDN = "https://alicdn.pppoker.club/review_hand/{}.json"
_UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) AppleWebKit/605 "
                     "Mobile/15E148 Safari/604",
       "Referer": "https://replay.pppoker.net/"}

_RANK = {2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
         10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}
# naipes: escada asiática ouros<paus<copas<espadas (1..4). O mapa antigo
# ({1:s,...,4:c}) chutou a ordem ocidental invertida — o admin conferiu o
# VÍDEO do replay: as cartas de código 4 (que saíam como ♣) são ESPADAS.
_SUIT = {1: "d", 2: "c", 3: "h", 4: "s"}

# código de ação do JSON -> nosso ActionType
_ACT = {1: ActionType.FOLD, 12: ActionType.FOLD, 2: ActionType.CHECK,
        3: ActionType.CALL, 4: ActionType.RAISE, 7: ActionType.BET}
_POST = {8: "sb", 9: "bb", 10: "ante"}  # type -> post_type

_STREETS = [("pre_flop", StreetName.PREFLOP), ("flop", StreetName.FLOP),
            ("turn", StreetName.TURN), ("river", StreetName.RIVER)]

# nomes de posição por nº de jogadores, começando no SB
_POS = {
    2: ["SB", "BB"],
    3: ["SB", "BB", "BTN"],
    4: ["SB", "BB", "UTG", "BTN"],
    5: ["SB", "BB", "UTG", "CO", "BTN"],
    6: ["SB", "BB", "UTG", "MP", "CO", "BTN"],
    7: ["SB", "BB", "UTG", "MP", "HJ", "CO", "BTN"],
    8: ["SB", "BB", "UTG", "UTG+1", "MP", "HJ", "CO", "BTN"],
    9: ["SB", "BB", "UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN"],
}

_SHARE_RE = re.compile(r"[?&]shareKey=([0-9a-zA-Z-]{12,})")


def share_key_from_url(url: str) -> str | None:
    m = _SHARE_RE.search(url or "")
    return m.group(1) if m else None


def _card(v) -> str | None:
    try:
        suit, rank = divmod(int(v), 256)
    except (TypeError, ValueError):
        return None
    r, s = _RANK.get(rank), _SUIT.get(suit)
    return (r + s) if r and s else None


def _cards(seq) -> list[str]:
    return [c for c in (_card(v) for v in (seq or [])) if c]


def fetch_and_parse(share_key: str) -> CanonicalHand | None:
    """Busca o JSON da mão no CDN e converte para CanonicalHand. None em falha."""
    if not share_key:
        return None
    try:
        req = urllib.request.Request(_CDN.format(share_key), headers=_UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read(500_000).decode("utf-8", "ignore"))
        return parse(data, share_key)
    except Exception as exc:
        log.warning("pppoker replay %s falhou: %s", share_key[:12], exc)
        return None


def parse(data: dict, share_key: str = "") -> CanonicalHand | None:
    info = data.get("info") or {}
    room = info.get("room") or {}
    jplayers = info.get("players") or []
    flow = data.get("flow") or {}
    if not jplayers or "pre_flop" not in flow:
        return None

    # blinds/ante: dos posts reais (mais confiável que o room), com fallback
    sb = bb = ante = 0.0
    for a in flow.get("pre_flop", {}).get("actions", []):
        pt = _POST.get(a.get("type"))
        amt = float(a.get("chips") or 0)
        if pt == "sb":
            sb = amt
        elif pt == "bb":
            bb = amt
        elif pt == "ante":
            ante = max(ante, amt)
    sb = sb or float(room.get("small_blind") or 0)
    bb = bb or sb * 2
    ante = ante or float(room.get("ante") or 0)

    seat_name = {}
    hero = None
    players: list[PlayerSeat] = []
    shown: dict[str, list[str]] = {}
    for p in jplayers:
        seat = p.get("seatid")
        name = str(p.get("user_name") or f"seat{seat}")
        seat_name[seat] = name
        is_hero = bool(p.get("isSelf"))
        if is_hero:
            hero = name
        # cartas reveladas no showdown (quando o JSON traz por jogador) —
        # viram shown_cards e aparecem na banda "Resultado" do filme
        cs = _cards(p.get("cards"))
        if cs and not is_hero:
            shown[name] = cs
        players.append(PlayerSeat(
            seat=int(seat) if seat is not None else 0, name=name,
            stack=float(p.get("hand_chips") or 0), is_hero=is_hero))

    # posições: ordem horária começando no SB (quem postou o SB)
    _assign_positions(players, flow, seat_name)

    # streets + ações
    streets: list[Street] = []
    board: list[str] = []
    for key, sname in _STREETS:
        st = flow.get(key) or {}
        cards = _cards(st.get("cards"))
        board += cards
        acts: list[Action] = []
        committed: dict[int, float] = {}  # exclui antes (dead money)
        for a in st.get("actions", []):
            seat = a.get("seatid")
            actor = seat_name.get(seat, f"seat{seat}")
            chips = float(a.get("chips") or 0)
            after = a.get("hand_chips")
            t = a.get("type")
            if t in _POST:
                pt = _POST[t]
                if pt in ("sb", "bb"):
                    committed[seat] = committed.get(seat, 0) + chips
                acts.append(Action(actor=actor, type=ActionType.POST,
                                   amount=chips, post_type=pt))
                continue
            at = _ACT.get(t)
            if at is None:
                continue  # tipo desconhecido: ignora com segurança
            if at in (ActionType.BET, ActionType.RAISE, ActionType.CALL):
                committed[seat] = committed.get(seat, 0) + chips
            acts.append(Action(
                actor=actor, type=at, amount=chips,
                to_amount=committed.get(seat, 0),
                all_in=bool(after == 0 and at in (
                    ActionType.BET, ActionType.RAISE, ActionType.CALL))))
        if acts or cards:
            streets.append(Street(name=sname, board=cards, actions=acts))

    # pote e vencedor
    total_pot = None
    collected: dict[str, float] = {}
    for w in flow.get("winning_info", []):
        seat = w.get("seatid")
        chips = float(w.get("chips") or 0)
        if chips:
            collected[seat_name.get(seat, f"seat{seat}")] = chips
            total_pot = (total_pot or 0) + chips

    is_mtt = bool(room.get("mtt"))
    return CanonicalHand(
        site=f"PPPoker · {room.get('room_name') or 'clube'}"[:80],
        hand_id=f"pppoker-{share_key or room.get('gameid') or 'replay'}"[:64],
        format=HandFormat.TOURNAMENT if is_mtt else HandFormat.CASH,
        stakes=Stakes(small_blind=sb, big_blind=bb, ante=ante),
        hero=hero,
        players=players,
        hero_cards=_cards(info.get("cards")),
        shown_cards=shown,
        streets=streets,
        final_board=board,
        total_pot=total_pot,
        collected=collected,
        tournament_id=str(room.get("gameid") or "") or None,
        source_format="pppoker_replay",
        confidence=0.95,
    )


def _assign_positions(players, flow, seat_name) -> None:
    """Nomeia posições em ordem horária a partir do SB (quem postou o SB)."""
    sb_seat = None
    for a in flow.get("pre_flop", {}).get("actions", []):
        if a.get("type") == 8:  # SB
            sb_seat = a.get("seatid")
            break
    seats = sorted(p.seat for p in players)
    n = len(seats)
    names = _POS.get(n)
    if not names or sb_seat not in seats:
        return
    start = seats.index(sb_seat)
    order = seats[start:] + seats[:start]  # horário a partir do SB
    seat_pos = dict(zip(order, names))
    for p in players:
        p.position = seat_pos.get(p.seat)
