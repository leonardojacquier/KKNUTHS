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
- **Veredito não se sorteia** — 99 recebeu "3-bet" e "call" em runs
  diferentes (temperature 1.0 + sem âncora); temperature 0.2/0.0 via
  wrapper `_create` + veredito preflop preso ao `preflop_range` +
  coerência entre mensagens ([[Coerência Gráfico-Análise]])
- **Número do aluno é insumo** — narração na legenda alimenta as tools;
  dado faltante vira pergunta, nunca "não dá pra calcular"
- **Print ilegível + narração = analisa pela narração** — fallback
  extract_from_hand_text(caption); "não li" só sem fonte nenhuma
- **hand_id por fingerprint** — todo print era 'vision-snapshot' e o
  upsert fazia cada foto SOBRESCREVER a anterior; sha1[:12] do conteúdo
  (reenvio deduplica, foto nova ganha linha)
- **Gráfico = mesmo número do veredito** — auditoria de 11 incoerências
  gráfico↔texto; invariantes em [[Coerência Gráfico-Análise]]
- **Glossário central (TERMOS_REGRA)** — calques banidos (par grande,
  rua/etapa p/ street…) nas 3 camadas de texto; registro sempre 'você'
