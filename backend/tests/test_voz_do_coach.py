"""A análise soa como conversa ou como formulário?

Medido sobre a população certa (spec §9 — só análise de mão com selo, sem
follow-up e sem torneio): o bloco depois do placar é 67% do texto (678 chars
em média, n=116); o título fixo "A conta que mais pesa" aparece em 102 de 212
(48%); a narração de bastidor sobrevive em 73 (34%). Os números antigos deste
cabeçalho (58% / 740 / 25% / 23%) vinham de denominador contaminado.
"""
from __future__ import annotations

import pytest

from app.bot.guarda_voz import (TETO_POS_PLACAR, bloco_pos_placar,
                                numeros_repetidos, problemas_de_voz)

ANALISE_REAL = """\
❌ Jogada cara — abriu pequeno com stack de shove e depois desistiu do pote

🟡 *Pré* — abrir 2.8bb com K♦Q♦ (18.7bb) no BTN: jammar rende +1.49bb.
❌ *Turn* 5♦ — deu check behind: você tinha 35% e muita equity de barrel.

A conta que mais pesa: com 18.7bb o BTN é território de jam — empurrar
K♦Q♦ rende +1.49bb vs foldar.
"""


def test_bloco_pos_placar_comeca_depois_da_ultima_linha_de_selo():
    bloco = bloco_pos_placar(ANALISE_REAL)
    assert bloco.startswith("A conta que mais pesa")
    assert "check behind" not in bloco, "o placar vazou para dentro do bloco"


def test_sem_selo_nenhum_o_bloco_e_vazio():
    assert bloco_pos_placar("papo solto sobre range, sem análise") == ""


def test_numero_do_placar_repetido_na_prosa_e_detectado():
    assert "+1.49bb" in numeros_repetidos(ANALISE_REAL)


def test_numero_que_so_existe_no_placar_nao_conta_como_repetido():
    assert "35%" not in numeros_repetidos(ANALISE_REAL)


def test_titulo_fixo_e_apontado():
    assert any("título fixo" in p for p in problemas_de_voz(ANALISE_REAL))


def test_bloco_longo_e_apontado():
    longo = "✅ Você jogou bem — call fácil\n\n" + ("palavra " * 200)
    assert any("bloco pós-placar" in p for p in problemas_de_voz(longo))
    assert len(bloco_pos_placar(longo)) > TETO_POS_PLACAR


def test_narracao_de_bastidor_e_apontada():
    t = "✅ Você jogou bem — call fácil\n\nDeixa eu conferir o EV desse shove."
    assert any("bastidor" in p for p in problemas_de_voz(t))


def test_anotacao_no_caderno_NAO_e_defeito():
    """32 análises trazem isso e é voz de coach, não bastidor de sistema —
    é a regra A2 (record_student_note) aparecendo para o aluno. Apagar
    seria remover a frase mais humana da resposta."""
    t = "✅ Você jogou bem — call fácil\n\nAnotei no caderno pra próxima."
    assert problemas_de_voz(t) == []


def test_autocorrecao_e_apontada():
    t = "✅ Você jogou bem\n\nAbriu 6♦... digo, abriu 2bb com 66."
    assert any("autocorreção" in p for p in problemas_de_voz(t))


def test_analise_limpa_nao_tem_problema_nenhum():
    limpa = ("✅ Você jogou bem — set flopado\n\n"
             "✅ *Flop* 5♥8♠6♦ — set de 6 e jam de 16.9bb: board conectado.\n\n"
             "Com set em board de draw, empacotar é obrigatório.")
    assert problemas_de_voz(limpa) == []


from app.bot.guarda_voz import limpar


def test_titulo_fixo_sai_e_a_frase_vira_maiuscula():
    t = ("✅ Você jogou bem — call fácil\n\n"
         "*A conta que mais pesa:* com 12bb, AK em HJ é jam pré-flop.")
    novo, feitos = limpar(t)
    assert "conta que mais pesa" not in novo
    assert "Com 12bb, AK em HJ é jam pré-flop." in novo
    assert any("título fixo" in f for f in feitos)


def test_titulo_nao_sai_quando_a_frase_nao_sobrevive_sozinha():
    """'A conta que mais pesa: que você paga sempre' — tirar o rótulo deixa
    um fragmento. Este repositório já tem test_corretor_nao_estraga_portugues
    para esta classe exata de bug; o guarda novo não pode reintroduzi-la."""
    t = ("✅ Você jogou bem\n\n"
         "A conta que mais pesa: que você paga sempre sem pensar.")
    novo, feitos = limpar(t)
    assert novo == t, "o guarda partiu a frase ao meio"
    assert feitos == []


def test_narracao_de_bastidor_sai_a_frase_inteira():
    t = ("✅ Você jogou bem — call fácil\n\n"
         "Deixa eu conferir o EV desse shove. Com 12bb o jam é claro.")
    novo, feitos = limpar(t)
    assert "Deixa eu conferir" not in novo
    assert "Com 12bb o jam é claro." in novo
    assert any("bastidor" in f for f in feitos)


