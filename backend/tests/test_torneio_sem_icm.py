"""Torneio sem ICM é cash game com blind subindo.

Auditoria de poker (07/08): das 25 análises de torneio mais recentes, ZERO
mencionam bolha, ICM, bubble factor ou bounty. Todo conselho de all-in saiu
em chip-EV puro — e na bolha e na mesa final, que é onde o dinheiro do MTT
está, conselho de chip-EV é ativamente perdedor.

Não é falta de motor: icm.py, pko.py e o `bf` do allin_engine funcionam. O
buraco é de FLUXO — `bf` só liga se o aluno digitar a premiação, e o bot
nunca pergunta. A regra C3 do prompt é passiva; nada agia quando os payouts
faltavam, então o default silencioso era bf=1.0 em 100% das análises.

O conserto NÃO é campo obrigatório no upload: o funil já está quebrado (8 de
10 alunos nunca mandaram uma mão) e formulário na frente piora. É medir o
que a bolha mudaria, com o motor que já existe, e entregar o número pronto.
"""
from __future__ import annotations

import pytest

from app.analysis.torneio import BF_BOLHA_TIPICO, situacao_icm

# a mão real do banco: SB paga o all-in do CO com 8.4bb efetivo
SPOT = {
    "format": "tournament", "hero_pos": "SB", "effective_bb": 8.4,
    "spots": [{"street": "preflop", "posicao": "SB", "acao": "call all-in",
               "vilao_pos": "CO"}],
}


def test_mede_o_que_a_bolha_mudaria_em_numero():
    """"O ICM importa" é palestra. "Esse call vira fold na bolha" é conselho."""
    r = situacao_icm(SPOT)
    assert r is not None
    assert r["range_chip_ev_pct"] > r["range_com_bolha_pct"], \
        "a bolha tem que APERTAR o range de call"
    # o efeito medido no spot real: ~36% -> ~14%
    assert r["range_chip_ev_pct"] == pytest.approx(35.5, abs=3)
    assert r["range_com_bolha_pct"] == pytest.approx(13.6, abs=3)
    assert r["quantas_somem"] > 20
    # e são exatamente as mãos que o bot vinha mandando pagar
    assert any(m.startswith("A") for m in r["maos_que_somem"])


def test_a_instrucao_pede_UMA_linha():
    """O auditor de linguagem já achou redundância em 4 parágrafos por
    análise. ICM não pode virar mais um."""
    ins = situacao_icm(SPOT)["instrucao"]
    assert "UMA linha" in ins
    assert "não é aula de ICM" in ins or "não um parágrafo" in ins
    # e os números vão prontos, para o coach não recalcular de cabeça
    assert "%" in ins


def test_com_a_premiacao_conhecida_nao_ha_o_que_avisar():
    """Aí o ICM sai de verdade (Malmuth-Harville), não por referência."""
    assert situacao_icm(SPOT, {"valores": [500, 300, 200]}) is None


def test_nao_dispara_fora_de_torneio_nem_sem_all_in():
    assert situacao_icm({**SPOT, "format": "cash"}) is None
    assert situacao_icm({**SPOT, "spots": [{"acao": "c-bet 3bb"}]}) is None
    assert situacao_icm({}) is None
    assert situacao_icm(None) is None


def test_stack_fundo_nao_e_spot_de_jam_fold():
    """Com 60bb a conversa é outra — o aviso seria ruído."""
    assert situacao_icm({**SPOT, "effective_bb": 60}) is None


def test_bf_de_referencia_e_de_bolha_de_verdade():
    """1.6 é bolha típica de MTT de clube. Acima de 2 o solver degenera
    (achado da auditoria de matemática) e não serve nem de referência."""
    assert 1.3 <= BF_BOLHA_TIPICO <= 1.8


def test_esta_ligado_na_analise():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "situacao_icm" in fonte
    assert "falta_icm" in fonte


def test_o_prompt_manda_usar_e_nao_inventar():
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm)
    assert "C3b" in fonte
    assert "falta_icm" in fonte
    # sem o campo no contexto, o coach não pode puxar o assunto sozinho
    # a frase é quebrada em literais no fonte; confere os pedaços
    assert "não invente o " in fonte and "assunto" in fonte
