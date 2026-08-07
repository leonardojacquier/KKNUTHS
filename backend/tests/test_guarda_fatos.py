"""A análise não pode afirmar o que a conta desmente.

Caso real (07/08, print do dono): numa mão de KK pagando all-in, o coach
escreveu "o vilão só te vira favorito com QQ ou AA". KK ganha de QQ em 80%
das vezes. O aluno que acredita nisso passa a foldar KK contra 4-bet — o
produto ensinando o erro.

'X é favorito contra Y' é pergunta fechada: o motor de equity responde. Então
confere antes de entregar, em vez de pedir de novo no prompt (F1 e F4 já
proibiam inventar, e saiu assim mesmo).
"""
from __future__ import annotations

from app.bot.guarda_fatos import (conferir_dominancia, maos_citadas,
                                  quem_ganha_do_heroi)

KK = ["Kh", "Kd"]


def test_o_caso_do_print():
    texto = ("A conta que mais pesa: com KK e stack curto você paga esse "
             "all-in sempre. O vilão só te vira favorito com QQ ou AA, e "
             "isso é raro.")
    novo, erros = conferir_dominancia(texto, KK)
    assert erros == ["QQ"]
    assert "QQ" not in novo
    assert "só te vira favorito com AA" in novo
    assert "e isso é raro" in novo, "não pode comer o resto da frase"


def test_afirmacao_correta_passa_intacta():
    for texto in ("Você só perde para AA aqui.",
                  "Ele só está atrás de AA nesse spot."):
        novo, erros = conferir_dominancia(texto, KK)
        assert erros == [] and novo == texto


def test_texto_sem_frase_de_dominancia_nao_e_tocado():
    texto = ("✅ Você jogou bem — pagar KK contra o all-in curto do CO\n\n"
             "Contra o range de shove dele, o call rende +8.2bb comparado a "
             "foldar.")
    novo, erros = conferir_dominancia(texto, KK)
    assert novo == texto and erros == []


def test_quando_nada_do_que_citou_ganha_poe_a_verdade():
    """'só perde para JJ e TT' com KK: nenhuma das duas ganha — a frase vira
    a mão que realmente ganha, não some deixando o aluno sem resposta."""
    novo, erros = conferir_dominancia("Você só perde para JJ ou TT.", KK)
    assert set(erros) == {"JJ", "TT"}
    assert "AA" in novo


def test_a_conta_de_verdade():
    from app.analysis.equity import equity_vs_hand

    assert equity_vs_hand(KK, ["Qs", "Qc"]) > 0.75   # KK esmaga QQ
    assert equity_vs_hand(KK, ["As", "Ac"]) < 0.25   # e apanha de AA
    assert quem_ganha_do_heroi(KK, ["QQ", "AA", "AKo"]) == ["AA"]


def test_le_notacao_de_mao_como_jogador_escreve():
    assert maos_citadas("QQ ou AA") == ["QQ", "AA"]
    assert maos_citadas("AKs e AKo") == ["AKs", "AKo"]
    assert maos_citadas("nada de mão aqui") == []


def test_heroi_desconhecido_nao_inventa_correcao():
    """Sem as cartas do herói não dá para conferir — melhor não mexer."""
    texto = "Você só perde para QQ."
    assert conferir_dominancia(texto, []) == (texto, [])
    assert conferir_dominancia(texto, ["Kh"]) == (texto, [])


def test_esta_ligado_na_analise_e_vira_evento():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "conferir_dominancia" in fonte
    assert "fato_corrigido" in fonte, "erro corrigido tem que virar evento"