def test_anotacao_no_caderno_sobrevive_a_limpeza():
    t = "✅ Você jogou bem\n\nAnotei no caderno pra puxarmos na próxima."
    novo, feitos = limpar(t)
    assert novo == t
    assert feitos == []


def test_autocorrecao_NAO_e_corrigida_so_medida():
    """n=4 em 403. Frequência baixa demais e falso positivo plausível na
    fala natural ('não é fold... digo, não sempre')."""
    t = "✅ Você jogou bem\n\nAbriu 6♦... digo, abriu 2bb com 66."
    novo, _ = limpar(t)
    assert novo == t


def test_analise_limpa_passa_intacta():
    limpa = ("✅ Você jogou bem — set flopado\n\n"
             "✅ *Flop* 5♥8♠6♦ — set de 6 e jam de 16.9bb.\n\n"
             "Com set em board de draw, empacotar é obrigatório.")
    novo, feitos = limpar(limpa)
    assert novo == limpa
    assert feitos == []


def test_limpar_nunca_devolve_vazio():
    """Degradar para nada é pior do que entregar com defeito."""
    t = "Deixa eu conferir o EV desse shove."
    novo, _ = limpar(t)
    assert novo.strip(), "o guarda comeu a resposta inteira"


# --- Rodada de correção 1: os quatro achados da revisão de qualidade -----
#
# As asserções abaixo usam igualdade EXATA (==), não `in`/`not in`. É a
# lição do próprio Important 4 da revisão: os dois testes de remoção acima
# (test_titulo_fixo_sai_..., test_narracao_de_bastidor_sai_...) usam `in` e
# passaram verdes com o Critical 1 em produção — 'in' é cego para o que vem
# ANTES do trecho procurado, e foi exatamente ali que o defeito morava.


def test_titulo_sem_negrito_preserva_a_quebra_de_paragrafo_anterior():
    """Critical 1 da revisão: sem negrito, o espaço em branco opcional no
    início de _TITULO_FIXO também casa a quebra de linha ANTES do rótulo.
    Cortar em m.start() (código antigo) comia esse '\\n\\n' sem reemitir e
    colava os dois parágrafos: '...fácilCom 12bb...', sem nem um espaço. E
    colava a linha de placar na prosa, zerando bloco_pos_placar."""
    t = ("✅ Você jogou bem — call fácil\n\n"
         "A conta que mais pesa: com 12bb, AK em HJ é jam pré-flop.")
    novo, feitos = limpar(t)
    assert novo == ("✅ Você jogou bem — call fácil\n\n"
                     "Com 12bb, AK em HJ é jam pré-flop.")
    assert any("título fixo" in f for f in feitos)


def test_titulo_com_negrito_continua_preservando_a_quebra():
    """O caso com negrito nunca teve o defeito (o '*' ancora o match no
    início do rótulo, não antes dele) — teste de não-regressão exato."""
    t = ("✅ Você jogou bem — call fácil\n\n"
         "*A conta que mais pesa:* com 12bb, AK em HJ é jam pré-flop.")
    novo, feitos = limpar(t)
    assert novo == ("✅ Você jogou bem — call fácil\n\n"
                     "Com 12bb, AK em HJ é jam pré-flop.")
    assert any("título fixo" in f for f in feitos)


def test_bastidor_com_numero_decimal_nao_mutila_o_numero():
    """Critical 2 da revisão da Task 2 + I1 da revisão final, no mesmo texto.

    Critical 2: o separador de frase antigo tratava TODO ponto como fim de
    frase, inclusive o ponto decimal — cortava '1.49bb' no meio e entregava
    '49bb' ao aluno, um número que não existe na mão. Com o _FRASE ingênuo,
    a frase de bastidor viraria 'Deixa eu conferir o EV: 1.' (sem número
    para proteger: nem o _NUMERO do placar nem o _TEM_NUMERO da casa acham
    conta num '1.' solto) e o que sobraria seria '49bb no spot.' — a
    mutilação de volta.

    I1: a frase de bastidor CARREGA 1.49bb, então ela fica inteira. O
    guarda mede e entrega; não apaga a conta.
    """
    t = ("✅ Você jogou bem\n\n"
         "Deixa eu conferir o EV: 1.49bb no spot. Com 12bb é jam.")
    novo, feitos = limpar(t)
    assert novo == t, "a limpeza mexeu numa frase que carrega a conta"
    assert "49bb no spot" not in novo.replace("1.49bb no spot", ""), \
        "número decimal vazou mutilado"
    assert feitos == []


def test_bastidor_sem_numero_de_conta_sai_sem_mutilar_decimal():
    """Segundo cenário do Critical 2, agora com uma frase que a exceção do
    I1 NÃO protege: '16.9 combos' não é conta nem para a definição LARGA da
    casa — o comentário de `guarda_fatos._TEM_NUMERO` diz isso com todas as
    letras ("não é afrouxar até \\d: número solto continua NÃO sendo
    conta"). Então a frase de bastidor sai — e tem que sair INTEIRA. Com o
    separador ingênuo ela viraria 'Vou conferir o range: 16.' + '9 combos.',
    e o pedaço '9 combos.' vazaria colado no texto entregue.

    Este teste é a contraprova do R1: alargar a definição de conta não pode
    virar 'nunca mais limpo nada'."""
    t = ("✅ Você jogou bem\n\n"
         "Com 12bb o jam é claro. Vou conferir o range: 16.9 combos.")
    novo, feitos = limpar(t)
    assert novo == "✅ Você jogou bem\n\nCom 12bb o jam é claro."
    assert any("bastidor" in f for f in feitos)


