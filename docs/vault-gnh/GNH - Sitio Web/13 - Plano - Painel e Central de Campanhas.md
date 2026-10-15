---
titulo: "Plano: Hub de Marketing (painel, campanhas, páginas, performance, redes)"
tags: [gnh, plano, hub, marketing, painel, campanhas, telegram, performance, seo]
atualizado: 2026-08-09
status: aguardando aprovação
---

# Plano — Hub de Marketing

[[00 - Indice|← Índice]]

> [!abstract] Em uma frase
> Um **hub** onde se vê e se opera todo o marketing digital dos dois sites:
> indicadores, campanhas, páginas, performance técnica, presença em buscadores e
> redes — com o Telegram como controle remoto e o fluxo de deploy que já existe
> como motor de publicação. A tela pode viver em `gnhorizons.com/hub/` **ou dentro
> do dashboard da Vortex369**: o que se constrói é a camada de dados, e ela serve
> as duas.

> [!info] Como este plano cresceu
> Começou como "painel de indicadores + central de campanhas" (07/08). Em 09/08
> virou hub de marketing a pedido do dono, incluindo desenvolvimento de páginas,
> performance e redes sociais. Os módulos A, B e C são os originais; D a H são novos. No mesmo dia veio o pedido
> de acoplar a tela ao dashboard da Vortex369 — daí o módulo A ter virado A1 (dados)
> e A2 (tela).

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

## Módulo A — Indicadores

> [!important] O hub tem duas metades, e só uma delas é valiosa
> **A1, a camada de dados**, é o ativo: views agregadas + RPCs com token que
> devolvem JSON. **A2, a tela**, é pele fina por cima. Quem consome o JSON — uma
> página nossa, o dashboard da Vortex369, o bot do Telegram — é escolha reversível.
>
> Por isso A1 é construída **primeiro e sozinha**, com contrato documentado. Nenhuma
> decisão de onde a tela mora bloqueia o trabalho.

### A1 — A camada de dados ✅ **feita em 09/08/2026**

> [!success] Está no ar
> Schema `hub` no Supabase, seis views e o papel `hub_reader`. Detalhes de ligação
> em `deploy/dashboard-hub/README.md`. O desenho abaixo previa **RPCs com token**
> porque a tela seria HTML estático; como a tela vai para o portal da Vortex369,
> que tem backend e NextAuth, o token some e o acesso é por **papel de banco
> somente-leitura** — menos código e mais seguro.

| View | Devolve |
|---|---|
| `hub.evento` | os dois sites numa tabela só, com coluna `site` |
| `hub.sesion` | uma linha por sessão: origem, país, entrada, duração, conversão, bot |
| `hub.v_dia` | por dia: sessões, pessoas, bots, contatos |
| `hub.v_origen` | por origem: sessões e conversões |
| `hub.v_busqueda` | o que buscam e **o que não acham** |
| `hub.v_pagina`, `hub.v_evento_dia`, `hub.v_detalle` | páginas, série por tipo, o que clicam |

<details>
<summary>Desenho original com RPCs (mantido como referência)</summary>

Funções RPC no Supabase, cada uma protegida por token, cada uma devolvendo JSON:

| Função | Devolve |
|---|---|
| `hub_resumen(token, site, desde, hasta)` | visitantes, sessões, funil, contatos |
| `hub_origenes(token, site, dias)` | sessões e conversões por `ref` |
| `hub_busquedas(token, site, dias)` | termos buscados e **os que não acharam nada** |
| `hub_campanas(token, dias)` | por `utm_campaign`: chegadas, cliques, promo |
| `hub_paginas(token, site, dias)` | visitas e contatos por página |
| `hub_performance(token, site, dias)` | LCP/INP/CLS p75 (depois da Fase 3) |

Notar o parâmetro **`site`** em quase todas: nasce multi-site, não como remendo.

</details>

> [!warning] A dívida que precisa morrer no começo
> Hoje são **duas tabelas** (`events` e `kasteller_events`) com o mesmo formato.
> Isso já dobra toda consulta, e num painel de vários clientes vira insustentável.
> Primeiro passo da Fase 1: uma **view** `eventos` que une as duas com uma coluna
> `site`. Não migra dado, não muda o JS dos sites, e todas as funções passam a ler
> só a view. Um cliente novo vira uma linha, não uma tabela nova.
>
> Cuidado técnico, resolvido na implementação: a view roda como dona e **fura o
> RLS** — o que aqui é proposital, porque o RLS existe só para travar a chave anon.
> A proteção real é o `GRANT`: ninguém do lado público tem acesso ao schema `hub`,
> e o papel de leitura não alcança nem `events` cru nem o financeiro.

### A2 — A tela

Três formas de consumir A1, em ordem de esforço. **Todas leem exatamente o mesmo
JSON** — dá para começar por uma e trocar depois sem refazer nada.

