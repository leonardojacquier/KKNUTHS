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

    # 6/20 = 30% contra 1/12 = 8,3% PARECE claro e não é: z = 1,44, abaixo
    # do limiar. Este caso era afirmado pela versão que comparava contagens
    # (6 > 1) e não sobrevive a um teste de duas proporções. Manter a
    # asserção antiga seria pedir de volta o defeito.
    quase = LinhaDaFaixa(faixa="curto", o_que_muda="", maos=20, spots=20,
                         erros=6, ev_perdido_bb=4.0, por_codigo={},
                         direcao={"passivo": 6, "solto": 1},
                         chances={"passivo": 20, "solto": 12})
    assert quase.direcao_confiavel is None, (
        "6 contra 1 com 20 e 12 chances não separa — afirmar aqui é chute")

    # com separação de verdade, o conselho sai
    justa = LinhaDaFaixa(faixa="curto", o_que_muda="", maos=40, spots=80,
                         erros=22, ev_perdido_bb=4.0, por_codigo={},
                         direcao={"passivo": 20, "solto": 2},
                         chances={"passivo": 40, "solto": 40})
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


# ---- chegou na tela? -------------------------------------------------------

def test_o_relatorio_html_traz_a_secao_de_faixas():
    """Módulo que ninguém liga não existe. A tabela vem ANTES das auditorias
    de all-in e pós-flop: aquelas listam spots e o aluno se perde na lista
    sem saber por onde começar; esta responde 'por onde começar'."""
    from app.analysis.handreport import build_report_html

    html = build_report_html([_limp(20, "a"), _limp(20, "b"), _limp(50, "c")])
    assert "Onde o EV foi embora" in html
    assert html.index("Onde o EV foi embora") < html.index("Mãos jogadas")

    # e a ordem em relação às auditorias fica travada na montagem
    import inspect

    from app.analysis import handreport

    fonte = inspect.getsource(handreport.build_report_html)
    assert fonte.index("_tabela_faixas") < fonte.index("_tabela_auditoria")


def test_o_html_avisa_o_que_a_tabela_nao_afirma():
    from app.analysis.handreport import build_report_html

    html = build_report_html([_limp(20, "a"), _limp(20, "b")])
    assert "não sai daqui é frequência" in html.lower() \
        or "NÃO sai daqui é frequência" in html


def test_a_secao_nao_derruba_o_relatorio_se_falhar():
    """Relatório inteiro não pode morrer por causa de uma seção nova."""
    import app.analysis.estrategia_torneio as et
    from app.analysis.handreport import build_report_html

    original = et.por_faixa
    et.por_faixa = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        html = build_report_html([_limp(20, "a")])
        assert "Mãos jogadas" in html, "a seção quebrada levou o resto junto"
        assert "Onde o EV foi embora" not in html
    finally:
        et.por_faixa = original


def test_o_torneio_manda_a_leitura_junto_do_quadro():
    """A curva mostra O QUE aconteceu; a leitura por faixa mostra ONDE o EV
    foi embora. Sem ela o aluno via a linha cair e não sabia o motivo."""
    import inspect

    from app.bot import handlers

    # o envio saiu para `_enviar_torneio`, compartilhado entre o comando e o
    # botão da lista — a leitura tem que estar LÁ, e o comando tem que passar
    # por lá
    assert "_enviar_torneio" in inspect.getsource(handlers.cmd_torneio)
    fonte = inspect.getsource(handlers._enviar_torneio)
    assert "estrategia_do_torneio" in fonte
    assert fonte.index("reply_photo") < fonte.index("estrategia_do_torneio"), \
        "a leitura vem depois do quadro, não antes"


def test_o_quadro_e_a_leitura_olham_as_mesmas_maos():
    """Se cada um buscasse por conta própria, os dois se contradiriam no dia
    em que o aluno mandasse dois torneios no mesmo minuto."""
    import inspect

    from app.bot import processing

    # com o /torneio N, a fonte comum virou `maos_do_torneio(tg, escolha)` —
    # e os DOIS têm que passar a MESMA escolha para a mesma fonte
    for fn in (processing.tournament_board_report,
               processing.estrategia_do_torneio):
        fonte = inspect.getsource(fn)
        assert "maos_do_torneio(telegram_id, escolha)" in fonte, fn.__name__


# ---- direção do erro: comparar CONTAGENS é decidir pelo denominador -------

def _linha_de_direcao(erros_passivo, n_passivo, erros_solto, n_solto):
    from app.analysis.estrategia_torneio import LinhaDaFaixa

    return LinhaDaFaixa(
        faixa="re-shove", o_que_muda="x", maos=0,
        spots=n_passivo + n_solto, erros=erros_passivo + erros_solto,
        ev_perdido_bb=0.0, por_codigo={},
        direcao={"passivo": erros_passivo, "solto": erros_solto},
        chances={"passivo": n_passivo, "solto": n_solto})


