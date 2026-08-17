"""O guarda dos termos: `river` é river, `air` é air — no texto ENTREGUE.

Caso real (16/08, análise que chegou a um aluno, mão 2f227463):

    "você estava na frente a mão inteira — 61% no pré, 60% no flop, 66% no
     turn — e foi o rio que virou tudo"
    "apostar de novo bate contra a fatia de ar do range dele"

O dono, na íntegra: "se é termo do poker não tem que traduzir" — e disse que
já tinha reclamado antes. Regra é pedido; conferência é garantia
(docs/METODO.md): o Conserto 1 pôs `flop/turn/river/air` na TERMOS_REGRA, e
isto aqui é o que confere depois que o modelo escreveu.

MEDIDO no corpus real antes de escrever o guarda (hand_analysis, 45 dias,
só análise de mão: `summary not like '[Follow-up]%'` e `mistakes not null`,
n=227):
  - 'rio' como palavra isolada:  1 análise  (a do caso real; 'Rio de
    Janeiro' aparece 0 vezes)
  - 'ar' como palavra isolada:   3 análises — e as três provam por que "ar"
    não pode ser corrigido cego:
       "é um spot de moeda ao ar"                  -> PORTUGUÊS, não toca
       "o BB tem MUITO ar que não paga a Q"        -> poker, mas fora de
                                                      colocação -> evento
       "bate contra a fatia de ar do range dele"   -> corrige
  - nos últimos 10 dias (n=29), TODOS os outros calques da TERMOS_REGRA
    aparecem 0 vezes; 'rio' e 'ar' são os únicos que ainda escapam.

Os testes daqui são de COMPORTAMENTO: o texto que sai e o evento gravado.
Nenhum toca rede ou LLM.
"""
from __future__ import annotations

import pytest

from app.bot import guarda_termos as gt

# as duas frases reais, como saíram
RIO_REAL = ("Você estava na frente a mão inteira — 61% no pré, 60% no flop, "
            "66% no turn — e foi o rio que virou tudo: o RicoFarah tinha "
            "5♠4♠ e completou a straight.")
AR_REAL = ("Ele te pagou duas vezes (check-call, check-call) — apostar de "
           "novo bate contra a fatia de ar do range dele e ainda pode ser "
           "pago por uma mão pior.")


class _Repo:
    """Repo falso: `enabled=True` porque guarda com repo desligado não grava
    evento nenhum e o teste passaria sem medir nada."""

    enabled = True

    def __init__(self):
        self.events: list[tuple] = []

    def log_event(self, telegram_id, username, event, detail=None):
        self.events.append((event, detail or {}))

    def evento(self, nome):
        for ev, det in self.events:
            if ev == nome:
                return det
        return None


@pytest.fixture
def repo(monkeypatch):
    r = _Repo()
    import app.db

    monkeypatch.setattr(app.db, "get_repository", lambda: r)
    return r


# ---------------------------------------------------------------- rio -----

def test_a_frase_real_do_rio_vira_river():
    novo, trocas, _amb = gt.conferir(RIO_REAL)
    assert "foi o river que virou tudo" in novo
    assert "o rio " not in novo
    assert trocas, "corrigiu o texto e não disse o que fez"
    # o resto da frase é intocável: o guarda mexe no termo, não na prosa
    assert "61% no pré, 60% no flop, 66% no turn" in novo
    assert "completou a straight" in novo


def test_rio_respeita_a_caixa_do_contexto():
    """'Rio veio K♠' abre linha de placar — devolver 'river' minúsculo ali
    deixa a frase torta de um jeito que o aluno percebe."""
    assert gt.conferir("Rio veio K♠.")[0] == "River veio K♠."
    assert gt.conferir("no rio ele apostou")[0] == "no river ele apostou"
    assert gt.conferir("O RIO MUDOU TUDO")[0] == "O RIVER MUDOU TUDO"


@pytest.mark.parametrize("frase", [
    "Ele mora no Rio de Janeiro e joga no clube de lá.",
    "Subiu de Rio Grande direto pro high stakes.",
])
def test_toponimo_com_rio_nao_vira_river(frase):
    novo, trocas, amb = gt.conferir(frase)
    assert novo == frase, "estragou nome de lugar"
    assert not trocas


@pytest.mark.parametrize("frase", [
    "Esse é o critério que separa call de fold.",
    "Foi um erro sério no próprio flop.",
    "Ele encostou no meio-rio do range dele.",
    "O Riozinho do clube paga tudo.",
])
def test_rio_dentro_de_palavra_maior_fica_intacto(frase):
    assert gt.conferir(frase)[0] == frase


# ----------------------------------------------------------------- ar -----

def test_a_frase_real_do_ar_vira_air():
    novo, trocas, _amb = gt.conferir(AR_REAL)
    assert "contra a fatia de air do range dele" in novo
    assert trocas
    assert "ainda pode ser pago por uma mão pior" in novo


