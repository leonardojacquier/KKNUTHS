"""GUARDA DA SAÍDA — a resposta responde o que foi pedido?

Por que existe: três vezes nesta semana o aluno pediu um gráfico e recebeu
prosa. O motor estava pronto e certo nas três. O que faltou foi a ponte —
e a ponte não se conserta com mais regra no prompt (já são quatro: C10,
C11, C11b, C11c). Regra é pedido; isto é conferência.

Mesma lógica do portão de testes no deploy: não confio na intenção, confio
na verificação ANTES de entregar. O juiz da saída já fazia isso, mas roda
no dia seguinte — tarde demais para quem está esperando a resposta.

Como funciona:
  1. classifica o PEDIDO (gráfico? número?) a partir do texto do aluno;
  2. confere a ENTREGA (saiu gráfico? tem número na resposta?);
  3. o que faltou é REMEDIADO chamando a ferramenta na marra, e o resultado
     entra na resposta em vez da desculpa;
  4. tudo vira evento — é assim que a taxa de entrega deixa de ser opinião.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

_PEDE_GRAFICO = re.compile(
    r"\b(gr[áa]fico|imagem|figura|matriz|tabela|chart|"
    r"(manda|mande|mostra|me\s+mostra)\s+o\s+range|"
    r"range\s+(de|com|do)\s+ev)\b", re.I)
_PEDE_NUMERO = re.compile(
    r"\b(ev\b|equity|odds|quanto\s+(custou|rende|vale|perdi|ganhei)|"
    r"vale\s+a\s+pena|joguei\s+certo|era\s+call|era\s+fold|"
    r"qual\s+o\s+(ev|range))\b", re.I)
# números que contam como resposta: 12bb, 34%, +1,9, −0.6
_TEM_NUMERO = re.compile(r"[-+−]?\d+[.,]?\d*\s*(bb|%|fichas)|[-+−]\d+[.,]\d")


_STREET = re.compile(r"\b(flop|turn|river)\b", re.I)


def street_pedida(texto: str) -> str | None:
    """A street que ele citou. Sem isto o guarda montava o gráfico da street
    mais profunda — ele perguntou do TURN e receberia o river."""
    m = _STREET.search(texto or "")
    return m.group(1).lower() if m else None


def pedido_do_aluno(texto: str) -> set[str]:
    """O que ele pediu, em tipos que dá para conferir objetivamente."""
    t = texto or ""
    pedido = set()
    if _PEDE_GRAFICO.search(t):
        pedido.add("grafico")
    if _PEDE_NUMERO.search(t):
        pedido.add("numero")
    return pedido


def faltou(pedido: set[str], resposta: str, tem_grafico: bool) -> set[str]:
    """O que foi pedido e NÃO foi entregue."""
    falhas = set()
    if "grafico" in pedido and not tem_grafico:
        falhas.add("grafico")
    if "numero" in pedido and not _TEM_NUMERO.search(resposta or ""):
        falhas.add("numero")
    return falhas


def remediar(telegram_id: int, falhas: set[str],
             street: str | None = None) -> tuple[str, list]:
    """Chama a ferramenta na marra e devolve (texto extra, specs de gráfico).

    Só usa contas determinísticas — nada de pedir ao modelo de novo, que é
    exatamente o que já falhou. Se nem isso der, devolve uma frase HONESTA
    dizendo o motivo, nunca uma desculpa vazia.
    """
    from app.analysis.equity import pretty_cards
    from app.analysis.ev_streets import ev_por_street
    from app.analysis.postflop_spot import spot_da_mao
    from app.bot.processing import conversation_hand

    h = conversation_hand(telegram_id)
    if h is None:
        return ("\n\n_(Eu ia puxar a conta, mas perdi a referência da mão "
                "desta conversa. Me reenvia a mão que eu faço na hora.)_", [])

    specs: list = []
    partes: list[str] = []

    if "grafico" in falhas:
        spot = spot_da_mao(h, street)
        if not spot.get("error"):
            specs.append(("posflop", tuple(spot["board"]), spot["oop_range"],
                          spot["ip_range"], float(spot["pot"]),
                          float(spot["stack"]), spot["player"], "ev"))
            partes.append(
                f"📊 Gráfico do *{spot['street']}* {pretty_cards(spot['board'])} "
                f"— pote {spot['pot']:g}bb, stack efetivo {spot['stack']:g}bb. "
                "Sai logo abaixo (o equilíbrio leva ~1 min).")
        elif "heads-up" in str(spot.get("error")):
            partes.append(
                "📊 A matriz 13×13 é heads-up e este pote foi multiway — "
                "então vai a conta que vale aqui:")
            falhas = falhas | {"numero"}
        else:
            partes.append(f"📊 Sem gráfico desta vez: {spot['error']}.")

    if "numero" in falhas:
        r = ev_por_street(h)
        if r.get("error"):
            partes.append(f"Sem a conta desta vez: {r['error']}.")
        else:
            linhas = []
            for d in r["decisoes"]:
                if d.get("ev_bb") is None:
                    continue
                linhas.append(
                    f"• *{d['street']}* ({d['adversarios']} adv, pote "
                    f"{d['pote_bb']:g}bb): {d['acao']} → *{d['ev_bb']:+.2f}bb*"
                    + (f" · melhor era {d['melhor']}"
                       if d.get("custo_do_erro_bb", 0) > 0.05 else ""))
            if linhas:
                partes.append("🧮 *EV de cada decisão sua*\n"
                              + "\n".join(linhas[:6])
                              + f"\n\nCusto total da linha: "
                                f"*{r['custo_total_bb']:g}bb*.")

    if not partes:
        return "", specs
    return "\n\n" + "\n\n".join(partes), specs


def conferir_e_remediar(telegram_id: int, pergunta: str, resposta: str,
                        tem_grafico: bool) -> tuple[str, list]:
    """Portão: confere a entrega e conserta o que faltou. Devolve
    (resposta final, specs de gráfico a anexar)."""
    from app.db import get_repository

    pedido = pedido_do_aluno(pergunta)
    if not pedido:
        return resposta, []
    falhas = faltou(pedido, resposta, tem_grafico)
    repo = get_repository()
    try:
        repo.log_event(telegram_id, None,
                       "entrega_falha" if falhas else "entrega_ok",
                       {"pediu": sorted(pedido), "faltou": sorted(falhas)})
    except Exception:
        pass
    if not falhas:
        return resposta, []
    try:
        extra, specs = remediar(telegram_id, falhas,
                                street_pedida(pergunta))
    except Exception as exc:
        log.warning("remediação da entrega falhou: %s", exc)
        return resposta, []
    if not extra:
        return resposta, []
    try:
        repo.log_event(telegram_id, None, "entrega_remediada",
                       {"faltou": sorted(falhas), "graficos": len(specs)})
    except Exception:
        pass
    return (resposta or "") + extra, specs
