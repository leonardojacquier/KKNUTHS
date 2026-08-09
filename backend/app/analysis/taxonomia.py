"""TAXONOMIA DE ERRO — o que permite contar em vez de opinar.

Hoje `hand_analysis.mistakes` guarda a DECISÃO, não o que houve de errado
nela, e sem código nem denominador:

    {"street": "preflop", "to_call": 1.0, "decision": "call",
     "pot_before": 2001.0, "required_equity": 0.0}

Com isso dá para mostrar uma mão. Não dá para dizer "você foldou 9 de 14
vezes nesse spot, e isso custou 2,1bb/100" — que é a frase que separa
diagnóstico de impressão, e é o insumo do plano de estudo, do relatório de
torneio e da medição de evolução.

Cada código aqui tem QUATRO coisas obrigatórias, e é a quarta que quase
sempre falta nas ferramentas do mercado:

  1. um código fechado (nada de texto livre — texto livre não se agrupa)
  2. OPORTUNIDADE computável: quando o spot aconteceu, mesmo que o aluno
     tenha acertado. Sem denominador, "errou 4 vezes" não quer dizer nada:
     4 em 4 e 4 em 400 são jogadores diferentes.
  3. ESCORREGADA computável: o que, naquele spot, foi o erro
  4. CUSTO em bb, e a honestidade de dizer quando ele é ESTIMADO

O erro é medido na DECISÃO, nunca no resultado. Se o detector olhasse
"perdeu o pote", estaria errado por construção — e este projeto já teve
exatamente esse bug (commit 9497ad8, "resultadismo no encanamento").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Iterable

from app.models.canonical import ActionType, CanonicalHand, StreetName


@dataclass(frozen=True)
class Codigo:
    """Um tipo de erro que a ferramenta sabe contar."""
    codigo: str
    nome: str            # como o aluno lê
    pergunta: str        # o problema vira PERGUNTA, não rótulo — é o que
                         # torna o ensino baseado em problema possível
    tolerancia_pct: float   # acima disso a taxa vira candidata a problema
    custo: str              # "exato" | "estimado"
    prereq: tuple[str, ...] = ()   # o que precisa estar resolvido antes


@dataclass
class Observacao:
    """Um spot visto. `escorregada=False` também importa — é o denominador."""
    codigo: str
    escorregada: bool
    custo_bb: float
    hand_id: str
    street: str = "preflop"
    stack_bb: float = 0.0


# ---------------------------------------------------------------- códigos --
CODIGOS: dict[str, Codigo] = {c.codigo: c for c in (
    Codigo("open_perdido", "deixa de abrir mão de ataque",
           "Com o pote não aberto na sua frente, quais mãos você abre desta "
           "posição?", 30.0, "estimado"),
    Codigo("shove_perdido", "não vai de all-in com stack curto quando paga",
           "Com menos de 12bb e ninguém na frente, quais mãos empurram?",
           25.0, "estimado", prereq=("push_fold_nash",)),
    Codigo("shove_largo", "vai de all-in largo demais",
           "Com stack curto, onde é a linha entre empurrar e largar?",
           25.0, "estimado", prereq=("push_fold_nash",)),
    Codigo("call_caro", "paga mais caro do que a mão vale",
           "Quanto de equity este pote está te pedindo, e quanto você tem?",
           25.0, "exato", prereq=("pot_odds",)),
    # --- os dois que o especialista de torneio apontou como os de maior
    #     sinal por amostra no campo de clube brasileiro ---
    Codigo("bb_subdefesa", "folda demais o big blind contra open barato",
           "No BB, com o pote te dando preço, quais mãos pagam o open?",
           35.0, "exato", prereq=("pot_odds",)),
    Codigo("limp_de_abertura", "entra limpando em vez de abrir",
           "Se a mão vale entrar, ela vale abrir. Se não vale abrir, vale "
           "entrar?", 5.0, "estimado"),
)}

# 'limp_de_abertura' tem tolerância de 5% porque a referência de equilíbrio é
# ZERO (fora do SB). Isso o torna o detector mais barato em amostra de toda a
# lista: 4 limps em 150 mãos já é diagnóstico, enquanto uma taxa cuja
# referência é 25% precisa de centenas de mãos para se separar do ruído.


# ------------------------------------------------------------- detectores --
_DETECTORES: list[Callable[[CanonicalHand, dict], Iterable[Observacao]]] = []


def detector(fn):
    _DETECTORES.append(fn)
    return fn


def _acao_pre_do_heroi(h: CanonicalHand):
    """A PRIMEIRA ação voluntária do herói no pré (POST não conta)."""
    pre = h.street(StreetName.PREFLOP)
    if not pre:
        return None
    for a in pre.actions:
        if a.actor == h.hero and a.type != ActionType.POST:
            return a
    return None


def _investido_no_pre(h: CanonicalHand, quem: str) -> float:
    pre = h.street(StreetName.PREFLOP)
    if not pre:
        return 0.0
    total = 0.0
    for a in pre.actions:
        if a.actor != quem:
            continue
        if a.to_amount is not None:
            total = max(total, float(a.to_amount))
        elif a.amount:
            total += float(a.amount)
    return total


@detector
def _limp_de_abertura(h: CanonicalHand, ctx: dict) -> Iterable[Observacao]:
    """Pote não aberto e o herói só PAGA a big blind.

    Fora do SB o equilíbrio abre ou larga — nunca limpa. É o leak número 1
    de clube e o detector de melhor razão sinal/amostra que existe aqui,
    justamente porque a referência é zero.
    """
    pos = ctx["pos"]
    if ctx["raises_antes"] != 0 or pos in ("BB", "SB", "?"):
        return
    acao = _acao_pre_do_heroi(h)
    if acao is None:
        return
    limpou = acao.type == ActionType.CALL
    yield Observacao("limp_de_abertura", limpou,
                     0.4 if limpou else 0.0, h.hand_id, "preflop",
                     ctx["stack_bb"])


@lru_cache(maxsize=512)
def _equity_bb_contra_open(classe: str, opener: str) -> float | None:
    """Equity crua da CLASSE de mão contra o range de abertura, memoizada.

    A equity não depende dos naipes concretos, só da classe (AKs vs AKo). Sem
    cache, 8000 iterações de Monte Carlo rodam de novo a cada mão: medido em
    0,31s por spot, o que num envio de 300 mãos com 40 spots de BB são 12
    segundos de espera para recalcular a mesma coisa.

    A chave inclui o `opener` porque o range de quem abriu muda a conta.

    E a ESTABILIDADE vem daqui, não do número de iterações. Antes a equity
    era calculada sobre as cartas concretas: `3d2c` e `3h2d` são a mesma mão
    (32o) e produziam equities diferentes por ruído de Monte Carlo, a ponto
    de receberem vereditos OPOSTOS — 0,00015 de diferença contra um limiar.
    Reduzir à classe torna o veredito determinístico por construção; as
    iterações passam a comprar só exatidão.
    """
    from app.analysis.ranges import OPEN_RANGES, equity_vs_range

    naipes = ["h", "h"] if classe.endswith("s") else ["h", "d"]
    if classe[0] == classe[1]:
        naipes = ["h", "d"]
    cartas = [classe[0] + naipes[0], classe[1] + naipes[1]]
    rng = OPEN_RANGES.get(opener) or OPEN_RANGES.get("CO")
    try:
        r = equity_vs_range(cartas, rng, [], iterations=4000, seed=7)
    except Exception:
        return None
    return float(r["equity"]) if isinstance(r, dict) else float(r)


def _classe_da_mao(cartas: list[str]) -> str | None:
    """'AhKh' -> 'AKs'; 'AhKd' -> 'AKo'; 'AhAd' -> 'AA'."""
    if len(cartas) != 2:
        return None
    ordem = "23456789TJQKA"
    r1, r2 = str(cartas[0])[0].upper(), str(cartas[1])[0].upper()
    if r1 not in ordem or r2 not in ordem:
        return None
    if ordem.index(r1) < ordem.index(r2):
        r1, r2 = r2, r1
        cartas = [cartas[1], cartas[0]]
    if r1 == r2:
        return r1 + r2
    suited = str(cartas[0])[1:].lower() == str(cartas[1])[1:].lower()
    return f"{r1}{r2}{'s' if suited else 'o'}"


def _realizacao_bb(cartas: list[str]) -> float:
    """Quanto da equity crua o BB efetivamente realiza, fora de posição.

    Equity all-in é o que a mão valeria se as cinco cartas viessem de graça.
    Não vêm: o BB age primeiro em todas as ruas seguintes, com range limitado
    (quem tinha mão muito forte teria 3-betado), contra quem tomou a
    iniciativa e pode apostar. O fator de realização é a diferença entre o
    que a mão VALE e o que ela GANHA.

    A forma da mão manda mais que a força crua, e é por isso que não dá para
    usar um número único:
      - PAR joga sozinho: acerta trinca ou desiste, decisão fácil pós-flop
      - SUITED tem flush draw, que é o draw que paga barrado e joga bem OOP
      - CONECTADA acerta straight e straight draw, que dão iniciativa
      - OFFSUIT com gap grande só acerta par fraco, e par fraco OOP é a mão
        mais cara de jogar que existe

    Faixa 0,65-0,95 — compatível com o que solvers publicam para BB vs open
    único (~0,75-0,85 no miolo do range).
    """
    if len(cartas) != 2:
        return 0.80
    ordem = "23456789TJQKA"
    r1, r2 = str(cartas[0])[0].upper(), str(cartas[1])[0].upper()
    n1, n2 = str(cartas[0])[1:].lower(), str(cartas[1])[1:].lower()
    if r1 not in ordem or r2 not in ordem:
        return 0.80
    par = r1 == r2
    suited = bool(n1) and n1 == n2
    gap = abs(ordem.index(r1) - ordem.index(r2))

    fator = 0.78
    if par:
        fator += 0.10
    if suited:
        fator += 0.07
    if not par and gap <= 1:
        fator += 0.03
    if not par and not suited and gap >= 4:
        fator -= 0.05
    return max(0.65, min(0.95, fator))


@detector
def _bb_subdefesa(h: CanonicalHand, ctx: dict) -> Iterable[Observacao]:
    """BB fechando a ação contra UM open, com preço, e largando.

    Custo EXATO: (equity_necessária − equity_da_mão) × pote, quando a mão
    tinha equity de sobra contra o range de abertura de quem abriu. Só conta
    como escorregada quando a conta prova; mão sem equity larga mesmo.
    """
    if ctx["pos"] != "BB" or ctx["raises_antes"] != 1:
        return
    acao = _acao_pre_do_heroi(h)
    if acao is None or not h.hero_cards or len(h.hero_cards) != 2:
        return
    bb = float(h.stakes.big_blind or 0) or 1.0
    # o que ele tinha para pagar ANTES de agir. Descontar o `_investido_no_pre`
    # cheio zerava o to_call justamente quando ele PAGOU — o acerto sumia do
    # denominador e o detector só enxergava fold, o que inflaria a taxa.
    to_call = max(0.0, ctx["maior_apostado"] - ctx["investido_heroi"])
    if to_call <= 0:
        return
    # o spot é BB contra open PADRÃO. Contra 6bb a conta é outra e largar
    # vira normal; medir os dois com o mesmo nome é somar coisas diferentes.
    if ctx["maior_apostado"] / bb > 3.0:
        return
    pote = ctx["pote_pre"]
    preco = to_call / max(pote + to_call, 1e-9)
    classe = _classe_da_mao(list(h.hero_cards))
    if not classe:
        return
    eq = _equity_bb_contra_open(classe, ctx["opener"] or "CO")
    if eq is None:
        return
    # EQUITY CRUA NÃO É O QUE ELE GANHA. Comparar equity all-in com pot odds
    # assume que o BB realiza 100% dela — e ele está FORA DE POSIÇÃO, com
    # range limitado, contra quem tomou a iniciativa. Sem este fator o
    # detector acusava fold em 148 das 169 classes de mão (87,6%): ele não
    # media subdefesa, media FOLD.
    eq = eq * _realizacao_bb(list(h.hero_cards))
    folgado = eq - preco
    foldou = acao.type == ActionType.FOLD
    # MARGEM DE MODELO, não de ruído — o ruído já foi resolvido reduzindo à
    # classe. `_realizacao_bb` é uma heurística por forma de mão, com uns
    # ±5pp de erro; acusar dentro dessa faixa seria acusar o modelo, não o
    # aluno. Medido nas 169 classes: 2pp acusa 49,7% · 4pp 36,1% · 6pp 27,8%
    # · 8pp 23,7%. A referência de defesa do BB é 45-55%, então 2pp
    # reproduz a referência — e é justamente onde a heurística é mais fraca,
    # porque as mãos marginais são as que dependem de realização.
    escorregou = bool(foldou and folgado > 0.06)
    yield Observacao("bb_subdefesa", escorregou,
                     round(folgado * (pote + to_call) / bb, 2)
                     if escorregou else 0.0,
                     h.hand_id, "preflop", ctx["stack_bb"])


@detector
def _open_perdido(h: CanonicalHand, ctx: dict) -> Iterable[Observacao]:
    """Pote não aberto e o herói larga mão que o range da posição abre."""
    if ctx["raises_antes"] != 0 or ctx["pos"] in ("BB", "?"):
        return
    from app.analysis.handreport import hand_class
    from app.analysis.ranges import OPEN_RANGES, parse_range

    hc = hand_class(h.hero_cards)
    rng = OPEN_RANGES.get(ctx["pos"])
    if not hc or not rng:
        return
    acao = _acao_pre_do_heroi(h)
    foldou = acao is not None and acao.type == ActionType.FOLD
    escorregou = bool(foldou and hc in parse_range(rng))
    yield Observacao("open_perdido", escorregou, 0.3 if escorregou else 0.0,
                     h.hand_id, "preflop", ctx["stack_bb"])


@detector
def _shove_curto(h: CanonicalHand, ctx: dict) -> Iterable[Observacao]:
    """Stack curto: empurrou o que não devia, ou largou o que empurrava."""
    from app.analysis.pushfold import push_fold

    stack = ctx["stack_bb"]
    if not stack or not h.hero_cards or len(h.hero_cards) != 2:
        return
    acao = _acao_pre_do_heroi(h)
    if acao is None:
        return
    jammed = bool(acao.all_in and acao.type in
                  (ActionType.RAISE, ActionType.BET, ActionType.CALL))

    if ctx["raises_antes"] == 0 and stack <= 12 and ctx["pos"] != "BB":
        pf = push_fold(list(h.hero_cards), stack, ctx["pos"])
        if pf.get("applicable"):
            perdeu = bool(acao.type == ActionType.FOLD
                          and pf["decision"] == "push")
            folga = max(0.0, (pf.get("shove_range_pct", 0)
                              - pf.get("hand_top_pct", 0))
                        / max(pf.get("shove_range_pct", 1), 1.0))
            yield Observacao("shove_perdido", perdeu,
                             round(0.3 + 1.2 * folga, 2) if perdeu else 0.0,
                             h.hand_id, "preflop", stack)

    if jammed and stack <= 20:
        pf = push_fold(list(h.hero_cards), stack, ctx["pos"])
        if pf.get("applicable"):
            largo = pf["decision"] == "fold"
            yield Observacao("shove_largo", largo, 1.0 if largo else 0.0,
                             h.hand_id, "preflop", stack)


@detector
def _call_caro(h: CanonicalHand, ctx: dict) -> Iterable[Observacao]:
    """Pagou pedindo mais equity do que a mão tem. Custo EXATO: o déficit
    de equity vezes o que estava em jogo.

    SÓ CALL. Raise e bet não são "pagar", e o preço de `equity_minima` é o de
    pagar — aplicá-lo a um raise é erro de categoria. Medido em 09/08: numa
    amostra de 24 mãos com 12 raises, as 24 apareciam como call caro, e a
    direção do erro no /torneio saía "solto demais" por causa disso.

    O FOLD entra como oportunidade (escorregada=False): sem ele a taxa vira
    P(erro | pagou), que é ~100% por construção.
    """
    from app.analysis.handreport import played_facts

    for n in (played_facts(h).get("numbers") or []):
        if "equity_minima" not in n:
            continue
        acao = (n.get("acao") or "").lower()
        if acao not in ("call", "fold"):
            continue
        if acao == "fold":
            yield Observacao("call_caro", False, 0.0, h.hand_id,
                             n.get("street") or "?", ctx["stack_bb"])
            continue
        if n.get("equity_vs_aleatoria") is None:
            continue
        deficit = n["equity_minima"] - n["equity_vs_aleatoria"]
        caro = deficit > 0.05
        yield Observacao(
            "call_caro", caro,
            round(deficit * (n["pote_bb"] + n["pagou_bb"]), 2) if caro else 0.0,
            h.hand_id, n.get("street") or "?", ctx["stack_bb"])


def _contexto(h: CanonicalHand) -> dict | None:
    """O que todo detector precisa saber, calculado UMA vez por mão."""
    from app.analysis.handreport import _facing_preflop

    if not h.hero or not h.stakes.big_blind:
        return None
    bb = float(h.stakes.big_blind)
    seat = h.hero_seat()
    raises, opener = _facing_preflop(h)
    pre = h.street(StreetName.PREFLOP)
    maior = 0.0
    pote = 0.0
    investido_heroi = 0.0
    if pre:
        for a in pre.actions:
            if a.actor == h.hero and a.type != ActionType.POST:
                break
            v = float(a.to_amount or a.amount or 0)
            if a.to_amount is not None:
                maior = max(maior, v)
            elif a.type == ActionType.POST:
                maior = max(maior, v)     # a big blind também é "para pagar"
            pote += float(a.amount or 0)
            if a.actor == h.hero:
                investido_heroi = max(investido_heroi, v)
    return {
        "pos": (seat.position if seat else None) or "?",
        "stack_bb": round(float(seat.stack) / bb, 1) if seat and seat.stack
        else 0.0,
        "raises_antes": raises,
        "opener": opener or "CO",
        "maior_apostado": maior,
        "investido_heroi": investido_heroi,
        "pote_pre": pote,
        "bb": bb,
    }


def observar(hands: list[CanonicalHand]) -> list[Observacao]:
    """Roda todos os detectores. Uma mão que quebra um detector não derruba
    os outros — e o silêncio dela aparece no `n`, não num erro."""
    out: list[Observacao] = []
    for h in hands:
        try:
            ctx = _contexto(h)
        except Exception:
            ctx = None
        if not ctx:
            continue
        for det in _DETECTORES:
            try:
                out.extend(det(h, ctx))
            except Exception:
                continue
    return out


def agregar(obs: list[Observacao], n_maos: int) -> list[dict]:
    """Observações -> diagnóstico, com shrinkage e decisão pelo limite BAIXO.

    Decidir pela MÉDIA é o que transforma 2 escorregadas em 3 chances num
    "leak crônico". O limite inferior do intervalo é o número que sobrevive
    a alguém perguntando "tem certeza?".
    """
    from app.analysis.bayes import shrunk_rate

    por_codigo: dict[str, dict] = {}
    for o in obs:
        c = por_codigo.setdefault(o.codigo, {"opp": 0, "miss": 0, "custo": 0.0,
                                             "exemplos": []})
        c["opp"] += 1
        if o.escorregada:
            c["miss"] += 1
            c["custo"] += o.custo_bb
            if len(c["exemplos"]) < 3:
                c["exemplos"].append(o.hand_id)

    saida = []
    for codigo, c in por_codigo.items():
        cfg = CODIGOS[codigo]
        mean, lo, hi = shrunk_rate(c["miss"], c["opp"], 20.0, 6.0)
        saida.append({
            "codigo": codigo,
            "nome": cfg.nome,
            "pergunta": cfg.pergunta,
            "oportunidades": c["opp"],
            "escorregadas": c["miss"],
            "taxa_lo": lo, "taxa_mean": mean, "taxa_hi": hi,
            "tolerancia_pct": cfg.tolerancia_pct,
            # a decisão é pelo limite INFERIOR: só é problema quando o pior
            # cenário do intervalo ainda está acima da tolerância
            "acima_da_tolerancia": lo > cfg.tolerancia_pct,
            "custo_bb_100": round(100.0 * c["custo"] / max(n_maos, 1), 2),
            "custo_e_estimado": cfg.custo == "estimado",
            "exemplos": c["exemplos"],
            "prereq": list(cfg.prereq),
        })
    saida.sort(key=lambda x: -x["custo_bb_100"])
    return saida
