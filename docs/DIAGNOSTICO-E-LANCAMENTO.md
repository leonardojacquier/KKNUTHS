# KKNuths ♠ — Diagnóstico profundo e plano de lançamento

*06/09/2026. Quatro auditorias paralelas (produto, confiabilidade, arquitetura,
custos) + medição direta do banco de produção (`kknuths-poker`). Tudo que é
número aqui foi medido; tudo que é estimativa está marcado.*

---

## 0. Resumo executivo

**O produto está bom. O piloto está morrendo.** As duas coisas ao mesmo tempo.

- **Uso real caiu 10× em 3 semanas**: de 204 ações/semana (fim de julho) para
  11 na semana passada. Entradas de mão: de 59/semana para 4.
- **De 13 alunos externos, 6 nunca mandaram uma mão.** Dos 7 que mandaram,
  **2 voltaram depois do 7º dia**. Hoje existe **1 usuário pesado** (Ricardo,
  232 mãos, série PDQ) e 1 leve (alvgomes19).
- **A causa não é custo nem cota** (ninguém esgotou; o piloto inteiro custou
  US$41 em 10 semanas). É produto: **todo comando de perfil e evolução rejeita
  o jogador de clube** — exige um arquivo de sessão que PPPoker/Suprema não
  exportam. Depois das primeiras análises, não há para onde voltar além do
  quiz das 19h.
- **O núcleo funciona e é forte**: link → análise com selo e placar → filme →
  conversa → treino. 1.695 testes. Deploy com portão. Custo por análise
  ≈ US$0,06.
- **Cobrar hoje é impossível**: não existe `/assinar`, o webhook do Stripe não
  rebaixa quem cancela, e o preço está em três lugares com três valores.
- **Dois buracos que não podem esperar o lançamento**: a cota só cobre
  upload — conversa, simulador e o solver de 75 s de CPU são ilimitados; e
  quatro chaves de API passaram por chat e a rotação está pendente desde
  15/08.
- **Recomendação**: **não lançar agora.** Duas semanas consertando o que mata
  a retenção, duas semanas montando cobrança, e relançar pelo canal que já
  existe (a série PDQ do Ricardo) com um plano só: **Pro R$49,90**.

---

## 1. Uso real — medido no banco

### 1.1 Quem são os 15 usuários

| | n | quem |
|---|---|---|
| Internos | 2 | Leo (dono), Lorenzo (filho) |
| Externos que mandaram ≥1 mão | 7 | Ricardo Farah, alvgomes19, Paulo Pinheiro, dscholze1979, ANTONIO PIRES, Antony S, Odilon Godeje |
| Externos que **nunca** mandaram mão | 6 | ttbahr, SivioFernandes, Raphael, Luiz Fabiano, Eder Rosa, Lucas Carvalho |

Os 6 que nunca mandaram entraram na onda de 05–09/08, responderam 0–2 quizzes
e sumiram em ≤4 dias.

### 1.2 O funil

```
13 externos cadastrados
 └─ 7 mandaram uma mão (54%)
     └─ 3 voltaram com mão entre D2 e D7 (43%)   Ricardo, alvgomes, dscholze
         └─ 2 voltaram entre D8 e D30 (29%)       Ricardo, alvgomes
             └─ 1 ativo hoje com mãos            Ricardo
```

**Cota esgotada: 0 eventos.** Ninguém saiu por limite.

### 1.3 A curva

| semana | usuários que USARAM | ações reais | mãos enviadas | conversas |
|---|---|---|---|---|
| 20/07 | 3 | **204** | 59 | 61 |
| 27/07 | 4 | 162 | 59 | 46 |
| 03/08 | **6** | 126 | 38 | 41 |
| 10/08 | 5 | 85 | 21 | 14 |
| 17/08 | 4 | 119 | 20 | 82 |
| 24/08 | 5 | 27 | 4 | 14 |
| 31/08 | **2** | **11** | 4 | 0 |

