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


# palavras que, logo depois do rótulo, denunciam que a frase DEPENDIA dele:
# tirar o rótulo deixaria um fragmento sem sujeito.
_FRAGMENTO = re.compile(r"^(que|porque|por\s+que|e|mas|ou|então|pois|se)\b",
                        re.I)


def _sem_titulo_fixo(texto: str) -> tuple[str, bool]:
    """Tira o rótulo e promove a frase a início de parágrafo.

    Só quando ela sobrevive sozinha: 'A conta que mais pesa: que você paga
    sempre' vira fragmento se o rótulo sair, e frase partida é o defeito que
    test_corretor_nao_estraga_portugues existe para impedir.

    Corta no início REAL do rótulo, não em m.start(): sem negrito, o trecho
    de espaço em branco opcional no começo de _TITULO_FIXO também casa a
    quebra de linha ANTES dele ('...fácil' + duas quebras + 'A conta...'
    vira o match inteiro, quebras incluídas). Cortar em m.start() comia
    essas quebras sem reemitir e colava o parágrafo anterior no texto
    promovido ('...fácilCom 12bb...') — Critical 1 da revisão de qualidade,
    que também zerava bloco_pos_placar ao juntar a linha de placar com a
    prosa seguinte. 'inicio' avança m.start() pelo tamanho do espaço em
    branco líder do match, preservando-o.

    O trecho de espaço em branco no FIM de _TITULO_FIXO é guloso e não tem
    nada depois dele no padrão: o que sobra em texto[m.end():] nunca começa
    com espaço (medido com espaço múltiplo, quebra dupla e quebra simples
    após o rótulo — sempre 0 nos três). Por isso não existe salto a
    preservar DEPOIS do rótulo, só ANTES.
    """
    saida: list[str] = []
    pos = 0
    mexeu = False
    for m in _TITULO_FIXO.finditer(texto):
        grupo = m.group(0)
        inicio = m.start() + (len(grupo) - len(grupo.lstrip()))
        cabeca = texto[m.end():].lstrip()
        if not cabeca or _FRAGMENTO.match(cabeca):
            continue
        saida.append(texto[pos:inicio])
        saida.append(cabeca[0].upper())
        pos = m.end() + 1
        mexeu = True
    saida.append(texto[pos:])
    return "".join(saida), mexeu


# fronteira real de frase: um "." só separa quando NÃO é ponto decimal.
# Medido: bb/% sempre aparecem com decimal de ponto (12.9bb, +1.49bb) — o
# separador ingênuo ([^.!?]+[.!?]*) tratava TODO ponto como fim de frase e
# cortava exatamente no meio do número, vazando o pedaço mutilado ('49bb')
# para o aluno. Critical 2 da revisão: é a classe de defeito que
# _conferir_numeros em llm.py existe para impedir, só que aqui do lado da
# limpeza de voz em vez do lado da IA.
_FRASE = re.compile(r"(?:[^.!?]|\.(?=\d))+[.!?]*")


def _sem_narracao(texto: str) -> tuple[str, bool]:
    """Remove a FRASE inteira de bastidor, não só a expressão.

    Cortar só 'deixa eu conferir' deixaria 'o EV desse shove.' solto, que é
    pior do que a frase original. O separador de frases é _FRASE, não um
    split ingênuo por ponto: ponto decimal (12.9bb) não é fim de frase.
    """
    mexeu = False
    saidas: list[str] = []
    for paragrafo in texto.split("\n"):
        frases = _FRASE.findall(paragrafo)
        mantidas = [f for f in frases if not _NARRACAO.search(f)]
        if len(mantidas) != len(frases):
            mexeu = True
            paragrafo = "".join(mantidas).strip()
        saidas.append(paragrafo)
    novo = "\n".join(saidas)
    if mexeu:
        # um parágrafo que era só bastidor vira "" e soma às quebras que já
        # separavam parágrafos ('...fácil\n\n\n\nCom 12bb...') — buraco
        # visível que a guarda de 'limpar' não pega, porque só olha o texto
        # INTEIRO vazio, não o parágrafo. Important 3 da revisão.
        novo = re.sub(r"\n{3,}", "\n\n", novo)
    return novo, mexeu


def limpar(texto: str) -> tuple[str, list[str]]:
    """Corrige o que é seguro corrigir. Devolve (texto, o que foi feito).

    Nunca degrada abaixo do que já ia sair: se a limpeza esvaziar o texto,
    a original volta. Mesma disciplina do _conferir_numeros em llm.py.
    """
    t = texto or ""
    if not t.strip():
        # devolve 't' (sempre str), não 'texto': se texto for None, devolver
        # None quebra a assinatura -> tuple[str, list[str]], e a Task 3 chama
        # 'answer, feitos = limpar(answer)' sem guarda de None antes.
        return t, []
    feitos: list[str] = []

    novo, mexeu = _sem_titulo_fixo(t)
    if mexeu:
        feitos.append("título fixo removido")
    novo, mexeu = _sem_narracao(novo)
    if mexeu:
        feitos.append("bastidor de busca removido")

    if not novo.strip():
        return texto, []
    return novo, feitos
