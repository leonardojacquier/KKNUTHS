"""O guarda da voz está LIGADO nos dois caminhos que falam com o aluno.

Teste por AST, não por substring do código-fonte. O METODO §8 documenta o
caso: um teste que comparava texto do fonte protegia um portão que podia
já nem existir, e invertendo a condição em produção os testes passavam.
"""
from __future__ import annotations

import ast
import pathlib


def _fonte() -> ast.Module:
    p = pathlib.Path(__file__).resolve().parents[1] / "app/bot/processing.py"
    return ast.parse(p.read_text(encoding="utf-8"))


def _nomes_importados(arvore: ast.Module) -> set[str]:
    achados = set()
    for node in ast.walk(arvore):
        if isinstance(node, ast.ImportFrom) and node.module == "app.bot.guarda_voz":
            achados.update(a.name for a in node.names)
    return achados


def test_o_guarda_da_voz_e_importado_no_processing():
    assert {"limpar", "problemas_de_voz"} <= _nomes_importados(_fonte()), \
        "guarda_voz não é usado em processing.py — o guarda existe e não roda"


def test_limpar_e_chamado_pelo_menos_duas_vezes():
    """Um caminho é a análise, o outro é a conversa. Ligar só num deles
    deixa metade do produto falando do jeito antigo."""
    chamadas = [n for n in ast.walk(_fonte())
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == "limpar"]
    assert len(chamadas) >= 2, f"limpar() chamado {len(chamadas)}x, esperado 2"
