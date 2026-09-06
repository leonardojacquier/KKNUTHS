"""Resultado da mão não pode ser vendido como custo da decisão.

Achado da auditoria de poker (07/08), o mais grave dela: a coluna
`hand_analysis.ev_loss` — nome que promete "EV perdido" — guarda `net_bb`,
o RESULTADO líquido da mão (repository.py). Conferido no banco:

    ev_loss = +40.79  -> o herói GANHOU o pote
    ev_loss = -12.54  -> perdeu (e o call de KK estava CERTO)

Esse número era colado no fim de toda lição do dia como "(custou X bb)".
Resultado: uma lição de uma mão GANHA anunciada como "custou 37,4bb", e um
call correto de KK como "custou 12,5bb". É julgar pela carta que veio — o
pecado que R5 do prompt proíbe em letras maiúsculas — entrando pelo
encanamento em vez de pelo texto do modelo.

O portal sempre chamou de "Resultado", que é honesto. A lição era a única
peça que rebatizava resultado de custo.
"""
from __future__ import annotations

import inspect

from app.bot.licao_envio import texto_da_licao

LICAO = {
    "titulo": "Trinca em board molhado: apostar por valor",
    "spot": "Você floppa trinca num board com flush draw.",
    "licao": "Dar check nas três streets deixa ~6bb de valor na mesa contra "
             "o range que paga duas apostas.",
    "ev_bb": -37.4,          # na verdade o RESULTADO, e a mão foi GANHA
    "categoria": "flop",
}


def test_a_licao_nao_anuncia_resultado_como_custo():
    txt = texto_da_licao(LICAO)
    assert "custou" not in txt, "resultado voltou a ser vendido como custo"
    assert "rendeu" not in txt
    assert "37.4" not in txt and "37,4" not in txt


def test_a_licao_continua_entregando_o_conteudo():
    """Tirar a mentira não pode ter levado a lição junto."""
    txt = texto_da_licao(LICAO)
    assert LICAO["titulo"] in txt
    assert LICAO["spot"] in txt
    assert LICAO["licao"] in txt
    # o número que PROVA a lição vem no texto dela (exigido pelo destilador)
    assert "6bb" in txt


def test_mao_ganha_nao_vira_licao_de_prejuizo():
    """O caso exato do banco: +40.8bb de resultado numa mão vencida."""
    ganha = dict(LICAO, ev_bb=40.79)
    txt = texto_da_licao(ganha)
    assert "rendeu" not in txt and "40.8" not in txt


def test_o_encanamento_esta_documentado_onde_engana():
    """O nome da coluna é a armadilha; quem editar tem que ver o aviso."""
    from app.db import repository

    fonte = inspect.getsource(repository.Repository.save_hand_analysis)
    assert "RESULTADO líquido da mão" in fonte
    assert "decisoes_por_street.ev_call_bb" in fonte, \
        "o aviso tem que dizer onde ESTÁ o EV de decisão de verdade"


def test_o_portal_chama_de_resultado_e_nao_de_ev():
    """O portal sempre acertou o rótulo — travar para não regredir junto."""
    from app.api import admin

    fonte = inspect.getsource(admin)
    assert "<th>Resultado</th>" in fonte
    assert "resultado <b>" in fonte
    # e nunca rotular esse campo como EV/custo
    assert "EV perdido" not in fonte and "custou" not in fonte
