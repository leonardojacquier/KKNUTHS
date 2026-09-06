# ♠️ KKNuths — Manual do Jogador
### Seu coach de poker com IA, no Telegram · t.me/KKNUts_BOT

---

## O que é o KKNuths?

O KKNuths é um **coach de poker profissional que mora no seu Telegram**. Você manda
suas mãos do jeito que for mais fácil — um print, um arquivo, um áudio — e recebe
em segundos uma análise técnica de verdade: onde você ganhou, onde deixou dinheiro
na mesa e o que treinar para evoluir.

**A diferença para "perguntar pro ChatGPT"?** O KKNuths não estima números — ele
**calcula**. Equity contra o range real do vilão, pressão de ICM na mesa final,
preço exato de cada call. As decisões de all-in em stack curto saem de
**equilíbrio Nash computado**, e os rivers importantes passam por um **solver de
verdade**. Números certos, conselho certo — e o gráfico de range junto, para você
VER o que o coach está falando.

E ele **lembra de você**: cada mão enviada alimenta seu perfil — estilo de jogo,
estatísticas, evolução — e deixa o coaching cada vez mais personalizado.

---

## 🚀 Começando em 30 segundos

1. Abra **t.me/KKNUts_BOT** no Telegram
2. Toque em **Iniciar**
3. Mande uma mão — pronto, a análise chega em instantes

---

## 📥 Como enviar suas mãos (do jeito que preferir)

| Jeito | Como fazer |
|---|---|
| 🔗 **Link de replay** | Cola o link do replay do clube (**PPPoker** e **Suprema**) e a mão abre sozinha — nada de digitar |
| 📸 **Print/foto** | Tire print do replay da mão (ou da mesa) e envie como foto. O KKNuths lê as cartas, stacks, posições e a ação completa |
| 📄 **Arquivo de mãos (.txt)** | Exporte o hand history da sua sala e anexe. Um torneio inteiro de uma vez! Suporta **GGPoker, PokerStars (inclusive Zoom), Winamax, PartyPoker e 888poker** — cash e torneio. Para **PPPoker** e **Suprema**, cola o link do replay |
| 📋 **Colar o texto** | Copie o texto da mão (ou da sessão inteira!) e cole direto na conversa. Texto longo demais? O Telegram corta em partes — **pode colar tudo em sequência que eu junto sozinho**; se a última parte não vier, é só responder “analisar” |
| 📊 **CSV do seu tracker** | Exporte do Hold'em Manager / PokerTracker e anexe |
| 📑 **PDF** | Relatórios em PDF também funcionam |
| 🎙️ **Áudio** | Grave sua pergunta por voz — o coach entende e responde |

**Onde pegar o arquivo de mãos:**

