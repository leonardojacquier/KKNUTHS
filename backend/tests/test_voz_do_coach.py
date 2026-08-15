"""A análise soa como conversa ou como formulário?

Medido em 403 análises reais (45 dias): o bloco depois do placar é 58% do
texto (740 de 1662 chars, n=183); o título fixo "A conta que mais pesa"
aparece em 102 delas (25%); a narração de bastidor sobrevive em 91 (23%).
"""
from __future__ import annotations

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
    """Critical 2 da revisão: o separador de frase antigo tratava TODO
    ponto como fim de frase, inclusive o ponto decimal — cortava '1.49bb'
    no meio e entregava '49bb' ao aluno, um número que não existe na mão.
    É a mesma classe de defeito que _conferir_numeros em llm.py existe
    para impedir, só que do lado da limpeza de voz."""
    t = ("✅ Você jogou bem\n\n"
         "Deixa eu conferir o EV: 1.49bb no spot. Com 12bb é jam.")
    novo, feitos = limpar(t)
    assert novo == "✅ Você jogou bem\n\nCom 12bb é jam."
    assert "1.49bb" not in novo
    assert "49bb no spot" not in novo, "número decimal vazou mutilado"
    assert any("bastidor" in f for f in feitos)


def test_bastidor_no_meio_da_frase_preserva_decimal_da_frase_seguinte():
    """Segundo cenário do Critical 2: o decimal pode estar na frase que
    SOBREVIVE, não só na que é removida — '9bb efetivo' colado em 'claro.'
    era o sintoma."""
    t = ("✅ Você jogou bem\n\n"
         "Com 12bb o jam é claro. Vou conferir o range: 16.9bb efetivo.")
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
