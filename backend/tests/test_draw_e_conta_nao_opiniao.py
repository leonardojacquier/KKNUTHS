"""'Ele tinha flush draw?' — 'Não, sem flush draw nenhum.' Tinha.

24/09, 23:45-23:46. Mão do PDQ: vilão com A♦7♦, flop 5♠4♦Q♦. São QUATRO
ouros — dois na mão, dois no board. Flush draw de livro, 9 outs.

O coach errou TRÊS vezes seguidas:
  1. "e como jogou o vilão?" → "A high puro: sem par, sem draw de verdade";
  2. "ele tinha flush draw?" → "Não, sem flush draw nenhum... precisaria de
     mais duas cartas do naipe";
  3. "você tá errado" → começou certo ("4 cartas do mesmo naipe, 9 outs"),
     se "corrigiu" no parágrafo seguinte e fechou com "minha resposta
     original tava certa".

Nenhum guarda pegou porque nenhum conferia draw. O gabarito da conversa
tinha mão feita street a street, showdown, textura do board — e NÃO tinha
draw. O modelo contou naipe de cabeça. É exatamente a classe de coisa que o
METODO tira do modelo: contagem é conta, e conta não é opinião.
"""
from __future__ import annotations

import pytest

from app.analysis.draws import draws, draws_por_street
from app.bot.guarda_fatos import conferir_draws

_FLOP = ["5s", "4d", "Qd"]
_A7 = ["Ad", "7d"]


# ---- 1) a conta ------------------------------------------------------------

def test_o_caso_real_e_flush_draw_com_9_outs():
    d = draws(_A7, _FLOP)
    assert d["flush_draw"] is True
    assert d["outs_flush"] == 9
    assert d["naipe"] == "d"


@pytest.mark.parametrize("cartas,board,esperado", [
    (["Ad", "7d"], ["5s", "4d", "Qd"], True),     # 2 + 2
    (["Ad", "7c"], ["5d", "4d", "Qd"], True),     # 1 + 3 (draw de uma carta)
    (["Ad", "7d"], ["5s", "4c", "Qd"], False),    # 2 + 1: backdoor, não draw
    (["Ad", "7c"], ["5s", "4d", "Qd"], False),    # 1 + 2
    (["Ah", "7h"], ["5d", "4d", "Qd"], False),    # naipe errado
    (["Ad", "7d"], ["5d", "4d", "Qd"], False),    # já é flush feito
])
def test_flush_draw_e_4_do_naipe_usando_carta_da_mao(cartas, board, esperado):
    assert draws(cartas, board)["flush_draw"] is esperado


def test_quatro_no_board_sem_carta_da_mao_nao_e_draw_do_jogador():
    """4 ouros no board e nenhum na mão: o draw é do BOARD, não dele."""
    assert draws(["Ah", "7c"], ["5d", "4d", "Qd", "2d"])["flush_draw"] is False


def test_flush_feito_e_reconhecido():
    assert draws(["Ad", "7d"], ["5d", "4d", "Qs", "2d"])["flush_feito"] is True


def test_no_river_nao_existe_draw():
    assert draws(_A7, _FLOP + ["Ks", "2c"])["flush_draw"] is False


@pytest.mark.parametrize("cartas,board,tipo", [
    (["8h", "7c"], ["6d", "5s", "Kh"], "oesd"),      # 5-6-7-8: 4 ou 9
    (["9h", "7c"], ["6d", "5s", "Kh"], "gutshot"),   # precisa do 8
    (["Ah", "Kc"], ["Qd", "Js", "2h"], "gutshot"),   # A-K-Q-J: só o T
    (["2h", "3c"], ["4d", "Ks", "Qh"], None),        # 2-3-4 não é draw
])
def test_draw_de_sequencia(cartas, board, tipo):
    assert draws(cartas, board)["sequencia"] == tipo


def test_roda_com_as_baixo():
    """A-2-3-4 é gutshot pro 5 (a roda)."""
    assert draws(["Ah", "2c"], ["3d", "4s", "Kh"])["sequencia"] == "gutshot"


