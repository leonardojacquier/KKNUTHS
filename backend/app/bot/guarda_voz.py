"""GUARDA DA VOZ — a análise soa como conversa ou como formulário?

Por que existe: medido em 403 análises reais de 45 dias, o bloco depois do
placar é 58% do texto (740 de 1662 chars, n=183), e boa parte dele repete o
que o placar já disse. O título "A conta que mais pesa" aparece em 25% —
e a origem era NOSSA, escrita na instrução do coach em llm.py. A narração
de bastidor ("deixa eu conferir o EV...") sobrevive em 23%.

Regra é pedido; conferência é garantia. O R3/R7 do prompt pedem; isto mede
e, onde é seguro, conserta.

O que CORRIGE e o que só MEDE, e o porquê de cada escolha:
  corrige  título fixo         rótulo sai sem tocar na frase (Task 2)
  corrige  narração de busca   frase inteira de bastidor, sai limpa
  mede     bloco pós-placar    cortar prosa de LLM na marra estraga
  mede     autocorreção        n=4 em 403; conserto arrisca mais que resolve
  mede     número repetido     repetir a conta no fecho pode ser ÊNFASE

O que NÃO é defeito, apesar de parecer: "anotei no caderno" (32 análises).
É voz de coach e é a regra A2 funcionando. A primeira versão da spec mandava
apagar — teria removido a frase mais humana da resposta.
"""
from __future__ import annotations

import re

# medido: média de 740 chars depois do placar, 34% das análises acima de 800
TETO_POS_PLACAR = 800

_SELOS = ("✅", "🟡", "❌")

# "A conta que mais pesa:" com ou sem negrito markdown em volta
_TITULO_FIXO = re.compile(
    r"\*{0,2}\s*a\s+conta\s+que\s+mais\s+pesa\s*\*{0,2}\s*:\s*\*{0,2}\s*",
    re.I)

# bastidor de BUSCA — 91/403. NÃO inclui "anotei no caderno", que é voz de
# coach: o guarda que apaga isso piora exatamente o que viemos melhorar.
_NARRACAO = re.compile(
    r"\b(deixa\s+eu\s+(conferir|ver|puxar|checar|rodar|calcular)|"
    r"vou\s+(conferir|puxar|checar|rodar|calcular)|"
    r"me\s+deixa\s+(ver|conferir))\b", re.I)

_AUTOCORRECAO = re.compile(r"\.{2,3}\s*digo\b", re.I)

# números que contam: 12bb, 34%, +1.49bb, -0,6bb
_NUMERO = re.compile(r"[-+]?\d+[.,]?\d*\s*(?:bb|%)")


def bloco_pos_placar(texto: str) -> str:
    """Tudo que vem DEPOIS da última linha de placar.

    É o sinal principal. A primeira versão media 'número repetido', que dá
    para contar por regex mas mira o sintoma: repetir o +1.49bb no fecho é
    ênfase legítima. O defeito é o parágrafo INTEIRO não acrescentar nada,
    e o proxy medível disso é o comprimento.
    """
    linhas = (texto or "").split("\n")
    ultimo = -1
    for i, ln in enumerate(linhas):
        if ln.lstrip().startswith(_SELOS):
            ultimo = i
    if ultimo < 0:
        return ""
    return "\n".join(linhas[ultimo + 1:]).strip()


def numeros_repetidos(texto: str) -> list[str]:
    """Números que aparecem no placar E de novo na prosa do fechamento."""
    linhas = (texto or "").split("\n")
    do_placar = {m.group(0).replace(" ", "")
                 for ln in linhas if ln.lstrip().startswith(_SELOS)
                 for m in _NUMERO.finditer(ln)}
    na_prosa = {m.group(0).replace(" ", "")
                for m in _NUMERO.finditer(bloco_pos_placar(texto))}
    return sorted(do_placar & na_prosa)


def problemas_de_voz(texto: str) -> list[str]:
    """Defeitos de VOZ numa resposta do coach (lista vazia = passou).

    Função pura — é o contrato que o R3/R7 do prompt promete ao aluno.
    """
    t = (texto or "").strip()
    if not t:
        return []
    probs: list[str] = []

    bloco = bloco_pos_placar(t)
    if len(bloco) > TETO_POS_PLACAR:
        probs.append(f"bloco pós-placar longo ({len(bloco)} chars; "
                     f"teto {TETO_POS_PLACAR})")
    if _TITULO_FIXO.search(t):
        probs.append("título fixo 'A conta que mais pesa'")
    if _NARRACAO.search(t):
        probs.append("bastidor de busca narrado ao aluno")
    if _AUTOCORRECAO.search(t):
        probs.append("autocorreção dentro do texto entregue")
    repetidos = numeros_repetidos(t)
    if repetidos:
        probs.append(f"número do placar repetido na prosa: "
                     f"{', '.join(repetidos[:4])}")
    return probs
