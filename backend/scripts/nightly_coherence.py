"""Auditor noturno de coerência — o "Leo automático".

O gap do processo de verificação (nota 8): os testes cobrem casos que já
conhecemos; quem achava contradição em produção era o admin usando. Este
cron varre as mãos REAIS do banco toda noite e procura contradições e dados
quebrados ANTES do usuário:

1. veredito da imagem vs equilíbrio de push/fold (classe do bug TT/15bb),
   agora sobre spots reais, não sintéticos;
2. sanidade do parser: cartas válidas/únicas, board ≤5, showdown com cartas
   válidas, pote coerente com o coletado.

Achou problema → loga bot_events (event='coherence') e avisa o ADMIN no
Telegram. Nada achado → loga o resumo silencioso (rastro de que rodou).

Cron: 0 6 * * *  cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/nightly_coherence.py
"""
from __future__ import annotations

import json
import re
import urllib.request

from app.config import get_settings
from app.db import get_repository

ADMIN_ID = 6452742024
_CARD = re.compile(r"^[2-9TJQKA][shdc]$")


def _valid_cards(cards) -> bool:
    cs = list(cards or [])
    return all(_CARD.match(c) for c in cs) and len(set(cs)) == len(cs)


def check_hand(h) -> list[str]:
    """Sanidade estrutural de uma mão parseada (classe: parser drift)."""
    probs = []
    if h.hero_cards and not _valid_cards(h.hero_cards):
        probs.append(f"{h.hand_id}: hero_cards inválidas {h.hero_cards}")
    if h.final_board and (not _valid_cards(h.final_board)
                          or len(h.final_board) > 5):
        probs.append(f"{h.hand_id}: board inválido {h.final_board}")
    for who, cs in (h.shown_cards or {}).items():
        if not _valid_cards(cs):
            probs.append(f"{h.hand_id}: showdown inválido {who}={cs}")
    allc = list(h.hero_cards or []) + list(h.final_board or [])
    if len(set(allc)) != len(allc):
        probs.append(f"{h.hand_id}: carta duplicada herói+board")
    if h.total_pot and h.collected:
        if sum(h.collected.values()) > h.total_pot * 1.01:
            probs.append(f"{h.hand_id}: coletado > pote")
    return probs


def check_verdict_vs_solver(h) -> list[str]:
    """Classe TT/15bb sobre mãos REAIS: nos spots pré-flop curtos com preço,
    o veredito da imagem não pode dizer PAGAR onde o equilíbrio manda JAM."""
    from app.analysis.pushfold import push_fold
    from app.analysis.tools import pot_odds
    from app.bot.processing import _walk_hand, storyboard_spot_from_drill

    probs = []
    bb = h.stakes.big_blind or 0
    seat = h.hero_seat()
    if not (bb and seat and h.hero_cards and h.format.value == "tournament"):
        return probs
    stack_bb = round(seat.stack / bb, 1)
    if not (0 < stack_bb <= 20):
        return probs
    try:
        _, decisions = _walk_hand(h)
    except Exception:
        return probs
    for d in decisions:
        if d.get("street") != "preflop" or not d.get("to_call_bb"):
            continue
        drill = {
            "cards": h.hero_cards, "position": seat.position or "MP",
            "stack_bb": stack_bb, "blinds": "x", "street": "preflop",
            "format": "tournament", "board": [],
            "pot_bb": d["pot_bb"], "to_call_bb": d["to_call_bb"],
            "required_eq": round(pot_odds(d["pot_bb"], d["to_call_bb"]), 3),
            "actual": d.get("actual") or "call", "net_bb": 0.0,
            "villains": [{"pos": "MP", "bet_bb": d["to_call_bb"]}],
            "storyboard": [{"name": "Pré-flop", "board": [], "lines": [],
                            "pot_bb": d["pot_bb"]}],
        }
        try:
            spec = storyboard_spot_from_drill(drill, choice="call")
            pf = push_fold(h.hero_cards, stack_bb, seat.position or "MP")
        except Exception:
            continue
        if (spec and pf.get("applicable") and pf.get("decision") == "push"
                and spec.get("correct") == "PAGAR (call)"):
            probs.append(
                f"{h.hand_id}: imagem=PAGAR, solver=JAM "
                f"({stack_bb}bb {seat.position})")
    return probs


def notify_admin(token: str, text: str) -> None:
    body = json.dumps({"chat_id": ADMIN_ID, "text": text[:4000]}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


def main() -> int:
    settings = get_settings()
    repo = get_repository()
    if not repo.enabled:
        return 0
    hands = repo.get_population_hands(limit=300)
    problems: list[str] = []
    for h in hands:
        problems += check_hand(h)
        problems += check_verdict_vs_solver(h)
    problems = problems[:30]

    repo.log_event(0, None, "coherence", {
        "maos": len(hands), "problemas": len(problems),
        "detalhe": problems[:12]})
    if problems and settings.telegram_bot_token:
        notify_admin(
            settings.telegram_bot_token,
            "🔍 Auditor noturno: "
            f"{len(problems)} problema(s) em {len(hands)} mãos:\n\n"
            + "\n".join(f"• {p}" for p in problems[:10]))
    print(f"coerência: {len(hands)} mãos, {len(problems)} problemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
