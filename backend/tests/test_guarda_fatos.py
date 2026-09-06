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


def test_esta_ligado_na_analise_e_vira_evento(rodar_pipeline):
    """O guarda RODA e o texto entregue muda — ver
    tests/test_pipeline_entrega_texto_conferido.py para o caso completo."""
    from tests.test_pipeline_entrega_texto_conferido import (TEXTO_ERRADO,
                                                             _mao_do_full)

    saida, repo, _ = rodar_pipeline(TEXTO_ERRADO, _mao_do_full())
    assert "só perdia pra AA" in saida, "a dominância falsa chegou ao aluno"
    assert repo.evento("fato_corrigido"), "corrigiu e não virou evento"


def test_conta_anunciada_sem_numero_e_flagrada():
    """"A conta que mais pesa: você paga sempre, sem pensar duas vezes" é
    prosa com nome de conta — e era a 3ª vez que o texto dizia o mesmo."""
    from app.bot.guarda_fatos import conta_sem_numero

    ruim = ("A conta que mais pesa: com KK e stack curto você paga esse "
            "all-in sempre, sem pensar duas vezes.")
    assert conta_sem_numero(ruim)

    boa = ("A conta que mais pesa: pagar rende +8.2bb a mais que foldar "
           "contra o range de shove dele.")
    assert conta_sem_numero(boa) == []

    # texto sem anúncio de conta não é flagrado
    assert conta_sem_numero("✅ Você jogou bem — pagar KK.") == []


def test_pot_odds_em_razao_e_outs_CONTAM_como_conta():
    """O falso positivo é caro dos dois lados.

    `_TEM_NUMERO` exigia sufixo bb/%/fichas, e com isso reprovava as duas
    formas mais básicas da matemática de poker: preço em razão e outs. O
    evento passava a dizer que a análise enrolou justamente quando ela
    mostrou a conta certinha — e taxa de falso positivo alta treina o dono a
    ignorar o sinal.
    """
    from app.bot.guarda_fatos import conta_sem_numero

    # cada frase exercita UMA forma só. Misturar (ex.: outs junto de "18%")
    # faz a asserção passar pelo ramo errado, e aí apagar o ramo certo do
    # código não quebra teste nenhum — medido: a mutação que remove `outs`
    # sobrevivia enquanto a frase tinha um `%` do lado.
    for boa in (
            "A conta: o pote paga 2.5 para 1 aqui.",       # razão com "para"
            "A conta: o preço é 3:1 aqui.",                # razão com ":"
            "A conta: você tem 1 em 3 de acertar.",        # "X em Y"
            "A conta: você paga esse all-in 2 vezes em cada 10 mãos.",
            "A conta: são 9 outs limpos no river.",        # outs
            "A conta: são 5000 fichas no pote.",           # fichas
            "A conta: pagar rende +8.2bb a mais que foldar.",   # unidade
            "A conta: seu EV nessa linha fica -1,5 contra o range dele."):
        assert conta_sem_numero(boa) == [], f"falso positivo em: {boa}"


def test_numero_solto_continua_NAO_sendo_conta():
    """O outro lado, e o que impede a correção acima de virar afrouxamento.

    Trocar `_TEM_NUMERO` por `\\d` faria o guarda aceitar qualquer dígito e a
    suíte não notava (medido na auditoria de 09/08). Estas frases têm número
    e não têm conta — é exatamente o print de 07/08 que criou o guarda.
    """
    from app.bot.guarda_fatos import conta_sem_numero

    for ruim in (
            "A conta que mais pesa: com KK você paga sempre, sem pensar "
            "duas vezes.",
            "A conta que mais pesa: é sempre pagar, na 3a street inclusive.",
            "A conta: você tem 2 cartas boas e o vilão 1 ruim."):
        assert conta_sem_numero(ruim), f"deixou passar prosa vazia: {ruim}"


# ---- FASE 1.1: os guardas passam a CONSERTAR, não só anotar ----
# O auditor de linguagem cravou: "a conferência virou telemetria, que é um
# terceiro estado que não garante nada". Ele tem razão — a mão de 07/08 foi
# entregue ao aluno com os guardas LIGADOS, porque eles só registravam evento.

TEXTO_REAL = ("seu full de 7 com A só perdia pra 77 ou AA — o vilão apareceu "
              "com 77 exatos numa das duas combinações que faltavam.")


