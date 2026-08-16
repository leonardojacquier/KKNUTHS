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
from app.bot.guarda_fatos import conferir_board
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


# ---------------------------------------------------------------------------
# CONSERTO 3 — o guarda do board: confere as cartas citadas contra o board real
#
# Nenhum guarda fazia isso: `conferir_dominancia` cuida de "só perde para X",
# `corrigir_showdown` cuida das cartas do showdown, `conferir_analise` confere
# NÚMEROS contra lastro — e naipe não é número.
#
# A regra de segurança é o coração do guarda: corrigir carta em prosa livre é
# perigoso, porque o coach legitimamente escreve hipótese ("se viesse o 2♦
# você fechava") e "corrigir" isso estragaria o texto. Então só corrige DENTRO
# da citação da linha do placar (R2), e só quando é inequívoco.

def _hand():
    return _mao_do_caso_real()


def test_o_2_de_ouros_do_caso_real_vira_2_de_copas():
    """O erro que quebrou a análise de 16/08: o 2♦ inventado no lugar do 2♥."""
    texto = ("🟡 Dava pra jogar melhor — o flop saiu caro\n"
             "❌ *Flop* 9♥J♦2♦ — c-bet com K high: 12bb no pote.")
    novo, achados = conferir_board(texto, _hand())

    assert "*Flop* 9♥J♦2♥ —" in novo
    assert "2♦" not in novo
    assert len(achados) == 1
    assert achados[0]["citada"] == "2♦"
    assert achados[0]["corrigido_para"] == "2♥"
    assert achados[0]["onde"] == "placar"
    assert achados[0]["street"] == "flop"


def test_o_naipe_branco_tambem_e_erro():
    """A segunda passagem escreveu 2♠: poker idêntico, board diferente. Fato
    é fato — o aluno vai comparar com o replay."""
    novo, achados = conferir_board("❌ *Flop* 9♥J♦2♠ — c-bet.", _hand())
    assert "9♥J♦2♥" in novo
    assert achados[0]["corrigido_para"] == "2♥"


def test_linha_do_placar_certa_atravessa_intacta():
    """Guarda que estraga texto certo é pior que guarda ausente."""
    texto = ("✅ Você jogou bem — linha limpa\n"
             "✅ *Flop* 9♥ J♦ 2♥ — c-bet de 4bb com K high.\n"
             "🟡 *Turn* 9♥ J♦ 2♥ 5♦ — check behind.")
    novo, achados = conferir_board(texto, _hand())
    assert novo == texto and achados == []


def test_a_linha_do_turn_confere_contra_o_board_CUMULATIVO():
    """O board "no turn" é flop+turn: a carta do flop citada na linha do turn
    tem que ser conferida contra as quatro."""
    novo, achados = conferir_board("🟡 *Turn* 9♥J♦2♠5♦ — check behind.",
                                   _hand())
    assert "9♥J♦2♥5♦" in novo
    assert achados[0]["corrigido_para"] == "2♥"


def test_hipotese_na_prosa_e_medida_mas_nunca_corrigida():
    """O CORAÇÃO da regra de segurança: "se viesse o 2♦" é hipótese legítima
    do coach. Corrigir isso estragaria a frase — vira evento, nada mais."""
    texto = ("✅ *Flop* 9♥J♦2♥ — c-bet certa.\n\n"
             "Se viesse o 2♦ você fechava o flush draw — não veio.")
    novo, achados = conferir_board(texto, _hand())

    assert novo == texto, "prosa livre NÃO se reescreve"
    assert [a["onde"] for a in achados] == ["prosa"]
    assert achados[0]["citada"] == "2♦"
    assert achados[0]["corrigido_para"] is None


def test_o_porque_da_propria_linha_do_placar_tambem_e_so_medido():
    """Dentro da linha do placar, só a CITAÇÃO (antes do travessão) é fato de
    board; o porquê depois dele já é prosa."""
    texto = "✅ *Flop* 9♥J♦2♥ — se viesse o 2♦ você fechava."
    novo, achados = conferir_board(texto, _hand())
    assert novo == texto
    assert [a["onde"] for a in achados] == ["prosa"]


def test_carta_de_verdade_da_mao_nunca_e_reescrita():
    """A trava que impede o pior falso positivo: a linha do placar cita a MÃO
    do herói ("com K♦ na mão") e o board tem K♥. Sem esta trava, o guarda
    trocaria a carta do ALUNO por uma do board."""
    h = _mao([Street(name=StreetName.PREFLOP, actions=[]),
              Street(name=StreetName.FLOP, board=["Kh", "Jd", "2h"],
                     actions=[])],
             ["Kh", "Jd", "2h"], hero_cards=["Kd", "8s"])
    texto = "❌ *Flop* K♥J♦2♥ com K♦ na mão — top pair fraco."
    novo, achados = conferir_board(texto, h)
    assert novo == texto
    assert achados == []


def test_rank_repetido_no_board_e_ambiguo_e_nao_se_toca():
    """Board 9♥J♦9♦: "9♠" pode ser erro de qualquer um dos dois noves. Não
    dá para corrigir sem chutar — evento, não correção."""
    h = _mao([Street(name=StreetName.PREFLOP, actions=[]),
              Street(name=StreetName.FLOP, board=["9h", "Jd", "9d"],
                     actions=[])],
             ["9h", "Jd", "9d"])
    novo, achados = conferir_board("❌ *Flop* 9♥J♦9♠ — trinca não.", h)
    assert novo.startswith("❌ *Flop* 9♥J♦9♠")
    assert achados[0]["corrigido_para"] is None
    assert achados[0]["onde"] == "placar"


