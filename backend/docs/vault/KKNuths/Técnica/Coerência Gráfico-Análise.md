---
tags: [kknuths, tecnica, produto]
---
# Coerência Gráfico↔Análise

Auditoria exaustiva (2026-07-11) após o caso do quiz de JTs: veredito "fold"
(shove UTG 8,9bb = top 12%) e a tabela veio o range de abertura de 100bb —
COM JTs dentro. 11 incoerências corrigidas; invariantes abaixo.

## Invariantes (garantidos por código + teste)
1. **Gráfico de spot de shove = o MESMO número do veredito**: `push_fold`
   aproximado gera chart automático "top X%"; `send_range_chart` aceita
   position+stack_bb (≤20bb) e usa `shove_threshold` — impossível divergir.
2. **"Shove BB" não existe** (BB é o caller): dispatch rejeita e instrui
   `role='BB'` (range de CALL de all-in).
3. **ICM sem bf real é erro**: o gráfico não pode citar bubble factor
   diferente do texto (default 1,5 abolido no modo icm).
4. **Todo gráfico prometido chega ou avisa**: render falho vira mensagem
   "⚠️ não consegui montar o gráfico (…)" + evento `chart_failed` no banco.
5. **Gráfico órfão expira**: `PENDING_CHARTS`/`PENDING_DOCS` têm TTL de
   15min — anexo de uma resposta que falhou não gruda na interação seguinte.
6. **Sem duplicatas**: dedupe por spec preservando ordem (teto de 4 é de
   gráficos ÚNICOS).
7. **Gráfico automático é citado no texto** (regra 2c do prompt): ranges
   consultados (preflop_range/equity_vs_range/push_fold) chegam anexados e
   o coach referencia ("range no gráfico abaixo").
8. **Títulos sem ambiguidade**: "3-bet contra open de CO" (não "3bet — CO");
   open ganha "(stack fundo)".
9. **/simular modo "e se" fecha o circuito**: `sim_whatif` coleta charts e
   `on_sim_answer` envia (antes o veredito prometia e nada chegava).
10. **Números iguais entre comandos**: /evolucao grava os valores
    bayes-corrigidos (os MESMOS do /stats); weekly report idem; "você vs
    field" rotula "(corrigido)" porque a mediana do field é crua.

## Consistência de veredito (a raiz do problema)
- Caso 99 CO vs UTG: "3-bet tranquilo" às 09:29, "call" às 12:29 — mesma
  equity (48%), conclusão sorteada. Causas: temperature default (1.0) e
  nenhuma âncora.
- **Fix**: temperature 0.2 nas análises / 0.0 na extração (via wrapper
  `_create`, ver [[Infraestrutura e Deploy]]); regra 2b: veredito preflop
  compara com `preflop_range` (mesma mão+posição+ação = mesmo veredito);
  followup: sem informação nova o veredito é o MESMO — mudou, diz o porquê;
  frequência mista de solver NUNCA é o conselho (vira UMA ação prática).
- Regra 1b: número dito pelo aluno (pote/sizing/stack) é INSUMO legítimo
  das tools; dado faltante vira PERGUNTA, nunca "não dá pra calcular".

## Onde olhar no código
- `app/agent/llm.py`: `charts_from_tool_call`, dispatch do
  `send_range_chart`, regras 1b/2b/2c, `_create`/`_NO_TEMP`
- `app/bot/processing.py`: `_stash_charts` (dedupe/TTL/aviso), `sim_whatif`
- `app/analysis/pushfold.py`: `shove_threshold`
- `tests/test_bayes.py`: regressões de cada invariante
