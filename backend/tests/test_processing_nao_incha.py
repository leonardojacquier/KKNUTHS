"""`processing.py` chegou a 3.870 linhas com 84 funções de topo.

Ele fala com o Telegram, com o banco, com o LLM, desenha imagem, calcula
equity, monta teclado e escreve prosa. Ninguém lê esse arquivo inteiro — e
foi dentro dele que quase todo defeito desta semana morou.

O primeiro lote saiu para módulos próprios: `leitura_da_mao` (andar pelas
ruas, nomear ação, formatar) e `menus` (os teclados). Foram escolhidos por
MEDIÇÃO, não por gosto — uma varredura de AST mostrou que essas funções não
dependem de mais nada do módulo, então mover não podia criar ciclo de
importação. O resto do arquivo continua importando delas pelo nome de
sempre, porque `processing` reexporta: nenhum call site precisou mudar.

O que este teste protege não é o tamanho de hoje: é a DIREÇÃO. Um arquivo
assim não cresce por decisão, cresce um parágrafo por vez.
"""
from __future__ import annotations

import ast
from pathlib import Path

_APP = Path(__file__).parent.parent / "app"

# teto = onde ficou depois do 1º lote, com folga curta. Baixar quando sair
# outro lote; subir só com um motivo escrito aqui.
_TETO_LINHAS = 3600
_TETO_FUNCOES = 80


def _fonte(nome: str) -> str:
    return (_APP / "bot" / nome).read_text()


def test_o_processing_nao_volta_a_crescer():
    n = len(_fonte("processing.py").splitlines())
    assert n <= _TETO_LINHAS, (
        f"processing.py está com {n} linhas (teto {_TETO_LINHAS}). "
        "Se a função nova é pura, ela provavelmente pertence a "
        "leitura_da_mao.py, menus.py ou a um módulo novo.")


def test_o_numero_de_funcoes_de_topo_tambem_tem_freio():
    t = ast.parse(_fonte("processing.py"))
    funcs = [n for n in t.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert len(funcs) <= _TETO_FUNCOES, (
        f"{len(funcs)} funções de topo — o arquivo virou um depósito")


def test_os_modulos_extraidos_continuam_folha():
    """A propriedade que TORNOU o corte seguro: eles não importam de volta.
    Se um dia `leitura_da_mao` precisar do `processing`, o ciclo aparece e o
    import quebra no ar, em produção, não aqui."""
    for nome in ("leitura_da_mao.py", "menus.py"):
        fonte = _fonte(nome)
        assert "from app.bot.processing" not in fonte, \
            f"{nome} importa de volta o processing — isso é ciclo"
        assert "import app.bot.processing" not in fonte, nome


def test_quem_importava_do_processing_continua_importando():
    """Reexportar não é elegância: é o que permitiu mover 291 linhas sem
    tocar em nenhum call site."""
    from app.bot import processing

    for nome in ("_walk_hand", "_preflop_summary", "_pretty_cards", "_fmt_bb",
                 "_seats_at_decision", "_mark_aggressor", "_decision_aggressor",
                 "_describe_safe", "action_menu_rows", "size_menu_rows",
                 "sizing_amounts", "drill_action", "botoes_pos_treino"):
        assert hasattr(processing, nome), \
            f"{nome} sumiu de processing — quem importava de lá quebrou"


def test_as_funcoes_movidas_continuam_funcionando():
    """Mover não pode mudar comportamento — o ponto do lote ser só folha."""
    from app.bot.leitura_da_mao import _fmt_bb, _pretty_cards
    from app.bot.menus import action_menu_rows, botoes_pos_treino

    assert _pretty_cards(["Ah", "Kd"]).strip()
    assert _fmt_bb(3.0) and _fmt_bb(2.5)
    linhas = action_menu_rows(10.0, 3.0, 40.0, "drill")
    assert linhas and all(isinstance(b, dict) for row in linhas for b in row)
    assert botoes_pos_treino(True)[0][0]["callback_data"] == "go:enviar"
