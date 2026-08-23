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
    for nome in ("leitura_da_mao.py", "menus.py", "storyboard.py",
                 "repeticao.py", "memoria_do_processo.py",
                 "link_do_clube.py"):
        fonte = _fonte(nome)
        assert "from app.bot.processing" not in fonte, \
            f"{nome} importa de volta o processing — isso é ciclo"
        assert "import app.bot.processing" not in fonte, nome


def test_modulo_extraido_nao_deixa_NOME_LIVRE_para_tras():
    """A extração de 09/08 quebrou em produção por isto: minha análise de AST
    olhou funções e globais do módulo de origem e NÃO olhou os imports dele.

    `storyboard_spot_from_drill` chamava `drill_action` e `sizing_amounts`,
    que o `processing` importa de `menus` no topo. No módulo novo os dois
    viraram nome livre — `NameError` na primeira chamada, e os testes de
    drill vermelhos.

    Este teste faz a conta que faltou: todo nome CARREGADO num módulo
    extraído tem que estar definido ou importado ali dentro.
    """
    import ast
    import builtins

    for nome in ("leitura_da_mao.py", "menus.py", "storyboard.py",
                 "repeticao.py", "memoria_do_processo.py",
                 "link_do_clube.py"):
        arvore = ast.parse(_fonte(nome))
        definidos = set(dir(builtins)) | {"annotations", "__name__", "__doc__"}
        for n in ast.walk(arvore):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
                definidos.add(n.name)
            elif isinstance(n, ast.arg):
                definidos.add(n.arg)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                definidos.add(n.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    definidos.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, ast.ExceptHandler) and n.name:
                definidos.add(n.name)
            elif isinstance(n, ast.comprehension):
                for alvo in ast.walk(n.target):
                    if isinstance(alvo, ast.Name):
                        definidos.add(alvo.id)
        # ANOTAÇÃO NÃO É USO. Com `from __future__ import annotations` a
        # anotação vira string e nunca é avaliada — `CanonicalHand` só no
        # `-> CanonicalHand` de leitura_da_mao.py não quebra nada. Contar
        # isso daria falso positivo e o teste seria desligado na primeira
        # semana.
        anotacoes = set()
        for n in ast.walk(arvore):
            alvos = []
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                alvos = [n.returns]
            elif isinstance(n, ast.arg):
                alvos = [n.annotation]
            elif isinstance(n, ast.AnnAssign):
                alvos = [n.annotation]
            for a in alvos:
                if a is None:
                    continue
                anotacoes |= {x.id for x in ast.walk(a)
                              if isinstance(x, ast.Name)}

        livres = {n.id for n in ast.walk(arvore)
                  if isinstance(n, ast.Name)
                  and isinstance(n.ctx, ast.Load)} - definidos - anotacoes
        assert not livres, (
            f"{nome} usa nome que não define nem importa: {sorted(livres)}")


def test_quem_importava_do_processing_continua_importando():
    """Reexportar não é elegância: é o que permitiu mover 291 linhas sem
    tocar em nenhum call site."""
    from app.bot import processing

    for nome in ("_walk_hand", "_preflop_summary", "_pretty_cards", "_fmt_bb",
                 "_seats_at_decision", "_mark_aggressor", "_decision_aggressor",
                 "_describe_safe", "action_menu_rows", "size_menu_rows",
                 "sizing_amounts", "drill_action", "botoes_pos_treino",
                 "replay_link_info", "replay_fallback_text"):
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
