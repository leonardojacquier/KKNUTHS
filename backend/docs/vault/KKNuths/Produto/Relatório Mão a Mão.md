---
tags: [kknuths, produto]
---
# Relatório Mão a Mão

HTML anexado automaticamente em todo upload de torneio (8+ mãos) — flag
`REPORT_AUTO=0` muda p/ sob demanda via /relatorio (alavanca de plano futuro).

## Anatomia (cada mão jogada vira um card)
1. Sequência + cartas + posição
2. Identificação: Nº da mão NA SALA (PokerCraft/HM), hora, blinds, stack e
   **stack efetivo**
3. **Selo de decisão** ✅/❌/⚠️ — vem do MESMO veredito do coach que assina o
   texto (nunca diverge da análise)
4. Resultado em BB (separado do selo — anti-resulting)
5. História lance a lance (sizings em BB e % do pote)
6. Análise do coach (LLM em lotes de 6, só com números calculados; fallback
   determinístico se LLM off)
7. 🎈 Versão mais simples embutida (toggle; gerada na MESMA chamada — entrada
   paga 1×, custo extra ≈ centavos)
8. Folds pré-flop em tabela com veredito por range ("dava para abrir…")

O quadro do torneio vai embutido no topo. Usuário pode citar o Nº de qualquer
mão no chat → coach abre via tool `get_hand` (ver [[Conversa com o Coach]]).
