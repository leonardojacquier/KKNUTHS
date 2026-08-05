"""Orquestração de custo: cache de 1h + roteamento por complexidade.

Medido (01-03/08): 53% de TODO o custo de LLM era reescrita do prefixo de
16k tokens — 28 esfriadas de cache em 3 dias (US$ 2,89) no padrão real de
uso (15 mãos numa manhã, intervalos de 10-40min > TTL de 5min). A escrita
de 1h custa 2x em vez de 1,25x; UMA reescrita evitada paga a diferença.

O roteamento (SIMPLE_HAND_MODEL) nasce DESLIGADO: só liga depois que o
juiz comparar a clareza por modelo — barato errando caro sai mais caro.
"""
from app.agent import llm
from app.agent.llm import _bloco_cacheado, mao_simples


def test_cache_declara_ttl_de_1h():
    bloco = _bloco_cacheado("sistema")
    assert bloco[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert bloco[0]["text"] == "sistema"


def test_rejeicao_do_ttl_cai_pro_padrao_sem_quebrar():
    llm._TTL_OK = False
    try:
        assert _bloco_cacheado("s")[0]["cache_control"] == {"type": "ephemeral"}
    finally:
        llm._TTL_OK = True


def test_create_envia_o_header_beta_do_ttl():
    import inspect

    fonte = inspect.getsource(llm._create)
    assert "_BETA_TTL" in fonte
    assert '"ttl" in msg' in fonte, "fallback quando a API rejeitar o ttl"


def test_mao_de_decisao_unica_preflop_e_simples():
    assert mao_simples({"spots": [
        {"street": "preflop", "type": "raise", "all_in": True}]})


def test_qualquer_decisao_pos_flop_vai_pro_modelo_cheio():
    assert not mao_simples({"spots": [
        {"street": "preflop", "type": "raise"},
        {"street": "river", "type": "call"}]})
    assert not mao_simples({"spots": [{"street": "turn", "type": "bet"}]})


def test_duas_decisoes_preflop_ja_nao_e_simples():
    """Open + call de 3-bet = árvore de verdade, não decisão única."""
    assert not mao_simples({"spots": [
        {"street": "preflop", "type": "raise"},
        {"street": "preflop", "type": "call"}]})


def test_icm_salvo_nunca_roteia_pro_barato():
    assert not mao_simples({"payouts_salvos": {"valores": [100, 60, 40]},
                            "spots": [{"street": "preflop", "type": "raise"}]})


def test_flag_desligada_por_padrao():
    import os

    from app.config import Settings

    os.environ.pop("SIMPLE_HAND_MODEL", None)
    assert Settings().simple_hand_model == ""


def test_analise_gravada_leva_o_modelo():
    """Sem o modelo na análise, o juiz não tem como comparar clareza por
    modelo — e o roteamento ligaria às cegas."""
    import inspect

    from app.bot import processing
    from app.db import repository

    assert "modelo" in inspect.getsource(repository.Repository.save_hand_analysis)
    fonte = inspect.getsource(processing._process_upload_inner)
    assert "modelo=modelo_escolhido or settings_rt.analysis_model" in fonte


def test_juiz_da_nota_por_modelo():
    """Com o roteamento ligado, a comparação Sonnet vs Opus é o que decide
    se a economia fica — e comparação silenciosa não decide nada: com 2+
    modelos na janela, o juiz SEMPRE reporta."""
    import inspect

    from scripts import output_judge

    fonte = inspect.getsource(output_judge.main)
    assert "notas_por_modelo" in fonte
    assert "modelo" in fonte.split('select("summary,created_at,modelo")')[0] \
        or 'select("summary,created_at,modelo")' in fonte
    assert "bool(notas_por_modelo)" in fonte, "A/B ativo força o relatório"


def test_achado_do_juiz_diz_o_modelo():
    import inspect

    from scripts import output_judge

    fonte = inspect.getsource(output_judge.main)
    assert "análise·" in fonte, "problema de forma atribuído ao modelo certo"


def test_carta_crua_ganha_icone_na_entrega():
    """1ª rodada do A/B: o Sonnet escreveu 'Jh, Kh' cru. A regra da casa
    (ícone de naipe) agora é aplicada na entrega, deterministicamente."""
    from app.agent.termos import corrigir

    assert corrigir("Com Jh e Kh no flop 9s 4d 2c.") \
        == "Com J♥ e K♥ no flop 9♠ 4♦ 2♣."
    assert corrigir("O Ah no river fechou o flush.") \
        == "O A♥ no river fechou o flush."


def test_portugues_nao_vira_carta():
    from app.agent.termos import corrigir

    for frase in ("Ah, entendi o spot!",       # interjeição
                  "As blinds subiram rápido.",  # artigo
                  "Ah… foi cooler mesmo."):
        assert corrigir(frase) == frase, frase


def test_analise_sem_selo_ganha_selo_de_emergencia():
    """O selo é a regra de ouro; se o modelo esquecer, a linha é gerada à
    parte (modelo barato) e PREPENDADA — nunca reescrevendo a análise."""
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm.coach)
    assert "_selo_de_emergencia" in fonte
    assert "key_hands is None" in fonte, "relatório de torneio fica de fora"
    fonte_selo = inspect.getsource(llm._selo_de_emergencia)
    assert "cheap_model" in fonte_selo
    assert 'startswith(_SELOS_DE_VEREDITO)' in fonte_selo, \
        "resposta que não é um selo é descartada, não prependada"
