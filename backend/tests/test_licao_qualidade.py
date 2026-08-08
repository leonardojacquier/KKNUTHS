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


def test_infere_estrategia_de_uma_mao():
    """Lição 21, texto REAL da estante. O vício de resultado com roupa de
    número: passava pelos filtros porque não usa 'confirmou/provou'."""
    ruim = {**_LIMPA,
            "titulo": "Raise em CO com KJ suited — margem fina demais",
            "spot": "Cutoff com KJ suited faz raise de ~0.8bb em pote de "
                    "~1bb. A ação volta e leva -3.6bb no final.",
            "licao": "KJ suited em CO tem EV positivo contra ranges wide. "
                     "Aqui o resultado de -3.6bb mostra que ou os opponents "
                     "tinham range forte demais, ou o tamanho do raise não "
                     "era suficiente para isolar."}
    probs = problemas_da_licao(ruim)
    assert any("UMA mão" in p for p in probs), probs


def test_ev_no_texto_nao_e_inferencia():
    """'a lição PRECISA do número' — citar o EV não pode virar alarme."""
    ok = {**_LIMPA,
          "licao": "O call rende +7.6bb de EV contra o range de shove."}
    assert problemas_da_licao(ok) == []


def test_dominancia_falsa_e_barrada_com_as_cartas_da_mao():
    """Lição 26, texto REAL: 'Só AA e QQ te viram favorito' com KK na mão.

    QQ perde de KK em 80% das vezes. O guarda que sabe isso existia e não
    rodava aqui — e a frase é do tipo que o aluno leva pra mesa.
    """
    ruim = {"titulo": "KK contra shove curto: call automático",
            "spot": "CO empurra ~8.4bb efetivo. Você paga com KK.",
            "licao": "Com KK o call rende +7.6bb de EV. Só AA e QQ te viram "
                     "favorito — perder para trinca é variância, não erro.",
            "hero_cards": ["Kh", "Kd"], "board": []}
    probs = problemas_da_licao(ruim)
    assert any("QQ" in p and "dominância" in p for p in probs), probs

    # sem as cartas o portão fica cego — é exatamente o buraco que `com_cartas`
    # tapa, e o teste registra que a diferença vem DELAS
    assert not any("dominância" in p for p in
                   problemas_da_licao({k: v for k, v in ruim.items()
                                       if k != "hero_cards"}))


def test_dominancia_verdadeira_passa():
    ok = {**_LIMPA, "licao": "Só AA te vira favorito aqui.",
          "hero_cards": ["Kh", "Kd"], "board": []}
    assert not any("dominância" in p for p in problemas_da_licao(ok))


def test_receita_raise_menor_do_que_o_que_chamou_de_pequeno():
    """Lição 27, texto REAL: critica 3bb por ser pequeno e propõe 2.5x."""
    ruim = {"titulo": "Raise pequeno em UTG com par médio",
            "spot": "UTG com 7♦7♥ faz raise de ~3bb em um pote de ~3bb.",
            "licao": "Raise pequeno (3bb) em posição inicial com par médio "
                     "é fraco. Um raise padrão de 2.5x teria extraído mais "
                     "valor das blinds."}
    probs = problemas_da_licao(ruim)
    assert any("MENOR" in p for p in probs), probs


def test_descricao_do_spot_nao_conta_como_proposta():
    """O spot DESCREVE 'faz raise de ~3bb'; isso não é receita. Sem esta
    distinção o tamanho batia consigo mesmo e o teste acima passava por
    coincidência."""
    ok = {"titulo": "Raise pequeno em UTG",
          "spot": "UTG faz raise de ~3bb em um pote de ~3bb.",
          "licao": "Raise pequeno (3bb) em posição inicial é fraco. "
                   "Um raise padrão de 4x extrai mais valor."}
    assert not any("MENOR" in p for p in problemas_da_licao(ok))


def test_com_cartas_busca_a_mao_pelos_dois_saltos():
    """licoes.hand_analysis_id → hand_analysis.hand_id → hands.canonical."""
    from app.bot.licao_qualidade import com_cartas

    class _Can:
        hero_cards = ["Kh", "Kd"]
        final_board = ["2c", "7c", "7h", "9d", "Ts"]

    class _Res:
        def __init__(self, data):
            self.data = data

    class _T:
        def __init__(self, nome):
            self.nome = nome

        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def execute(self):
            return _Res([{"hand_id": "H1"}] if self.nome == "hand_analysis"
                        else [])

    class _Client:
        def table(self, nome):
            return _T(nome)

    class _Repo:
        enabled = True
        client = _Client()

        def get_hand_canonical(self, hid):
            return _Can() if hid == "H1" else None

    rico = com_cartas(_Repo(), {"id": 26, "hand_analysis_id": "A1"})
    assert rico["hero_cards"] == ["Kh", "Kd"]
    assert len(rico["board"]) == 5


def test_com_cartas_sem_banco_devolve_a_licao_intacta():
    """Falha silenciosa: sem cartas o portão volta ao que era, nunca pior."""
    from app.bot.licao_qualidade import com_cartas

    class _Repo:
        enabled = False

    assert com_cartas(_Repo(), {"id": 1, "titulo": "x"})["titulo"] == "x"


def test_portao_do_envio_usa_as_cartas():
    """Sem `com_cartas` no caminho do /licoes N ok, a checagem de fato de
    poker existe e nunca roda — foi assim que a 26 chegou à estante."""
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing.licoes_reply)
    assert fonte.count("problemas_da_licao(com_cartas(repo, linha))") == 2


def test_o_portao_para_o_ok_e_oferece_o_ja():
    """Sinaliza e para — mas não é prisão: o dono fura com /licoes N ja."""
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing.licoes_reply)
    assert "problemas_da_licao" in fonte
    assert "Não mandei" in fonte
    assert fonte.index("problemas_da_licao") < fonte.index("enviar_licao"), \
        "confere ANTES de enviar, não depois"
