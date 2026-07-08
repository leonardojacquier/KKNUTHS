---
tags: [kknuths, operacao]
---
# Portal Admin e Métricas

`/admin` no poker-web (vorte369.com.br quando o DNS/Caddy apontarem):
- Usuários com interações / uploads / análises / erros por pessoa
- Barras diárias de atividade; seção de erros
- Fonte: `bot_events` — inclui followup (logado ANTES do LLM p/ nunca perder
  rastro), followup_failed, simplify, relatorio, drill, deploy…

## Leituras úteis
- Mix followup-dominante = usuários conversando = saudável
- `simplify` concentrado num tema = a linguagem padrão está perdendo gente ali
- Erros repetidos = abrir investigação (todo erro de produção vira teste)
