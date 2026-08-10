"""O mesmo vilão em dois retratos: o que ele MOSTROU e o que ele FEZ.

O dono pediu com todas as letras: "considerando showdown o perfil é um;
considerando o que não vimos, mas pela linha dele, o perfil é Y". Os dois
retratos existem porque medem populações diferentes:

- O retrato A (showdown) só contém as mãos em que ALGUÉM PAGOU — é concreto
  (cartas vistas), mas é uma amostra selecionada exatamente pela condição
  que se quer estudar, e costuma ser minúscula (3 a 26 mãos na base real).
- O retrato B (linha) não precisa de carta nenhuma, então cobre TODAS as
  agressões dele — c-bet, barrelas, potes levados sem mostrar, sizing. É
  maior e não tem o viés do pagamento; em troca, nunca viu uma carta.

A DIVERGÊNCIA entre os dois é o produto: "pelo showdown parece honesto, pela
linha leva 11 de 14 potes sem mostrar" é uma conclusão que nenhum retrato dá
sozinho. Rótulo e divergência só saem quando o intervalo de Wilson sustenta
(mesma régua de mesa.py); os FATOS (contagens) saem sempre, com o n junto.
Nada aqui chama modelo; nada aqui vira "blefa X%".
"""
from __future__ import annotations

from typing import Any, NamedTuple

from app.analysis.defesa import _wilson_lo
from app.analysis.dossie import Dossie, _linha_do_vilao
from app.models.canonical import ActionType

# showdowns para o rótulo do retrato A; abaixo disso é relato, não perfil
MINIMO_SHOWDOWN = 3
# agressões pós-flop para rótulo/divergência do retrato B
MINIMO_LINHA = 8
# fração das agressões sem showdown (piso de Wilson) que sustenta o rótulo
ESCURO_ACIMA_DE = 0.5

_POS_FLOP = ("flop", "turn", "river")


class PerfilShowdown(NamedTuple):
    n: int
    valor: int                  # inclui valor fino
    blefes: int
    pagou: int
    rotulo: str                 # honesto no que mostrou | mostrou blefe | ...


class PerfilLinha(NamedTuple):
    agressoes: int              # mãos com agressão pós-flop dele
    sem_showdown: int           # dessas, ninguém viu as cartas
    levou_sem_mostrar: int      # e ainda levou o pote
    cbet_k: int
    cbet_n: int                 # oportunidades: agrediu o pré e veio flop
    barrela_k: int
    barrela_n: int              # apostou o flop e veio turn
    fracao_media: dict          # rua -> fração média do pote das apostas dele
    rotulo: str                 # agride e não mostra | "" (sem sustento)


class PerfilDuplo(NamedTuple):
    a: PerfilShowdown | None
    b: PerfilLinha | None
    divergencia: str | None     # None = a amostra não sustenta comparação


def _rua(st: Any) -> str:
    return str(getattr(st.name, "value", st.name)).lower()


def perfil_showdown(d: Dossie | None) -> PerfilShowdown | None:
    """Retrato A. As contagens vêm do dossiê (classificação pela LINHA)."""
    if d is None or not d.showdowns:
        return None
    valor, blefes, pagou = len(d.valor), len(d.blefes), len(d.pagou)
    if d.showdowns < MINIMO_SHOWDOWN:
        rotulo = "amostra curta"
    elif blefes and valor:
        rotulo = "misto no que mostrou"
    elif blefes:
        rotulo = "mostrou blefe"
    elif valor:
        rotulo = "honesto no que mostrou"
    else:
        rotulo = "só pagou/mostrou"
    return PerfilShowdown(n=d.showdowns, valor=valor, blefes=blefes,
                          pagou=pagou, rotulo=rotulo)


def _agrediu(st: Any, nome: str) -> bool:
    return any(a.actor == nome and a.type in (ActionType.BET, ActionType.RAISE)
               for a in (st.actions or ()))


def _fracoes_do_vilao(h: Any, nome: str) -> dict:
    """Fração do pote NAQUELE momento, por rua, das apostas/raises dele.

    Mesmo pote-corrente da narrativa (leitura_vilao.narrar_mao): raise soma
    'até', não '+'. Pré-flop fica de fora — sizing pré se mede em bb e o
    storyboard já mostra."""
    fracoes: dict[str, list[float]] = {}
    pote = 0.0
    for st in (getattr(h, "streets", None) or ()):
        rua = _rua(st)
        na_street: dict[str, float] = {}
        for a in (st.actions or ()):
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - na_street.get(a.actor, 0.0)
            add = max(0.0, add)
            if (a.actor == nome and rua in _POS_FLOP and pote > 0 and add > 0
                    and a.type in (ActionType.BET, ActionType.RAISE)):
                fracoes.setdefault(rua, []).append(add / pote)
            na_street[a.actor] = na_street.get(a.actor, 0.0) + add
            pote += add
    return fracoes


