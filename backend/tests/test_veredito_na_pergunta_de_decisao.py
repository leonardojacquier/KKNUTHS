"""Pergunta de decisão respondida sem veredito.

Juiz de 22/08, pior resposta (3.5/10, conversa): "Resposta não diz se a
decisão foi certa ou errada com clareza — mistura análise de equity com
narrativa do que aconteceu, deixando confuso se o call foi +EV ou não."

Medido no corpus da janela: 7 perguntas de DECISÃO, 5 respondidas sem selo
(71%). A análise tem o R1 obrigando o selo na 1ª linha; a conversa herda o
prompt e nunca exige veredito.

O contrato NÃO é "toda conversa leva selo" — o docstring de judge_answer já
decidiu, com razão, que carimbar ✅/🟡/❌ numa resposta explicativa ("não
seria melhor o shove de 11bb?") é ruído. O contrato é: quando o aluno PEDE
o veredito, ele recebe o veredito.
"""
from __future__ import annotations

import json

import pytest

from scripts.output_judge import judge_answer

SEM_SELO = ("Com sua equity de 75% contra o all-in de 17bb num pote de "
            "50bb, o call dá +33bb de EV — bem lucrativo no longo prazo.")
COM_SELO = ("✅ Call certo — +33bb de EV\n\nCom 75% de equity contra o "
            "all-in de 17bb num pote de 50bb, pagar ganha fichas.")

DECISAO = [
    "Aquela mão com k e 5 por ICM está certo o call ?",
    "Joguei certo ?",
    "eu devia ter pagado ali?",
    "foi erro dar call nesse spot",
    "vale a pena pagar com esse stack?",
]
EXPLICATIVA = [
    "não seria melhor o shove de 11bb?",
    "me explica o que é fold equity",
    "qual o range dele nesse spot?",
]


@pytest.mark.parametrize("q", DECISAO)
def test_pergunta_de_decisao_sem_selo_e_apontada(q):
    probs = judge_answer(SEM_SELO, conversa=True, pergunta=q)
    assert any("veredito" in p for p in probs), f"{q!r} passou batido: {probs}"


@pytest.mark.parametrize("q", DECISAO)
def test_pergunta_de_decisao_com_selo_passa(q):
    assert judge_answer(COM_SELO, conversa=True, pergunta=q) == []


@pytest.mark.parametrize("q", EXPLICATIVA)
def test_pergunta_explicativa_nao_exige_selo(q):
    """O ruído que o docstring de judge_answer proíbe continua proibido."""
    probs = judge_answer(SEM_SELO, conversa=True, pergunta=q)
    assert not any("veredito" in p for p in probs), f"{q!r} virou falso positivo"


def test_sem_a_pergunta_o_juiz_nao_inventa_defeito():
    """Chamada antiga (sem `pergunta`) não pode passar a acusar."""
    assert not any("veredito" in p
                   for p in judge_answer(SEM_SELO, conversa=True))


def test_a_analise_continua_exigindo_selo_sempre():
    """Não-regressão: o R1 da análise não depende de pergunta nenhuma."""
    analise = ("Você pagou 2bb no flop e 4bb no turn, com equity de 30% "
               "contra o range dele.")
    assert any("SEM selo" in p for p in judge_answer(analise, conversa=False))


def test_o_prompt_da_conversa_manda_liderar_com_o_veredito(monkeypatch):
    from types import SimpleNamespace

    from app.agent import llm

    monkeypatch.setattr(
        llm, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-t", "analysis_model": "m",
                               "cheap_model": "b"})())
    visto: dict = {}

    def _fake(client, **kw):
        visto.update(kw)
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text="ok")])

    monkeypatch.setattr(llm, "_create", _fake)
    llm.followup({"mao": {}}, [], "joguei certo?")
    system = json.dumps(visto["system"], ensure_ascii=False).lower()
    assert "decis" in system and "selo" in system
