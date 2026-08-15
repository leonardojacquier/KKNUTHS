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
