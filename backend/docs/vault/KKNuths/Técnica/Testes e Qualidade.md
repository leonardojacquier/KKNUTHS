---
tags: [kknuths, tecnica]
---
# Testes e Qualidade

- Suite pytest (~167 testes) é o **gate de deploy** no VPS
- `tests/conftest.py`: isolamento GLOBAL — todo teste nasce offline (env
  limpo + caches de settings/repository resetados). Antes disso a suite
  dependia da ORDEM dos módulos e chegou a queimar tokens reais no gate
- Padrão: todo bug de produção vira teste de regressão (ex.: `def
  stats_report` engolido por edição; relatório ausente no upload; matriz
  Nash transposta; "3-bet 100%")
- Testes direcionais para modelos (tilt dispara no chase sintético e fica
  calado no jogador estável; range tracker sobe valor com bomba grande)
- Gerador de torneio demo (`scripts/gen_demo_tournament.py`): 150 mãos
  determinísticas por seed, pote contábil, showdowns — smoke de ponta a ponta
