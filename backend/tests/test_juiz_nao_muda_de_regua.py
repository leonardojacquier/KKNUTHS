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


_COM_PLACAR = ("✅ Você jogou bem — set flopado\n"
               "✅ *Flop* 5♥8♠6♦ — set de 6 e jam de 16.9bb.\n\n")


def test_contadores_de_voz_e_funcao_pura_testavel():
    linha = juiz.resumo_de_voz([
        _COM_PLACAR + "A conta que mais pesa: com 12bb é jam.",
        _COM_PLACAR + "Com 12bb é jam.",
    ])
    assert linha["analisadas"] == 2
    assert linha["com_titulo_fixo"] == 1


# --- C1: o juiz mede o que o MODELO escreveu, não o que o guarda deixou ---


def test_o_juiz_le_os_eventos_de_voz_e_nao_so_o_texto_gravado():
    """C1 — o guarda LIMPA antes de gravar (processing.py:577 antes de :663),
    e o juiz media o texto GRAVADO. Título fixo e bastidor iam a ~0 por
    construção: o bloco R3/R7/V4 do prompt poderia ser um no-op completo e a
    linha do juiz seria idêntica. Os eventos voz_corrigida/voz_medida já
    gravam `problemas` medidos ANTES da limpeza — ninguém os lia.
    """
    cru = juiz.resumo_dos_eventos_de_voz([
        {"feitos": ["título fixo removido"],
         "problemas": ["título fixo 'Resumo:'",
                       "bastidor de busca narrado ao aluno"]},
        {"feitos": [], "problemas": ["bloco pós-placar longo (1200 chars; "
                                     "teto 800)"], "onde": "conversa"},
        "detalhe que veio como string quebrada",
    ])
    assert cru == {"eventos": 2, "corrigidas": 1, "em_conversa": 1,
                   "com_titulo_fixo": 1, "com_bastidor": 1,
                   "com_bloco_longo": 1, "com_autocorrecao": 0}


def test_o_juiz_consulta_os_eventos_de_voz_em_main():
    """Por AST: prova que main() chama resumo_dos_eventos_de_voz(). Sem esta
    chamada, o contador do prompt não existe — e é ele que o merge espera."""
    p = pathlib.Path(__file__).resolve().parents[1] / "scripts/output_judge.py"
    main_func = [n for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
                 if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    chamadas = [n for n in ast.walk(main_func)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "resumo_dos_eventos_de_voz"]
    assert len(chamadas) == 1, \
        "main() não agrega os eventos de voz — o juiz voltou a medir só o " \
        "texto já limpo"


def test_a_linha_impressa_distingue_o_modelo_do_aluno():
    """As duas leituras medem coisas diferentes e a linha tem que dizer
    qual é qual — senão o dono soma numerador de uma com denominador da
    outra, que é o erro que a spec §9 documenta."""
    fonte = inspect.getsource(juiz.main)
    assert "antes da limpeza" in fonte and "depois da limpeza" in fonte


# --- I4: a linha diária compara populações comparáveis --------------------


def test_relatorio_de_torneio_nao_entra_na_media_do_bloco():
    """I4 — `resumo_de_voz` não filtrava torneio nem decisão única. Nesses
    textos não existe placar, então `bloco_pos_placar` devolve TUDO o que vem
    depois do selo do R1: um relatório de ~1200 chars vira "bloco" de 1199 e
    é marcado longo. Executado contra o código antigo: média 1359 chars."""
    torneio = "✅ Torneio ok — bom ITM\n\n" + ("palavra " * 170)
    linha = juiz.resumo_de_voz([torneio, _COM_PLACAR + "Com 12bb é jam."])
    assert linha["analisadas"] == 1
    assert linha["sem_placar_ignoradas"] == 1
    assert linha["com_bloco_longo"] == 0
    assert linha["chars_pos_placar_medio"] == len("Com 12bb é jam.")


def test_a_populacao_dos_contadores_exclui_torneio_e_follow_up():
    """Mesmo filtro do comparador (`mistakes is not null`): torneio nunca
    grava "spots", análise de mão sempre grava a lista — mão bem jogada sai
    com `mistakes: []`, que NÃO é NULL e continua na conta."""
    textos = juiz.analises_de_mao([
        {"summary": "mão com erro", "mistakes": [{"spot": "river"}]},
        {"summary": "mão bem jogada", "mistakes": []},
        {"summary": "relatório de torneio", "mistakes": None},
        {"summary": "[Follow-up] pergunta avulsa", "mistakes": []},
        {"summary": "", "mistakes": []},
    ])
    assert textos == ["mão com erro", "mão bem jogada"]


def test_a_linha_diaria_cita_a_base_remedida_e_nao_a_errada():
    """A §9 desta mesma branch declarou os 740 medidos sobre população
    contaminada; o valor certo é 678. Imprimir 740 faz o dono ler progresso
    (740 -> 700) onde a população real diz regressão (678 -> 700)."""
    fonte = inspect.getsource(juiz.main)
    assert "base 15/08: 678" in fonte
    assert "740" not in fonte, "o número que a spec §9 provou errado voltou"
