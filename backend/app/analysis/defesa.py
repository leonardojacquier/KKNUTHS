"""Defesa contra a aposta do river: a pergunta que TEM resposta exata.

O pedido original era "onde ele provavelmente blefou" nas mãos sem showdown.
Medido antes de escrever isto: nas 39 mãos da base em que um vilão apostou o
river e FOI PAGO, ele tinha mão fraca em 2 (5%). Só que essas 39 são as mãos
em que alguém pagou — e as 88 sem showdown são as mãos em que todos largaram.
A seleção acontece exatamente sobre a coisa a estimar: paga-se quando se
desconfia. Aplicar os 5% nas 88 seria usar um número medido sob a condição
contrária, e qualquer "provavelmente blefou X%" aqui seria invenção com cara
de medida. Este módulo se recusa a fazer isso.

O que ele faz no lugar são duas coisas honestas:

1. VIRA a pergunta. Não importa quanto o vilão blefa; importa quanto VOCÊ
   larga. Se ele aposta `b` num pote `p`, o blefe dele paga o risco quando
   você folda mais que b/(p+b) das vezes — teorema de indiferença, não
   estimativa, e não precisa das cartas dele. As 88 mãos sem showdown deixam
   de ser especulação e viram o denominador da SUA defesa.

2. LISTA as mãos não vistas com os fatos que existem — a linha dele, o
   tamanho, e que ninguém viu — sem probabilidade nenhuma pendurada.

A comparação com o limiar é por FRAÇÃO MEDIANA do pote (a aposta típica que
o aluno enfrentou, robusta ao overbet isolado) e o veredito de overfold só
sai pelo LIMITE INFERIOR de Wilson da taxa de fold — com 6 folds em 8 a
média diz 75%, mas o intervalo ainda abraça 40%, e acusar overfold aí seria
o mesmo pecado do "provavelmente blefou".
"""
from __future__ import annotations

import math
from typing import Any, NamedTuple

from app.models.canonical import ActionType, StreetName

_AGRESSIVAS = (ActionType.BET, ActionType.RAISE)

# amostra mínima para VEREDITO (o relato dos números sai com qualquer n>0)
MINIMO_PARA_VEREDITO = 8


class ApostaEnfrentada(NamedTuple):
    hand_id: str
    vilao: str
    fracao_do_pote: float | None    # b/p; None quando os valores não vieram
    resposta: str                   # fold | call | raise
    houve_showdown: bool
    linha_do_vilao: str


class Defesa(NamedTuple):
    apostas: int
    folds: int
    fracao_mediana: float | None
    limiar_fold: float | None       # b/(p+b) na fração mediana
    fold_taxa: float
    fold_lo: float                  # limite inferior de Wilson (95%)
    veredito: str                   # overfold | ok | amostra_curta


def _hero_de(hand: Any) -> str:
    nome = getattr(hand, "hero", None)
    if nome:
        return str(nome)
    for p in (getattr(hand, "players", None) or ()):
        if getattr(p, "is_hero", False):
            return str(p.name)
    return "Hero"


def _pote_antes_do_river(hand: Any) -> float:
    """Fichas no pote quando o river começa (raise conta 'até', não '+')."""
    total = 0.0
    for st in (getattr(hand, "streets", None) or ()):
        nome = getattr(st.name, "value", st.name)
        if str(nome).lower() == "river":
            break
        na_street: dict[str, float] = {}
        for a in (st.actions or ()):
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - na_street.get(a.actor, 0.0)
            add = max(0.0, add)
            na_street[a.actor] = na_street.get(a.actor, 0.0) + add
            total += add
    return total


def _linha(hand: Any, nome: str) -> str:
    from app.analysis.dossie import _linha_do_vilao

    return _linha_do_vilao(hand, nome)[2]


def aposta_enfrentada(hand: Any) -> ApostaEnfrentada | None:
    """A PRIMEIRA aposta do river feita por um vilão com o herói ainda na
    mão, e o que o herói fez diante dela. None quando não houve.

    A primeira, não a última: a resposta do herói à primeira agressão é a
    decisão de defesa; depois de um raise dele a mão virou outra conversa.
    """
    hero = _hero_de(hand)
    river = next((s for s in (getattr(hand, "streets", None) or ())
                  if str(getattr(s.name, "value", s.name)).lower() == "river"),
                 None)
    if river is None:
        return None

    acoes = list(river.actions or ())
    idx = next((i for i, a in enumerate(acoes)
                if a.type in _AGRESSIVAS and a.actor != hero), None)
    if idx is None:
        return None
    aposta = acoes[idx]

    resposta = next((a for a in acoes[idx + 1:] if a.actor == hero), None)
    if resposta is None:
        # herói agiu antes e não voltou a falar = já não estava na mão
        # (fold anterior) ou a mão fechou sem decisão dele — não é defesa
        return None
    tipo = resposta.type.value if hasattr(resposta.type, "value") else str(resposta.type)

    pote = _pote_antes_do_river(hand)
    # apostas do river ANTERIORES à do vilão (check-call antes de raise etc.)
    for a in acoes[:idx]:
        pote += max(0.0, a.amount)
    b = float(aposta.amount or 0)
    fracao = round(b / pote, 3) if b > 0 and pote > 0 else None

    mostradas = getattr(hand, "shown_cards", None) or {}
    return ApostaEnfrentada(
        hand_id=str(getattr(hand, "hand_id", "") or ""),
        vilao=str(aposta.actor),
        fracao_do_pote=fracao,
        resposta=str(tipo).lower(),
        houve_showdown=bool(mostradas.get(aposta.actor)),
        linha_do_vilao=_linha(hand, str(aposta.actor)))