"Usuários ativos" pelo total de eventos diz 9/semana — mas 7 desses eventos
por usuário são o quiz das 19h sendo *enviado*. Tirando o passivo, sobram 2.

### 1.4 O que é usado

| feature | usos | usuários | leitura |
|---|---|---|---|
| quiz diário (enviado → respondido) | 379 → 121 | 13 | **32% de resposta** — a feature de maior alcance |
| follow-up (conversa) | 280 | 6 | forte em quem usa; concentrado |
| upload/replay | 275 | 9 | 164 são replay PPPoker de **3 usuários** |
| /treino, /simular, /stats, /range… | 9–16 cada | 2–6 | cauda longa, quase ninguém |
| /ask | 0 | 0 | — |

**O replay do PPPoker é a feature-assassina e é usado por 3 pessoas.** O
quiz é o único ponto de contato diário com os outros 10.

### 1.5 Quando usam

Picos: sexta 9h, segunda 10h, quinta 6h, sábado 17h. **É revisão de manhã
seguinte à sessão**, não durante o jogo. Isso valida a tese "pós-sessão, sem
RTA" com dado real — e diz quando mandar o quiz (hoje vai às 19h).

### 1.6 Custo real

| | total 10 semanas | últimos 30 dias |
|---|---|---|
| Opus 4.8 (529 chamadas) | US$29,07 | US$8,38 |
| Sonnet 5 (267 chamadas) | US$12,00 | US$11,41 |
| Haiku 4.5 (253 chamadas) | US$0,40 | US$0,20 |
| **Total LLM** | **US$41,47** | **US$20,00** |

US$0,055/chamada Opus, US$0,045 Sonnet. **O custo do LLM não é uma
variável do negócio nesta escala** — é menor que um buy-in por mês para o
piloto inteiro.

### 1.7 Falhas vistas pelo aluno

- `followup_failed`: 16 em 280 (5,7%); `upload_failed`: 12 em 275 (4,4%).
- Rajadas de **Bad Gateway** em 23, 24 e 26/08 (6 seguidos cada) e
  `httpx.ReadError` hoje (06/09) — API upstream, não código nosso.
- Nota do juiz: média histórica **5,94/10** (n=91) — mas ver §3: até 26/08 o
  próprio juiz fabricava cortes e descontava por eles.

---

## 2. O produto — o que existe, o que está ligado, o que mente

### 2.1 O núcleo está inteiro

Link de replay (PPPoker/Suprema) → análise com selo ✅🟡❌ e placar street a
street → filme da mão → botões (🎈 simplificar / 🔁 simular / 📖 range) →
conversa com 33 ferramentas de matemática → quiz e treino a partir das
próprias mãos. Tudo ligado, testado, e o primeiro valor chega em <1 minuto
sem gastar LLM (mão-demo + drill determinístico).

### 2.2 O segundo andar rejeita o cliente-alvo

`FONTES_COMPLETAS = {txt, text, csv, phh, pdf}` (`stats.py:21`). Replay e
print ficam **fora de toda estatística de frequência** — correto pelo METODO
§1 (viés de seleção). Mas a consequência de produto é esta:

| comando | o que o aluno de clube ouve | é verdade? |
|---|---|---|
| `/stats` | "Ainda não tenho mãos suas. Envie um arquivo" (`handlers.py:296`) | **Falso** — ele mandou 50 replays |
| `/estilo` | "Preciso de ~10 mãos suas. Envie uma sessão" (`:383`) | Enganoso — 10 replays não contam |
| `/evolucao` | "cada lote vira um ponto" (`processing.py:1418`) | **Falso** — replay nunca vira ponto |
| `/foco` | "só tenho replay/print — manda o arquivo do torneio" (`:1510`) | Honesto, pede o impossível |
| `/relatorio` | "mínimo 8 mãos de torneio" | Inatingível no clube |

