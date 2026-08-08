"""Contar em vez de opinar — a taxonomia fechada de erro.

`hand_analysis.mistakes` guardava a DECISÃO, sem código e sem denominador:

    {"street": "preflop", "to_call": 1.0, "decision": "call", ...}

Dá para mostrar uma mão. Não dá para dizer "você foldou 9 de 14 vezes nesse
spot e custou 2,1bb/100" — que é a frase que separa diagnóstico de
impressão, e o insumo do plano de estudo, do relatório de torneio e da
medição de evolução.

O que cada código precisa ter, e o item 2 é o que quase sempre falta:
  1. código fechado          (texto livre não se agrupa)
  2. OPORTUNIDADE computável (4 em 4 e 4 em 400 são jogadores diferentes)
  3. ESCORREGADA computável
  4. custo em bb, dizendo quando é ESTIMADO
"""
from __future__ import annotations

import pytest

from app.analysis.taxonomia import (CODIGOS, Observacao, agregar, observar)
from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  HandFormat, PlayerSeat, Stakes, Street,
                                  StreetName)


def _mao(hero_pos, hero_cards, acoes_pre, stack=40.0, hid="h1"):
    bb = 100.0
    jog = [PlayerSeat(seat=1, name="Hero", stack=stack * bb,
                      position=hero_pos, is_hero=True),
           PlayerSeat(seat=2, name="Vil", stack=40 * bb, position="CO"),
           PlayerSeat(seat=3, name="Out", stack=40 * bb, position="BTN")]
    return CanonicalHand(
        site="T", hand_id=hid, hero="Hero", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=bb / 2, big_blind=bb),
        players=jog, hero_cards=hero_cards,
        streets=[Street(name=StreetName.PREFLOP, actions=acoes_pre)])


def _post(quem, v, tipo="bb"):
    return Action(actor=quem, type=ActionType.POST, amount=v, post_type=tipo)


# ---- o contrato de cada código --------------------------------------------

def test_todo_codigo_tem_as_quatro_coisas():
    for c in CODIGOS.values():
        assert c.codigo and c.nome
        assert c.pergunta.endswith("?"), \
            f"{c.codigo}: problema é PERGUNTA acionável, não rótulo"
        assert 0 < c.tolerancia_pct <= 60
        assert c.custo in ("exato", "estimado")


def test_a_pergunta_e_o_que_permite_ensinar():
    """'você tem leak de defesa de BB' é rótulo. 'No BB, com o pote te dando
    preço, quais mãos pagam o open?' é a pergunta que vira estudo."""
    assert "quais mãos pagam" in CODIGOS["bb_subdefesa"].pergunta


# ---- limp: o detector mais barato em amostra ------------------------------

def test_limp_de_abertura_e_pego():
    """Fora do SB o equilíbrio abre ou larga, nunca limpa — a referência é
    ZERO, e é isso que torna 4 limps em 150 mãos já diagnóstico."""
    h = _mao("CO", ["7h", "2d"], [
        _post("Vil", 50, "sb"), _post("Out", 100, "bb"),
        Action(actor="Hero", type=ActionType.CALL, amount=100, to_amount=100)])
    obs = [o for o in observar([h]) if o.codigo == "limp_de_abertura"]
    assert len(obs) == 1 and obs[0].escorregada is True


def test_abrir_com_raise_nao_e_limp():
    h = _mao("CO", ["Ah", "Kd"], [
        _post("Vil", 50, "sb"), _post("Out", 100, "bb"),
        Action(actor="Hero", type=ActionType.RAISE, amount=250, to_amount=250)])
    obs = [o for o in observar([h]) if o.codigo == "limp_de_abertura"]
    assert len(obs) == 1 and obs[0].escorregada is False, \
        "o spot aconteceu (denominador) e ele acertou"


def test_completar_o_sb_nao_e_limp_de_abertura():
    """No SB completar é jogada legítima — o detector não pode acusar."""
    h = _mao("SB", ["7h", "2d"], [
        _post("Hero", 50, "sb"), _post("Out", 100, "bb"),
        Action(actor="Hero", type=ActionType.CALL, amount=50, to_amount=100)])
    assert not [o for o in observar([h]) if o.codigo == "limp_de_abertura"]


def test_pote_ja_aberto_nao_e_oportunidade_de_abrir():
    h = _mao("BTN", ["7h", "2d"], [
        _post("Vil", 50, "sb"), _post("Out", 100, "bb"),
        Action(actor="Vil", type=ActionType.RAISE, amount=250, to_amount=250),
        Action(actor="Hero", type=ActionType.CALL, amount=250, to_amount=250)])
    assert not [o for o in observar([h]) if o.codigo == "limp_de_abertura"]


# ---- defesa de BB ---------------------------------------------------------

def _bb_vs_open(cards, acao_do_heroi, open_para=240):
    resposta = (Action(actor="Hero", type=ActionType.FOLD)
                if acao_do_heroi == ActionType.FOLD else
                Action(actor="Hero", type=acao_do_heroi,
                       amount=open_para - 100, to_amount=open_para))
    return _mao("BB", cards, [
        _post("Out", 50, "sb"), _post("Hero", 100, "bb"),
        Action(actor="Vil", type=ActionType.RAISE, amount=open_para,
               to_amount=open_para),
        resposta])


