"""EQUITY MULTIWAY — a chance de bater TODOS, não um de cada vez.

Motivo (pergunta do aluno: "você não calcula o EV em pote multiway?"): o
motor de all-in tratava as fichas de quem JÁ pagou como dinheiro morto, sem
tratar essas pessoas como adversárias vivas. O herói recebia o stack delas
no cálculo e só precisava ganhar do primeiro. Resultado: "overcall com 100%
das mãos" e 72o aparecendo +3,4bb. Conselho que perde dinheiro.

O atalho óbvio — multiplicar as equities heads-up (independência) — foi
MEDIDO e reprovado: erra até 14 pontos nas mãos fracas (QJs: 17% pelo
produto contra 29% de verdade). Então aqui é Monte Carlo de verdade.

Truque que faz caber no tempo: os cenários (mãos dos vilões + board) são
sorteados UMA vez e as 169 mãos do herói são avaliadas contra os MESMOS
cenários. Além de rápido (um sorteio, 169 avaliações), isso é redução de
variância por números aleatórios comuns: o ruído é comum a todas as mãos,
então a ORDEM entre elas — que é o que decide a fronteira pagar/foldar —
fica muito mais estável do que o erro individual sugere.
"""
from __future__ import annotations

import random

import numpy as np

_RANKS = "23456789TJQKA"


def _combos_da_mao(mao: str) -> list[tuple[str, str]]:
    """Combos concretos de uma mão canônica ('AKs', 'TT', 'A5o')."""
    from app.analysis.ranges import expand_combos

    return expand_combos([mao])


def _sortear_do_range(hands: list[str], pesos: np.ndarray,
                      rng: random.Random, usadas: set[str]) -> tuple | None:
    """Um combo do range (proporcional ao peso da estratégia), sem repetir
    carta já usada na mesa. None se não achar em algumas tentativas."""
    total = float(pesos.sum())
    if total <= 0:
        return None
    for _ in range(40):
        alvo = rng.random() * total
        acc = 0.0
        idx = 0
        for i, p in enumerate(pesos):
            acc += float(p)
            if acc >= alvo:
                idx = i
                break
        combos = _combos_da_mao(hands[idx])
        rng.shuffle(combos)
        for c in combos:
            if c[0] not in usadas and c[1] not in usadas:
                return c
    return None


