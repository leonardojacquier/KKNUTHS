"""O selo julga a DECISÃO — com o que se sabia na hora, não com o resultado.

25/09: 7 análises desde 06/09 abriram com "✅ Você jogou bem" e marcaram ❌
no river, justificando com a carta que caiu ou com a mão que o vilão mostrou:

  "❌ *River* Q♠ — pagou 7.3bb… mas a Q♠ completou o straight do BB e sua
   equity caiu pra 0% → −7.3bb."
  "❌ *River* — o A♥ pareia a mesa… Sem decisão sua também."

Pelo manual, ❌ é "erro claro". Este guarda confere cada linha de placar com
❌/🟡 antes da entrega:

  1. street em que o herói NÃO decidiu nada (all-in antes, só veio carta):
     não existe veredito. O selo vira 🃏 — evento, não julgamento.
  2. ❌ num CALL justificado pelo RESULTADO, quando a conta da decisão
     (equity contra o range que o vilão representava, `ev_streets`) diz que
     o call tinha preço: a linha é reescrita com a conta da decisão.

O que ele NÃO faz, de propósito:
  · não mexe em ❌ justificado por leitura/técnica ("essa linha é valor
    quase sempre nesse field") — o modelo pode ter razão que a conta
    aproximada não vê;
  · não mexe em ❌ de call que a conta confirma como caro;
  · não mexe em aposta/raise (o EV de aposta tem premissas demais para o
    guarda reescrever com segurança) — só registra.
"""
from __future__ import annotations

import re

from app.models.canonical import ActionType, CanonicalHand, StreetName

_LINHA = re.compile(
    r"^(?P<selo>❌|🟡)\s*\*(?P<street>Pr[ée]|Flop|Turn|River)\*(?P<resto>.*)$",
    re.M | re.I)
_STREET = {"pre": StreetName.PREFLOP, "pré": StreetName.PREFLOP,
           "flop": StreetName.FLOP, "turn": StreetName.TURN,
           "river": StreetName.RIVER}
_NOME = {StreetName.PREFLOP: "pré-flop", StreetName.FLOP: "flop",
         StreetName.TURN: "turn", StreetName.RIVER: "river"}

# a justificativa é o RESULTADO: a carta que caiu, a mão que apareceu, a
# equity contra cartas que só se viram depois
_PELO_RESULTADO = re.compile(
    r"caiu\s+(?:pra|para|a)\s+(?:0|zero)|a\s+zero|equity\s+(?:foi|vai)\s+a"
    r"|\b0\s*%|passou\s+o\s+seu|completou|fechou\s+o\s+(?:straight|flush|full)"
    r"|virou\s+(?:a\s+m[ãa]o|o\s+jogo|trinca|full)|pareou|pareia"
    r"|apareceu\s+com|ele\s+(?:tinha|mostrou)|contra\s+(?:AA|KK|QQ|JJ|o\s+full)"
    r"|azar|cooler|sem\s+decis[ãa]o",
    re.I)


def _acoes_do_heroi(hand: CanonicalHand, street: StreetName) -> list:
    st = hand.street(street)
    if not st:
        return []
    return [a for a in st.actions
            if a.actor == hand.hero and a.type != ActionType.POST]


def _decisao_da_street(decisoes: list[dict], street: StreetName) -> dict | None:
    """A última decisão do herói naquela street, se for um call."""
    nome = _NOME[street]
    nos = [d for d in decisoes if d.get("street") == nome]
    return nos[-1] if nos and nos[-1].get("acao") == "call" else None


def conferir_selo(texto: str, hand: CanonicalHand,
                  decisoes: list[dict] | None = None
                  ) -> tuple[str, list[dict]]:
    """Confere as linhas ❌/🟡 do placar. Devolve (texto, achados).

    `decisoes` é o `ev_por_street(hand)["decisoes"]`; se não vier, é
    calculado só quando há uma linha suspeita (a conta custa segundos)."""
    if not texto or not hand or not getattr(hand, "hero", None):
        return texto, []
    linhas = list(_LINHA.finditer(texto))
    if not linhas:
        return texto, []

    achados: list[dict] = []
    novo = texto
    for m in reversed(linhas):                      # de trás pra frente: offsets
        street = _STREET.get(m.group("street").lower())
        if street is None:
            continue
        resto = m.group("resto")

        # 1) sem decisão do herói nessa street: não há veredito
        if not _acoes_do_heroi(hand, street):
            linha_nova = f"🃏 *{m.group('street')}*{resto}"
            novo = novo[:m.start()] + linha_nova + novo[m.end():]
            achados.append({"street": _NOME[street], "motivo": "sem_decisao",
                            "selo_antes": m.group("selo")})
            continue

        # 2) ❌ num call, justificado pelo resultado
        if m.group("selo") != "❌" or not _PELO_RESULTADO.search(resto):
            continue
        if decisoes is None:
            try:
                from app.analysis.ev_streets import ev_por_street

                decisoes = ev_por_street(hand).get("decisoes") or []
            except Exception:                        # noqa: BLE001
                return novo, achados
        d = _decisao_da_street(decisoes, street)
        if not d or d.get("equity_pct") is None:
            continue
        pote, pagar = float(d.get("pote_bb") or 0), float(d.get("pagar_bb") or 0)
        if pagar <= 0:
            continue
        pedia = 100 * pagar / (pote + pagar)
        tinha = float(d["equity_pct"])
        if tinha < pedia:
            continue                                  # a conta confirma o ❌
        board = f" {d['board']}" if d.get("board") not in (None, "—") else ""
        linha_nova = (
            f"✅ *{m.group('street')}*{board} — pagou {pagar:g}bb num pote de "
            f"{pote:g}bb: pedia {pedia:.1f}%, e contra o range que ele "
            f"representava você tinha {tinha:.1f}% → call certo. A mão dele "
            f"só apareceu depois; ela explica o resultado, não muda a decisão.")
        novo = novo[:m.start()] + linha_nova + novo[m.end():]
        achados.append({"street": _NOME[street], "motivo": "resultado_virou_selo",
                        "pedia_pct": round(pedia, 1), "tinha_pct": tinha})
    achados.reverse()
    return novo, achados