- **GGPoker**: PokerCraft → sua sessão/torneio → *Download hand history*
- **PokerStars**: pasta `Documentos\PokerStars\HandHistory\seu_nick\`

💡 *Dica de ouro: mande o torneio INTEIRO num arquivo. O coach monta a "história
do torneio" — os momentos que decidiram seu resultado — e seu perfil evolui muito
mais rápido.*

**Torneio grande não vira resumo.** Num torneio longo, o coach analisa até **150
mãos** — e escolhe as que decidiram o resultado (all-ins primeiro, depois as de
maior impacto no seu stack), não as 150 primeiras. As demais entram com resumo
automático, avisado como tal, e o botão 🔍 reabre qualquer uma no chat.

---

## 🧠 O que você recebe em cada análise

- **Leitura técnica street a street** — em português claro; todo termo técnico vem
  explicado na primeira vez (ex.: *pot odds — o preço que o pote te oferece*)
- **Números calculados**: sua chance real de ganhar contra o range do vilão, o
  preço de cada decisão, o custo dos erros
- **📊 Gráfico de range junto**: quando o coach assume um range para o vilão ou
  cita um equilíbrio, a **matriz 13×13 chega como imagem** na sequência — você vê
  exatamente as mãos de que ele está falando. E pode **pedir na conversa**:
  *"me passa a tabela"*, *"e o EV de cada mão?"* — o gráfico vem em seguida
- **🎬 O filme da mão**: cada mão jogada no relatório vira um **storyboard** — a
  mão inteira quadro a quadro (pré-flop → river), com o board, os stacks, **o que
  os vilões fizeram em cada street**, a matemática (equity/EV) e o veredito do
  coach, tudo numa imagem só. Bate o olho e entende o spot inteiro
- **Em torneios**: pressão de ICM (quanto suas fichas valem em dinheiro real),
  decisões de bubble e mesa final, all-ins de stack curto comparados com o
  **equilíbrio Nash calculado**
- **Plano de melhoria**: 2–3 pontos priorizados para estudar

💬 **E soa como coach, não como formulário.** A análise fecha explicando *por
que* a jogada decide o spot — sem título fixo, sem repetir a conta que o
placar já deu. Termo técnico fica em inglês, como se fala na mesa (*river* é
river, *flop* é flop), e ganha um parêntese curto na primeira vez.

### 🛡️ Por que confiar no número

A regra da casa é: **regra é pedido, conferência é garantia.** Pedir a um modelo
que não erre é esperança, não garantia — então toda resposta passa por
conferências determinísticas antes de chegar em você:

- **A conta não vem do modelo.** Equity, ICM, equilíbrio de Nash e pot odds saem
  de código matemático. O coach lê, julga e explica; quem calcula é a matemática.
- **As cartas conferem com a mesa.** A carta citada no placar é comparada com o
  board real. Divergiu, corrige; ficou ambíguo, ele avisa em vez de chutar.
- **Número sem lastro não passa.** Todo número precisa vir de uma ferramenta ou
  do histórico da mão — sem lastro, não é entregue.
- **Termo de poker não vira tradução.** *River* é river, *flop* é flop, *air* é
  air. Do jeito que se fala na mesa.
- **E se a análise não fechar**, você recebe o resumo honesto com os números da
  mão e um aviso de que a análise completa não saiu — nunca meia frase.

### 🧠 KKN Tilt Detector — o que a perda faz com o seu jogo

O tilt deixa de ser sensação e vira número. Depois de **cada pote grande**
(15bb ou mais), o KKNuths observa as **8 mãos seguintes** e compara com a sua
linha de base — não com a de um jogador médio, com a **sua**.

Ele procura dois padrões opostos, os dois vindos da Teoria da Perspectiva de
**Daniel Kahneman** (Nobel de Economia de 2002):

- **Chase** — depois de PERDER um pote grande, você abre mais mãos do que
  costuma, tentando voltar ao zero. É a aversão à perda virando busca de risco.
- **Medo de ganhar** — depois de GANHAR um pote grande, você trava e folda
  além da conta, com medo de devolver. Justamente quando o stack te dava
  pressão para usar.

**Ele não acusa por pouco.** Só chama de padrão quando o desvio passa de **8
pontos de VPIP** e há mãos suficientes na janela — meia dúzia de mãos agitadas
não vira diagnóstico. E o resultado vem com o preço: *"nessas 24 mãos o saldo
foi −31.4bb"*. Você vê o que o padrão custou, não só que ele existe.

Sai no `/stats`, e alimenta o `/preparar` — o briefing pré-torneio lembra do
seu padrão antes de você sentar.

### 💬 Converse com o coach — sobre a mão ou sobre QUALQUER coisa de poker
Discordou da análise? Tem mais contexto? Responda na conversa (texto ou áudio):

> *"Mas o vilão era super tight, só pagava com JJ+"*

O coach **recalcula tudo com a informação nova** — e manda o gráfico do novo range.
Se algo do print foi mal lido, diga — ele relê a imagem e corrige.

E não precisa ser sobre uma mão: pergunte o que quiser —
*"como lidar com downswing?"*, *"que stakes devo jogar com banca de $500?"* —
o coach responde levando em conta o **seu** perfil de jogo.

### 🔬 O que mais roda por baixo

Nem tudo tem comando próprio — muita coisa entra sozinha quando o spot pede:

- **Blockers**: o que as SUAS cartas tiram do range dele. *"Seu A♠ bloqueia o
  nut flush — blefe melhor do range"* é conta, não impressão.
- **PKO / bounty**: em torneio de recompensa, eliminar o vilão paga a bounty
  **agora** — isso é dinheiro morto a mais no pote, e muda o preço do call.
  A conta entra automática quando a mão tem bounty.
- **Defesa do river**: contra a aposta final, a pergunta que tem resposta
  exata — com que frequência você precisa pagar para não ser explorado.
- **Spot pós-flop**: gráfico de EV mão a mão a partir da SUA mão real, do
  flop ao river — não só de all-in pré-flop.
- **Tendências da população**: com que frequência o field folda para agressão
  em cada street. É a base de todo exploit, e cruza com o perfil do vilão.
- **Estrutura do torneio**: o ritmo (turbo, regular, hyper) **medido nas suas
  mãos**, não adivinhado pelo nome que você digitou. Quando você manda o print
  do lobby, ele lê a tabela de blinds, o relógio e o stack inicial.

---

## 🎮 Comandos

Os mesmos quatro grupos que aparecem no `/start` — toque no botão da categoria
e a lista abre com tudo clicável.

### 📊 Análise e perfil
| Comando | O que faz |
|---|---|
| `/stats` | Perfil de estilo, leaks em bb/100 e **KKN Tilt Detector** — onde sua decisão muda depois de uma perda |
| `/estilo` | Cartão visual do seu estilo comparado com os grandes nomes, com plano de transição |
| `/evolucao` | Sua linha do tempo (VPIP, PFR, resultado…) com gráficos por indicador |
| `/torneio` | Quadro de um torneio: o último, ou escolha na lista — `/torneio 2` e `/torneio <código>` também valem |
| `/relatorio` | **O torneio inteiro analisado, mão por mão** (HTML): o filme de cada mão, a análise do coach e o botão 🔍 que reabre qualquer uma no chat |
| `/prova` | **Audite a ferramenta** nas suas próprias mãos — classes de verificação, com as falhas na cara |

### 🎮 Treino
| Comando | O que faz |
|---|---|
| `/preparar` | Briefing pré-torneio: seus leaks, protocolo mental e metas |
| `/simular` | Jogue uma mão SUA de novo, decisão a decisão, com botões — e compare sua linha com a real |
| `/treino` | Drill rápido: o que você faria neste spot? Ao responder, chega o filme da mão |
| `/leitura` | Adivinhe a mão do vilão a partir da linha que ele tomou |
| `/foco` | No que você está trabalhando agora, e como está indo — um problema por vez, com o critério de alta escrito ANTES |

### 📐 Ferramentas
| Comando | O que faz |
|---|---|
| `/spot` | EV de all-in: o equilíbrio do spot, **com e sem ICM** |
| `/range` | Gráficos 13×13: `/range btn` · `/range sb 10` · `/range sb 10 ev` (EV em bb de cada mão) · `/range sb 10 icm 1.5` (sob pressão de ICM) |
| `/vilao` | Perfil rápido de um oponente, no chat: frequências, showdowns e como explorar |
| `/dossie` | **Dossiê completo em HTML** de um vilão num torneio: `/dossie fulano` · `/dossie fulano 2` (torneio anterior) |
| `/banca` | Risco de ruína e downswing esperado para a sua banca |
| `/ask` | Busque no seu histórico: `/ask quantas vezes paguei 3-bet fora de posição?` |

### ⚙️ Conta e ajuda
| Comando | O que faz |
|---|---|
| `/manual` | Este manual em PDF |
| `/plano` | Seu plano, seus limites e o que já usou |
| `/start` | Voltar ao começo, com os atalhos do primeiro minuto |

### 🃏 Quiz do dia
Todo dia às 19h o KKNuths te manda **uma decisão real das suas mãos**: "o que você
faz?". Cada quiz é **um único ponto de decisão** — o mais instrutivo da mão, com a
história até ali. Responda no botão e veja na hora se acertou: chega **o filme da
mão** (storyboard) mostrando a jogada inteira até sua decisão, a matemática e o
veredito. Estudo diário sem esforço.

### 📅 Resumo da semana
Todo domingo: suas mãos da semana, resultado, evolução das estatísticas e o
**leak da semana** — o erro que mais te custou, para focar o estudo.

---

## 💎 Planos

| | **Grátis** | **Pro** *(em breve)* |
|---|---|---|
| Análises por mês | 50 | Ilimitadas |
| Torneio completo + história | ✔️ | ✔️ |
| Simulador, quiz diário e gráficos de range | ✔️ | ✔️ |
| Voz, prints, todos os formatos | ✔️ | ✔️ |
| Relatório semanal | ✔️ | ✔️ |
| Recursos avançados de solver e exploit | — | ✔️ |

Durante o **beta**, tudo liberado no plano Grátis. Aproveite e mande feedback —
os melhores testadores ganham benefícios no lançamento. 🎁

---

## ❓ Perguntas frequentes

**Isso é permitido pelas salas de poker?**
Sim. O KKNuths analisa **depois da sessão**, sobre arquivos que a própria sala
exporta para você — a mesma categoria dos trackers usados há 15+ anos. Ele **não**
se conecta à sua conta e **não** dá assistência em tempo real durante o jogo
(RTA), que é o que as salas proíbem.

**Meus dados estão seguros?**
Suas mãos ficam na sua conta, usadas só para as suas análises e seu perfil.
Não compartilhamos seus dados individuais.

**O coach pode errar?**
Os números são calculados — esses não erram. A leitura estratégica é opinião
técnica de alto nível: use como um coach humano, questionando e discutindo
(é para isso que a conversa existe!).

**Funciona para cash game e torneio?**
Os dois. Torneios têm análise extra de ICM/bubble e equilíbrios de stack curto.

**Colei o histórico e o Telegram cortou no meio.**
Sem problema — cole as partes em sequência que o KKNuths **remonta tudo sozinho**
e analisa junto. Se ele ficar aguardando, responda “analisar” que ele fecha a
conta com o que chegou.

**Não achei minha sala na lista.**
Manda um print que funciona para qualquer sala — e nos avise qual é a sua:
adicionamos suporte rapidinho.

---

## 📣 Convide a galera

Poker se estuda melhor em grupo. Compartilhe:
**https://t.me/KKNUts_BOT?start=convite**

E experimente mandar `/range sb 10` num grupo de poker — o gráfico do equilíbrio
calculado costuma abrir uma boa discussão. 😉

*KKNuths — pare de achar. Calcule.* ♠️
