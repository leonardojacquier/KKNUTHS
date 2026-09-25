"""Ele melhorou? — a medição que se recusa a mentir.

Esta é a parte com maior chance de queimar a confiança de novo, porque
"progresso" é o número que o dono mais quer ver e o mais fácil de fabricar
sem perceber.

O DEFEITO QUE ERA NOSSO: `leak_boost` puxa mais das categorias em que o
aluno erra. Ótimo para TREINAR, fatal para MEDIR — quando ele melhora, o
boost cai, o mix de spots muda, e a taxa de acerto observada muda por
mudança de AMOSTRA, não de habilidade. Qualquer série temporal montada sobre
o drill normal é ininterpretável por construção.
"""
from __future__ import annotations

import pytest

from app.analysis.evolucao import (INCONCLUSIVO, MELHOROU, NAO_MELHOROU,
                                   contexto_mudou, kappa, medir,
                                   n_necessario, texto_da_medicao)


# ---- o veredito tem TRÊS valores, e o terceiro é obrigatório --------------

def _pos(opp=40, erros=6):
    return {"oportunidades": opp, "escorregadas": erros}


def test_melhora_so_quando_o_intervalo_inteiro_cabe_abaixo_do_alvo():
    """Conservador por desenho: depois de um incidente de confiança, o custo
    de dizer 'ainda não sei' é muito menor que o de errar de novo."""
    m = medir({"taxa": 70.0}, _pos(60, 4), limiar=28.0)
    assert m.veredito == MELHOROU and "abaixo do alvo" in m.por_que


def test_amostra_curta_e_sempre_inconclusivo():
    """Sem exceção, sem 'mas a tendência é boa'."""
    m = medir({"taxa": 70.0}, _pos(12, 1), limiar=28.0)
    assert m.veredito == INCONCLUSIVO
    assert m.faltam == 18


def test_faixa_encostando_no_alvo_nao_e_melhora():
    m = medir({"taxa": 70.0}, _pos(40, 12), limiar=28.0)
    assert m.veredito == INCONCLUSIVO and "encosta" in m.por_que


def test_taxa_que_subiu_e_dita_sem_rodeio():
    m = medir({"taxa": 30.0}, _pos(40, 32), limiar=12.0)
    assert m.veredito == NAO_MELHOROU


# ---- a categoria de controle ----------------------------------------------

def test_controle_que_melhorou_junto_derruba_a_conclusao():
    """A linha de código de maior retorno da lista: se um código que ninguém
    tratou melhorou junto, foi campo mais mole ou amostra diferente."""
    m = medir({"taxa": 70.0}, _pos(60, 4), limiar=28.0,
              controle_antes={"taxa": 40.0}, controle_depois={"taxa": 15.0})
    assert m.veredito == INCONCLUSIVO
    assert "campo mais mole" in m.por_que


def test_controle_estavel_deixa_a_melhora_de_pe():
    m = medir({"taxa": 70.0}, _pos(60, 4), limiar=28.0,
              controle_antes={"taxa": 40.0}, controle_depois={"taxa": 38.0})
    assert m.veredito == MELHOROU


# ---- mudança de contexto ---------------------------------------------------

def test_trocar_de_stake_recusa_a_comparacao():
    """'Você melhorou' quando ele desceu de $22 para $5 é uma mentira que o
    próprio aluno desmente sozinho."""
    m = medir({"taxa": 70.0}, _pos(60, 4), limiar=28.0,
              contexto_antes={"buyin_medio": 22.0},
              contexto_depois={"buyin_medio": 5.0})
    assert m.veredito == INCONCLUSIVO and "não dá para comparar" in m.por_que


def test_variacao_pequena_de_contexto_nao_atrapalha():
    assert contexto_mudou({"buyin_medio": 10.0}, {"buyin_medio": 11.0}) is False
    assert contexto_mudou({"buyin_medio": 10.0}, {"buyin_medio": 22.0}) is True


# ---- o piso do chute -------------------------------------------------------

def test_acerto_de_quiz_e_ajustado_por_chance():
    """60% com 4 botões é 47% ajustado. Reportar o acerto cru infla o
    progresso de graça, e o piso do chute é o que ninguém lembra de descontar."""
    assert kappa(60, 100, opcoes=4) == pytest.approx(0.467, abs=0.01)
    assert kappa(25, 100, opcoes=4) == pytest.approx(0.0, abs=0.01)
    assert kappa(0, 0) is None


# ---- alvo que a amostra não mede não é alvo --------------------------------

def test_melhora_pequena_e_declarada_imensuravel():
    """50%->40% precisa de ~400 oportunidades por período. Nenhum aluno de
    clube produz isso; o sistema tem que DIZER isso em vez de fingir."""
    assert n_necessario(50.0, 40.0) >= 400
    assert n_necessario(60.0, 30.0) <= 60


# ---- o texto do aluno ------------------------------------------------------

def test_inconclusivo_soa_como_trabalho_em_curso():
    """Se 'ainda não sei' soar como falha da ferramenta, o aluno some antes
    de a amostra fechar."""
    t = texto_da_medicao(medir({"taxa": 70.0}, _pos(10, 2), 28.0), "defesa de BB")
    assert "ainda não sei" in t
    assert "Prefiro te dizer isso a chutar" in t
    assert "Faltam ~20" in t


