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


# --- 19/08: o juiz pegou uma CONVERSA entregue cortada no meio ------------
#
# `followup` (teto 1200) e `evaluate_line` (900) só liam `tool_use`: corte
# por max_tokens era tratado como resposta final e ia ao aluno. "Resposta
# incompleta (corta no meio)" — juiz de 19/08, nota 5.5, n=1.


def test_conversa_cortada_nao_e_entregue(llm, monkeypatch, repo):
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    monkeypatch.setattr(llm, "_force_text",
                        lambda *a, **k: "Resposta inteira do resgate.")
    out = llm.followup({"summary": "mão analisada"}, [], "e se ele 3-beta?")
    assert out == "Resposta inteira do resgate."
    assert TEXTO_QUE_O_ALUNO_RECEBEU not in (out or "")
    assert any(e == "analise_cortada" and d.get("onde") == "conversa"
               for e, d in repo.eventos)


def test_conversa_cortada_sem_resgate_devolve_none(llm, monkeypatch, repo):
    """None faz o processing mandar o recado honesto ('me embananei') em vez
    de meia frase — o mesmo contrato que o followup já tinha para falha."""
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    monkeypatch.setattr(llm, "_force_text", lambda *a, **k: None)
    assert llm.followup({"summary": "m"}, [], "?") is None


def test_simulador_cortado_nao_e_entregue(llm, monkeypatch, repo):
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    monkeypatch.setattr(llm, "_force_text",
                        lambda *a, **k: "Veredito inteiro do resgate.")
    out = llm.evaluate_line({"cards": ["As", "Kd"], "position": "CO",
                             "history": [], "street": "flop"})
    assert out == "Veredito inteiro do resgate."
    assert any(e == "analise_cortada" and d.get("onde") == "simulador"
               for e, d in repo.eventos)


def test_conversa_sem_corte_continua_intacta(llm, monkeypatch, repo):
    inteira = SimpleNamespace(
        stop_reason="end_turn",
        content=[_bloco("text", text="Resposta completa, sem corte.")])
    monkeypatch.setattr(llm, "_create", lambda *a, **k: inteira)
    monkeypatch.setattr(llm, "_force_text",
                        lambda *a, **k: pytest.fail("resgate não devia rodar"))
    out = llm.followup({"summary": "m"}, [], "?")
    assert out == "Resposta completa, sem corte."
    assert repo.eventos == []


# --- 21/08: TERCEIRA mão PDQ com corte duplo (4000 + 2500, sempre exatos) --
#
# O titular degenera nessas mãos; repetir o mesmo modelo repete o loop. A
# reserva troca de modelo UMA vez antes do plano C — em 16/08 o opus fez
# essas mesmas mãos em 300-750 tokens.


def _create_por_modelo(chamadas):
    """_create fake: titular sempre corta; a reserva responde inteiro."""
    def _fake(client, **kw):
        chamadas.append(kw.get("model"))
        if kw.get("model") == "reserva-m":
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[_bloco("text", text=ANALISE_INTEIRA)])
        return _resposta_cortada()
    return _fake


def test_corte_duplo_tenta_a_reserva_e_o_aluno_recebe_analise(
        llm, monkeypatch, repo):
    chamadas: list = []
    monkeypatch.setattr(llm, "_create", _create_por_modelo(chamadas))
    monkeypatch.setattr(
        llm, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "titular-m",
                               "cheap_model": "barato",
                               "analysis_fallback_model": "reserva-m"})())
    out = llm.coach({"summary": "PLANO C"}, None)
    assert out == ANALISE_INTEIRA          # análise de verdade, não o resumo
    assert "reserva-m" in chamadas          # a reserva foi chamada
    assert chamadas.count("reserva-m") == 1  # UMA vez, não um segundo loop
    assert any(e == "analise_cortada" and d.get("resgatado") is True
               for e, d in repo.eventos)


def test_reserva_tambem_cortada_cai_no_plano_c(llm, monkeypatch, repo):
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    out = llm.coach({"summary": "PLANO C"}, None)
    assert out == "PLANO C"
    assert any(e == "plano_c" for e, d in repo.eventos)


