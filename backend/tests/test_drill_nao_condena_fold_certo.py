"""O gabarito do drill não pode decidir pós-flop com equity vs mão aleatória.

Achado da auditoria de poker (07/08). Drill real do banco: A♥T♥ no turn
9♥7♠3♦Q♣, o vilão deu check-raise no flop e jam de 24,1bb com 36bb atrás.

    equity vs MÃO ALEATÓRIA (o que o bot usava):  43.6%
    preço que o pote pedia:                       28.1%
    -> bot carimbava "o certo era PAGAR", e o FOLD do aluno virava "ruim"

    equity vs o range que dá check-raise + jam:    ~4%
    -> o call queima ~16bb. O fold do aluno estava CERTO.

Agrava: o veredito alimenta leak_error_rates, então o sorteio de drills
passava a perseguir o aluno justamente na categoria em que ele acertou —
ensinando a pagar demais e reforçando o erro.

Quem aposta não aposta com mão qualquer. Contra agressão pós-flop, equity vs
random não é aproximação: é outro jogo.
"""
from __future__ import annotations

BASE = {
    "cards": ["Ah", "Th"], "board": ["9h", "7s", "3d", "Qc"], "street": "turn",
    "pot_bb": 24.1, "to_call_bb": 24.1, "required_eq": 0.281, "stack_bb": 36,
    "actual": "fold",
    "storyboard": [{"name": "turn", "board": ["9h", "7s", "3d", "Qc"],
                    "lines": []}],
}


def test_o_caso_real_nao_condena_mais_o_fold():
    from app.bot.processing import storyboard_spot_from_drill

    r = storyboard_spot_from_drill(BASE, "fold")
    assert r["verdict"] == "mista", "o fold correto voltou a ser carimbado"
    assert "PAGAR" not in r["correct"]
    assert "range" in r["correct"].lower()


def test_o_texto_explica_por_que_o_preco_nao_decide():
    from app.bot.processing import storyboard_spot_from_drill

    t = storyboard_spot_from_drill(BASE, "fold")["verdict_text"]
    assert "APOSTOU" in t
    assert "mão qualquer" in t
    # e mostra os dois números, para o aluno ver de onde vinha a confusão
    assert "%" in t


def test_preflop_com_range_de_verdade_segue_decidindo():
    """O conserto não pode calar o drill inteiro: no pré-flop a conta usa o
    range de abertura do agressor, que é premissa legítima."""
    from app.bot.processing import storyboard_spot_from_drill

    pre = dict(BASE, street="preflop", board=[], to_call_bb=2.5,
               required_eq=0.30,
               storyboard=[{"name": "preflop", "board": [], "lines": []}])
    r = storyboard_spot_from_drill(pre, "call")
    assert r["verdict"] in ("boa", "ruim", "mista")
    assert r["correct"], "o pré-flop tem que continuar dando gabarito"


def test_sem_aposta_para_pagar_nao_ha_o_que_travar():
    """Spot de check/aposta própria não passa pelo guarda — ele é sobre
    PAGAR contra agressão."""
    from app.bot.processing import storyboard_spot_from_drill

    sem = dict(BASE, to_call_bb=0, required_eq=None)
    r = storyboard_spot_from_drill(sem, "check")
    assert r is not None