def test_o_lado_com_mais_CHANCES_nao_ganha_por_isso():
    """O defeito medido em 09/08: com os DOIS lados na MESMA taxa real de
    erro, 40 chances contra 5, o veredito saía 'passivo demais' em 99,5% das
    simulações. Quem tem mais oportunidades acumula mais ERROS mesmo jogando
    igual — e o portão de 5 chances não corrigia isso, só liberava a
    comparação já viciada.
    """
    # 12/40 = 30% e 2/5 = 40%: o passivo tem MAIS erros e MENOS taxa
    linha = _linha_de_direcao(12, 40, 2, 5)
    assert linha.direcao_confiavel is None, (
        "afirmou direção com base na contagem bruta")

    # mesma taxa dos dois lados, denominadores muito diferentes
    assert _linha_de_direcao(12, 40, 2, 5).direcao_confiavel is None
    assert _linha_de_direcao(20, 60, 2, 6).direcao_confiavel is None


def test_diferenca_grande_e_com_amostra_AINDA_e_afirmada():
    """Consertar virando mudo seria trocar um defeito por outro. Quando a
    diferença é real e a amostra dá, o conselho sai."""
    linha = _linha_de_direcao(20, 40, 2, 40)     # 50% vs 5%
    assert linha.direcao_confiavel == "passivo"


def test_a_taxa_de_falsa_direcao_fica_no_nominal():
    """Simulação sob H0: os dois lados com a MESMA taxa real. Um teste a 5%
    pode errar 5% das vezes — não 99,5%.

    Inclui o caso de denominadores IGUAIS de propósito: ali o lado é escolhido
    olhando o dado (`max`), então testar num rabo só dava 10,4%, o dobro do
    nominal. É o mesmo viés de 'procurar o extremo' que a correção de
    comparações múltiplas trata em problemas.py.
    """
    import random

    rnd = random.Random(7)
    for p, na, nb in ((0.30, 40, 5), (0.30, 40, 40), (0.20, 100, 100)):
        afirmou = 0
        for _ in range(3000):
            ea = sum(rnd.random() < p for _ in range(na))
            eb = sum(rnd.random() < p for _ in range(nb))
            if _linha_de_direcao(ea, na, eb, nb).direcao_confiavel:
                afirmou += 1
        taxa = 100 * afirmou / 3000
        assert taxa < 8.0, (
            f"p={p} n={na}vs{nb}: afirmou direção em {taxa:.1f}% dos casos "
            f"em que NÃO há diferença nenhuma")


def test_o_poder_e_declarado_e_nao_prometido():
    """Com amostra de clube o veredito honesto é quase sempre 'não sei de que
    lado'. Este teste fixa isso para ninguém achar que a ferramenta calou por
    bug: separar 35% de 20% exige ~200 spots POR LADO."""
    import random

    rnd = random.Random(11)
    achou = 0
    for _ in range(2000):
        ea = sum(rnd.random() < 0.35 for _ in range(60))
        eb = sum(rnd.random() < 0.20 for _ in range(60))
        if _linha_de_direcao(ea, 60, eb, 60).direcao_confiavel == "passivo":
            achou += 1
    poder = 100 * achou / 2000
    assert 30.0 < poder < 65.0, (
        f"poder de {poder:.0f}% para 35% vs 20% com 60 por lado — se subiu "
        f"muito, o limiar afrouxou; se caiu, a ferramenta ficou muda")


def test_uma_decisao_nao_alimenta_os_DOIS_lados_da_direcao():
    """Um limp de 72o dispara `limp_de_abertura` (passivo) E `call_caro`
    (solto). Contar os dois é a MESMA ficha nos dois pratos da balança — e
    uma decisão não pode ser prova de passividade e de soltura ao mesmo
    tempo. Quando os códigos apontam para lados opostos, o honesto é não
    contar nenhum.

    Medido em 09/08 numa amostra de 24 mãos com 12 limps: `direcao` saía
    {passivo: 12, solto: 24} e `chances` {passivo: 48, solto: 24}.
    """
    from app.analysis.estrategia_torneio import por_faixa
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      HandFormat, PlayerSeat, Stakes, Street,
                                      StreetName)

    def _limp(hid):
        bb = 100.0
        return CanonicalHand(
            site="GG", hand_id=hid, hero="Hero",
            format=HandFormat.TOURNAMENT, source_format="txt",
            played_at="2026-08-01T20:00:00+00:00",
            stakes=Stakes(small_blind=50, big_blind=bb, ante=25),
            players=[PlayerSeat(seat=1, name="Hero", stack=18 * bb,
                                position="CO", is_hero=True),
                     PlayerSeat(seat=2, name="V", stack=18 * bb,
                                position="BTN"),
                     PlayerSeat(seat=3, name="O", stack=18 * bb,
                                position="SB")],
            hero_cards=["7h", "2d"],
            streets=[Street(name=StreetName.PREFLOP, actions=[
                Action(actor="O", type=ActionType.POST, amount=50,
                       post_type="sb"),
                Action(actor="V", type=ActionType.POST, amount=100,
                       post_type="bb"),
                Action(actor="Hero", type=ActionType.CALL, amount=100,
                       to_amount=100)])])

    linha = por_faixa([_limp(f"h{i}") for i in range(12)])[0]
    ambiguos = min(linha.direcao["passivo"], linha.direcao["solto"])
    assert ambiguos == 0, (
        f"a mesma decisão apareceu nos dois lados: {linha.direcao}")
    assert linha.direcao_confiavel is None, (
        "afirmou direção a partir de decisões que apontam para os dois lados")


