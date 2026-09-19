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


# ---- bb_subdefesa: equity CRUA não é o que o BB ganha ----------------------
# Auditoria de 09/08: o detector acusava fold em 148 das 169 classes de mão
# (87,6%). Ele não media subdefesa — media FOLD. Causa: comparava equity
# all-in com pot odds, o que assume realização de 100% para quem está fora de
# posição, com range limitado, contra quem tomou a iniciativa.

def _bb_fold_ou_call(cartas, acao=ActionType.FOLD):
    from app.models.canonical import (CanonicalHand, HandFormat, PlayerSeat,
                                      Stakes, Street, StreetName)
    from app.models.canonical import Action as A

    return CanonicalHand(
        site="GG", hand_id="bb1", hero="Hero", format=HandFormat.TOURNAMENT,
        source_format="txt", played_at="2026-08-01T20:00:00+00:00",
        stakes=Stakes(small_blind=50, big_blind=100, ante=0),
        players=[PlayerSeat(seat=1, name="Hero", stack=3000, position="BB",
                            is_hero=True),
                 PlayerSeat(seat=2, name="V", stack=3000, position="CO")],
        hero_cards=cartas,
        streets=[Street(name=StreetName.PREFLOP, actions=[
            A(actor="Hero", type=ActionType.POST, amount=100, post_type="bb"),
            A(actor="V", type=ActionType.RAISE, amount=240, to_amount=240),
            A(actor="Hero", type=acao, amount=140.0, to_amount=240.0)
            if acao == ActionType.CALL
            else A(actor="Hero", type=acao)])])


def _obs_bb(cartas, acao=ActionType.FOLD):
    from app.analysis.taxonomia import observar

    return [o for o in observar([_bb_fold_ou_call(cartas, acao)])
            if o.codigo == "bb_subdefesa"]


def test_o_veredito_nao_depende_do_NAIPE():
    """`3d2c` e `3h2d` são a MESMA mão (32o) e recebiam vereditos opostos,
    por 0,00015 de ruído de Monte Carlo contra um limiar.

    Agora a equity é calculada sobre a CLASSE, com seed fixa: determinístico
    por construção, não por sorte de iteração.
    """
    from app.analysis.taxonomia import _classe_da_mao

    assert _classe_da_mao(["3d", "2c"]) == _classe_da_mao(["3h", "2d"]) == "32o"
    assert _classe_da_mao(["Ah", "Kh"]) == "AKs"
    assert _classe_da_mao(["Kd", "Ah"]) == "AKo"
    assert _classe_da_mao(["7c", "7s"]) == "77"

    a = _obs_bb(["3d", "2c"])[0].escorregada
    b = _obs_bb(["3h", "2d"])[0].escorregada
    assert a == b, "a mesma mão recebeu vereditos diferentes por naipe"


def test_lixo_offsuit_pode_foldar_o_BB_em_paz():
    """O detector tem que medir SUBDEFESA, não fold. 32o, 72o e 93o não
    defendem BB contra open, em nenhum livro."""
    for cartas in (["3d", "2c"], ["7h", "2c"], ["9d", "3c"], ["8h", "4c"]):
        obs = _obs_bb(cartas)
        assert obs, f"{cartas} nem virou oportunidade"
        assert not obs[0].escorregada, (
            f"acusou fold de {cartas}, que é lixo offsuit fora de posição")


def test_mao_que_defende_de_verdade_continua_sendo_acusada():
    """O outro lado: afrouxar até não acusar nada seria 'consertar' virando
    inútil. AA, AKs e pares médios são defesa obrigatória."""
    for cartas in (["Ah", "Ad"], ["Ah", "Kh"], ["8h", "8d"], ["Ah", "5h"]):
        obs = _obs_bb(cartas)
        assert obs and obs[0].escorregada, (
            f"deixou de acusar o fold de {cartas}, que é defesa clara")


def test_a_taxa_de_acusacao_ficou_no_campo_certo():
    """A faixa é estreita de propósito, porque a margem É carregadora.

    Medido nas 169 classes: margem de 2pp acusa 49,7% · 4pp 36,1% · 6pp
    27,8% · 8pp 23,7%.

    A referência de defesa do BB contra open barato é 45-55%, então 2pp
    reproduz a referência — e é exatamente onde `_realizacao_bb` é mais
    fraca, porque mão marginal é a que mais depende de realização. Acusar
    ali seria acusar o modelo, não o aluno.

    Abaixo de 20% o detector para de servir; acima de 35% ele começa a
    cobrar defesa marginal com uma heurística que tem ±5pp de erro. Se
    alguém mexer na margem, este teste é onde a conta reaparece.
    """
    RANKS = "AKQJT98765432"

    def classe(i, j):
        a, b = RANKS[i], RANKS[j]
        if i == j:
            return [a + "h", b + "d"]
        return [a + "h", b + "h"] if i < j else [b + "h", a + "d"]

    acusadas = sum(1 for i in range(13) for j in range(13)
                   if (_o := _obs_bb(classe(i, j))) and _o[0].escorregada)
    taxa = 100 * acusadas / 169
    assert 20.0 <= taxa <= 35.0, (
        f"acusa {taxa:.1f}% das 169 classes — fora da faixa defensável para "
        f"um detector conservador de subdefesa (era 87,6%). Abaixo de 20% "
        f"ele não serve; acima de 35% cobra defesa marginal com uma "
        f"heurística de realização que tem ±5pp de erro.")