def test_paragrafo_so_de_bastidor_nao_deixa_buraco_de_linhas_vazias():
    """Important 3 da revisão: um parágrafo que era só a frase de bastidor
    virava '' e a guarda de limpar (que só olha o texto INTEIRO vazio) não
    pegava — sobravam quatro quebras de linha seguidas, buraco visível na
    mensagem entregue ao aluno."""
    t = ("✅ Você jogou bem — call fácil\n\n"
         "Deixa eu conferir o EV desse shove.\n\n"
         "Com 12bb o jam é claro.")
    novo, feitos = limpar(t)
    assert novo == ("✅ Você jogou bem — call fácil\n\n"
                     "Com 12bb o jam é claro.")
    assert "\n\n\n" not in novo, "sobrou buraco de linhas vazias"
    assert any("bastidor" in f for f in feitos)


# --- Onda final: I1, I2, I3 ---------------------------------------------
#
# Asserções por igualdade EXATA. A revisão final achou três testes
# decorativos (dois deles escritos pela própria execução) e o pior defeito
# da Task 2 passou por baixo de um `in` solto.


def test_bastidor_que_carrega_a_conta_nao_e_apagado():
    """I1 — o achado com dano direto ao aluno.

    Executado contra o código antigo, este texto virava
    '✅ Você jogou bem\\n\\nPortanto foi call caro.': um veredito com ZERO
    número, que é literalmente a forma que guarda_fatos.conta_sem_numero
    existe para detectar. E ele roda 45 linhas ANTES do guarda da voz
    (processing.py:532 × :577), sobre o texto que ainda tinha a conta — o
    defeito nascia depois do detector.
    """
    t = ("✅ Você jogou bem\n\n"
         "Vou calcular: pedia 30%, tinha 12% → −11bb. Portanto foi call caro.")
    novo, feitos = limpar(t)
    assert novo == t, "a limpeza apagou a única frase com a conta"
    assert feitos == []


def test_bastidor_que_carrega_a_conta_continua_sendo_medido():
    """A exceção do I1 não é anistia: o defeito continua apontado, o evento
    continua sendo gravado e o dono continua vendo a taxa. O que muda é que
    o guarda MEDE em vez de apagar."""
    t = ("✅ Você jogou bem\n\n"
         "Vou calcular: pedia 30%, tinha 12% → −11bb. Portanto foi call caro.")
    assert problemas_de_voz(t) == ["bastidor de busca narrado ao aluno"]


def test_resposta_de_conversa_pedida_pelo_aluno_mantem_o_numero():
    """O mesmo mecanismo, no caminho da conversa e com custo maior: o aluno
    PERGUNTOU o EV, o guarda_saida.faltou (processing.py:1217) achou o
    número e deu entrega_ok, e a limpeza (:1229) apagava a frase logo
    depois — resposta sem número com o portão que existe para impedir isso
    já tendo dito OK."""
    t = ("Vou conferir o EV: +1.49bb no jam. "
         "Contra o range dele, empurrar bate foldar.")
    novo, feitos = limpar(t)
    assert novo == t
    assert feitos == []


def test_frase_fundida_sem_espaco_depois_do_ponto_nao_come_a_resposta():
    """Diferido (b) da revisão final, morto pelo conserto do I1 e não por
    conserto próprio: sem o espaço depois do ponto, _FRASE lê '.' seguido de
    dígito como DECIMAL, então a corrida inteira é uma frase só. Antes, ela
    era removida por conter bastidor e o aluno recebia apenas o selo."""
    t = "✅ Você jogou bem\n\nVou conferir o EV.12bb é jam, e o range aperta."
    novo, feitos = limpar(t)
    assert novo == t
    assert feitos == []


# --- R1 dos resíduos: a CLASSE do I1, não só o cenário -------------------
#
# O I1 travou a limpeza quando a frase carrega a conta, mas a trava usava o
# `_NUMERO` do próprio guarda da voz, que só conhece `bb` e `%`. A definição
# de conta desta casa é `guarda_fatos._TEM_NUMERO`, e o comentário dela diz
# por quê: "exigir sufixo bb/%/fichas reprovava as duas formas mais básicas
# da matemática de poker". Os quatro textos abaixo são os que a re-revisão
# final EXECUTOU contra a branch — os quatro perdiam a única conta e viravam
# veredito pelado. Critério, nas palavras do dono: "Eu quero q simplifique
# mas que não apague números importantes."

