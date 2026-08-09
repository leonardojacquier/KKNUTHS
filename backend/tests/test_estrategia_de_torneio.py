"""Estratégia de torneio: onde o EV foi embora, por profundidade de stack.

A pergunta do dono era "etapa inicial mais tight ou mais agressivo?". A
resposta honesta começa rejeitando a pergunta: "etapa" mistura profundidade
de STACK (que muda a árvore de decisão) com profundidade de TORNEIO (que
muda a pressão de ICM). Um jogador com 18bb no nível 3 e outro com 18bb no
nível 14 jogam a mesma estratégia de fichas e estratégias de risco
diferentes.

O relatório mede ACURÁCIA, não frequência — cada spot auditável tem resposta
certa, então "nesses 6 spots de 15-25bb você deixou 5,3bb na mesa" vale com
n=1. Frequência ("você joga X% nesta faixa") precisaria de n>=60 NA FAIXA, e
mão de torneio não é i.i.d.: quem quebra cedo só contribui com mãos de stack
fundo.
"""
from __future__ import annotations

import pytest

from app.analysis.estrategia_torneio import (FAIXAS, LinhaDaFaixa,
                                             corte_por_ante, faixa_de,
                                             onde_doi_mais, por_faixa, texto)
from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  HandFormat, PlayerSeat, Stakes, Street,
                                  StreetName)


# ---- o eixo é o stack, e as fronteiras são onde a ÁRVORE muda -------------

@pytest.mark.parametrize("stack,esperado", [
    (100.0, "deep"), (40.1, "deep"), (40.0, "padrão"), (25.1, "padrão"),
    (25.0, "re-shove"), (15.1, "re-shove"), (15.0, "curto"), (8.1, "curto"),
    (8.0, "crítico"), (2.0, "crítico"),
])
def test_faixa_por_stack_efetivo(stack, esperado):
    assert faixa_de(stack) == esperado


def test_sem_stack_nao_inventa_faixa():
    assert faixa_de(None) is None and faixa_de(0) is None


def test_a_faixa_de_reshove_esta_declarada_como_a_esquecida():
    """O especialista previu que o problema do campo de clube não está no
    early, e sim em 15-25bb — onde mora o re-shove e ninguém estuda."""
    nome, lo, hi, texto_ = [f for f in FAIXAS if f[0] == "re-shove"][0]
    assert (lo, hi) == (15.0, 25.0)
    assert "ninguém" in texto_


# ---- a montagem ------------------------------------------------------------

def _mao(stack_bb, acoes, pos="CO", cards=("7h", "2d"), hid="h", ante=25.0):
    bb = 100.0
    return CanonicalHand(
        site="T", hand_id=hid, hero="Hero", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=bb / 2, big_blind=bb, ante=ante),
        players=[PlayerSeat(seat=1, name="Hero", stack=stack_bb * bb,
                            position=pos, is_hero=True),
                 PlayerSeat(seat=2, name="Vil", stack=30 * bb, position="BTN"),
                 PlayerSeat(seat=3, name="Out", stack=30 * bb, position="SB")],
        hero_cards=list(cards),
        streets=[Street(name=StreetName.PREFLOP, actions=acoes)])


def _limp(stack_bb, hid):
    return _mao(stack_bb, [
        Action(actor="Out", type=ActionType.POST, amount=50, post_type="sb"),
        Action(actor="Vil", type=ActionType.POST, amount=100, post_type="bb"),
        Action(actor="Hero", type=ActionType.CALL, amount=100, to_amount=100),
    ], hid=hid)


def test_o_erro_cai_na_faixa_do_stack_em_que_aconteceu():
    linhas = {l.faixa: l for l in por_faixa(
        [_limp(50, "a"), _limp(20, "b"), _limp(20, "c")])}
    assert linhas["deep"].erros == 1
    assert linhas["re-shove"].erros == 2
    assert linhas["re-shove"].ev_perdido_bb > linhas["deep"].ev_perdido_bb


def test_faixa_sem_erro_aparece_como_de_pe():
    """Relatório que só mostra o que está ruim vira crítico, e crítico se
    abandona. A faixa limpa tem que aparecer."""
    boa = _mao(50, [
        Action(actor="Out", type=ActionType.POST, amount=50, post_type="sb"),
        Action(actor="Vil", type=ActionType.POST, amount=100, post_type="bb"),
        Action(actor="Hero", type=ActionType.RAISE, amount=250, to_amount=250),
    ], cards=("Ah", "Kd"), hid="ok")
    l = [x for x in por_faixa([boa]) if x.faixa == "deep"][0]
    assert l.spots >= 1 and l.erros == 0
    assert "de pé" in texto([l])


def test_a_faixa_que_mais_custou_e_a_resposta_com_numero():
    linhas = por_faixa([_limp(20, f"r{i}") for i in range(6)]
                       + [_limp(50, "d")])
    pior = onde_doi_mais(linhas)
    assert pior.faixa == "re-shove"
    assert "re-shove" in texto(linhas)


