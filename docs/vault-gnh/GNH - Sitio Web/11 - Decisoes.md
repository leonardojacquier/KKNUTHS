---
titulo: Decisões
tags: [gnh, decisoes, adr]
atualizado: 2026-07-29
---

# Decisões

[[00 - Indice|← Índice]]

> [!info] Para que serve esta nota
> Registrar o **porquê** das escolhas, para não gastar tempo revisitando o que já
> foi decidido. Decisões do dono estão marcadas como tal.

---

## D1 · GNH é grupo de comercio internacional, não importadora
**Decisão do dono.** A importação é uma das cinco frentes de serviço, não a
identidade da empresa. Vale para site, apresentações e `llms.txt`.

## D2 · Três frentes sem unificação visual
**Decisão do dono.** Gateway/ventas e institucional mantêm identidades próprias.
Não unificar.

## D3 · Cimento fora do site
**Decisão do dono.** Entra nas apresentações, no site não — exceto o card
"Cementos y Morteros" que já existe.

## D4 · Espanhol como idioma base
O público é Paraguai + região. O institucional tem 4 idiomas; o resto é espanhol.
Confirmado pelos dados: Paraguay 18, Brasil 12, Argentina 2, Chile 1.

## D5 · `assets/nuevo/` é a raiz publicada
O Caddy serve `/opt/gnh/assets/nuevo`. Páginas de produto, fichas e promoções
convivem lá com o build do Vite — por isso o deploy copia **seletivamente** e
`rm -rf assets/nuevo` é proibido.

## D6 · `catalogo-data.ts` como fonte única
Cards, páginas estáticas, tabelas, JSON-LD e índice de busca saem do mesmo arquivo.
Evita a divergência clássica entre "o que o site mostra" e "o que o catálogo diz".

## D7 · Nunca inventar spec
Campo sem dado do fabricante fica fora da tabela ou vira "Consultar". Spec errada em
ficha técnica é problema comercial e de segurança.

## D8 · Analytics sem cookies e sem PII
Sessão anônima em `sessionStorage`, origem inferida do fuso horário. A chave anon do
Supabase é pública **por design** — RLS só permite INSERT; leitura exige token.

## D9 · Filtro anti-bot conservador
Só marca bot quem tem fuso de nuvem **e** navegador en-US **e** zero interação.
Quem clica em qualquer coisa conta como pessoa.
**Motivo:** preferir contar um bot a mais do que descartar um cliente real.
E o resumo **mostra** quantos foram filtrados — filtrar não é esconder.

## D10 · Progressive enhancement em três camadas
HTML puro → vanilla JS → GSAP/Lenis. Se a CDN cair, o site funciona. Se o
`prefers-reduced-motion` estiver ligado, tudo desliga.

## D11 · Fallback em toda imagem hotlinkada
Cadeia de `onerror` até SVG inline ou remoção do elemento.
**Motivo:** o site nunca pode parecer quebrado se `gnhorizons.com` estiver fora.

## D12 · CSS das fichas compartilhado por leitura, não por cópia
`build-plataformas.cjs` lê o CSS de `build-gruas.cjs` em tempo de execução, e falha em
voz alta se não achar.
**Motivo:** cópia de CSS envelhece; leitura não.

## D13 · Imagem OG dedicada para campanhas
Arte vertical cortaria no preview das redes. A imagem 1200×630 é composta **dos pixels
da própria arte** (fundo desfocado dela mesma), sem retipografar nada.

## D14 · Sitemap gerado do filesystem
Nada de lista manual. `build-sitemap.cjs` varre `assets/nuevo/` e roda **por último**.

## D15 · Rótulos de spec seguem a fonte
A página da promoção dizia "Altura de trabajo"; o catálogo do fabricante diz só
"Altura". Alinhado ao catálogo — a diferença (~1,7 m) muda a decisão de compra, e não
temos confirmação de qual é.

---

**Ver também:** [[08 - Marca e conteudo]] · [[01 - Arquitetura do site]]
