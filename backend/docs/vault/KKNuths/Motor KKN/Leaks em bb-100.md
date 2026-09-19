---
tags: [kknuths, motor-kkn]
---
# Leaks em bb/100

Plano de estudo rankeado por DINHEIRO no /stats: *"esse leak te custa ~4bb a
cada 100 mãos"*.

## Detectores (`app/analysis/leaks.py`)
| Leak | Detector | Custo |
|---|---|---|
| open_perdido | folda mão dentro do range em pote não aberto | estimativa 0,3bb |
| shove_perdido | ≤12bb, Nash diz push, foldou | proporcional à folga no range |
| call_caro | déficit de equity >5pts vs preço | **exato**: déficit × pote |
| shove_largo | jam ≤20bb fora do equilíbrio | estimativa 1bb |

- Taxa de escorregada corrigida por shrinkage (prior 20%, força 6) — 1 vacilo
  em 2 chances NÃO vira leak crônico; só acusa com posterior ≥25%
- Lente de custo afundado: call caro concentrado em turn/river (≥60%) →
  diagnóstico vira mental ("as fichas no pote não são mais suas")
- Amostra limitada a 150 mãos no /stats (equity MC por decisão)
