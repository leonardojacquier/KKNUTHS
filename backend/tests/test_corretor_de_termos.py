"""O corretor conserta o calque ANTES de chegar no aluno.

Pergunta do dono (02/08): "tem como fazer o próprio juiz já corrigir esses
termos, ou preciso de você aqui?". Resposta em código: o subconjunto
mecânico é corrigido na entrega, deterministicamente — mesma filosofia do
guarda da saída. O que precisa de contexto continua só sinalizado pelo
juiz, porque trocar errado é pior que avisar.
"""
from app.agent.termos import corrigir


def test_full_house_traduzido_vira_full_de_x_com_y():
    assert corrigir("Ele tinha 7 cheio de 2, o full máximo.") \
        == "Ele tinha full de 7 com 2, o full máximo."
    assert corrigir("Você mostrou A cheia de K.") == "Você mostrou full de A com K."


def test_check_atras_vira_check_behind():
    assert corrigir("Deu check atrás no turn.") == "Deu check behind no turn."


def test_aumentou_pra_vira_deu_raise():
    assert corrigir("Ele aumentou pra 6bb no flop.") \
        == "Ele deu raise pra 6bb no flop."
    assert corrigir("re-aumentou para o all-in de 49.5bb") \
        == "deu re-raise para o all-in de 49.5bb"


def test_carta_alta_e_sequencia_de_cor():
    assert corrigir("Só tinha carta alta no river.") \
        == "Só tinha high card no river."
    assert corrigir("Fechou a sequência de cor.") == "Fechou a straight flush."


def test_portugues_normal_fica_intacto():
    """As trocas são cirúrgicas: frase legítima não pode mudar."""
    for frase in ("O pote passou de 20bb.",
                  "A pressão aumentou depois do 3-bet.",
                  "Ele fez uma sequência de 3-bets seguidos.",
                  "O board estava cheio de draws.",
                  "A mesa aumentou o ritmo."):
        assert corrigir(frase) == frase, frase


def test_texto_vazio_nao_quebra():
    assert corrigir("") == ""
    assert corrigir(None) is None


def test_corretor_roda_na_montagem_e_na_simplificacao():
    """Tem que estar no ponto de ENTREGA — senão o texto torto chega no
    aluno e ainda fica gravado no banco pro juiz reprovar depois."""
    import inspect

    from app.agent import llm

    assert "corrigir" in inspect.getsource(llm._montar_resposta)
    assert "corrigir" in inspect.getsource(llm.simplify)
