# KKNuths ♠ vs GTO Wizard — onde ganhamos, onde perdemos

*Levantado em 23/08/2026. Lado deles: pesquisa pública (ver Fontes). Lado
nosso: leitura do próprio código, não da propaganda.*

---

## 0. O boato do WSOP: é verdade, mas ao contrário

A história que chegou foi *"teve um evento do WSOP em que usaram a ferramenta
de forma online"*. Isso aconteceu — e não é escândalo, é **patrocínio**.

| O que é verdade | O que não é |
|---|---|
| O WSOP nomeou o GTO Wizard **Parceiro Oficial de Treinamento** da série de 2026 (Paris/Horseshoe Las Vegas), com marca no palco principal. | Não houve jogador usando solver na mesa nesse acordo. |
| Nas mesas finais, a **transmissão** roda análise de solver ao vivo — o gráfico *"Optimal Play"*, que mostra a jogada de equilíbrio e se o jogador seguiu ou desviou. | Isso é para o **público**, não para quem está jogando. |
| O WSOP proíbe expressamente solver na mesa: pena até desqualificação e expulsão. | Ninguém foi pego usando GTO Wizard num evento do WSOP nessa história. |

Onde há caso real de solver em tempo real, é **outro** assunto: o WPT Gardens
(2023, Andrew Esposito usando GTO Wizard na mesa) e as acusações de RTA online
— nas quais o GTO Wizard aparece do lado **da fiscalização**, não do crime: o
*Fair Play Check* dele é usado por operadores, e a parceria com a GGPoker
(mar/2025) baniu 31 contas na primeira leva, com perda de elegibilidade para
o WSOP.

**Por que isso importa comercialmente para nós:** o mercado acabou de
normalizar, em rede nacional, a ideia de que *"a resposta certa é calculada"*.
Isso valida a nossa tese — **a IA não faz a conta, quem calcula é a
matemática** — e reforça a nossa única linha vermelha: **análise pós-sessão,
sem RTA**. Estamos do lado que o WSOP aprova.

---

## 1. Onde estamos à FRENTE

### 1.1 Nós lemos a mão que o aluno realmente jogou

Este é o item que mais vale, e é estrutural. O jogador brasileiro de clube
joga em PPPoker, Suprema, ClubGG, PokerBros — apps que **não exportam hand
history** no formato que um solver importa. Ele tem um *link de replay* e um
*print da tela*.

O KKNuths engole os quatro caminhos:

- **link de replay** do PPPoker e da Suprema — puxa a mão sozinho do CDN;
- **print da mesa** — leitura por visão;
- **arquivo** de hand history;
- **texto colado ou narrado** ("77 no CO, 30bb, flop A♦7♣9♣…").

No GTO Wizard, para estudar essa mesma mão, o aluno tem que **remontar o spot
à mão** na interface. É a diferença entre "cola o link" e "reconstrói o
board, o pote, o stack efetivo e os dois ranges antes de ver qualquer coisa".

### 1.2 Veredito em português, não uma grade de frequências

A saída deles é uma matriz 13×13 com percentuais — o aluno precisa **já saber
ler solver** para extrair uma decisão. A nossa saída é um placar street a
street com o número preso ao veredito: *"abriu 2.8bb: com 18.7bb é território
de jam — jammar rende +1.49bb"*. Quem tem 14 alunos de clube sabe qual das
duas o aluno usa na terça-feira à noite.

### 1.3 Exploit sobre a população DELE (`population.py`)

Solver dá equilíbrio. Equilíbrio é a resposta certa contra quem joga certo —
e ninguém no clube dele joga certo. Nós medimos, das mãos que o próprio aluno
subiu, com que frequência o *field* folda para agressão em cada street, e
cruzamos com o breakeven do blefe: *"o field folda 62% pro bet de turn; blefe
de 2/3 pote precisa de 40% — aposte"*. **Esse dado é proprietário e nenhum
solver de prateleira tem** — porque ele não existe fora da base do aluno.

### 1.4 Tilt Detector — vazamento mental em número (`mental.py`)

Kahneman em código: gatilho de pote grande (15bb), janela de 8 mãos depois,
desvio de 8 pontos de VPIP contra a **linha de base do próprio jogador**, com
shrinkage bayesiano para meia dúzia de mãos agitadas não virar diagnóstico.
GTO Wizard é um motor de teoria de jogos — **não faz leitura comportamental
nenhuma**. Aqui não estamos à frente: estamos em outra categoria.

### 1.5 Ele acompanha o aluno; eles têm uma biblioteca

Evolução por indicador ao longo do tempo, leaks, plano de estudo, dossiê de
vilão, banca/risco de ruína, drills tirados das mãos DELE, o filme da mão.
GTO Wizard é uma biblioteca que você consulta. O KKNuths é um coach que
assistiu à sua sessão.

### 1.6 Atrito zero e preço

Telegram. Sem app, sem assinatura para escolher, sem curva de interface.
O GTO Wizard em 2026 vai de ~US$ 26 a ~US$ 206/mês conforme o plano.

### 1.7 ICM entra sozinho, na mão real

