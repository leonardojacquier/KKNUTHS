"""Exploit por VILÃO específico — o exploit que paga em clube.

Em clube são sempre os mesmos regs: as mãos que o aluno envia contêm as
ações (e showdowns!) de cada oponente recorrente. Este módulo monta o
perfil de um vilão a partir do acervo do PRÓPRIO aluno, com correção
bayesiana pra amostra curta (mesma engenharia do /stats) e dicas de
exploit TRAVADAS por tamanho de amostra (nada de ruído virar conselho).
"""
from __future__ import annotations

from app.analysis.bayes import is_firm, shrunk_af, shrunk_rate
from app.models.canonical import ActionType, CanonicalHand, StreetName

# priors: população de clube (levemente mais solta que reg de site)
_VPIP_PRIOR = (28.0, 12.0)   # (média %, força em mãos)
_PFR_PRIOR = (18.0, 12.0)

MIN_SAMPLE_HINTS = 15


def villain_profile(hands: list[CanonicalHand], name: str) -> dict | None:
    """Perfil do vilão `name` nas mãos fornecidas. None se nunca apareceu."""
    alvo = (name or "").strip().lower()
    seen = vpip_n = pfr_n = 0
    bets_raises = calls = folds_vs_bet = faced_bet = 0
    showdowns: list[dict] = []
    nome_real = name

    for h in hands:
        p = next((x for x in h.players
                  if x.name and x.name.strip().lower() == alvo), None)
        if p is None:
            continue
        nome_real = p.name
        seen += 1
        pre = h.street(StreetName.PREFLOP)
        voluntary = raised = False
        for a in (pre.actions if pre else []):
            if a.actor != p.name or a.type == ActionType.POST:
                continue
            if a.type in (ActionType.CALL, ActionType.BET, ActionType.RAISE):
                voluntary = True
            if a.type == ActionType.RAISE:
                raised = True
        vpip_n += int(voluntary)
        pfr_n += int(raised)

        for st in h.streets:
            outstanding = 0.0
            for a in st.actions:
                if a.actor == p.name and a.type != ActionType.POST:
                    if a.type in (ActionType.BET, ActionType.RAISE):
                        bets_raises += 1
                    elif a.type == ActionType.CALL:
                        calls += 1
                        if outstanding > 0:
                            faced_bet += 1
                    elif a.type == ActionType.FOLD and outstanding > 0:
                        folds_vs_bet += 1
                        faced_bet += 1
                if a.type in (ActionType.BET, ActionType.RAISE):
                    outstanding = max(outstanding, a.amount or 1.0)

        if p.name in (h.shown_cards or {}):
            showdowns.append({"cartas": h.shown_cards[p.name],
                              "board": h.final_board,
                              "mao": h.hand_id})

    if seen == 0:
        return None

    vpip = shrunk_rate(vpip_n, seen, *_VPIP_PRIOR)
    pfr = shrunk_rate(pfr_n, seen, *_PFR_PRIOR)
    af = shrunk_af(bets_raises, calls)
    fold_vs_bet = (shrunk_rate(folds_vs_bet, faced_bet, 50.0, 10.0)
                   if faced_bet else None)

    perfil = {
        "vilao": nome_real,
        "maos_na_base": seen,
        "vpip": {"media": vpip[0], "ic95": [vpip[1], vpip[2]],
                 "cravado": is_firm(vpip[1], vpip[2])},
        "pfr": {"media": pfr[0], "ic95": [pfr[1], pfr[2]]},
        "af": af,
        "fold_quando_apostado": (
            {"media": fold_vs_bet[0], "ic95": [fold_vs_bet[1], fold_vs_bet[2]],
             "amostra": faced_bet} if fold_vs_bet else None),
        "showdowns_vistos": showdowns[-6:],
        "amostra": ("alta" if seen >= 40 else
                    "média" if seen >= MIN_SAMPLE_HINTS else "baixa"),
        "exploits": _hints(seen, vpip, pfr, af, fold_vs_bet, faced_bet),
    }
    if seen < MIN_SAMPLE_HINTS:
        perfil["aviso"] = (
            f"amostra BAIXA ({seen} mãos): números com intervalo largo — "
            "trate como impressão inicial, não como leitura firme.")
    tt = timing_tells(hands, name)
    if tt:
        perfil["timing"] = tt
    return perfil


