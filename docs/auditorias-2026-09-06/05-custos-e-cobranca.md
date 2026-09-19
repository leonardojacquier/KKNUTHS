# Anexo 5 — Custos e modelo de cobrança

*Agente financeiro, 06/09/2026. `[MEDIDO]` = lido no código com arquivo:linha.
`[ESTIMADO]` = conta sobre premissas declaradas. Preços de API: tabela
Anthropic 2026-06-24 (Sonnet 5 US$2/10 por M in/out; Opus 4.8 5/25; Haiku
4.5 1/5; cache leitura 0,1×, escrita 1,25× (5 min) / 2× (1 h)) — **confirmar
na fatura**. Câmbio R$5,40 (cravado em `custo.py:203`).*

## 1. Modelos e chamadas `[MEDIDO]`

| Setting | Default | Onde |
|---|---|---|
| `analysis_model` | `claude-sonnet-5` (era opus até 15/08; A/B 7,7 × 6,0) | `config.py:34`; `OPERATIONS.md:140` |
| `cheap_model` | `claude-haiku-4-5-20251001` | `config.py:36` |
| `analysis_fallback_model` | `claude-opus-4-8` (só no resgate) | `config.py:41` |
| `.env.example:6` | **ainda diz `ANALYSIS_MODEL=claude-opus-4-8`** | conferir o `.env` do VPS |

| Operação | Modelo | max_tokens | Cache | Linha |
|---|---|---|---|---|
| Análise de mão | analysis | 4000; resgate 2500 | sim, 1h | `llm.py:24,36,2165` |
| Leitura de torneio | analysis | 6000; resgate 4000 | sim | `llm.py:60,2126` |
| Relatório mão a mão (lotes de 6) | analysis | 4000/lote | **não** | `handreport.py:238` |
| Follow-up | **analysis** (não Haiku) | 1200; resgate 2500 | sim | `llm.py:2679,2710` |
| Simulador | analysis | 900 | sim | `llm.py:2804` |
| Briefing pré-torneio | analysis | 1100 | não | `llm.py:2343` |
| Leitura de print (2 passadas) | analysis | 1024+500 | não | `llm.py:3036` |
| Lobby (2 passadas) | analysis | 2048+2048 | não | `llm.py:3398` |
| Selo de emergência / simplificar / caderno / /ask / juiz | cheap | 60 / 700 / 400 / 500 / 200 | — | várias |
| Voz/vídeo | OpenAI whisper-1 (US$0,006/min) | — | — | `speech.py:26` |

Thinking desligado em toda chamada (`llm.py:1135`). Prefixo cacheado ≈ 16k tokens (system + 33 tools). Cache só no bloco `system`; o JSON da mão (3-9k) é reenviado sem cache a cada rodada.

**Divergência na tabela do código:** `custo.py:36` grava Sonnet a **US$3/15**; a tabela pública diz **2/10**. `custo.py:44` usa escrita 1,25×; o app pede TTL 1h (2×). O `/quem` superestima Sonnet ~50% e subestima escritas de cache 37,5%.

## 2. Custo por operação `[ESTIMADO]` (Sonnet 2/10; entre parênteses, tabela do código 3/15)

| Operação | US$ | R$ |
|---|---|---|
| 1 análise de mão avulsa (3 rodadas) | 0,06 (0,08) | 0,32 |
| — pior caso (5 rodadas + resgate + Opus) | 0,35–0,40 | |
| — em Opus | 0,14 | |
| 1 follow-up (2 rodadas) | 0,03 (0,045) | 0,16 |
| 1 torneio de 150 mãos (coach + 25 lotes) | 0,51 (0,75) | 2,75 |
| — torneio de 60 mãos | 0,25 | |
| 1 leitura de print | 0,02 | 0,11 |
| Juiz diário + crons | 1–3/mês | |

## 3. Custo por aluno/mês

Cota `[MEDIDO]`: free 50 (env; `.env.example` e `OPERATIONS.md` dizem 100), piloto 100, pro/premium **ilimitado** (`quota.py:13,22,31`). **Só upload consome** (`processing.py:683`); follow-up, simulador, /treino, /range não consomem (`quota.py:152`).

| Cenário | US$/mês | R$/mês |
|---|---|---|
| Realista (15 análises + 30 follow-ups) | **2,4** | **13** |
| Idem em Opus | 5,8 | 31 |
| Pior caso free=50 (50 torneios + 200 msgs) | 31,5 | 170 |
| Pior caso piloto=100 | 57 | 308 |
| Pro "ilimitado" heavy (60 torneios + 300 msgs) | 39,6 | 214 |

Infra fixa: VPS compartilhado com GNH/TitanCalc (custo não atribuído; BP diz "US$20"); Supabase plano não documentado; **Redis: zero uso em `app/`**; crons US$1–3. **Fixo ≈ R$110–280/mês.**