def _wilson_lo(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    den = 1 + z * z / n
    centro = p + z * z / (2 * n)
    ajuste = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centro - ajuste) / den)


def _mediana(xs: list[float]) -> float | None:
    ys = sorted(xs)
    if not ys:
        return None
    meio = len(ys) // 2
    return ys[meio] if len(ys) % 2 else (ys[meio - 1] + ys[meio]) / 2


def medir(hands: list, vilao: str | None = None) -> Defesa | None:
    """A defesa do herói contra apostas do river — de um vilão, ou de todos.

    `veredito` = "overfold" SÓ quando o limite inferior de Wilson da taxa de
    fold fica acima do limiar da fração mediana. Média acima do limiar com
    intervalo que ainda o abraça é "ok" com os números à mostra — o leitor
    vê a distância, o código não acusa.
    """
    alvo = (vilao or "").strip().lower()
    apostas = [e for h in (hands or []) if (e := aposta_enfrentada(h))
               and (not alvo or e.vilao.strip().lower() == alvo)]
    if not apostas:
        return None

    folds = sum(1 for e in apostas if e.resposta == "fold")
    fracoes = [e.fracao_do_pote for e in apostas if e.fracao_do_pote]
    mediana = _mediana(fracoes)
    limiar = round(mediana / (1 + mediana), 3) if mediana else None
    n = len(apostas)
    lo = _wilson_lo(folds, n)

    if n < MINIMO_PARA_VEREDITO or limiar is None:
        veredito = "amostra_curta"
    elif lo > limiar:
        veredito = "overfold"
    else:
        veredito = "ok"
    return Defesa(apostas=n, folds=folds,
                  fracao_mediana=round(mediana, 2) if mediana else None,
                  limiar_fold=limiar, fold_taxa=round(folds / n, 3),
                  fold_lo=round(lo, 3), veredito=veredito)


def nao_vistas(hands: list, vilao: str) -> list[ApostaEnfrentada]:
    """As apostas do river desse vilão que NINGUÉM viu — os fatos, sem taxa."""
    alvo = vilao.strip().lower()
    return [e for h in (hands or []) if (e := aposta_enfrentada(h))
            and e.vilao.strip().lower() == alvo and not e.houve_showdown]


def texto(d: Defesa | None, escuras: list[ApostaEnfrentada],
          vilao: str, limite: int = 3) -> str:
    """Bloco determinístico dos dois lados: o que não se viu, e a SUA defesa."""
    linhas: list[str] = []
    if escuras:
        linhas.append(f"\n*Apostou o river e ninguém viu* ({len(escuras)})")
        for e in escuras[:limite]:
            tam = (f" ({e.fracao_do_pote:g}× pote)" if e.fracao_do_pote
                   else "")
            linhas.append(f"• _{e.linha_do_vilao}_{tam} — você: {e.resposta}")
        if len(escuras) > limite:
            linhas.append(f"_…e mais {len(escuras) - limite}._")
        linhas.append(
            "_Sem showdown não existe \"provavelmente blefou\": quem paga é "
            "quem vê, e esse filtro entortaria qualquer taxa. O que dá para "
            "medir é a sua defesa:_")

    if d is not None:
        pct = round(100 * d.fold_taxa)
        linhas.append(f"\n🛡 *Sua defesa contra a aposta de river "
                      f"{'dele' if escuras else ''}*")
        base = (f"• Ele apostou {d.apostas}× · você largou {d.folds} "
                f"({pct}%)")
        if d.fracao_mediana is not None and d.limiar_fold is not None:
            base += (f"\n• Tamanho típico {d.fracao_mediana:g}× pote → o "
                     f"blefe dele lucra se você foldar mais que "
                     f"{round(100 * d.limiar_fold)}%")
        linhas.append(base)
        if d.veredito == "overfold":
            linhas.append(
                f"• *Você folda demais contra ele* (mesmo no piso da "
                f"estatística: ≥{round(100 * d.fold_lo)}%). Qualquer duas "
                f"cartas lucram te apostando — não precisa saber quanto ele "
                f"blefa.")
        elif d.veredito == "amostra_curta":
            linhas.append(f"• _Amostra curta ({d.apostas} apostas) — números "
                          f"à mostra, veredito não._")
        else:
            linhas.append("• Sua frequência de defesa não abre espaço para "
                          "blefe automático.")
    return "\n".join(linhas)
