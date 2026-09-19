"""Auditoria de TODA JOGADA de um torneio — os motores aplicados mão a mão.

Três níveis de rigor, sempre ROTULADOS (o aluno precisa saber o que é
equilíbrio calculado e o que é referência de tabela):

  all-in pré-flop  -> EQUILÍBRIO resolvido (allin_engine)
  pré-flop deep    -> REFERÊNCIA (tabelas de open/3-bet)
  pós-flop         -> EQUILÍBRIO CFR+ (river_solver), só nos potes maiores
                      (cada spot custa segundos de CPU)

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


# ------------------------------------------------------------ pré-flop deep
def _acao_pre_do_heroi(h: CanonicalHand) -> dict | None:
    """Primeira ação voluntária do herói no pré-flop, com o contexto: quem
    abriu antes dele e quantos pagaram. None se ele não agiu."""
    pre = h.street(StreetName.PREFLOP)
    if not pre or not h.hero or not h.hero_cards:
        return None
    bb = h.stakes.big_blind or 1
    pos = {p.name: (p.position or "") for p in h.players}
    abriu, pagaram = None, 0
    for a in pre.actions:
        if a.type == ActionType.POST:
            continue
        if a.actor == h.hero:
            return {"tipo": a.type.value, "abriu": abriu, "pagaram": pagaram,
                    "pos": pos.get(h.hero) or "MP", "all_in": a.all_in}
        if a.type in (ActionType.RAISE, ActionType.BET) and not abriu:
            abriu = pos.get(a.actor) or "MP"
        elif a.type == ActionType.CALL and abriu:
            pagaram += 1
    return None


_GRUPO_3BET = {"UTG": "EP", "UTG+1": "EP", "UTG+2": "EP", "MP": "MP",
               "LJ": "MP", "HJ": "MP", "CO": "CO", "BTN": "BTN",
               "SB": "BTN", "BB": "BTN"}


def auditar_preflop_deep(hands: list[CanonicalHand]) -> list[dict]:
    """Pré-flop de stack DEEP contra o range de REFERÊNCIA.

    NÃO é solver — o nível vai rotulado, porque tabela de referência e
    equilíbrio calculado não podem ser vendidos como a mesma coisa."""
    from app.analysis.pushfold import canonical_hand
    from app.analysis.ranges import OPEN_RANGES, THREEBET_RANGES, parse_range

    out: list[dict] = []
    for h in hands:
        try:
            seat = h.hero_seat()
            bb = h.stakes.big_blind or 1
            if not seat or seat.stack / bb <= MAX_STACK_BB:
                continue          # stack curto é do motor de all-in
            act = _acao_pre_do_heroi(h)
            if not act or act["all_in"]:
                continue
            mao = canonical_hand(h.hero_cards)
            pos, tipo, abriu = act["pos"], act["tipo"], act["abriu"]

            if abriu is None:                    # ninguém abriu: open ou fold
                ref = OPEN_RANGES.get(pos)
                if not ref or pos in ("SB", "BB"):
                    continue
                dentro = mao in set(parse_range(ref))
                abriu_mesmo = tipo in ("raise", "bet")
                fez = "abriu" if abriu_mesmo else "largou"
                certo = "abrir" if dentro else "largar"
                acertou = abriu_mesmo == dentro
                nome = f"open de {pos}"
            elif tipo == "raise":                # 3-bet sobre um open
                ref = THREEBET_RANGES.get(f"vs_{_GRUPO_3BET.get(abriu, 'MP')}")
                if not ref:
                    continue
                dentro = mao in set(parse_range(ref))
                fez, certo = "3-betou", ("3-betar" if dentro else "pagar/largar")
                acertou = dentro
                nome = f"3-bet contra open de {abriu}"
            else:
                continue          # call/fold contra open: sem referência firme

            out.append({
                "hand_id": h.hand_id, "mao": mao, "posicao": pos,
                "spot": nome, "voce_fez": fez, "referencia": certo,
                "acertou": acertou, "stack_bb": round(seat.stack / bb, 1),
                "nivel": "referência",
            })
        except Exception:
            continue
    return out


# ----------------------------------------------------------------- pós-flop
def _decisoes_posflop(h: CanonicalHand) -> list[dict]:
    """Decisões pós-flop do herói, com o pote (bb) e o board do momento."""
    bb = h.stakes.big_blind or 1
    ordem = (StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN,
             StreetName.RIVER)
    pot, board, out = 0.0, [], []
    for sname in ordem:
        st = h.street(sname)
        if not st:
            continue
        board = board + [c for c in st.board if c not in board]
        aposta_pendente = False
        for a in st.actions:
            if a.type == ActionType.POST:
                pot += a.amount
                continue
            # AUDITA só decisão de INICIATIVA (apostar ou dar check). Com
            # aposta pendente o nó é outro (fold/call/jam) e comparar o call
            # do aluno com a frequência de APOSTA do equilíbrio seria erro
            # de categoria.
            if (a.actor == h.hero and sname != StreetName.PREFLOP
                    and not aposta_pendente
                    and a.type in (ActionType.BET, ActionType.CHECK)):
                out.append({"street": sname.value,
                            "pot_bb": round(pot / bb, 1),
                            "acao": a.type.value, "board": list(board)})
            if a.type in (ActionType.BET, ActionType.RAISE):
                aposta_pendente = True
            if a.type in (ActionType.CALL, ActionType.BET, ActionType.RAISE):
                pot += a.amount
    return out


def auditar_posflop(hands: list[CanonicalHand], max_spots: int = 3) -> list[dict]:
    """Pós-flop pelo CFR+ nos MAIORES potes.

    Audita as decisões de INICIATIVA do herói (apostar ou dar check) — o nó
    que o solver expõe na raiz. Enfrentando aposta, a decisão é fold/call/jam
    em outro nó; comparar com a frequência de aposta seria erro de categoria.
    Cada spot custa segundos de CPU, então o teto de spots vai declarado."""
    from app.analysis.pushfold import canonical_hand
    from app.analysis.river_solver import RiverSolver

    cand = []
    for h in hands:
        if not h.hero_cards:
            continue
        for d in _decisoes_posflop(h):
            if len(d["board"]) >= 3 and d["pot_bb"] > 0:
                cand.append((d["pot_bb"], h, d))
    cand.sort(key=lambda t: -t[0])

    out: list[dict] = []
    for _pot, h, d in cand[:max_spots]:
        try:
            seat = h.hero_seat()
            bb = h.stakes.big_blind or 1
            stack = round((seat.stack if seat else 0) / bb, 1)
            mao = canonical_hand(h.hero_cards)
            # a mão REAL do herói entra no range assumido — sem isso a
            # auditoria pulava em silêncio toda vez que ele tinha algo fora
            # da faixa genérica (caso real: QJs não estava em "88+, ATs+...")
            base = "88+, ATs+, KQs, AJo+"
            rng_heroi = f"{base}, {mao}"
            solver = RiverSolver(d["board"][:5], rng_heroi, base,
                                 float(d["pot_bb"]), max(stack, 1.0)).solve()
            hv = solver.hand_values("oop")
            if not hv:
                continue
            freq = hv["freq"].get(mao)
            if freq is None:
                continue
            apostou = d["acao"] == "bet"
            # TRÊS faixas, não duas: entre 30% e 70% o equilíbrio joga MISTO
            # e as duas ações estão certas — cravar erro num 43% seria mentir
            if 0.30 <= freq <= 0.70:
                veredito, acertou = "mista", True
            elif freq > 0.70:
                veredito, acertou = "apostar", apostou
            else:
                veredito, acertou = "check", not apostou
            out.append({
                "hand_id": h.hand_id, "mao": mao, "street": d["street"],
                "board": " ".join(d["board"][:5]), "pot_bb": d["pot_bb"],
                "voce_fez": d["acao"],
                "freq_equilibrio_pct": round(freq * 100),
                "equilibrio": veredito, "acertou": acertou,
                "valor_bb": hv["ev"].get(mao),
                "nivel": "equilíbrio CFR+ (ranges estimados)",
            })
        except Exception:
            continue
    return out
