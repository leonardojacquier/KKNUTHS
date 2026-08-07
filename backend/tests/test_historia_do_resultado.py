"""A narrativa do desfecho tem que sair da conta — caso real de 07/08.

O aluno (dono) empurrou A4o com 3.6bb, levou call de ATo e perdeu para um
full house. A análise fechou com "esse cooler de river (você tinha dois
pares, o vilão fechou full house)". A conta: 29% no pré, 29% no flop, 0% no
turn — nunca esteve na frente, a mão foi decidida no PRÉ e o river não mudou
nada. E os "dois pares" eram da MESA. Resposta do dono: "como pode ser tão
burro". Ele tinha razão — e um dia antes a mão de KK saiu com "virar trinca
foi azar DELE", o pronome apontando pro vilão que GANHOU.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.analysis.historia import historia_do_resultado, narrou_azar_inexistente

# a mão do print, campo a campo do canonical gravado no banco
MAO_A4 = SimpleNamespace(
    hero="KKNUThS",
    hero_cards=["Ad", "4h"],
    final_board=["7c", "5s", "5c", "Tc", "Th"],
    shown_cards={"ImperadorJuju": ["Ah", "Ts"],
                 "Caio@vaicurintia": ["5h"]},      # SB mostrou UMA carta
    collected={"ImperadorJuju": 25231600.0},
)

TEXTO_ERRADO = (
    "A conta que mais pesa: contra fold o shove rende +1.71bb, então mesmo "
    "levando esse cooler de river (você tinha dois pares, o vilão fechou "
    "full house), a decisão foi lucrativa no longo prazo.")


def test_a_mao_do_print_nunca_esteve_na_frente():
    h = historia_do_resultado(MAO_A4)
    assert h is not None
    assert not h["ganhou"]
    assert h["esteve_na_frente_em"] == []
    assert not h["river_mudou_o_vencedor"], "o river não decidiu nada"
    assert h["equity_pct"]["pre"] == pytest.approx(29, abs=3)
    assert h["equity_pct"]["turn"] == 0, "no turn o A4o estava morto"
    # a leitura proíbe exatamente o que a análise escreveu
    assert "PRÉ-FLOP" in h["leitura"] and "PROIBIDO" in h["leitura"]
    assert "cooler" in h["leitura"]


def test_as_maos_finais_tem_nome_certo():
    """"Você tinha dois pares" sem dizer que eram DA MESA foi metade do
    estrago — o campo dá o nome pronto para o coach citar."""
    h = historia_do_resultado(MAO_A4)
    assert "dois pares" in h["sua_mao_final"]
    assert "full house" in h["mao_final_dos_viloes"]["ImperadorJuju"]
    # o SB que mostrou UMA carta não entra: equity contra meia mão é chute
    assert "Caio@vaicurintia" not in h["mao_final_dos_viloes"]


def test_o_texto_do_print_e_flagrado():
    h = historia_do_resultado(MAO_A4)
    trecho = narrou_azar_inexistente(TEXTO_ERRADO, h)
    assert trecho and "cooler" in trecho


def test_variancia_sem_grito_de_cooler_passa():
    """Perder um 29/71 É variância — o que não pode é inventar a virada."""
    h = historia_do_resultado(MAO_A4)
    ok = ("O shove rende +1.7bb contra foldar. Você estava atrás desde o "
          "pré (29%) e não melhorou — resultado esperado, variância do "
          "spot, decisão certa.")
    assert narrou_azar_inexistente(ok, h) is None


def test_virada_de_verdade_pode_chamar_de_azar():
    """KK contra Q9s que vira trinca no river: aí SIM houve virada — o
    detector não pode acusar, e a leitura manda dizer que foi azar."""
    # board com a segunda dama SÓ no river: KK lidera até lá, a trinca vira
    mao_kk = SimpleNamespace(
        hero="KKNUThS", hero_cards=["Kd", "Kh"],
        final_board=["2c", "7d", "Qc", "8s", "Qs"],
        shown_cards={"ImperadorJuju": ["Qh", "9s"]},
        collected={"ImperadorJuju": 55291600.0},
    )
    h = historia_do_resultado(mao_kk)
    assert h["esteve_na_frente_em"], "KK liderava antes do river"
    assert h["river_mudou_o_vencedor"]
    assert "azar" in h["leitura"]
    assert narrou_azar_inexistente("que cooler, hein", h) is None


def test_sem_showdown_completo_nao_inventa():
    sem = SimpleNamespace(hero="X", hero_cards=["Ad", "4h"],
                          final_board=["7c", "5s", "5c", "Tc", "Th"],
                          shown_cards={"Y": ["5h"]}, collected={})
    assert historia_do_resultado(sem) is None
    incompleta = SimpleNamespace(hero="X", hero_cards=["Ad", "4h"],
                                 final_board=["7c", "5s", "5c"],
                                 shown_cards={"Y": ["Ah", "Ts"]}, collected={})
    assert historia_do_resultado(incompleta) is None
    assert narrou_azar_inexistente("cooler", None) is None


def test_esta_ligada_na_analise_e_vira_evento():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "historia_do_resultado" in fonte
    assert "instrucao_historia" in fonte
    assert "narrativa_enganosa" in fonte, "grito de azar falso vira evento"


def test_o_prompt_manda_seguir_a_conta():
    import inspect

    from app.agent import llm

    fonte = inspect.getsource(llm)
    assert "R5b" in fonte
    assert "river_mudou_o_vencedor" in fonte
    # o par da mesa não é "seu par" (a frase é quebrada em literais no
    # fonte, então confere os pedaços)
    assert "NA MESA" in fonte and "seu par" in fonte
    # e o pronome do azar: quem virou teve SORTE
    assert "pronome do azar" in fonte


# ---- a mão do full house (07/08, 12:47): narrou derrota numa mão GANHA ----
# A♠7♠ em 2♣7♣7♥A♣10♥ = full de 7 com A; vilão mostrou 7♦2♦ = full de 7 com
# 2; collected no nome do herói. A análise fechou com "o vilão apareceu com
# 77 exatos numa das duas combinações que faltavam" — cooler invertido numa
# mão vencida, contradizendo o showdown gravado duas linhas acima.

MAO_FULL = SimpleNamespace(
    hero="KKNUThS", hero_cards=["As", "7s"],
    final_board=["2c", "7c", "7h", "Ac", "Th"],
    shown_cards={"arisn": ["2d", "7d"]},
    collected={"KKNUThS": 32132600},
)

TEXTO_INVERTIDO = (
    "*A conta que mais pesa:* seu full house full de 7 com A no river só "
    "perde pra quadra de 7 (impossível, você tem um), 1010 e AA — o vilão "
    "apareceu com 77 exatos numa das duas combinações que faltavam.")


def test_mao_ganha_tem_leitura_de_vitoria():
    from app.analysis.historia import historia_do_resultado

    h = historia_do_resultado(MAO_FULL)
    assert h["ganhou"]
    assert h["equity_pct"]["river"] == 100
    assert "GANHOU" in h["leitura"] and "PROIBIDO narrar derrota" in h["leitura"]
    assert "2d 7d" in h["leitura"], "a mão real do vilão vai na leitura"
    assert h["sua_mao_final"] == "full house (7 cheio de A)"
    assert h["mao_final_dos_viloes"]["arisn"] == "full house (7 cheio de 2)"


def test_showdown_citado_errado_e_flagrado():
    from app.analysis.historia import citou_showdown_errado

    erro = citou_showdown_errado(TEXTO_INVERTIDO, MAO_FULL)
    assert erro is not None
    assert erro["citado"] == "77"
    assert "72s" in erro["reais"]
    assert "apareceu com 77" in erro["trecho"]


def test_showdown_citado_certo_passa():
    from app.analysis.historia import citou_showdown_errado

    ok = ("O vilão mostrou 72s e o full dele era menor — seu 7 cheio de A "
          "leva. Você mostrou A7s e arrastou o pote.")
    assert citou_showdown_errado(ok, MAO_FULL) is None
    # falar de range ("range dele tem 77+") não é citar showdown
    assert citou_showdown_errado("o range de raise dele é 77+, AQ+",
                                 MAO_FULL) is None
    # e a palavra "as" minúscula nunca vira A♠ ("apareceu com as cartas")
    assert citou_showdown_errado("ele apareceu com as cartas viradas",
                                 MAO_FULL) is None


def test_sem_showdown_nao_ha_o_que_conferir():
    from app.analysis.historia import citou_showdown_errado

    sem = SimpleNamespace(hero="X", hero_cards=[], final_board=[],
                          shown_cards={}, collected={})
    assert citou_showdown_errado(TEXTO_INVERTIDO, sem) is None
    assert citou_showdown_errado("", MAO_FULL) is None


def test_showdown_errado_vira_evento():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "citou_showdown_errado" in fonte
    assert "showdown_errado" in fonte