def equity_table(hands: list[str], ranges: list[np.ndarray],
                 board: list[str] | None = None,
                 iters: int = 3000, seed: int = 7) -> np.ndarray:
    """Equity de CADA mão canônica do herói contra N vilões simultâneos.

    `ranges`: um vetor de pesos (sobre as mesmas 169 mãos) por vilão — o
    range com que ele entrou. Empate divide o pote (conta a fração).
    Devolve array alinhado a `hands`; NaN vira 0 (mão sem cenário válido).
    """
    from treys import Card, Evaluator

    board = list(board or [])
    ev = Evaluator()
    rng = random.Random(seed)
    baralho = [r + s for r in _RANKS for s in "cdhs"]
    # Card.new faz parsing de string: converter as 52 cartas uma vez corta a
    # maior parte do custo (o laço interno roda 169 vezes por cenário)
    CN = {c: Card.new(c) for c in baralho}

    combos_por_mao = [_combos_da_mao(h) for h in hands]
    soma = np.zeros(len(hands))
    validos = np.zeros(len(hands))

    for _ in range(iters):
        usadas = set(board)
        vilaos = []
        for pesos in ranges:
            c = _sortear_do_range(hands, pesos, rng, usadas)
            if c is None:
                break
            usadas.update(c)
            vilaos.append(c)
        if len(vilaos) != len(ranges):
            continue
        resto = [c for c in baralho if c not in usadas]
        rng.shuffle(resto)
        faltam = 5 - len(board)
        # o board "padrão" (sem tirar as cartas do herói) serve para a maioria
        # das mãos: só quando o herói segura uma das cartas sorteadas é que a
        # mesa precisa ser remontada. Isso corta ~80% das avaliações dos vilões
        # sem mudar o resultado (cada mão continua vendo um board legal).
        padrao = resto[:faltam]
        set_padrao = set(padrao)
        mesa_pad = [CN[c] for c in board] + [CN[c] for c in padrao]
        notas_pad = [ev.evaluate(mesa_pad, [CN[a], CN[b]]) for a, b in vilaos]
        melhor_pad = min(notas_pad)
        emp_pad = sum(1 for x in notas_pad if x == melhor_pad)
        for i, combos in enumerate(combos_por_mao):
            # ORDEM IMPORTA: o herói pega as cartas dele ANTES do board.
            # Sortear o board de um baralho que ainda continha as cartas do
            # herói inflava a equity em 3 a 6 pontos — viés sistemático,
            # flagrado comparando com o Monte Carlo independente.
            vivos = [c for c in combos
                     if c[0] not in usadas and c[1] not in usadas]
            if not vivos:
                continue
            h1, h2 = vivos[rng.randrange(len(vivos))]
            if h1 in set_padrao or h2 in set_padrao:
                novas = []
                for c in resto:                   # board sem as cartas do herói
                    if c != h1 and c != h2:
                        novas.append(c)
                        if len(novas) == faltam:
                            break
                if len(novas) < faltam:
                    continue
                mesa_c = [CN[c] for c in board] + [CN[c] for c in novas]
                notas_vil = [ev.evaluate(mesa_c, [CN[a], CN[b]])
                             for a, b in vilaos]
                melhor_vil = min(notas_vil)
                empates = sum(1 for x in notas_vil if x == melhor_vil)
            else:
                mesa_c, melhor_vil, empates = mesa_pad, melhor_pad, emp_pad
            nota = ev.evaluate(mesa_c, [CN[h1], CN[h2]])
            if nota < melhor_vil:
                soma[i] += 1.0
            elif nota == melhor_vil:
                soma[i] += 1.0 / (1 + empates)
            validos[i] += 1

    return np.where(validos > 0, soma / np.maximum(validos, 1), 0.0)


def equity_vs_campo(hero_cards: list[str],
                    conhecidas: list[list[str]],
                    ranges: list,
                    board: list[str] | None = None,
                    iters: int = 6000, seed: int = 13) -> float | None:
    """Equity de UMA mão contra um campo MISTO: alguns vilões com cartas
    conhecidas (showdown) e outros só com range.

    É o caso da mão normal que vai a showdown sem all-in: no flop havia três
    jogadores, mas um foldou no turn e nunca mostrou. Calcular a equity só
    contra quem mostrou trata o pote de 3 como heads-up — e infla a equity
    do herói exatamente como o erro do overcall.
    """
    from treys import Card, Evaluator

    from app.analysis.ranges import expand_combos, parse_range

    hero_cards = [c for c in (hero_cards or []) if c]
    if len(hero_cards) != 2:
        return None
    board = list(board or [])
    mortas0 = set(hero_cards) | set(board)
    for cs in conhecidas:
        mortas0.update(cs)

    if not ranges:
        # campo todo conhecido: enumeração EXATA é barata pós-flop e não tem
        # ruído nenhum — simular seria trocar resposta certa por aproximada
        from app.analysis.equity import equity_vs_hands

        return equity_vs_hands(hero_cards, list(conhecidas), board)

    combos_range = []
    for r in ranges:
        # aceita notação ("TT+, AQs") OU lista de combos concretos — é o que
        # range_que_continua devolve, e passar combo como notação levantava
        # ValueError que morria num except mudo lá em cima
        if isinstance(r, str):
            combos = expand_combos(parse_range(r), mortas0)
        else:
            combos = [tuple(c) for c in r
                      if c[0] not in mortas0 and c[1] not in mortas0]
        if not combos:
            return None
        combos_range.append(combos)

    ev = Evaluator()
    rng = random.Random(seed)
    baralho = [r + s for r in _RANKS for s in "cdhs"]
    CN = {c: Card.new(c) for c in baralho}
    hero_c = [CN[c] for c in hero_cards]
    faltam = 5 - len(board)

    soma = 0.0
    validos = 0
    for _ in range(iters):
        usadas = set(mortas0)
        vilaos = [list(cs) for cs in conhecidas]
        ok = True
        for combos in combos_range:
            for _t in range(30):
                c = combos[rng.randrange(len(combos))]
                if c[0] not in usadas and c[1] not in usadas:
                    usadas.update(c)
                    vilaos.append(list(c))
                    break
            else:
                ok = False
                break
        if not ok:
            continue
        resto = [c for c in baralho if c not in usadas]
        rng.shuffle(resto)
        mesa = [CN[c] for c in board] + [CN[c] for c in resto[:faltam]]
        nota_h = ev.evaluate(mesa, hero_c)
        notas = [ev.evaluate(mesa, [CN[a], CN[b]]) for a, b in vilaos]
        melhor = min(notas)
        if nota_h < melhor:
            soma += 1.0
        elif nota_h == melhor:
            soma += 1.0 / (1 + sum(1 for x in notas if x == melhor))
        validos += 1
    return soma / validos if validos else None


