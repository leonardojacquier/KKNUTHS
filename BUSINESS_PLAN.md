# KKNuths — Business Plan
### Coach de poker com IA no Telegram · Julho/2026

---

## 1. Sumário executivo

**KKNuths** é um coach de poker com IA que vive no Telegram: o jogador envia suas mãos
em qualquer formato (arquivo, print, texto colado, CSV, voz) e recebe análise técnica
com **matemática exata** (equity vs range, ICM, pot odds), em **português acessível**,
com **memória permanente** do seu jogo — perfil de estilo, evolução, treinos e
simulações personalizadas.

- **Estado**: produto construído e no ar (@KKNUts_BOT), em beta. Infra a ~US$20/mês,
  75 testes automatizados, deploy contínuo.
- **Mercado**: 12M+ brasileiros já jogaram poker online; campo em crescimento (+27%
  em prize pools em 2026) e recém-regulamentado (Lei 14.790/2023).
- **Modelo**: freemium + assinatura (R$ 29,90 Pro / R$ 69,90 Premium), Pix + cartão +
  Telegram Stars, ancorado como "20x mais barato que o GTO Wizard".
- **Tese**: as ferramentas sérias (GTO Wizard US$26–206/mês, PokerTracker) são caras,
  em inglês, desktop e intimidadoras. A massa recreativa-séria de torneios low/mid
  stakes no Brasil/LatAm não usa nada — e vive no celular/Telegram.
- **Meta 12 meses (cenário base)**: 1.000 assinantes pagos ≈ **R$ 35 mil MRR** com
  margem bruta ≥ 65%.

---

## 2. O produto (já construído)

| Capacidade | Descrição |
|---|---|
| Ingestão universal | `.txt` de 5 salas (PokerStars, GGPoker, Winamax, Party, 888), CSV de trackers, print/foto com leitura da ação completa, PDF, texto colado, **voz** |
| Análise com IA | Claude com ferramentas determinísticas: equity vs range (Monte Carlo), ICM Malmuth-Harville, bubble factor, Nash push/fold, pot odds/EV/SPR — **números calculados, nunca inventados** |
| Torneio completo | "História do torneio": mãos decisivas analisadas e conectadas num diagnóstico |
| Memória | Todo histórico em banco; perfil (VPIP/PFR/3-bet/AF) cumulativo; busca semântica (`/ask`) |
| Treino | `/treino` (drill), `/simular` (replay jogável com botões + veredito "e se" da linha do usuário), quiz diário (roadmap) |
| Conversa | Follow-up em texto/áudio sobre qualquer análise; coach geral para dúvidas abertas; releitura do print quando contestado |
| Automação | Relatório semanal com "leak da semana"; auto-sync de pasta (roadmap) |
| Custo protegido | Cota gratuita, modelo barato em tarefas simples, prompt caching |

---

## 3. Oportunidade de mercado

**Momento Brasil (2026):**
- 12M+ brasileiros já experimentaram poker online; GGPoker (nosso formato nativo)
  ultrapassou a PokerStars como sala mais popular, com interface PT e torneios BR.
- Circuitos ao vivo: média de 450 → 700+ jogadores/etapa; prize pool médio +27% a/a.
- Lei 14.790/2023 + entendimento AGU (poker = habilidade) deram segurança jurídica.

**O gap:** ferramentas existentes atendem o profissional anglófono de desktop:
- GTO Wizard: US$ 26–206/mês (R$ 140–1.100+), inglês, curva de aprendizado alta.
- PokerTracker/HM3: instalação, configuração, 100+ métricas cruas, sem coaching.
- ChatGPT genérico: **erra a matemática** e não tem memória do jogador.

**Nosso cliente (ICP):** jogador recreativo-sério de MTT/cash low-mid stakes
(buy-ins US$ 1–50), 25–45 anos, joga no celular, estuda pouco por falta de ferramenta
acessível, já usa Telegram diariamente. Estimativa conservadora de mercado endereçável
imediato: 1–3% dos 12M = **120–360 mil jogadores** ativos o bastante para pagar por
melhoria de jogo.

---

## 4. Diferenciação e fosso competitivo

**Por que não usar um LLM genérico?** (nosso pitch técnico)
1. **Matemática exata**: LLM puro alucina equity/ICM; nós calculamos (demonstrável em
   vídeo lado a lado — peça-chave de marketing).
2. **Memória longitudinal**: milhares de mãos em banco, perfil e evolução — impossível
   numa janela de contexto; quanto mais usa, mais insubstituível.
3. **Ingestão em escala**: torneio de 2.000 mãos parseado com precisão determinística.
4. **Produto é push**: quiz diário, relatório semanal, análise pós-sessão — chat
   genérico só responde quando perguntado; hábito é o que retém.
5. **Fluxos nativos**: simulador com botões, drills, voz — produto, não prompt.
6. **Benchmarks do field** (com escala): "seu 3-bet está abaixo da média do seu stake"
   — dado agregado proprietário que cresce com cada usuário.

**Por que não o GTO Wizard?** Preço (20x), idioma, plataforma (desktop vs Telegram),
proposta (estudo de equilíbrio vs coaching das SUAS mãos em linguagem simples).

**Fosso real** = dados do usuário + hábito diário + português/comunidade + benchmarks.
A tecnologia de LLM é commodity; o sistema em volta não.

---

## 5. Modelo de receita

| Plano | Preço | Inclui |
|---|---|---|
| **Grátis** | R$ 0 | 15 análises/mês, /treino, coach geral limitado |
| **Pro** | **R$ 29,90/mês** (R$ 299/ano) | Ilimitado, torneio completo, /simular + "e se", voz, relatório semanal |
| **Premium** | **R$ 69,90/mês** (R$ 699/ano) | Tudo + auto-sync, benchmarks do field, prioridade, painel web |

