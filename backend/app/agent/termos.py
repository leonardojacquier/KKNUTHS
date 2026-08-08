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
    # 'sevens full of twos' ao pé da letra: '7 cheio de 2'. O "full house"
    # que quase sempre vem antes é ABSORVIDO: sem isso a troca gaguejava —
    # "full house 7 cheio de A" virava "full house full de 7 com A".
    (re.compile(rf"\b(?:full\s*house\s+)?({_RANK})\s+chei[oa]s?\s+de\s+"
                rf"({_RANK})\b", re.I),
     r"full de \1 com \2"),
    (re.compile(r"\bcheck\s+atr[áa]s\b", re.I), "check behind"),
    (re.compile(r"\bsequ[êe]ncia\s+de\s+cor\b", re.I), "straight flush"),
    # plural separado do singular: "suas cartas altas" virava "suas high
    # card", que é pior português que o calque que se queria consertar
    (re.compile(r"\bcartas\s+altas\b", re.I), "high cards"),
    (re.compile(r"\bcarta\s+alta\b", re.I), "high card"),
    # 'aumentou' só quando é inequivocamente a ação de apostar (segue 'pra
    # 6bb' / 'para 3x'): 'a pressão aumentou' fica intacta
    (re.compile(r"\bre-?aumentou\s+(pra|para)\b", re.I), r"deu re-raise \1"),
    (re.compile(r"\baumentou\s+(pra|para)\b", re.I), r"deu raise \1"),
    # (as cartas viram ícone em _cartas_para_icones, abaixo — regex solto
    #  transformava "joguei 3h ontem" em "joguei 3♥ ontem")
]

_SUIT = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
# rank de FACE + naipe é inequívoco: "Kh"/"Qs"/"Jd"/"Tc" não existem em
# português. Já o rank de DÍGITO colide com as unidades mais faladas pelo
# aluno: 3h (horas), 3d (dias), 30s (segundos), 10h (horário do torneio).
_CARTA_FACE = re.compile(r"\b([KQJT])([shdc])\b")
_CARTA_AS = re.compile(r"\bA([hdc])\b(?![,.!?…])")   # 'As' = artigo; 'Ah,' = interjeição
# um dígito só vira carta quando está numa SEQUÊNCIA de cartas — "Ah7h",
# "7c 5s 5c", "A♠ 7♠". Carta solta de dígito ("o 7h do board") fica crua: é
# o preço de não estragar "joguei 3h". Perder um ícone é cosmético; escrever
# "fiquei 2♥ no tilt" é o coach parecendo maluco, que foi a reclamação real.
_TOKEN = r"(?:10|[AKQJT2-9])(?:[shdc]|[♠♥♦♣])"
_SEQUENCIA = re.compile(rf"{_TOKEN}(?:\s*{_TOKEN})+")
_UM_TOKEN = re.compile(r"(10|[AKQJT2-9])([shdc])")


def _cartas_para_icones(texto: str) -> str:
    """'Ah7h' -> 'A♥7♥', mas 'joguei 3h' fica intacto.

    Duas passadas: primeiro as sequências (2+ cartas juntas, onde dígito é
    seguro por contexto), depois as faces e o ás soltos.
    """
    def _seq(m: re.Match) -> str:
        return _UM_TOKEN.sub(lambda c: c.group(1) + _SUIT[c.group(2)],
                             m.group(0))

    t = _SEQUENCIA.sub(_seq, texto or "")
    t = _CARTA_FACE.sub(lambda m: m.group(1) + _SUIT[m.group(2)], t)
    return _CARTA_AS.sub(lambda m: "A" + _SUIT[m.group(1)], t)


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
    saida = _cartas_para_icones(saida)
    if trocas:
        logging.getLogger("termos").info(
            "calques corrigidos na entrega: %s", trocas)
    return saida
