"""O solver dizia COM QUE ABSTRAÇÃO resolveu, mas não QUÃO PERTO chegou.

`METODO.md` manda toda taxa carregar sua margem. O `solve_river` declarava
honestamente a abstração ("sizings 50%/100%/all-in, uma raise no máximo") e
entregava frequência e EV **sem nenhuma medida de convergência** — não dava
para saber se aquele 7,2% estava a 0,2 ou a 3,5 pontos do equilíbrio.

Medido em 25/08 no river A♥K♦7♣2♠9♥ (pote 20, stack 60), contra o mesmo spot
resolvido a 20.000 iterações:

    400 iterações  -> 1,75 pp de erro médio (3,50 pp na pior ação)
  6.400 iterações  -> 0,23 pp

A medida barata que dá para carregar junto é o quanto as frequências ainda se
moviam na segunda metade do solve. Ela ACOMPANHA o erro real (0,70 / 0,53 /
0,27 pp para 400 / 1.600 / 6.400) mas o SUBESTIMA — cerca de 2× a 400
iterações. Por isso ela entra como **piso do erro**, nunca como margem: dizer
"±0,7pp" quando o erro é 1,75pp seria exatamente o número errado que o METODO
proíbe.
"""
from __future__ import annotations

from app.analysis import river_solver as R

_BOARD = ["Ah", "Kd", "7c", "2s", "9h"]
_OOP = "AA,KK,77,22,99,AK,AQ,AJ,KQ,QJ,JT,T9,98,87,76,65"
_IP = "AK,AQ,AJ,ATs,KQ,KJs,QJs,JTs,T9s,99,77,22,A5s,A4s"


def _resolve(iters: int) -> dict:
    R._CACHE.clear()
    return R.solve_river(_BOARD, _OOP, _IP, 20.0, 60.0, "oop",
                         iterations=iters)


def test_o_resultado_carrega_a_convergencia():
    conv = _resolve(400).get("convergencia")
    assert conv, "o solver entrega frequência sem dizer quão perto chegou"
    assert conv["iteracoes"] == 400
    assert conv["desvio_medio_pp"] >= 0
    assert conv["desvio_max_pp"] >= conv["desvio_medio_pp"]


def test_mais_iteracoes_convergem_mais():
    """Se o número não cai com mais trabalho, ele não está medindo nada."""
    pouco = _resolve(300)["convergencia"]["desvio_medio_pp"]
    muito = _resolve(4000)["convergencia"]["desvio_medio_pp"]
    assert muito < pouco, (
        f"4.000 iterações não convergiram mais que 300 "
        f"({muito} vs {pouco} pp)")


def test_a_medida_e_rotulada_como_PISO_e_nao_como_margem():
    """O ponto inteiro: ela subestima o erro real em ~2x. Vendê-la como
    margem de erro seria pior que não ter medida nenhuma."""
    conv = _resolve(400)["convergencia"]
    rotulo = str(conv.get("leitura", "")).lower()
    assert rotulo, "a medida saiu sem explicar o que é"
    assert "piso" in rotulo or "subestima" in rotulo, (
        "o rótulo não avisa que a medida é um piso do erro")
    assert "±" not in rotulo and "margem de erro" not in rotulo, (
        "está se vendendo como margem de erro — é o que o METODO proíbe")


def test_a_resposta_grosseira_se_denuncia_na_nota():
    """Quem lê a nota tem que saber que aquela resposta é grosseira, sem
    precisar abrir o dicionário de convergência."""
    grosseira = _resolve(100)
    assert "convergência" in grosseira["nota"].lower() or \
           "convergiu" in grosseira["nota"].lower(), \
        "solve pouco convergido não avisou na nota"


def test_a_nota_limpa_nao_polui_a_resposta_boa():
    fina = _resolve(6000)
    assert fina["convergencia"]["desvio_medio_pp"] < 0.5
    assert "grosseir" not in fina["nota"].lower()