def test_foldar_mao_com_preco_de_sobra_e_escorregada():
    """K♦J♦ no BB contra open de 2.4bb: o pote pede ~29% e a mão tem bem
    mais que isso contra o range de abertura."""
    obs = [o for o in observar([_bb_vs_open(["Kd", "Jd"], ActionType.FOLD)])
           if o.codigo == "bb_subdefesa"]
    assert len(obs) == 1 and obs[0].escorregada is True
    assert obs[0].custo_bb > 0


def test_pagar_conta_como_acerto_e_entra_no_denominador():
    obs = [o for o in observar([_bb_vs_open(["Kd", "Jd"], ActionType.CALL)])
           if o.codigo == "bb_subdefesa"]
    assert len(obs) == 1 and obs[0].escorregada is False


def test_mao_sem_equity_pode_foldar_em_paz():
    """3♦2♣ larga e ISSO NÃO É ERRO. Um detector que acusasse todo fold
    ensinaria o aluno a pagar tudo — criaria um leak pior."""
    obs = [o for o in observar([_bb_vs_open(["3d", "2c"], ActionType.FOLD)])
           if o.codigo == "bb_subdefesa"]
    assert len(obs) == 1 and obs[0].escorregada is False


def test_open_gigante_nao_e_o_spot():
    """Contra open de 6bb o preço muda e largar vira normal — acusar aqui
    seria medir outra coisa com o mesmo nome."""
    assert not [o for o in observar(
        [_bb_vs_open(["Kd", "Jd"], ActionType.FOLD, open_para=600)])
        if o.codigo == "bb_subdefesa"]


# ---- a agregação decide pelo limite BAIXO ---------------------------------

def _obs(codigo, erros, total, custo=1.0):
    return [Observacao(codigo, i < erros, custo if i < erros else 0.0,
                       f"h{i}") for i in range(total)]


def test_duas_escorregadas_em_tres_nao_viram_leak_cronico():
    """Decidir pela MÉDIA é o que transforma acidente em diagnóstico. O
    limite inferior é o número que sobrevive a 'tem certeza?'."""
    d = agregar(_obs("bb_subdefesa", 2, 3), 3)[0]
    assert d["taxa_mean"] > d["tolerancia_pct"], "a média até passaria"
    assert d["acima_da_tolerancia"] is False, "mas o limite inferior não"


def test_padrao_repetido_com_amostra_vira_problema():
    d = agregar(_obs("bb_subdefesa", 28, 40), 40)[0]
    assert d["acima_da_tolerancia"] is True
    assert d["taxa_lo"] > 35.0


def test_o_denominador_entra_na_conta():
    """4 erros em 4 e 4 em 400 são jogadores diferentes — e antes da
    taxonomia os dois davam 'quatro erros'."""
    poucos = agregar(_obs("limp_de_abertura", 4, 4), 4)[0]
    muitos = agregar(_obs("limp_de_abertura", 4, 400), 400)[0]
    assert poucos["taxa_lo"] > muitos["taxa_lo"]
    assert muitos["acima_da_tolerancia"] is False


def test_custo_estimado_e_declarado():
    """Custo de open perdido é estimativa; o de call caro é conta exata. O
    aluno tem direito de saber qual está lendo."""
    est = agregar(_obs("open_perdido", 5, 10), 10)[0]
    exato = agregar(_obs("call_caro", 5, 10), 10)[0]
    assert est["custo_e_estimado"] is True
    assert exato["custo_e_estimado"] is False


# ---- uma fonte só ---------------------------------------------------------

def test_detect_leaks_nao_tem_mais_detector_proprio():
    """Duas listas de detectores divergem em uma semana. `leaks.py` virou
    casca sobre a taxonomia."""
    import inspect

    from app.analysis import leaks

    fonte = inspect.getsource(leaks.detect_leaks)
    assert "from app.analysis.taxonomia import" in fonte
    assert "push_fold(" not in fonte, "voltou a detectar por conta própria"


def test_o_formato_antigo_continua_valendo():
    """`leaks_text` e o contexto do coach não podem ter quebrado."""
    from app.analysis.leaks import detect_leaks, leaks_text

    maos = [_mao("CO", ["7h", "2d"], [
        _post("Vil", 50, "sb"), _post("Out", 100, "bb"),
        Action(actor="Hero", type=ActionType.CALL, amount=100, to_amount=100)],
        hid=f"h{i}") for i in range(12)]
    saida = detect_leaks(maos)
    assert saida, "12 limps em 12 chances tinham que acusar"
    for chave in ("leak", "nome", "oportunidades", "escorregadas",
                  "taxa_pct", "confianca", "custo_bb_100maos", "exemplos"):
        assert chave in saida[0], f"o formato perdeu `{chave}`"
    assert leaks_text(saida)


def test_uma_mao_quebrada_nao_derruba_a_varredura():
    """Silêncio de uma mão aparece no `n`, não num erro."""
    class _Ruim:
        hero = "Hero"

    boa = _mao("CO", ["Ah", "Kd"], [
        _post("Vil", 50, "sb"), _post("Out", 100, "bb"),
        Action(actor="Hero", type=ActionType.RAISE, amount=250, to_amount=250)])
    assert observar([_Ruim(), boa, _Ruim()])