def perfil_linha(hands: list, nome: str) -> PerfilLinha | None:
    """Retrato B: só a linha, todas as mãos — inclusive as com showdown.

    (O retrato A é um SUBCONJUNTO selecionado destas; excluir os showdowns
    daqui tornaria os dois retratos incomparáveis por construção.)"""
    agressoes = sem_showdown = levou_sem = 0
    cbet_k = cbet_n = barrela_k = barrela_n = 0
    fracoes: dict[str, list[float]] = {}

    for h in (hands or []):
        streets = {_rua(st): st for st in (getattr(h, "streets", None) or ())}
        if not any(nome == a.actor for st in streets.values()
                   for a in (st.actions or ())):
            continue
        _, agrediu_em, _ = _linha_do_vilao(h, nome)
        if agrediu_em in _POS_FLOP:
            agressoes += 1
            mostrou = bool((getattr(h, "shown_cards", None) or {}).get(nome))
            if not mostrou:
                sem_showdown += 1
                if (getattr(h, "collected", None) or {}).get(nome):
                    levou_sem += 1
        # c-bet: ele foi o ÚLTIMO agressor do pré e a mão viu flop
        pre, flop = streets.get("preflop"), streets.get("flop")
        if pre is not None and flop is not None and (flop.actions or ()):
            ultimo = None
            for a in (pre.actions or ()):
                if a.type in (ActionType.BET, ActionType.RAISE):
                    ultimo = a.actor
            if ultimo == nome:
                cbet_n += 1
                cbet_k += int(_agrediu(flop, nome))
        # 2ª barrela: apostou o flop e o turn teve ação
        turn = streets.get("turn")
        if (flop is not None and _agrediu(flop, nome)
                and turn is not None and (turn.actions or ())):
            barrela_n += 1
            barrela_k += int(_agrediu(turn, nome))
        for rua, fs in _fracoes_do_vilao(h, nome).items():
            fracoes.setdefault(rua, []).extend(fs)

    if not agressoes:
        return None
    media = {rua: round(sum(fs) / len(fs), 2)
             for rua, fs in fracoes.items() if fs}
    rotulo = ""
    if (agressoes >= MINIMO_LINHA
            and _wilson_lo(sem_showdown, agressoes) >= ESCURO_ACIMA_DE):
        rotulo = "agride e não mostra"
    return PerfilLinha(agressoes=agressoes, sem_showdown=sem_showdown,
                       levou_sem_mostrar=levou_sem, cbet_k=cbet_k,
                       cbet_n=cbet_n, barrela_k=barrela_k,
                       barrela_n=barrela_n, fracao_media=media, rotulo=rotulo)


def montar(hands: list, nome: str, d: Dossie | None) -> PerfilDuplo:
    a = perfil_showdown(d)
    b = perfil_linha(hands, nome)
    return PerfilDuplo(a=a, b=b, divergencia=_divergencia(a, b))


def _divergencia(a: PerfilShowdown | None, b: PerfilLinha | None
                 ) -> str | None:
    """A frase que nenhum retrato dá sozinho. Só sai SUSTENTADA:
    A com n mínimo, B com rótulo (que já exige Wilson)."""
    if a is None or b is None:
        return None
    if a.n < MINIMO_SHOWDOWN or b.rotulo != "agride e não mostra":
        return None
    if a.rotulo == "honesto no que mostrou":
        return (f"Pelo showdown ele parece honesto ({a.valor} de {a.n} mãos "
                f"mostradas agredindo eram valor) — mas você só viu a parte "
                f"em que alguém pagou: pela linha, {b.sem_showdown} de "
                f"{b.agressoes} agressões dele terminaram sem showdown, "
                f"{b.levou_sem_mostrar} levando o pote. O retrato honesto é "
                f"o retrato das exceções.")
    if a.blefes:
        return (f"Ele JÁ mostrou blefe ({a.blefes}×) e ainda leva "
                f"{b.levou_sem_mostrar} de {b.agressoes} potes agredindo sem "
                f"mostrar — os dois retratos apontam para o mesmo lado: "
                f"pague mais leve.")
    return None


def texto(p: PerfilDuplo) -> list[str]:
    """As linhas dos dois retratos — para o chat e para o HTML formatarem."""
    linhas: list[str] = []
    if p.a:
        linhas.append(f"Pelo que ele MOSTROU ({p.a.n} mãos): {p.a.rotulo} — "
                      f"{p.a.valor} valor · {p.a.blefes} blefe · "
                      f"{p.a.pagou} pagou")
    else:
        linhas.append("Pelo que ele MOSTROU: nada — nenhum showdown dele")
    if p.b:
        b = p.b
        l2 = (f"Pela LINHA ({b.agressoes} agressões pós-flop): "
              f"{b.sem_showdown} sem showdown, {b.levou_sem_mostrar} potes "
              f"levados sem mostrar")
        if b.cbet_n:
            l2 += f" · c-bet {b.cbet_k}/{b.cbet_n}"
        if b.barrela_n:
            l2 += f" · 2ª barrela {b.barrela_k}/{b.barrela_n}"
        if b.fracao_media:
            l2 += " · aposta média " + " ".join(
                f"{rua} {round(100 * fr)}%" for rua, fr in
                sorted(b.fracao_media.items(),
                       key=lambda kv: _POS_FLOP.index(kv[0])))
        if b.rotulo:
            l2 += f" → {b.rotulo}"
        linhas.append(l2)
    else:
        linhas.append("Pela LINHA: nenhuma agressão pós-flop dele nestas mãos")
    return linhas
