"""Leaks quantificados em dinheiro — fase 2 do motor bayesiano.

Cada leak tem um detector determinístico (oportunidade + escorregada + custo
estimado em BB). A taxa de escorregada é corrigida por shrinkage (prior do
field), então 1 vacilo em 2 chances não vira "leak crônico" — e o plano de
estudo sai rankeado por quanto cada leak custa por 100 mãos.

Custos: o de call caro é matemática exata (déficit de equity × pote); os de
shove/open perdido são estimativas conservadoras proporcionais à profundidade
da mão no range — sempre apresentados como estimativa.
"""
from __future__ import annotations

from app.analysis.bayes import shrunk_rate
from app.models.canonical import ActionType, CanonicalHand, StreetName

# prior do field para "taxa de escorregada" num spot (a maioria dos amadores
# erra às vezes): média 20%, força 6 observações-equivalentes
_LEAK_PRIOR = (20.0, 6.0)

LEAK_NAMES = {
    "open_perdido": "deixa de abrir mão de ataque (fold passivo pré)",
    "shove_perdido": "não vai de all-in com stack curto quando é lucrativo",
    "call_caro": "paga mais caro do que a mão vale pós-flop",
    "shove_largo": "vai de all-in largo demais",
}


def _hero_folded_pre(h: CanonicalHand) -> bool:
    pre = h.street(StreetName.PREFLOP)
    return bool(pre) and any(
        a.actor == h.hero and a.type == ActionType.FOLD for a in pre.actions
    )


def _hero_jammed_pre(h: CanonicalHand) -> bool:
    pre = h.street(StreetName.PREFLOP)
    return bool(pre) and any(
        a.actor == h.hero and a.all_in and a.type in
        (ActionType.RAISE, ActionType.BET, ActionType.CALL)
        for a in pre.actions
    )


def detect_leaks(hands: list[CanonicalHand]) -> list[dict]:
    """Leaks rankeados por custo. Hoje é uma CASCA sobre `taxonomia`.

    O corpo antigo era um laço monolítico com os quatro detectores embutidos,
    que contava oportunidade e escorregada na mesma passada. Funcionava, mas
    não dava para: (a) acrescentar um detector sem mexer no laço, (b) saber
    QUAIS mãos formaram cada número, (c) usar o mesmo diagnóstico no relatório
    de torneio e na medição de evolução. As três coisas são pré-requisito do
    plano de estudo baseado em problema.

    O formato de saída é o de antes, de propósito: `leaks_text` e o contexto
    do coach continuam funcionando sem tocar em nada.
    """
    from app.analysis.taxonomia import CODIGOS, agregar, observar

    n_maos = max(len(hands), 1)
    out = []
    for d in agregar(observar(hands), n_maos):
        # DECIDE PELO LIMITE INFERIOR, igual ao resto do sistema.
        #
        # Antes o corte era `taxa_mean < 25.0` — a MÉDIA, que é exatamente o
        # que `agregar` existe para não usar. Duas escorregadas em duas
        # chances davam média 100% e viravam leak de 15bb/100 aqui, enquanto
        # `agregar` já dizia `acima_da_tolerancia=False` (limite inferior de
        # 8%). Ou seja: a camada de limite inferior estava construída,
        # testada, e o caminho que fala com o aluno passava por fora dela.
        #
        # `acima_da_tolerancia` também respeita a tolerância PRÓPRIA de cada
        # código: limp tem referência 5%, subdefesa de BB tem 35%. Um corte
        # único de 25% acusava limp de menos e BB de mais.
        if d["escorregadas"] == 0 or d["custo_bb_100"] <= 0:
            continue
        if not d.get("acima_da_tolerancia"):
            continue
        largura = d["taxa_hi"] - d["taxa_lo"]
        out.append({
            "leak": d["codigo"],
            "nome": CODIGOS[d["codigo"]].nome,
            "oportunidades": d["oportunidades"],
            "escorregadas": d["escorregadas"],
            "taxa_pct": d["taxa_mean"],
            "taxa_lo": d["taxa_lo"],
            "taxa_hi": d["taxa_hi"],
            "confianca": ("alta" if largura <= 25.0 and d["oportunidades"] >= 8
                          else "media"),
            "custo_bb_100maos": d["custo_bb_100"],
            "exemplos": d["exemplos"],
            "pergunta": d["pergunta"],
        })
    out.sort(key=lambda x: -x["custo_bb_100maos"])
    return out


def leaks_text(leaks: list[dict]) -> str:
    """Bloco 'plano de estudo' em voz de coach para o /stats."""
    if not leaks:
        return ""
    linhas = ["\n\n🎯 *O que está te custando mais* (por 100 mãos)"]
    for lk in leaks[:2]:
        certeza = ("" if lk["confianca"] == "alta"
                   else " _(ainda confirmando — amostra curta)_")
        linhas.append(
            f"• {lk['nome']}: ~{lk['custo_bb_100maos']:g}bb — aconteceu em "
            f"{lk['escorregadas']} de {lk['oportunidades']} chances{certeza}")
        if lk.get("vies"):
            linhas.append(f"  ↳ 🧠 {lk['vies']}")
    linhas.append("_Me pergunta sobre qualquer um que eu abro as mãos._")
    return "\n".join(linhas)