def _mao_do_full():
    from types import SimpleNamespace

    return SimpleNamespace(
        hero="KKNUThS", hero_cards=["As", "7s"],
        final_board=["2c", "7c", "7h", "Ac", "Th"],
        shown_cards={"arisn": ["2d", "7d"]},
        collected={"KKNUThS": 32132600})


def test_o_verbo_no_imperfeito_nao_escapa_mais():
    """O texto real dizia "só PERDIA pra 77" — o regex só pegava "perde"."""
    from app.bot.guarda_fatos import _DOMINANCIA

    for frase in ("só perde para AA", "só perdia pra 77", "só perdeu pro AA",
                  "só perderia para AA", "só estava atrás de AA"):
        assert _DOMINANCIA.search(frase), frase


def test_a_lista_de_maos_nao_engole_a_frase_seguinte():
    """`[^.;\\n]+` capturava até o ponto final: "só perdia pra 77 ou AA — o
    vilão apareceu com 72s" virava uma lista só, e a correção comia o trecho
    depois do travessão."""
    from app.bot.guarda_fatos import _DOMINANCIA

    m = _DOMINANCIA.search(TEXTO_REAL)
    assert m and "apareceu" not in m.group("maos")


def test_com_board_a_pergunta_e_sobre_a_mao_feita():
    """Frase de river conferida com equity PRÉ-FLOP é resposta certa para a
    pergunta errada: pré-flop 77 ganha de A7s, mas naquele board o herói tem
    full de 7 com A e 77 nem existe (três setes já à vista)."""
    from app.bot.guarda_fatos import quem_ganha_do_heroi

    hero, board = ["As", "7s"], ["2c", "7c", "7h", "Ac", "Th"]
    # sem board: 77 "ganha" (equity pré-flop de par contra A7s)
    assert "77" in quem_ganha_do_heroi(hero, ["77"])
    # com board: 77 sai, e AA (ases full) fica, que é a verdade da mesa
    com = quem_ganha_do_heroi(hero, ["77", "AA"], board)
    assert "77" not in com and "AA" in com


def test_a_cadeia_inteira_conserta_o_texto_entregue():
    from app.analysis.historia import corrigir_showdown
    from app.bot.guarda_fatos import conferir_dominancia

    h = _mao_do_full()
    txt, erro_sd = corrigir_showdown(TEXTO_REAL, h)
    txt, mentiras = conferir_dominancia(txt, list(h.hero_cards),
                                        list(h.final_board))
    assert erro_sd["citado"] == "77" and erro_sd["corrigido_para"] == "72s"
    assert mentiras == ["77"]
    assert "apareceu com 72s" in txt, "o showdown não foi corrigido"
    assert "só perdia pra AA" in txt, "a dominância não foi corrigida"
    assert "AA —" in txt, "espaço comido antes do travessão"
    # e o resto da frase sobreviveu
    assert "combinações que faltavam" in txt


def test_par_que_nao_cabe_no_baralho_e_flagrado():
    """"77" com 7♣7♥ no board e 7♠ na mão do herói: sobrou UM sete. A frase
    anterior do próprio texto dizia "quadra de 7 é impossível"."""
    from app.analysis.historia import cita_mao_impossivel

    h = _mao_do_full()
    assert cita_mao_impossivel(TEXTO_REAL, h) == ["77"]
    # par possível não é acusado
    assert cita_mao_impossivel("ele pode ter 99 aqui", h) is None


def test_os_guardas_novos_estao_ligados(rodar_pipeline):
    """Os dois guardas de showdown rodam no pipeline e o texto sai limpo."""
    from tests.test_pipeline_entrega_texto_conferido import (
        TEXTO_ERRADO, _mao_do_full as _mao_canonica)

    saida, repo, _ = rodar_pipeline(TEXTO_ERRADO, _mao_canonica())
    assert "apareceu com 72s" in saida, "showdown errado chegou ao aluno"
    assert repo.evento("showdown_errado"), "corrigiu e não virou evento"




# ---- os três furos do guarda, achados na auditoria de 09/08 ---------------