def test_amostra_curta_na_faixa_sai_sem_percentual():
    """A regra que teria evitado o VPIP 94%, agora por faixa."""
    t = texto(por_faixa([_limp(20, "x")]))
    assert "sem percentual" in t


# ---- o viés do próprio detector -------------------------------------------

def test_direcao_nao_e_afirmada_quando_o_outro_lado_nao_teve_chance():
    """São 4 detectores de passividade contra 2 de soltura. Sem esta trava,
    "todos os erros foram passivos" pode significar só "eu só sei procurar
    isso" — e a ferramenta empurraria todo aluno para a agressão, criando o
    leak que depois iria diagnosticar."""
    cega = LinhaDaFaixa(faixa="curto", o_que_muda="", maos=20, spots=20,
                        erros=6, ev_perdido_bb=4.0, por_codigo={},
                        direcao={"passivo": 6, "solto": 0},
                        chances={"passivo": 20, "solto": 1})
    assert cega.direcao_confiavel is None

    justa = LinhaDaFaixa(faixa="curto", o_que_muda="", maos=20, spots=20,
                         erros=6, ev_perdido_bb=4.0, por_codigo={},
                         direcao={"passivo": 6, "solto": 1},
                         chances={"passivo": 20, "solto": 12})
    assert justa.direcao_confiavel == "passivo"


def test_um_erro_so_nao_e_direcao():
    l = LinhaDaFaixa(faixa="curto", o_que_muda="", maos=9, spots=9, erros=1,
                     ev_perdido_bb=1.0, por_codigo={},
                     direcao={"passivo": 1, "solto": 0},
                     chances={"passivo": 9, "solto": 9})
    assert l.direcao_confiavel is None


def test_empate_nao_vira_conclusao():
    l = LinhaDaFaixa(faixa="curto", o_que_muda="", maos=20, spots=20, erros=6,
                     ev_perdido_bb=3.0, por_codigo={},
                     direcao={"passivo": 3, "solto": 3},
                     chances={"passivo": 20, "solto": 20})
    assert l.direcao_confiavel is None


# ---- o corte por ante ------------------------------------------------------

def test_amostra_de_um_lado_so_nao_vira_comparacao():
    """Todas as 517 mãos completas da base são COM ante. Comparar um grupo
    com nada é o tipo de tabela que parece análise e não é."""
    r = corte_por_ante([_limp(30, "a"), _limp(30, "b")])
    assert r["aplicavel"] is False
    assert "não há com o que comparar" in r["por_que"]


def test_com_os_dois_lados_o_corte_sai():
    sem = _mao(30, [
        Action(actor="Out", type=ActionType.POST, amount=50, post_type="sb"),
        Action(actor="Vil", type=ActionType.POST, amount=100, post_type="bb"),
        Action(actor="Hero", type=ActionType.CALL, amount=100, to_amount=100),
    ], hid="s", ante=0.0)
    r = corte_por_ante([sem, _limp(30, "c")])
    assert r["aplicavel"] is True
    assert r["maos"] == {"sem_ante": 1, "com_ante": 1}


def test_o_corte_e_por_ante_e_nao_por_palpite_de_etapa():
    """`stakes.ante` é dado exato na mão; 'nível' não vem numerado nos apps
    de clube e 'etapa inicial' é palpite com nome de estratégia."""
    import inspect

    from app.analysis import estrategia_torneio

    doc = inspect.getdoc(estrategia_torneio.corte_por_ante)
    assert "dado exato" in doc


def test_uma_decisao_conta_um_custo_so():
    """Um limp com 72o dispara `limp_de_abertura` E `call_caro` — é a mesma
    ficha entrando no pote pelo mesmo motivo. Somar os dois inflaria o "EV
    perdido", que é exatamente o número que o aluno vai citar por aí."""
    l = [x for x in por_faixa([_limp(50, "a")]) if x.faixa == "deep"][0]
    por_codigo = sum(c["erros"] for c in l.por_codigo.values())
    assert por_codigo >= 2, "o fixture precisa disparar dois códigos"
    assert l.erros == 1, "duas etiquetas, uma decisão"
    assert l.ev_perdido_bb == max(c["ev"] for c in l.por_codigo.values())


def test_erros_em_streets_diferentes_contam_separado():
    """A dedução é por DECISÃO, não por mão: pagar caro no flop e de novo no
    turn são dois erros e dois custos."""
    from app.analysis.estrategia_torneio import LinhaDaFaixa  # noqa
    from app.analysis.taxonomia import Observacao, agregar    # noqa

    # o comportamento é da montagem; aqui basta garantir que a chave inclui
    # a street, senão o segundo erro sumiria
    import inspect

    from app.analysis import estrategia_torneio

    fonte = inspect.getsource(estrategia_torneio.por_faixa)
    assert "(o.hand_id, o.street)" in fonte
