"""Controle de cota — protege o custo de LLM mesmo sem billing ativo.

Plano free: N análises/mês. Planos pro/premium (setados manualmente no banco
enquanto o Stripe não entra): ilimitado. Com Supabase ativo a contagem vem de
`usage_events`; sem banco, um contador em memória por processo segura o dev/beta.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

FREE_MONTHLY_ANALYSES = int(os.getenv("FREE_MONTHLY_ANALYSES", "50"))

# O dono opera a ferramenta: reprocessa mão, testa release, roda diagnóstico.
# Quando a cota do free caiu de 100 para 50 ele já estava em 78 no mês e teria
# sido BLOQUEADO pelo próprio preço, na véspera de chamar os testadores.
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "6452742024"))
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "2"))
MAX_COACHED_HANDS = int(os.getenv("MAX_COACHED_HANDS", "5"))

_UNLIMITED_PLANS = {"pro", "premium"}

# fallback em memória: {telegram_id: (ano-mes, contagem)}
_mem: dict[int, tuple[str, int]] = {}


def _month_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}"


@dataclass
class QuotaResult:
    allowed: bool
    remaining: int
    plan: str = "free"
    degraded: bool = False  # banco caiu: não dá para SABER a cota (fail-closed)


def check_quota(telegram_id: int, user: dict | None, repo=None) -> QuotaResult:
    """Verifica (sem consumir) se o usuário pode rodar mais uma análise no mês.

    Fail-CLOSED: se a contagem no banco falhar, bloqueia (degraded=True) em vez
    de liberar — banco instável não pode virar análise de LLM ilimitada e grátis.
    """
    plan = (user or {}).get("plan", "free")
    if plan in _UNLIMITED_PLANS or telegram_id == ADMIN_TELEGRAM_ID:
        return QuotaResult(True, -1, plan)

    # banco ligado mas usuário não veio (falha transitória do get_or_create):
    # também é "não sei a cota" — sem isso cairia no contador em memória, que
    # zera a cada restart do processo
    if repo is not None and getattr(repo, "enabled", False) and not user:
        return QuotaResult(False, 0, plan, degraded=True)

    used = _count_used(telegram_id, user, repo)
    if used is None:
        return QuotaResult(False, 0, plan, degraded=True)
    remaining = max(0, FREE_MONTHLY_ANALYSES - used)
    return QuotaResult(remaining > 0, remaining, plan)


def consume_quota(telegram_id: int, user: dict | None, repo=None, kind: str = "analysis") -> None:
    """Registra o consumo de uma análise (banco se disponível, senão memória)."""
    if repo is not None and getattr(repo, "enabled", False) and user:
        repo.record_usage(user["id"], kind, cost_credits=1)
        return
    month = _month_key()
    cur_month, count = _mem.get(telegram_id, (month, 0))
    if cur_month != month:
        count = 0
    _mem[telegram_id] = (month, count + 1)


def _count_used(telegram_id: int, user: dict | None, repo) -> int | None:
    """Análises usadas no mês. None = banco indisponível (chamador decide;
    devolver 0 aqui liberaria análises ilimitadas durante qualquer instabilidade)."""
    if repo is not None and getattr(repo, "enabled", False) and user:
        try:
            month_start = datetime.now(timezone.utc).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            res = (
                repo.client.table("usage_events")
                .select("id", count="exact")
                .eq("user_id", user["id"])
                .gte("created_at", month_start.isoformat())
                .execute()
            )
            return res.count or 0
        except Exception:
            return None
    month, count = _mem.get(telegram_id, (_month_key(), 0))
    return count if month == _month_key() else 0


def reset_memory() -> None:
    """Só para testes."""
    _mem.clear()