O manual promete `/stats` com leaks e Tilt Detector (`MANUAL.md:166`). Para
quem joga em clube, **nenhum desses quatro comandos funciona nunca**. É o
primeiro comando do menu, e o aluno testa depois da terceira análise — o
produto nega o que acabou de aceitar. Isso explica o funil do §1.2 melhor
que qualquer outra hipótese.

### 2.3 Gatilhos que o aluno não conhece

- **Lobby**: a foto da estrutura só é lida se a legenda tiver
  `lobby|estrutura|blinds|níveis|preparar` (`handlers.py:1141`). O docstring
  diz "o manual e o /preparar ensinam a legenda" — **nenhum dos dois ensina**.
  Sem a palavra, gasta cota e devolve "print ilegível".
- **O botão "Enviar minhas mãos"** não ensina onde fica o Compartilhar do
  PPPoker e não cita Suprema (`handlers.py:213-223`). O passo a passo só
  aparece na mensagem de *falha*.
- **Mão narrada** (texto ou voz): cai em "coaching geral", **não é persistida**
  — sem filme, sem simular, não vira quiz. É o caminho que o próprio fallback
  recomenda ("ou descreve").
- **ICM "automático"**, blockers, PKO, população: existem só como *tool* que o
  modelo decide chamar — e **não há registro de quais tools foram chamadas**.
  Não dá para saber se o motor de população já produziu valor alguma vez.

### 2.4 O que não é medido

Nada mede se o veredito está **certo**, se o aluno **voltou** depois de uma
análise, se ele **leu**, ou se **fez a jogada certa depois**. O juiz mede
forma e clareza. `cota_esgotada` existe e ninguém cruza com sumiço.

---

## 3. Confiabilidade

### 3.1 O histórico conta uma coisa só

Os comentários do código guardam **25 incidentes** entre 09/07 e 22/08, e 60
scripts em `deploy/oneshot/` são o diário de reparos em produção. Agosto foi
dominado por incidentes de LLM, e **quase todos têm a mesma forma: o sinal
existia (`stop_reason`, código 400, exceção) e ninguém lia.** A causa raiz
da semana de cortes (21/08) foi um parâmetro omitido — `thinking` ligado por
padrão no sonnet-5 — que consumia o orçamento inteiro antes de escrever.

Os que mais custaram: 275 restarts em laço com o bot mudo (27/07); crédito
Anthropic zerado e o dono sabendo "xingando" (27/07); um aluno recebendo
"KK só perde para QQ ou AA" (07/08); site caído com deploy anunciando
sucesso (09/08); portão `publicavel` invertido com 971 testes passando
(09/08); meia frase entregue como análise e **rollback às cegas** (16/08);
torneio de 192 mãos com 16 lotes cortados e o aluno como único sensor
(18/08).

### 3.2 O buraco de custo que ninguém fechou (crítico)

**A cota só cobre `process_upload`.** Conversa (`process_followup`), `/simular`,
`/preparar`, `/dossie`, `/leitura`, `/spot` e `/ask` não passam por
`check_quota`. Cada mensagem de texto = até 1.200 tokens de saída + 5
rodadas de ferramenta, e a tool `solve_river` roda CFR+ **até 75 s de CPU**.
Não existe rate-limit por usuário. Um aluno free com 0 análises restantes
tem LLM e CPU ilimitados conversando — e `texto_cota_esgotada`
(`quota.py:161-169`) **o convida a fazer exatamente isso**.

Hoje o freio é a velocidade de digitação de 14 pessoas. Não dá para vender
plano com esse buraco aberto.

### 3.3 Falhas que o aluno sente e o dono não vê

