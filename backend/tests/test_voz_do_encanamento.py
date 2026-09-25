"""O guarda da voz está LIGADO nos dois caminhos que falam com o aluno.

Teste por AST, não por substring do código-fonte. O METODO §8 documenta o
caso: um teste que comparava texto do fonte protegia um portão que podia
já nem existir, e invertendo a condição em produção os testes passavam.

Rodada de correção 1: a lógica que media/corrigia/registrava foi extraída
para `guarda_voz.conferir_e_limpar` (espelhando `guarda_saida.
conferir_e_remediar`), para não empurrar processing.py contra o teto de
linhas vigiado por test_processing_nao_incha.py. Os testes abaixo cobram o
que passou a ser verdade: `conferir_e_limpar` importado e chamado nos dois
caminhos — não mais `limpar`/`problemas_de_voz` direto em processing.py.
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
    assert "conferir_e_limpar" in _nomes_importados(_fonte()), \
        "guarda_voz não é usado em processing.py — o guarda existe e não roda"


def test_conferir_e_limpar_e_chamado_pelo_menos_duas_vezes():
    """Um caminho é a análise, o outro é a conversa. Ligar só num deles
    deixa metade do produto falando do jeito antigo."""
    chamadas = [n for n in ast.walk(_fonte())
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "conferir_e_limpar"]
    assert len(chamadas) >= 2, \
        f"conferir_e_limpar() chamado {len(chamadas)}x, esperado 2"


def test_toda_chamada_do_guarda_da_voz_declara_a_populacao():
    """A POPULAÇÃO do evento é carimbada na origem, e a origem é aqui.

    Esta chamada roda ANTES do `if not is_tournament` que separa mão de
    torneio, então sem `onde` o relatório de torneio virava evento
    indistinguível de análise de mão — e ia parar no numerador de uma taxa
    cujo denominador só conta análise de mão com placar. Executado pela
    re-revisão: "6 de 12 análises = 50%" com a verdade em 0%, e 225% num dia
    plausível. Um chamador que esquece o `onde` recria o defeito inteiro, e
    o juiz não tem como perceber.
    """
    chamadas = [n for n in ast.walk(_fonte())
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "conferir_e_limpar"]
    ondes = [next((k.value for k in c.keywords if k.arg == "onde"), None)
             for c in chamadas]
    assert all(o is not None for o in ondes), \
        "chamada de conferir_e_limpar sem `onde=`: o evento sai sem população"

    # e o caminho da análise decide o rótulo POR is_tournament — carimbar
    # "analise" fixo ali é o mesmo defeito com um rótulo bonito por cima
    nomes = {n.id for o in ondes for n in ast.walk(o)
             if isinstance(n, ast.Name)}
    assert "is_tournament" in nomes, \
        "nenhuma chamada distingue torneio de análise de mão"
    literais = {n.value for o in ondes for n in ast.walk(o)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert {"torneio", "analise", "conversa"} <= literais, \
        f"as três populações da origem não são todas nomeadas: {literais}"
