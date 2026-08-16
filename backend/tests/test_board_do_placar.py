"""O BOARD tem que chegar pronto ao modelo — e voltar conferido do modelo.

Caso real de 16/08, mão f2cd6504-9faa-48d5-87f7-1adfa6770ad2, board 9h Jd 2h
5d 3c. O contexto só levava o board FINAL numa string única ("9♥ J♦ 2♥ 5♦
3♣") e o coach precisava fatiar as três primeiras de cabeça para escrever a
linha do placar. Ele errou duas vezes:

  - prompt antigo: "*Flop* 9♥J♦2♦" — erro MATERIAL. O 2♦ inventa um flush
    draw que não existia e a análise inteira se apoia nele ("c-bet com K
    high + flush draw", "o turn 5♦ que completa seu flush draw").
  - prompt novo: "*Flop* 9♥J♦2♠" — naipe errado, poker idêntico.

São dois consertos: dar o board fatiado por street (o modelo copia em vez de
fatiar) e conferir o que ele escreveu na linha do placar contra o board real.
"""
from __future__ import annotations

from app.agent.analyzer import analyze_hand
from app.models.canonical import (CanonicalHand, PlayerSeat, Stakes, Street,
                                  StreetName)

FLOP_REAL = ["9h", "Jd", "2h"]


def _mao(streets: list[Street], final_board: list[str],
         hero_cards: list[str] | None = None) -> CanonicalHand:
    return CanonicalHand(
        site="pppoker", hand_id="f2cd6504", hero="Hero",
        stakes=Stakes(small_blind=100, big_blind=200),
        players=[PlayerSeat(seat=1, name="Hero", stack=10000, is_hero=True)],
        hero_cards=hero_cards if hero_cards is not None else ["Kc", "8s"],
        final_board=final_board, streets=streets)


def _mao_do_caso_real() -> CanonicalHand:
    return _mao(
        [Street(name=StreetName.PREFLOP, actions=[]),
         Street(name=StreetName.FLOP, board=FLOP_REAL, actions=[]),
         Street(name=StreetName.TURN, board=["5d"], actions=[]),
         Street(name=StreetName.RIVER, board=["3c"], actions=[])],
        ["9h", "Jd", "2h", "5d", "3c"])


# ---------------------------------------------------------------------------
# CONSERTO 2 — o board chega fatiado, cumulativo e já bonito


def test_board_por_street_e_cumulativo_e_pronto_para_colar():
    """O board "no turn" é flop + turn: no canônico cada street guarda só as
    cartas NOVAS dela, e é a soma que o coach precisa copiar."""
    ct = analyze_hand(_mao_do_caso_real())["cartas_texto"]
    assert ct["board_por_street"] == {
        "flop": "9♥ J♦ 2♥",
        "turn": "9♥ J♦ 2♥ 5♦",
        "river": "9♥ J♦ 2♥ 5♦ 3♣",
    }
    assert ct["board"] == "9♥ J♦ 2♥ 5♦ 3♣"  # o board final continua lá


def test_mao_que_parou_no_flop_nao_ganha_chave_de_turn():
    """Só streets que existiram — chave de turn em mão que acabou no flop é
    convite para o coach narrar uma carta que não veio."""
    ct = analyze_hand(_mao(
        [Street(name=StreetName.PREFLOP, actions=[]),
         Street(name=StreetName.FLOP, board=FLOP_REAL, actions=[])],
        FLOP_REAL))["cartas_texto"]
    assert ct["board_por_street"] == {"flop": "9♥ J♦ 2♥"}


def test_board_por_street_soma_as_cartas_das_streets_nao_fatia_o_final():
    """Prova que a soma vem de `street(nome).board` (as cartas novas) e não
    de um fatiamento do final_board: sem final_board, o board por street
    continua saindo certo."""
    ct = analyze_hand(_mao(
        [Street(name=StreetName.PREFLOP, actions=[]),
         Street(name=StreetName.FLOP, board=FLOP_REAL, actions=[]),
         Street(name=StreetName.TURN, board=["5d"], actions=[])],
        []))["cartas_texto"]
    assert ct["board_por_street"] == {"flop": "9♥ J♦ 2♥",
                                      "turn": "9♥ J♦ 2♥ 5♦"}


def test_board_por_street_aguenta_a_fonte_que_ja_traz_cumulativo():
    """Convenção NÃO é uniforme entre parsers: pppoker_replay e phh gravam as
    cartas NOVAS da street; pokerstars e dealing_family gravam o board já
    somado. Somar às cegas daria 'turn' com 7 cartas."""
    ct = analyze_hand(_mao(
        [Street(name=StreetName.PREFLOP, actions=[]),
         Street(name=StreetName.FLOP, board=FLOP_REAL, actions=[]),
         Street(name=StreetName.TURN, board=FLOP_REAL + ["5d"], actions=[])],
        []))["cartas_texto"]
    assert ct["board_por_street"] == {"flop": "9♥ J♦ 2♥",
                                      "turn": "9♥ J♦ 2♥ 5♦"}


def test_mao_sem_board_nao_ganha_a_chave():
    ct = analyze_hand(_mao(
        [Street(name=StreetName.PREFLOP, actions=[])], []))["cartas_texto"]
    assert "board_por_street" not in ct