@pytest.mark.parametrize("frase,esperado", [
    ("bate contra a fatia de ar do range dele",
     "bate contra a fatia de air do range dele"),
    ("o range de ar dele é enorme", "o range de air dele é enorme"),
    ("ele paga com mão de ar", "ele paga com mão de air"),
    ("ele apostou com mãos de ar", "ele apostou com mãos de air"),
    ("essa linha é puro ar", "essa linha é puro air"),
    ("ele tinha só ar ali", "ele tinha só air ali"),
    ("ele te paga com ar.", "ele te paga com air."),
])
def test_colocacao_de_poker_inequivoca_e_corrigida(frase, esperado):
    assert gt.conferir(frase)[0] == esperado


@pytest.mark.parametrize("frase", [
    "Ele deixou no ar se ia pagar ou não.",
    "É um spot de moeda ao ar.",            # real, 31/07, análise entregue
    "Jogou o torneio ao ar livre.",
    "Ele contou a história com ar de deboche.",
])
def test_portugues_com_ar_nao_e_tocado_nem_vira_evento(frase):
    """A parte difícil da tarefa: "ar" é palavra comum do português.
    Corrigir cego estraga texto BOM, e texto bom estragado custa mais
    confiança do que o calque custa."""
    novo, trocas, ambiguos = gt.conferir(frase)
    assert novo == frase, "o guarda estragou português normal"
    assert not trocas
    assert not ambiguos, (
        "idioma assentado do português não é caso ambíguo — virar evento "
        "aqui polui a medição que o dono vai ler depois")


def test_ar_de_poker_fora_da_colocacao_vira_evento_e_nunca_correcao():
    """Real (14/08): "o BB tem MUITO ar que não paga a Q". É air de poker, e
    mesmo assim não se corrige: nenhuma colocação da lista casa, e inventar
    uma regra nova para caber esta frase é o caminho do falso positivo."""
    frase = "O bet funciona porque o BB tem MUITO ar que não paga a Q."
    novo, trocas, ambiguos = gt.conferir(frase)
    assert novo == frase
    assert not trocas
    assert ambiguos, "não corrigiu e também não deixou medir"
    assert "ar" in ambiguos[0]


# -------------------------------------------------------------- evento ----

def test_o_evento_de_correcao_tem_nome_proprio_e_diz_o_que_trocou(repo):
    saida = gt.conferir_e_registrar(4242, RIO_REAL, username="tester",
                                    onde="analise")
    assert "o river que virou tudo" in saida
    ev = repo.evento("termo_corrigido")
    assert ev, f"corrigiu sem registrar: {repo.events}"
    assert any("river" in t for t in ev["trocas"])
    assert ev["onde"] == "analise"


def test_o_ambiguo_registra_evento_proprio_sem_mexer_no_texto(repo):
    texto = "O bet funciona porque o BB tem MUITO ar que não paga a Q."
    saida = gt.conferir_e_registrar(4242, texto, onde="conversa")
    assert saida == texto
    assert repo.evento("termo_corrigido") is None
    ev = repo.evento("termo_ambiguo")
    assert ev and ev["onde"] == "conversa"


def test_texto_limpo_nao_gera_evento_nenhum(repo):
    limpo = ("✅ Você jogou bem — c-bet no flop\n\nNo river ele deu check "
             "behind e você mostrou top pair.")
    assert gt.conferir_e_registrar(4242, limpo) == limpo
    assert repo.events == [], f"gravou ruído: {repo.events}"


def test_texto_vazio_ou_none_atravessa_sem_quebrar(repo):
    assert gt.conferir_e_registrar(4242, "") == ""
    assert gt.conferir_e_registrar(4242, None) is None
    assert gt.conferir(None) == (None, [], [])
    assert repo.events == []


def test_o_guarda_nao_amplia_o_conserto_para_os_outros_calques():
    """Escopo é decisão, não descuido: a medição mostrou 0 ocorrência dos
    outros calques nos últimos 10 dias, então consertá-los aqui seria
    código sem defeito para justificar. Se um dia entrarem, que entre num
    commit que os mediu."""
    frase = ("Ele fechou a sequência no turn, aumentou pra 6bb com carta "
             "alta e você passou.")
    assert gt.conferir(frase)[0] == frase


# ------------------------------------------------------- ligado de fato ---

def test_o_guarda_roda_no_portao_de_entrega_da_voz(repo):
    """Guarda que não é chamado é código morto.

    O encanamento mora AQUI, no guarda, e não em processing.py: o arquivo
    está a uma linha do teto de `test_processing_nao_incha` e um segundo
    portão custaria 8. `guarda_voz.conferir_e_limpar` já é o último portão
    do texto entregue nos DOIS caminhos (análise, processing.py:583; e
    conversa, :1237), então é por ele que a terminologia entra.
    """
    from app.bot.guarda_voz import conferir_e_limpar

    saida = conferir_e_limpar(4242, RIO_REAL, username="tester",
                              onde="analise")
    assert "o river que virou tudo" in saida
    assert repo.evento("termo_corrigido"), "o portão da entrega não conferiu"