def test_a_virgula_nao_esconde_o_resto_da_lista():
    """O PIOR dos três, porque falha em silêncio.

    `[^.;,\\n—–]` excluía a vírgula, então "Você só perde para AA, QQ ou JJ"
    capturava apenas `AA`. Como AA é verdade, o guarda devolvia `erros=[]` —
    declarava a frase LIMPA com duas mentiras dentro. E aí o evento
    `fato_corrigido` não dispara e o portal registra a análise como
    conferida: pior que não checar.
    """
    novo, erros = conferir_dominancia("Você só perde para AA, QQ ou JJ.", KK)
    assert set(erros) == {"QQ", "JJ"}, (
        f"a lista parou na primeira vírgula: {erros}")
    assert "QQ" not in novo and "JJ" not in novo
    assert "AA" in novo


def test_virgula_que_NAO_e_lista_nao_e_engolida():
    """O outro lado: aceitar vírgula não pode fazer a lista comer a frase.
    Entre duas mãos de uma enumeração só cabem vírgula, espaço e conector."""
    t = "Só perde para AA, e por isso você paga esse all-in."
    novo, erros = conferir_dominancia(t, KK)
    assert erros == [] and novo == t

    # e com uma mão DEPOIS do texto que não é lista: "QQ" está na frase mas
    # não na enumeração. Sem o cortador, ela entraria e a correção comeria
    # metade da frase.
    t2 = "Você só perde para AA, e com QQ ele até paga mais leve."
    novo2, erros2 = conferir_dominancia(t2, KK)
    assert erros2 == [], f"pegou QQ que estava fora da lista: {erros2}"
    assert novo2 == t2


def test_frase_sobre_o_VILAO_nao_e_conferida_contra_o_heroi():
    """O guarda apagava informação CERTA sobre o oponente.

    "O vilão só perde para AA e KK" com o herói de KK virava "...só perde
    para AA": o guarda conferia contra `hero_cards` sem olhar de quem a frase
    fala. Guarda que estraga texto certo custa mais confiança que guarda
    ausente.
    """
    t = "O vilão só perde para AA e KK nesse spot."
    novo, erros = conferir_dominancia(t, KK)
    assert erros == [] and novo == t

    for outra in ("O oponente só está atrás de AA e KK.",
                  "Ele só perde para AA e KK."):
        assert conferir_dominancia(outra, KK) == (outra, [])


def test_mas_sujeito_de_terceira_pessoa_NAO_basta_para_pular():
    """A primeira versão do portão de sujeito quebrou o caso que criou este
    módulo inteiro.

    "O vilão só te vira favorito com QQ ou AA" tem sujeito de terceira pessoa
    E é sobre o herói, porque o objeto é o "te". O que decide é a referência
    ao aluno DENTRO da frase; o sujeito só desempata quando ela não existe.
    """
    t = "O vilão só te vira favorito com QQ ou AA, e isso é raro."
    novo, erros = conferir_dominancia(t, KK)
    assert erros == ["QQ"], "voltou a deixar passar o caso do print de 07/08"
    assert "QQ" not in novo and "e isso é raro" in novo


def test_o_guarda_de_fatos_roda_na_CONVERSA(monkeypatch):
    """Ele vivia num caminho só: a análise do upload.

    A conversa livre é onde "só perde para QQ" é MAIS provável — é nela que o
    aluno pergunta justamente sobre mãos. O texto novo saía do modelo barato
    e ia ao aluno sem nenhuma conferência de fato de poker.
    """
    from app.bot import processing as proc

    eventos = []

    class _Repo:
        enabled = True

        def log_event(self, tg, u, ev, det=None):
            eventos.append((ev, det))

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(proc, "get_repository", lambda: _Repo())
    ctx = {"context": {"mao": {"hero_cards": ["Kh", "Kd"],
                               "final_board": []}}}

    saida = proc._conferir_fatos_da_conversa(
        1, "t", "Aqui você só perde para QQ, então pode pagar.", ctx)

    assert "QQ" not in saida, f"a mentira chegou ao aluno na conversa: {saida}"
    assert any(ev == "fato_corrigido" and (d or {}).get("onde") == "conversa"
               for ev, d in eventos), (
        "corrigiu na conversa e não registrou de onde veio")


def test_sem_as_cartas_da_mao_a_conversa_passa_intacta():
    """Sem saber a mão do herói não dá para conferir nada — e inventar
    correção é pior que não conferir."""
    from app.bot import processing as proc

    t = "Aqui você só perde para QQ."
    assert proc._conferir_fatos_da_conversa(1, "t", t, {"context": {}}) == t
