"""O SB de um MTT de 9 lugares não joga o mesmo jogo do SB de um HU.

Havia DOIS solvers exatos respondendo o mesmo spot, e discordando:

  · `jam_fold_solver`   — match heads-up: 2 antes no pote;
  · `open_shove_solver` — mesa de 9 com ante de TODOS: muito mais dinheiro
                          morto, e com mais dinheiro morto empurra-se mais largo.

Nenhum dos dois tem bug: são jogos diferentes. O defeito era o ROTEAMENTO —
`llm.py` mandava todo SB para o modelo heads-up, inclusive em mesa cheia, onde
ele sai sistematicamente tight. Medido em 25/08: discordam em 7% das mãos a
6bb e 12% a 20bb — e o erro CRESCE com o stack.

Caso âncora: SB, 6bb, 65o — mesa de 9 manda empurrar, HU manda largar.

O BB era pior ainda: caía na tabela estática de open-shove, que não é nem o
jogo dele (BB não abre de all-in — ele PAGA).
"""
from __future__ import annotations

import inspect

import pytest

from app.analysis.pushfold import push_fold

_65o = ["6h", "5s"]
_T5o = ["Th", "5s"]
_K2o = ["Kh", "2s"]


# ---- 1) o tamanho da mesa muda a resposta -----------------------------------

@pytest.mark.parametrize("cartas,nome", [(_65o, "65o"), (_T5o, "T5o")])
def test_mesa_cheia_empurra_o_que_o_heads_up_larga(cartas, nome):
    """Mais dinheiro morto = range mais largo. Se os dois derem igual, o
    roteamento por tamanho de mesa não está acontecendo."""
    mesa9 = push_fold(cartas, 6.0, "SB", jogadores=9)
    hu = push_fold(cartas, 6.0, "SB", jogadores=2)
    assert mesa9["decision"] == "push", f"{nome} em mesa de 9 é push"
    assert hu["decision"] == "fold", f"{nome} em HU é fold"


def test_mao_boa_e_push_nos_dois_jogos():
    """Controle: o teste acima não pode estar passando porque 'HU folda
    tudo'. K2o a 6bb é push nos dois modelos."""
    assert push_fold(_K2o, 6.0, "SB", jogadores=9)["decision"] == "push"
    assert push_fold(_K2o, 6.0, "SB", jogadores=2)["decision"] == "push"


def test_o_padrao_e_mesa_cheia_porque_o_produto_e_MTT():
    """Quem não informa a mesa está num MTT — não num HU de mesa final."""
    assert (push_fold(_65o, 6.0, "SB")["decision"]
            == push_fold(_65o, 6.0, "SB", jogadores=9)["decision"])
    assert push_fold(_65o, 6.0, "SB")["decision"] == "push"


def test_cada_modelo_se_declara():
    """Premissa que não se declara vira alucinação (METODO §1)."""
    mesa9 = push_fold(_65o, 6.0, "SB", jogadores=9)
    hu = push_fold(_65o, 6.0, "SB", jogadores=2)
    assert "9" in str(mesa9.get("premissas", "")), \
        "o veredito de mesa cheia não diz que assumiu mesa de 9"
    texto_hu = f"{hu.get('premissas', '')} {hu.get('nota', '')}".lower()
    assert "heads-up" in texto_hu or "hu" in texto_hu.split(), \
        "o veredito de HU não diz que assumiu heads-up"


# ---- 2) o BB não abre de all-in: ele paga ----------------------------------

def test_o_push_fold_recusa_o_BB_em_vez_de_inventar():
    """Era este o caminho velho: _POSITION_GROUP mapeava BB -> grupo 'SB' e
    devolvia range de OPEN-SHOVE para quem estava decidindo um CALL.

    A recusa é `applicable: False` de propósito — os seis chamadores de
    push_fold já conferem esse campo, então nenhum deles precisa aprender
    um vocabulário novo."""
    r = push_fold(_65o, 6.0, "BB", jogadores=9)
    assert r["applicable"] is False
    assert "call" in r["reason"].lower()
    assert "aproximação" not in str(r.get("note", ""))


def test_o_veredito_de_shove_nunca_recebe_um_dicionario_de_call():
    """A regressão que isto prende: se `push_fold` devolvesse
    decision='call'/'fold' para o BB, o relatório mão a mão chamaria de
    '❌ shove exagerado' TODO all-in do BB (decision != 'push'), e o /treino
    estouraria KeyError procurando `shove_range_pct`."""
    for pos in ("UTG", "MP", "CO", "BTN", "SB", "BB"):
        r = push_fold(_65o, 8.0, pos)
        if r.get("applicable"):
            assert r["decision"] in ("push", "fold"), \
                f"{pos} devolveu vocabulário de call num veredito de shove"
            assert "shove_range_pct" in r, f"{pos} sem shove_range_pct"


def test_a_decisao_de_call_mora_na_sua_propria_funcao():
    from app.analysis.pushfold import call_de_allin

    r = call_de_allin(_65o, 6.0, "BTN")
    assert r["applicable"] and r["decision"] in ("call", "fold")
    assert "call_range_pct" in r


def test_o_BB_paga_mais_largo_contra_o_BTN_do_que_contra_UTG():
    """Sanidade do modelo: o BTN empurra mais largo, então o BB paga mais
    largo contra ele. Se o vilão não muda nada, o parâmetro é decorativo."""
    from app.analysis.pushfold import call_de_allin

    contra_btn = call_de_allin(_K2o, 10.0, "BTN")
    contra_utg = call_de_allin(_K2o, 10.0, "UTG")
    assert contra_btn["call_range_pct"] > contra_utg["call_range_pct"], (
        "a posição de quem empurrou não mudou o range de call do BB")


def test_o_call_em_HU_usa_o_modelo_de_HU():
    from app.analysis.pushfold import call_de_allin

    hu = call_de_allin(_65o, 6.0, "SB", jogadores=2)
    assert str(hu.get("role", "")).upper() == "BB" or "heads-up" in \
        f"{hu.get('nota', '')}".lower()


# ---- 3) a porta é uma só ---------------------------------------------------

def test_o_llm_nao_roteia_mais_todo_SB_para_o_modelo_HU():
    from app.agent import llm

    fonte = inspect.getsource(llm._run_tool) if hasattr(llm, "_run_tool") \
        else inspect.getsource(llm)
    trecho = fonte[fonte.index('if name == "push_fold"'):][:800]
    assert 'nash_jam_fold(args["cards"]' not in trecho, (
        "llm.py ainda chama o modelo heads-up direto — a decisão de qual "
        "jogo modelar tem que morar num lugar só (pushfold.push_fold)")
    assert "jogadores" in trecho, \
        "o tool não repassa o tamanho da mesa para o motor"


def test_a_tool_do_agente_expoe_o_tamanho_da_mesa():
    from app.agent import llm

    tool = next(t for t in llm.TOOLS if t["name"] == "push_fold")
    props = tool["input_schema"]["properties"]
    assert "jogadores" in props, (
        "sem esse campo o modelo não tem como dizer que é mesa final HU")
