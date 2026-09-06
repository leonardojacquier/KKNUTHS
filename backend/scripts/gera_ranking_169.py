"""Gera o RANKING_169 de app/analysis/combos.py — rode e cole a saída.

Uma vez, offline: equity de cada uma das 169 mãos iniciais contra mão
aleatória, Monte Carlo com seed FIXA (reproduzível), avaliador do próprio
repo. Em runtime o ranking é constante; este script existe para que a
constante tenha origem auditável, não memória de ninguém.

    PYTHONPATH=. ./venv/bin/python scripts/gera_ranking_169.py
"""
from app.analysis.equity import equity_vs_random

RANKS = "AKQJT98765432"
SEED = 1234
ITERACOES = 40_000


def _cartas(a: str, b: str, suited: bool) -> list[str]:
    if a == b:
        return [a + "s", b + "h"]
    return [a + "s", b + ("s" if suited else "h")]


def main() -> None:
    out = []
    for i, a in enumerate(RANKS):
        for b in RANKS[i:]:
            if a == b:
                rotulos = [a + b]
            else:
                rotulos = [a + b + "s", a + b + "o"]
            for rot in rotulos:
                eq = equity_vs_random(
                    _cartas(a, b, rot.endswith("s") and a != b),
                    iterations=ITERACOES, seed=SEED)
                out.append((rot, eq))
    out.sort(key=lambda t: (-t[1], t[0]))
    assert len(out) == 169
    for i in range(0, 169, 8):
        print("    " + " ".join(f'"{r}",' for r, _ in out[i:i + 8]))
    d = dict(out)
    print(f"# conferência: AA {d['AA']:.3f} · AKs {d['AKs']:.3f} · "
          f"32o {d['32o']:.3f}")


if __name__ == "__main__":
    main()
