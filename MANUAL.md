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
| 📸 **Print/foto** | Tire print do replay da mão (ou da mesa) e envie como foto. O KKNuths lê as cartas, stacks, posições e a ação completa |
| 📄 **Arquivo de mãos (.txt)** | Exporte o hand history da sua sala e anexe. Um torneio inteiro de uma vez! Suporta **GGPoker, PokerStars (inclusive Zoom), Winamax, PartyPoker e 888poker** — cash e torneio |
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

### 💬 Converse com o coach — sobre a mão ou sobre QUALQUER coisa de poker
Discordou da análise? Tem mais contexto? Responda na conversa (texto ou áudio):

> *"Mas o vilão era super tight, só pagava com JJ+"*

O coach **recalcula tudo com a informação nova** — e manda o gráfico do novo range.
Se algo do print foi mal lido, diga — ele relê a imagem e corrige.

E não precisa ser sobre uma mão: pergunte o que quiser —
*"como lidar com downswing?"*, *"que stakes devo jogar com banca de $500?"* —
o coach responde levando em conta o **seu** perfil de jogo.

---

## 🎮 Comandos

| Comando | O que faz |
|---|---|
| `/start` | Menu inicial |
| `/stats` | Seu perfil de estilo (VPIP, agressividade, tendência) calculado sobre todas as suas mãos |
| `/simular` | **Simulador**: jogue uma mão SUA de novo, decisão a decisão, com botões — no final, compare sua linha com a real e receba o veredito do coach |
| `/treino` | Drill rápido: **uma decisão** de uma mão sua — a mais instrutiva da mão, com a história até ali. O que você faria? Ao responder, chega **o filme da mão** (storyboard): a jogada do pré até a sua decisão, com a matemática (equity/EV) e o veredito |
| `/range` | **Gráficos de range 13×13**: `/range btn` (open por posição) · `/range sb 10` (Nash de all-in com 10bb) · `/range bb 8` (Nash de call) · `/range sb 10 ev` (**EV em BB de cada mão**, verde = empurrar rende mais que foldar) · `/range sb 10 icm 1.5` (o mesmo **sob pressão de ICM** — veja o range mudar perto da bolha) |
| `/ask` + pergunta | Pesquise no seu histórico: *"/ask minhas maiores perdas no river"* |
| `/foco` | **No que você está trabalhando**: um problema por vez — o mais caro que passou por cinco portões (amostra, frequência, custo, recorrência, procedência) — com o critério de alta escrito ANTES e o número de mãos que ainda faltam |
| `/evolucao` | Sua linha do tempo, com gráficos por indicador |
| `/estilo` | Você comparado com os arquétipos dos grandes nomes |
| `/torneio` | Quadro do último torneio + **onde o EV foi embora, por profundidade de stack**, e com que frequência você entra em cada faixa |
| `/relatorio` | **Relatório mão a mão do torneio**, em documento: cada mão jogada com o filme quadro a quadro, a análise do coach e um botão **🔍 Análise completa no bot** — toque e aquela mão reabre no chat, com placar street a street, pronta pra você discutir |
| `/preparar` | Preparação pré-torneio: o perfil daquele formato e o que ele exige |
| `/spot` | EV de all-in escrito em linguagem de mesa: `/spot reshove btn 12 co` |
| `/prova` | **Audite a ferramenta** nas suas próprias mãos — oito classes de verificação, com as falhas na cara |
| `/leitura` | Adivinhe a mão do vilão a partir da linha dele |
| `/vilao` | Dossiê de um oponente específico |
| `/banca` | Risco de ruína e downswing esperado |
| `/manual` | Este manual em PDF |
| `/plano` | Seu plano e limites |

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
| Análises por mês | 100 | Ilimitadas |
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
