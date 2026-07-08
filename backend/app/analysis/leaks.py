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
    """Varre as mãos e devolve os leaks rankeados por custo (bb/100)."""
    from app.agent.analyzer import analyze_hand
    from app.analysis.handreport import _facing_preflop, played_facts
    from app.analysis.pushfold import push_fold
    from app.analysis.ranges import OPEN_RANGES, parse_range

    counts = {k: {"opp": 0, "miss": 0, "custo": 0.0, "exemplos": []}
              for k in LEAK_NAMES}

    def hit(key: str, custo: float, hand_id: str) -> None:
        c = counts[key]
        c["miss"] += 1
        c["custo"] += custo
        if len(c["exemplos"]) < 3:
            c["exemplos"].append(hand_id)

    n_ok = 0
    for h in hands:
        try:
            if not h.hero or not h.stakes.big_blind:
                continue
            a = analyze_hand(h)
            n_ok += 1
            pos = a.get("position") or "?"
            stack = a.get("hero_stack_bb") or 0
            raises, _ = _facing_preflop(h)
            folded = _hero_folded_pre(h)
            from app.analysis.handreport import hand_class

            hc = hand_class(h.hero_cards)

            # pote não aberto na frente do herói
            if raises == 0 and hc:
                rng = OPEN_RANGES.get(pos)
                if rng:
                    counts["open_perdido"]["opp"] += 1
                    if folded and hc in parse_range(rng):
                        hit("open_perdido", 0.3, h.hand_id)  # estimativa
                if stack and stack <= 12:
                    pf = push_fold(h.hero_cards, stack, pos)
                    if pf.get("applicable"):
                        counts["shove_perdido"]["opp"] += 1
                        if folded and pf["decision"] == "push":
                            edge = max(0.0, (pf["shove_range_pct"] -
                                             pf["hand_top_pct"]) /
                                       max(pf["shove_range_pct"], 1.0))
                            hit("shove_perdido", round(0.3 + 1.2 * edge, 2),
                                h.hand_id)  # estimativa proporcional à folga

            # jam pré largo demais
            if _hero_jammed_pre(h) and stack and stack <= 20:
                pf = push_fold(h.hero_cards, stack, pos)
                if pf.get("applicable"):
                    counts["shove_largo"]["opp"] += 1
                    if pf["decision"] == "fold":
                        hit("shove_largo", 1.0, h.hand_id)  # estimativa

            # calls pagando caro pós-flop (custo exato: déficit × pote final)
            if not folded:
                facts = played_facts(h)
                for n in facts["numbers"]:
                    if "equity_minima" in n and n.get("equity_vs_aleatoria") is not None:
                        counts["call_caro"]["opp"] += 1
                        deficit = n["equity_minima"] - n["equity_vs_aleatoria"]
                        if deficit > 0.05:
                            custo = round(
                                deficit * (n["pote_bb"] + n["pagou_bb"]), 2)
                            hit("call_caro", custo, h.hand_id)
        except Exception:
            continue

    out = []
    for key, c in counts.items():
        if c["opp"] < 2:
            continue
        mean, lo, hi = shrunk_rate(c["miss"], c["opp"], *_LEAK_PRIOR)
        custo_100 = round(100.0 * c["custo"] / max(n_ok, 1), 1)
        # só vira "leak" se a taxa corrigida indica padrão, não acidente
        if c["miss"] == 0 or mean < 25.0 or custo_100 <= 0:
            continue
        out.append({
            "leak": key,
            "nome": LEAK_NAMES[key],
            "oportunidades": c["opp"],
            "escorregadas": c["miss"],
            "taxa_pct": mean,
            "taxa_lo": lo,
            "taxa_hi": hi,
            "confianca": "alta" if (hi - lo) <= 25.0 and c["opp"] >= 8 else "media",
            "custo_bb_100maos": custo_100,
            "exemplos": c["exemplos"],
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
    linhas.append("_Me pergunta sobre qualquer um que eu abro as mãos._")
    return "\n".join(linhas)