def test_nao_melhorou_troca_a_abordagem_e_nao_o_volume():
    """Repetir a mesma lição mais alto é o modo de falha clássico: se não
    melhorou, a hipótese de CAUSA estava errada."""
    t = texto_da_medicao(medir({"taxa": 30.0}, _pos(40, 32), 12.0), "call caro")
    assert "trocar a abordagem" in t and "mais alto" in t


def test_alta_vem_com_vigilancia_e_sem_drama():
    t = texto_da_medicao(medir({"taxa": 70.0}, _pos(60, 4), 28.0), "limp")
    assert "Resolvido" in t and "60 dias" in t


# ---- o conserto do leak_boost ---------------------------------------------

def test_o_drill_de_afericao_sorteia_uniforme():
    """Com o boost ligado, a taxa de acerto muda porque o MIX mudou, não
    porque o aluno melhorou. Só o de aferição pode virar número."""
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing.build_drill)
    assert "afericao" in fonte
    assert "lambda _r, _c: 1.0" in fonte, "o boost não foi neutralizado"


def test_uma_afericao_a_cada_cinco():
    from app.bot.repeticao import A_CADA, e_afericao

    assert A_CADA == 5
    assert [n for n in range(1, 16) if e_afericao(n)] == [5, 10, 15]
    assert e_afericao(0) is False


def test_a_conta_e_de_drills_feitos_e_nao_sorteio():
    """Aleatório pode passar semanas sem cair uma aferição justamente no
    aluno que treina pouco — que é quem menos tem amostra a perder."""
    from app.bot.repeticao import e_afericao

    assert all(e_afericao(n) == (n % 5 == 0 and n > 0) for n in range(0, 40))


def test_o_evento_marca_o_que_foi_afericao():
    """Sem a marca no evento não dá para separar depois o que MEDE do que
    TREINA — e o evento é a única fonte."""
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers.on_drill_answer)
    assert "afericao=bool(drill.get(\"afericao\"))" in fonte


def test_o_treino_escolhe_afericao_pelo_historico():
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers._send_treino)
    assert "e_afericao" in fonte and "drill_verdicts" in fonte


def test_placebo_aluno_que_nao_muda_nao_recebe_alta():
    """A prova que faltava, e a mais importante do módulo.

    O aluno é escolhido para intervenção por estar no EXTREMO da flutuação,
    então a janela seguinte melhora sozinha — regressão à média. Se o critério
    de alta fosse derivado daquela janela (`taxa * 0,4`, como era até 09/08),
    essa melhora fantasma viraria alta.

    Com o alvo sendo a TOLERÂNCIA DO CÓDIGO — externa, fixa, conhecida antes
    de olhar o aluno — e a alta exigindo o limite SUPERIOR abaixo dela, a
    barra não se move. Aqui a habilidade NÃO muda em nenhum dos casos.

    Medido com 4.000 sorteios por célula (aqui reduzido para a suíte rodar
    rápido):

        taxa real   n=62    n=120
             2%    28,9%    31,2%   <- ESTÁ curado (2% < 5%): alta é correta
             5%     4,5%     1,4%   <- na linha: erro nominal, e cai com n
            10%     0,1%     0,0%
            20%     0,0%     0,0%
            35%     0,0%     0,0%
    """
    import random

    from app.analysis.bayes import shrunk_rate
    from app.analysis.evolucao import MELHOROU, medir
    from app.analysis.problemas import criterio_de_alta, pode_dar_alta

    alta = criterio_de_alta({"codigo": "limp_de_abertura",
                             "taxa_mean": 100.0, "taxa_lo": 90.0})
    limiar, n = alta["limiar"], alta["n_minimo"]
    rnd = random.Random(20260809)

    def _fracao_de_altas(p_verdadeiro, sorteios=800):
        altas = 0
        for _ in range(sorteios):
            erros = sum(rnd.random() < p_verdadeiro for _ in range(n))
            m = medir({"taxa": 100.0},
                      {"oportunidades": n, "escorregadas": erros}, limiar)
            if m.veredito != MELHOROU:
                continue
            _, _lo, hi = shrunk_rate(erros, n, 20.0, 6.0)
            ok, _ = pode_dar_alta(
                {"oportunidades": n, "post_hi": round(hi, 1),
                 "limiar": limiar, "janelas": 4, "dias": 20}, False, True)
            altas += ok
        return altas / sorteios

    # ACIMA da referência: a habilidade não mudou e ele NÃO está curado
    for p in (0.10, 0.20, 0.35):
        taxa = _fracao_de_altas(p)
        assert taxa <= 0.01, (
            f"aluno com taxa real de {p*100:.0f}% (referência {limiar}%) "
            f"recebeu alta em {taxa*100:.1f}% das simulações sem mudar nada")

    # ABAIXO da referência: ele ESTÁ curado, e aí a alta é o comportamento
    # certo. Um sistema que nunca dá alta é tão inútil quanto um que sempre dá.
    assert _fracao_de_altas(0.02) > 0.10, (
        "aluno genuinamente abaixo da referência nunca recebe alta — o ciclo "
        "não fecha e o aluno abandona")
