"""A conversa confunde a mão narrada com a última analisada.

Caso real (21/08, conversa do dono): ele tinha analisado a mão A♠A♥ contra o
Tio Neuri e DEPOIS narrou por texto uma mão de K♠5♠. Ao pedir "me mostra o EV
de call dessa mão", o bot respondeu sobre a A♠A♥ — três vezes, até o dono
escrever "Não seu burro quero a outra mão que eu estava narrando do call com
K5". Ele se corrigia quando cobrado, mas custava dois turnos.

A causa não era memória: era um RÓTULO QUE MENTE. O contexto ia para o modelo
sob o título "Contexto da análise em discussão", e o modelo acreditava —
resolvia "essa mão" para a mão do rótulo, ignorando a que o aluno acabara de
narrar. O rótulo honesto é "última mão ANALISADA", que é o que ele de fato é.
"""
from __future__ import annotations

import json

import pytest


@pytest.fixture
def llm(monkeypatch):
    from app.agent import llm as modulo

    monkeypatch.setattr(
        modulo, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m",
                               "cheap_model": "barato"})())
    return modulo


def _capturar(monkeypatch, llm):
    """Roda followup com _create falso e devolve o que foi enviado."""
    from types import SimpleNamespace

    visto: dict = {}

    def _fake(client, **kw):
        visto.update(kw)
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text="ok")])

    monkeypatch.setattr(llm, "_create", _fake)
    return visto


CONTEXTO = {"analysis_anterior": "✅ Você jogou bem com A♠A♥",
            "mao": {"hero_cards": ["As", "Ah"], "site": "PPPoker"}}


def test_o_rotulo_nao_promete_que_e_a_mao_em_discussao(llm, monkeypatch):
    visto = _capturar(monkeypatch, llm)
    llm.followup(CONTEXTO, [], "me mostra o EV de call dessa mão")
    enviado = json.dumps(visto["messages"], ensure_ascii=False)
    assert "análise em discussão" not in enviado, (
        "o rótulo afirma que ESTA é a mão em discussão — era a mentira que "
        "fazia o modelo ignorar a mão narrada pelo aluno")
    assert "ANALISADA" in enviado


def test_a_regra_manda_a_mao_narrada_vencer(llm, monkeypatch):
    visto = _capturar(monkeypatch, llm)
    llm.followup(CONTEXTO, [], "e o K5 de espadas?")
    system = json.dumps(visto["system"], ensure_ascii=False)
    assert "narr" in system.lower(), "o prompt não diz o que fazer com mão narrada"
    # a regra tem de nomear o conflito: narrada x analisada
    assert "analisada" in system.lower()


def test_o_historico_da_conversa_continua_indo_junto(llm, monkeypatch):
    """A correção não pode custar o histórico — é onde a narração mora."""
    visto = _capturar(monkeypatch, llm)
    llm.followup(CONTEXTO,
                 [{"q": "tinha K♠5♠ e paguei o all-in", "a": "beleza"}],
                 "qual o EV?")
    enviado = json.dumps(visto["messages"], ensure_ascii=False)
    assert "K♠5♠" in enviado
