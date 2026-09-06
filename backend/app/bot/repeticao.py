"""REPETIÇÃO ESPAÇADA guiada por erro — e por que ela não pode MEDIR.

O sorteio do treino puxa mais das categorias em que o aluno erra, e conforme
a taxa de acerto sobe o peso decai sozinho. Isso é ótimo para TREINAR.

E é fatal para MEDIR: quando o aluno melhora, o boost cai, o mix de spots
muda, e a taxa de acerto observada muda por mudança de AMOSTRA, não de
habilidade. Qualquer série temporal montada em cima do drill normal é
ininterpretável por construção. Por isso existe o drill de AFERIÇÃO, com
sorteio uniforme — e só ele conta como medida.

Saiu do processing.py: são funções puras (conferido por AST) e mudam por um
motivo diferente do resto do arquivo.
"""
from __future__ import annotations


def drill_category(drill: dict) -> str:
    """Categoria de LEAK de um spot de treino — o eixo da repetição espaçada.

    push_fold (pré-flop curto em torneio) é separado do pré-flop deep porque
    o erro é de natureza diferente (Nash vs range de abertura)."""
    st = (drill.get("street") or "preflop").lower()
    if st != "preflop":
        return st
    stk = drill.get("stack_bb")
    if stk and stk <= 20 and drill.get("format") in ("tournament", "sng"):
        return "push_fold"
    return "preflop"


def leak_error_rates(verdicts: list[dict]) -> dict[str, dict]:
    """Taxa de erro por categoria a partir dos eventos drill_verdict
    (ruim=1, mista=0.5, boa=0), com suavização de Laplace — um erro isolado
    não vira leak. Eventos antigos sem 'cat' são ignorados."""
    peso = {"boa": 0.0, "mista": 0.5, "ruim": 1.0}
    agg: dict[str, list[float]] = {}
    for v in verdicts or []:
        cat, verd = v.get("cat"), v.get("verdict")
        if cat and verd in peso:
            agg.setdefault(cat, []).append(peso[verd])
    out: dict[str, dict] = {}
    for cat, errs in agg.items():
        n = len(errs)
        out[cat] = {"n": n, "erros": round(sum(errs), 1),
                    "taxa": round((sum(errs) + 1.0) / (n + 2.0), 3)}
    return out


def leak_boost(rates: dict[str, dict], cat: str) -> float:
    """Multiplicador de peso no sorteio do drill: categorias em que o aluno
    ERRA aparecem mais (até ~4x); sem histórico ou indo bem, fica em 1.
    Conforme a taxa de acerto sobe, o boost cai sozinho — é a repetição
    espaçada guiada por erro."""
    r = rates.get(cat) or {}
    if not r or r.get("n", 0) < 1:
        return 1.0
    return 1.0 + max(0.0, r["taxa"] - 0.4) * 6.0


_CAT_NOMES = {"push_fold": "pré-flop de stack curto (push/fold)",
              "preflop": "pré-flop", "flop": "flop", "turn": "turn",
              "river": "river"}


# 1 a cada 5. Menos que isso e a medição nunca junta amostra; mais e o
# treino perde a força, porque é o boost que faz o aluno praticar onde dói.
A_CADA = 5


def e_afericao(drills_feitos: int) -> bool:
    """Este drill é de AFERIÇÃO (sorteio uniforme, entra na medida)?

    A conta é do NÚMERO de drills já respondidos, não de sorteio aleatório:
    aleatório pode passar semanas sem cair uma aferição justamente no aluno
    que treina pouco — que é quem menos tem amostra para perder.
    """
    return drills_feitos > 0 and drills_feitos % A_CADA == 0