def range_que_continua(notacao: str, board: list[str], mortas: set[str],
                       fracao: float) -> list[tuple[str, str]] | None:
    """A parte do range que SEGUE na mão contra uma aposta: as `fracao` mãos
    mais fortes naquele board (ordenadas pela mão feita).

    Sem isto, o EV de apostar usa a equity contra o range INTEIRO do vilão —
    e como o modelo dá crédito de fold equity, apostar aparecia melhor que
    dar check em toda mão com equity > 0 ("sempre aposte", conselho ruim).
    Quem paga não é o range todo: é a parte que bate em você.

    Aproximação declarada: ordena pela FORÇA ATUAL no board. Projeto (draw)
    fica subestimado — quem paga com draw entra abaixo do corte.
    """
    from treys import Card, Evaluator

    from app.analysis.ranges import expand_combos, parse_range

    combos = expand_combos(parse_range(notacao), set(mortas))
    if not combos or len(board) < 3:
        return None
    fracao = max(0.02, min(1.0, float(fracao)))
    ev = Evaluator()
    mesa = [Card.new(c) for c in board]
    notas = sorted(combos,
                   key=lambda c: ev.evaluate(mesa, [Card.new(c[0]),
                                                    Card.new(c[1])]))
    corte = max(1, int(round(len(notas) * fracao)))
    return notas[:corte]


def continua_com(cartas: list[str], notacao: str, board: list[str],
                 mortas: set[str], fracao: float) -> bool | None:
    """Uma mão CONHECIDA segue na mão contra a aposta? Compara a força dela
    no board com o corte de defesa do range de referência.

    Existe porque dar crédito de fold equity contra um vilão cujas cartas a
    gente VIU é inventar dinheiro: quem tem par de ases no board não folda,
    e o modelo estava embolsando o pote como se foldasse.
    """
    from treys import Card, Evaluator

    from app.analysis.ranges import expand_combos, parse_range

    if len(cartas) != 2 or len(board) < 3:
        return None
    combos = expand_combos(parse_range(notacao), set(mortas))
    if not combos:
        return None
    ev = Evaluator()
    mesa = [Card.new(c) for c in board]
    notas = sorted(ev.evaluate(mesa, [Card.new(a), Card.new(b)])
                   for a, b in combos)
    corte = notas[max(0, min(len(notas) - 1,
                             int(round(len(notas) * max(0.02, fracao))) - 1))]
    return ev.evaluate(mesa, [Card.new(cartas[0]), Card.new(cartas[1])]) <= corte
