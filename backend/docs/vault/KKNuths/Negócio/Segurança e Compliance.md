---
tags: [kknuths, negocio, seguranca]
---
# Segurança e Compliance

## Poker (ToS das salas)
- NUNCA conectar na conta do usuário; NUNCA tempo real (RTA) — só análise
  pós-sessão sobre arquivos que a própria sala exporta (mesma categoria dos
  trackers). Dito explicitamente no FAQ do manual e no folder

## Segredos
- `.env` fora do git (push protection ativa no GitHub); segredos NUNCA em
  commit/chat (a UI mascara cópia — transferir por arquivo/scp)
- ⚠️ PENDENTE pós-beta: **rotacionar todas as chaves** que circularam no
  início (Anthropic, OpenAI, token do BotFather, service key do Supabase)
- Deixar o repositório privado

## Dados de usuário
- Mãos/relatórios de usuários nunca vão para o repositório
- Individual nunca compartilhado; agregado anônimo calibra o motor
- RLS no banco; quota fail-closed (indisponibilidade não libera uso infinito)
