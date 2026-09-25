"""Perfil de DECISÕES — o /stats de quem só manda replay e print.

VPIP/PFR/3-bet exigem a sessão inteira: replay e print são mãos ESCOLHIDAS
pelo aluno (as que doeram, as que ficaram na cabeça), e contar frequência
nelas é viés de seleção — o METODO §1 as tira do perfil de estilo, com
razão. A consequência de produto era outra: o aluno de clube, com 50 replays
mandados, ouvia do /stats "Ainda não tenho mãos suas". Falso.

O que essas mãos PODEM dizer sem viés é o veredito de cada decisão, que o
coach já deu e o aluno já leu: quantas saíram ✅/🟡/❌ e em que street o erro
se concentra. Isso não é frequência de jogo, é o placar das mãos que ele
trouxe — e é dito assim.
"""
from __future__ import annotations

import re

_SELO_GERAL = re.compile(r"^\s*(✅|🟡|❌)\s*(.*)$")
_SELO_STREET = re.compile(
    r"^(✅|🟡|❌)\s*\*(Pr[ée](?:-flop)?|Flop|Turn|River)\*", re.M | re.I)
_NOME = {"pre": "pré-flop", "pré": "pré-flop", "pre-flop": "pré-flop",
         "pré-flop": "pré-flop", "flop": "flop", "turn": "turn",
         "river": "river"}


def contar(resumos: list[str]) -> dict:
    """Conta os selos das análises entregues (primeira linha + placar)."""
    geral = {"✅": 0, "🟡": 0, "❌": 0}
    por_street: dict[str, dict[str, int]] = {}
    motivos_x: list[str] = []
    for r in resumos:
        if not r:
            continue
        m = _SELO_GERAL.match(r.strip().splitlines()[0])
        if m:
            geral[m.group(1)] += 1
            if m.group(1) == "❌" and len(motivos_x) < 3:
                motivo = m.group(2).split("—", 1)[-1].strip()
                if motivo:
                    motivos_x.append(motivo[:80])
        for s in _SELO_STREET.finditer(r):
            st = _NOME.get(s.group(2).lower(), s.group(2).lower())
            por_street.setdefault(st, {"✅": 0, "🟡": 0, "❌": 0})
            por_street[st][s.group(1)] += 1
    return {"geral": geral, "por_street": por_street, "motivos_x": motivos_x}


def texto(resumos: list[str], n_maos: int) -> str | None:
    c = contar(resumos)
    g = c["geral"]
    julgadas = sum(g.values())
    if not n_maos:
        return None
    linhas = [f"*Suas decisões* ({n_maos} mão(s) que você mandou)"]
    if julgadas:
        linhas.append(f"• Veredito do coach: ✅ {g['✅']} · 🟡 {g['🟡']} · "
                      f"❌ {g['❌']}")
        # onde o erro se concentra: a street com mais 🟡+❌, se houver
        ruins = {st: v["🟡"] + v["❌"] for st, v in c["por_street"].items()}
        if ruins and max(ruins.values()) > 0:
            pior = max(ruins, key=ruins.get)
            total = sum(c["por_street"][pior].values())
            linhas.append(f"• Onde mais escapa: *{pior}* — {ruins[pior]} de "
                          f"{total} decisões com 🟡/❌")
        if c["motivos_x"]:
            linhas.append("• Os ❌ mais recentes: " + "; ".join(c["motivos_x"]))
    linhas.append(
        "\n_VPIP, PFR e estilo precisam da sessão inteira: replay e print "
        "são mãos que você escolheu, e contar frequência nelas engana. "
        "Manda o histórico (.txt/.zip) de um torneio que eu traço o seu "
        "estilo também._")
    return "\n".join(linhas)


def perfil_de_decisoes(repo, user: dict | None, n_maos: int) -> str | None:
    """O /stats para quem só tem replay/print. None sem mão nenhuma."""
    if not n_maos:
        return None
    resumos = repo.get_analysis_summaries(user["id"]) \
        if user and getattr(repo, "enabled", False) else []
    return texto(resumos, n_maos)
