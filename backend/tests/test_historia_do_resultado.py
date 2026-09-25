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
    assert h["mao_final_dos_viloes"]["ImperadorJuju"] == \
        "full de 10 com 5 (trinca de 10)"
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


def test_esta_ligada_na_analise_e_vira_evento(rodar_pipeline):
    """A história do resultado CHEGA ao prompt do modelo.

    Antes isto era `assert "historia_do_resultado" in inspect.getsource(...)`,
    que passa mesmo se o retorno da função for descartado. Aqui o coach falso
    guarda o `structured` que recebeu, e a asserção é sobre o que o modelo
    de fato viu.
    """
    from tests.test_pipeline_entrega_texto_conferido import _mao_do_full

    _saida, _repo, contexto = rodar_pipeline("Análise qualquer.",
                                             _mao_do_full())
    assert contexto.get("historia_do_resultado"), (
        "o modelo escreveu o desfecho sem receber a trajetória calculada")
    assert contexto.get("instrucao_historia"), (
        "a trajetória foi enviada sem a instrução de segui-la à risca — "
        "dado sem regra o modelo ignora")
    assert "não é opinião" in contexto["instrucao_historia"]


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
    assert h["sua_mao_final"] == "full de 7 com A (trinca de 7)"
    assert h["mao_final_dos_viloes"]["arisn"] == "full de 7 com 2 (trinca de 7)"


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


def test_showdown_errado_vira_evento(rodar_pipeline):
    """O evento carrega a mão CITADA e a REAL — sem os dois não dá para
    separar 'o modelo inventou' de 'o parser leu errado'."""
    from tests.test_pipeline_entrega_texto_conferido import (TEXTO_ERRADO,
                                                             _mao_do_full)

    _saida, repo, _ = rodar_pipeline(TEXTO_ERRADO, _mao_do_full())
    evento = repo.evento("showdown_errado")
    assert evento, "citou showdown errado e não virou evento"
    assert evento["citado"] == "77" and "72s" in evento["reais"]


def _mao_do_full():
    """A mão de 07/08 12:47 como CanonicalHand, para rodar o FILME nela."""
    from app.models.canonical import CanonicalHand

    return CanonicalHand(**{
        "game": "NLHE", "hero": "KKNUThS", "site": "PPPoker",
        "format": "tournament",
        "stakes": {"small_blind": 1.0, "big_blind": 2.0, "ante": 0.25,
                   "currency": "USD"},
        "hand_id": "t",
        "players": [
            {"name": "KKNUThS", "seat": 5, "stack": 100.0, "is_hero": True,
             "position": "SB"},
            {"name": "arisn", "seat": 0, "stack": 100.0, "is_hero": False,
             "position": "BTN"}],
        "streets": [{"name": "preflop", "board": [], "actions": []},
                    {"name": "flop", "board": ["2c", "7c", "7h"],
                     "actions": []},
                    {"name": "turn", "board": ["Ac"], "actions": []},
                    {"name": "river", "board": ["Th"], "actions": []}],
        "hero_cards": ["As", "7s"],
        "final_board": ["2c", "7c", "7h", "Ac", "Th"],
        "shown_cards": {"arisn": ["2d", "7d"]},
        "collected": {"KKNUThS": 160.0}, "total_pot": 160.0,
    })


def test_o_desenho_e_a_historia_contam_a_MESMA_coisa():
    """O filme acertou tudo ("7 cheio de 2" / "7 cheio de A" / VOCÊ leva) e o
    texto do modelo, na MESMA mensagem, inventou um 77. As duas camadas
    determinísticas saem de describe_hand — se divergirem um dia, o aluno vê
    duas versões do mesmo showdown lado a lado, que foi o estrago aqui.
    """
    from app.analysis.historia import historia_do_resultado
    from app.bot.processing import film_bands

    h = _mao_do_full()
    banda = [b for b in film_bands(h) if b.get("name") == "Resultado"][0]
    hist = historia_do_resultado(h)

    # o herói leva o pote nas duas leituras
    assert hist["ganhou"]
    assert any("VOCÊ leva o pote" in l for l in banda["lines"])

    # e as mãos finais têm o MESMO nome nas duas
    assert hist["sua_mao_final"] == "full de 7 com A (trinca de 7)"
    assert any(hist["sua_mao_final"] in l for l in banda["lines"])
    revelado = {r["who"]: r["desc"] for r in banda["reveals"]}
    assert revelado["arisn (BTN) mostra"] == "full de 7 com 2 (trinca de 7)"
    assert hist["mao_final_dos_viloes"]["arisn"] == \
        revelado["arisn (BTN) mostra"]


def test_a_nomenclatura_do_full_house_esta_certa():
    """'7 cheio de 2' = trinca de 7 + par de 2 (sevens full of twos). Os dois
    têm trinca de 7 (duas na mesa, uma de cada); decide o PAR que acompanha."""
    from app.analysis.equity import describe_hand

    board = ["2c", "7c", "7h", "Ac", "Th"]
    assert describe_hand(["2d", "7d"], board) == "full de 7 com 2 (trinca de 7)"
    assert describe_hand(["As", "7s"], board) == "full de 7 com A (trinca de 7)"
    # e o desempate é o par: A > 2, então o herói leva
    from app.analysis.equity import equity_vs_hands
    assert equity_vs_hands(["As", "7s"], [["2d", "7d"]], board) == 1.0
