---
tags: [kknuths, operacao, decisoes]
---
# Histórico de Decisões (resumo)

- **Stacks nunca estimados** — bug "12bb vs 58bb" (era o valor do BB); análise
  passa stacks + stack efetivo; regra dura no prompt; teste de regressão
- **Motor KKN sempre ligado e invisível** — qualidade não é opção; flags só
  p/ rollout; profundidade sob demanda no chat
- **Selo de decisão = veredito do coach** — selo determinístico divergia do
  texto ("decisão ✅" + "jogou passivo demais"); fonte única
- **Relatório automático no upload** — era só script manual; virou default
  (REPORT_AUTO como alavanca de plano)
- **Voz do coach** — informal, veredito primeiro; proibido papo de sistema e
  "resumo brutal"; simplificação como botão
- **Nobel factual** — "baseado na ciência que ganhou…"; 2 Nobels (Kahneman
  2002, Nash 1994), ambos genuinamente usados
- **Suite hermética** — testes offline em qualquer ordem (gate queimava
  tokens reais)
- **Jam/fold transposto** — matriz Nash invertida corrigida e validada contra
  tabela de referência
- **Quota fail-closed** + upsert de mãos por chave natural (reenvio não duplica)
