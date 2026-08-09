---
titulo: "Plano: Hub de Marketing (painel, campanhas, páginas, performance, redes)"
tags: [gnh, plano, hub, marketing, painel, campanhas, telegram, performance, seo]
atualizado: 2026-08-09
status: aguardando aprovação
---

# Plano — Hub de Marketing

[[00 - Indice|← Índice]]

> [!abstract] Em uma frase
> Um **hub** em `gnhorizons.com/hub/` onde se vê e se opera todo o marketing digital
> dos dois sites: indicadores, campanhas, páginas, performance técnica, presença em
> buscadores e redes — com o Telegram como controle remoto e o fluxo de deploy que
> já existe como motor de publicação.

> [!info] Como este plano cresceu
> Começou como "painel de indicadores + central de campanhas" (07/08). Em 09/08
> virou hub de marketing a pedido do dono, incluindo desenvolvimento de páginas,
> performance e redes sociais. Os módulos A, B e C são os originais; D a G são novos.

## A regra que segura o escopo

Um hub de marketing é o tipo de coisa que incha até nunca ficar pronto. A regra que
adoto aqui, e que vale para qualquer módulo futuro:

> **O hub só mostra o que já é nosso, ou o que fica nosso com uma ligação explícita.**

Dado do site, evento, arte, deploy: é nosso, entra barato. Curtida do Instagram,
posição no Google: pertence a terceiros e exige **conectar uma conta**. Esses ficam
atrás de uma etapa própria, declarada — nunca "quase pronto, falta só o token".

## Por que agora

O lançamento do Generador 38 kVA foi o ensaio geral, feito à mão:
slide no carrossel + card em Promociones + landing + imagem de preview + 3 vídeos
para redes + links UTM + ficha técnica. Funcionou — mas foram ~15 arquivos tocados
em 6 commits, e dois erros clássicos de processo apareceram no caminho:

1. A promoção anterior dizia "solo por esta semana" e ficou **10 dias no ar** — não
   havia vigência automática.
2. O preview de link saiu **sem identidade** na primeira versão — não havia checklist
   que obrigasse a peça.

O plano transforma esse fluxo manual em processo com formato, validação e vencimento.

## Fundação que já existe (nada disso precisa ser construído)

| Peça | Onde | Papel no plano |
|---|---|---|
| Supabase `events` + `kasteller_events` | projeto `tqvrsusrbnyahpxhnwxe` | fonte única dos indicadores |
| Coluna `ref` (origem da visita) | migration de 09/08 | a aba **Origens** do painel, que antes era impossível |
| Função `resumen_dia()` com token | `deploy/supabase/fase6-analytics.sql` | modelo de acesso seguro por RPC |
| Bot Telegram `/resumo /ontem /semana` | `deploy/telegram/gnh-bot.py` (systemd no VPS) | base do controle remoto |
| Resumo diário 20h no Telegram | cron no VPS | canal de alertas |
| Autodeploy (cron 2 min, git → `/opt/gnh`) | `vps-autodeploy.sh` | publicação sem SSH |
| Pipeline de build | `gnh-hero/` + `tools/*.cjs` | onde os geradores se encaixam |
| Gerador de artes sociais | `deploy/social/*/_overlay-fonte.html` | vira template parametrizado |
| Umami | stats.vortex369.com.br | pageviews brutos (fica como está) |

---

## Módulo A — Indicadores (`/hub/`)

Página estática servida pelo próprio site, **protegida por token secreto na URL**
(`gnhorizons.com/hub/?k=...`). Sem login, sem backend novo: o HTML chama funções
RPC do Supabase que **exigem o token** (mesmo modelo do `resumen_dia()` — a chave
anon sozinha não lê nada).

**Telas (uma página, 5 abas):**

1. **Hoje / Semana** — visitantes, funil porta→ventas→WhatsApp, comparativo com a
   semana anterior, linha do tempo por dia.
2. **Campanhas** — por `utm_campaign`: chegadas por rede, cliques em WhatsApp,
   evento `promo`. Responde "o post do Instagram trouxe alguém?".
3. **Buscas** — o que se busca no site e **o que não encontra** (busquedas vacías),
   GNH e Kasteller lado a lado. É o ciclo que já rendeu palavras-chave no Kasteller.
