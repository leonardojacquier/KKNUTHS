"""Vazamentos mentais ("Rápido e Devagar", Kahneman) — tilt em números.

Aversão à perda vira busca de risco: depois de perder um pote grande o
jogador abre demais tentando "voltar ao zero" (chase). O espelho é o medo de
ganhar: depois de um pote grande GANHO, trava e folda além da conta. Ambos
são mensuráveis: comparamos o VPIP nas janelas pós-gatilho com a linha de
base do PRÓPRIO jogador, com shrinkage ancorado na base — meia dúzia de mãos
agitadas não vira diagnóstico de tilt.
"""
from __future__ import annotations

from app.analysis.bayes import shrunk_rate
from app.models.canonical import ActionType, CanonicalHand, StreetName

TRIGGER_BB = 15.0   # pote grande (em BB) que dispara a janela
WINDOW = 8          # mãos observadas depois do gatilho
MIN_OBS = 6         # mínimo de mãos em janelas para diagnosticar
DELTA_PP = 8.0      # desvio (pontos de VPIP) que caracteriza o padrão


def _vpip(h: CanonicalHand) -> bool:
    pre = h.street(StreetName.PREFLOP)
    return bool(pre) and any(
        a.actor == h.hero and a.type in
        (ActionType.CALL, ActionType.BET, ActionType.RAISE)
        for a in pre.actions
    )


def mental_from_series(nets: list[float], vpips: list[bool]) -> list[dict]:
    """Núcleo puro: séries de resultado (BB) e VPIP por mão, em ordem."""
    n = len(nets)
    if n < 20:
        return []
    baseline = 100.0 * sum(vpips) / n

    def windows(trigger_ok) -> list[int]:
        idx: set[int] = set()
        for i, net in enumerate(nets):
            if trigger_ok(net):
                idx.update(range(i + 1, min(i + 1 + WINDOW, n)))
        return sorted(idx)

    out = []
    for tipo, cond, direcao in (
        ("tilt_chase", lambda x: x <= -TRIGGER_BB, +1),
        ("medo_de_ganhar", lambda x: x >= TRIGGER_BB, -1),
    ):
        idx = windows(cond)
        if len(idx) < MIN_OBS:
            continue
        k = sum(1 for i in idx if vpips[i])
        # prior = a própria linha de base do jogador: só acusa se a janela
        # puxar o posterior para longe dela
        mean, lo, hi = shrunk_rate(k, len(idx), baseline, 12.0)
        delta = (mean - baseline) * direcao
        if delta < DELTA_PP:
            continue
        saldo = sum(nets[i] for i in idx)
        out.append({
            "tipo": tipo,
            "vpip_base": round(baseline, 1),
            "vpip_janela": mean,
            "maos_na_janela": len(idx),
            "saldo_janela_bb": round(saldo, 1),
            "frase": (
                f"depois de perder um pote grande você abre {mean:.0f}% das mãos "
                f"(sua base é {baseline:.0f}%) — perseguindo prejuízo; o saldo "
                f"nessas {len(idx)} mãos foi {saldo:+.1f}bb"
                if tipo == "tilt_chase" else
                f"depois de GANHAR um pote grande você trava: abre só "
                f"{mean:.0f}% das mãos (sua base é {baseline:.0f}%) — medo de "
                f"devolver; agressão paga exatamente quando o stack te dá pressão"
            ),
        })
    return out


def detect_mental(hands: list[CanonicalHand]) -> list[dict]:
    """Detecta tilt/medo de ganhar num histórico (ordena por horário)."""
    from app.agent.analyzer import analyze_hand

    seq = sorted((h for h in hands if h.hero and h.stakes.big_blind),
                 key=lambda h: h.played_at or "")
    nets, vpips = [], []
    for h in seq:
        try:
            nets.append(analyze_hand(h)["net_bb"])
            vpips.append(_vpip(h))
        except Exception:
            continue
    return mental_from_series(nets, vpips)


def mental_text(found: list[dict]) -> str:
    if not found:
        return ""
    linhas = ["\n\n🧠 *Cabeça no jogo*"]
    for f in found:
        linhas.append(f"• {f['frase']}")
    linhas.append("_Resultado ruim não é licença para mudar de jogo — nem o "
                  "bom. O plano é o mesmo antes e depois do pote grande._")
    return "\n".join(linhas)
