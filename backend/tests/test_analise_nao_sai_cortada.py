"""A análise nunca sai pela metade: o teto medido e o sinal de corte da API.

Caso real de 16/08 19:19. Um aluno recebeu 150 caracteres, gravados assim em
`hand_analysis` — não é corte do Telegram, é o texto que o código produziu:

    🟡 Dava pra jogar melhor — pagou um all-in no talo
    ✅ *Pré-flop* — abriu 2bb com 3♣3♦ no HJ: padrão, sem problema, ...
    🟡 *

Cortado no meio da segunda linha do placar. A chamada saiu com exatamente
1.500 tokens de saída — o `max_tokens` da análise —, a API devolveu
`stop_reason='max_tokens'` com um `tool_use` pendurado, e o código entregou
assim mesmo: a ÚNICA porta do resgate era `if not _tem_selo(final)`, e texto
cortado que COMEÇA com selo passa nessa checagem. O sinal que a API manda
dizendo "isto está incompleto" não era lido em lugar nenhum do fluxo.

Subir o teto (o outro conserto, em `test_teto_da_analise.py`) reduz a chance;
não elimina. O contrato que estes testes prendem é o sinal:
`stop_reason == 'max_tokens'` na resposta que produziria o texto final proíbe
a entrega — mesmo com selo. Tenta o resgate; se o resgate não vier completo,
cai no plano C, que é honesto ("a análise completa não saiu") em vez de meia
frase. E o corte vira evento com nome próprio, para dar para medir a
frequência depois.

O que NÃO é defeito: bater no teto durante uma rodada de ferramenta. O laço
continua e o texto se completa depois — só o corte no texto FINAL é o
problema.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

# O texto exato que chegou ao aluno em 16/08 19:19: parcial, COM selo na
# primeira linha (é isso que fura a checagem) e cortado no meio da segunda
# linha do placar.
TEXTO_QUE_O_ALUNO_RECEBEU = (
    "🟡 Dava pra jogar melhor — pagou um all-in no talo\n\n"
    "✅ *Pré-flop* — abriu 2bb com 3♣3♦ no HJ: padrão, sem problema, "
    "dentro do seu range de abertura.\n"
    "🟡 *"
)

ANALISE_INTEIRA = "✅ Você jogou bem — a análise inteira, do pré ao river."


def _bloco(tipo, **kw):
    return SimpleNamespace(type=tipo, **kw)


def _resposta_cortada():
    """A resposta de produção: texto parcial COM selo + `tool_use` pendurado."""
    return SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("text", text=TEXTO_QUE_O_ALUNO_RECEBEU),
                 _bloco("tool_use", id="toolu_01PENDURADO", name="ev_call",
                        input={})])


def _rodada_de_ferramenta():
    """Rodada normal: o modelo pede ferramenta e o laço continua."""
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[_bloco("tool_use", id="t1", name="inexistente", input={})])


class _Repo:
    enabled = True

    def __init__(self):
        self.eventos: list[tuple[str, dict]] = []

    def log_event(self, tid, user, event, detail):
        self.eventos.append((event, detail))


@pytest.fixture
def repo(monkeypatch):
    r = _Repo()
    monkeypatch.setattr("app.db.get_repository", lambda: r)
    return r


@pytest.fixture
def llm(monkeypatch):
    from app.agent import llm as modulo

    monkeypatch.setattr(
        modulo, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m",
                               "cheap_model": "barato"})())
    return modulo


def _identidade_da_conferencia(*a):
    """`_conferir_numeros(client, modelo, blocks, messages, final, fontes)`.

    Neutralizada de propósito: sem isso a reescrita da conferência poderia
    trocar o texto cortado pelo bom e o teste passaria pelo motivo errado.
    """
    return a[4]


def test_texto_cortado_com_selo_nao_chega_ao_aluno(llm, monkeypatch, repo):
    """O furo exato de 16/08: o parcial JÁ TEM selo, então `_tem_selo(final)`
    é verdadeiro e o resgate nem era tentado. Agora o `stop_reason` manda."""
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)
    monkeypatch.setattr(llm, "_force_text", lambda *a, **k: ANALISE_INTEIRA)

    out = llm.coach({"summary": "PLANO C"}, None)

    assert out == ANALISE_INTEIRA
    assert "Pré-flop" not in out, "meia frase de 16/08 voltou ao aluno"


def test_sem_resgate_o_aluno_le_o_resumo_e_nao_meia_frase(llm, monkeypatch,
                                                          repo):
    """Plano C é honesto: o aluno lê que a análise completa não saiu, em vez
    de uma frase pela metade que parece uma análise."""
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)
    monkeypatch.setattr(llm, "_force_text", lambda *a, **k: None)

    out = llm.coach({"summary": "RESUMO DETERMINÍSTICO"}, None)

    assert out == "RESUMO DETERMINÍSTICO"
    assert "Pré-flop" not in out


def test_corte_no_teto_vira_evento_com_nome_proprio(llm, monkeypatch, repo):
    """Sem evento próprio não dá para medir a frequência do defeito depois —
    o `plano_c` sozinho mistura corte com falha de rede e resposta muda."""
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)
    monkeypatch.setattr(llm, "_force_text", lambda *a, **k: None)

    llm.coach({"summary": "RESUMO DETERMINÍSTICO"}, None)

    nomes = [e for e, _ in repo.eventos]
    assert "analise_cortada" in nomes, \
        "o corte tem de ser contável sozinho, no padrão de plano_c/voz_corrigida"
    detalhe = next(d for e, d in repo.eventos if e == "analise_cortada")
    assert detalhe["stop_reason"] == "max_tokens"
    assert detalhe["onde"] == "analise_principal"
    assert detalhe["resgatado"] is False
    assert "plano_c" in nomes, "a queda no resumo continua registrada"


def test_conclusao_de_resgate_cortada_nao_e_entregue(llm, monkeypatch, repo):
    """Se a própria conclusão de resgate sair cortada, ela também não pode ser
    entregue: `_force_text` descarta o parcial e devolve None."""
    monkeypatch.setattr(llm, "_create", lambda *a, **k: SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("text",
                        text="✅ Você jogou bem — o pote estava em 24bb e o")]))

    assert llm._force_text(None, "m", [], []) is None
    assert "analise_cortada" in [e for e, _ in repo.eventos]
    detalhe = next(d for e, d in repo.eventos if e == "analise_cortada")
    assert detalhe["onde"] == "forca_conclusao"


def test_fim_de_rodadas_com_resgate_cortado_nao_entrega_meia_conclusao(
        llm, monkeypatch, repo):
    """O outro ponto do fluxo: rodadas esgotadas, o resgate é a única fonte de
    texto — e sai cortado. O aluno leva o resumo, não a meia conclusão."""
    fila = iter([_rodada_de_ferramenta()] * llm.MAX_TOOL_ROUNDS
                + [SimpleNamespace(
                    stop_reason="max_tokens",
                    content=[_bloco("text", text=TEXTO_QUE_O_ALUNO_RECEBEU)])])
    monkeypatch.setattr(llm, "_create", lambda *a, **k: next(fila))

    out = llm.coach({"summary": "RESUMO DETERMINÍSTICO"}, None)

    assert "Pré-flop" not in out
    assert out == "RESUMO DETERMINÍSTICO"
    assert "analise_cortada" in [e for e, _ in repo.eventos]


def test_o_caminho_bom_continua_intacto(llm, monkeypatch, repo):
    """Bater no teto DURANTE uma rodada de ferramenta não é o defeito: o laço
    continua e o texto se completa depois. Análise que termina em 'end_turn'
    vai inteira ao aluno, sem resgate e sem evento de corte."""
    completa = ("🟡 Dava pra jogar melhor — pagou um all-in no talo\n\n"
                "✅ *Pré-flop* — abertura padrão.\n"
                "🟡 *Flop* — o check-raise ficou grande demais.")
    fila = iter([_rodada_de_ferramenta(),
                 SimpleNamespace(stop_reason="end_turn",
                                 content=[_bloco("text", text=completa)])])
    monkeypatch.setattr(llm, "_create", lambda *a, **k: next(fila))
    monkeypatch.setattr(llm, "_conferir_numeros", _identidade_da_conferencia)

    def _resgate_nao_deveria_rodar(*a, **k):
        raise AssertionError("resgate disparou no caminho bom")

    monkeypatch.setattr(llm, "_force_text", _resgate_nao_deveria_rodar)

    out = llm.coach({"summary": "PLANO C"}, None)

    assert "Flop" in out
    assert repo.eventos == [], "o caminho bom não paga pedágio de evento"
