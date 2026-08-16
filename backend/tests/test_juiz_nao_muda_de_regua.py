"""O juiz ganha contadores novos, e a NOTA continua a mesma régua."""
from __future__ import annotations

import ast
import inspect
import pathlib

import scripts.output_judge as juiz

_FONTE = (pathlib.Path(__file__).resolve().parents[1]
          / "scripts/output_judge.py").read_text(encoding="utf-8")


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


# --- R2: a linha impressa. Agora RENDERIZADA, não lida do código-fonte ----
#
# Era f-string dentro de main(), que só roda com Supabase — por isso os
# testes liam `inspect.getsource(juiz.main)`, e por isso a re-revisão final
# achou dois defeitos de REPORTE que nenhum teste podia pegar. A montagem
# saiu para `linha_da_voz(cru, voz)`, função pura: daqui em diante o que se
# afirma é o texto que o dono lê.

_CRU = {"eventos": 10, "corrigidas": 3, "em_conversa": 4,
        "com_titulo_fixo": 5, "com_bastidor": 6, "com_bloco_longo": 1,
        "com_autocorrecao": 0}
_VOZ = {"analisadas": 12, "sem_placar_ignoradas": 2, "com_titulo_fixo": 0,
        "com_bastidor": 4, "com_bloco_longo": 1, "com_numero_repetido": 3,
        "chars_pos_placar_medio": 590}


def _lado_do_modelo() -> str:
    return juiz.linha_da_voz(_CRU, _VOZ).strip().splitlines()[0]


def _lado_do_aluno() -> str:
    return juiz.linha_da_voz(_CRU, _VOZ).strip().splitlines()[1]


def _main_ast() -> ast.FunctionDef:
    return [n for n in ast.walk(ast.parse(_FONTE))
            if isinstance(n, ast.FunctionDef) and n.name == "main"][0]


def test_o_juiz_le_bot_events_de_verdade_e_nao_uma_lista_vazia():
    """R3 — o buraco de cobertura do próprio C1, executado pela re-revisão
    final: trocar a consulta por `eventos_voz = []` reinstala a cegueira que
    o C1 existe para curar (o contador do PROMPT devolvendo zero para
    sempre, com rótulo honesto na tela) e os 22 testes de juiz/voz ficavam
    VERDES. Os testes AST prendiam a CHAMADA a `resumo_dos_eventos_de_voz`,
    nunca a query que a alimenta.

    Aqui a corrente inteira é presa por AST: consulta a `bot_events`
    filtrando os dois eventos de voz -> laço sobre `eventos_voz` -> o mesmo
    nome que entra em `resumo_dos_eventos_de_voz`.
    """
    main_func = _main_ast()

    atribuicoes = [n for n in ast.walk(main_func) if isinstance(n, ast.Assign)
                   and any(getattr(a, "id", None) == "eventos_voz"
                           for a in n.targets)]
    assert len(atribuicoes) == 1, \
        "eventos_voz não é atribuído exatamente uma vez em main()"

    chamadas: dict[str, list[ast.Call]] = {}
    for n in ast.walk(atribuicoes[0].value):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            chamadas.setdefault(n.func.attr, []).append(n)
    assert "execute" in chamadas, \
        "eventos_voz não vem de uma consulta — o C1 voltou a ser cego"
    tabelas = [a.value for c in chamadas.get("table", []) for a in c.args
               if isinstance(a, ast.Constant)]
    assert tabelas == ["bot_events"], \
        f"os eventos de voz saíram de bot_events: {tabelas}"
    eventos = sorted(e.value for c in chamadas.get("in_", []) for a in c.args
                     if isinstance(a, ast.List) for e in a.elts
                     if isinstance(e, ast.Constant))
    assert eventos == ["voz_corrigida", "voz_medida"], \
        f"o filtro de evento mudou e o contador do prompt muda junto: {eventos}"

    # e o resultado da consulta é MESMO o que alimenta o contador
    chamada = [n for n in ast.walk(main_func)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "resumo_dos_eventos_de_voz"][0]
    assert len(chamada.args) == 1 and isinstance(chamada.args[0], ast.Name), \
        "resumo_dos_eventos_de_voz recebe um literal — a consulta é decorativa"
    alvo = chamada.args[0].id
    lacos = [n for n in ast.walk(main_func) if isinstance(n, ast.For)
             and isinstance(n.iter, ast.Name) and n.iter.id == "eventos_voz"]
    assert lacos, "eventos_voz é consultado e descartado"
    assert [n for laco in lacos for n in ast.walk(laco)
            if isinstance(n, ast.Attribute) and n.attr == "append"
            and isinstance(n.value, ast.Name) and n.value.id == alvo], \
        f"o laço sobre eventos_voz não alimenta {alvo}"


