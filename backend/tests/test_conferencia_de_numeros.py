"""A conferência de números chega à análise principal — combinado de 15/08.

Juiz do dia em 6.3 com meta 7: entram as duas alavancas combinadas com o
dono — Sonnet como default e a regra da casa no caminho principal: todo
número da análise precisa de LASTRO (contexto da mão ou resultado de
ferramenta). Número órfão gera UMA reescrita corretiva; se persistir, a
análise sai e o evento fica registrado — visibilidade, nunca silêncio, e
nunca abaixo do que já ia sair.

As fronteiras anti-falso-positivo valem tanto quanto a checagem: carta não
é número, jargão ('3-bet', '2 pares') não é número, e arredondamento na
precisão escrita é lastro ('22,7%' e '23%' casam com 0.227 do contexto).
"""
from __future__ import annotations

import pytest

from app.analysis.conferencia import conferir_analise, numeros_do_lastro


LASTRO = numeros_do_lastro(
    '{"equity_real": 0.227, "ev_call_bb": -1.49, "stack_bb": 18.7, '
    '"pot": 8780}',
    '{"result": 0.7487}',
)


def test_numeros_com_lastro_passam_em_qualquer_escala():
    texto = ("❌ Pagou pedindo 22,7% — você tinha 74,87% antes, mas o EV do "
             "call é -1,49bb com 18.7bb de stack e pote de 8780.")
    assert conferir_analise(texto, LASTRO) == []


def test_arredondamento_na_precisao_escrita_e_lastro():
    assert conferir_analise("tinha 75% e pedia 23%", LASTRO) == []
    assert conferir_analise("stack de 19bb", LASTRO) == []


def test_numero_inventado_reprova():
    assert conferir_analise("você blefa 87% das vezes", LASTRO) == ["87"]
    # 0.70 de lastro NÃO lastreia 75 (|70-75| = 5 > 0.5)
    assert conferir_analise("tinha 75%", numeros_do_lastro("0.70")) == ["75"]


def test_carta_nao_e_numero():
    assert conferir_analise("o 10♣ pareou e o 9♥ fechou flush", set()) == []


def test_jargao_pequeno_nao_conta_mas_decimal_pequeno_conta():
    assert conferir_analise("3-bet com 2 pares em 4 jogadores", set()) == []
    assert conferir_analise("EV de 2,5bb", set()) == ["2,5"], \
        "decimal é conta, não jargão — precisa de lastro"


# ---- a correção no coach ----------------------------------------------------

def test_reescrita_corrigida_e_adotada(monkeypatch):
    import app.agent.llm as llm

    monkeypatch.setattr(llm, "_force_text",
                        lambda *a: "✅ Você jogou bem\npedia 22,7%, EV -1,49bb")
    saida = llm._conferir_numeros(
        None, "m", [], [], "✅ Você jogou bem\nvocê blefa 87% das vezes",
        ['{"eq": 0.227, "ev": -1.49}'])
    assert "87" not in saida
    assert "22,7%" in saida


def test_reescrita_pior_mantem_a_original(monkeypatch):
    """A reescrita veio sem selo (ou igualmente órfã): entrega a original —
    a conferência nunca degrada abaixo do que já ia sair."""
    import app.agent.llm as llm

    original = "✅ Você jogou bem\nvocê blefa 87% das vezes"
    monkeypatch.setattr(llm, "_force_text",
                        lambda *a: "continuo achando 87% e sem selo")
    assert llm._conferir_numeros(None, "m", [], [], original,
                                 ['{"eq": 0.227}']) == original


def test_analise_limpa_nao_gasta_chamada(monkeypatch):
    import app.agent.llm as llm

    def explode(*a):
        raise AssertionError("não pode chamar o modelo quando o lastro fecha")

    monkeypatch.setattr(llm, "_force_text", explode)
    limpa = "✅ Você jogou bem\npedia 22,7%"
    assert llm._conferir_numeros(None, "m", [], [], limpa,
                                 ['{"eq": 0.227}']) == limpa


def test_as_duas_saidas_do_coach_conferem_numeros():
    import inspect

    import app.agent.llm as llm

    fonte = inspect.getsource(llm.coach)
    assert fonte.count("_conferir_numeros(") == 2
    assert "fontes_de_numeros.append(out)" in fonte, \
        "cada resultado de tool entra no lastro"


# ---- o combinado do modelo --------------------------------------------------

def test_default_da_analise_e_sonnet(monkeypatch):
    monkeypatch.delenv("ANALYSIS_MODEL", raising=False)
    from app.config import Settings

    assert Settings().analysis_model == "claude-sonnet-5"


def test_R1_nomeia_a_ressalva_no_selo():
    """A pior resposta de 15/08 (5.5): '✅ jogou bem' seguido de crítica ao
    pré sem aviso — lia como contradição. O prompt agora exige a ressalva
    nas palavras do próprio selo."""
    from app.agent.llm import _SYSTEM

    assert "nomeiam a ressalva" in _SYSTEM["pt"]
    assert "só o sizing do pré escapou" in _SYSTEM["pt"]


def test_fronteira_do_jargao_e_5():
    """5 sem decimal é jargão e passa; 6 já precisa de lastro."""
    assert conferir_analise("pagou 5 vezes", set()) == []
    assert conferir_analise("pagou 6 vezes", set()) == ["6"]


def test_reescrita_com_selo_mas_igualmente_orfa_nao_e_adotada(monkeypatch):
    """A reescrita só entra se REDUZIU os órfãos — trocar 87 por 91 com selo
    bonito não é correção."""
    import app.agent.llm as llm

    original = "✅ Você jogou bem\nvocê blefa 87% das vezes"
    monkeypatch.setattr(llm, "_force_text",
                        lambda *a: "✅ Você jogou bem\nvocê blefa 91% das vezes")
    assert llm._conferir_numeros(None, "m", [], [], original,
                                 ['{"eq": 0.227}']) == original
