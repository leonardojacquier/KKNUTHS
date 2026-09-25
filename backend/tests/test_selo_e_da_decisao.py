"""O selo julga a DECISÃO com o que se sabia na hora — não o resultado.

Medido em 25/09: 7 análises desde 06/09 abrem com "✅ Você jogou bem" e
marcam ❌ no river, justificando com a carta que caiu ou com a mão que o
vilão mostrou depois. Exemplos reais:

  "❌ *River* Q♠ — pagou 7.3bb num pote de 14.6bb: pedia 33.3%, mas a Q♠
   completou o straight do BB e sua equity caiu pra 0% → −7.3bb."
  "❌ *River* — o A♥ pareia a mesa… derruba sua equity a zero. Sem decisão
   sua também (stack já estava no meio)."

Duas falhas somadas:
  · a conta: ev_por_street calculava a equity contra as cartas REVELADAS no
    showdown — no river isso é 0% ou 100%, informação que o aluno não tinha
    na hora do call;
  · o selo: nada impedia ❌ numa street sem decisão, nem ❌ justificado pelo
    resultado quando a conta da decisão dizia que o call era certo.

Pelo manual, ❌ é "erro claro". O produto que vende decisão-não-resultado
estava ensinando resulting.
"""
from __future__ import annotations

from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  PlayerSeat, Stakes, Street, StreetName)


def _mao_trinca_perde_no_river(mostrou: bool = True):
    """Herói com trinca de A paga aposta pequena no river; o vilão mostra o
    straight que a Q do river completou. Formato do caso real de 21/09."""
    pre = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="BB", type=ActionType.POST, amount=1, post_type="bb"),
        Action(actor="Hero", type=ActionType.RAISE, amount=2, to_amount=2),
        Action(actor="BB", type=ActionType.CALL, amount=1)])
    flop = Street(name=StreetName.FLOP, board=["3h", "Ac", "Ad"], actions=[
        Action(actor="BB", type=ActionType.CHECK),
        Action(actor="Hero", type=ActionType.CHECK)])
    turn = Street(name=StreetName.TURN, board=["3h", "Ac", "Ad", "Ks"], actions=[
        Action(actor="BB", type=ActionType.BET, amount=1),
        Action(actor="Hero", type=ActionType.CALL, amount=1)])
    river = Street(name=StreetName.RIVER, board=["3h", "Ac", "Ad", "Ks", "Qs"],
                   actions=[
        Action(actor="BB", type=ActionType.BET, amount=3),
        Action(actor="Hero", type=ActionType.CALL, amount=3)])
    return CanonicalHand(
        site="x", hand_id="trinca-river", hero="Hero",
        stakes=Stakes(small_blind=0.5, big_blind=1),
        players=[PlayerSeat(seat=1, name="Hero", stack=100, is_hero=True,
                            position="UTG"),
                 PlayerSeat(seat=2, name="BB", stack=100, position="BB")],
        hero_cards=["Ah", "9h"],
        shown_cards={"BB": ["Jc", "Tc"]} if mostrou else {},
        streets=[pre, flop, turn, river],
        final_board=["3h", "Ac", "Ad", "Ks", "Qs"], total_pot=14)


def _river(r):
    return next(d for d in r["decisoes"]
                if d["street"] == "river" and d["acao"] == "call")


# ---- 1) a conta da decisão não olha as cartas do showdown -------------------

def test_equity_da_decisao_nao_e_zero_so_porque_ele_mostrou_a_mao_que_ganha():
    from app.analysis.ev_streets import ev_por_street

    d = _river(ev_por_street(_mao_trinca_perde_no_river()))
    assert d["equity_pct"] > 30, (
        f"equity da decisão {d['equity_pct']}% — está usando as cartas "
        "reveladas, informação que o aluno não tinha na hora do call")


def test_mostrar_ou_nao_mostrar_nao_muda_o_julgamento_da_decisao():
    """A mesma decisão, com e sem showdown, tem que ter a mesma nota."""
    from app.analysis.ev_streets import ev_por_street

    com = _river(ev_por_street(_mao_trinca_perde_no_river(True), iters=4000))
    sem = _river(ev_por_street(_mao_trinca_perde_no_river(False), iters=4000))
    assert abs(com["equity_pct"] - sem["equity_pct"]) < 4, (com, sem)
    assert (com["custo_do_erro_bb"] > 0) == (sem["custo_do_erro_bb"] > 0)


def test_o_resultado_continua_disponivel_mas_com_nome_de_resultado():
    """Pra contar o que aconteceu ('a Q completou o straight dele'), a conta
    contra a mão revelada existe — com um nome que não deixa confundir."""
    from app.analysis.ev_streets import ev_por_street

    d = _river(ev_por_street(_mao_trinca_perde_no_river()))
    assert d["equity_vs_mao_revelada_pct"] == 0.0
    r = ev_por_street(_mao_trinca_perde_no_river())
    assert any("resultado" in p.lower() and "decis" in p.lower()
               for p in r["premissas"])