| Forma | Como funciona | Custo | Quando escolher |
|---|---|---|---|
| **Página própria** `/hub/?k=token` | HTML estático no próprio site | 1–2 sessões | Se a Vortex não deve virar dona disso |
| **Embutida na Vortex** | a mesma página dentro de um `<iframe>`, token no `src` | +0,2 sessão | Caminho mais rápido para "aparecer lá dentro" |
| **Nativa na Vortex** ✅ escolhida | `/marketing` no portal Next.js, lendo o schema `hub` com um segundo cliente postgres.js | 1 sessão | É o caminho: o portal já tem NextAuth, sidebar e recharts |

O `iframe` é a ponte típica: entrega valor na semana 1 e não impede a versão nativa
depois — a API não muda.

**Segurança em qualquer das três:** a chave anon do Supabase **não lê nada** (RLS só
permite INSERT). Quem lê é a função, e ela exige token. Se a tela for nativa na
Vortex, o token vive no backend dela e o navegador nunca o vê — que é melhor que o
`?k=` na URL.

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
| ~~**1a**~~ | ~~Schema `hub`: 6 views multi-site + papel `hub_reader`~~ **✅ 09/08** | — | — |
| **1b** | Página `/marketing` no portal — código escrito, falta ligar e buildar na VPS | 0,3 sessão | senha do papel |
| **2** | Pacote de campanha: `build-campana` + vigência automática | 2–3 sessões | — |
| **3** | Performance de campo (Core Web Vitals reais) → aba Performance | 1 sessão | 1a |
| **4** | Telegram consulta (`/campana`, `/buscas`, `/kasteller`) + alertas | 1 sessão | 1a |
| **5** | Redes: aba de efeito no site + calendário editorial | 1 sessão | 1a, 2 |
| **6** | Google Search Console → aba Buscadores | 1 sessão | conta ligada |
| **7** | Lighthouse a cada deploy + os checks de acessibilidade como teste | 1 sessão | — |
| **8** | Páginas: formato único + aba com órfãs e mortas | 2 sessões | 2 |
| **9** | GitHub Action: pasta em `campanas/` → publica sozinho | 1 sessão | 2 |
| **10** | Telegram intake (`/nueva` → aprovar → no ar) | 2 sessões | 2, 9 |
| **11** | Biblioteca de marca | 0,5 sessão | 1b |
| **12** | Meta API: alcance, seguidores, melhor horário | 2 sessões | conta conectada |

**Rota recomendada: 1a → 1b → 2 → 3 → 4.**

O raciocínio: a Fase 1 te tira a dependência de me perguntar — e sai partida em
duas de propósito, para que a 1a comece **antes** de decidir onde a tela mora. A 2 mata o trabalho
braçal e o erro de vigência. A 3 é a mais barata com efeito direto em venda — sabendo
quanto cada segundo de espera custa em cliques de WhatsApp, otimizar deixa de ser
estética. A 4 põe tudo no celular por quase nada.

A Fase 6 (Search Console) é a de **maior retorno por sessão gasta** do plano inteiro e
a única que fica parada esperando conta ligada — por isso vale iniciar a verificação da
propriedade cedo, mesmo que a tela venha bem depois.

## Decisões que preciso de você

1. **Onde mora a tela:** página própria, `iframe` dentro da Vortex369, ou nativa no
   dashboard dela? *(não bloqueia o começo — a Fase 1a é a mesma nos três casos)*
2. **O painel da Vortex369 é multi-cliente?** Se for, a camada de dados nasce com a
   dimensão `site` e token por cliente. Retrofit depois é caro — esta é a decisão que
   mais muda o desenho.
3. **Proteção:** token na URL resolve, ou o token deve viver no backend da Vortex
   (melhor, se a tela for nativa lá)?
4. **Por onde começo:** Fase 1a (dados) ou Fase 2 (campanhas)?
5. **Google Search Console:** posso preparar o passo a passo para você verificar a
   propriedade dos dois domínios? É de graça, é a maior alavanca de SEO do plano, e
   quanto antes começar, mais histórico a GSC acumula. *(Recomendo fortemente sim.)*
6. **Redes sociais — até onde ir agora:** só o efeito no site + calendário (G1, dado
   nosso, barato), ou já ligar a API da Meta para alcance e seguidores (G2, conta
   conectada e manutenção recorrente)?
7. **Core Web Vitals:** ok mandar **um evento a mais por sessão** com LCP/INP/CLS?
   Continua sem cookie e sem identificar ninguém.
8. **Bot dedicado no @BotFather** para o intake: criar já ou adiar para a Fase 10?
9. **Chromium + ffmpeg no VPS** (~500 MB) para o bot gerar artes lá, ou gerar por
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
