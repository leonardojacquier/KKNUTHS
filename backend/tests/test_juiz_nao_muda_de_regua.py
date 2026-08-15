"""O juiz ganha contadores novos, e a NOTA continua a mesma régua."""
from __future__ import annotations

import ast
import inspect
import pathlib

import scripts.output_judge as juiz


def test_a_nota_nao_passou_a_considerar_voz():
    """Se problemas_de_voz entrar em _nota_uma ou judge_answer, a série de
    7 dias muda de significado no meio e o antes/depois perde o sentido."""
    for fn in (juiz.judge_answer, juiz._nota_uma):
        assert "problemas_de_voz" not in inspect.getsource(fn), \
            f"{fn.__name__} passou a medir voz — a régua da nota mudou"


def test_o_juiz_conta_voz_em_algum_lugar():
    """Por AST, não por substring: prova que main() de fato chama resumo_de_voz().

    Teste que compara texto do código-fonte protege portões que podem já nem
    existir; só AST garante que a chamada real está lá."""
    # Parse do arquivo output_judge.py
    p = pathlib.Path(__file__).resolve().parents[1] / "scripts/output_judge.py"
    arvore = ast.parse(p.read_text(encoding="utf-8"))

    # Encontra a função main()
    funcoes = [n for n in ast.walk(arvore)
               if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert funcoes, "Função main() não encontrada"

    # Procura por chamadas a resumo_de_voz() dentro de main()
    main_func = funcoes[0]
    chamadas = [n for n in ast.walk(main_func)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "resumo_de_voz"]
    assert len(chamadas) >= 1, \
        "resumo_de_voz() não é chamado em main() — contadores não rodam"


def test_contadores_de_voz_e_funcao_pura_testavel():
    linha = juiz.resumo_de_voz([
        "✅ Você jogou bem\n\nA conta que mais pesa: com 12bb é jam.",
        "✅ Você jogou bem\n\nCom 12bb é jam.",
    ])
    assert linha["analisadas"] == 2
    assert linha["com_titulo_fixo"] == 1
