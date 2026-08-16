"""O juiz ganha contadores novos, e a NOTA continua a mesma régua."""
from __future__ import annotations

import ast
import inspect
import pathlib
import re

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
                       "bastidor de busca narrado ao aluno"],
         "onde": "analise", "com_placar": True},
        {"feitos": [], "problemas": ["bloco pós-placar longo (1200 chars; "
                                     "teto 800)"], "onde": "conversa"},
        "detalhe que veio como string quebrada",
    ])
    assert cru == {"eventos": 2, "corrigidas": 1, "em_conversa": 1,
                   "em_torneio": 0, "de_analise": 1,
                   "em_analise_sem_placar": 0, "sem_rotulo": 0,
                   "com_titulo_fixo": 1, "com_bastidor": 1,
                   "com_bloco_longo": 1, "com_autocorrecao": 0}


def test_cada_evento_de_voz_cai_em_exatamente_uma_populacao():
    """As quatro populações mais o bucket dos eventos anteriores ao carimbo
    têm que FECHAR com o total: se somarem menos, algum evento sumiu da
    tela; se somarem mais, alguém está contado duas vezes e a taxa passa de
    100%. Torneio e análise sem placar entravam no numerador de graça
    porque `conferir_e_limpar` roda antes do `if not is_tournament`."""
    cru = juiz.resumo_dos_eventos_de_voz([
        {"problemas": ["x"], "onde": "analise", "com_placar": True},
        {"problemas": ["x"], "onde": "analise", "com_placar": True},
        {"problemas": ["x"], "onde": "analise", "com_placar": False},
        {"problemas": ["x"], "onde": "torneio", "com_placar": False},
        {"problemas": ["x"], "onde": "conversa"},
        {"problemas": ["x"]},  # gravado antes do carimbo existir
    ])
    assert cru["de_analise"] == 2, "o numerador da taxa mudou de população"
    assert cru["em_analise_sem_placar"] == 1
    assert cru["em_torneio"] == 1
    assert cru["em_conversa"] == 1
    assert cru["sem_rotulo"] == 1, \
        "evento sem carimbo entrou numa população em vez de ficar visível"
    assert (cru["de_analise"] + cru["em_analise_sem_placar"]
            + cru["em_torneio"] + cru["em_conversa"]
            + cru["sem_rotulo"]) == cru["eventos"]


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