_CONTA_QUE_NAO_E_BB_NEM_PORCENTO = [
    # pot odds em razão + frequência escrita por extenso
    "Vou calcular: o pote paga 2.5 para 1 e você tem 1 em 3. "
    "Portanto foi call caro.",
    # outs
    "Vou conferir: você tinha 9 outs. Portanto foi call caro.",
    # fichas (torneio)
    "Vou calcular: o pote tinha 5000 fichas e o call custa 1200 fichas. "
    "Portanto foi call caro.",
    # EV com sinal, sem unidade
    "Vou rodar o EV: deu +8.2 no shove. Portanto foi jam claro.",
]


@pytest.mark.parametrize("t", _CONTA_QUE_NAO_E_BB_NEM_PORCENTO)
def test_bastidor_com_conta_que_nao_e_bb_nem_porcento_nao_e_apagado(t):
    """R1 — igualdade EXATA, e não `in`: foi asserção `in` solta que deixou
    passar o pior defeito desta branch. Com `_NUMERO` (bb/% apenas) os
    quatro saíam como o veredito sozinho, sem número nenhum."""
    novo, feitos = limpar(t)
    assert novo == t, "a limpeza apagou a única frase com a conta"
    assert feitos == []


@pytest.mark.parametrize("t", _CONTA_QUE_NAO_E_BB_NEM_PORCENTO)
def test_bastidor_com_conta_larga_continua_sendo_medido(t):
    """A exceção não é anistia — o defeito continua apontado e vira evento,
    exatamente como no cenário bb/% do I1. O guarda mede em vez de apagar."""
    assert problemas_de_voz(t) == ["bastidor de busca narrado ao aluno"]


def _nomes_carregados(code) -> set[str]:
    """Todo nome que o bytecode de `code` carrega, comprehensions inclusas.

    Ler `inspect.getsource` aqui seria decorativo: a docstring de
    `_sem_narracao` CITA `_TEM_NUMERO` ao explicar o R1, então a substring
    sobreviveria à reversão do código. `co_names` só enxerga o que roda — e
    a comparação da lista fica dentro de uma list comprehension, que em 3.11
    é um code object próprio, por isso a recursão em `co_consts`.
    """
    nomes = set(code.co_names)
    for const in code.co_consts:
        if hasattr(const, "co_names"):
            nomes |= _nomes_carregados(const)
    return nomes


def test_o_guarda_da_voz_usa_a_definicao_de_conta_da_casa():
    """Duas definições de conta em dois módulos foi o defeito; uma cópia
    nova reinstala o R1 sem que nenhum cenário acuse. `_NUMERO` continua
    existindo — mas só para `numeros_repetidos`, que compara placar × prosa
    e cujo universo é mesmo bb/%."""
    from app.bot import guarda_fatos, guarda_voz

    nomes = _nomes_carregados(guarda_voz._sem_narracao.__code__)
    assert "_TEM_NUMERO" in nomes, \
        "_sem_narracao não consulta a definição de conta da casa"
    assert "_NUMERO" not in nomes, \
        "_sem_narracao voltou a decidir por uma régua de conta só sua"
    # e a definição da casa continua sendo mais larga que a do placar: se um
    # dia alguém estreitar `_TEM_NUMERO` para bb/%, este teste cai junto.
    for texto in ("o pote paga 2.5 para 1", "você tinha 9 outs",
                  "5000 fichas", "+8.2"):
        assert guarda_fatos._TEM_NUMERO.search(texto), texto
        assert not guarda_voz._NUMERO.search(texto), \
            f"{texto!r} passou a casar em _NUMERO — os dois convergiram"


def test_o_criterio_do_dono_esta_escrito_no_guarda():
    """Este repositório documenta o porquê junto do quê, e o porquê aqui é
    uma frase do dono (16/08/2026). Sem ela, a próxima pessoa que ler
    `_sem_narracao` vê uma exceção sem critério e a 'simplifica' de volta."""
    import inspect

    from app.bot import guarda_voz

    fonte = inspect.getsource(guarda_voz)
    assert "não apague números importantes" in fonte, \
        "o critério do dono saiu da docstring do guarda"


def test_analise_conforme_ao_R5b_nao_tem_defeito_nenhum():
    """I3 — o contador marcava como defeito o que o prompt agora MANDA.

    Esta análise obedece ao R3 (fechamento sem rótulo, sem recitar preço) e
    ao R5b (a história do desfecho com as % de cada street). O código antigo
    devolvia ['número do placar repetido na prosa: 12%, 30%'], gravava um
    evento `voz_medida` e fazia `com_numero_repetido` subir por causa da
    melhoria que a branch existe para provar.
    """
    conforme = ("❌ Jogada cara — pagou o river sem preço\n\n"
                "🟡 *Pré* — 3-bet A♠K♠: contra o range dele, +EV.\n"
                "❌ *River* K♠ — pagou 18bb: pedia 30%, tinha 12% → −11bb.\n\n"
                "Você estava atrás desde o pré: 30% no flop, 12% no river. "
                "Não foi bad beat.")
    assert problemas_de_voz(conforme) == []


