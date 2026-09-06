---
tags: [kknuths, negocio]
atualizado: 2026-07-26
---
# Pricing e Planos

- **Beta:** tudo liberado no free (50 análises/mês). Melhores testadores
  ganham benefício no lançamento
- **Âncora de valor:** 1h de coach humano R$200+; a assinatura "se paga" se
  recuperar 1 buy-in (leak de 4bb/100 detectado já paga)
- **Faixa alvo:** R$39–59/mês (Pro); B2B: clubes/times com portal próprio
- **Alavancas prontas no código:** `REPORT_AUTO` (relatório automático = Pro,
  sob demanda = free); quota mensal; "solver e exploit avançados" como linha Pro
- Stripe: código existe, DESLIGADO no beta (webhook exige secret; não aceitar
  pagamento antes do lançamento)

## Teto por plano (2026-07-26)
Só existiam dois mundos — 50 análises ou ilimitado. Dar 100 a um testador
exigia dar ILIMITADO, justamente o que não se banca sem saber o custo.

| plano | teto/mês |
|---|---|
| free | 50 |
| **piloto** | **100** (testador convidado, sem cartão) |
| pro / premium | ilimitado |

- Nome `piloto` de propósito: `plus`/`vip` sugere preço e vira promessa que
  ninguém fez
- **Plano desconhecido cai no teto do free, não no ilimitado** — typo em
  `/planode` não pode virar análise ilimitada e de graça. Fail-closed do
  banco caído vale para todo plano com teto
- `/plano` lê o plano REAL e mostra quantas restam. Antes imprimia a
  constante do free para todos: com mais de um teto, um testador com 100
  lendo "você tem 50" é o produto mentindo, e ele não tem como saber qual
  número vale

## A restrição do Telegram (decisão pendente)
Bot que vende bem digital DENTRO do Telegram é obrigado a usar
**Telegram Stars (XTR)**. Não é preferência, é política da plataforma.

| rail | de R$100 você recebe |
|---|---|
| Stars no **celular** (iOS/Android) | ~R$68 — Apple/Google levam 30% antes |
| Stars no desktop/web | ~R$95 |
| **Pix (Mercado Pago / Asaas)** | ~R$99 |
| Stripe cartão BR | ~R$96 |

Os alunos pagam pelo celular → Stars custaria **~32% da receita**.

**Recomendação: não vender dentro do bot.** O bot manda link, o pagamento
acontece fora (Pix), o webhook libera o acesso. O `stripe_service` já tem
essa forma (`create_checkout_session` → `handle_webhook` →
`update_user_plan`); trocar Stripe por Mercado Pago/Asaas dá Pix.

**Risco declarado:** "vender fora, entregar dentro" é fronteira cinza na
política do Telegram. Bots grandes fazem há anos sem problema, mas não é
zero — o pior caso é perder o bot. Com 10 usuários o risco prático é
irrelevante; reavaliar quando virar receita.

## Não dá para precificar ainda
Ver [[Custo de LLM]]: o custo por análise passou a ser medido em
2026-07-26 e **não existe histórico**. Regra de ouro: **só anunciar preço
depois que uma semana de piloto medir o custo**.

Ancoragem para quando o número existir (números para discutir, não para
implementar):

| plano | preço | teto |
|---|---|---|
| Free | R$0 | 5 análises (isca, não produto) |
| Pro | R$59 | 40 |
| Premium | R$129 | 150 |

Referência: GTO Wizard cobra US$49–129/mês, mas atende reg; o público aqui
é o recreativo brasileiro.

## Promoções — o modelo de dados já aguenta
- **`plan`** = teto mensal recorrente
- **`credits`** = saldo avulso que soma ao teto e **não expira** (é o
  "aumentei o crédito do usuário A")
- **`user_meta`** (0 linhas) = estado da promoção:
  `{"promo": "...", "trial_ate": "...", "indicado_por": "..."}`

Falta: `/creditar`, `/liberar <dias>`, cupom e indicação. **Cupom para 10
usuários não precisa de tabela** — dict no `.env` resolve e evita infra para
um problema que ainda não existe.

## Ordem recomendada
1. **Agora (medição, não feature):** log de custo ✅ + `/quem` ✅
2. **Durante o piloto: cobrar nada.** Dez convidados não validam preço;
   validam se a ferramenta presta. O que o piloto tem de produzir é o
   **custo real por aluno engajado**
3. **Depois:** roteamento Opus/Haiku · rail Pix + webhook · comandos de promoção

Relacionado: [[Custo de LLM]] · [[Comandos do Bot]] ·
[[Segurança e Compliance]]
