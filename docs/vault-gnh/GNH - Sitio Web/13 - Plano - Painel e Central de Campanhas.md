---
titulo: "Plano: Painel de indicadores + Central de Campanhas"
tags: [gnh, plano, painel, campanhas, telegram]
atualizado: 2026-08-09
status: aguardando aprovação
---

# Plano — Painel de indicadores + Central de Campanhas

[[00 - Indice|← Índice]]

> [!abstract] Em uma frase
> Um **painel** para ver os números dos dois sites sem precisar perguntar, e uma
> **central de campanhas** onde um único "pacote" (arte + textos + vigência)
> vira banner, card, landing, preview de link, vídeos para redes e links UTM —
> tudo pelo fluxo de deploy que já existe, com o Telegram como controle remoto.

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

## Módulo A — Painel de indicadores (`/panel/`)

Página estática servida pelo próprio site, **protegida por token secreto na URL**
(`gnhorizons.com/panel/?k=...`). Sem login, sem backend novo: o HTML chama funções
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

**Entregas:** views SQL agregadas + RPCs com token (migration) · página `/panel/`
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

## Ordem de implementação

| Fase | Entrega | Custo | Depende de |
|---|---|---|---|
| **1** | Painel `/panel/` com 5 abas + RPCs com token | 1–2 sessões | — |
| **2** | Refactor campanhas → dados + `build-campana` + vigência automática | 2–3 sessões | — |
| **3** | Telegram consulta (`/campana`, `/buscas`, `/kasteller`, alertas) | 1 sessão | 1 |
| **4** | GitHub Action: pasta em `campanas/` → publica sozinho | 1 sessão | 2 |
| **5** | Telegram intake (`/nueva` → aprovar → no ar) | 2 sessões | 2, 4 |
| **6** | Extras: produtos 100 % por pacote, A/B de slide, agendamento de posts | a definir | 2 |

Fases 1 e 2 são independentes — dá pra começar pelas duas em paralelo ou pela que
te doer mais. Minha recomendação: **1 → 2 → 3**, porque o painel te dá retorno no
dia seguinte e o Telegram de consulta é quase grátis depois do painel.

## Decisões que preciso de você

1. **Proteção do painel:** link secreto com token resolve? (recomendo sim; a
   alternativa — login de verdade — custa uma fase inteira a mais)
2. **Ordem:** começo pela Fase 1 (painel) ou pela 2 (central de campanhas)?
3. **Bot dedicado:** para o C2 (intake) o ideal é criar um bot novo no @BotFather
   (o de consulta pode ficar sobrecarregado de permissões). Criar já ou adiar?
4. **Instalar chromium + ffmpeg no VPS** (para o bot gerar artes lá): ok? São
   ~500 MB de disco. Alternativa: gerar via GitHub Action (zero disco no VPS,
   +2 min de latência).

## Riscos e cuidados

- **Caddyfile compartilhado**: o painel não precisa de bloco novo no Caddy (vive
  dentro de `assets/nuevo/panel/`) — zero risco nos outros domínios.
- **Chaves**: nada de chave nova poderosa; tudo via token de leitura + RLS, como
  o `resumen_dia()` de hoje. O bot de intake usa deploy key do git restrita à branch.
- **Robô editando código**: eliminado por design — o gerador só escreve JSON,
  HTML de template e arquivos de mídia; `ventas.ts` importa, não é editado.
- **Vencimento automático** mexe no site sozinho: toda ação do job noturno chega
  como mensagem no Telegram ("campanha X saiu do ar hoje"), nunca em silêncio.

---

**Ver também:** [[05 - Analytics e rastreamento]] · [[07 - Promocoes e campanhas]] · [[03 - Deploy]]