def test_RAISE_nao_e_call_caro():
    """"Pagou mais caro do que a mão vale" para quem AUMENTOU é erro de
    categoria, não de conta — e o preço usado (`to_call/(pote+to_call)`) é o
    de pagar.

    Medido em 09/08: 24 mãos, 12 delas com raise, e as 24 acusadas.
    """
    from app.analysis.taxonomia import observar
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      HandFormat, PlayerSeat, Stakes, Street,
                                      StreetName)

    bb = 100.0
    aumentou = CanonicalHand(
        site="GG", hand_id="r1", hero="Hero", format=HandFormat.TOURNAMENT,
        source_format="txt", played_at="2026-08-01T20:00:00+00:00",
        stakes=Stakes(small_blind=50, big_blind=bb, ante=25),
        players=[PlayerSeat(seat=1, name="Hero", stack=18 * bb, position="CO",
                            is_hero=True),
                 PlayerSeat(seat=2, name="V", stack=18 * bb, position="BTN"),
                 PlayerSeat(seat=3, name="O", stack=18 * bb, position="SB")],
        hero_cards=["7h", "2d"],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="O", type=ActionType.POST, amount=50, post_type="sb"),
            Action(actor="V", type=ActionType.POST, amount=100,
                   post_type="bb"),
            Action(actor="Hero", type=ActionType.RAISE, amount=250,
                   to_amount=250)])])

    assert not [o for o in observar([aumentou]) if o.codigo == "call_caro"], (
        "um RAISE virou 'pagou mais caro do que a mão vale'")


# ---- etapa do torneio, frequência e inversão -------------------------------

def _mao_de_etapa(hid, stack_bb, mesa_bb, entrou, n_jog=6):
    """Mão com stack do HERÓI e média da MESA controlados separadamente —
    que é o ponto: os dois eixos são ortogonais."""
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      HandFormat, PlayerSeat, Stakes, Street,
                                      StreetName)

    bb = 100.0
    # os vilões carregam o resto para a média da mesa bater
    resto = (mesa_bb * n_jog - stack_bb) / (n_jog - 1)
    jog = [PlayerSeat(seat=1, name="Hero", stack=stack_bb * bb, position="CO",
                      is_hero=True)]
    jog += [PlayerSeat(seat=i + 2, name=f"V{i}", stack=max(resto, 1.0) * bb,
                       position=p)
            for i, p in enumerate(["BTN", "SB", "BB", "UTG", "MP"][:n_jog - 1])]
    acao = (Action(actor="Hero", type=ActionType.RAISE, amount=250,
                   to_amount=250) if entrou
            else Action(actor="Hero", type=ActionType.FOLD))
    return CanonicalHand(
        site="GG", hand_id=hid, hero="Hero", format=HandFormat.TOURNAMENT,
        source_format="txt", played_at="2026-08-01T20:00:00+00:00",
        stakes=Stakes(small_blind=50, big_blind=bb, ante=25),
        players=jog, hero_cards=["Ah", "Kd"],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="V1", type=ActionType.POST, amount=50,
                   post_type="sb"),
            Action(actor="V2", type=ActionType.POST, amount=100,
                   post_type="bb"),
            acao])])


def test_a_etapa_do_torneio_sai_da_MESA_e_nao_do_heroi():
    """O eixo que faltava, e ele É medido. O corte por ante nunca separou a
    amostra — no banco, as 517 mãos de fonte completa TÊM ante, todas. O
    stack médio da mesa separa porque as blinds sobem mais rápido do que as
    fichas se concentram.

    E é ortogonal à profundidade do herói, que é a premissa do módulo: 18bb
    numa mesa de 60bb é ser o curto; 18bb numa mesa de 15bb é todo mundo
    estar curto.
    """
    from app.analysis.estrategia_torneio import etapa_do_torneio, faixa_de

    curto_cedo = _mao_de_etapa("a", stack_bb=18, mesa_bb=60, entrou=False)
    curto_tarde = _mao_de_etapa("b", stack_bb=18, mesa_bb=15, entrou=False)

    assert etapa_do_torneio(curto_cedo) == "inicial"
    assert etapa_do_torneio(curto_tarde) == "final"
    # mesma faixa de stack, etapas diferentes — é isso que permite a pergunta
    assert faixa_de(18.0) == faixa_de(18.0) == "re-shove"


