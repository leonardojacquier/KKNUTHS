"""O prompt pede a voz nova — e não briga com o que já pedia."""
from __future__ import annotations

import inspect
import re

from app.agent import llm

PROMPT = llm._SYSTEM["pt"]


def _instrucoes_de(fn) -> str:
    """O fonte com os literais COSTURADOS.

    A primeira versão deste teste lia `inspect.getsource` cru e passava mesmo
    com o defeito no lugar: a frase estava quebrada entre dois literais
    Python (`"Feche com A conta que "` / `"mais pesa. "`), então a substring
    que ele procurava não existia no fonte. Teste decorativo — verde pela
    formatação do arquivo, não pelo conteúdo do prompt.
    """
    fonte = inspect.getsource(fn)
    costurado = re.sub(r'"\s*\n\s*"', "", fonte)   # junta literal quebrado
    return re.sub(r"\s+", " ", costurado)          # e normaliza o espaço


def test_a_instrucao_nao_planta_mais_o_titulo_fixo():
    """llm.py:1854 mandava 'Feche com A conta que mais pesa.' — o formulário
    que apareceu em 25% das análises era pedido nosso, por escrito."""
    fonte = _instrucoes_de(llm.coach)
    assert "conta que mais pesa" not in fonte.lower(), \
        "a instrução do coach ainda planta o título fixo"


def test_a_instrucao_do_coach_proibe_recitar_e_nao_qualquer_numero():
    """A ordem contrária estava no lugar MAIS forte, e verde.

    O R3 aprendeu a distinguir RECITAR a conta (proibido) de contar a
    história do desfecho com as % de cada street (obrigatório, R5b). A
    `instruction` continuava com a redação em bloco que o R3 aposentou —
    'sem repetir número que já está no placar' — e ela não vai no system:
    vai no TURNO DE USUÁRIO, que pesa mais. Na prática a contradição
    R3 × R5b seguia de pé com a suíte inteira verde, porque nenhum teste
    lia o texto da instrução.
    """
    fonte = _instrucoes_de(llm.coach)
    assert "repetir número" not in fonte.lower(), \
        "a instrução ainda manda calar qualquer número repetido"
    assert "recitar" in fonte.lower(), \
        "a instrução tem que proibir a RECITAÇÃO da conta, não o número"


def test_a_instrucao_do_followup_proibe_recitar_e_nao_qualquer_numero():
    """Gêmeo do de cima: o bloco de voz da conversa tinha a mesma ordem."""
    fonte = _instrucoes_de(llm.followup)
    assert "repetir número" not in fonte.lower(), \
        "o bloco de voz do followup ainda manda calar número repetido"
    assert "recitar" in fonte.lower()


def test_o_prompt_proibe_o_titulo_fixo():
    assert "conta que mais pesa" in PROMPT.lower(), \
        "o prompt precisa NOMEAR o título para proibi-lo"


def test_o_prompt_proibe_repetir_numero_do_placar_no_fechamento():
    baixo = PROMPT.lower()
    assert "já apareceu no placar" in baixo or "repet" in baixo


def test_o_prompt_manda_explicar_o_conceito():
    assert "por que" in PROMPT.lower() or "porquê" in PROMPT.lower()


def test_o_prompt_permite_parentese_didatico_na_primeira_aparicao():
    """O V4 antigo PROIBIA parêntese didático na análise. O dono pediu
    conceito + termo explicados, então a proibição vira exceção regrada."""
    baixo = PROMPT.lower()
    assert "primeira aparição" in baixo or "primeira vez" in baixo


def _regra(nome: str, seguinte: str) -> str:
    return re.search(rf"{nome} .*?(?={seguinte} )", PROMPT, re.S).group(0)


def test_o_guarda_conhece_todos_os_rotulos_que_o_R3_proibe():
    """I2 — o guarda conhecia UM rótulo e o R3 proíbe TRÊS.

    O modelo obedece à proibição mais específica (a que tem nome próprio),
    troca 'A conta que mais pesa:' por 'Resumo:' e nada vê: _TITULO_FIXO não
    casa, limpar não mexe, problemas_de_voz não aponta, com_titulo_fixo = 0.
    Todos os contadores dizem sucesso com o formulário intacto sob cabeçalho
    novo.

    Este teste lê os rótulos DO PROMPT e cobra cada um do guarda — quem
    acrescentar um quarto rótulo lá é obrigado a ensiná-lo aqui.
    """
    from app.bot.guarda_voz import problemas_de_voz

    proibicao = _regra("R3", "R4").split("PROIBIDO RECITAR", 1)[0]
    rotulos = re.findall(r"'([^']+:)'", proibicao)
    assert len(rotulos) >= 3, "o R3 parou de nomear os rótulos proibidos"
    for rot in rotulos:
        t = f"✅ Você jogou bem\n\n{rot} com 12bb, AK em HJ é jam pré-flop."
        assert any("título fixo" in p for p in problemas_de_voz(t)), (
            f"o R3 proíbe {rot!r} e o guarda não enxerga — o modelo troca de "
            "rótulo e todos os contadores dizem sucesso")


def test_o_R3_escreve_a_prioridade_dos_tres_fechadores():
    """I7 — três fechadores obrigatórios para duas vagas.

    R5b (a história do desfecho), C3b (o ICM que falta) e A1 (o aviso do
    gráfico) são todos obrigatórios quando a mão dispara os três, e o R3 dá
    no MÁXIMO 2 parágrafos. Sem prioridade escrita, o candidato a cair é o
    C3b: o único dos três que carrega um número computado que o placar não
    deu, e o único cuja ausência o aluno não tem como perceber.
    """
    r3 = _regra("R3", "R4")
    assert "PRIORIDADE" in r3, "o R3 põe três fechadores em duas vagas e não "\
        "diz qual cai"
    ordem = r3.split("PRIORIDADE", 1)[1]
    posicao = {r: ordem.index(r) for r in ("R5b", "C3b", "A1")}
    assert posicao["R5b"] < posicao["C3b"] < posicao["A1"], (
        "a prioridade tem que pôr o C3b acima do A1: o ICM é conta que o "
        f"placar não deu, o gráfico é aviso. Ordem escrita: {posicao}")


def test_o_bloco_de_voz_do_followup_nao_cala_a_resposta_ao_aluno():
    """I6 — o R3 ia sem escopo para a conversa.

    Na análise ele é escopado ('depois do placar'). Numa conversa não existe
    placar, e a pergunta mais comum do aluno é justamente pela conta ('por
    que −11bb?'). O resultado era resposta sem número — ou o guarda_saida
    grampeando um bloco calculado no fim, uma ida a mais na API no lugar da
    conversa natural que o dono pediu.
    """
    fonte = _instrucoes_de(llm.followup).lower()
    assert "recitar" in fonte
    escopo = fonte[fonte.index("recitar"):][:600]
    assert "pergunt" in escopo and "número" in escopo, (
        "proibir formulário virou proibir responder a pergunta feita")


def test_o_selo_e_o_placar_continuam_obrigatorios():
    """Regra de ouro. Nenhuma mudança de voz pode afrouxá-la."""
    assert "R1 SELO NA 1ª LINHA" in PROMPT
    assert "R2 PLACAR STREET A STREET" in PROMPT


def test_o_prompt_nao_pede_e_proibe_a_mesma_coisa():
    """O V4 novo manda explicar; o R7 proíbe parágrafo longo. A saída é a
    explicação morar DENTRO do porquê curto do placar — se o prompt não
    disser onde, ele briga consigo."""
    assert "dentro do porquê" in PROMPT.lower() or \
           "no porquê da linha" in PROMPT.lower()