| sev. | onde | o que acontece |
|---|---|---|
| alto | `processing.py:683` | cota consumida **antes** do envio; se o Telegram falhar, dólar gasto + análise gravada + nada entregue, sem evento distinto |
| alto | `db/repository.py:20-35` | Supabase fora → toda falha vira `None` e log no pm2; **nenhum alerta ao admin** |
| alto | `sonda_recebimento.py:222` | a sonda testa o *token* (`getMe`), não o *processo* — o laço de 275 restarts passaria nela |
| alto | `vps_deploy.sh:63` | `pm2 restart` a cada push mata análises em voo; com deploy por commit (12 num dia em 16/08), é rotina |
| médio | `llm.py:2006,2077` | `plano_c` e `analise_cortada` gravados com `telegram_id=0` — não dá para saber **qual aluno** recebeu o plano C |
| médio | `speech.py`, `embeddings.py` | chave OpenAI morta → voz e RAG degradam em silêncio; `saude.py` só cobre Anthropic |
| médio | `daily_quiz.py`, crons | envio falho retorna `False` e some; sem *dead-man's-switch* para cron ausente |

### 3.4 Deploy

- A suíte leva **9m33s** neste container (1.695 testes); os scripts assumem
  "~3 min". Um push leva 4–12 min para chegar, na **mesma CPU** que serve o
  bot e outros dois sites.
- **Rollback só existe para "não subiu".** Código que passa nos testes e
  está errado exige revert + ciclo completo — foi o 16/08. Não há "voltar
  para o último OK".
- Venv de produção é mutado (`pip install`) **antes** do portão de testes.
- Redis está em `requirements.txt` e `config.py` e **nunca é importado**.

### 3.5 Segurança

- Chaves de Anthropic, OpenAI, BotFather e Supabase **passaram por chat**;
  a rotação está pendente desde 15/08 (`OPERATIONS.md:131`). O repo era
  público.
- Dois oneshots ainda no repo montam `admin?key=$ADMIN_TOKEN` e mandam por
  Telegram — query string vai para o log do Caddy.
- `ADMIN_ID` hardcoded em ≥8 arquivos.
- Comandos de admin conferem ID (ok). Webhook não autenticado já foi
  removido. Links de replay usam allowlist de hosts — sem SSRF pelo que
  foi lido. Injeção de prompt: sem defesa explícita, mas as tools com efeito
  são escopadas ao próprio aluno.

### 3.6 O que quebra primeiro com 10× alunos

1. Custo e CPU da conversa sem cota (o solver serializa no único processo).
2. Um VPS, um processo, restart a cada commit — cada push vira incidente.
3. `bot_events` como tabela de tudo com janelas fixas que truncam calado.
4. Alarme de um destinatário só — vira ruído e o dono desliga.
5. CDNs de clube sem retry — o PPPoker trocando domínio numa noite de
   torneio produz dezenas de falhas e o primeiro a saber é o aluno.

---

## 4. Arquitetura e código

### 4.1 O que está sólido

- 1.695 testes, 120 arquivos de teste para 112 módulos.
- Deploy com portão: pytest roda **no clone** antes de tocar produção
  (`auto_update.sh`), com o incidente que motivou a ordem documentado.
- Quase zero `TODO` real; 0 `except:` nu.
- METODO.md é um contrato de verdade, com portões de amostra em escrita e
  leitura.

### 4.2 Os riscos reais, por impacto no aluno

**1. Contaminação entre alunos (crítico, piora com escala).**
`llm.py` guarda em variáveis de módulo o resultado da última chamada:
`LAST_VISION_CHECK:3007`, `LAST_SIMPLIFY_REASON:2428`,
`LAST_LOBBY_CHECK:3316`. `handlers.py` tem **85** `asyncio.to_thread` —
threads reais. Dois alunos mandando print ao mesmo tempo → o B pode receber
"li A♠K♦ — confere?" com as cartas do A. O padrão certo (`ContextVar`) já
existe no mesmo arquivo (`_TOOL_CHAT:1298`). Com 14 alunos é raro; com 100
é semanal.

**2. Portões que falham abertos e calados.** `licao_qualidade.py:138` — o
guarda contra mentira de poker na lição diária quebra → `pass` → a lição
vai para todos. `guarda_fatos.py:123` — a conferência de equity quebra →
`continue` → a afirmação sai sem conferir. "Conferência é garantia" só vale
se a conferência acusa quando ela mesma quebra.