def test_o_fator_de_realizacao_respeita_a_forma_da_mao():
    """Par joga sozinho, suited tem flush draw, offsuit com gap grande só
    acerta par fraco — que é a mão mais cara de jogar fora de posição."""
    from app.analysis.taxonomia import _realizacao_bb

    par = _realizacao_bb(["8h", "8d"])
    suited = _realizacao_bb(["8h", "7h"])
    conectada = _realizacao_bb(["8h", "7d"])
    lixo = _realizacao_bb(["9h", "3d"])

    assert par > conectada and suited > conectada > lixo
    for f in (par, suited, conectada, lixo):
        assert 0.65 <= f <= 0.95


def test_a_equity_por_classe_e_memoizada():
    """8000 iterações de Monte Carlo por mão custavam 0,31s cada — num envio
    de 300 mãos com 40 spots de BB, 12 segundos recalculando a mesma coisa."""
    from app.analysis.taxonomia import _equity_bb_contra_open

    _equity_bb_contra_open.cache_clear()
    _obs_bb(["Ah", "Kh"])
    depois_de_uma = _equity_bb_contra_open.cache_info()
    _obs_bb(["Ad", "Kd"])      # mesma CLASSE, outros naipes
    agora = _equity_bb_contra_open.cache_info()
    assert agora.misses == depois_de_uma.misses, (
        "recalculou a equity para a mesma classe de mão")
    assert agora.hits > depois_de_uma.hits


def test_o_caminho_que_fala_com_o_aluno_usa_o_MESMO_criterio():
    """`detect_leaks` cortava por `taxa_mean < 25.0` — a MÉDIA, que é
    exatamente o que `agregar` existe para não usar.

    Duas escorregadas em duas chances davam média 100% e viravam leak de
    15bb/100 no /stats e no contexto do coach, enquanto `agregar` já dizia
    `acima_da_tolerancia=False`. A camada de limite inferior estava
    construída, testada — e o caminho que fala com o aluno passava por fora
    dela.

    O corte único de 25% também ignorava a tolerância PRÓPRIA de cada código:
    limp tem referência 5%, subdefesa de BB tem 35%.
    """
    from app.analysis.leaks import detect_leaks

    maos = [_mao("CO", ["7h", "2d"],
                 [_post("Vil", 50, "sb"), _post("Out", 100, "bb"),
                  Action(actor="Hero", type=ActionType.CALL, amount=100,
                         to_amount=100)], hid=f"h{i}") for i in range(2)]

    publicados = {l["leak"] for l in detect_leaks(maos)}
    por_codigo = {d["codigo"]: d for d in agregar(observar(maos), 2)}

    for codigo, d in por_codigo.items():
        if d["escorregadas"] == 0 or d["custo_bb_100"] <= 0:
            continue
        assert (codigo in publicados) == bool(d["acima_da_tolerancia"]), (
            f"{codigo}: agregar diz acima_da_tolerancia="
            f"{d['acima_da_tolerancia']} (lo={d['taxa_lo']:.0f}% vs "
            f"tolerância {d['tolerancia_pct']:.0f}%) e detect_leaks "
            f"{'publicou' if codigo in publicados else 'omitiu'}")

    # o caso concreto do achado: call_caro com limite inferior de 8% contra
    # tolerância de 25% não pode aparecer como leak
    assert "call_caro" not in publicados


def test_foldar_diante_de_um_preco_ENTRA_no_denominador_do_call_caro():
    """Sem o fold, a taxa vira P(erro | pagou) — que é ~100% por construção,
    porque só quem pagou pode ter pago caro.

    É o mesmo defeito que o `bb_subdefesa` tinha, num código marcado como
    custo "exato": o denominador só continha a ação errada.
    """
    from app.analysis.taxonomia import observar

    bb = 100.0
    foldou = _mao("BB", ["7h", "2d"], [
        _post("Out", 50, "sb"), _post("Hero", 100, "bb"),
        Action(actor="Vil", type=ActionType.RAISE, amount=300, to_amount=300),
        Action(actor="Hero", type=ActionType.FOLD)], hid="fold1")

    obs = [o for o in observar([foldou]) if o.codigo == "call_caro"]
    assert obs, "foldar diante de um preço não virou oportunidade de call caro"
    assert all(not o.escorregada for o in obs), (
        "foldar foi contado como PAGAR caro")
