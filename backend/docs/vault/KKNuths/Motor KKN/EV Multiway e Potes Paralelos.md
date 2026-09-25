---
tags: [kknuths, motor]
atualizado: 2026-07-26
---
# EV Multiway e Potes Paralelos

Pergunta do aluno que originou tudo: *"você não calcula o EV em pote
multiway?"* e depois *"só funciona com all-in? Se a mão for até showdown
sem all-in, dá pra calcular o EV de cada street sendo multiway?"*.

## Equity multiway (`app/analysis/multiway_equity.py`)
Monte Carlo real contra N ranges. A aproximação por independência
(multiplicar equities heads-up) foi **medida e rejeitada**: errava até 14
pontos (QJs dava 17% quando o valor real é 29%).

Defeito corrigido e validado: o board era sorteado de um baralho que ainda
continha as cartas do herói, o que inflava a equity em **3 a 6 pontos**.
Agora o herói tira as cartas ANTES do board — viés medido 0,003, máximo
0,009.

- `equity_vs_campo` delega para o cálculo EXATO quando não há ranges
- `ranges` aceita notação ou lista de combos concretos
- `range_que_continua` devolvia combos e `equity_vs_campo` os lia como
  notação → `ValueError` morria num `except` silencioso e caía na equity
  errada. O `except` foi REMOVIDO: quando a equity não dá para calcular, a
  opção simplesmente não é oferecida

## Potes paralelos (`app/analysis/side_pots.py`)
`dividir_potes(investido, fora, extra)` → um pote por camada de all-in;
`extra` (mortos/ante) vai para o pote **principal**.

Validado: contribuições 10/25/40 → potes **[30, 30, 15]**. Herói curto com
par de ases ganha **+20bb líquidos, não +50bb** — só disputa o que cobriu.

Pote com um único elegível = aposta devolvida, não vitória.

## EV street a street, multiway, sem all-in
`app/analysis/ev_streets.py`. Modelo declarado na docstring (régua única
para todas as opções):

| opção | EV |
|---|---|
| CALL | exato |
| APOSTA | `p_fold × pote + (1−p_fold) × [eq_call × (pote + 2×aposta) − aposta]` |
| CHECK | `equity × pote` |
| FOLD | 0 |
| CUSTO DO ERRO | melhor − escolhida |

Dois artefatos corrigidos:
- **"aposte sempre"** — a fold equity era creditada de graça E a equity
  usada era contra o range INTEIRO. Corrigido com condicionamento no range
  que continua + probabilidade de fold **por adversário** (quem já pagou
  nunca foge)
- **base inconsistente** — check valia 0 e bet valia +4bb na mesma régua

## Overcall multiway
Defeito: `pagaram > 0` gerava range de call de 100% e **72o com +3,42bb**.
As fichas de quem pagou entravam como dinheiro morto sem que eles fossem
adversários vivos. Corrigido → range 23,7% e 72o **−5,42bb**.

## Limite atual
A matriz 13×13 e o solver CFR+ são **heads-up**. Em pote multiway o bot
avisa isso e entrega a conta que vale (EV por street + potes paralelos) em
vez do gráfico — nunca uma matriz que não descreve o spot.

MDF multiway: cada defensor defende `1 − α^(1/N)`, de modo que
`P(todos foldam) = α`.

Relacionado: [[Motor KKN]] · [[Guarda da Saída]] ·
[[Ingestão de Replays de Clube]]
