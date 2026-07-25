"""Auditoria de ALL-INS de um torneio — o motor aplicado mão a mão.

O motor de EV existia mas só era alcançado se o coach resolvesse chamá-lo no
meio de uma conversa. Aqui ele roda sozinho sobre o torneio inteiro: toda
decisão de all-in ou fold do herói com stack curto vira um veredito de
equilíbrio COM o EV em bb — determinístico, custo zero de IA.

É a resposta a "temos as ferramentas mas eu não estou testando isso": o
relatório do torneio passa a trazer a conta de cada all-in.
"""
from __future__ import annotations

from app.models.canonical import ActionType, CanonicalHand, StreetName

# acima disso o framework de push/fold deixa de valer
MAX_STACK_BB = 22.0


def _spot_do_heroi(h: CanonicalHand) -> dict | None:
    """Identifica o spot de all-in pré-flop do herói, se houver.

    Devolve {spot, hero_pos, vilao_pos, open_bb, pagaram, acao, stack_bb} —
    a entrada do motor. None quando a mão não é um spot de all-in."""
    pre = h.street(StreetName.PREFLOP)
    if not pre or not h.hero or not h.hero_cards:
        return None
    bb = h.stakes.big_blind or 1
    seat = h.hero_seat()
    if not seat:
        return None
    stack_bb = round(seat.stack / bb, 1)
    if not 0 < stack_bb <= MAX_STACK_BB:
        return None

    pos = {p.name: (p.position or "") for p in h.players}
    abriu: str | None = None
    open_bb = 0.0
    pagaram = 0
    shove_antes: str | None = None

    for a in pre.actions:
        if a.type == ActionType.POST:
            continue
        if a.actor == h.hero:
            # a decisão do herói: all-in (empurrar) ou fold diante de ação
            e_allin = a.all_in or (
                a.type in (ActionType.RAISE, ActionType.BET)
                and (a.to_amount or a.amount) / bb >= stack_bb - 0.5)
            if a.type == ActionType.FOLD and not (abriu or shove_antes):
                return None            # fold sem ação na frente: não é spot
            if not e_allin and a.type != ActionType.FOLD:
                return None            # aumentou pequeno: não é push/fold
            if shove_antes:
                spot = "overcall" if pagaram else "call_shove"
                vil = shove_antes
            elif abriu:
                spot = "squeeze" if pagaram else "reshove"
                vil = abriu
            else:
                spot = "open_shove"
                vil = None
            return {
                "spot": spot,
                "hero_pos": pos.get(h.hero) or "MP",
                "vilao_pos": vil,
                "open_bb": round(open_bb, 1) or 2.2,
                "pagaram": pagaram,
                "acao": "fold" if a.type == ActionType.FOLD else "all-in",
                "stack_bb": stack_bb,
            }
        # ações dos vilões ANTES do herói
        if a.type in (ActionType.RAISE, ActionType.BET):
            if a.all_in:
                shove_antes = pos.get(a.actor) or "MP"
            elif not abriu:
                abriu = pos.get(a.actor) or "MP"
                open_bb = (a.to_amount or a.amount) / bb
            pagaram = 0
        elif a.type == ActionType.CALL and (abriu or shove_antes):
            pagaram += 1
    return None


def auditar_allins(hands: list[CanonicalHand], bf: float = 1.0) -> list[dict]:
    """Roda o motor em cada spot de all-in do herói. Devolve uma linha por
    mão auditada, com o veredito de equilíbrio e o EV da mão em bb."""
    from app.analysis.allin_engine import available, solve_spot
    from app.analysis.pushfold import canonical_hand

    if not available():
        return []
    out: list[dict] = []
    for h in hands:
        try:
            spot = _spot_do_heroi(h)
            if not spot:
                continue
            ante_bb = (h.stakes.ante or 0) / (h.stakes.big_blind or 1)
            sol = solve_spot(spot["spot"], spot["hero_pos"],
                             round(spot["stack_bb"], 1),
                             round(min(ante_bb, 0.5), 3), bf,
                             spot["vilao_pos"], spot["open_bb"],
                             spot["pagaram"])
            if not sol:
                continue
            mao = canonical_hand(h.hero_cards)
            ev = sol["ev"].get(mao)
            freq = sol["acao"].get(mao, 0.0)
            certo = "all-in" if freq > 0.5 else "fold"
            fez = spot["acao"]
            # custo do erro: quem devia empurrar e largou perdeu o EV; quem
            # empurrou sem dever perdeu o EV negativo (que era o preço)
            erro_bb = 0.0 if certo == fez else abs(ev or 0.0)
            out.append({
                "hand_id": h.hand_id,
                "mao": mao,
                "spot": sol["spot"],
                "posicao": spot["hero_pos"],
                "vilao": spot["vilao_pos"],
                "stack_bb": spot["stack_bb"],
                "voce_fez": fez,
                "equilibrio": certo,
                "ev_bb": ev,
                "acertou": certo == fez,
                "custo_bb": round(erro_bb, 2),
                "range_pct": sol["acao_pct"],
            })
        except Exception:
            continue
    return out


def resumo_auditoria(linhas: list[dict]) -> dict:
    """Placar da auditoria: quantos all-ins, quantos certos e o preço dos
    erros em bb — o número que o aluno leva do torneio."""
    if not linhas:
        return {}
    erros = [l for l in linhas if not l["acertou"]]
    custo = round(sum(l["custo_bb"] for l in erros), 1)
    por_spot: dict[str, int] = {}
    for l in erros:
        por_spot[l["spot"]] = por_spot.get(l["spot"], 0) + 1
    pior = max(erros, key=lambda l: l["custo_bb"], default=None)
    return {
        "total": len(linhas),
        "certos": len(linhas) - len(erros),
        "erros": len(erros),
        "custo_total_bb": custo,
        "erros_por_spot": por_spot,
        "pior": pior,
    }
