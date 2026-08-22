"""O manual descreve o produto ou uma lembrança dele?

22/08: o MANUAL.md anunciava "100 análises por mês" quando o código aplicava
50, e não citava /dossie. Os dois são material que circula com o aluno — o
número errado vira reclamação, o comando ausente vira feature que ninguém usa.

Este teste amarra o manual às DUAS fontes de verdade: o catálogo de comandos
(app/bot/catalogo.py, que já é fonte única dos três lugares que listam
comandos) e a constante de cota. Documento e código mudam juntos, ou aqui
falha.
"""
from __future__ import annotations

import pathlib

import pytest

MANUAL = pathlib.Path(__file__).resolve().parents[2] / "MANUAL.md"


def _texto() -> str:
    return MANUAL.read_text(encoding="utf-8")


def _comandos_do_catalogo() -> list[str]:
    from app.bot.catalogo import CATEGORIAS

    return [c.nome for cat in CATEGORIAS for c in cat.comandos]


def test_o_manual_existe_e_nao_ficou_vazio():
    assert MANUAL.exists() and len(_texto()) > 3000


@pytest.mark.parametrize("nome", _comandos_do_catalogo())
def test_todo_comando_do_catalogo_esta_no_manual(nome):
    # com `in` cru, "/dossie" casa dentro de "/dossie-removido" e a mutação
    # passa verde (medido). Fronteira de palavra é o que torna o teste real.
    import re

    assert re.search(rf"/{nome}(?![\w-])", _texto()), (
        f"/{nome} existe no bot e não está no manual — o aluno não descobre "
        "comando que ninguém documentou")


def test_a_cota_do_manual_bate_com_a_que_o_codigo_aplica():
    from app.quota import FREE_MONTHLY_ANALYSES

    texto = _texto()
    assert f"| {FREE_MONTHLY_ANALYSES} |" in texto or \
        f"{FREE_MONTHLY_ANALYSES} análises" in texto, (
        f"o código aplica {FREE_MONTHLY_ANALYSES}/mês e o manual não diz isso")
    # o número velho não pode ter sobrado em lugar nenhum
    assert "100 análises" not in texto


def test_o_manual_promete_o_que_o_produto_entrega():
    """Amarras do que foi construído e o aluno usa."""
    texto = _texto()
    for prometido in ("Link de replay", "botão 🔍", "150", "Por que confiar"):
        assert prometido in texto, f"o manual não cita: {prometido}"
