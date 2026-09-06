---
tags: [kknuths, produto]
---
# Conversa com o Coach

Depois de qualquer análise, o usuário conversa em linguagem natural (texto ou
áudio). Contexto sobrevive a restart (recuperação da última análise do banco).

## Ferramentas do coach (tool-use, 18 tools)
- Cálculo: equity MC, pot odds, EV, SPR, breakeven de blefe, equity vs range
- Ranges/solver: preflop_range, push_fold (Nash), solve_river (CFR+), icm,
  bubble_factor, send_range_chart (gera gráfico na conversa)
- Histórico do aluno: `search_hands` (padrões: cbet/fold/allin/…),
  `get_hand` (abre mão específica por Nº da sala ou cartas — "abre o A3o")
- [[Leitura de Vilão - Range Tracker]]: `read_villain` (odds de valor vs blefe)
- Memória: `record_student_note` (caderno do coach: leaks, metas, progresso)
- Estilo: `compare_style_to_pros` (Yuri, Akkari, Dwan, Negreanu…)

## Regras de voz (prompt)
- Papo de mesa informal; veredito primeiro; máx 1-2 números por ponto, sempre
  explicados; jargão traduzido na 1ª vez
- PROIBIDO: mencionar sistema/correções/bastidores; adjetivar veredito
- "Não entendi" → reexplica a MESMA ideia p/ iniciante (analogia, zero jargão)
- Psicologia: anti-resulting, taxa-base contra "sempre perco com X",
  regressão à média pós-downswing, custo afundado

## Consistência (regra dura)
- Mesma mão + posição + ação = MESMO veredito (ancorado no
  `preflop_range`); frequência mista nunca é o conselho
- Followup não vira casaca: sem dado novo, mantém; com dado novo,
  explicita "isso muda o que eu disse porque X"
- Números do aluno (pote/sizing/stack ditos na legenda ou no chat) são
  INSUMOS das tools; faltou dado → pergunta o dado exato
- Gráficos automáticos dos ranges consultados chegam anexados e são
  citados no texto — detalhes em [[Coerência Gráfico-Análise]]

## 🎈 Simplificação
Botão em toda resposta do coach → reescreve p/ iniciante total (modelo barato,
~2s). Encadeável; a versão simples entra no histórico da conversa. Evento
`simplify` no portal mede onde a linguagem perde as pessoas.