4. **Kasteller** — visitantes, seções vistas, produtos abertos, cliques WhatsApp.
5. **Origens** *(nova, 09/08)* — de onde vêm as sessões e **quais convertem**:
   Google, Instagram, WhatsApp, ficha do Google, ChatGPT/Perplexity, directo.
   Só existe porque a coluna `ref` entrou; ver [[05 - Analytics e rastreamento]].

**Entregas:** views SQL agregadas + RPCs com token (migration) · página `/hub/`
(HTML único, gráficos leves, mesmo padrão visual do site) · link no vault.

**Custo:** 1–2 sessões. **Risco:** token na URL pode vazar por histórico de
navegador — aceitável para uso de uma pessoa; trocável a qualquer momento por
`update` na função.

---

## Módulo B — Central de Campanhas (o "pacote")

A ideia central do teu pedido: **subir um arquivo base e ele aplicar tudo.**

### O formato: uma pasta `campanas/<slug>/`

```
campanas/generador-38kva/
├── campana.yml      ← o manifesto (abaixo)
└── media/
    ├── video.mp4    ← ou foto-principal.jpg
    └── fotos extra, PDF de specs...
```

```yaml
# campana.yml — tudo que a campanha precisa, num arquivo só
tipo: lanzamiento          # lanzamiento | promo | banner | producto
titulo: Generador 38 kVA
descripcion: Motor Ricardo, ¡pronta entrega! ...
badge: { texto: Lanzamiento, color: rojo }     # rojo=novidade/desconto
sello: [Pronta entrega, Ya en stock]           # o carimbo circular (opcional)
vigencia: { desde: 2026-08-07, hasta: 2026-08-21 }   # ← vencimento AUTOMÁTICO
destaques: { slide_hero: true, card_promos: true, landing: true }
whatsapp: Hola, quiero información del Generador 38 kVA
specs:                                          # vira ficha na landing e no catálogo
  Grupo:
    Modelo: HZ38GF
    Potencia: 38 kVA / 30,4 kW
redes: [vertical, cuadrado, ancho, og]          # artes a gerar
utm: generador-38kva
```

### O gerador: `tools/build-campana.cjs <slug>`

Lê o manifesto, valida (campos obrigatórios, medidas das imagens, texto que não
cabe) e produz **tudo o que fizemos à mão no lançamento**:

| Saída | Onde entra |
|---|---|
| Slide do carrossel + slide estático (LCP) | dados gerados que `ventas.ts` importa |
| Card em Promociones | idem |
| Landing `/promo/<slug>/` | template com specs, CTAs, rastreio |
| Imagem OG 1200×630 com identidade | `img/prod/og-<slug>-vN.jpg` (nome versionado — cache) |
| Vídeos/artes vertical, quadrado, largo | `deploy/social/<slug>/` + README com legenda |
| Links UTM por rede | seção em `LINKS-UTM.md` |
| Sitemap atualizado, noindex quando vencida | automático |

**Vigência automática** — o ponto que resolve o erro da Plataforma Eléctrica:
um job diário (GitHub Action agendada) roda `build-campana --vencer`: campanha com
`hasta` no passado sai do slide e do card, a landing vira "finalizada + noindex",
commit e push — o autodeploy publica. Ninguém precisa lembrar.

**Pré-requisito técnico honesto:** hoje `FEATURED` e `PROMOS` vivem dentro de
`ventas.ts` e o slide estático é escrito à mão no HTML. O primeiro passo do módulo
é extraí-los para um arquivo de dados gerado (`campanas-data.json`) e marcar o
bloco estático com delimitadores. É refactor pequeno, mas é o que torna o resto
mecânico e seguro (nada de robô editando TypeScript por regex).

**Produtos** (subir produto novo com arte + descritivo + specs): mesmo pacote com
`tipo: producto` — gera a entrada de specs, a página estática no catálogo e o
sitemap. O card no catálogo continua manual num primeiro momento (o `CATALOG` é
código com subgrupos; automatizar isso é uma fase própria, ver Fase 6).

**Custo:** 2–3 sessões (refactor + gerador + vencimento). 

### Como o pacote chega no repositório (três portas, em ordem de chegada)

1. **Chat (já funciona hoje):** você me manda a arte e os textos aqui, eu monto o
   pacote e rodo o gerador. A diferença: vira 1 comando, não 6 commits artesanais.
2. **GitHub Action:** subiu pasta em `campanas/` (pelo site do GitHub, arrastando)
   → a Action valida, gera tudo, commita e publica. Sem depender de mim.
