"""Corretor DETERMINÍSTICO de terminologia — roda em toda saída do coach.

O ciclo era: calque sai pro aluno → juiz acusa às 8h → dono lê → eu proíbo
no prompt. O prompt reduz, mas modelo desobedece prompt de vez em quando —
e o aluno da vez recebe o texto torto mesmo assim.

Este módulo fecha o buraco pro subconjunto MECÂNICO: troca que é segura sem
entender a frase. Mesma regra do guarda da saída: conserto determinístico,
nunca uma segunda chamada de modelo (que é o que já falhou).

O que NÃO entra aqui, de propósito — e fica só no vigia do juiz:
  'passou'     -> 'o pote passou de 20bb' é português normal
  'sequência'  -> 'sequência de 3-bets' é português normal
  'par alto'   -> pode ser overpair OU top pair; trocar errado é pior
  'igualar'    -> raro e ambíguo
Regra de bolso: o corretor só faz a troca que um regex acerta em 100% dos
casos. O resto é sinalizado, não consertado.
"""
from __future__ import annotations

import logging
import re

_RANK = r"(?:10|[AKQJT2-9])"

# (padrão, substituição) — ordem importa: o mais específico primeiro
_TROCAS: list[tuple[re.Pattern, str]] = [
    # 'sevens full of twos' ao pé da letra: '7 cheio de 2'
    (re.compile(rf"\b({_RANK})\s+chei[oa]s?\s+de\s+({_RANK})\b", re.I),
     r"full de \1 com \2"),
    (re.compile(r"\bcheck\s+atr[áa]s\b", re.I), "check behind"),
    (re.compile(r"\bsequ[êe]ncia\s+de\s+cor\b", re.I), "straight flush"),
    (re.compile(r"\bcartas?\s+altas?\b", re.I), "high card"),
    # 'aumentou' só quando é inequivocamente a ação de apostar (segue 'pra
    # 6bb' / 'para 3x'): 'a pressão aumentou' fica intacta
    (re.compile(r"\bre-?aumentou\s+(pra|para)\b", re.I), r"deu re-raise \1"),
    (re.compile(r"\baumentou\s+(pra|para)\b", re.I), r"deu raise \1"),
    # carta crua vira carta com ícone: 'Kh' -> 'K♥' (regra da casa; o juiz
    # acusava e o Sonnet escorregou na 1ª rodada do A/B). Duas exclusões de
    # português: 'As' (artigo) fica fora — espadas só de 2 a K; e o ás não
    # converte antes de pontuação, senão a interjeição 'Ah,' vira 'A♥,'.
    (re.compile(r"\b((?:10|[KQJT98765432]))s\b"), r"\1♠"),
    (re.compile(r"\b((?:10|[KQJT98765432]))h\b"), r"\1♥"),
    (re.compile(r"\b((?:10|[KQJT98765432]))d\b"), r"\1♦"),
    (re.compile(r"\b((?:10|[KQJT98765432]))c\b"), r"\1♣"),
    (re.compile(r"\bA([hdc])\b(?![,.!?…])"),
     lambda m: "A" + {"h": "♥", "d": "♦", "c": "♣"}[m.group(1)]),
]


# ---- glossário vivo (tabela `glossario`) -----------------------------------
# O linguista propõe, o dono aprova via /termo, e daqui pra frente o termo é
# executado deterministicamente: tipo 'corrigir' entra nas trocas da entrega,
# tipo 'vigiar' entra na lista do juiz. Cache de 10 min: o glossário muda
# poucas vezes por dia e a entrega não pode esperar um select por resposta.
_CACHE: dict = {"ate": 0.0, "corrigir": [], "vigiar": []}
_TTL = 600.0


def _regex_literal(errado: str) -> re.Pattern:
    """Palavra/expressão literal com borda — 'carta alta' não casa 'encarta'."""
    return re.compile(r"(?<!\w)" + re.escape(errado) + r"(?!\w)", re.I)


def _carregar_glossario() -> None:
    import time

    if time.time() < _CACHE["ate"]:
        return
    _CACHE["ate"] = time.time() + _TTL
    try:
        from app.db import get_repository

        repo = get_repository()
        if not repo.enabled:
            return
        linhas = (repo.client.table("glossario")
                  .select("errado,certo,tipo").eq("aprovado", True)
                  .execute().data) or []
    except Exception:
        return  # sem banco, o glossário fixo continua valendo
    _CACHE["corrigir"] = [(_regex_literal(l["errado"]), l["certo"])
                          for l in linhas if l["tipo"] == "corrigir"]
    _CACHE["vigiar"] = [l["errado"].lower()
                        for l in linhas if l["tipo"] == "vigiar"]


def vigiados() -> list[str]:
    """Termos aprovados como 'vigiar' — o juiz soma à lista fixa dele."""
    _carregar_glossario()
    return list(_CACHE["vigiar"])


def corrigir(texto: str) -> str:
    """Aplica as trocas mecânicas (fixas + glossário aprovado no banco).
    Devolve o texto (intacto se nada casou)."""
    if not texto:
        return texto
    _carregar_glossario()
    saida = texto
    trocas: list[str] = []
    for padrao, sub in _TROCAS + _CACHE["corrigir"]:
        novo = padrao.sub(sub, saida)
        if novo != saida:
            trocas.append(padrao.pattern[:40])
            saida = novo
    if trocas:
        logging.getLogger("termos").info(
            "calques corrigidos na entrega: %s", trocas)
    return saida