**3. Entrega perdida sem rastro.** `handlers.py:2270,2279` — gráfico ou
relatório mão a mão falha ao enviar → `pass`, e o documento já foi removido
da fila. O aluno pagou a análise e o PDF sumiu sem mensagem nem evento.
`processing.py:845` — persistência da conversa falha em silêncio → no
próximo deploy, "não achei a mão desta conversa".

**4. `processing.py` é o deus-módulo.** Fan-out 60 (importa 54% do sistema),
fan-in 10, 11 ciclos resolvidos por import tardio, e `analysis/` + `agent/`
+ `db/` dependem de `bot/` em 26 pontos. O teto de 3.600 linhas segura
tamanho, não acoplamento.

**5. Números degradados sem marca.** `db/repository.py:349` grava VPIP cru
na história quando o shrinkage falha. `pushfold.py:115` entrega tabela
estática como "aprox. Nash" se o solver quebrar, sem log.

**6. Código morto perigoso.** `app/repository.py`: 734 linhas, zero
referências, e é a cópia **sem** o portão `publicavel` do METODO §1.

**7. Configuração.** `ADMIN_TELEGRAM_ID` está hardcoded em 3 lugares além
da env (`saude.py:26`, `licao_envio.py:19`, `notify.py:23`). `ARQUITETURA.md`
está 20% desatualizado (diz 99 módulos; são 112).

---

## 5. Custos e economia

### 5.1 Custo por operação (estimado, Sonnet 5, cache quente)

| operação | US$ | R$ |
|---|---|---|
| 1 análise de mão avulsa | 0,06 | 0,32 |
| 1 follow-up | 0,03 | 0,16 |
| 1 torneio de 150 mãos (25 lotes) | 0,51 | 2,75 |
| 1 leitura de print | 0,02 | 0,11 |
| juiz + crons | ≈ 1–3/mês | |

Aluno realista (15 análises + 30 conversas): **US$2,40 ≈ R$13/mês**.
Pior caso free=50 com torneios: US$31 ≈ R$170. **A cota é a alavanca de
margem; o modelo não.**

### 5.2 Três correções antes de qualquer número ir pra fatura

1. `custo.py:36` grava Sonnet a US$3/15; a tabela pública é 2/10. O `/quem`
   superestima Sonnet em ~50%.
2. `custo.py:44` usa escrita de cache 1,25×; o app pede TTL de 1h (2×).
3. `.env.example:6` ainda diz `ANALYSIS_MODEL=claude-opus-4-8`. **Confirmar
   o `.env` do VPS** — se estiver em Opus, o custo real é 2,4× o estimado.

### 5.3 Cobrança: o que existe e o que falta

Existe: checkout Stripe em modo assinatura, webhook com assinatura
obrigatória, tabelas `users.plan` e `subscriptions`, script que cria os
produtos.

Falta, em ordem de gravidade:
1. **Nenhum `/assinar`** — o aluno não tem como chegar ao checkout.
2. **Cancelar não rebaixa o plano** (`stripe_service.py:103-119` só grava a
   assinatura; `users.plan`, que a cota lê, não muda). Cancelou → segue
   ilimitado.
3. `user_id` nos eventos de assinatura vem de metadata que o checkout não
   põe na subscription → `NOT NULL` estoura.
4. `invoice.payment_failed` não é tratado → inadimplência não bloqueia.
5. Sem Pix, sem anual. Zero teste de evento real do Stripe.
6. Preço em 3 lugares: BP diz 29,90/69,90; `setup_stripe.py` diz 49/129;
   vault diz 39–59.
7. `PUBLIC_BASE_URL` default `localhost:8000` → o retorno do checkout aponta
   pra lugar nenhum.
8. **Follow-ups não consomem cota** (`quota.py:152`). Vender "conversa
   ilimitada" sem medir é promessa sem medidor.

