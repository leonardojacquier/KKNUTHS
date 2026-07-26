"""CUSTO REAL de cada chamada ao modelo — em dólar, não em "créditos".

Por que existe: até aqui o produto contava USOS. `record_usage` grava o
inteiro 1 e pronto. Nenhuma linha do código sabia quanto custa uma análise,
e por isso **nenhum preço era defensável** — qualquer plano seria chute, e
chute em custo erra sempre pro lado caro. O teto de 50 análises/mês foi
decidido sem esse número; este módulo existe para que o piloto produza ele.

O que registra, por chamada:
  • tokens de entrada, saída, escrita e LEITURA de cache (o cache muda o
    custo em 10x — ignorá-lo daria um número inventado);
  • o dólar calculado com a tabela oficial de preços;
  • a TAREFA (análise, conversa, leitura de print…) e o dono da conversa.

O detalhamento por tarefa é o que decide a próxima economia: se a conversa
depois da análise custa mais que a análise, ela vai pro modelo barato.

Regra dura: modelo sem preço na tabela é registrado com `usd = None` e um
aviso no log. Nunca inventa preço, nunca assume zero — um custo falso é
pior que custo nenhum, porque parece medição.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# US$ por 1 milhão de tokens: (entrada, saída).
# Tabela oficial da API Anthropic, conferida em 2026-06-24.
PRECOS: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

# multiplicadores do cache sobre o preço de ENTRADA (docs oficiais):
# leitura 0,1x; escrita 1,25x no TTL de 5 min (que é o que usamos, ephemeral).
LEITURA_CACHE = 0.10
ESCRITA_CACHE = 1.25

_SEM_PRECO_AVISADO: set[str] = set()


def preco_do_modelo(modelo: str | None) -> tuple[float, float] | None:
    """(entrada, saída) por 1M tokens, ou None se o modelo é desconhecido.

    Aceita sufixo de data (`claude-haiku-4-5-20251001`) porque é assim que
    ele está no .env de produção hoje.
    """
    if not modelo:
        return None
    if modelo in PRECOS:
        return PRECOS[modelo]
    for nome, preco in PRECOS.items():
        if modelo.startswith(nome):
            return preco
    if modelo not in _SEM_PRECO_AVISADO:
        _SEM_PRECO_AVISADO.add(modelo)
        log.warning("custo: modelo '%s' fora da tabela de preços — os tokens "
                    "serão registrados, o dólar não.", modelo)
    return None


def custo_usd(modelo: str | None, entrada: int, saida: int,
              cache_leitura: int = 0, cache_escrita: int = 0) -> float | None:
    """Dólares desta chamada. None quando não sei o preço do modelo."""
    preco = preco_do_modelo(modelo)
    if preco is None:
        return None
    p_in, p_out = preco
    total = (entrada * p_in
             + cache_leitura * p_in * LEITURA_CACHE
             + cache_escrita * p_in * ESCRITA_CACHE
             + saida * p_out) / 1_000_000
    return round(total, 6)


def medir(resp, modelo: str | None, tarefa: str = "outro") -> dict | None:
    """Extrai o bloco `usage` da resposta e devolve o registro pronto.

    Devolve None quando a resposta não traz usage (mock em teste, stream
    interrompido) — nesses casos não há nada honesto a registrar.
    """
    u = getattr(resp, "usage", None)
    if u is None:
        return None
    entrada = int(getattr(u, "input_tokens", 0) or 0)
    saida = int(getattr(u, "output_tokens", 0) or 0)
    c_read = int(getattr(u, "cache_read_input_tokens", 0) or 0)
    c_write = int(getattr(u, "cache_creation_input_tokens", 0) or 0)
    if not (entrada or saida or c_read or c_write):
        return None
    return {
        "tarefa": tarefa,
        "modelo": modelo,
        "entrada": entrada,
        "saida": saida,
        "cache_leitura": c_read,
        "cache_escrita": c_write,
        "usd": custo_usd(modelo, entrada, saida, c_read, c_write),
    }


def registrar(resp, modelo: str | None, tarefa: str = "outro",
              telegram_id: int | None = None,
              user_id: str | None = None) -> dict | None:
    """Mede e grava em `bot_events` (event='custo_llm').

    Escolhi `bot_events` de propósito: `detail` é jsonb, então isto entra em
    produção sem migração de schema e sem risco de derrubar o insert de uso.
    Contabilidade NUNCA pode quebrar a resposta do aluno — daí o try/except
    largo aqui dentro, em vez de espalhado por quem chama.
    """
    try:
        reg = medir(resp, modelo, tarefa)
        if reg is None:
            return None
        from app.db import get_repository

        detalhe = dict(reg)
        if user_id:
            detalhe["user_id"] = user_id
        get_repository().log_event(telegram_id, None, "custo_llm", detalhe)
        return reg
    except Exception as exc:  # nunca derruba a resposta
        log.debug("custo: não consegui registrar (%s)", exc)
        return None


# ------------------------------------------------------------------ leitura
def eventos_de_custo(repo, desde_iso: str,
                     telegram_id: int | None = None) -> list[dict]:
    """Eventos 'custo_llm' desde uma data (paginado — a tabela cresce)."""
    out: list[dict] = []
    step = 1000
    for page in range(30):
        q = (repo.client.table("bot_events")
             .select("telegram_id,detail,created_at")
             .eq("event", "custo_llm")
             .gte("created_at", desde_iso))
        if telegram_id is not None:
            q = q.eq("telegram_id", telegram_id)
        rows = (q.order("created_at")
                .range(page * step, page * step + step - 1)
                .execute().data) or []
        out += rows
        if len(rows) < step:
            break
    return out


def somar(eventos: list[dict]) -> dict:
    """Agrega os eventos em dólares. Função PURA — testável sem banco.

    `chamadas_sem_preco` não é enfeite: se ele for > 0, o total está
    SUBESTIMADO e quem lê o número precisa saber disso.
    """
    total = 0.0
    tokens_in = tokens_out = 0
    sem_preco = 0
    por_tarefa: dict[str, float] = {}
    por_pessoa: dict[int, float] = {}
    for ev in eventos:
        d = ev.get("detail") or {}
        usd = d.get("usd")
        tokens_in += int(d.get("entrada") or 0) + int(d.get("cache_leitura") or 0) \
            + int(d.get("cache_escrita") or 0)
        tokens_out += int(d.get("saida") or 0)
        if usd is None:
            sem_preco += 1
            continue
        total += usd
        tarefa = str(d.get("tarefa") or "outro")
        por_tarefa[tarefa] = round(por_tarefa.get(tarefa, 0.0) + usd, 6)
        tg = ev.get("telegram_id")
        if tg is not None:
            por_pessoa[tg] = round(por_pessoa.get(tg, 0.0) + usd, 6)
    return {
        "chamadas": len(eventos),
        "chamadas_sem_preco": sem_preco,
        "usd": round(total, 4),
        "tokens_entrada": tokens_in,
        "tokens_saida": tokens_out,
        "por_tarefa": dict(sorted(por_tarefa.items(),
                                  key=lambda kv: -kv[1])),
        "por_pessoa": dict(sorted(por_pessoa.items(),
                                  key=lambda kv: -kv[1])),
    }


# ---------------------------------------------------------------- relatório
def texto_do_mes(agr: dict, nomes: dict[int, str] | None = None,
                 usos: dict[int, int] | None = None,
                 dolar: float = 5.4) -> str:
    """Mensagem do /quem. Função PURA — testável sem banco e sem Telegram.

    Mostra o custo POR ANÁLISE de cada aluno, que é o único número que
    permite escolher preço: plano só fecha se a mensalidade cobrir o teto
    de análises vezes esse valor.
    """
    nomes = nomes or {}
    usos = usos or {}
    if not agr["chamadas"]:
        return ("💸 *Custo do mês*\n\nNenhuma chamada registrada ainda. "
                "O log de custo passa a valer a partir do deploy — "
                "meses anteriores não têm esse dado.")

    linhas = [f"💸 *Custo do mês* — US$ {agr['usd']:.2f} "
              f"(≈ R$ {agr['usd'] * dolar:.2f})",
              f"_{agr['chamadas']} chamadas · "
              f"{agr['tokens_entrada'] / 1000:.0f}k entrada / "
              f"{agr['tokens_saida'] / 1000:.0f}k saída_"]
    if agr["chamadas_sem_preco"]:
        linhas.append(f"⚠️ {agr['chamadas_sem_preco']} chamada(s) de modelo "
                      "fora da tabela de preços — o total está SUBESTIMADO.")

    if agr["por_tarefa"]:
        linhas.append("\n*Onde vai o dinheiro*")
        for tarefa, usd in list(agr["por_tarefa"].items())[:8]:
            fatia = 100 * usd / agr["usd"] if agr["usd"] else 0
            linhas.append(f"• {tarefa}: US$ {usd:.2f} ({fatia:.0f}%)")

    if agr["por_pessoa"]:
        linhas.append("\n*Por aluno*")
        for tg, usd in list(agr["por_pessoa"].items())[:10]:
            quem = nomes.get(tg) or str(tg)
            n = usos.get(tg, 0)
            por_analise = (f" · US$ {usd / n:.2f}/análise" if n else "")
            linhas.append(f"• {quem}: US$ {usd:.2f}"
                          + (f" em {n} análises" if n else "")
                          + por_analise)
    return "\n".join(linhas)


def relatorio_do_mes(telegram_id: int | None = None) -> str:
    """Junta banco + agregação + texto. É o corpo do /quem."""
    from datetime import datetime, timezone

    from app.db import get_repository

    repo = get_repository()
    if not getattr(repo, "enabled", False):
        return "Banco desligado — sem histórico de custo para ler."
    inicio = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        eventos = eventos_de_custo(repo, inicio, telegram_id)
    except Exception as exc:
        return f"Não consegui ler o custo: {type(exc).__name__}: {exc}"
    agr = somar(eventos)

    nomes: dict[int, str] = {}
    usos: dict[int, int] = {}
    try:
        users = (repo.client.table("users")
                 .select("id,telegram_id,username").execute().data) or []
        por_id = {u["id"]: u for u in users if u.get("id")}
        for u in users:
            tg = u.get("telegram_id")
            if tg is not None:
                nomes[int(tg)] = u.get("username") or str(tg)
        gastos = (repo.client.table("usage_events")
                  .select("user_id").gte("created_at", inicio)
                  .execute().data) or []
        for g in gastos:
            u = por_id.get(g.get("user_id"))
            if u and u.get("telegram_id") is not None:
                tg = int(u["telegram_id"])
                usos[tg] = usos.get(tg, 0) + 1
    except Exception:
        pass  # nomes e contagem são enfeite; o dólar é o que importa
    return texto_do_mes(agr, nomes, usos)
