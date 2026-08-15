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
