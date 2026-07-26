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

## Canários por REGRA, não por lista (2026-07-26)
Lista fixa é whitelist: não pega o arquivo novo. Os canários varrem o
diretório e falham sozinhos:
- `messages.create` fora de `llm._create` → custo invisível ([[Custo de LLM]])
- teto de análises escrito na mão no texto do `/plano` → com mais de um
  teto, número fixo é mentira para metade dos alunos
- ligação do parser: `replay_link_info` → `ingest` → handler. **Motor certo
  que ninguém chama não entrega nada** — foi o defeito do gráfico de EV,
  que existia e nunca era invocado

## Teste não pode ter efeito colateral
Dois incidentes no mesmo dia, ambos com teste de regressão:
- teste de integração gravou seus fixtures em `/tmp/replay_sniff` do VPS
  durante o gate de deploy. O admin abriu a pasta esperando a captura real
  da Suprema e encontrou 57 bytes de fixture. **Plantar dado falso onde se
  procura dado real custa mais que não gravar nada.** O caminho de despejo
  virou argumento, e `None` (padrão) não grava
- outro teste saiu batendo em domínio inexistente DE VERDADE (12s de DNS
  timeout no gate). A camada de rede virou seam substituível

## O que a suite NÃO pega
Balanço da semana de 2026-07-26: 12 defeitos encontrados — 6 pelo dono
usando o produto, 5 por mim ao validar, 1 pelo juiz da saída, **0 pelos 261
testes de então**. Daí a [[Guarda da Saída]] e a sonda de jornadas: teste
verde e resposta útil são coisas diferentes.

Suite hoje: **339 testes**, ainda o gate de deploy.
