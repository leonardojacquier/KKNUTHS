"""A análise entregue começa pelo selo — a narração de tools fica no bastidor.

Caso real — juiz da saída de 31/07, primeiro dia medindo o artefato certo:
nota 3.5/10, com 6 análises "SEM selo de veredito na 1ª linha". O selo
EXISTIA em todas; estava enterrado atrás de "Deixa eu conferir o EV desse
open-shove..." — a frase que o coach escreve antes de chamar cada tool. Com
duas rodadas de tools o preâmbulo ainda saía duplicado ("Deixa eu conferir
a leitura do river..." + "Deixa eu ver que equity...").
"""
from app.agent.llm import _montar_resposta


def test_narracao_pre_tool_e_cortada():
    parts = ["Deixa eu conferir o EV desse open-shove com A7s a 7.9bb.",
             "✅ Você jogou bem — open-shove padrão\n\nCom 7.9bb no CO..."]
    saida = _montar_resposta(parts)
    assert saida.startswith("✅")
    assert "Deixa eu conferir" not in saida


def test_preambulo_duplicado_some_inteiro():
    """Duas rodadas de tools = duas frases de bastidor. Caso real das 10:18."""
    parts = ["Deixa eu conferir a leitura do river e a força do seu range.",
             "Deixa eu ver que equity seus dois pares têm contra o range.",
             "✅ Você jogou bem — largou o river com preço ruim\n\n🟡 *Pré*..."]
    saida = _montar_resposta(parts)
    assert saida.startswith("✅")
    assert "Deixa eu" not in saida


def test_sem_selo_nenhum_bloco_e_descartado():
    """Rodadas esgotadas ou resposta de conversa: o texto pré-tools é a rede
    de segurança e não pode sumir — comportamento antigo preservado."""
    parts = ["Vou calcular a equity desse spot.",
             "Contra 88+ e AQ você tem 41% — o call fica marginal."]
    saida = _montar_resposta(parts)
    assert saida == ("Vou calcular a equity desse spot.\n\n"
                     "Contra 88+ e AQ você tem 41% — o call fica marginal.")


def test_selo_amarelo_e_vermelho_tambem_ancoram():
    assert _montar_resposta(["bastidor", "🟡 Dava pra jogar melhor..."]) \
        .startswith("🟡")
    assert _montar_resposta(["bastidor", "❌ Jogada cara..."]).startswith("❌")


def test_blocos_depois_do_selo_sao_mantidos():
    parts = ["bastidor", "✅ Você jogou bem", "A conta que mais pesa: ..."]
    saida = _montar_resposta(parts)
    assert saida.endswith("A conta que mais pesa: ...")


def test_todos_os_loops_de_tools_usam_a_montagem():
    """Se um caminho novo voltar ao join cru, o preâmbulo volta com ele."""
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm)
    assert 'join(x.strip() for x in parts' not in fonte, \
        "use _montar_resposta(parts) em vez do join cru"
    assert fonte.count("_montar_resposta(parts)") >= 6