- **Pagamento**: Pix (essencial no BR) + cartão via Stripe + **Telegram Stars**
  (pagamento sem sair do bot). Anual com ~2 meses grátis para reduzir churn.
- **Âncoras**: "menos que 1 buy-in por mês"; "20x mais barato que ferramenta gringa".
- **Receitas paralelas** (fase 2+): afiliação de salas, marketplace de coaches
  (take 15–20%), white-label B2B para escolas de poker.

**Unit economics (premissas explícitas):**
- Custo LLM/análise profunda (Opus + caching): US$ 0,05–0,15.
- Usuário Pro típico: 25–40 análises + chats/mês → custo **R$ 10–18/mês**.
- Margem bruta alvo Pro: **50–65%** (melhora com Haiku no chat geral e caching);
  Premium: ~75%. Infra fixa: ~US$ 20–50/mês até ~2.000 usuários (VPS + Supabase free→Pro).
- Regra de proteção: cota dura no grátis; chat geral migra p/ modelo barato ao escalar.

---

## 6. Go-to-market (validação antes de escala)

**Fase 0 — Beta fechado (agora → 6 semanas)**
- 20–50 jogadores de grupos/clubes que o fundador conhece. Custo: R$ 0.
- **Métrica de corte: retenção semana 4 ≥ 35%** e ≥ 3 sessões de uso/semana/usuário.
  Sem isso, não gastar R$ 1 em tráfego — iterar produto.

**Fase 1 — Comunidades (meses 2–4)**
- Grupos de Telegram/WhatsApp de poker BR, fóruns, influencers micro (jogadores de
  MTT com 5–50k seguidores) com código de afiliado (mês grátis + rev share 20%).
- Conteúdo: vídeos "ChatGPT vs KKNuths" e "análise da mão famosa do torneio X".
- Ligar cobrança (Pix) quando retenção provada. Meta: 100–200 pagantes.

**Fase 2 — Escala paga (meses 5–12)**
- Tráfego pago (Meta/YouTube poker) com CAC alvo ≤ 3 meses de ARPU (~R$ 90–100).
- Espanhol → LatAm (GGPoker forte em AR/MX). Parcerias com clubes credenciados
  (novo marco regulatório estadual).

---

## 7. Roadmap de produto

| Trimestre | Entregas | Objetivo |
|---|---|---|
| **T3/2026** | Quiz diário push · Pix/Stripe ligado · streaks/metas · hardening | Hábito + primeiras receitas |
| **T4/2026** | Auto-sync (watcher de pasta) · bankroll tracker · painel web básico | Momento "uau" + stickiness |
| **T1/2027** | Benchmarks do field · espanhol · bot em grupos de estudo | Fosso de dados + LatAm |
| **T2/2027** | Marketplace de coaches · white-label B2B · API | Novas linhas de receita |

---

## 8. Métricas (o que olhar toda semana)

- **North star: análises por usuário ativo/semana** (proxy de valor entregue).
- Retenção W1/W4, DAU/MAU, conversão grátis→pago, churn mensal, MRR, CAC/LTV,
  custo LLM por usuário (guardrail de margem).
- Já instrumentado: tabela `bot_events` registra toda interação.

---

## 9. Projeções 12 meses (pós-lançamento pago)

| Cenário | Usuários grátis | Pagantes | ARPU | MRR | Margem bruta |
|---|---|---|---|---|---|
| Conservador | 2.000 | 300 | R$ 33 | **R$ 10 mil** | ~55% |
| Base | 6.000 | 1.000 | R$ 35 | **R$ 35 mil** | ~65% |
| Otimista | 15.000 | 2.800 | R$ 38 | **R$ 106 mil** | ~70% |

Premissas: conversão grátis→pago 12–18% (produto de hábito com paywall de uso),
churn mensal 8–12% (anual + bankroll tracker derrubam isso), mix 80/20 Pro/Premium.

---

## 10. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Churn alto (ferramenta de estudo) | Quiz diário, streaks, relatório semanal, bankroll tracker, plano anual |
| GTO Wizard/BBB lançar coach IA barato | Correr no fosso: dados + PT/ES + hábito no Telegram + benchmarks |
| Custo LLM corroer margem | Cotas, Haiku no chat, caching, monitorar custo/usuário semanal |
| Salas mudarem formato de HH | Formato canônico isola; ajuste de parser em horas (deploy contínuo) |
| Percepção de "ferramenta proibida" | Posicionar como estudo pós-sessão (como trackers, permitidos); nunca RTA; nunca conectar na conta |
| Dependência de 1 fundador | Código versionado, testes, deploy automático, docs (já feito) |

---

## 11. Investimento e uso de recursos

Bootstrapped-friendly: o produto já existe. Necessidades até o breakeven (~150–300
pagantes): custos de LLM/infra (R$ 500–2.000/mês conforme uso), ~R$ 3–8 mil/mês de
marketing na Fase 2, contabilidade/MEI→ME. Sem necessidade de capital externo no
cenário conservador; um aporte anjo (R$ 150–300 mil) apenas aceleraria a Fase 2
(tráfego + ES + benchmarks com time).

---

## 12. Marcos de decisão

1. **Semana 6**: retenção W4 ≥ 35%? → liga cobrança. Senão → itera hábito.
2. **Mês 4**: 100+ pagantes com churn < 12%? → inicia tráfego pago.
3. **Mês 8**: CAC ≤ 3×ARPU sustentado? → escala + espanhol.
4. **Mês 12**: MRR ≥ R$ 25 mil? → contratar 1 dev/growth ou avaliar aporte.