3. **Telegram** (Módulo C): a porta mais confortável no celular.

---

## Módulo C — Telegram como controle remoto

O bot `gnh-bot.py` já escuta comandos no VPS. Duas extensões:

### C1 — Consulta (rápido, 1 sessão)
- `/campana generador-38kva` — chegadas por rede, cliques WhatsApp da campanha
- `/buscas` — últimas buscas vazias dos dois sites
- `/kasteller` — resumo do site Kasteller (hoje o bot só cobre GNH)
- Alerta proativo no resumo das 20h: *"⚠️ 7 dias sem clique de WhatsApp"*,
  *"campanha X vence em 2 dias"*.

### C2 — Subir campanha pelo Telegram (2 sessões)
Fluxo de conversa no bot:

```
Você:  [envia vídeo ou foto]
Você:  /nueva generador-50kva
Bot:   Título? → Badge? → Sello? → Vigência? → Redes?
       (cada resposta é uma mensagem; "ok" aceita o padrão)
Bot:   📦 Pacote montado. Gerando…
Bot:   [manda a OG image e o preview do slide como foto]
       Publicar? (sim/não)
Você:  sim
Bot:   ✅ No ar em ~2 min. Links UTM: …
```

Por trás: o bot escreve `campanas/<slug>/` no clone do VPS, roda o gerador ali
mesmo (chromium + ffmpeg instalados uma vez), commita na branch e o autodeploy
faz o resto. **Guard-rails:** só chats da allowlist comandam; o bot só toca
`campanas/` e arquivos gerados; commit sempre identificado `[bot-telegram]`.

---

## Módulo D — Performance (o que o visitante sente)

Duas fontes, e a diferença entre elas importa.

### D1 — Campo: os números dos visitantes de verdade (1 sessão)

O `track.ts` e o `KT` já mandam eventos. Somar as **Core Web Vitals** custa ~15 linhas
com a biblioteca `web-vitals` (3 kB) e um evento por sessão:

| Métrica | O que é, em português | Bom |
|---|---|---|
| **LCP** | quanto tempo até aparecer a coisa principal | < 2,5 s |
| **INP** | quanto o site demora a responder ao toque | < 200 ms |
| **CLS** | quanto a página "pula" enquanto carrega | < 0,1 |

Isso é **dado de campo**: o celular real do cliente, na internet real de CDE — que é
o que decide se ele espera ou desiste. Vale mais que qualquer teste em laboratório.

Na aba de performance: mediana e p75 por página e por tipo de aparelho, com a série
por dia. E o cruzamento que ninguém faz e é o mais útil: **conversão por faixa de
LCP** — quanto custa, em cliques de WhatsApp, cada segundo de espera.

> [!tip] O motivo de começar por aqui
> Medido em 09/08 no Pixel 5: a `/ventas/` leva **2.575 ms** para ficar interativa e
> pesa 470 kB. Já sabemos que há o que ganhar; o que falta é ver o efeito na conversão.

### D2 — Laboratório: Lighthouse a cada deploy (1 sessão)

Uma GitHub Action agendada roda o Lighthouse nas páginas principais dos dois sites e
guarda o histórico. Serve para outra coisa: **pegar regressão**. Se um deploy derruba
a nota, chega alerta no Telegram com o antes e o depois — em vez de descobrir meses
depois que o site ficou lento.

Inclui os três checks que já rodei à mão e viraram correção esta semana: H1 presente
depois do JS, imagens com `alt`, alvos de toque de 44 px ([[14 - Acessibilidade e H1]]).
O que foi conserto manual vira **teste que não deixa voltar**.

---

## Módulo E — Desenvolvimento de páginas

Mesma ideia do pacote de campanha, aplicada a página que fica: `paginas/<slug>/pagina.yml`
com título, textos, blocos, imagens, SEO e JSON-LD → gera a página estática, entra no
sitemap, no `llms.txt` e no menu.

É o que já existe disperso — as 79 fichas, as 27 páginas de produto, as 6 páginas de
marca da Kasteller foram feitas por três geradores diferentes (`build-productos.cjs`,
`build-categorias.cjs`, `build-marcas.py`). O módulo unifica o formato.

**Na aba Páginas do hub:** todas as páginas dos dois sites numa tabela — última
alteração, visitas em 30 dias, cliques de WhatsApp, se tem H1/`alt`/JSON-LD, se está
no sitemap. É aqui que se vê **página órfã** (ninguém aponta para ela) e **página
morta** (no ar há meses, zero visita). As duas coisas custam SEO e hoje são invisíveis.

