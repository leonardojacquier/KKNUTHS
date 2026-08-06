"""Selo de veredito é contrato da ANÁLISE, não de toda resposta.

Caso real — o juiz das 8h reportou dois "problemas de forma":
  análise de mão SEM selo de veredito na 1ª linha — «Não seria melhor o
  show de 11bb…»
Aquilo era uma PERGUNTA de follow-up do aluno. A resposta certa explica a
alternativa; carimbar ✅ na primeira linha ali é ruído.

O juiz amostrava só conversation_state.history — que é follow-up puro — e
cobrava dali o contrato da análise inicial, que mora em hand_analysis. Dois
falsos positivos por dia, e a análise de verdade nunca auditada.
"""
from scripts.output_judge import _e_analise_de_mao, judge_answer

_COM_STREET_E_BB = ("Se você shovar 11bb ali no turn, o range que te paga "
                    "vira 88+ e AQ+ — a conta muda muito.")


def test_follow_up_nao_precisa_de_selo():
    assert _e_analise_de_mao(_COM_STREET_E_BB), "tem street e bb"
    assert judge_answer(_COM_STREET_E_BB, conversa=True) == []


def test_analise_entregue_ainda_precisa_de_selo():
    probs = judge_answer(_COM_STREET_E_BB, conversa=False)
    assert any("SEM selo" in p for p in probs)


def test_analise_com_selo_passa():
    texto = "✅ Você jogou bem\n\n" + _COM_STREET_E_BB
    assert not any("SEM selo" in p for p in judge_answer(texto))


def test_conversa_ainda_cobra_o_resto_do_contrato():
    """Afrouxar o selo não pode afrouxar calque, carta crua e bastidor."""
    ruim = "No turn com 10bb você tinha um par alto — a ferramenta calculou."
    probs = judge_answer(ruim, conversa=True)
    assert any("calque" in p or "par alto" in p for p in probs) or probs, probs
    assert not any("SEM selo" in p for p in probs)


def test_o_juiz_le_os_dois_artefatos():
    """Se voltar a ler só a conversa, o selo deixa de ser auditado."""
    import inspect

    from scripts import output_judge

    fonte = inspect.getsource(output_judge.main)
    assert "hand_analysis" in fonte, "as análises entregues têm que entrar"
    assert "conversation_state" in fonte
    assert "[Follow-up]" in fonte, "follow-up gravado em hand_analysis não é análise"


def test_o_juiz_audita_a_janela_de_24h_e_nao_o_museu():
    """O texto gravado é imutável: auditar 'os últimos N' faz o mesmo estoque
    antigo reprovar todo dia. Caso real: um dia depois do conserto do
    preâmbulo, o juiz reportou 5 análises 'sem selo' — todas de ANTES do
    deploy. As pós-conserto estavam limpas, e a nota não media o produto
    corrente."""
    import inspect

    from scripts import output_judge

    fonte = inspect.getsource(output_judge.main)
    assert "day_ago" in fonte
    assert fonte.count('gte("updated_at", day_ago)') == 1, "janela na conversa"
    assert fonte.count('gte("created_at", day_ago)') == 1, "janela nas análises"


def test_nota_sobre_amostra_pequena_vem_com_aviso():
    """05/08: nota 3.5 sobre DUAS respostas — um turno de conversa pesou a
    janela inteira e soou como colapso do produto. Nota agora diz o n, e
    n<4 leva o aviso de sal."""
    import inspect

    from scripts import output_judge

    fonte = inspect.getsource(output_judge.main)
    assert "amostra pequena" in fonte
    assert "len(pares) < 4" in fonte


def test_conversa_manda_responder_antes_de_confirmar():
    """Caso real (7-2 por voz): a 1ª resposta gastou o turno pedindo
    confirmação e narrando busca falhada ('não consegui puxar a mão')."""
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm.followup)
    assert "RESPONDA PRIMEIRO" in fonte
    assert "NÃO narre bastidor de busca" in fonte


def test_agregar_notas_da_as_tres_leituras_das_mesmas_notas():
    """Pedido do dono (06/08): nota POR resposta + nota geral. A média da
    janela, o A/B por modelo e a pior resposta saem das MESMAS notas
    individuais — e cada nota vira evento, alimentando a média de 7 dias."""
    from scripts.output_judge import agregar_notas

    avaliadas = [
        {"nota": 9.0, "conversa": False, "modelo": "opus-4-8"},
        {"nota": 8.0, "conversa": False, "modelo": "opus-4-8"},
        {"nota": 7.0, "conversa": False, "modelo": "sonnet-5"},
        {"nota": 3.0, "conversa": True, "pior": "enrolou"},
        {"nota": None, "conversa": True},          # avaliação falhou
    ]
    agr = agregar_notas(avaliadas)
    assert agr["media"] == 6.8 and agr["n"] == 4
    assert agr["por_modelo"] == {"opus-4-8": {"media": 8.5, "n": 2},
                                 "sonnet-5": {"media": 7.0, "n": 1}}
    assert agr["pior"]["nota"] == 3.0, "a conversa ruim é apontada, não a média"


def test_sem_nenhuma_nota_nao_inventa_media():
    from scripts.output_judge import agregar_notas

    assert agregar_notas([{"nota": None}])["media"] is None


def test_cada_nota_vira_evento_e_a_media_movel_vem_do_historico():
    import inspect

    from scripts import output_judge

    fonte = inspect.getsource(output_judge.main)
    assert '"nota_resposta"' in fonte, "nota individual gravada como evento"
    assert "media7" in fonte and "days=7" in fonte
    assert "média 7 dias" in fonte, "o relatório mostra o produto, não só o dia"
