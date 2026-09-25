"""Leitura mecânica da mão — andar pelas ruas, nomear ações, formatar.

Saiu do processing.py, que passou de 3.870 linhas. São funções PURAS sem
nenhuma dependência do resto do módulo (conferido por AST antes de mover):
recebem uma CanonicalHand e devolvem texto ou estrutura. É a camada que
toda as outras usam e ninguém deveria precisar procurar no meio do arquivo
que também fala com o Telegram, com o banco e com o LLM.
"""
from __future__ import annotations

from app.models.canonical import ActionType, StreetName


def _pretty_cards(cards: list[str]) -> str:
    sym = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
    return " ".join(c[0] + sym.get(c[1], c[1]) for c in cards if len(c) == 2)


def _fmt_bb(x: float | None) -> str:
    """'(9bb)' pronto pra botão — vazio quando não dá pra calcular."""
    if not x or x <= 0:
        return ""
    return f" ({round(x, 1):g}bb)"


def _describe_safe(cards, board) -> str | None:
    """describe_hand sem quebrar o fluxo (drill não pode morrer por leitura)."""
    try:
        from app.analysis.equity import describe_hand

        return describe_hand(cards, board)
    except Exception:
        return None


def _walk_hand(h: CanonicalHand) -> tuple[list[str], list[dict]]:
    """Percorre a mão narrando por POSIÇÃO e em BB; devolve (linhas, decisões).

    Cada decisão do herói vem com o índice da narrativa naquele momento +
    street, mesa, pote, preço e a ação real — a matéria-prima do quiz."""
    from app.models.canonical import ActionType, StreetName

    bb = h.stakes.big_blind or 1
    pos = {p.name: (p.position or p.name[:8]) for p in h.players}
    verbs = {"fold": "folda", "check": "dá check", "call": "paga",
             "bet": "aposta", "raise": "aumenta para"}
    lines: list[str] = []
    decisions: list[dict] = []
    pot = 0.0
    order = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN, StreetName.RIVER]

    for sname in order:
        st = h.street(sname)
        if not st:
            continue
        contrib: dict[str, float] = {}
        started = False
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - contrib.get(a.actor, 0.0)
            counts = a.type != ActionType.POST or a.post_type in ("sb", "bb")
            outstanding = max(contrib.values(), default=0.0)

            if a.type != ActionType.POST and not started:
                board = _pretty_cards(st.board) if st.board else ""
                lines.append(f"*{sname.value.upper()}*" + (f"  ({board})" if board else ""))
                started = True

            if a.actor == h.hero and a.type != ActionType.POST:
                to_call = max(0.0, outstanding - contrib.get(h.hero or "", 0.0))
                decisions.append({
                    "line_idx": len(lines),
                    "street": sname.value,
                    "board": list(st.board),
                    "pot_bb": round(pot / bb, 1),
                    "to_call_bb": round(to_call / bb, 1),
                    "actual": a.type.value,
                    "amount_bb": round(((a.to_amount or a.amount) / bb), 1),
                    "all_in": a.all_in,
                })
                amt = round((a.to_amount or a.amount) / bb, 1)
                lines.append(f"  VOCÊ {verbs.get(a.type.value, a.type.value)}"
                             + (f" {amt:g}bb" if amt else "")
                             + (" (all-in)" if a.all_in else ""))
            elif a.type != ActionType.POST:
                who = pos.get(a.actor, a.actor[:8])
                amt = round((a.to_amount or a.amount) / bb, 1)
                lines.append(f"  {who} {verbs.get(a.type.value, a.type.value)}"
                             + (f" {amt:g}bb" if amt else "")
                             + (" (all-in)" if a.all_in else ""))

            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET, ActionType.RAISE):
                pot += add
                if counts:
                    contrib[a.actor] = contrib.get(a.actor, 0.0) + add
    return lines, decisions


