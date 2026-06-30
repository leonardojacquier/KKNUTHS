# Poker Hand Analyzer — Plano de Produto (SaaS via Telegram)

> Nome de trabalho: **KKNuths** (ajustável). Documento de planejamento — define funcionalidades,
> arquitetura, modelo de dados, pipeline de análise e o modelo de cobrança do SaaS.
>
> **Decisões assumidas (pontos de decisão — fáceis de reverter):**
> - **Foco do MVP:** Torneios (MTT/SNG) primeiro, arquitetura já suporta cash game.
> - **Cobrança:** Assinatura por planos + pacotes de créditos extras (híbrido).
> - **Idioma:** Português no MVP, pipeline pronto para multilíngue.

---

## 1. Visão geral

Um agente de IA que vive dentro do **Telegram** e analisa pôquer. O jogador envia
**qualquer formato** — print/foto da mesa, PDF de relatório, `.txt` de hand history exportado
(PokerStars, GGPoker, PartyPoker, 888, etc.), CSV de tracker (Hold'em Manager / PokerTracker) —
e o agente:

1. **Normaliza** o input para um formato canônico de mãos.
2. **Analisa** mão a mão, sessão a sessão e o **torneio inteiro** (ICM, bubble, push/fold).
3. **Estabelece o estilo do jogador** (VPIP/PFR/3bet/agressão, tendências, leaks).
4. **Armazena tudo** numa base de conhecimento por usuário (estruturada + vetorial).
5. **Responde no chat** com leitura técnica, plano de melhoria e métricas ao longo do tempo.

Monetização: **SaaS com cobrança recorrente** (planos) + créditos para uso pesado.

### Proposta de valor
- Coach de pôquer disponível 24/7 no app que o jogador já usa (Telegram).
- Aceita **qualquer formato** — zero fricção de exportação.
- Memória persistente: o agente "conhece" o histórico e a evolução do jogador.

---

## 2. Funcionalidades

### 2.1 MVP (Fase 1 — primeiras 6–8 semanas)
- **Onboarding no Telegram**: `/start`, vínculo de conta, escolha de idioma e moeda.
- **Ingestão multi-formato**:
  - `.txt` de hand history (parser nativo — começa por PokerStars + GGPoker).
  - Imagem/print (OCR + visão para extrair board, stacks e ações).
  - PDF (relatórios de torneio / hand history em PDF).
- **Análise de mão única**: equity, pot odds, EV da decisão, erro vs. linha GTO/exploit, comentário em linguagem natural.
- **Análise de torneio completo**: trajetória de stack, momentos-chave, decisões de bubble/ICM, push/fold por estágio.
- **Perfil de estilo**: VPIP, PFR, 3-bet%, fator de agressão, WTSD — com rótulo (TAG, LAG, nit, calling station…).
- **Base de conhecimento por usuário**: histórico de mãos, sessões e torneios consultável ("quais meus maiores leaks no river?").
- **Cobrança**: plano Free + Pro via Stripe; medição de uso.

### 2.2 Fase 2 (escala e profundidade)
- Suporte a mais salas (PartyPoker, 888, WPN, Winamax) e a cash game.
- **Solver leve / pré-computado** para ranges e sizings comuns (não solver completo em runtime).
- **Relatórios semanais** automáticos enviados no Telegram (resumo + 3 leaks prioritários).
- **Comparação temporal**: evolução de métricas, "você melhorou X% em 3-bet defense".
- Pacotes de **créditos** para análises pesadas (torneio longo, deep-dive com solver).
- Painel web (read-only) para visualizar gráficos e histórico.

### 2.3 Fase 3 (diferenciação)
- **Análise de vídeo/replay** e import direto de trackers (HM3/PT4) via upload de DB.
- **Range builder** interativo e drills personalizados baseados nos leaks do jogador.
- **Modo coach**: planos de estudo semanais com metas mensuráveis.
- API pública / parceria com afiliados de salas.
- Comunidade / leaderboards anônimos por buy-in.

---

## 3. Arquitetura técnica

```
                            ┌──────────────────────────┐
   Telegram (usuário) ──────▶  Telegram Bot (webhook)  │
                            └────────────┬─────────────┘
                                         │  enfileira job
                                ┌────────▼─────────┐
                                │   API / Backend  │  (FastAPI ou NestJS)
                                │  - auth/billing  │
                                │  - rate limit    │
                                └────────┬─────────┘
                                         │
                        ┌────────────────┼────────────────┐
                        ▼                ▼                 ▼
                 ┌────────────┐   ┌─────────────┐   ┌──────────────┐
                 │ Ingestão / │   │  Agente de  │   │  Knowledge   │
                 │  Parsers   │   │  Análise    │   │  Base        │
                 │ (txt/img/  │   │ (LLM + tools│   │ (Postgres +  │
                 │  pdf/csv)  │   │  de poker)  │   │  pgvector)   │
                 └─────┬──────┘   └──────┬──────┘   └──────┬───────┘
                       └─────────────────┴─────────────────┘
                                 formato canônico de mão
```

### 3.1 Stack recomendada
- **Bot/Backend**: Python + FastAPI + `python-telegram-bot` (ou aiogram). Python tem o melhor ecossistema de pôquer (`treys`, `deuces`, `PokerKit` para equity/eval).
- **Fila de jobs**: Redis + RQ/Celery (análise é assíncrona; arquivos grandes não bloqueiam o chat).
- **Banco**: **Supabase (Postgres) + pgvector** — relacional para mãos/usuários/billing e vetorial para a base de conhecimento (MCP do Supabase já disponível neste ambiente).
- **Storage de arquivos**: Supabase Storage / S3 para os uploads originais.
- **LLM**: Claude (Opus para análise profunda, Haiku para classificação/parse barato). Visão do Claude para OCR de prints.
- **Billing**: Stripe (assinaturas + metered usage + pacotes de crédito).
- **Deploy**: Railway/Fly.io/Render no início; container único + worker.

### 3.2 Por que assíncrono
Parsear um torneio de 2.000 mãos + rodar equity + LLM leva segundos a minutos. O bot responde
"recebido, analisando…" na hora e envia o resultado quando o worker termina. Evita timeouts do
Telegram e dá UX previsível.

---

## 4. Pipeline de ingestão (o coração do "qualquer formato")

| Formato | Estratégia |
|---|---|
| `.txt` hand history | Parser determinístico por sala (regex/gramática). Mais preciso e barato. PokerStars/GG primeiro. |
| CSV de tracker | Mapeamento de colunas por tracker (HM3/PT4) → formato canônico. |
| PDF | Extração de texto (`pdfplumber`); se for PDF "imagem", cai no fluxo de visão. |
| Imagem/print | **Visão do LLM** extrai board, hero cards, stacks, posições e ações → JSON canônico. Fallback OCR (`tesseract`) para texto puro. |
| Formato desconhecido | LLM tenta inferir o esquema e converte para o canônico, com flag de baixa confiança para revisão. |

**Formato canônico de mão** (validado com Pydantic) — tudo converge para isto:
```jsonc
{
  "hand_id": "...",
  "site": "PokerStars",
  "game": "NLHE",
  "format": "tournament",        // tournament | cash | sng
  "stakes": { "buyin": 22, "currency": "USD", "level": "100/200/25" },
  "table": { "max_seats": 9, "button_seat": 3 },
  "hero": { "seat": 5, "position": "BTN", "cards": ["As","Kd"], "stack": 14500 },
  "players": [ /* seat, stack, position */ ],
  "streets": {
    "preflop": [ { "actor": "hero", "action": "raise", "amount": 450 } ],
    "flop":    { "board": ["Ah","7c","2d"], "actions": [ /* ... */ ] },
    "turn":    { /* ... */ },
    "river":   { /* ... */ }
  },
  "result": { "hero_won": 980, "showdown": true },
  "confidence": 0.97             // qualidade do parse (1.0 = txt nativo, menor = visão/inferência)
}
```

O `confidence` permite tratar dados de print (menos confiáveis) diferente de hand history nativa.

---

## 5. Agente de análise

O agente é um **LLM com ferramentas determinísticas** (não pede pro LLM "calcular equity de cabeça").

**Tools expostas ao agente:**
- `equity(hero, villain_range, board)` → equity exata/Monte Carlo (`PokerKit`/`treys`).
- `pot_odds(pot, to_call)` e `ev(decision)` → cálculos fechados.
- `icm(stacks, payouts)` → pressão de ICM e EV em $ real no torneio.
- `push_fold(stack_bb, position, players_left)` → range Nash/Holdem Resources pré-computado.
- `range_vs_range(...)`, `preflop_chart(...)` → charts pré-computados.
- `kb_search(user_id, query)` → busca semântica no histórico do jogador.

**Fluxo por mão:** parse → enriquecer com tools → LLM monta a leitura técnica (o que foi bem/mal, linha alternativa, magnitude do erro em EV/$) → grava resumo + embedding na KB.

**Análise de torneio:** agrega mãos, identifica spots críticos (all-ins, bubble, decisões de ICM, blefes grandes), e produz um **relatório de torneio** com nota e 3 ações de melhoria.

**Estilo do jogador:** estatísticas calculadas de forma determinística sobre todas as mãos
(VPIP, PFR, 3-bet, AF, WTSD, c-bet%, fold-to-3bet) + rótulo gerado pelo LLM com contexto. Recalculado
incrementalmente a cada novo upload.

---

## 6. Base de conhecimento

Dois níveis, ambos no Postgres:

1. **Estruturado** (tabelas relacionais): toda mão, sessão e torneio normalizados → permite
   estatísticas exatas e gráficos.
2. **Semântico** (`pgvector`): resumos em linguagem natural de cada mão/torneio/leak embedados →
   permite perguntas abertas ("me mostre mãos onde paguei river ruim contra raise") com RAG.

### Modelo de dados (essencial)
```
users(id, telegram_id, lang, currency, plan, credits, created_at)
subscriptions(id, user_id, stripe_sub_id, plan, status, period_end)
uploads(id, user_id, file_url, format, status, confidence, created_at)
hands(id, user_id, upload_id, site, format, canonical_jsonb, played_at)
hand_analysis(id, hand_id, ev_loss, mistakes_jsonb, summary, embedding vector)
tournaments(id, user_id, buyin, result, itm, report_jsonb, played_at)
player_stats(user_id, vpip, pfr, three_bet, af, wtsd, label, updated_at)
usage_events(id, user_id, type, cost_credits, created_at)   -- billing/metering
```

---

## 7. Modelo de cobrança (SaaS) — como será feito

**Stripe** como gateway. Híbrido **assinatura + créditos**:

| Plano | Preço (sugestão) | Limites |
|---|---|---|
| **Free** | R$ 0 | 20 mãos/mês, 1 torneio/mês, análise resumida, sem histórico longo |
| **Pro** | ~R$ 49/mês | 2.000 mãos/mês, torneios ilimitados, perfil de estilo, relatórios semanais, KB completa |
| **Premium** | ~R$ 129/mês | Ilimitado*, deep-dive com solver, comparação temporal, prioridade na fila |
| **Créditos extras** | pacotes (ex. R$ 19 / 500 créditos) | Para análises pesadas além da cota |

**Como funciona tecnicamente:**
1. **Stripe Checkout** para assinar; **Customer Portal** para o usuário gerenciar/cancelar.
2. **Webhooks do Stripe** (`checkout.session.completed`, `customer.subscription.updated/deleted`,
   `invoice.paid`) atualizam `subscriptions` e liberam o plano.
3. **Metering**: cada análise grava um `usage_event` com custo em créditos. Antes de processar, o
   backend checa cota/créditos; se estourar, oferece upgrade ou compra de créditos **dentro do Telegram**
   (botão inline → link de pagamento Stripe).
4. **Cobrança de uso variável** (Premium pesado) via Stripe metered billing opcional.
5. **Trial** de 7 dias no Pro para conversão.

**Antifraude/limites:** rate limit por usuário, validação de tamanho de arquivo, e cota dura no Free
para controlar custo de LLM (o maior custo variável). Haiku para parse/classificação barata, Opus só
no deep-dive — isso protege a margem.

---

## 8. Custos e margem (ordem de grandeza)
- **Maior custo variável:** tokens de LLM. Mitigação: parsers determinísticos (não gastam LLM),
  Haiku para tarefas baratas, Opus só em deep-dive, cache de análises idênticas.
- **Infra:** Supabase + 1 worker + Redis ≈ baixo no início (dezenas de USD/mês).
- **Margem-alvo:** manter custo de LLM por usuário Pro bem abaixo do preço; cota dura garante teto.

---

## 9. Roadmap por fases

| Fase | Entrega | Duração estimada |
|---|---|---|
| **0 — Fundação** | Repo, bot `/start`, Supabase, upload de `.txt`, formato canônico | 1–2 sem |
| **1 — MVP** | Parser PokerStars/GG, análise de mão + torneio, perfil de estilo, KB, Stripe (Free/Pro) | 4–6 sem |
| **2 — Escala** | Visão p/ prints, PDF, mais salas, cash game, créditos, relatórios semanais, painel web | 6–8 sem |
| **3 — Diferenciação** | Solver leve, drills, import de trackers, API/afiliados | contínuo |

---

## 10. Riscos e mitigação
- **Variedade de formatos de hand history** → começar com 2 salas, formato canônico isola o resto.
- **Precisão de OCR em prints** → usar visão do LLM + `confidence`; pedir confirmação quando baixo.
- **Custo de LLM** → cotas duras, modelos baratos no caminho quente, cache.
- **Termos das salas de pôquer** → análise é sobre arquivos exportados pelo próprio usuário (uso pessoal); revisar ToS de cada sala antes de import automatizado.
- **Conformidade de pagamento/jogo** → SaaS de análise/educação, não operação de jogo; ainda assim validar regras locais.

---

## 11. Próximos passos imediatos
1. Confirmar nome, planos/preços e sala inicial (PokerStars vs GGPoker).
2. Criar projeto Supabase + schema da Seção 6.
3. Esqueleto do bot Telegram (`/start`, upload, "recebido → analisando").
4. Parser determinístico da primeira sala + formato canônico (Pydantic).
5. Primeira tool de análise (equity + pot odds) e resposta no chat.
6. Integração Stripe (Free/Pro) + metering.