def test_o_guarda_conhece_os_tres_rotulos_do_R3():
    """I2 — o guarda conhecia 1 rótulo e o R3 proíbe 3. O modelo obedece à
    proibição mais específica (a que tem nome próprio), troca para 'Resumo:'
    e todos os contadores dizem sucesso com o formulário intacto."""
    for rotulo in ("A conta que mais pesa:", "Resumo:", "O que treinar:"):
        t = f"✅ Você jogou bem\n\n{rotulo} com 12bb, AK em HJ é jam pré-flop."
        assert problemas_de_voz(t) == [f"título fixo {rotulo!r}"], rotulo
        novo, feitos = limpar(t)
        assert novo == ("✅ Você jogou bem\n\n"
                        "Com 12bb, AK em HJ é jam pré-flop."), rotulo
        assert feitos == ["título fixo removido"], rotulo


def test_resumo_no_meio_da_frase_nao_e_titulo_fixo():
    """'resumo' e 'o que treinar' são português comum — só contam como
    TÍTULO quando abrem a linha, que é o que um rótulo de seção faz.
    Acusar 'em resumo, ...' seria o guarda inventando defeito."""
    t = "✅ Você jogou bem\n\nEm resumo: com 12bb o jam é a única linha."
    assert problemas_de_voz(t) == []
    assert limpar(t) == (t, [])


def test_limpar_de_none_devolve_string_vazia_nao_none():
    """Achado extra que o dispatcher decidiu incluir apesar de o revisor
    classificar como Minor: a assinatura promete tuple[str, list[str]], mas
    limpar(None) devolvia (None, []). A Task 3 chama
    'answer, feitos = limpar(answer)' sem guarda de None antes disso."""
    assert limpar(None) == ("", [])


# --- Rodada de correção 1, achado Important: conferir_e_limpar -----------
#
# processing.py inlinhava ~10 linhas por caminho chamando problemas_de_voz +
# limpar + repo.log_event direto, empurrando o arquivo para o teto de 3600
# linhas de test_processing_nao_incha.py — satisfeito por compressão de
# formatação em vez da extração que o próprio teste pede. conferir_e_limpar
# espelha guarda_saida.conferir_e_remediar: mede, corrige e registra o
# evento por conta própria, e processing.py vira uma chamada por caminho.
# Sem cobertura própria aqui, é a função que agora carrega a lógica e fica
# sem teste.

from app.bot.guarda_voz import conferir_e_limpar


def test_conferir_e_limpar_texto_limpo_passa_intacto_sem_evento(monkeypatch):
    """Sem defeito e sem correção, a função nem chega a pedir o repositório
    — se log_event fosse chamado aqui, seria um evento fantasma."""
    def _log_event_nao_deveria_ser_chamado(*a, **k):
        raise AssertionError("log_event chamado para texto sem defeito nem correção")

    monkeypatch.setattr(
        "app.db.get_repository",
        lambda: type("R", (), {
            "log_event": staticmethod(_log_event_nao_deveria_ser_chamado)})())

    limpa = ("✅ Você jogou bem — set flopado\n\n"
             "✅ *Flop* 5♥8♠6♦ — set de 6 e jam de 16.9bb.\n\n"
             "Com set em board de draw, empacotar é obrigatório.")
    saida = conferir_e_limpar(123, limpa, username="tester")
    assert saida == limpa


def test_conferir_e_limpar_titulo_fixo_volta_corrigido_e_registrado(monkeypatch):
    eventos: list[tuple] = []

    class _Repo:
        def log_event(self, telegram_id, username, evento, detalhe=None):
            eventos.append((telegram_id, username, evento, detalhe))

    monkeypatch.setattr("app.db.get_repository", lambda: _Repo())

    t = ("✅ Você jogou bem — call fácil\n\n"
         "*A conta que mais pesa:* com 12bb, AK em HJ é jam pré-flop.")
    saida = conferir_e_limpar(456, t, username="tester", onde="conversa")

    assert "conta que mais pesa" not in saida
    assert "Com 12bb, AK em HJ é jam pré-flop." in saida
    assert len(eventos) == 1
    telegram_id, username, evento, detalhe = eventos[0]
    assert (telegram_id, username, evento) == (456, "tester", "voz_corrigida")
    assert any("título fixo" in f for f in detalhe["feitos"])
    assert detalhe["onde"] == "conversa"


# --- A POPULAÇÃO É CARIMBADA NA ORIGEM ------------------------------------
#
# A taxa da linha 🗣 do juiz dividia populações diferentes: o numerador vinha
# dos eventos de voz do caminho de ANÁLISE — que inclui relatório de TORNEIO
# e análise SEM placar, porque `conferir_e_limpar` roda em processing.py:571,
# ANTES do `if not is_tournament` de :582 — e o denominador só continha
# análise de mão COM placar. Executado pela re-revisão: "6 de 12 análises =
# 50%" num dia cuja verdade era 0%, e "9 de 4 = 225%". Quem sabe de que
# população o texto veio é quem chama; daí o carimbo aqui, e não uma
# adivinhação no juiz.


