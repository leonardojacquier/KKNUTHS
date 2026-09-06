# Anexo 1 — Uso medido no banco de produção (`kknuths-poker`, 06/09/2026)

Todas as consultas são `SELECT` sobre `bot_events`, `users`, `uploads`,
`hand_analysis`, `usage_events`. `telegram_id <> 0` exclui os crons.

## Usuários e atividade

| username | plano | cadastro | eventos | último evento | dias sem uso |
|---|---|---|---|---|---|
| Ricardo Farah | piloto | 13/07 | 756 | 06/09 | 0 |
| Leo (dono) | free | 02/07 | 962 | 06/09 | 0 |
| alvgomes19 (= Alvino Gomide) | free | 08/08 | 285 | 06/09 | 0 |
| Antony S | free | 24/08 | 33 | 05/09 | 1 |
| Paulo Pinheiro | free | 09/08 | 75 | 05/09 | 1 |
| Lorenzo Jacquier (filho) | free | 03/08 | 86 | 05/09 | 1 |
| ANTONIO PIRES | free | 29/07 | 51 | 05/09 | 1 |
| dscholze1979 | piloto | 04/07 | 124 | 05/09 | 1 |
| Odilon Godeje | piloto | 04/07 | 96 | 05/09 | 1 |
| ttbahr | free | 06/08 | 19 | 14/08 | 23 |
| SivioFernandes | free | 09/08 | 3 | 09/08 | 28 |
| Raphael | free | 09/08 | 6 | 09/08 | 28 |
| Luiz Fabiano Simioni | free | 06/08 | 8 | 09/08 | 28 |
| Eder Rosa | free | 05/08 | 3 | 09/08 | 28 |
| Lucas Carvalho | free | 28/07 | 9 | 09/08 | 28 |

"1 dia sem uso" para 6 deles = o quiz das 19h foi *enviado*; não é uso.

## Por usuário — o que fizeram de verdade

| username | mãos enviadas | conversas | quiz respondidos | comandos | falhas | último uso REAL |
|---|---|---|---|---|---|---|
| Ricardo Farah | 232 | 82 | 27 | 1 | 11 | 06/09 |
| Leo | 213 | 143 | 36 | 49 | 14 | 28/08 |
| alvgomes19 + Alvino Gomide | 14 | 38 | 30 | 26 | 2 | 30/08 |
| Paulo Pinheiro | 8 | 0 | 2 | 5 | 0 | 09/08 |
| dscholze1979 | 4 | 4 | 2 | 0 | 1 | 30/07 |
| ANTONIO PIRES | 4 | 0 | 1 | 0 | 0 | 29/07 |
| Lorenzo Jacquier | 2 | 12 | 1 | 3 | 1 | 30/08 |
| Antony S | 2 | 0 | 3 | 3 | 0 | 24/08 |
| Odilon Godeje | 1 | 3 | 7 | 4 | 1 | 21/08 |
| Raphael, Eder, Luiz Fabiano, Sivio, ttbahr, Lucas | **0** | 0 | 0–2 | 0–6 | 0 | — |

## Retenção depois da primeira mão (externos)

| username | 1ª mão | conversas no D1 | mãos D2–D7 | mãos D8–D30 |
|---|---|---|---|---|
| Ricardo Farah | 17/07 | 5 | **62** | **136** |
| alvgomes19 | 09/08 | 14 | 4 | 2 |
| dscholze1979 | 22/07 | 22 | 3 | 0 |
| Odilon Godeje | 15/07 | 7 | 0 | 0 |
| ANTONIO PIRES | 29/07 | 0 | 0 | 0 |
| Paulo Pinheiro | 09/08 | 0 | 0 | 0 |
| Antony S | 24/08 | 0 | 0 | 0 |

`cota_esgotada`: **0 eventos** para todos.

## Semana a semana

| semana | usuários que usaram | ações reais | mãos enviadas | conversas | análises geradas |
|---|---|---|---|---|---|
| 29/06 | 2 | 55 | 0 | 41 | 48 |
| 06/07 | 2 | 71 | 0 | 41 | 55 |
| 13/07 | 3 | 66 | 16 | 11 | 24 |
| 20/07 | 3 | **204** | 59 | 61 | **136** |
| 27/07 | 4 | 162 | 59 | 46 | 91 |
| 03/08 | **6** | 126 | 38 | 41 | 51 |
| 10/08 | 5 | 85 | 21 | 14 | 27 |
| 17/08 | 4 | 119 | 20 | 82 | 28 |
| 24/08 | 5 | 27 | 4 | 14 | 5 |
| 31/08 | **2** | **11** | 4 | 0 | 4 |

## Eventos (total / usuários distintos / últimos 30 dias)

custo_llm 698/9/336 · daily_quiz_sent 379/9/247 · followup 280/6/64 ·
upload 275/9/59 · replay_pppoker 164/**3**/27 · drill_answer 121/13/57 ·
drill_verdict 97/13/57 · followup_resposta 55/5/55 · start 34/15/11 ·
licao_recebida 23/13/13 · print_recebido 22/5/10 · simplify 20/2/0 ·
btn_range 18/2/1 · followup_failed 16/4/9 · replay_suprema 16/2/6 ·
sim_done 16/3/1 · go_treino 15/9/9 · simular 14/2/0 · treino 12/4/2 ·
upload_failed 12/2/1 · error 12/2/4 · stats 11/4/5 · torneio 9/3/8 ·
dossie_cmd 9/1/9 · evolucao 9/2/7 · range 9/6/5 · vilao 8/2/5 ·
estilo 7/3/4 · preparar 7/3/3 · relatorio 4/3/3 · manual 4/2/1 · /ask 0.

## Uploads por formato

pppoker_replay 164 (conf 0,95; "PDQ 2026 Rodada 5C…6E" = série semanal
do Ricardo) · image 67 (**PPPoker conf 0,56**; GG 0,84; Stars 0,85) ·
txt 26 (GGPoker 19, PokerStars 7; conf 1,00) · suprema_replay 16 ·
mao_do_relatorio 2 · phh 1.

## Custo LLM

| modelo | chamadas | US$ total | US$/chamada | US$ 30d |
|---|---|---|---|---|
| claude-opus-4-8 | 529 | 29,07 | 0,055 | 8,38 |
| claude-sonnet-5 | 267 | 12,00 | 0,045 | 11,41 |
| claude-haiku-4-5 | 253 | 0,40 | 0,002 | 0,20 |
| **total** | | **41,47** | | **20,00** |

Análises consumidas da cota (`usage_events`): Leo 91 (jul) / 45 (ago);
Ricardo 72 / 40 / 4 (set); alvgomes 7; dscholze 7; Paulo 4; demais ≤2.

## Erros recentes

Bad Gateway ×6 em 23/08, ×2 em 24/08, ×6 em 26/08 (upstream);
httpx.ReadError 27/08 e 06/09; "Query is too old" (callback do Telegram
expirado) ×2 em 27/08; `analise_cortada` ×2 em 21/08 (thinking — corrigido);
`narrativa_enganosa` ×2 (guarda pegou); `entrega_falha` 22/08 (gráfico
pedido e não entregue).

## Hora do uso (America/Sao_Paulo, só mãos e conversas)

sex 9h (36) · seg 10h (28) · qui 6h (27) · sáb 17h (25) · qui 9h (23) ·
sex 14h (23) · dom 14h (21). **Manhã seguinte à sessão.** O quiz vai às 19h.

## Juiz

`nota_resposta`: 91 avaliações, média **5,94/10** — contaminada até 26/08
pelo corte de 1.500 chars que o próprio juiz fazia (ver commit `c315347`).