**Custo:** 2 sessões. **Depende de:** nada — mas fica muito melhor depois da Fase 2,
porque reaproveita o validador e o gerador de OG.

---

## Módulo F — Buscadores e IAs

### F1 — Google Search Console (1 sessão + uma ligação de conta)

É a peça que falta para fechar o ciclo de SEO, e é **de graça**. A GSC diz o que
nenhum analytics diz: **quais buscas mostram o site, quantas vezes, em que posição e
quantos clicaram**. Hoje só sabemos o que a pessoa digita *dentro* do site.

Com a API, um job diário puxa para o Supabase e o hub mostra: consultas em subida e
em queda, posição média por página, e o mapa de **impressão alta com clique baixo** —
que é onde um título melhor vira visita sem nenhum trabalho de conteúdo.

Precisa de: propriedade verificada na GSC (fácil, controlamos o DNS e o HTML) e uma
conta de serviço no Google Cloud com acesso de leitura. **Ambas as etapas são suas**,
eu preparo o passo a passo.

### F2 — Presença nas IAs (0,5 sessão)

Todo o trabalho de GEO (`llms.txt`, JSON-LD, páginas de marca) foi feito no escuro:
nunca medimos. Duas medidas agora possíveis:

- **Visitas vindas de IA** — a coluna `ref` já separa `chatgpt`, `perplexity`,
  `gemini`, `claude`. Só falta a tela.
- **Crawler de IA passando** — GPTBot, ClaudeBot, PerplexityBot aparecem no log do
  Caddy. Um contador diário mostra se estão lendo, e o quê.

O teste de citação ("¿dónde compro porcelanato Portinari en Ciudad del Este?") continua
manual — nenhuma API responde isso de forma confiável. Fica como checklist trimestral.

---

## Módulo G — Redes sociais

Aqui é onde preciso ser mais franco, porque "redes sociais no painel" pode significar
duas coisas de custo muito diferente.

### G1 — O que as redes trazem para o site (1 sessão, dado nosso)

Isso já é nosso, hoje, e é o número que decide orçamento: cada post carrega link com
UTM, cada visita traz `ref`, cada clique de WhatsApp é evento. O hub mostra por rede e
por campanha: **sessões, tempo até o contato, cliques de WhatsApp, custo zero de API.**

Junto vem o **calendário editorial** — `redes/agenda.yml` com data, rede, peça, legenda
e link UTM. O hub mostra o que está publicado, o que está agendado e o que venceu; o
Telegram lembra na véspera. As artes vêm do gerador da Fase 2, então o pacote da
campanha já nasce com as peças das redes dentro.

### G2 — O que acontece dentro das redes (2 sessões + conta conectada)

Alcance, impressões, curtidas, seguidores, melhor horário: **isso só existe pela API
da Meta**, com conta Business, App e token de longa duração. Não é difícil, mas é uma
etapa de conta que depende de você — e a Meta muda regra e revalida token com
frequência, então é manutenção recorrente, não "faz uma vez".

Existe um conector de Facebook nesta sessão de trabalho, **ainda não autorizado**.
Se autorizar, parte disso encurta bastante.

TikTok tem API própria e mais fechada; Instagram entra junto com o Facebook (mesma
conta Business). **Minha recomendação: fazer G1 agora e só encarar G2 quando a
pergunta "quanto alcance tive" começar a doer mais que "quantos clientes vieram".**

---

## Módulo H — Biblioteca de marca (0,5 sessão)

Página do hub gerada do próprio repositório: logos (fundo claro, escuro, sem nome),
paleta com os códigos, tipografia, vídeos, artes já publicadas, PDFs de ficha. Cada
item com **para que serve** e botão de baixar.

Resolve uma pergunta que já apareceu de várias formas: *qual arquivo eu mando para o
fornecedor / para a gráfica / para o parceiro?*


---

## Ordem de implementação

O hub nasce numa página só e ganha abas. Cada fase entrega **uma aba usável** — nunca
metade de uma tela esperando a fase seguinte.