def test_a_linha_impressa_distingue_o_modelo_do_aluno():
    """As duas leituras medem coisas diferentes e a linha tem que dizer
    qual é qual — senão o dono soma numerador de uma com denominador da
    outra, que é o erro que a spec §9 documenta."""
    modelo, aluno = _lado_do_modelo(), _lado_do_aluno()
    assert "MODELO" in modelo and "antes da limpeza" in modelo
    assert "ALUNO" in aluno and "depois da limpeza" in aluno
    # e diz o que cada lado MEDE, que é a pergunta que o dono está fazendo
    assert "PROMPT" in modelo, "a leitura do modelo não diz que mede o prompt"
    assert "GUARDA" in aluno, "a leitura do aluno não diz que mede o guarda"


def test_a_leitura_do_modelo_tem_denominador_e_separa_a_conversa():
    """R2(a) — a linha imprimia numerador puro ("10 respostas tiveram algo a
    apontar") ao lado de uma base que é TAXA (48% / 34%, spec §9), e o
    numerador somava análise com conversa: `em_conversa` era calculado e
    jogado fora na hora de imprimir. 10 eventos − 4 de conversa = 6 do lado
    de análise, sobre as 12 análises da MESMA janela = 50%."""
    modelo = _lado_do_modelo()
    assert "6 de 12 análises" in modelo, modelo
    assert "= 50%" in modelo, "a leitura continua sem taxa comparável à base"
    assert "+4 em conversa" in modelo, \
        "em_conversa continua calculado e jogado fora"


def test_a_leitura_do_modelo_nao_inventa_taxa_sem_denominador():
    """Dia sem análise de mão na janela: dividir por zero derruba o juiz
    inteiro, e imprimir '0%' mentiria. Degrada dizendo que não tem base."""
    vazio = {**_VOZ, "analisadas": 0}
    modelo = juiz.linha_da_voz(_CRU, vazio).strip().splitlines()[0]
    assert "= sem base hoje;" in modelo, modelo
    assert "6 de 0 análises" in modelo, "o numerador some junto com a base"


def test_a_leitura_do_aluno_mostra_os_tres_contadores_do_lado_dela():
    """R2(b) — estrago novo da onda anterior: o conserto do C1 moveu
    `título fixo · bastidor · bloco longo` para a leitura do MODELO (certo,
    é ela que mede o prompt) e o lado do ALUNO ficou só com a média do
    bloco. E o lado do aluno virou informativo exatamente agora: o I1/R1 fez
    o guarda RECUSAR apagar a frase de bastidor que carrega a única conta,
    então `com_bastidor` entregue deixou de tender a zero. A única métrica
    que a onda piorou de propósito era a que tinha saído da tela do dono."""
    aluno = _lado_do_aluno()
    assert "título fixo 0" in aluno
    assert "bastidor entregue 4" in aluno, \
        "o bastidor ENTREGUE (I1/R1) continua invisível para o dono"
    assert "bloco longo 1" in aluno
    assert "pós-placar médio 590 chars" in aluno


def test_os_contadores_dos_dois_lados_nao_se_confundem():
    """Os mesmos quatro nomes existem nos dois dicionários com valores
    diferentes. Ler o dict errado é o modo de falha silencioso desta linha —
    aqui `com_bastidor` é 6 no modelo e 4 no aluno."""
    modelo, aluno = _lado_do_modelo(), _lado_do_aluno()
    assert "bastidor 6" in modelo and "bastidor entregue 4" in aluno
    assert "título fixo 5" in modelo and "título fixo 0" in aluno
    assert "bastidor entregue 6" not in aluno, "o lado do aluno leu o `cru`"
    assert "título fixo 0 ·" not in modelo, "o lado do modelo leu o `voz`"


def test_main_ainda_imprime_a_linha_da_voz():
    """A extração não pode virar código morto: se main() parar de chamar
    `linha_da_voz`, os testes acima ficam verdes sobre uma função que
    ninguém usa — que é a definição de teste decorativo."""
    main_func = [n for n in ast.walk(ast.parse(_FONTE))
                 if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    chamadas = [n for n in ast.walk(main_func)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "linha_da_voz"]
    assert len(chamadas) == 1, "main() não monta mais a linha de voz"
    assert "linha_voz" in inspect.getsource(juiz.main), \
        "a linha foi montada e não entra na mensagem"


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
    (740 -> 700) onde a população real diz regressão (678 -> 700).

    Agora sobre a linha RENDERIZADA, não sobre o código-fonte de main()."""
    impressa = juiz.linha_da_voz(_CRU, _VOZ)
    assert "base 15/08: 678" in impressa
    assert "740" not in impressa, "o número que a spec §9 provou errado voltou"
    # as duas bases de taxa da linha 🗣 são as da §9, não as contaminadas
    assert "título fixo 48%" in impressa and "bastidor 34%" in impressa
    for errado in ("25%", "23%", "58%"):
        assert errado not in impressa, \
            f"a base contaminada {errado} voltou para a tela do dono"
