"""Conferência de números da ANÁLISE — a garantia chega ao caminho principal.

"O modelo escreve, a conferência garante" já protegia a síntese do dossiê;
a análise de mão — o produto — continuava na base da confiança. Depois do
juiz de 15/08 (nota 6.3, meta era 7), o combinado com o dono entrou: todo
número que a análise cita tem que ter lastro no contexto da mão ou no
resultado das ferramentas. Número sem lastro = uma reescrita corretiva; se
persistir, entrega com registro em bot_events — nunca silêncio.

As regras anti-falso-positivo importam tanto quanto a checagem:
- notação de carta sai antes ("10♣", "9♥" não são números da análise);
- inteiro pequeno sem decimal é jargão (3-bet, 2 pares, 4 jogadores);
- um número do texto casa se É arredondamento de algo do lastro, na
  precisão em que foi escrito — inclusive trocando escala de fração e
  porcentagem (0.227 no contexto lastreia "22,7%" e "23%" no texto).
"""
from __future__ import annotations

import re

_CARTA = re.compile(r"(?:10|[2-9TJQKA])[♠♥♦♣]")
_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")
# inteiros até este valor, sem casa decimal, são jargão e não contam
_JARGAO_ATE = 5


def numeros_do_lastro(*fontes) -> set[float]:
    """Todo número presente nas fontes (contexto JSON, resultados de tool)."""
    ns: set[float] = set()
    for f in fontes:
        for m in _NUMERO.findall(str(f or "")):
            ns.add(float(m.replace(",", ".")))
    return ns


def _tem_lastro(valor: float, casas: int, lastro: set[float]) -> bool:
    tolerancia = 0.5 * 10 ** -casas + 1e-9
    for a in lastro:
        for escala in (a, a * 100, a / 100):
            if abs(escala - valor) <= tolerancia:
                return True
    return False


def conferir_analise(texto: str, lastro: set[float]) -> list[str]:
    """Os números do texto SEM lastro. [] = análise aprovada."""
    limpo = _CARTA.sub(" ", texto or "")
    fora: list[str] = []
    for m in _NUMERO.findall(limpo):
        casas = len(re.split("[.,]", m)[-1]) if ("," in m or "." in m) else 0
        valor = float(m.replace(",", "."))
        if casas == 0 and valor <= _JARGAO_ATE:
            continue
        if not _tem_lastro(valor, casas, lastro):
            fora.append(m)
    return fora