def test_por_street_diz_QUANDO_o_draw_existia():
    s = draws_por_street(_A7, _FLOP + ["5c", "3h"])
    assert s["flop"]["flush_draw"] is True
    assert s["turn"]["flush_draw"] is True
    assert "river" not in s, "river não tem draw — só mão feita"


def test_texto_do_gabarito_e_citavel():
    """O coach copia do gabarito — tem que vir pronto em português."""
    s = draws_por_street(_A7, _FLOP)
    assert "flush draw" in s["flop"]["texto"]
    assert "9 outs" in s["flop"]["texto"]


# ---- 2) o guarda -----------------------------------------------------------

_JOGADORES = {"heroi": ["Kc", "Kh"], "Vilão": _A7}


@pytest.mark.parametrize("frase", [
    "Não, sem flush draw nenhum. Ele pagou com A high.",
    "pagou o shove só com A♦7♦, sem flush draw e sem par",
    "A high puro: sem par, sem draw de verdade nesse board",
    "precisaria de mais duas cartas do naipe pra ter draw, e isso não existe",
    "nunca teve equity de draw real no momento da decisão dele",
])
def test_negar_o_draw_que_existe_e_corrigido(frase):
    texto, achados = conferir_draws(frase, _JOGADORES, _FLOP + ["5c", "3h"])
    assert achados, f"deixou passar: {frase}"
    assert "A♦7♦" in texto and "flush draw" in texto
    assert "9 outs" in texto


def test_a_correcao_nomeia_as_cartas_e_o_board():
    """Sem dizer DE QUEM, a correção seria outra frase ambígua."""
    texto, _ = conferir_draws("sem flush draw nenhum", _JOGADORES, _FLOP)
    assert "A♦7♦" in texto and "5♠4♦Q♦" in texto


def test_quem_nao_tinha_draw_pode_ser_dito_sem_draw():
    """O herói com KK não tinha draw — dizer isso é verdade."""
    jog = {"heroi": ["Kc", "Kh"]}
    texto, achados = conferir_draws("você não tinha draw nenhum, só o par",
                                    jog, _FLOP)
    assert not achados and texto == "você não tinha draw nenhum, só o par"


def test_afirmar_o_draw_que_existe_passa_intacto():
    frase = "ele tinha flush draw (9 outs) no momento do call"
    texto, achados = conferir_draws(frase, _JOGADORES, _FLOP)
    assert not achados and texto == frase


def test_texto_sem_assunto_de_draw_passa_intacto():
    frase = "✅ *Flop* — shove de 36.8bb com KK: overpair, valor puro."
    texto, achados = conferir_draws(frase, _JOGADORES, _FLOP)
    assert not achados and texto == frase


def test_nao_duplica_a_correcao():
    t1, _ = conferir_draws("sem flush draw nenhum", _JOGADORES, _FLOP)
    t2, achados = conferir_draws(t1, _JOGADORES, _FLOP)
    assert t2.count("Conferido na conta") == 1


def test_sem_cartas_conhecidas_do_vilao_nao_inventa():
    """Se o vilão não mostrou, não há o que conferir."""
    texto, achados = conferir_draws("sem flush draw nenhum",
                                    {"heroi": ["Kc", "Kh"]}, _FLOP)
    assert not achados


# ---- 3) ligado nos dois caminhos -------------------------------------------

def test_o_gabarito_do_analyzer_traz_os_draws():
    from app.bot.processing import _GABARITO_KEYS

    assert "draws_by_street" in _GABARITO_KEYS, (
        "conversa antiga não recebe o campo novo no refresh")


def test_a_conversa_confere_draws():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._conferir_fatos_da_conversa)
    assert "conferir_draws" in fonte


def test_a_analise_do_upload_confere_draws():
    """A conferência mora no corpo real do upload (`_process_upload_inner`;
    `process_upload` é a casca de cota/concorrência em volta dele)."""
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "_conferir_draws_e_registrar" in fonte
    assert fonte.index("conferir_dominancia") < fonte.index(
        "_conferir_draws_e_registrar"), "o guarda de draws saiu do bloco dos fatos"