### 5.4 Unit economics (estimado; opção A do §8; 20% pagantes)

| | 14 alunos | 50 | 200 |
|---|---|---|---|
| pagantes | 3 | 10 | 40 |
| receita/mês | R$200 | R$599 | R$2.296 |
| variável (LLM + taxas) | R$84 | R$250 | R$946 |
| fixo (VPS, Supabase, crons) | R$129 | R$129 | R$281 |
| **resultado** | **−R$13** | **+R$220** | **+R$1.069** |
| margem bruta | 58% | 58% | 59% |

Sensibilidade: manter o free em 50–100 análises faz o resultado em 200
alunos virar negativo. Voltar para Opus leva o break-even para ~200.

---

## 6. Diagnóstico — por que o piloto está morrendo

Juntando as quatro auditorias com o banco:

1. **A onda de agosto entrou sem porta.** 6 de 13 nunca mandaram mão. O
   `/start` tem 4 botões e uma mão-demo, mas o botão "Enviar" não ensina onde
   fica o link do PPPoker. Quem não sabia, saiu em 4 dias.
2. **Quem mandou, bateu no segundo andar.** `/stats`, `/estilo`, `/evolucao`,
   `/foco` — os comandos que dariam motivo para voltar — respondem "não tenho
   mãos suas" para quem só tem replay. 5 de 7 pararam antes do D8.
3. **Nada puxa a segunda mão.** Depois da análise, os botões são sobre
   *aquela* mão. Não há "manda a próxima". O quiz das 19h é o único gancho
   diário — e vai na hora errada (o uso real é de manhã).
4. **O único retido tem um ritual.** Ricardo manda a série PDQ toda semana.
   Ele não precisa de gancho — o torneio é o gancho. **Isso é o canal.**
5. **Custo, cota e confiabilidade não são a causa.** Ninguém esgotou cota;
   falha vista pelo aluno é ~5%; o piloto custou US$41.

---

## 7. Plano de lançamento

Princípio: **não lançar para o público o que já provou que perde 70% dos
alunos em uma semana.** Primeiro fechar o funil com quem já está dentro,
depois abrir.

### Fase 0 — Estancar (semanas 1–2) · *critério de saída: 2 alunos externos com mão no D8*

**Produto (o que mata retenção):**
1. `/stats`, `/estilo`, `/evolucao`, `/foco` **úteis para replay-only**:
   separar "perfil de decisões" (EV por decisão, categorias de erro, custo
   total dos erros, taxa de acerto no quiz — tudo já calculado) do "perfil
   de frequência" (VPIP, que exige sessão). A mensagem vira "das suas 23
   mãos: X; para VPIP preciso de sessão inteira". *8–12 h.* Métrica: eventos
   "não tenho mãos" para quem tem ≥1 mão → 0.
2. **Ensinar o link** no botão "Enviar" e no manual: PPPoker → mão →
   Compartilhar → cola aqui; Suprema idem; foto do lobby com a palavra
   "lobby". *1 h.* Métrica: % de primeiros uploads que são replay.
3. **Botão "📤 Mandar outra mão"** depois de toda análise; `/start` sem
   "mão de teste" para quem já tem mão. *1–2 h.* Métrica: 2º upload em 48h.
4. **Quiz na hora certa**: 8h em vez de 19h (o uso é de manhã). *0,5 h.*
   Métrica: taxa de resposta (hoje 32%).
5. **Logar as tools chamadas** por análise. *1–2 h.* Sem isso não dá pra
   saber quais motores valem o custo de manutenção.

**Confiabilidade (o que não pode ir pra mais gente):**
6. `LAST_*` de `llm.py` → `ContextVar`. *2–3 h.* Contaminação entre alunos
   zerada antes de haver alunos suficientes para ela aparecer.
7. Portões que falham calados (`licao_qualidade:138`, `guarda_fatos:123`)
   passam a **acusar** quando quebram. *1 h.*