def test_carta_que_nao_esta_no_board_da_street_nao_e_corrigida():
    """O A♠ citado na linha do FLOP com o A♥ só no river: a citação está fora
    de lugar, mas trocar naipe aqui seria chute."""
    h = _mao([Street(name=StreetName.PREFLOP, actions=[]),
              Street(name=StreetName.FLOP, board=FLOP_REAL, actions=[]),
              Street(name=StreetName.TURN, board=["5d"], actions=[]),
              Street(name=StreetName.RIVER, board=["Ah"], actions=[])],
             ["9h", "Jd", "2h", "5d", "Ah"])
    novo, achados = conferir_board("❌ *Flop* 9♥J♦A♠ — c-bet.", h)
    assert novo == "❌ *Flop* 9♥J♦A♠ — c-bet."
    assert achados[0]["corrigido_para"] is None


def test_linha_do_pre_cita_a_mao_do_heroi_e_passa_limpa():
    """*Pré* não tem board: nada ali é conferível contra mesa nenhuma."""
    texto = "✅ *Pré* — 3-bet K♣8♠: contra o range dele, +EV."
    novo, achados = conferir_board(texto, _hand())
    assert novo == texto and achados == []


def test_texto_sem_board_na_mao_nao_e_tocado():
    h = _mao([Street(name=StreetName.PREFLOP, actions=[])], [])
    texto = "✅ *Pré* — jam de 12bb.\nSe viesse o 2♦ era outra história."
    novo, achados = conferir_board(texto, h)
    assert novo == texto and achados == []


# ---------------------------------------------------------------------------
# LIGADO EM PRODUÇÃO — guarda que não é chamado é código morto. Este teste
# roda o pipeline inteiro (LLM e banco falsos) e olha só as duas coisas que
# importam: o TEXTO que chega ao aluno e os EVENTOS gravados.


def _mao_de_pipeline() -> CanonicalHand:
    from app.models.canonical import Action, ActionType

    return CanonicalHand(
        hand_id="f2cd6504", site="PPPoker", hero="KKNUThS",
        hero_cards=["Kc", "8s"], source_format="txt", confidence=1.0,
        stakes=Stakes(small_blind=100, big_blind=200),
        players=[
            PlayerSeat(seat=1, name="KKNUThS", stack=20000, is_hero=True,
                       position="BTN"),
            PlayerSeat(seat=2, name="vilao", stack=20000, position="BB")],
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                Action(actor="KKNUThS", type=ActionType.RAISE, amount=500,
                       to_amount=500),
                Action(actor="vilao", type=ActionType.CALL, amount=300)]),
            Street(name=StreetName.FLOP, board=FLOP_REAL, actions=[
                Action(actor="vilao", type=ActionType.CHECK),
                Action(actor="KKNUThS", type=ActionType.BET, amount=700),
                Action(actor="vilao", type=ActionType.CALL, amount=700)]),
            Street(name=StreetName.TURN, board=["5d"], actions=[
                Action(actor="vilao", type=ActionType.CHECK),
                Action(actor="KKNUThS", type=ActionType.CHECK)]),
            Street(name=StreetName.RIVER, board=["3c"], actions=[
                Action(actor="vilao", type=ActionType.BET, amount=1500),
                Action(actor="KKNUThS", type=ActionType.FOLD)])],
        final_board=["9h", "Jd", "2h", "5d", "3c"],
        collected={"vilao": 3400})


def test_o_flop_errado_nao_chega_ao_aluno(rodar_pipeline):
    """A asserção que nenhuma substring consegue fazer: o texto ENTREGUE tem
    o flop certo, e o evento ficou gravado."""
    texto = ("🟡 Dava pra jogar melhor — o river ficou caro\n"
             "❌ *Flop* 9♥J♦2♦ — c-bet de 3.5bb com K high.\n"
             "✅ *River* 9♥J♦2♥5♦3♣ — fold de 7.5bb: certo.")
    saida, repo, _ = rodar_pipeline(texto, _mao_de_pipeline())

    assert "9♥J♦2♥ — c-bet" in saida, (
        f"o flop errado sobreviveu até o aluno: {saida[:300]}")
    assert "2♦" not in saida
    evento = repo.evento("board_corrigido")
    assert evento, "corrigiu o texto e não registrou o evento"
    assert evento["achados"][0]["citada"] == "2♦"
    assert evento["achados"][0]["corrigido_para"] == "2♥"


def test_hipotese_do_coach_chega_intacta_ao_aluno_e_vira_evento(rodar_pipeline):
    """O outro lado do portão em produção: prosa livre atravessa sem um
    caractere mexido, e a frequência fica medida."""
    texto = ("🟡 Dava pra jogar melhor — o river ficou caro\n"
             "❌ *Flop* 9♥J♦2♥ — c-bet de 3.5bb com K high.\n"
             "✅ *River* 9♥J♦2♥5♦3♣ — fold de 7.5bb: certo.\n\n"
             "Se viesse o 2♦ no turn a história era outra.")
    saida, repo, _ = rodar_pipeline(texto, _mao_de_pipeline())

    assert "Se viesse o 2♦ no turn" in saida
    assert repo.evento("board_corrigido") is None
    evento = repo.evento("board_nao_conferido")
    assert evento and evento["achados"][0]["citada"] == "2♦"
    assert evento["achados"][0]["onde"] == "prosa"
