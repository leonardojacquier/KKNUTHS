---
tags: [kknuths, produto]
---
# Visão Geral do Produto

**O que é:** coach de poker com IA dentro do Telegram. O usuário envia mãos em
qualquer formato e recebe análise de nível profissional com matemática de
solver — nunca números estimados.

## Formatos de entrada
- Arquivo `.txt` de hand history: GGPoker (PokerCraft), PokerStars (inclusive
  Zoom), Winamax, PartyPoker, 888poker
- **Texto colado** no chat — se o Telegram cortar em partes, o bot remonta
  sozinho (reassembly com validação de emenda)
- Print/foto da mesa ou replay (visão computacional) — funciona p/ qualquer sala
- CSV de tracker (HM/PT), PDF, áudio (transcrição Whisper)

## O que sai de um upload de torneio
1. Análise do coach (texto, voz informal — ver [[Conversa com o Coach]])
2. Quadro do campeonato (curva de stack + KPIs estilo PokerCraft)
3. [[Relatório Mão a Mão]] em HTML anexado automaticamente
4. Perfil atualizado ([[Estatística Bayesiana - Shrinkage]], [[Leaks em bb-100]],
   [[KKN Tilt Detector]])

## Princípios inegociáveis
- Números **calculados** pelos motores; o LLM só narra (ver [[Motor KKN]])
- **Decisão ≠ resultado** (anti-resulting em todo o produto)
- Nunca conectar na conta da sala; só análise pós-sessão (ver
  [[Segurança e Compliance]])
- Voz de coach: informal, veredito primeiro, 1-2 números explicados; proibido
  jargão de sistema e adjetivar veredito ("resumo brutal")