## 4. Cobrança — o que existe `[MEDIDO]`

**Existe:** `create_checkout_session` (assinatura, price id por plano, cupons) `stripe_service.py:41-62`; `handle_webhook` valida assinatura `:73-80`; `checkout.session.completed` → `update_user_plan` + `upsert_subscription` `:86-101`; rota `POST /stripe/webhook` `api/main.py:45-58`; tabelas `users.plan/credits`, `subscriptions`; `setup_stripe.py` cria Pro **R$49** / Premium **R$129**.

**Impede cobrar:**
1. **Nenhum `/assinar`** — `create_checkout_session` só é chamado em teste.
2. **Cancelamento não rebaixa o plano** (`:103-119` só grava a assinatura; `users.plan` não muda).
3. `user_id` nos eventos de assinatura vem de metadata que o checkout só põe na session → `NOT NULL` estoura.
4. `invoice.paid` no-op; `invoice.payment_failed` não tratado.
5. Testes só dos caminhos "desligado" e "sem assinatura recusa". Zero evento real.
6. Sem Pix, sem Stars, sem anual.
7. Preços em 3 lugares: BP 29,90/69,90; `setup_stripe` 49/129; vault 39-59.

**Checklist:** rail (Pix via Stripe ou MP/Asaas) · `/assinar` · `subscription_data.metadata` · rebaixar plano em cancel/past_due/failed · `/plano` com vencimento · testes com `construct_event` mockado · `STRIPE_WEBHOOK_SECRET` + `PUBLIC_BASE_URL` real · preço num lugar só · **medir follow-ups**.

## 5. Business plan × código

| Tema | BP | Código |
|---|---|---|
| Free | 15/mês | 50 / **100 em prod** |
| Pro/Premium | R$29,90 / 69,90 | Stripe 49 / 129 |
| Features Pro exclusivas | torneio, /simular, voz, semanal | **tudo liberado no free** |
| Features Premium | auto-sync, benchmarks, painel | **não existem** |
| "Haiku no chat geral" | mitigação | **não implementado** — follow-up usa `analysis_model` |
| Pix + Stars + anual | sim | nenhum |
| "Custo protegido: cota" | sim | só upload |

## 6. Três opções de cobrança

**A — Assinatura por faixa (recomendada):** Free 5 análises + 20 msgs; **Pro R$49,90** (R$499/ano) 60 análises (torneio >8 mãos = 3), 200 msgs; Premium R$99,90 200 análises. Pro realista R$13 → **margem 74%**; no teto → −76% (raro). Mudança mínima: `LIMITE_POR_PLANO` já é o mecanismo.

**B — Créditos pré-pagos (Pix):** 20 por R$29, 60 por R$69, 150 por R$149; torneio = 3-5. Margem 45-78%. Encaixa em `users.credits`. Risco: sem MRR, churn invisível, "cada mão custa".

**C — Freemium + Pro ilimitado R$39,90:** margem 67% realista, −436% no heavy. É o que o código já faz; simples de vender, perigoso de bancar.

**Recomendação A**: MRR (o BP mede isso); teto por plano é a única proteção contra o pior caso e já existe; R$49,90 < 1 buy-in e ~3× abaixo do GTO Wizard; margem 74% cobre a incerteza de preço e um retorno a Opus (~38%).

## 7. Unit economics `[ESTIMADO]` (opção A; 20% pagantes; ARPU pagante R$57,40)

| | Hoje (14, grátis) | 14 | 50 | 200 |
|---|---|---|---|---|
| Pagantes | 0 | 3 | 10 | 40 |
| Receita | 0 | R$200 | R$599 | R$2.296 |
| Var. free | R$72 | R$16 | R$58 | R$230 |
| Var. pagantes | — | R$64 | R$180 | R$670 |
| Taxas (2%) | — | R$4 | R$12 | R$46 |
| Fixo | R$129 | R$129 | R$129 | R$281 |
| **Resultado** | **−R$201** | **−R$13** | **+R$220 (37%)** | **+R$1.069 (47%)** |

Sensibilidades: tabela do código ×1,5 → 200 alunos ≈ R$700; Opus ×2,4 → break-even em 200; **free em 50-100 → resultado em 200 vira negativo**. A cota do free é a alavanca de margem mais forte.

## 8. Ações
1. `/quem` × fatura Anthropic; corrigir `custo.py:36,44` e câmbio.
2. Confirmar `ANALYSIS_MODEL` no `.env` do VPS.
3. Medir follow-ups por 2 semanas antes de vender "ilimitado".
4. Corrigir webhook (cancelamento, metadata) e criar `/assinar` — ou MP/Asaas com Pix.
5. `FREE_MONTHLY_ANALYSES` → 5-10 no lançamento; piloto=100 só para os atuais.
6. Preço num lugar só.
