---
tags: [kknuths, tecnica, negocio]
atualizado: 2026-07-26
---
# Custo de LLM

Até 2026-07-26 o produto contava **usos**, nunca **dinheiro**:
`record_usage` gravava o inteiro 1. Nenhuma linha do código sabia quanto
custa uma análise — e o teto de 50 análises/mês foi decidido sem esse
número. Sem custo medido, qualquer preço é chute, e chute em custo erra
sempre pro lado caro.

## Onde é medido
`_create()` em `app/agent/llm.py` — o ponto **único** por onde passa toda
chamada do produto. Canário varre `app/` e falha se aparecer
`messages.create` fora dele: chamada fora do porteiro gasta dinheiro que a
contabilidade não vê.

Registra em `bot_events` (`event='custo_llm'`, `detail` jsonb — entra sem
migração): entrada, saída, **escrita e leitura de cache**, modelo, tarefa,
dono, e o dólar calculado.

- cache **leitura 0,1×** / **escrita 1,25×** (TTL 5 min) sobre o preço de
  entrada. O cache já está ligado; ignorá-lo daria número inventado
- tarefas: `analise`, `conversa`, `simulador`, `leitura_print`, `briefing`,
  `busca`, `caderno`, `simplificar`, `cron:juiz`
- **modelo fora da tabela → `usd = None` + aviso.** Nunca inventa preço nem
  assume zero: custo falso é pior que custo nenhum, porque parece medição.
  O agregado expõe `chamadas_sem_preco` e o texto grita SUBESTIMADO
- contabilidade nunca derruba a resposta do aluno (`registrar()` engole
  exceção; há teste)

## Tabela de preços (US$/1M tokens, conferida 2026-06-24)
| modelo | entrada | saída |
|---|---|---|
| Opus 5 / 4.8 / 4.7 / 4.6 | 5 | 25 |
| Fable 5 | 10 | 50 |
| Sonnet 5 / 4.6 | 3 | 15 |
| **Haiku 4.5** | **1** | **5** |

Em uso: `analysis_model=claude-opus-4-8`, `cheap_model=claude-haiku-4-5`.

## Onde o número aparece
- `/quem [telegram_id]` (só o dono) — custo do mês, por tarefa, por aluno e
  o **US$/análise** de cada um. É a régua do preço: plano só fecha se a
  mensalidade cobrir o teto × esse valor
- resumo diário 23h — custo do dia e US$/mão, sem precisar pedir

## Estimativa antes da medição (ORDEM DE GRANDEZA, não medida)
Análise ≈ 4 rodadas de ferramenta ≈ US$0,30; a conversa depois soma
US$0,30–0,60 (cada pergunta reprocessa o histórico crescendo). Logo
**US$0,30–1,00 (R$1,50–5,00) por análise + conversa** → o teto de 50
custaria **R$75–250/usuário/mês** de custo bruto. Nenhum recreativo BR paga
isso: se o custo real ficar no topo da faixa, o plano de 50 dá prejuízo em
qualquer preço vendável.

Alavanca óbvia antes de mexer em preço: **análise em Opus, conversa em
Haiku** (5× mais barato). O follow-up é onde o custo acumula e é a parte
menos exigente — corte esperado de 50–65%. **Não implementado**: espera o
número real do piloto.

## Limite honesto
Os dados começam do zero em 2026-07-26. Julho não tem esse número e nunca
vai ter — o histórico não pode ser reconstruído porque os tokens nunca
foram gravados. ~3 dias de uso do dono dão a ordem de grandeza; 1 semana
com os 10 testadores dá o número real (o padrão de uso de quem não opera a
ferramenta é o que importa).

Relacionado: [[Pricing e Planos]] · [[Banco de Dados]] ·
[[Portal Admin e Métricas]]