@pytest.mark.parametrize("texto,onde,esperado_onde,esperado_placar", [
    # análise de mão de verdade: duas linhas de selo = placar street a street
    ("✅ Você jogou bem — call fácil\n"
     "✅ *Flop* 5♥8♠6♦ — set de 6.\n\n"
     "*A conta que mais pesa:* com 12bb, AK em HJ é jam pré-flop.",
     "analise", "analise", True),
    # relatório de torneio: um selo só, nunca placar
    ("✅ Torneio ok — bom ITM\n\n*Resumo:* você foi bem no ICM.",
     "torneio", "torneio", False),
    # decisão única (R4): também análise, também sem placar
    ("✅ Call certo\n\n*Resumo:* pagar 12bb ali é padrão.",
     "analise", "analise", False),
    # conversa continua sendo o que sempre foi
    ("*Resumo:* com 12bb, AK em HJ é jam pré-flop.",
     "conversa", "conversa", False),
])
def test_o_evento_de_voz_sai_com_a_populacao_carimbada(
        monkeypatch, texto, onde, esperado_onde, esperado_placar):
    """Sem `onde` E `com_placar` no evento, o juiz não tem como separar o
    numerador dele — foi assim que torneio e análise sem placar entraram
    numa taxa cujo denominador não os continha."""
    eventos: list[dict] = []

    class _Repo:
        def log_event(self, telegram_id, username, evento, detalhe=None):
            eventos.append(detalhe)

    monkeypatch.setattr("app.db.get_repository", lambda: _Repo())
    conferir_e_limpar(1, texto, username="tester", onde=onde)

    assert len(eventos) == 1, "o texto de teste parou de gerar evento"
    assert eventos[0]["onde"] == esperado_onde
    assert eventos[0]["com_placar"] is esperado_placar


def test_o_evento_sem_onde_declarado_ainda_diz_de_onde_veio(monkeypatch):
    """O caminho histórico da análise chamava sem `onde` nenhum. O carimbo
    não pode depender de o chamador lembrar: sem declaração o evento sai
    como "analise", que é o que aquele caminho sempre foi."""
    eventos: list[dict] = []

    class _Repo:
        def log_event(self, telegram_id, username, evento, detalhe=None):
            eventos.append(detalhe)

    monkeypatch.setattr("app.db.get_repository", lambda: _Repo())
    conferir_e_limpar(1, "✅ Call certo\n\n*Resumo:* pagar 12bb é padrão.")

    assert eventos[0]["onde"] == "analise"
    assert eventos[0]["com_placar"] is False


def test_tem_placar_e_a_mesma_regua_dos_dois_lados_da_razao():
    """Acordo, não forma: o numerador (carimbo do evento) e o denominador
    (o texto gravado, filtrado pelo juiz) têm que responder IGUAL para o
    mesmo texto. Duas cópias da régua de população é exatamente o defeito
    que a taxa mentirosa expôs — o juiz tinha a dele, o guarda não tinha
    nenhuma."""
    from app.bot.guarda_voz import tem_placar

    casos = [
        ("✅ a\n✅ b", True),
        ("✅ a\n🟡 b\n❌ c", True),
        ("✅ Torneio ok\n\nprosa sem selo", False),
        ("prosa sem selo nenhum", False),
        ("", False),
        ("  ✅ indentado\n  ✅ indentado", True),
    ]
    for texto, esperado in casos:
        assert tem_placar(texto) is esperado, texto
        assert juiz_resumo_placar(texto) is esperado, texto


def juiz_resumo_placar(texto: str) -> bool:
    """O juiz visto de fora: a análise só entra no denominador se `resumo_de_voz`
    a contar. É o mesmo `tem_placar`, exercido pelo caminho do juiz."""
    from scripts.output_judge import resumo_de_voz

    return resumo_de_voz([texto])["analisadas"] == 1


def test_conferir_e_limpar_excecao_do_repositorio_nao_propaga(monkeypatch):
    """CONTRATO HONESTO: só o log_event está protegido aqui dentro — a
    exceção de problemas_de_voz/limpar continua responsabilidade de quem
    chama, em processing.py. Isto cobre a metade que É desta função."""
    class _RepoQuebrado:
        def log_event(self, *a, **k):
            raise RuntimeError("repositório fora do ar")

    monkeypatch.setattr("app.db.get_repository", lambda: _RepoQuebrado())

    t = ("✅ Você jogou bem — call fácil\n\n"
         "*A conta que mais pesa:* com 12bb, AK em HJ é jam pré-flop.")
    saida = conferir_e_limpar(789, t)  # não pode levantar

    assert "conta que mais pesa" not in saida
    assert "Com 12bb, AK em HJ é jam pré-flop." in saida


def test_conferir_e_limpar_de_texto_vazio_nao_toca_no_repositorio(monkeypatch):
    """Espelha o contrato de limpar(None) == ("", []), mas sem a coerção:
    devolve o texto como veio (None continua None), porque quem chama
    (a análise) usava 'if coaching:' para não converter None em "" antes
    da extração — mover a guarda para dentro preserva esse comportamento."""
    def _log_event_nao_deveria_ser_chamado(*a, **k):
        raise AssertionError("log_event chamado para texto vazio")

    monkeypatch.setattr(
        "app.db.get_repository",
        lambda: type("R", (), {
            "log_event": staticmethod(_log_event_nao_deveria_ser_chamado)})())

    assert conferir_e_limpar(1, None) is None
    assert conferir_e_limpar(1, "") == ""


