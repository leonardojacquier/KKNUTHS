---
tags: [kknuths, motor-kkn]
---
# Leitura de Vilão — Range Tracker

O raciocínio do pro, explícito: range do vilão nasce no chart da posição
(open/call/3bet) e cada ação reponderada os combos —
P(combo|ação) ∝ P(ação|combo) × P(combo).

- Buckets por street contra o board: forte / média / draw / ar (avaliador
  determinístico de 7 cartas + detecção de draws; sem Monte Carlo, subsegundo)
- Likelihoods P(ação|tipo) em tabelas EXPLÍCITAS no código (comportamento
  típico de field) — calibráveis por [[Calibração por Showdown]]
- Saída: fatias por street + odds — "cerca de 4 pra 1 que é valor"
- Tool `read_villain`; prompt manda narrar a mudança e comparar com o preço
  do call; sempre sinaliza "estimativa por comportamento típico do field"
- Código: `app/analysis/rangetracker.py`

Guarda-corpo: testes travam o comportamento direcional (bomba grande → valor
sobe; check → valor desce).
