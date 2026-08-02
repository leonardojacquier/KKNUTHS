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
]


def corrigir(texto: str) -> str:
    """Aplica as trocas mecânicas. Devolve o texto (intacto se nada casou)."""
    if not texto:
        return texto
    saida = texto
    trocas: list[str] = []
    for padrao, sub in _TROCAS:
        novo = padrao.sub(sub, saida)
        if novo != saida:
            trocas.append(padrao.pattern[:40])
            saida = novo
    if trocas:
        logging.getLogger("termos").info(
            "calques corrigidos na entrega: %s", trocas)
    return saida