8. Entrega perdida (`handlers.py:2270,2279`, `processing.py:845`) ganha
   `log_event` e mensagem ao aluno. *1 h.*
9. Apagar `app/repository.py`. *15 min.*

**Operação (o que o dono precisa enxergar):**
10. Sonda passa a testar o **processo** (último evento humano / heartbeat do
    bot), não só o token. *1 h.* O laço de 275 restarts vira alerta em 1 h.
11. Supabase fora → alerta ao admin (hoje é `None` calado). *0,5 h.*
12. `plano_c` e `analise_cortada` gravam o `telegram_id` do aluno. *0,5 h.*
13. Cota consumida **depois** da entrega, não antes. *1 h.*

**Dinheiro (fechar o buraco antes de abrir a loja):**
14. **Cota na conversa.** `process_followup`, `/simular`, `/preparar` passam
    por `check_quota` com peso próprio (ex.: 5 mensagens = 1 análise), e o
    `solve_river` ganha limite por usuário/dia. *3–4 h.* **Sem isto não há
    plano vendável** — o custo é ilimitado por construção.
15. Corrigir `custo.py` (tabela e cache), conferir `.env` do VPS. *1 h.*
16. Baixar `FREE_MONTHLY_ANALYSES` para 10; manter `piloto`=100 só para os
    atuais. *5 min.*
17. **Rotacionar as quatro chaves** que passaram por chat (Anthropic, OpenAI,
    BotFather, Supabase) e apagar os dois oneshots que mandam `ADMIN_TOKEN`
    por Telegram. *1 h.* Pendente desde 15/08; antes de receber dinheiro.
18. Tirar Redis de `requirements.txt` e `config.py`. *10 min.*

### Fase 1 — Cobrar (semanas 3–4) · *critério de saída: 1 pagamento real processado de ponta a ponta*

19. **Rail**: Stripe com Pix habilitado (menor mudança de código) — ou
    Mercado Pago/Asaas se o Pix do Stripe não estiver disponível na conta.
20. `/assinar` gera o link e grava evento; `/plano` mostra vencimento.
21. Webhook: `subscription_data.metadata`, rebaixar `users.plan` em
    cancel/past_due/failed, tratar `invoice.payment_failed`.
22. Teto real nos planos pagos (`quota.py:22` hoje é ilimitado): torneio >8
    mãos vale 3 análises.
23. Testes com eventos Stripe construídos (`construct_event` mockado).
24. **Preço num lugar só.**
25. **Rollback de um comando** ("voltar para o último OK") e snapshot fora
    de `/tmp`. Cobrar de alguém exige poder desfazer um deploy ruim em 1
    minuto, não em um ciclo de 12.
26. Converter os dois retidos com **preço de fundador** (50% vitalício):
    Ricardo e alvgomes19. Métrica: 2 pagantes.

### Fase 2 — Relançar (semanas 5–8) · *critério de saída: 30 usuários, 6 pagantes, D30 ≥ 30%*

27. **Canal 1 — a série PDQ.** Ricardo já manda toda rodada. Oferecer ao
    organizador: análise da mão da semana para o grupo, card "quem acerta o
    spot?" (já existe, com `?start=card` medindo origem). O torneio é o
    ritual; o bot entra nele.
28. **Canal 2 — Suprema.** O parser existe; 2 usuários usaram. Um clube da
    Suprema com o mesmo formato.
29. **Materiais**: folder, manual e card já existem e estão alinhados.
    Refazer o manual **depois** do item 1 (hoje promete `/stats` que não
    funciona para o público).
30. **Onboarding guiado**: 3 mensagens nos 3 primeiros dias (D0: manda seu
    primeiro replay assim; D1: o que o placar significa; D3: seu primeiro
    perfil de decisões). Só depois disso o quiz entra.
31. **Painel semanal para o dono** (já existe `anomalias.py` e `situacao_do_aluno`):
    acrescentar o funil do §1.2 e D7/D30 por coorte.