_CRU = {"eventos": 10, "corrigidas": 3, "em_conversa": 4, "em_torneio": 0,
        "de_analise": 6, "em_analise_sem_placar": 0, "sem_rotulo": 0,
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


# --- A TAXA 🗣 divide a MESMA população, do guarda até a tela -------------
#
# Os dois cenários abaixo foram EXECUTADOS pela re-revisão contra o código
# anterior e são a razão de este bloco existir. Eles não montam o `detail` na
# mão: mandam os textos do dia pelo `conferir_e_limpar` de produção, com o
# mesmo `onde` que processing.py passa, e leem o que o juiz imprime. É a
# corrente inteira — se o carimbo sair da origem ou o juiz parar de filtrar
# por ele, aqui fica vermelho.

_LIMPA = ("✅ Você jogou bem — set flopado\n"
          "✅ *Flop* 5♥8♠6♦ — set de 6 e jam de 16.9bb.\n\n"
          "Com set em board de draw, empacotar é obrigatório.")
_COM_DEFEITO = ("✅ Você jogou bem — call fácil\n"
                "✅ *Flop* 5♥8♠6♦ — set de 6.\n\n"
                "*A conta que mais pesa:* com 12bb, AK em HJ é jam.")
_TORNEIO = "✅ Torneio ok — bom ITM\n\n" + ("palavra " * 170)
_SEM_PLACAR = "✅ Call certo\n\n" + ("palavra " * 170)


def _dia(monkeypatch, limpas=0, com_defeito=0, torneios=0, sem_placar=0,
         conversas=0) -> str:
    """Um dia de produção inteiro: os textos passam pelo guarda (que grava os
    eventos) e as análises viram linhas de `hand_analysis`. Devolve a linha
    que o dono lê."""
    from app.bot.guarda_voz import conferir_e_limpar

    eventos: list[dict] = []

    class _Repo:
        def log_event(self, telegram_id, username, evento, detalhe=None):
            eventos.append(detalhe)

    monkeypatch.setattr("app.db.get_repository", lambda: _Repo())

    linhas: list[dict] = []
    for texto, n, onde, mistakes in (
            (_LIMPA, limpas, "analise", []),
            (_COM_DEFEITO, com_defeito, "analise", []),
            # torneio: `mistakes` NULL, do mesmo jeito que analyze_tournament grava
            (_TORNEIO, torneios, "torneio", None),
            (_SEM_PLACAR, sem_placar, "analise", []),
            (_SEM_PLACAR, conversas, "conversa", None)):
        for _ in range(n):
            conferir_e_limpar(1, texto, onde=onde)
            if onde != "conversa":
                linhas.append({"summary": texto, "mistakes": mistakes})

    cru = juiz.resumo_dos_eventos_de_voz(eventos)
    voz = juiz.resumo_de_voz(juiz.analises_de_mao(linhas))
    return juiz.linha_da_voz(cru, voz)


def test_dia_de_analises_limpas_com_torneio_e_sem_placar_da_zero(monkeypatch):
    """O cenário EXECUTADO pela re-revisão: 12 análises de mão TODAS limpas,
    4 relatórios de torneio e 2 análises sem placar. A linha imprimia "6 de
    12 análises com algo a apontar = 50%" — os 6 eventos eram os torneios e
    as sem placar, nenhum deles na população do denominador. A verdade é 0%,
    e um dia perfeito era reportado como metade defeituoso."""
    linha = _dia(monkeypatch, limpas=12, torneios=4, sem_placar=2)
    modelo = linha.strip().splitlines()[0]
    assert "0 de 12 análises de mão com placar" in modelo, modelo
    assert "= 0%" in modelo, modelo
    assert "+4 em torneio" in modelo and "+2 análise sem placar" in modelo, \
        "as populações à parte sumiram da tela em vez de sair do numerador"


def test_a_taxa_da_voz_nunca_passa_de_cem_por_cento(monkeypatch):
    """O outro cenário executado: "9 de 4 análises = 225%". Uma razão acima
    de 100% é a forma VISÍVEL de numerador e denominador virem de populações
    diferentes — o mesmo erro que a spec §9 documenta e que esta linha
    existe para medir. Nenhuma combinação de dia pode produzi-la."""
    combinacoes = [
        # o dia do 225%: 4 análises com defeito + 5 torneios = 9 eventos / 4
        dict(com_defeito=4, torneios=5),
        dict(limpas=12, torneios=4, sem_placar=2),
        dict(com_defeito=12, conversas=9),
        dict(com_defeito=3, limpas=1, torneios=7, sem_placar=6, conversas=4),
        dict(com_defeito=1),
        dict(torneios=5, conversas=3),  # nenhuma análise de mão no dia
    ]
    for kw in combinacoes:
        modelo = _dia(monkeypatch, **kw).strip().splitlines()[0]
        achou = re.search(r"em 24h = (\d+)%", modelo)
        if achou:
            assert int(achou.group(1)) <= 100, f"{kw}: {modelo}"
        else:
            assert "= sem base hoje" in modelo, f"{kw}: {modelo}"
        assert "⚠️" not in modelo, \
            f"{kw}: o numerador saiu maior que a base — {modelo}"


def test_a_linha_avisa_quando_o_numerador_passa_da_base():
    """Se a invariante quebrar por outro motivo (evento gravado e análise
    não — o guarda roda antes do `save_hand_analysis`), a linha DIZ. O dono
    não pode ler 225% de cara limpa e ter que descobrir sozinho que aquilo
    não é uma taxa."""
    torto = {**_CRU, "de_analise": 9}
    modelo = juiz.linha_da_voz(torto, {**_VOZ, "analisadas": 4})
    modelo = modelo.strip().splitlines()[0]
    assert "225%" in modelo, modelo
    assert "⚠️ acima da base" in modelo, \
        "a taxa impossível sai sem avisar que é impossível"


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