def timing_tells(hands: list[CanonicalHand], name: str) -> dict | None:
    """Timing tells do vilão — dado que NENHUM tracker do mercado usa.

    O replay da PPPoker traz o tempo de cada ação (Action.time_raw). A
    semântica varia (duração ou timestamp): normalizamos por DIFERENÇAS
    dentro da mesma mão quando parece timestamp. Sinais só com amostra;
    correlação com showdown (força real da mão mostrada) quando existir."""
    alvo = (name or "").strip().lower()
    dur_agg: list[float] = []     # tempo de bet/raise
    dur_pass: list[float] = []    # tempo de call/check
    sd_points: list[tuple[float, bool]] = []  # (tempo da agressão, forte?)

    for h in hands:
        p = next((x for x in h.players
                  if x.name and x.name.strip().lower() == alvo), None)
        if p is None:
            continue
        strong = None
        if (len((h.shown_cards or {}).get(p.name) or []) == 2
                and len(h.final_board or []) == 5):
            from app.analysis.river_solver import _strengths
            try:
                strong = bool(_strengths(
                    [tuple(h.shown_cards[p.name])], h.final_board)[0] <= 3325)
            except Exception:
                strong = None
        for st in h.streets:
            prev_t = None
            for a in st.actions:
                t = a.time_raw
                if t is None:
                    prev_t = None
                    continue
                # timestamp (número grande): a duração é a diferença
                dur = (t - prev_t) if (t > 100_000 and prev_t
                                       and t >= prev_t) else (
                    t if t <= 120 else None)
                prev_t = t
                if a.actor != p.name or dur is None or dur < 0:
                    continue
                if a.type in (ActionType.BET, ActionType.RAISE):
                    dur_agg.append(dur)
                    if strong is not None:
                        sd_points.append((dur, strong))
                elif a.type in (ActionType.CALL, ActionType.CHECK):
                    dur_pass.append(dur)

    total = len(dur_agg) + len(dur_pass)
    if total < 12:
        return None

    def med(v):
        s = sorted(v)
        return round(s[len(s) // 2], 1) if s else None

    out = {"acoes_com_tempo": total,
           "mediana_agressao_s": med(dur_agg),
           "mediana_passiva_s": med(dur_pass),
           "sinais": []}
    m = med(dur_agg)
    if m is not None and len(sd_points) >= 5:
        rapidos = [forte for d, forte in sd_points if d <= m]
        if len(rapidos) >= 4:
            pct = sum(rapidos) / len(rapidos)
            if pct >= 0.75:
                out["sinais"].append(
                    f"aposta RÁPIDA dele foi valor em {pct*100:.0f}% dos "
                    f"showdowns vistos ({len(rapidos)}) — snap-bet = força")
            elif pct <= 0.25:
                out["sinais"].append(
                    f"aposta rápida dele foi AR em {(1-pct)*100:.0f}% dos "
                    f"showdowns vistos ({len(rapidos)}) — snap-bet = blefe")
    out["nota"] = ("tells de tempo são TENDÊNCIA, não certeza; amostra de "
                   f"{len(sd_points)} agressões com showdown")
    return out


def _hints(seen, vpip, pfr, af, fold_vs_bet, faced_bet) -> list[str]:
    """Dicas de exploit — SÓ com amostra mínima (ruído não vira conselho)."""
    if seen < MIN_SAMPLE_HINTS:
        return []
    out = []
    # limiares pela MÉDIA encolhida: o gate de amostra já filtra o ruído e a
    # dica sempre sai com o tamanho da amostra citado pelo coach
    if vpip[0] >= 35:
        out.append("paga demais pré-flop: aposte por valor mais fino "
                   "(top pair fraco vira value) e blefe MENOS")
    if vpip[0] >= 30 and pfr[0] / max(vpip[0], 1) < 0.45:
        out.append("passivo (paga muito, aumenta pouco): raise dele é força "
                   "REAL — respeite e largue as marginais")
    if vpip[0] <= 20:
        out.append("nit: rouba os blinds dele sem dó e fuja quando ele "
                   "entrar no pote")
    if af >= 3.0:
        out.append("agressivo: seus bluff-catchers sobem de valor — pague "
                   "mais leve nos rivers")
    if fold_vs_bet and faced_bet >= 10 and fold_vs_bet[1] >= 55:
        out.append("folda demais quando apostado: c-beta e barrele mais "
                   "contra ele")
    return out