def test_o_range_encolhe_com_a_acao_do_vilao():
    """Sem isto, um shove no river seria comparado com o range pré-flop
    inteiro e todo call pareceria certo — o erro no sentido oposto."""
    from app.analysis.ev_streets import ev_por_street

    passivo = _mao_trinca_perde_no_river(False)
    agressivo = _mao_trinca_perde_no_river(False)
    agressivo.streets[3].actions[0] = Action(
        actor="BB", type=ActionType.BET, amount=12)          # 85% do pote
    eq_p = _river(ev_por_street(passivo, iters=4000))["equity_pct"]
    eq_a = _river(ev_por_street(agressivo, iters=4000))["equity_pct"]
    assert eq_a < eq_p, (f"aposta grande no river não estreitou o range "
                         f"({eq_a}% vs {eq_p}%)")


# ---- 2) o guarda do selo -----------------------------------------------------

_ANALISE = (
    "✅ Você jogou bem — river foi azar puro, não erro\n\n"
    "✅ *Pré* — raise de 2bb com A♥9♥ no UTG: abertura padrão.\n"
    "✅ *Flop* 3♥A♣A♦ — check com trinca escondida.\n"
    "✅ *Turn* K♠ — pagou 1bb num pote de 6.3bb: pedia 13.7%, tinha 91%.\n"
    "❌ *River* Q♠ — pagou 3bb num pote de 8bb: pedia 27.3%, mas a Q♠ "
    "completou o straight do BB e sua equity caiu pra 0% → −3bb.\n\n"
    "O river foi azar.")


def test_x_pelo_resultado_num_call_certo_vira_selo_da_decisao():
    from app.bot.guarda_selo import conferir_selo

    texto, achados = conferir_selo(_ANALISE, _mao_trinca_perde_no_river())
    linha = next(l for l in texto.splitlines() if "*River*" in l)
    assert linha.startswith("✅"), linha
    assert "caiu pra 0%" not in linha, "a justificativa pelo resultado ficou"
    assert "range" in linha.lower()
    assert achados and achados[0]["street"] == "river"


def test_street_sem_decisao_do_heroi_nao_leva_selo():
    """'❌ *River* — o A♥ pareia a mesa… Sem decisão sua também.'"""
    from app.bot.guarda_selo import conferir_selo

    h = _mao_trinca_perde_no_river()
    h.streets[3].actions = [Action(actor="BB", type=ActionType.CHECK),
                            Action(actor="Hero", type=ActionType.CHECK)]
    h.streets[3].actions = []          # all-in antes: ninguém age no river
    texto = ("✅ Você jogou bem\n\n✅ *Turn* K♠ — pagou.\n"
             "❌ *River* Q♠ — a carta derruba sua equity a zero. Sem decisão sua.")
    novo, achados = conferir_selo(texto, h)
    linha = next(l for l in novo.splitlines() if "*River*" in l)
    assert not linha.startswith(("❌", "🟡", "✅")), linha
    assert linha.startswith("🃏"), "a carta que caiu é evento, não veredito"


def test_x_de_decisao_errada_de_verdade_fica():
    """Call sem preço é erro — o guarda não pode virar anistia."""
    from app.bot.guarda_selo import conferir_selo

    h = _mao_trinca_perde_no_river(False)
    h.hero_cards = ["7c", "2d"]                       # nada no board
    h.streets[3].actions[0] = Action(actor="BB", type=ActionType.BET,
                                     amount=12)
    h.streets[3].actions[1] = Action(actor="Hero", type=ActionType.CALL,
                                     amount=12)
    texto = ("❌ Jogada cara — pagou o river sem mão\n\n"
             "❌ *River* Q♠ — pagou 12bb com 7 high, e ele mostrou a mão que "
             "ganhava: equity 0%.")
    novo, achados = conferir_selo(texto, h)
    assert novo == texto and not achados


def test_x_justificado_por_leitura_e_nao_por_resultado_fica():
    """Só o ❌ que cita o RESULTADO é suspeito; o modelo pode ter razão
    técnica que a conta aproximada não vê."""
    from app.bot.guarda_selo import conferir_selo

    texto = ("✅ Você jogou bem\n\n❌ *River* Q♠ — pagou 3bb: essa linha de "
             "aposta pequena no river é valor quase sempre nesse field.")
    novo, achados = conferir_selo(texto, _mao_trinca_perde_no_river())
    assert novo == texto and not achados


def test_texto_sem_placar_passa_intacto():
    from app.bot.guarda_selo import conferir_selo

    t = "Isso não é padrão de baralho te perseguindo."
    assert conferir_selo(t, _mao_trinca_perde_no_river()) == (t, [])


# ---- 3) ligado e ensinado ---------------------------------------------------

def test_a_analise_e_a_conversa_conferem_o_selo():
    import inspect

    from app.bot import processing

    assert "conferir_selo" in inspect.getsource(processing._process_upload_inner)
    assert "conferir_selo" in inspect.getsource(
        processing._conferir_fatos_da_conversa)


def test_o_prompt_diz_que_o_selo_e_da_decisao():
    from app.agent import llm

    fonte = llm.SYSTEM_PROMPT_PT if hasattr(llm, "SYSTEM_PROMPT_PT") else \
        __import__("inspect").getsource(llm)
    baixo = fonte.lower()
    assert "resultado não muda selo" in baixo or \
        "selo julga a decisão" in baixo