ICM Malmuth-Harville com bubble factor e limiar de call com dead money já
aplicado à mão que ele mandou — não como uma calculadora separada que ele
precisa lembrar de abrir.

---

## 2. Onde estamos ATRÁS — sem maquiar

### 2.1 Escala da biblioteca de soluções — **a maior diferença**

Eles **pré-calculam** milhões de spots. Em março/2026 lançaram as *Single Size
Solutions*, que multiplicaram a biblioteca por ~50: todo spot pré-flop passou
a ter árvore pós-flop completa. Resposta instantânea e exata para o spot
padrão.

Nós **resolvemos na hora**, com CFR+ multi-street de verdade (`river_solver.py`)
— mas com abstração declarada: **uma raise por street**, poucos tamanhos de
aposta, e teto de combos (900 no river, 420 no turn/flop) por custo. Para o
spot padrão, a resposta deles é mais exata e chega mais rápido. Isso é fato.

### 2.2 Pós-flop multiway

Eles têm solver pré-flop multiway para até 9 jogadores no navegador. Nós
temos **equity** multiway (`multiway_equity.py`), que é outra coisa —
equilíbrio multiway não temos.

### 2.3 Variantes

Eles têm solver de **PLO**. Nós somos **só NLHE**.

### 2.4 Interface de estudo

Navegar range vs range, comparar tamanhos, rodar drill em volume — isso pede
uma aplicação web. Um 13×13 no Telegram resolve a consulta pontual, não a
sessão de estudo de duas horas.

### 2.5 Marca e distribuição

Parceiro oficial do WSOP, marca no palco principal, gráfico na transmissão
nacional. Nós temos 14 alunos. Não há comparação — e não deveria haver: são
estágios diferentes.

### 2.6 Base de comparação

Com milhões de usuários eles conseguem benchmark ("você acerta X% dos spots
contra a média"). A nossa base é pequena demais para isso ainda — e todo
número nosso de população carrega o tamanho da amostra justamente por isso.

---

## 3. Onde NÃO devemos competir

**Não devemos tentar virar uma biblioteca de solver.** Perderíamos por
definição: é capital computacional pré-pago, e eles têm anos de vantagem.

O terreno onde eles **não podem** nos alcançar sem mudar de produto é:

1. ler o link do clube brasileiro;
2. falar português de coach;
3. conhecer o field específico do aluno;
4. ler o comportamento dele, não só as cartas;
5. acompanhar a evolução ao longo dos meses.

---

## 4. A frase de posicionamento

> **GTO Wizard é a biblioteca. KKNuths é o coach que assistiu à sua sessão.**
>
> Eles te dão a resposta certa para um spot que você precisa remontar.
> Nós lemos a mão que você jogou, no clube em que você joga, contra o field
> que você enfrenta — e explicamos em português, com o número na frente.

E a linha que o WSOP acabou de nos dar de graça:
**análise pós-sessão, sem RTA — do lado que o WSOP aprova.**

---

## 5. Ressalvas deste levantamento

- Os números do lado deles vêm de **busca pública**; o proxy de rede bloqueou
  o acesso direto a `blog.gtowizard.com`, `pokernews.com` e `poker.org`, então
  não abri as fontes primárias. Os preços em especial divergem entre fontes
  (uma lista Starter US$ 39 / Premium US$ 99 / Elite US$ 129+; outra, faixa de
  US$ 26 a US$ 206). **Confirmar antes de usar preço em peça comercial.**
- O lado nosso é leitura direta do código (`app/analysis/`), não do manual.

## Fontes

- [WSOP Names GTO Wizard Official Poker Training Partner for 2026 Series — PokerNews](https://www.pokernews.com/news/2026/06/wsop-gto-wizard-official-poker-training-partner-2026-partner-51512.htm)
- [GTO Wizard at the 2026 World Series of Poker](https://blog.gtowizard.com/gto-wizard-at-the-2026-world-series-of-poker/)
- [GTO Wizard New Pricing & Plans 2026 — PokerNews](https://www.pokernews.com/news/2026/03/gto-wizard-subscription-plans-new-features-pricing-50908.htm)
- [Single Size Solutions Are Live. New Pricing. 50x More Solutions.](https://blog.gtowizard.com/single-size-solutions-are-live-new-pricing-50x-more-solutions/)
- [GGPoker & GTO Wizard Join Forces to Strengthen Poker Security — PokerNews](https://www.pokernews.com/news/2025/03/ggpoker-and-gto-wizard-team-up-to-keep-poker-fair-48110.htm)
- [GTO Wizard's Fair Play Check at heart of multiple online-poker cheating accusations — poker.org](https://www.poker.org/latest-news/gto-wizards-fair-play-check-at-heart-of-multiple-online-poker-cheating-accusations-and-controversies-aDfUQ8T4eJle/)
- [WSOP Issues GTO Solver Table Ban Notice — HighStakesDB](https://highstakesdb.com/news/high-stakes-reports/wsop-issues-gto-solver-table-ban-notice)
- [The Muck: Solver at Table Causes Stir in WPT Gardens Poker Championship — PokerNews](https://www.pokernews.com/news/2023/05/gto-solver-wpt-gardens-poker-43611.htm)
