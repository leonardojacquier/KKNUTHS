"""Imagens de demonstração do site — geradas pelos renderizadores REAIS.

A landing vende o produto mostrando o produto: o filme da mão (com showdown
gráfico), a mesa do quiz e o card de desafio saem dos mesmos renderizadores
PIL do bot, a partir de uma mão 100% SINTÉTICA (nenhum dado de usuário).
Geradas na primeira visita e cacheadas em disco (custo zero depois).
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path

log = logging.getLogger("site_assets")

_ASSETS = Path(__file__).parent / "assets"

_DEMO = {
    "site_filme.png": "_filme",
    "site_mesa.png": "_mesa",
    "site_card.png": "_card",
}


def _demo_hand():
    """Mão sintética de vitrine: herói paga com top pair, vilão mostra a
    broadway no showdown — exibe filme, streets, reveals e vencedor."""
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      HandFormat, PlayerSeat, Stakes, Street,
                                      StreetName)

    pl = [
        PlayerSeat(seat=1, name="Hero", stack=9_000_000, position="BB",
                   is_hero=True),
        PlayerSeat(seat=2, name="Rival do Clube", stack=18_000_000,
                   position="BTN"),
        PlayerSeat(seat=3, name="TightPassivo", stack=6_000_000,
                   position="CO"),
    ]
    pre = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="Hero", type=ActionType.POST, amount=250_000,
               post_type="bb"),
        Action(actor="TightPassivo", type=ActionType.FOLD),
        Action(actor="Rival do Clube", type=ActionType.RAISE, amount=550_000,
               to_amount=550_000),
        Action(actor="Hero", type=ActionType.CALL, amount=300_000,
               to_amount=550_000),
    ])
    flop = Street(name=StreetName.FLOP, board=["Qs", "Th", "4d"], actions=[
        Action(actor="Hero", type=ActionType.CHECK),
        Action(actor="Rival do Clube", type=ActionType.BET, amount=700_000),
        Action(actor="Hero", type=ActionType.CALL, amount=700_000),
    ])
    turn = Street(name=StreetName.TURN, board=["Qs", "Th", "4d", "8c"],
                  actions=[
        Action(actor="Hero", type=ActionType.CHECK),
        Action(actor="Rival do Clube", type=ActionType.BET, amount=1_800_000),
        Action(actor="Hero", type=ActionType.CALL, amount=1_800_000),
    ])
    river = Street(name=StreetName.RIVER,
                   board=["Qs", "Th", "4d", "8c", "2s"], actions=[
        Action(actor="Hero", type=ActionType.CHECK),
        Action(actor="Rival do Clube", type=ActionType.BET, amount=4_200_000),
        Action(actor="Hero", type=ActionType.CALL, amount=4_200_000),
    ])
    # blinds de 125k/250k COM ante são forma de torneio; o modelo saía como
    # cash (o default), então o metadado contradizia a própria mão
    return CanonicalHand(
        site="Demo", hand_id="demo-site", hero="Hero",
        format=HandFormat.TOURNAMENT, tournament_id="demo-torneio",
        stakes=Stakes(small_blind=125_000, big_blind=250_000, ante=31_250),
        players=pl, hero_cards=["Qd", "Jd"],
        streets=[pre, flop, turn, river],
        final_board=["Qs", "Th", "4d", "8c", "2s"],
        shown_cards={"Rival do Clube": ["Ah", "Kc"]},
        collected={"Hero": 15_000_000}, total_pot=15_000_000)


def _filme() -> bytes | None:
    from app.bot.processing import hand_film_png

    return hand_film_png(_demo_hand())


def _mesa() -> bytes | None:
    from app.analysis.hand_figure import render_hand_figure

    return render_hand_figure({
        "title": "Quiz — sua vez",
        "hero_cards": ["Qd", "Jd"],
        "board": ["Qs", "Th", "4d"],
        "position": "BB", "stack_bb": 36.0, "pot_bb": 4.6,
        "to_call_bb": 2.8, "required_eq": 0.278, "street": "flop",
        "blinds": "125k/250k",
        "villains": [
            {"position": "BTN", "stack_bb": 72.0, "bet_bb": 2.8,
             "aggressor": True},
            {"position": "CO", "stack_bb": 24.0, "folded": True},
        ],
    })


def _card() -> bytes | None:
    from app.analysis.hand_figure import render_share_card

    return render_share_card({
        "hero_cards": ["Qd", "Jd"],
        "board": ["Qs", "Th", "4d"],
        "position": "BB", "stack_bb": 36.0, "pot_bb": 4.6,
        "to_call_bb": 2.8, "street": "flop",
    })


def ensure_demo_assets() -> None:
    """Gera as imagens que faltarem (uma vez; depois é leitura de disco)."""
    _ASSETS.mkdir(exist_ok=True)
    for name, fn_name in _DEMO.items():
        path = _ASSETS / name
        if path.exists() and path.stat().st_size > 1000:
            continue
        try:
            png = globals()[fn_name]()
            if png:
                path.write_bytes(png)
        except Exception as exc:
            log.warning("asset do site %s falhou: %s", name, exc)


def img_data(name: str) -> str:
    """data-URI base64 do asset (gera o lote na primeira chamada)."""
    ensure_demo_assets()
    try:
        raw = (_ASSETS / name).read_bytes()
        return "data:image/png;base64," + base64.standard_b64encode(raw).decode()
    except Exception:
        return ""
