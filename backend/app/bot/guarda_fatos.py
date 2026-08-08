"""GUARDA DOS FATOS — a análise afirma coisa que não é verdade?

Caso real (07/08, print do dono): numa análise de KK pagando all-in, o coach
escreveu "o vilão só te vira favorito com QQ ou AA". KK ganha de QQ em 80%
das vezes. O aluno que acredita nisso passa a foldar KK contra 4-bet.

Isso é da mesma família do guarda da saída: o prompt JÁ proíbe (F1 "nunca
invente números", F4 "sem showdown fale em range"), e mesmo assim saiu. Regra
é pedido; isto é conferência — e esta dá pra fazer com a conta na mão, porque
"X é favorito contra Y" é uma pergunta fechada que o motor de equity responde.

Só mexe no que consegue PROVAR errado: acha a frase, testa cada mão citada,
e corrige a lista para as mãos que realmente ganham do herói. Sem frase do
tipo, não toca em nada.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

# "só te vira favorito com QQ ou AA", "só perde para AA", "só está atrás de AA"
_DOMINANCIA = re.compile(
    # o VERBO em qualquer tempo: "só perde para AA" pegava, mas o texto real
    # entregue em 07/08 dizia "só PERDIA pra 77 ou AA/1010" — imperfeito — e
    # passou batido. Mesma armadilha em "perdeu", "perdem", "perderia".
    r"(?P<abre>só\s+(?:te\s+)?(?:vira\s+favorito\s+(?:com|contra)|"
    r"perd(?:e|ia|eu|em|iam|eria|eriam)\s+(?:para|pra|pro)|"
    r"est[aá]\s+atr[áa]s\s+d[eo]|estava\s+atr[áa]s\s+d[eo]|"
    r"fica\s+atr[áa]s\s+d[eo]|ficava\s+atr[áa]s\s+d[eo]|"
    r"apanha(?:va)?\s+(?:para|pra|de)))"
    # a lista de mãos para NA primeira fronteira de oração. Sem isso o
    # `[^.;\n]+` engolia o resto da frase: "só perdia pra 77 ou AA — o vilão
    # apareceu com 72s" virava uma lista só, e a correção comia o trecho
    # depois do travessão.
    r"\s+(?P<maos>[^.;,\n—–]{1,60})", re.I)

# A MESMA mentira com a ordem trocada: "Só AA e QQ te viram favorito" (lição
# 26, real, com KK na mão). O verbo vem DEPOIS das mãos, então o padrão de
# cima não via nada — e essa é justamente a forma que o destilador escreve,
# porque copia o título ("Só X te vira favorito") em vez da frase corrida.
_DOMINANCIA_INVERTIDA = re.compile(
    r"(?P<abre>\bs[óo]|\bapenas|\bsomente)\s+"
    r"(?P<maos>[^.;,\n—–]{1,60}?)\s+"
    r"(?P<fecha>(?:te\s+)?(?:vira(?:m|ram|va|vam)?\s+favorito|"
    r"ganha(?:m|va|vam)?\s+de\s+(?:voc[êe]|vc|ti|si)|"
    r"te\s+bate(?:m|ria|riam)?|"
    r"est[áa](?:o)?\s+na\s+frente|estava(?:m)?\s+na\s+frente))", re.I)

# AA, KK, AKs, AKo, QQ+ — o vocabulário de mão que aparece nessas frases
_MAO = re.compile(r"\b([AKQJT2-9])\1\b|\b([AKQJT2-9])([AKQJT2-9])([so])\b",
                  re.I)

_NAIPES = ("h", "d", "c", "s")


def _combos(nota: str) -> list[list[str]] | None:
    """'QQ' -> [['Qh','Qd']]; 'AKo' -> [['Ah','Kd']]; 'AKs' -> [['Ah','Kh']].

    Um combo representativo basta: a equity pré-flop de QQ contra KK é a
    mesma para qualquer par de naipes (a menos de bloqueio irrelevante aqui).
    """
    n = nota.strip().upper().replace("10", "T")
    if len(n) == 2 and n[0] == n[1]:
        return [[n[0] + "h", n[1] + "d"]]
    if len(n) == 3 and n[2] in ("S", "O"):
        a, b = n[0], n[1]
        if a == b:
            return None
        return [[a + "h", b + "h"]] if n[2] == "S" else [[a + "h", b + "d"]]
    return None


def maos_citadas(trecho: str) -> list[str]:
    """As mãos nomeadas num pedaço de frase, na ordem em que aparecem."""
    achadas = []
    for m in _MAO.finditer(trecho or ""):
        if m.group(1):
            nota = (m.group(1) * 2).upper()
        else:
            nota = (m.group(2) + m.group(3) + m.group(4)).upper()
            nota = nota[:2] + nota[2].lower()
        if nota not in achadas:
            achadas.append(nota)
    return achadas


def quem_ganha_do_heroi(hero: list[str], candidatas: list[str],
                        board: list[str] | None = None) -> list[str]:
    """Das mãos citadas, quais REALMENTE ganham do herói.

    COM board, a conta é sobre a mão FEITA — que é outra pergunta. "seu full
    de 7 com A só perdia pra 77" é uma frase de river, e comparar equity
    pré-flop ali responde a pergunta errada: pré-flop 77 é favorito contra
    A7s, mas NAQUELE board o herói tem full de 7 com A e 77 seria quadra
    impossível. Sem board (frase de pré-flop), segue a equity de mão vs mão.
    """
    from app.analysis.equity import equity_vs_hand, equity_vs_hands

    b = [c for c in (board or []) if isinstance(c, str) and c]
    mortas = {(c[0].upper() + c[1:].lower()) for c in list(hero) + b}
    vencem = []
    for nota in candidatas:
        combos = _combos(nota)
        if not combos:
            continue
        vil = combos[0]
        # mão que usa carta já visível não é combo possível — pula em vez de
        # devolver equity de um baralho impossível
        if {(c[0].upper() + c[1:].lower()) for c in vil} & mortas:
            continue
        try:
            eq = (equity_vs_hands(list(hero), [vil], b) if len(b) >= 3
                  else equity_vs_hand(list(hero), vil))
        except Exception:
            continue
        if eq is None:
            continue
        if eq < 0.5:                      # o herói perde => a citada ganha
            vencem.append(nota)
    return vencem


def conferir_dominancia(texto: str, hero: list[str],
                        board: list[str] | None = None) -> tuple[str, list[str]]:
    """Corrige frases de 'só perde para X'. Devolve (texto, erros_achados).

    Conservador: se NENHUMA das mãos citadas ganha do herói, a frase inteira
    é falsa e vira o nome da mão que realmente ganha; se alguma ganha e outra
    não, ficam só as verdadeiras. Sem mão citada, não mexe.

    `board` muda a PERGUNTA: com mesa, a conta é sobre a mão feita. Sem ele,
    uma frase de river era conferida com equity pré-flop — resposta certa
    para a pergunta errada.
    """
    if not texto or not hero or len(hero) != 2:
        return texto, []

    erros: list[str] = []

    def _verdade(citadas: list[str]) -> tuple[list[str], str] | None:
        """(mentiras, lista_certa) — None quando a frase já está correta."""
        vencem = quem_ganha_do_heroi(hero, citadas, board)
        mentiras = [x for x in citadas if x not in vencem]
        if not mentiras:
            return None
        if vencem:
            return mentiras, " ou ".join(vencem)
        # nenhuma das citadas ganha: procura a verdade entre os pares
        # altos, que é de onde essa frase sempre fala
        return mentiras, " ou ".join(_pares_que_ganham(hero, board)) or "nada"

    def _corrige(m: re.Match) -> str:
        trecho = m.group("maos")
        citadas = maos_citadas(trecho)
        if not citadas:
            return m.group(0)
        achado = _verdade(citadas)
        if not achado:
            return m.group(0)
        mentiras, certo = achado
        erros.extend(mentiras)
        # preserva o resto da frase depois das mãos (", e isso é raro")
        resto = _cauda(trecho, citadas)
        return f"{m.group('abre')} {certo}{resto}"

    def _corrige_invertida(m: re.Match) -> str:
        citadas = maos_citadas(m.group("maos"))
        if not citadas:
            return m.group(0)
        achado = _verdade(citadas)
        if not achado:
            return m.group(0)
        mentiras, certo = achado
        erros.extend(mentiras)
        return f"{m.group('abre')} {certo} {m.group('fecha')}"

    novo = _DOMINANCIA.sub(_corrige, texto)
    novo = _DOMINANCIA_INVERTIDA.sub(_corrige_invertida, novo)
    if erros:
        log.warning("guarda de fatos: mão citada como favorita sem ser: %s",
                    ", ".join(erros))
    return novo, erros


def _cauda(trecho: str, citadas: list[str]) -> str:
    """O que vem depois da última mão citada — vírgula, 'e isso é raro', etc."""
    fim = 0
    for m in _MAO.finditer(trecho):
        fim = m.end()
    resto = trecho[fim:]
    if resto.strip():
        return resto
    # só espaço em branco: devolve UM espaço, não string vazia — sem isso
    # "pra AA — o vilão" saía colado ("pra AA— o vilão")
    return " " if resto else ""


# "A conta que mais pesa:", "a conta:", "fazendo a conta" — o coach ANUNCIA
# que vai mostrar a matemática
_ANUNCIA_CONTA = re.compile(
    r"^[^\n]{0,40}\ba\s+conta\b[^\n]{0,40}:", re.I | re.M)
_TEM_NUMERO = re.compile(r"[-+−]?\d+[.,]?\d*\s*(bb|%|fichas)|[-+−]\d+[.,]\d|\d+%")


def conta_sem_numero(texto: str) -> list[str]:
    """Parágrafos que se anunciam como 'a conta' e não trazem número nenhum.

    No print de 07/08: "A conta que mais pesa: com KK e stack curto você paga
    esse all-in sempre, sem pensar duas vezes." Prosa com nome de conta — e
    era a TERCEIRA vez que o texto dizia a mesma coisa, o que faz o aluno
    achar que o coach está enrolando.

    Só DETECTA (vira evento). Reescrever prosa de LLM na marra estraga mais
    do que conserta; o que isto dá é a taxa — se for alta, o prompt está
    errado e eu conserto lá, com número na mão em vez de impressão.
    """
    achados = []
    for m in _ANUNCIA_CONTA.finditer(texto or ""):
        # o parágrafo inteiro a partir do anúncio
        fim = (texto or "").find("\n\n", m.start())
        trecho = (texto or "")[m.start():fim if fim > 0 else len(texto or "")]
        if not _TEM_NUMERO.search(trecho):
            achados.append(trecho[:120].strip())
    return achados


def _pares_que_ganham(hero: list[str],
                      board: list[str] | None = None) -> list[str]:
    """Os pares que ganham do herói (a resposta que a frase queria dar).
    Só pares: é o caso que aparece nessas frases."""
    ordem = "AKQJT98765432"
    return quem_ganha_do_heroi(hero, [r * 2 for r in ordem], board)
