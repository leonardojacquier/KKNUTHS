"""Do erro ao problema, do problema à alta — e as armadilhas no caminho.

Um erro isolado não é problema; um PADRÃO é. A diferença entre os dois não é
impressão, é um conjunto de portões — e é o que separa um plano de estudo de
uma opinião com número.

As três armadilhas que destroem esse tipo de sistema, e que os testes aqui
travam:

1. REGRESSÃO À MÉDIA. O problema é escolhido POR SER O PIOR, ou seja, por
   estar no extremo da flutuação. A próxima medição melhora sozinha, sem
   intervenção nenhuma. Sem tratar isso o sistema reporta melhora falsa de
   forma SISTEMÁTICA — e seria a segunda quebra de confiança da ferramenta.
2. COMPARAÇÕES MÚLTIPLAS. Varrer 15 códigos e escolher o pior é procurar o
   extremo; a IC95 erra 1 em 20 por desenho.
3. DECLARAR VITÓRIA CEDO. Sem critério pré-registrado, sempre se acha um
   jeito de fechar olhando o dado depois.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.analysis.problemas import (ARQUIVADO, CAUSAS, EM_ALTA, MAX_ATIVOS,
                                    OBSERVACAO, PROBLEMA, RESOLVIDO, SUSPEITA,
                                    Evidencia, avaliar, baseline_valida,
                                    bloqueado_por, criterio_de_alta,
                                    pode_dar_alta, prioridade)


def _diag(**kw):
    base = {"codigo": "bb_subdefesa", "oportunidades": 40, "escorregadas": 28,
            "taxa_mean": 70.0, "tolerancia_pct": 35.0, "custo_bb_100": 2.1,
            "custo_e_estimado": False}
    return {**base, **kw}


def _ev(dias, opp=10, miss=5, exata=True):
    return [Evidencia(d, opp, miss, exata) for d in dias]


_TRES_SESSOES = ["2026-07-20", "2026-07-26", "2026-08-01"]


# ---- os cinco portões ------------------------------------------------------

def test_padrao_com_evidencia_vira_problema():
    v = avaliar(_diag(), _ev(_TRES_SESSOES))
    assert v.estado == PROBLEMA
    assert all(ok for ok, _ in v.portoes.values())


def test_erro_concentrado_numa_noite_e_tilt_nao_leak():
    """40 oportunidades numa sessão só, com a mesma taxa: pode ter sido uma
    noite ruim. Abrir um ciclo de 4 semanas em cima disso é caro e errado."""
    v = avaliar(_diag(), _ev(["2026-08-01"]))
    assert v.estado == SUSPEITA
    assert "recorrencia" in v.por_que


def test_amostra_pequena_nem_chega_a_suspeita():
    """2 escorregadas em 3 chances. Não se fala com o aluno — o posterior
    ainda é o prior, e 'estou de olho' já seria afirmação demais."""
    v = avaliar(_diag(oportunidades=3, escorregadas=2), _ev(_TRES_SESSOES))
    assert v.estado == OBSERVACAO


def test_evidencia_de_print_nao_sustenta_diagnostico():
    """Print lido por visão erra carta e posição. Diagnóstico em cima disso
    é o incidente do VPIP por outro caminho."""
    v = avaliar(_diag(), _ev(_TRES_SESSOES, exata=False))
    assert v.estado == SUSPEITA and "procedencia" in v.por_que


def test_leak_barato_nao_vira_ciclo_de_quatro_semanas():
    v = avaliar(_diag(custo_bb_100=0.2), _ev(_TRES_SESSOES))
    assert v.estado == SUSPEITA and "custo" in v.por_que


def test_custo_estimado_exige_mais_evidencia():
    """Detector de custo estimado erra mais; a régua acompanha."""
    exato = avaliar(_diag(oportunidades=22, escorregadas=16),
                    _ev(_TRES_SESSOES))
    estim = avaliar(_diag(oportunidades=22, escorregadas=16,
                          custo_e_estimado=True), _ev(_TRES_SESSOES))
    assert exato.estado == PROBLEMA
    assert estim.estado == OBSERVACAO


def test_o_motivo_vem_junto_do_estado():
    """O dono precisa poder DISCORDAR. Estado sem motivo é caixa-preta."""
    v = avaliar(_diag(custo_bb_100=0.1), _ev(_TRES_SESSOES))
    assert "0.10bb/100" in v.por_que or "0.1" in v.por_que


# ---- comparações múltiplas -------------------------------------------------

def test_muitos_codigos_testados_endurecem_a_regua():
    """Varrer 15 códigos e pegar o pior é procurar o extremo: com IC95, ~1 em
    20 dá positivo por sorte, e o sistema é DESENHADO para maximizar isso."""
    # 14/22: pior caso 36.2% no IC95 (passa da tolerância de 35%) e 30.5%
    # no IC99 (não passa). É exatamente a faixa em que a régua decide.
    marginal = _diag(oportunidades=22, escorregadas=14, taxa_mean=60.0)
    poucos = avaliar(marginal, _ev(_TRES_SESSOES), codigos_testados=3)
    muitos = avaliar(marginal, _ev(_TRES_SESSOES), codigos_testados=15)
    assert poucos.estado == PROBLEMA
    assert muitos.estado != PROBLEMA, "a régua não endureceu"


# ---- regressão à média -----------------------------------------------------

def test_baseline_nao_pode_ser_a_janela_que_diagnosticou():
    """A armadilha mais insidiosa, e a única SISTEMÁTICA: o problema foi
    escolhido por estar no extremo, então a medição seguinte melhora sozinha."""
    assert baseline_valida("2026-08-01", ["2026-08-01"]) is False
    assert baseline_valida("2026-08-01", ["2026-07-28"]) is False
    assert baseline_valida("2026-08-01", ["2026-08-05", "2026-08-07"]) is True


def test_sem_baseline_nao_ha_baseline():
    assert baseline_valida("2026-08-01", []) is False


# ---- critério de alta pré-registrado --------------------------------------

def test_o_criterio_e_escrito_antes_e_por_extenso():
    c = criterio_de_alta(_diag(), datetime(2026, 8, 9, tzinfo=timezone.utc))
    assert c["n_minimo"] == 30 and c["janelas_minimas"] == 2
    assert c["registrado_em"].startswith("2026-08-09")
    assert "considero resolvido quando" in c["por_extenso"]


def test_o_alvo_e_grande_porque_pequeno_e_imensuravel():
    """Melhora de 50%->40% precisa de ~400 oportunidades por período para ser
    detectável. Nenhum aluno de clube produz isso; alvo que a amostra não
    mede não é alvo."""
    c = criterio_de_alta(_diag(taxa_mean=70.0))
    assert c["limiar"] == pytest.approx(28.0, abs=0.1)
    assert c["limiar"] / 70.0 <= 0.45


# ---- os seis critérios da alta --------------------------------------------

def _medicao(**kw):
    base = {"oportunidades": 40, "post_hi": 20.0, "limiar": 28.0,
            "janelas": 2, "dias": 20}
    return {**base, **kw}


def test_alta_com_tudo_no_lugar():
    ok, por_que = pode_dar_alta(_medicao(), controle_melhorou=False,
                                contexto_estavel=True)
    assert ok and "bateram" in por_que


def test_amostra_curta_nao_da_alta():
    ok, por_que = pode_dar_alta(_medicao(oportunidades=12), False, True)
    assert not ok and "30" in por_que


def test_intervalo_encostando_no_limiar_nao_da_alta():
    """Exigir o limite SUPERIOR abaixo da linha é deliberadamente
    conservador: só afirma melhora quando a incerteza inteira cabe embaixo.
    A média poderia estar em 20% com o intervalo indo até 30 — e aí a
    melhora ainda não está provada."""
    encostando, _ = pode_dar_alta(_medicao(post_hi=28.5), False, True)
    assert not encostando
    coube, _ = pode_dar_alta(_medicao(post_hi=27.9), False, True)
    assert coube, "intervalo inteiro abaixo do limiar TEM que dar alta"


def test_uma_sessao_boa_nao_e_alta():
    ok, por_que = pode_dar_alta(_medicao(janelas=1, dias=3), False, True)
    assert not ok and "2 janelas" in por_que


def test_controle_que_melhorou_junto_derruba_a_alta():
    """O teste mais barato e mais eficaz da lista: se uma categoria NÃO
    tratada melhorou junto, foi campo mais mole, não aprendizado."""
    ok, por_que = pode_dar_alta(_medicao(), controle_melhorou=True,
                                contexto_estavel=True)
    assert not ok and "campo mais mole" in por_que


def test_mudanca_de_stake_recusa_a_comparacao():
    ok, por_que = pode_dar_alta(_medicao(), False, contexto_estavel=False)
    assert not ok and "não dá para comparar" in por_que


# ---- fila, prioridade e pré-requisito -------------------------------------

def test_um_problema_ativo_por_vez():
    """O argumento é ESTATÍSTICO: três ativos dividem as oportunidades por
    três e nenhum fecha."""
    assert MAX_ATIVOS == 1


def test_pre_requisito_vira_o_problema_no_lugar():
    """Não adianta trabalhar defesa de BB com quem não calcula preço de pote:
    metade daquelas mãos ele erra pelo motivo errado."""
    assert bloqueado_por("bb_subdefesa", set()) == "pot_odds"
    assert bloqueado_por("bb_subdefesa", {"pot_odds"}) is None
    assert bloqueado_por("limp_de_abertura", set()) is None


def test_aluno_novo_comeca_pelo_ciclo_mais_curto():
    """A primeira alta é o que ensina o aluno que o sistema tem saída. Sem
    ela ele abandona antes da segunda."""
    caro_e_lento = _diag(codigo="call_caro", custo_bb_100=4.0)
    barato_e_rapido = _diag(codigo="limp_de_abertura", custo_bb_100=0.9)

    veterano = (prioridade(caro_e_lento, 2.0)
                > prioridade(barato_e_rapido, 25.0))
    novato = (prioridade(barato_e_rapido, 25.0, aluno_novo=True)
              > prioridade(caro_e_lento, 2.0, aluno_novo=True))
    assert veterano, "para quem já está dentro, manda o custo"
    assert novato, "para quem chegou agora, manda o que fecha rápido"


def test_o_que_destrava_outros_sobe_na_fila():
    sozinho = _diag(codigo="limp_de_abertura", custo_bb_100=1.0)
    destrava = _diag(codigo="pot_odds", custo_bb_100=1.0)
    assert prioridade(destrava, 10.0) > prioridade(sozinho, 10.0)


# ---- as quatro causas ------------------------------------------------------

def test_cada_causa_tem_intervencao_propria():
    """Mandar teoria para quem já sabe a teoria é o desperdício mais comum:
    se o aluno acerta o quiz e erra na mesa, mais lição não resolve nada."""
    assert set(CAUSAS) == {"conhecimento", "reconhecimento", "execucao",
                           "economico"}
    for _sintoma, intervencao in CAUSAS.values():
        assert intervencao
    assert "não é teoria" in CAUSAS["execucao"][1]
    assert "bankroll" in CAUSAS["economico"][1]


# ---- os seis estados -------------------------------------------------------

def test_arquivado_e_diferente_de_resolvido():
    """É o estado que impede o sistema de FABRICAR vitória: quando o aluno
    para de jogar aquele spot, o problema não foi resolvido — sumiu. Com
    três estados isso viraria sucesso no relatório."""
    assert ARQUIVADO != RESOLVIDO
    assert len({OBSERVACAO, SUSPEITA, PROBLEMA, EM_ALTA, RESOLVIDO,
                ARQUIVADO}) == 6


def test_so_problema_gera_plano_de_estudo():
    import inspect

    from app.analysis import problemas

    doc = inspect.getdoc(problemas)
    assert "ÚNICO estado que gera plano" in doc


# ---- o que o aluno lê ------------------------------------------------------

def _ativo(**kw):
    base = {"codigo": "bb_subdefesa", "nome": "folda demais o big blind",
            "pergunta": "No BB, quais mãos pagam o open?",
            "oportunidades": 14, "escorregadas": 4, "alta_n_minimo": 40}
    return {**base, **kw}


def test_abaixo_do_n_minimo_sai_contagem_crua_e_nao_percentual():
    """'4 de 14' é honesto. '29%' com n=14 é a mesma classe de erro do VPIP
    94% — percentual promete uma precisão que o denominador não paga."""
    from app.analysis.problemas import texto_do_plano

    t = texto_do_plano(_ativo(), [], [])
    assert "4 escorregada(s) nessas 14" in t
    assert "%" not in t


def test_enquanto_nao_conclui_mostra_progresso_de_COLETA():
    """A alta demora 4-8 semanas. Ficar mudo é perder o aluno; inventar
    número é perder a confiança. Barra de coleta é honesta e motiva."""
    from app.analysis.problemas import texto_do_plano

    t = texto_do_plano(_ativo(), [], [])
    assert "Coleta:" in t and "14 de ~40" in t
    assert "Ainda não dá para dizer se melhorou" in t
    assert "te aviso quando souber" in t


def test_a_fila_aparece_mesmo_com_um_ativo_so():
    """Um por vez é decisão estatística; sem ver o resto o aluno acha que a
    ferramenta é míope."""
    from app.analysis.problemas import texto_do_plano

    t = texto_do_plano(_ativo(), [{"nome": "call caro"}, {"nome": "limp"}], [])
    assert "Na fila (2)" in t and "call caro" in t


def test_todo_plano_mostra_pelo_menos_um_acerto():
    """Detector de acerto quase nunca é construído — e sem ele a ferramenta
    é só um crítico. Crítico se abandona."""
    from app.analysis.problemas import texto_do_plano

    t = texto_do_plano(_ativo(), [], ["12 shoves de stack curto, nenhum erro"])
    assert "está de pé" in t and "nenhum erro" in t


def test_com_amostra_cheia_o_criterio_pre_registrado_aparece():
    from app.analysis.problemas import texto_do_plano

    t = texto_do_plano(
        _ativo(oportunidades=44, escorregadas=6,
               alta_por_extenso="considero resolvido quando cair para 28%"),
        [], [])
    assert "6 de 44" in t
    assert "considero resolvido quando" in t


def test_sem_problema_ativo_nao_inventa_plano():
    from app.analysis.problemas import texto_do_plano

    assert texto_do_plano({}, [{"nome": "x"}], ["y"]) == ""