def test_evento_do_corte_carrega_amostra_do_texto(llm, monkeypatch, repo):
    monkeypatch.setattr(llm, "_create", lambda *a, **k: _resposta_cortada())
    llm.coach({"summary": "PLANO C"}, None)
    cortes = [d for e, d in repo.eventos
              if e == "analise_cortada" and d.get("onde") == "analise_principal"]
    assert cortes and "amostra_inicio" in cortes[0]
    assert TEXTO_QUE_O_ALUNO_RECEBEU.startswith(
        cortes[0]["amostra_inicio"][:40])


# --- 21/08, segunda sonda: corte SEM texto (loop dentro do tool_use) ------
#
# A mão PDQ do Rico cortou 4000 com amostra NULA: o teto inteiro foi
# queimado num tool_use cujo input nunca fecha. Amostra de texto não vê
# isso; a de blocos vê — nome da ferramenta e o RABO do input.


def test_corte_sem_texto_amostra_os_blocos(llm, monkeypatch, repo):
    so_tool = SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("tool_use", id="t1", name="ev_call",
                        input={"range": ["AA", "KK"] * 40})])
    monkeypatch.setattr(llm, "_create", lambda *a, **k: so_tool)
    llm.coach({"summary": "PLANO C"}, None)
    cortes = [d for e, d in repo.eventos
              if e == "analise_cortada" and d.get("onde") == "analise_principal"]
    assert cortes, "o corte nem foi registrado"
    amostra = cortes[0].get("amostra_inicio") or ""
    assert "ev_call" in amostra          # a ferramenta do loop tem nome
    assert "input_fim" in amostra        # e o rabo do input está lá


def test_corte_do_resgate_amostra_o_texto(llm, monkeypatch, repo):
    monkeypatch.setattr(llm, "_create", lambda *a, **k: SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("text", text="tagarelando sobre ranges " * 30)]))
    llm._force_text(None, "m", [], [{"role": "user", "content": "x"}])
    cortes = [d for e, d in repo.eventos
              if e == "analise_cortada" and d.get("onde") == "forca_conclusao"]
    assert cortes and "tagarelando sobre ranges" in \
        (cortes[0].get("amostra_inicio") or "")


# --- 21/08, a CAUSA RAIZ da semana: thinking adaptativo por omissão --------
#
# O sonnet-5 liga pensamento adaptativo quando `thinking` é omitido, e o
# pensamento consome max_tokens ANTES do texto (sonda: 2500 tokens = um
# bloco [thinking] e nada mais). A casa decide: o LLM julga, as FERRAMENTAS
# fazem a conta — thinking desligado por padrão, com retry se o modelo
# rejeitar o parâmetro (mesmo contrato do _NO_TEMP).


class _ClienteQueCaptura:
    def __init__(self):
        self.kwargs: list[dict] = []

        class _Msgs:
            def __init__(s, outer):
                s.outer = outer

            def create(s, **kw):
                s.outer.kwargs.append(kw)
                return SimpleNamespace(
                    stop_reason="end_turn",
                    content=[_bloco("text", text="ok")], usage=None)

        self.messages = _Msgs(self)


def test_create_desliga_thinking_por_padrao(llm):
    cli = _ClienteQueCaptura()
    llm._create(cli, model="claude-sonnet-5", max_tokens=100,
                messages=[{"role": "user", "content": "x"}])
    assert cli.kwargs[0]["thinking"] == {"type": "disabled"}


def test_modelo_que_rejeita_thinking_entra_na_lista_e_segue(llm):
    class _ClienteQueRejeita(_ClienteQueCaptura):
        def __init__(self):
            super().__init__()
            self._ja = False
            create_ok = self.messages.create

            def create(**kw):
                if not self._ja and "thinking" in kw:
                    self._ja = True
                    raise ValueError("thinking is not supported on this model")
                return create_ok(**kw)

            self.messages.create = create

    llm._NO_THINK.discard("modelo-arcaico")
    cli = _ClienteQueRejeita()
    resp = llm._create(cli, model="modelo-arcaico", max_tokens=100,
                       messages=[{"role": "user", "content": "x"}])
    assert resp.stop_reason == "end_turn"       # a resposta saiu
    assert "modelo-arcaico" in llm._NO_THINK    # e o modelo foi memorizado
    assert "thinking" not in cli.kwargs[-1]     # segunda tentativa sem o parâmetro
