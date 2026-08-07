"""O botão 🎈 tem que ENTREGAR algo diferente do texto original.

Caso real (07/08, dono): "a simplificação tá igual ao texto principal". Não
era o prompt estar errado — a análise já sai em português simples e já glosa
os números entre parênteses ("+7.6bb de EV (você ganha 7.6 fichas em média
nessa situação)"), então "reescreva mais simples" não tinha o que fazer e
devolvia um parágrafo quase igual. Pedir de novo, com outras palavras, não
resolve: o que precisa mudar é a ESTRUTURA.

Aqui se testa a parte que não depende da API: a conferência.
"""
from __future__ import annotations

from app.agent.llm import parecidos

ORIGINAL = (
    "✅ Você jogou bem — pagar KK contra o all-in curto do CO\n\n"
    "Decisão única: CO empurrou 8.4bb efetivo e você paga com KK. Contra o "
    "range de shove dele nessa profundidade, o call rende +8.2bb de EV "
    "comparado a foldar — é um dos calls mais claros que existem em torneio.\n\n"
    "A conta que mais pesa: com KK e stack curto você paga esse all-in "
    "sempre, sem pensar duas vezes. O vilão só te vira favorito com AA."
)


def test_maquiagem_e_reprovada():
    """Trocar meia dúzia de palavras mantendo o mesmo texto não é simplificar."""
    quase_igual = ORIGINAL.replace("Decisão única", "Decisão só uma").replace(
        "mais claros", "mais óbvios")
    assert parecidos(ORIGINAL, quase_igual)
    assert parecidos(ORIGINAL, ORIGINAL)


def test_reescrita_com_outra_estrutura_passa():
    """A forma imposta — resumo, bullets curtos, UM número — usa vocabulário
    novo suficiente para não ser a mesma coisa."""
    simples = (
        "Em resumo: você pagou certo, foi jogada fácil.\n\n"
        "• Seu par é quase sempre o melhor aqui.\n"
        "• Ele arrisca tudo com muita coisa pior.\n"
        "• Fugir custaria fichas à toa.\n\n"
        "O número que importa: +8.2bb, ou seja, cada vez que aparece "
        "essa situação você fatura oito cegas e meia."
    )
    assert not parecidos(ORIGINAL, simples)


def test_texto_vazio_conta_como_nao_simplificado():
    assert parecidos(ORIGINAL, "")
    assert parecidos(ORIGINAL, "   ")


def test_acento_e_caixa_nao_enganam_a_conferencia():
    assert parecidos("Decisão Única com KK", "DECISAO UNICA COM KK")


def test_simplify_tenta_de_novo_antes_de_desistir():
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm.simplify)
    assert "parecidos(text, out)" in fonte, "não confere a 1ª tentativa"
    assert "_FORMA_SIMPLES" in fonte, "não impõe estrutura"
    # a 2ª tentativa existe e é conferida também
    assert "out2" in fonte and "parecidos(text, out2)" in fonte
    # desistir devolve None: quem chamou é que conta a verdade ao aluno
    assert "return None" in fonte


def test_as_duas_causas_dao_respostas_opostas():
    """API fora: o coach nem rodou, dizer 'já está simples' é mentira.
    API de pé e texto já simples: 'me embananei' é que é mentira."""
    import app.bot.processing as proc
    from app.agent import llm

    tg = 555002
    proc.LAST_ANALYSIS[tg] = {
        "context": {"coaching_anterior": "call correto: equity 31% > 25%"},
        "history": [], "hand_row_id": None, "user_id": None,
    }
    try:
        # sem chave: simplify() marca 'indisponivel' e o aluno ouve o padrão
        llm.LAST_SIMPLIFY_REASON = "indisponivel"
        out = proc.simplify_last(tg, "t")
        assert out and "embananei" in out
        assert "nível mais simples" not in out

        # API de pé, texto já simples: a verdade, e um convite a perguntar
        real = llm.simplify
        llm.simplify = lambda _t: None
        try:
            llm.LAST_SIMPLIFY_REASON = "ja_simples"
            out2 = proc.simplify_last(tg, "t")
        finally:
            llm.simplify = real
        assert out2 and "nível mais simples" in out2
        assert "embananei" not in out2
    finally:
        proc.LAST_ANALYSIS.pop(tg, None)
        llm.LAST_SIMPLIFY_REASON = ""
