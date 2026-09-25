"""O juiz cortava a resposta em 1500 chars e depois reclamava do corte.

Caso real (relatório de 26/08, nota 6.5/10, n=1). A "pior resposta" citada
terminava assim:

    "…e um TERCEIRO ainda sobe de novo — essa é a sequê"

com o comentário do juiz: *"frase incompleta e desvia do foco"*.

Não foi o relatório que cortou: a linha inteira tem 141 chars contra um teto
de 160. Quem cortou foi o PRÓPRIO juiz, em `_nota_uma`, com um `[:1500]` cego
no texto que manda para o modelo auditor. A análise entregue ao aluno estava
inteira; o auditor é que leu um pedaço, viu a palavra partida no meio e
descontou nota por um defeito que ele mesmo fabricou.

É o erro de instrumento do METODO §1 pelo outro lado: lá o denominador estava
contaminado, aqui é o NUMERADOR — a medida está medindo a própria régua.

Piora com o tempo: a análise de mão com placar street a street mais o bloco
pós-placar (1063 chars médios no dia) encosta em 1500 com facilidade. Ou
seja, quanto mais completa a análise, mais o juiz a punia.
"""
from __future__ import annotations

import inspect

from scripts.output_judge import (TETO_DO_TEXTO_JULGADO, _nota_uma,
                                  texto_para_o_juiz)

# a frase real do caso, montada até passar de 1500 chars como a de produção
_CAUDA = ("Uma coisa pra guardar: quando você aperta, alguém sobe, e um "
          "TERCEIRO ainda sobe de novo — essa é a sequência de 3-bets que "
          "define o spot.")


def _analise_longa(n: int = 1800) -> str:
    corpo = ("✅ *Pré* — abriu 2.5bb com AKo no CO: abertura padrão. "
             "❌ *Flop* — c-bet de 3.2bb num board K72r: 61% de equity. ")
    texto = ""
    while len(texto) < n:
        texto += corpo
    return texto[:n] + " " + _CAUDA


# ---- 1) o que cabe passa inteiro -------------------------------------------

def test_resposta_curta_chega_intacta():
    curta = "✅ *Pré* — jam de 12bb com A9s no BTN rende +1.2bb."
    assert texto_para_o_juiz(curta) == curta


def test_o_teto_cabe_uma_analise_de_verdade():
    """1500 era menor que a análise média COM placar. O teto novo tem que
    caber a análise inteira, senão o defeito só muda de tamanho."""
    assert TETO_DO_TEXTO_JULGADO >= 4000, (
        "teto ainda corta análise de mão com placar street a street")


def test_a_analise_do_caso_real_chega_inteira():
    """A regressão âncora: 1.800 chars + a cauda que foi cortada em produção."""
    inteira = _analise_longa()
    assert len(inteira) > 1500, "o caso de teste não reproduz o tamanho real"
    saida = texto_para_o_juiz(inteira)
    assert saida.endswith("define o spot."), \
        "a frase que o juiz chamou de incompleta continua sendo cortada"
    assert "sequência de 3-bets" in saida


# ---- 2) quando cortar for inevitável, não mentir ---------------------------

def test_corte_nao_parte_palavra_no_meio():
    saida = texto_para_o_juiz(_analise_longa(9000), teto=600)
    corpo = saida.split("[NOTA DO AUDITOR")[0].rstrip()
    assert corpo, "cortou tudo"
    assert corpo[-1] in ".!?;\n", (
        f"cortou no meio da frase: …{corpo[-40:]!r}")


def test_o_corte_se_declara_como_sendo_do_AUDITOR():
    """O ponto inteiro: o juiz precisa saber que o corte é dele, senão
    desconta nota do coach por uma frase que o coach terminou."""
    saida = texto_para_o_juiz(_analise_longa(9000), teto=600)
    assert "NOTA DO AUDITOR" in saida
    assert "incompleta" in saida.lower(), (
        "o aviso não diz explicitamente para não chamar de frase incompleta")


def test_texto_no_limite_exato_nao_ganha_aviso():
    exato = "a" * TETO_DO_TEXTO_JULGADO
    assert "NOTA DO AUDITOR" not in texto_para_o_juiz(exato)


# ---- 3) o caminho de produção usa a função --------------------------------

def test_a_nota_passa_pelo_preparo_em_vez_de_fatiar_cru():
    fonte = inspect.getsource(_nota_uma)
    assert "texto_para_o_juiz" in fonte, (
        "o juiz voltou a fatiar o texto direto")
    assert "[:1500]" not in fonte, "o corte cego de 1500 continua lá"
