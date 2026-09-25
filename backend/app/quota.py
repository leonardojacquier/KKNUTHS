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

# A CONVERSA TAMBÉM CUSTA. Até 25/09 só o upload passava pela cota: a
# conversa com o coach (Opus + ferramentas, o caminho mais caro por mensagem)
# era ilimitada por construção — "sem isto não há plano vendável"
# (diagnóstico de 06/09, item 14). Peso leve: N mensagens = 1 análise.
MENSAGENS_POR_ANALISE = int(os.getenv("MENSAGENS_POR_ANALISE", "5"))
TIPOS_LEVES = ("conversa",)

# TETO MENSAL POR PLANO. Antes só existiam dois mundos — 50 análises ou
# ilimitado — e o meio-termo ("esse aluno merece 100") só era possível dando
# ilimitado, que é justamente o que não dá para bancar sem saber o custo.
#
# 'piloto' é o plano dos testadores convidados: teto dobrado, prazo do
# piloto, sem cartão. Nome honesto de propósito — 'plus'/'vip' sugere preço
# e vira promessa que ninguém prometeu.
LIMITE_POR_PLANO: dict[str, int] = {
    "free": FREE_MONTHLY_ANALYSES,
    "piloto": int(os.getenv("PILOTO_MONTHLY_ANALYSES", "100")),
}

# planos que o dono pode atribuir pelo bot (o Stripe não conhece 'piloto')
PLANOS_MANUAIS = sorted(set(LIMITE_POR_PLANO) | _UNLIMITED_PLANS)


def limite_do_plano(plan: str | None) -> int | None:
    """Teto mensal do plano. None = ilimitado.

    Plano desconhecido cai no teto do free — fail-closed. Um typo em
    `/planode` não pode virar análise ilimitada e de graça.
    """
    p = (plan or "free").strip().lower()
    if p in _UNLIMITED_PLANS:
        return None
    return LIMITE_POR_PLANO.get(p, FREE_MONTHLY_ANALYSES)

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
    teto = limite_do_plano(plan)
    if teto is None or telegram_id == ADMIN_TELEGRAM_ID:
        return QuotaResult(True, -1, plan)

    # banco ligado mas usuário não veio (falha transitória do get_or_create):
    # também é "não sei a cota" — sem isso cairia no contador em memória, que
    # zera a cada restart do processo
    if repo is not None and getattr(repo, "enabled", False) and not user:
        return QuotaResult(False, 0, plan, degraded=True)

    used = _count_used(telegram_id, user, repo)
    if used is None:
        return QuotaResult(False, 0, plan, degraded=True)
    remaining = max(0, teto - used)
    return QuotaResult(remaining > 0, remaining, plan)


def consume_quota(telegram_id: int, user: dict | None, repo=None, kind: str = "analysis") -> None:
    """Registra o consumo (banco se disponível, senão memória). `kind` em
    TIPOS_LEVES pesa 1/MENSAGENS_POR_ANALISE."""
    leve = kind in TIPOS_LEVES
    if repo is not None and getattr(repo, "enabled", False) and user:
        repo.record_usage(user["id"], kind, cost_credits=0 if leve else 1)
        return
    month = _month_key()
    cur_month, cheias, leves = _mem.get(telegram_id, (month, 0, 0))
    if cur_month != month:
        cheias, leves = 0, 0
    _mem[telegram_id] = (month, cheias + (0 if leve else 1),
                         leves + (1 if leve else 0))


def bloqueio_da_conversa(telegram_id: int, user: dict | None,
                         repo=None) -> str | None:
    """Texto para o aluno se a cota acabou; None se pode seguir.

    Banco instável NÃO bloqueia a conversa (o upload, sim): uma mensagem
    custa 1/MENSAGENS_POR_ANALISE de análise, e travar o papo inteiro por um
    soluço do banco é pior que o custo de algumas respostas."""
    q = check_quota(telegram_id, user, repo)
    if q.allowed or q.degraded:
        return None
    return texto_cota_esgotada(q.plan)


def _count_used(telegram_id: int, user: dict | None, repo) -> int | None:
    """Análises usadas no mês. None = banco indisponível (chamador decide;
    devolver 0 aqui liberaria análises ilimitadas durante qualquer instabilidade)."""
    if repo is not None and getattr(repo, "enabled", False) and user:
        try:
            month_start = datetime.now(timezone.utc).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            def _contar(leves: bool) -> int:
                q = (repo.client.table("usage_events")
                     .select("id", count="exact")
                     .eq("user_id", user["id"])
                     .gte("created_at", month_start.isoformat()))
                if leves:
                    q = q.in_("type", list(TIPOS_LEVES))
                return q.execute().count or 0

            total, leves = _contar(False), _contar(True)
            return (total - leves) + leves // MENSAGENS_POR_ANALISE
        except Exception:
            return None
    month, cheias, leves = _mem.get(telegram_id, (_month_key(), 0, 0))
    if month != _month_key():
        return 0
    return cheias + leves // MENSAGENS_POR_ANALISE


def reset_memory() -> None:
    """Só para testes."""
    _mem.clear()


def dias_ate_renovar(agora: datetime | None = None) -> tuple[int, str]:
    """(dias, data dd/mm) até a cota zerar — vira no 1º do mês, em UTC.

    A contagem de `_count_used` começa no dia 1 às 00:00 UTC; a mensagem
    precisa dizer a MESMA data, senão o aluno volta um dia antes e apanha
    de novo.
    """
    agora = agora or datetime.now(timezone.utc)
    ano, mes = (agora.year + 1, 1) if agora.month == 12 else \
        (agora.year, agora.month + 1)
    virada = datetime(ano, mes, 1, tzinfo=timezone.utc)
    dias = max(1, (virada - agora).days + (1 if (virada - agora).seconds else 0))
    return dias, f"{virada.day:02d}/{virada.month:02d}"


def texto_cota_esgotada(plan: str | None = None,
                        agora: datetime | None = None) -> str:
    """O que o aluno lê quando a cota acaba. Função PURA.

    Era um beco sem saída: "acabaram, renovam no próximo mês" — sem data,
    sem ação, sem alternativa, numa tela em que o aluno tinha acabado de
    mandar um arquivo. E é FALSO que não sobrou nada: a cota conta ANÁLISE
    DE UPLOAD; treino, leitura de vilão, range, banca e a conversa com o
    coach continuam de pé. Quem não sabe disso simplesmente some.
    """
    dias, data = dias_ate_renovar(agora)
    quando = "amanhã" if dias == 1 else f"em {dias} dias"
    teto = limite_do_plano(plan)
    quanto = f"as {teto} análises" if teto else "as análises"
    return (
        f"🚦 Acabaram {quanto} deste mês — renova {quando} ({data}).\n\n"
        "*Isso trava a análise de arquivo/print e a conversa com o coach "
        f"({MENSAGENS_POR_ANALISE} mensagens = 1 análise). Continua liberado:*\n"
        "• /treino — drill num spot das suas mãos\n"
        "• /leitura — adivinhe a mão do vilão\n"
        "• /stats e /evolucao — seu perfil e sua linha do tempo\n"
        "• /range — gráficos 13×13 de qualquer spot\n\n"
        "_Guarda o arquivo que você ia mandar: no dia "
        f"{data} ele entra na hora._"
    )
