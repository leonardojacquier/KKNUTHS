"""HISTÓRIA DO RESULTADO — quem estava na frente em cada rua, pela conta.

Caso real (07/08, print do dono): A4o pagou o preço num shove de 3.6bb,
levou call de ATo e a análise fechou com "esse cooler de river (você tinha
dois pares, o vilão fechou full house)". A conta diz outra coisa: 29% no
pré, 29% no flop, 0% no turn — o aluno nunca esteve na frente, a mão foi
decidida no PRÉ e o river não mudou nada. E "os dois pares" eram da mesa.
Um dia antes, a mesma doença na mão de KK: "virar trinca de Q no river foi
azar DELE" — o vilão que virou a trinca e GANHOU.

O modelo narra o desfecho de imaginação. Isto aqui calcula a trajetória de
equity rua a rua (determinístico, custo zero de LLM) e entrega a leitura
pronta; o prompt manda seguir ELA. Cooler/bad beat só existe se você estava
na frente e a carta virou — dominação decidida no pré não é cooler.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

# reclamação de azar de carta: só é verdade quando a liderança VIROU
_GRITO_DE_AZAR = re.compile(r"cooler|bad ?beat|suck ?out", re.I)


def historia_do_resultado(h) -> dict | None:
    """A trajetória da mão até o showdown. None quando não dá para contar.

    Precisa de showdown de verdade: as duas cartas do herói, board completo
    e pelo menos um vilão com as DUAS cartas viradas (vilão que mostrou uma
    carta só, como o SB que exibe um 5 ao foldar, fica de fora — equity
    contra meia mão é chute, e chute é exatamente o que isto substitui).
    """
    from app.analysis.equity import describe_hand, equity_vs_hands

    hero_cards = list(getattr(h, "hero_cards", None) or [])
    board = list(getattr(h, "final_board", None) or [])
    shown = dict(getattr(h, "shown_cards", None) or {})
    hero_nome = getattr(h, "hero", None)
    if len(hero_cards) != 2 or len(board) != 5:
        return None
    viloes = {nome: list(cs) for nome, cs in shown.items()
              if nome != hero_nome and len(cs or []) == 2}
    if not viloes:
        return None

    campo = list(viloes.values())
    eq: dict[str, int] = {}
    for rua, n in (("pre", 0), ("flop", 3), ("turn", 4), ("river", 5)):
        e = equity_vs_hands(hero_cards, campo, board[:n])
        if e is None:
            return None
        eq[rua] = round(e * 100)

    na_frente = [rua for rua, v in eq.items() if v > 50]
    ganhou = hero_nome in (getattr(h, "collected", None) or {})
    # o river decidiu? Só se a liderança era outra no turn.
    river_virou = (eq["turn"] > 50) != (eq["river"] > 50)

    if ganhou:
        viloes_txt = "; ".join(
            f"{n} mostrou {' '.join(c)}" for n, c in viloes.items())
        leitura = (
            f"Você GANHOU este pote — o showdown confirmou sua mão melhor "
            f"({viloes_txt}, tudo PIOR que a sua). PROIBIDO narrar derrota, "
            "dizer que a mão dele te bate, ou que ele 'apareceu com' uma "
            "combinação que ganha: ele apareceu com a mão que PERDEU.")
    elif not na_frente:
        leitura = (
            f"Você esteve ATRÁS em todas as ruas (pré {eq['pre']}%, flop "
            f"{eq['flop']}%, turn {eq['turn']}%). A mão foi decidida no "
            "PRÉ-FLOP; o river não mudou nada. PROIBIDO chamar de cooler, "
            "bad beat ou azar de carta — perder estando atrás o tempo todo "
            "é o resultado esperado da situação, não uma virada.")
    elif river_virou:
        leitura = (
            f"Você estava na frente até o turn ({eq['turn']}%) e o river "
            "virou a mão. Aqui SIM é azar de carta: decisão certa, resultado "
            "ruim — diga isso.")
    else:
        virada = next((r for r in ("flop", "turn") if eq[r] <= 50), "flop")
        leitura = (
            f"Você começou na frente e a liderança virou no {virada} "
            f"(pré {eq['pre']}%, flop {eq['flop']}%, turn {eq['turn']}%). "
            "Narre a rua em que a mão realmente escapou — não o river.")

    return {
        "ganhou": ganhou,
        "equity_pct": eq,
        "esteve_na_frente_em": na_frente,
        "river_mudou_o_vencedor": river_virou,
        "sua_mao_final": describe_hand(hero_cards, board),
        "mao_final_dos_viloes": {n: describe_hand(c, board)
                                 for n, c in viloes.items()},
        "leitura": leitura,
    }


# "o vilão apareceu com 77" — verbos de SHOWDOWN seguidos de notação de mão.
# Ranks em MAIÚSCULA de propósito: com re.I, a palavra "as" ("apareceu com
# as cartas...") viraria A♠ e o detector acusaria frase inocente.
_CITA_SHOWDOWN = re.compile(
    r"(?:apareceu|mostrou|abriu|revelou|virou)\s+(?:com\s+)?(?:exatamente\s+)?"
    r"\*{0,2}((?:10|[AKQJT98765432]){2}[so]?)\b")


def citou_showdown_errado(texto: str, h) -> dict | None:
    """A mão que o texto diz que apareceu no showdown bate com a que veio?

    Caso real (07/08): o vilão mostrou 7♦2♦ (72s) e a análise fechou com "o
    vilão apareceu com 77 exatos numa das duas combinações que faltavam" —
    narrou derrota numa mão que o aluno GANHOU, contradizendo o showdown
    gravado duas linhas acima. Cartas viradas são dado, não interpretação:
    citar errado é mentira que a máquina prova.

    Devolve {"citado", "reais", "trecho"} na primeira citação que não bate
    com NENHUMA mão mostrada (nem a do herói — citar a própria mão certa é
    legítimo). None se não há citação ou todas conferem.
    """
    if not texto:
        return None
    from app.analysis.pushfold import canonical_hand

    shown = dict(getattr(h, "shown_cards", None) or {})
    reais = set()
    for cs in shown.values():
        if len(cs or []) == 2:
            try:
                reais.add(canonical_hand(list(cs)))
            except Exception:
                pass
    hero_cards = list(getattr(h, "hero_cards", None) or [])
    if len(hero_cards) == 2:
        try:
            reais.add(canonical_hand(hero_cards))
        except Exception:
            pass
    if not reais:
        return None
    # "72s" e "72o" citados sem sufixo viram "72": aceita os dois lados
    aceitas = reais | {r.rstrip("so") for r in reais}
    for m in _CITA_SHOWDOWN.finditer(texto):
        citado = m.group(1).replace("10", "T").upper().replace("S", "s") \
            if m.group(1)[-1] in "so" else m.group(1).replace("10", "T")
        citado = citado[:2].upper() + citado[2:]
        if citado in aceitas or citado.rstrip("so") in aceitas:
            continue
        i = max(0, m.start() - 60)
        return {"citado": citado, "reais": sorted(reais),
                "trecho": texto[i:m.end() + 60]}
    return None


def narrou_azar_inexistente(texto: str, historia: dict | None) -> str | None:
    """O texto gritou 'cooler/bad beat' numa mão sem virada? Devolve o trecho.

    Só acusa o caso provadamente falso: perdeu, nunca esteve na frente, e
    mesmo assim o texto fala em cooler. 'Variância' e 'azar' soltos passam —
    perder um 29/71 É variância; o que não existe é a VIRADA."""
    if not texto or not historia:
        return None
    if historia.get("ganhou") or historia.get("esteve_na_frente_em"):
        return None
    m = _GRITO_DE_AZAR.search(texto)
    if not m:
        return None
    i = max(0, m.start() - 60)
    return texto[i:m.end() + 60]