# ---------------------------------------------------------------------------
# Plano C com motivo: a falha de 16/08 foi invisível porque o except do
# coach() era mudo. O contrato agora: TODA queda no resumo determinístico
# registra o evento `plano_c` com o motivo — falha nunca mais é silenciosa.


def test_coach_que_explode_registra_plano_c_com_motivo(monkeypatch):
    from app.agent import llm

    eventos = []

    class _Repo:
        enabled = True

        def log_event(self, tid, user, event, detail):
            eventos.append((event, detail))

    monkeypatch.setattr("app.db.get_repository", lambda: _Repo())
    monkeypatch.setattr(
        llm, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m"})())

    def _explode(*a, **k):
        raise RuntimeError("boom de teste")

    monkeypatch.setattr(llm, "_create", _explode)
    out = llm.coach({"summary": "FALLBACK DETERMINÍSTICO"}, None)

    assert out == "FALLBACK DETERMINÍSTICO"  # plano C continua entregue
    assert [e for e, _ in eventos] == ["plano_c"]
    detail = eventos[0][1]
    assert "RuntimeError" in detail["motivo"]
    assert "boom de teste" in detail["motivo"]
    assert "trace" in detail  # o traceback vai junto — é ele que faltou em 16/08


def test_plano_c_com_repositorio_quebrado_nao_derruba_o_aluno(monkeypatch):
    """O diagnóstico é blindado como o custo: logar não pode falhar a resposta."""
    from app.agent import llm

    class _RepoQuebrado:
        enabled = True

        def log_event(self, *a, **k):
            raise OSError("banco fora")

    monkeypatch.setattr("app.db.get_repository", lambda: _RepoQuebrado())
    monkeypatch.setattr(
        llm, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m"})())
    monkeypatch.setattr(llm, "_create",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    assert llm.coach({"summary": "PLANO C"}, None) == "PLANO C"


# ---------------------------------------------------------------------------
# A causa raiz de 16/08: análise cortada por max_tokens no meio de uma
# ferramenta deixa um tool_use PENDURADO; o resgate recolava esse content na
# conversa sem tool_result e a API devolvia 400 ('tool_use ids without
# tool_result') — final vazio, aluno no plano C. O resgate agora só recola
# blocos de TEXTO.


def _bloco(tipo, **kw):
    from types import SimpleNamespace
    return SimpleNamespace(type=tipo, **kw)


def test_resgate_nao_recola_tool_use_pendurado(monkeypatch):
    from app.agent import llm

    capturado = {}

    def _força_fake(client, modelo, blocks, msgs, teto=None):
        capturado["msgs"] = msgs
        return "✅ Call correto — resgatado."

    monkeypatch.setattr(llm, "_force_text", _força_fake)
    out = llm._resgatar_conclusao(
        None, "m", [], [{"role": "user", "content": "contexto"}],
        ultimo_assistant=[_bloco("text", text="Deixa eu calcular o EV..."),
                          _bloco("tool_use", id="toolu_pendurado", name="ev",
                                 input={})])

    assert out == "✅ Call correto — resgatado."
    tipos = [getattr(b, "type", None)
             for m in capturado["msgs"] if isinstance(m.get("content"), list)
             for b in m["content"] if not isinstance(b, dict)]
    assert "tool_use" not in tipos  # o 400 de 16/08 era exatamente isto
    assert "text" in tipos  # a narração útil continua indo junto


def test_resgate_com_assistant_so_de_tool_use_nao_apenda_mensagem_vazia(monkeypatch):
    from app.agent import llm

    capturado = {}

    def _força_fake(client, modelo, blocks, msgs, teto=None):
        capturado["msgs"] = msgs
        return "✅ ok"

    monkeypatch.setattr(llm, "_force_text", _força_fake)
    llm._resgatar_conclusao(
        None, "m", [], [{"role": "user", "content": "contexto"}],
        ultimo_assistant=[_bloco("tool_use", id="t1", name="ev", input={})])
    papeis = [m["role"] for m in capturado["msgs"]]
    assert "assistant" not in papeis  # assistant vazio também é 400


def test_analise_cortada_por_max_tokens_recupera_em_vez_de_plano_c(monkeypatch):
    """O cenário de produção inteiro: rodada devolve stop_reason='max_tokens'
    com tool_use pendurado -> o coach resgata a conclusão em vez de entregar
    o resumo determinístico."""
    from types import SimpleNamespace
    from app.agent import llm

    monkeypatch.setattr(
        llm, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m"})())
    resp = SimpleNamespace(
        stop_reason="max_tokens",
        content=[_bloco("text", text="Vou conferir o EV do shove..."),
                 _bloco("tool_use", id="toolu_01QVG", name="ev_allin",
                        input={})])
    monkeypatch.setattr(llm, "_create", lambda *a, **k: resp)

    visto = {}

    def _força_fake(client, modelo, blocks, msgs, teto=None):
        visto["tool_use_recolado"] = any(
            getattr(b, "type", None) == "tool_use"
            for m in msgs if isinstance(m.get("content"), list)
            for b in m["content"] if not isinstance(b, dict))
        return "✅ Jogada certa — 32% contra 30.8% que pedia."

    monkeypatch.setattr(llm, "_force_text", _força_fake)
    out = llm.coach({"summary": "PLANO C"}, None)

    assert out == "✅ Jogada certa — 32% contra 30.8% que pedia."
    assert visto["tool_use_recolado"] is False


# ---------------------------------------------------------------------------
# O galho MUDO que sobrou: `if resp.stop_reason != "tool_use"`. A
# instrumentação de 16/08 fechou o `except` e o fim-de-rodadas e passou
# batido neste — o modelo para sem pedir ferramenta, o resgate não recupera
# nada, `final` fica vazio e o aluno leva o plano C sem UMA linha de
# registro. Caso real de 16/08: o comparador rodou 8 mãos e a mão
# 43450b49-8e78-406e-aa00-ced59e1d4364 caiu aqui; a consulta a bot_events
# devolveu zero eventos, porque o código não escrevia nenhum.


def _coach_sem_tool_use(monkeypatch, eventos, stop_reason="end_turn"):
    """Cenário da mão 43450b49: resposta sem tool_use, sem texto, resgate
    vazio -> plano C. Devolve a saída do coach."""
    from types import SimpleNamespace
    from app.agent import llm

    class _Repo:
        enabled = True

        def log_event(self, tid, user, event, detail):
            eventos.append((event, detail))

    monkeypatch.setattr("app.db.get_repository", lambda: _Repo())
    monkeypatch.setattr(
        llm, "get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m"})())
    monkeypatch.setattr(
        llm, "_create",
        lambda *a, **k: SimpleNamespace(stop_reason=stop_reason, content=[]))
    monkeypatch.setattr(llm, "_force_text", lambda *a, **k: "")
    return llm.coach({"summary": "PLANO C"}, None)


def test_plano_c_sem_tool_use_registra_motivo_com_stop_reason(monkeypatch):
    """O caminho da mão 43450b49 deixa rastro: evento com o stop_reason."""
    eventos: list = []
    out = _coach_sem_tool_use(monkeypatch, eventos)

    assert out == "PLANO C"                      # o aluno continua atendido
    assert [e for e, _ in eventos] == ["plano_c"], \
        "queda no plano C sem evento é exatamente o defeito de 16/08"
    assert "end_turn" in eventos[0][1]["motivo"], \
        "sem o stop_reason não dá para saber POR QUE o modelo parou"


def test_plano_c_sem_tool_use_carrega_o_stop_reason_real(monkeypatch):
    """O stop_reason não é constante decorativa: 'max_tokens' aparece no
    evento quando foi ele que parou o modelo.

    Busca o `plano_c` pelo nome em vez de indexar [0]: com 'max_tokens' o
    corte agora registra ANTES o evento próprio `analise_cortada`, e o que
    este teste cobra é o motivo do plano_c.
    """
    eventos: list = []
    _coach_sem_tool_use(monkeypatch, eventos, stop_reason="max_tokens")
    motivo = next(d["motivo"] for e, d in eventos if e == "plano_c")
    assert "max_tokens" in motivo


def test_os_dois_galhos_do_plano_c_tem_motivos_distintos(monkeypatch):
    """Dá para separar na consulta 'parou sem pedir ferramenta' de 'rodadas
    esgotadas' — dois defeitos diferentes, dois motivos diferentes."""
    from types import SimpleNamespace
    from app.agent import llm

    sem_tool_use: list = []
    _coach_sem_tool_use(monkeypatch, sem_tool_use)

    # rodadas esgotadas: toda rodada pede ferramenta até estourar o limite
    rodadas: list = []

    class _Repo:
        enabled = True

        def log_event(self, tid, user, event, detail):
            rodadas.append((event, detail))

    monkeypatch.setattr("app.db.get_repository", lambda: _Repo())
    monkeypatch.setattr(
        llm, "_create",
        lambda *a, **k: SimpleNamespace(
            stop_reason="tool_use",
            content=[_bloco("tool_use", id="t1", name="inexistente",
                            input={})]))
    monkeypatch.setattr(llm, "_force_text", lambda *a, **k: "")
    assert llm.coach({"summary": "PLANO C"}, None) == "PLANO C"

    assert [e for e, _ in rodadas] == ["plano_c"]
    # o PREFIXO tem de diferir, não só a string inteira: o sufixo
    # '(stop_reason=...)' já garantia desigualdade, então trocar o prefixo de
    # um galho pelo do outro passava — a consulta que separa os dois defeitos
    # filtra por prefixo, e era exatamente isso que o teste não cobrava.
    assert sem_tool_use[0][1]["motivo"].startswith("resposta_vazia_sem_tool_use")
    assert rodadas[0][1]["motivo"].startswith("resposta_vazia_apos_rodadas")
