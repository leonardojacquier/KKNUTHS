"""Portão de qualidade: a lição fala com TODOS de uma vez.

Caso real — a #24 chegou à véspera do 1º broadcast com o spot dizendo
"13 outs" e a lição dizendo "12" (eu corrigi um campo e esqueci o outro).
A varredura da biblioteca mostrou que não era isolado: de 24 lições, 8
tinham conta de outs, raciocínio por resultado ou promessa absoluta.

Diferente da análise (vai para UM aluno, que contesta), a lição vai para
todos e leva a assinatura da ferramenta.
"""
from app.bot.licao_qualidade import problemas_da_licao, selo_de_qualidade

_LIMPA = {"titulo": "Iso contra limpers",
          "spot": "Isolou 2 limpers do SB com K♦J♦. Flop A♥6♦Q♦.",
          "licao": "São 12 outs (9 do flush + 3 do straight) = ~52%."}


def test_licao_limpa_passa():
    assert problemas_da_licao(_LIMPA) == []
    assert selo_de_qualidade(_LIMPA) == "✅ limpa"


def test_contradicao_de_outs_no_mesmo_card():
    """O defeito exato da #24: spot dizia 13, lição dizia 12."""
    ruim = {**_LIMPA,
            "spot": "nut flush draw + gutshot (13 outs)",
            "licao": "São 12 outs (9 do flush + 3 do straight)"}
    probs = problemas_da_licao(ruim)
    assert any("se contradiz" in p for p in probs)
    assert "12 outs" in probs[0] and "13 outs" in probs[0]


def test_mesma_contagem_repetida_nao_e_contradicao():
    ok = {**_LIMPA, "spot": "12 outs no flop", "licao": "os 12 outs dão 52%"}
    assert problemas_da_licao(ok) == []


def test_raciocinio_por_resultado_e_pego():
    """'O fold do BTN confirmou que a agressão funciona' — o vício que um
    coach deve COMBATER, não ensinar."""
    ruim = {**_LIMPA,
            "licao": "O fold do BTN confirmou que a agressão funciona aqui."}
    assert any("resultado" in p for p in problemas_da_licao(ruim))


def test_promessa_absoluta_e_pega():
    for frase in ("jam é obrigatório", "isso é +EV automático",
                  "sempre aposta esse flop", "ganho garantido"):
        probs = problemas_da_licao({**_LIMPA, "licao": frase})
        assert any("absoluta" in p for p in probs), frase


def test_licao_vazia_nao_ensina():
    assert any("sem spot" in p for p in
               problemas_da_licao({**_LIMPA, "spot": "  "}))
    assert any("sem lição" in p for p in
               problemas_da_licao({**_LIMPA, "licao": ""}))


def test_o_portao_para_o_ok_e_oferece_o_ja():
    """Sinaliza e para — mas não é prisão: o dono fura com /licoes N ja."""
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing.licoes_reply)
    assert "problemas_da_licao" in fonte
    assert "Não mandei" in fonte
    assert fonte.index("problemas_da_licao") < fonte.index("enviar_licao"), \
        "confere ANTES de enviar, não depois"