def test_frequencia_por_faixa_so_afirma_com_amostra():
    """"Você joga X% das mãos nesta faixa" é afirmação sobre um NÚMERO, e
    precisa de n. Faixa curta não some — sai com `dizivel=False` e o motivo,
    porque faixa que some vira 'ele não joga isso'."""
    from app.analysis.estrategia_torneio import (MIN_PARA_FREQUENCIA,
                                                 frequencia_por_faixa)

    maos = ([_mao_de_etapa(f"d{i}", 60, 60, entrou=(i % 4 == 0))
             for i in range(MIN_PARA_FREQUENCIA + 10)]
            + [_mao_de_etapa(f"r{i}", 18, 40, entrou=True) for i in range(5)])
    linhas = {l["faixa"]: l for l in frequencia_por_faixa(maos)}

    assert linhas["deep"]["dizivel"] is True
    assert linhas["deep"]["vpip_pct"] == pytest.approx(25.0, abs=3.0)
    assert linhas["deep"]["margem_pp"] > 0, "taxa sem margem é promessa"

    assert linhas["re-shove"]["dizivel"] is False
    assert "preciso de" in linhas["re-shove"]["por_que_nao"]
    assert linhas["re-shove"]["maos"] == 5, "a faixa curta sumiu"


def test_frequencia_nao_sai_de_replay_avulso():
    """Frequência sobre mão escolhida a dedo é o VPIP 94% de novo."""
    from app.analysis.estrategia_torneio import frequencia_por_faixa

    maos = [_mao_de_etapa(f"d{i}", 60, 60, entrou=True) for i in range(80)]
    for m in maos:
        m.source_format = "pppoker_replay"
    assert frequencia_por_faixa(maos) == []


def test_inversao_compara_a_MESMA_profundidade_entre_etapas():
    """A pergunta original do dono, finalmente mensurável.

    Sem fixar o stack, a diferença entre início e fim é só o stack
    encolhendo — que é a árvore mudando, não o jogador.
    """
    from app.analysis.estrategia_torneio import inversao

    # mesma faixa (re-shove), MUITO mais solto no fim
    maos = ([_mao_de_etapa(f"i{i}", 18, 60, entrou=(i % 5 == 0))
             for i in range(40)]                       # 20% no início
            + [_mao_de_etapa(f"f{i}", 18, 15, entrou=(i % 5 != 0))
               for i in range(40)])                    # 80% no fim
    out = inversao(maos)

    assert out["aplicavel"] is True
    linha = next(l for l in out["linhas"] if l["faixa"] == "re-shove")
    assert linha["inicio"]["vpip_pct"] < linha["final"]["vpip_pct"]
    assert linha["veredito"] == "solta perto do dinheiro"


def test_inversao_se_cala_quando_a_diferenca_nao_separa():
    """Os números REAIS do dono, medidos no banco em 09/08: re-shove com 42
    mãos no início (VPIP 16,7%) e 32 no fim (15,6%).

    Não há inversão nenhuma ali, e a resposta certa é o silêncio — não um
    veredito com cara de diagnóstico. Este teste existe para que 'a
    ferramenta não achou nada' seja um resultado, e não um bug.
    """
    from app.analysis.estrategia_torneio import inversao

    maos = ([_mao_de_etapa(f"i{i}", 18, 60, entrou=(i < 7)) for i in range(42)]
            + [_mao_de_etapa(f"f{i}", 18, 15, entrou=(i < 5))
               for i in range(32)])
    out = inversao(maos)

    linha = next(l for l in out["linhas"] if l["faixa"] == "re-shove")
    assert linha["inicio"]["maos"] == 42 and linha["final"]["maos"] == 32
    assert linha["veredito"] is None, (
        f"afirmou inversão com {linha['inicio']['vpip_pct']}% contra "
        f"{linha['final']['vpip_pct']}%")


def test_sem_os_dois_lados_a_inversao_diz_por_que_nao_da():
    """Toda a amostra numa etapa só: comparar um grupo com nada é o tipo de
    tabela que parece análise e não é."""
    from app.analysis.estrategia_torneio import inversao

    out = inversao([_mao_de_etapa(f"i{i}", 18, 60, entrou=False)
                    for i in range(60)])
    assert out["aplicavel"] is False
    assert "início E no fim" in out["por_que"]
