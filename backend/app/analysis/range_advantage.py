"""Range advantage / nut advantage — o conceito nº 1 do pós-flop moderno.

Em cada board, quem conecta melhor: o range de quem agrediu pré ou o de quem
pagou? Duas medidas determinísticas:

- EQUITY advantage: equity média do range A contra o range B neste board
  (quem tem >55% "é dono" do board e pode c-betar barato com tudo);
- NUT advantage: fração dos combos de cada range que são premium AQUI
  (equity ≥70% contra o range adversário) — quem tem mais monstros dita as
  apostas GRANDES, mesmo sem vantagem de equity média.

Do par de números sai o conselho clássico: vantagem dupla = aposta pequena
frequente; só nut advantage = polarize grande; nenhuma = cheque muito.
"""
from __future__ import annotations

import numpy as np

from app.analysis.ranges import expand_combos, parse_range
from app.analysis.river_solver import _equity_matrix

_MAX = 420
_NUT_EQ = 0.70


def range_advantage(board: list[str], range_a: str, range_b: str,
                    label_a: str = "agressor", label_b: str = "defensor") -> dict:
    """Compara os dois ranges no board (3-5 cartas). Determinístico."""
    if not 3 <= len(board) <= 5:
        raise ValueError("board de 3 a 5 cartas")
    dead = set(board)
    a = expand_combos(parse_range(range_a), dead)
    b = expand_combos(parse_range(range_b), dead)
    if not a or not b:
        raise ValueError("range vazio dado o board")
    if len(a) > _MAX or len(b) > _MAX:
        raise ValueError("range grande demais; use um range mais estreito")

    E = _equity_matrix(a, b, list(board))          # E[i,j] = equity de A_i vs B_j
    M = np.array([[0.0 if set(ca) & set(cb) else 1.0 for cb in b]
                  for ca in a])
    w = M.sum(axis=1)
    eq_a = float((E * M).sum() / max(M.sum(), 1.0))          # equity média de A
    eq_combo_a = (E * M).sum(axis=1) / np.maximum(w, 1.0)     # por combo de A
    wb = M.sum(axis=0)
    eq_combo_b = ((1.0 - E) * M).sum(axis=0) / np.maximum(wb, 1.0)

    nuts_a = float((eq_combo_a >= _NUT_EQ).mean())
    nuts_b = float((eq_combo_b >= _NUT_EQ).mean())

    # veredito clássico do par (equity média, densidade de nuts)
    eq_edge = eq_a - 0.5
    if eq_edge >= 0.05 and nuts_a >= nuts_b:
        verd = (f"board do {label_a}: c-bet PEQUENO e frequente funciona "
                "com o range inteiro")
    elif nuts_a > nuts_b * 1.5 and nuts_a >= 0.08:
        verd = (f"{label_a} tem o NUT advantage: polarize — apostas GRANDES "
                "com monstros e blefes, cheque o miolo")
    elif eq_edge <= -0.05:
        verd = (f"board do {label_b}: {label_a} deve chequar muito; "
                f"apostar aqui é queimar fichas contra range que conectou")
    else:
        verd = ("board neutro: sem vantagem clara — jogo de ranges mistos, "
                "posição e leitura pesam mais que agressão automática")

    return {
        "board": list(board),
        "equity_media": {label_a: round(eq_a * 100, 1),
                         label_b: round((1 - eq_a) * 100, 1)},
        "nuts_pct": {label_a: round(nuts_a * 100, 1),
                     label_b: round(nuts_b * 100, 1)},
        "veredito": verd,
        "nota": (f"nuts = combos com ≥{_NUT_EQ*100:.0f}% de equity contra o "
                 "range adversário NESTE board; equity por enumeração/"
                 "amostragem de runouts (determinístico)"),
    }