### O que NÃO fazer agora
- Não competir com biblioteca de solver (COMPARATIVO §3).
- Não abrir Premium até alguém bater o teto do Pro.
- Não lançar anúncio pago: o funil perde 70% em uma semana; anúncio
  compraria churn.
- Não mexer no teto do pós-placar sem amostra.

---

## 8. Modelo de cobrança — a decisão

O agente de custos comparou três opções (assinatura por faixa; créditos
pré-pagos via Pix; freemium com ilimitado) e recomendou a primeira. Os dados
de uso do §1 apontam para uma versão **mais simples** dela:

**Um plano pago só no lançamento.**

| | Free | **Pro** |
|---|---|---|
| preço | R$0 | **R$49,90/mês** (R$499/ano) |
| análises | 10/mês | 60/mês (torneio >8 mãos = 3) |
| conversa | 20 msgs/mês | 200 msgs/mês |
| quiz diário, treino, /range, /spot | sim | sim |
| relatório mão a mão, dossiê, /preparar | não | sim |
| fundador (piloto atual) | — | R$24,90 vitalício |

**Por quê:**
- **Ninguém no piloto passou de 10 análises/mês além do Ricardo (40).** 60 é
  teto confortável para 100% dos casos vistos e protege o pior caso de §5.1.
- R$49,90 é **metade de um buy-in** de clube e ~3× abaixo do GTO Wizard de
  entrada. Margem realista 74%; no teto do plano, −76% — raro, e o teto
  protege.
- **Um plano = uma decisão para o aluno, um caminho de código, um preço para
  manter.** Premium entra quando alguém bater os 60 — hoje esse alguém não
  existe.
- Pix é obrigatório: o público é celular + clube.
- Recorrência: o BUSINESS_PLAN mede MRR; créditos pré-pagos dariam LTV menor
  e churn invisível.

**Condições para virar a chave** (todas da Fase 0–1): follow-up medido,
cancelamento rebaixa plano, preço num lugar só, `.env` conferido.

---

## 9. Esta semana

Ordem, com esforço:

| # | o quê | h | efeito |
|---|---|---|---|
| 1 | **Rotacionar as 4 chaves** + apagar os oneshots do `ADMIN_TOKEN` | 1 | pendente desde 15/08; fecha a exposição |
| 2 | **Cota na conversa** + limite do solver por usuário | 4 | fecha o custo ilimitado |
| 3 | Ensinar o link no botão "Enviar" + manual | 1 | fecha a porta por onde 6 saíram |
| 4 | `LAST_*` → `ContextVar` | 3 | contaminação entre alunos zerada |
| 5 | Sonda testa o processo; Supabase fora alerta | 1,5 | o dono sabe antes do aluno |
| 6 | Portões acusam quando quebram; cota depois da entrega | 2 | conferência volta a garantir |
| 7 | Apagar `app/repository.py`; tirar Redis | 0,5 | duas minas a menos |
| 8 | `custo.py` + conferir `.env` do VPS | 1 | o `/quem` passa a dizer a verdade |
| 9 | Quiz às 8h; botão "mandar outra mão" | 2 | dois ganchos de retorno |
| 10 | **`/stats` para replay-only** | 10 | o motivo de voltar |

Total ≈ 26 h. O item 10 é o maior e o mais importante para retenção; os
itens 1 e 2 são os que não podem esperar o lançamento — um é exposição, o
outro é custo sem teto. Os outros oito cabem em três dias.

---

*Fontes: banco `kknuths-poker` (queries em 06/09); relatórios dos agentes de
produto, arquitetura, custos e confiabilidade (esta sessão); `MANUAL.md`,
`BUSINESS_PLAN.md`, `OPERATIONS.md`, `backend/docs/METODO.md`,
`docs/COMPARATIVO-GTO-WIZARD.md`. Preços de API: tabela Anthropic
2026-06-24 — confirmar na fatura.*
