---
titulo: Analytics e rastreamento
tags: [gnh, analytics, supabase, telegram, dados]
atualizado: 2026-07-29
---

# Analytics e rastreamento

[[00 - Indice|← Índice]]

## Filosofia

Sem cookies, sem IP, sem PII. A sessão é anônima (`sessionStorage`), e a origem
geográfica é **inferida do fuso horário do navegador** — não de geolocalização.
O que interessa não é quem entrou, é **o que a pessoa procurou**.

## As duas camadas

| Camada | O que mede | Onde |
|---|---|---|
| **Umami** | Páginas vistas, sessões, referrer | stats.vortex369.com.br |
| **Supabase** | Eventos de negócio e jornada | projeto `tqvrsusrbnyahpxhnwxe` |

## Tabelas no Supabase

**`events`** — `id`, `type`, `detail`, `path`, `session_id`, `created_at`
**`leads`** — `id`, `nombre`, `empresa`, `whatsapp`, `producto`, `mensaje`, `origen`, `session_id`, `created_at`

RLS: a chave anon só permite **INSERT**. Ler exige a função protegida por token.
Por isso a chave anon pode viver no JavaScript público sem risco.

## Tipos de evento

| `type` | Quando dispara | `detail` guarda |
|---|---|---|
| `landing` | Primeiro toque da sessão | `fuso\|idioma\|entrada` |
| `porta` | Escolha no gateway | `ventas` ou `institucional` |
| `product` | Clique em "Cotizar/Consultar" | nome do produto |
| `ficha` | Abertura de ficha técnica | arquivo da ficha |
| `busqueda` | Busca **com** resultado | o termo digitado |
| `busqueda-vacia` | Busca **sem** resultado | o termo digitado |
| `whatsapp` | Clique em qualquer link wa.me | trecho da mensagem |
| `promo` | Clique no CTA de promoção | nome da promoção |
| `negocio` | Card no institucional | nome do negócio |
| `ceo-carta` | Leitura da carta do CEO | — |
| `idioma` | Troca de idioma | idioma escolhido |

> [!tip] O campo `landing` é o mais rico
> Formato `fuso|idioma|entrada`, por exemplo `America/Asuncion|es-PY|ventas`.
> Desde 29/07 a entrada carrega **a rede de origem** quando o link traz `?utm_source=`:
> `promo-instagram`, `ventas-facebook`, `promo-whatsapp`. Ver [[07 - Promocoes e campanhas]].

## Funções SQL

| Função | Para quê |
|---|---|
| `resumen_dia(token, offset)` | Agregados de um dia (offset 0 = hoje). Protegida por token |
| `tz_pais(fuso)` | Traduz fuso horário em país legível |
| `es_bot(pais, lang, interacciones)` | Heurística anti-bot |

O token do resumo **não é colado nesta documentação** — vive na própria função e em
`/opt/gnh_lib/gnh-resumen.env`.

## Filtro anti-bot

> [!info] A regra
> É considerado bot quem tem **fuso de nuvem** (fora da nossa região) **e** navegador
> **en-US** **e** **zero interação**. Quem clica em qualquer coisa conta como pessoa,
> sempre.

Deliberadamente conservador: prefere contar um bot a mais do que descartar um cliente real.

**Efeito real medido (19–28/07):** 107 sessões brutas → **~88 pessoas reais + 19 bots**.
O caso mais claro foi 27/07: **9 sessões no mesmo minuto** (16h50), todas de fuso de
nuvem, en-US, zero cliques. Os bots só aparecem a partir de 24/07 — coincide com o site
novo entrar no ar e começar a ser rastreado por crawlers, o que é **bom sinal**.

O resumo mostra `👥 19 visitantes (+11 bots filtrados)` — filtra, mas não esconde.

## Resumo diário no Telegram

- Script: `deploy/telegram/gnh-resumen-diario.py` (formatação em `gnhresumen.py`)
- Roda por cron às **20h**, config em `/opt/gnh_lib/gnh-resumen.env`
- Já em funcionamento

O que o resumo traz: visitantes (e bots filtrados), portas, origem por país, produtos
consultados, negócios, buscas, **buscas sem resultado**, promoções clicadas, fichas
abertas, cliques de WhatsApp, leads e as **jornadas** mais completas do dia.

**Bot sob demanda** (`/resumo`, `/ontem`, `/semana`): código pronto em
`deploy/telegram/gnh-bot.py` + `gnh-bot.service`, mas **não instalado** — ver
[[10 - Pendencias e roadmap]].

## O código de referência

O link de WhatsApp carrega um **código de 4 letras** derivado da sessão anônima.
Quando o cliente escreve, esse código permite cruzar a conversa com o que a pessoa
navegou antes (`events.session_id LIKE 'XXXX%'`) — sem identificar ninguém.

## O que os dados já mostraram (19–28/07)

| Achado | Número |
|---|---|
| Pessoas reais | ~88 |
| Origem | Paraguay 18 · Brasil 12 · Argentina 2 · Chile 1 |
| Cliques de WhatsApp | 7 |
| Leads de formulário | **0** — a conversão acontece toda pelo WhatsApp |
| Buscas registradas | 15, de 9 pessoas |

**A busca campeã é "grúa"** — 4 pessoas distintas em 4 dias diferentes. Isso validou o
trabalho das grúas araña: a demanda batia na busca antes das páginas existirem.

**Duas buscas voltaram vazias — as duas em português:** `escav` (a pessoa se corrigiu
sozinha para `exca`) e `Pisos em Concreto` (essa **foi embora**). Ver a falha em
[[04 - Catalogo e fichas tecnicas]].

---

**Ver também:** [[07 - Promocoes e campanhas]] · [[10 - Pendencias e roadmap]]