def _preflop_summary(h: CanonicalHand, stop_actor: str | None = None) -> str | None:
    """Resumo do pré-flop em ORDEM DE POSIÇÃO (UTG primeiro), compacto e
    legível — como um jogador conta a mão. Ignora posts de blind/ante.
    `stop_actor`: para antes da decisão do herói (quando a decisão é no pré)."""
    from app.models.canonical import ActionType, StreetName

    pre = h.street(StreetName.PREFLOP)
    if not pre:
        return None
    bb = h.stakes.big_blind or 1
    pos = {p.name: (p.position or "") for p in h.players}
    # ORDEM CRONOLÓGICA (que já é a ordem de ação correta: UTG primeiro).
    # Escondemos posts (ruído de blind/ante) e folds — como um jogador conta:
    # "MP abre 2bb · SB 3-beta 6bb · MP paga". Se folda até o herói, avisa.
    parts: list[str] = []
    folds_antes = 0
    n_raises = 0
    for a in pre.actions:
        if a.type == ActionType.POST:
            continue
        if stop_actor and a.actor == h.hero:
            break
        if a.type == ActionType.FOLD:
            folds_antes += 1
            continue
        who = "você" if a.actor == h.hero else (pos.get(a.actor) or a.actor[:6])
        amt = round((a.to_amount or a.amount) / bb, 1)
        if a.type == ActionType.RAISE:
            n_raises += 1
            verb = "abre" if n_raises == 1 else (
                "3-beta" if n_raises == 2 else "4-beta")
        else:
            verb = {"call": "paga", "bet": "abre", "check": "dá check"}.get(
                a.type.value, a.type.value)
        txt = f"{who} {verb}"
        # valor só em bet/raise (definem o preço); call = 'paga' (igualou)
        if amt and a.type.value in ("bet", "raise"):
            txt += f" {amt:g}bb"
        if a.all_in:
            txt += " (all-in)"
        parts.append(txt)
    if not parts:
        # ninguém aumentou/pagou antes do herói — foldou geral até você
        return "Pré-flop: folda até você" if folds_antes else None
    return "Pré-flop: " + " · ".join(parts)


def _seats_at_decision(h: CanonicalHand, di: int) -> list[dict]:
    """TODOS os jogadores (menos o herói) no estado do MOMENTO da decisão di:
    folded=True só se já tinha foldado ANTES daquele instante. Corrige a mesa
    que 'mentia' o spot: um vilão ativo na decisão sumia da figura porque
    foldava mais tarde na mão (multiway virava heads-up)."""
    from app.models.canonical import ActionType

    bb = h.stakes.big_blind or 1
    folded: set = set()
    ndec = 0
    done = False
    for st in h.streets:
        for a in st.actions:
            if a.actor == h.hero and a.type != ActionType.POST:
                if ndec == di:
                    done = True
                    break
                ndec += 1
            elif a.type == ActionType.FOLD:
                folded.add(a.actor)
        if done:
            break
    out = []
    for p in sorted(h.players, key=lambda p: p.seat):
        if p.is_hero or p.name == h.hero:
            continue
        out.append({"pos": p.position or p.name[:6],
                    "stack_bb": round(p.stack / bb, 1),
                    "folded": p.name in folded})
    return out


def _mark_aggressor(villains: list[dict], agg_pos, agg_bet,
                    pos_stack: dict) -> list[dict]:
    """Marca o vilão que fez a aposta (fichas na figura). Se ele não está na
    lista de ativos — porque foldou MAIS TARDE na mão —, inclui mesmo assim,
    senão a aposta que o herói enfrenta some do desenho."""
    if not agg_pos:
        return villains
    for v in villains:
        if v.get("pos") == agg_pos:
            v["bet_bb"] = agg_bet
            v["to_act"] = True
            return villains
    villains.append({"pos": agg_pos, "stack_bb": pos_stack.get(agg_pos),
                     "bet_bb": agg_bet, "to_act": True})
    return villains


def _decision_aggressor(h: CanonicalHand, d: dict) -> tuple[str | None, float | None]:
    """Na street da decisão, quem foi o último a apostar/aumentar ANTES do herói
    — o vilão que o herói tem de responder — e o tamanho (em bb)."""
    from app.models.canonical import ActionType, StreetName

    bb = h.stakes.big_blind or 1
    try:
        st = h.street(StreetName(d["street"]))
    except Exception:
        st = None
    if not st:
        return None, None
    pos = {p.name: (p.position or p.name[:8]) for p in h.players}
    # o herói pode agir mais de uma vez na street (check, depois fold à aposta).
    # Guardamos a última aposta/aumento de VILÃO e, quando o herói responde a
    # ela, essa é a aposta que ele enfrenta.
    pending = (None, None)
    facing = (None, None)
    for a in st.actions:
        if a.actor == h.hero and a.type != ActionType.POST:
            if pending[0] is not None:
                facing = pending      # herói responde a uma aposta pendente
            continue
        if a.type in (ActionType.BET, ActionType.RAISE):
            pending = (a.actor, round((a.to_amount or a.amount) / bb, 1))
    name, amt = facing
    return (pos.get(name) if name else None), amt