| Fase | Entrega | Custo | Depende de |
|---|---|---|---|
| **1** | `/hub/` no ar: abas Hoje/Semana, Origens, Buscas, Kasteller + RPCs com token | 1–2 sessões | — |
| **2** | Pacote de campanha: `build-campana` + vigência automática | 2–3 sessões | — |
| **3** | Performance de campo (Core Web Vitals reais) → aba Performance | 1 sessão | 1 |
| **4** | Telegram consulta (`/campana`, `/buscas`, `/kasteller`) + alertas | 1 sessão | 1 |
| **5** | Redes: aba de efeito no site + calendário editorial | 1 sessão | 1, 2 |
| **6** | Google Search Console → aba Buscadores | 1 sessão | conta ligada |
| **7** | Lighthouse a cada deploy + os checks de acessibilidade como teste | 1 sessão | — |
| **8** | Páginas: formato único + aba com órfãs e mortas | 2 sessões | 2 |
| **9** | GitHub Action: pasta em `campanas/` → publica sozinho | 1 sessão | 2 |
| **10** | Telegram intake (`/nueva` → aprovar → no ar) | 2 sessões | 2, 9 |
| **11** | Biblioteca de marca | 0,5 sessão | 1 |
| **12** | Meta API: alcance, seguidores, melhor horário | 2 sessões | conta conectada |

**Rota recomendada: 1 → 2 → 3 → 4.**

O raciocínio: a Fase 1 te tira a dependência de me perguntar. A 2 mata o trabalho
braçal e o erro de vigência. A 3 é a mais barata com efeito direto em venda — sabendo
quanto cada segundo de espera custa em cliques de WhatsApp, otimizar deixa de ser
estética. A 4 põe tudo no celular por quase nada.

A Fase 6 (Search Console) é a de **maior retorno por sessão gasta** do plano inteiro e
a única que fica parada esperando conta ligada — por isso vale iniciar a verificação da
propriedade cedo, mesmo que a tela venha bem depois.

## Decisões que preciso de você

1. **Proteção do hub:** link secreto com token resolve? *(recomendo sim; login de
   verdade custa uma fase inteira a mais para um painel de uma pessoa)*
2. **Por onde começo:** Fase 1 (hub) ou Fase 2 (campanhas)?
3. **Google Search Console:** posso preparar o passo a passo para você verificar a
   propriedade dos dois domínios? É de graça, é a maior alavanca de SEO do plano, e
   quanto antes começar, mais histórico a GSC acumula. *(Recomendo fortemente sim.)*
4. **Redes sociais — até onde ir agora:** só o efeito no site + calendário (G1, dado
   nosso, barato), ou já ligar a API da Meta para alcance e seguidores (G2, conta
   conectada e manutenção recorrente)?
5. **Core Web Vitals:** ok mandar **um evento a mais por sessão** com LCP/INP/CLS?
   Continua sem cookie e sem identificar ninguém.
6. **Bot dedicado no @BotFather** para o intake: criar já ou adiar para a Fase 10?
7. **Chromium + ffmpeg no VPS** (~500 MB) para o bot gerar artes lá, ou gerar por
   GitHub Action (zero disco, +2 min)? *Só importa na Fase 10 — pode decidir depois.*

## Riscos e cuidados

- **Caddyfile compartilhado**: o painel não precisa de bloco novo no Caddy (vive
  dentro de `assets/nuevo/panel/`) — zero risco nos outros domínios.
- **Chaves**: nada de chave nova poderosa; tudo via token de leitura + RLS, como
  o `resumen_dia()` de hoje. O bot de intake usa deploy key do git restrita à branch.
- **Robô editando código**: eliminado por design — o gerador só escreve JSON,
  HTML de template e arquivos de mídia; `ventas.ts` importa, não é editado.
- **Vencimento automático** mexe no site sozinho: toda ação do job noturno chega
  como mensagem no Telegram ("campanha X saiu do ar hoje"), nunca em silêncio.
- **Contas de terceiros** (Google Search Console, Meta): token expira e regra muda.
  Toda tela que depende delas mostra **a data da última sincronização** — dado velho
  se anuncia como velho, em vez de mentir com número parado.
- **O hub não vira ferramenta de gestão de pessoas.** Sem tarefa, sem prazo, sem
  responsável: para isso existe ferramenta melhor. O hub mostra número e publica peça.

---

**Ver também:** [[05 - Analytics e rastreamento]] · [[07 - Promocoes e campanhas]] · [[03 - Deploy]] · [[06 - SEO e GEO]] · [[14 - Acessibilidade e H1]] · [[15 - Fichas do Google (GNH e Kasteller)]]
