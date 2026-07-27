# Análise competitiva — LUME Logística vs. GNH

**Data:** 2026-07-27
**Concorrente:** https://www.lumelogistica.com.py/ (Wix)
**Nós:** https://gnhorizons.com/ e https://gnhorizons.com/ventas/

---

## 0. Aviso sobre o que foi e o que não foi medido

**O site da GNH não pôde ser acessado deste ambiente.** A política de saída de rede
bloqueia o domínio: toda tentativa de conexão a `gnhorizons.com:443` e
`www.gnhorizons.com:443` é rejeitada com **403 no CONNECT** pelo gateway — via `curl`,
via WebFetch e via navegador headless. O mesmo vale para `/ventas/`. Isso é um bloqueio
do ambiente, não um problema do site.

Consequência prática, e ela é importante para ler o resto do documento:

| Item | LUME | GNH |
|---|---|---|
| HTML bruto, peso, scripts | **medido** | não medido |
| Títulos, meta, schema, canonical | **medido** | não medido |
| Catálogo completo e preços | **medido** (59 produtos) | não medido |
| Conteúdo indexável sem JS | **medido** | não medido |
| Core Web Vitals de laboratório | não medido¹ | não medido |

¹ O Lighthouse também não rodou: o Chrome não consegue atravessar o proxy do ambiente
(`ERR_CONNECTION_RESET`), e o CDN de assets do Wix (`static.parastorage.com`) está
igualmente bloqueado com 403. Não há número de LCP/CLS/TBT aqui — nem deles, nem nosso.
Onde eu não medi, **não inventei**: o lado GNH desta análise está apoiado no que você
descreveu (feito à mão, rápido, catálogo montado por JS numa página só, domínio novo) e
está marcado como *premissa* sempre que for o caso.

O que **eu consegui** medir sobre nós, indiretamente: um buscador retorna a **home** de
`gnhorizons.com` com o título *"GNH - Generando Nuevos Horizontes"* e um resumo que fala
em *"importación y distribución de productos estratégicos"*, *"materiales de
construcción"* e *"representación de marcas internacionales"*. Nenhuma URL `/ventas/`
e nenhum termo de produto aparece. Voltarei a esse ponto — ele é mais grave do que
parece.

Para fechar os buracos, preciso de uma destas coisas: (a) liberar `gnhorizons.com` na
política de rede da sessão, ou (b) o repositório do site (ele não está aqui — este repo
é o KKNUTHS/PavCalc, não tem `HANDOFF.md` nem a branch `claude/professional-website-design-qqgnfg`).

---

## 1. Resumo executivo

**Onde ganhamos:** velocidade e qualidade de execução técnica. Provavelmente por uma
margem grande.

**Onde perdemos:** em tudo que decide ranqueamento. Eles têm ~110 URLs indexáveis; nós
temos, pelo que você descreveu, essencialmente 2. Essa é a partida inteira.

E aqui está o ponto que muda a leitura da coisa: **o site deles é tecnicamente medíocre
e o SEO on-page é ruim de verdade** — 0 de 59 páginas de produto têm meta description,
a home não tem `<h1>`, há títulos em branco, conteúdo duplicado e 26 páginas de produto
com menos de 400 caracteres. Eles não estão ganhando por competência. Estão ganhando
porque **existem em 110 endereços e nós existimos em 1**.

Isso é excelente notícia. Significa que a vantagem deles é a mais fácil de copiar (é só
gerar páginas) e a nossa é a mais difícil (um site rápido feito à mão não se replica em
Wix). A ordem correta de jogo é: **replicar a estrutura deles em semanas, mantendo nossa
vantagem técnica que eles não conseguem replicar nunca.**

**Resposta direta à sua pergunta:** sim, vale muito criar páginas indexáveis por produto,
e é a ação de maior retorno da lista. Comece por grúa araña e plataformas de elevação —
justamente onde eles são mais fracos em conteúdo e onde o SERP paraguaio parece vazio.

---

## 2. Performance técnica

### 2.1 O que foi medido no LUME

| Métrica | Home | Página de produto (grúa araña) |
|---|---|---|
| HTML transferido (comprimido) | **323 KB** | **237 KB** |
| HTML descomprimido (DOM entregue) | **3,09 MB** | **1,61 MB** |
| Tags `<script>` | **80** | **61** |
| JS externo | 20 arquivos | 11 arquivos |
| JS *inline* dentro do HTML | 60 blocos, **~502 KB** | 50 blocos, **~506 KB** |
| Tags `<img>` no HTML bruto | 97 | 10 |
| TTFB (3 medições) | 2,90s / 0,37s / 0,24s | 0,62s / 0,45s / 0,28s |

Duas coisas saltam:

**Meio megabyte de JavaScript embutido dentro do HTML.** Não é um bundle que o navegador
pode cachear entre páginas — é payload novo em toda navegação. É o estado de hidratação
do Wix Thunderbolt. Em cada página. Sempre.

**O primeiro acesso é lento e os seguintes não são.** TTFB de 2,90s no primeiro hit e
0,24s depois, com `x-cache-status: MISS` → `HIT` nos headers. Eles estão atrás do Fastly.
Ou seja: **quem chega frio no site deles espera ~3s pelo primeiro byte.** E "chegar frio"
é exatamente o que faz quem vem do Google.

### 2.2 A pilha de JS que eles carregam

`react@18.3.1` + `react-dom@18.3.1` (UMD, produção) + `lodash@4.17.23` + `core-js-bundle@3.2.1`
+ `focus-within-polyfill` + `wix-thunderbolt` (main, renderer, commons) + `browser-deprecation`
+ Sentry + Wix tag manager.

Não pude medir os bytes desses arquivos (o `static.parastorage.com` está bloqueado com
403), então não vou chutar números. Mas a lista fala por si: é React UMD não *tree-shaken*,
lodash inteiro e um polyfill core-js completo, em 2026. Isso não é otimizável por eles —
é o que o Wix entrega.

### 2.3 Veredito

**Ganhamos, e não é perto.** Um site estático feito à mão contra 3 MB de DOM e 500 KB de
JS inline não é uma comparação difícil.

Mas seja honesto sobre o que essa vitória vale: **performance é critério de desempate no
Google, não critério de entrada.** Core Web Vitals ajuda a decidir entre duas páginas que
já disputam o mesmo termo. Não coloca uma página na disputa. Se a página de "grúa araña"
deles é a única que existe, ela ranqueia sozinha, a 3 segundos de TTFB.

Não abandone a vantagem técnica — ela é real e vira conversão. Só não conte com ela para
resolver descoberta, porque ela não resolve.

---

## 3. SEO e descoberta

### 3.1 Estrutura de URLs e superfície indexável

Do `sitemap.xml` deles (índice Wix, `lastmod` de hoje):

| Sitemap | URLs |
|---|---|
| `store-products-sitemap.xml` | **59** |
| `store-sub-categories-sitemap.xml` | **37** |
| `store-categories-sitemap.xml` | **9** |
| `pages-sitemap.xml` | **5** |
| **Total** | **~110** |

Padrões: `/product-page/<slug-em-espanhol>` e `/category/<slug-em-espanhol>`.

Os slugs carregam o termo de busca inteiro, com acento e tudo:
`/product-page/grúa-araña-spider-crane`, `/category/plataforma-elevadora-a-orugas-elevador-tijera`,
`/category/plataforma-de-brazo-articulado`.

`/product-page/` é feio e é assinatura de Wix. Mas o slug depois dele faz o trabalho.

**Nós:** premissa sua — home + `/ventas/`, catálogo montado por JS numa página só.
Se for isso, temos **2 URLs indexáveis contra ~110**. Uma URL só pode ranquear para um
conjunto de termos. Não dá para uma página `/ventas/` competir simultaneamente por
"grúa araña", "plataforma tijera 16 metros", "minicargador" e "retroexcavadora" — o
Google precisa de um destino específico por intenção, e nós não damos nenhum.

### 3.2 Conteúdo indexável sem JavaScript

Aqui está a descoberta mais desconfortável, e é a que eu recomendo levar mais a sério:

**O Wix entrega tudo renderizado no servidor.** Removendo `<script>` e `<style>` do HTML
bruto da página da grúa araña, sobram **4.656 caracteres de texto visível** — e nesse
texto já está *tudo*: o `<h1>`, o preço (`Gs. 135.600.000`), a descrição comercial
completa, os seis modelos (SC-1.5T a SC-12T), o breadcrumb, o menu inteiro de categorias,
o endereço, o WhatsApp e o e-mail.

Ou seja: **um crawler que não execute uma linha de JS lê a página deles inteira.**

Se o nosso catálogo é montado por JS, estamos do lado errado dessa comparação — e não
adianta o argumento de que "o Googlebot renderiza JS". Ele renderiza, mas numa segunda
passada, com fila e orçamento de renderização, e num domínio novo sem autoridade essa
fila é lenta. Além disso, Bing, os crawlers de LLM e o preview do WhatsApp — que num
mercado B2B paraguaio importa muito — são bem piores nisso ou simplesmente não executam JS.

**Perdemos essa, e é a que mais custa.**

### 3.3 Títulos, meta e dados estruturados — a auditoria das 59 páginas

Baixei e analisei as 59 páginas de produto. O resultado:

| Verificação | Resultado |
|---|---|
| Páginas com **meta description** | **0 de 59** ❌ |
| Páginas com JSON-LD `Product` | 57 de 59 ✅ |
| Páginas com **título ausente/padrão** | **2** (`plataforma-de-tijera-eléctrica-12-metros`, `minicargador-compacto-zyl-skid-steer-loader`) ❌ |
| Páginas com preço no schema | 57 de 59 |
| Descrições **duplicadas byte a byte** | **4 textos em 8 páginas** ❌ |
| Descrições **finas** (< 400 caracteres) | **26 de 59** ❌ |
| Tamanho de descrição (mín / mediana / máx) | 105 / 927 / 3.248 caracteres |

As duplicatas exatas (mesmo texto, URLs diferentes):

- `grúa-araña-spider-crane` (venda, Gs. 135.600.000) **↔** `grúa-araña-spider-crane-1` (aluguel, Gs. 450.000)
- `elevador-manual-eléctrico-mástil-simple` ↔ `…-simple-1`
- `elevador-manual-eléctrico-mástil-doble` ↔ `…-doble-1`
- `plancha-vibratoria-120-kg-unidireccional` ↔ `…-1`

E há slugs `copia-de-…` vazando para o sitemap público
(`copia-de-plataforma-de-tijera-eléctrica-16-metros`, `copia-de-andamios-ringlock-galvanizados`,
`copia-de-andamio-modulare-frame`). Eles duplicaram produtos para separar venda de
aluguel e nunca reescreveram o texto.

**O que eles fazem certo:**

```json
{"@context":"https://schema.org/","@type":"Product",
 "name":"Grúa Araña (Spider Crane)",
 "brand":{"@type":"Brand","name":"ZYL"},
 "Offers":{"@type":"Offer","priceCurrency":"PYG","price":"135600000",
           "Availability":"https://schema.org/InStock",
           "seller":{"@type":"Organization","name":"LUME Logística"}}}
```

`Product` + `Offer` + preço + moeda + marca + disponibilidade. Mais `canonical` correto,
`og:*` completo (9 tags), `robots: index`. Na home: `LocalBusiness` (com endereço e
telefone) e `WebSite`.

**Onde eles estão abertos:**

- **`meta description` em nenhuma das 59.** O Google inventa o snippet a partir do texto.
- **A home não tem `<h1>`.** Nenhum. O título é `Inicio | LUME Logística` — zero palavra-chave.
- **Nenhum `BreadcrumbList` em JSON-LD.** O breadcrumb existe visualmente mas não está marcado.
- **Nenhum `hreflang`.** `<html lang="es">`, mas o header HTTP responde `content-language: en`. Contradição.
- **Nenhum GA4, GTM ou pixel do Meta no HTML bruto.** Só o tag manager do Wix. Ou não medem, ou medem muito mal.

### 3.4 Espanhol e português

**LUME é 100% espanhol.** Sem `hreflang`, sem versão pt. A nomenclatura é consistente e
bem escolhida para o mercado — usam o termo local e o técnico juntos:
*"Plataforma Elevadora a Ruedas (Elevador Tijera)"*, *"Grúa Araña (Spider Crane)"*,
*"Andamios Multidireccional (Ringlock)"*, *"Dumper (Mini Volquete)"*. Isso captura
variações de busca sem precisar de páginas separadas. É a coisa mais inteligente que eles
fizeram, e provavelmente por acidente.

**Espaço aberto:** se a GNH vende para o Brasil, ou para compradores brasileiros no
Paraguai, **eles não disputam nada em português**. "Grua aranha", "plataforma elevadora
tesoura", "mini escavadeira" — vazio de concorrência vinda deles. Um par `es`/`pt-BR` com
`hreflang` correto é território que o Wix deles não ocupa. Isso é diferencial real, não
consolo.

### 3.5 Sobre indexação — leia com cuidado

Busquei por marca ("lumelogistica.com.py LUME Logística Paraguay") e **eles não
apareceram**. Também busquei "grúa araña Paraguay" e o resultado veio dominado por
fabricantes chineses, Chile e Espanha — nenhum player paraguaio.

**Não tire conclusão forte disso.** A ferramenta de busca deste ambiente é orientada aos
EUA e não honra o operador `site:` — ela não é substituto de um SERP do `google.com.py`.
O que dá para dizer com honestidade: **não há evidência de que o LUME domine o SERP
paraguaio**, e os nomes que aparecem de fato para "alquiler de maquinaria Paraguay" são
**Rentex, Rentax Maquinarias, Bras Rental, SET Maquinarias e Construex** — não o LUME.

Isso reposiciona o problema. É bem possível que o LUME não seja o concorrente de busca
mais forte, apenas o mais visível para você. **Antes de investir pesado, valide o SERP
real:** abra o `google.com.py` a partir do Paraguai (ou com VPN paraguaia) e busque os
10 termos que mais importam. E instale o Google Search Console no nosso domínio hoje —
sem ele estamos operando às cegas.

### 3.6 Veredito

**Perdemos, de forma decisiva, mas por um motivo estrutural e barato de corrigir.** Eles
não têm SEO bom; têm SEO *existente*. Nós temos SEO ausente. A distância é de arquitetura,
não de qualidade — e arquitetura a gente constrói.

---

## 4. Experiência e conversão

### 4.1 Caminho até o produto (LUME)

Menu persistente com 6 grupos e ~40 subcategorias, presente em toda página, **no HTML
servido** (bom para crawler e para usuário sem JS):

> Soluciones en Altura · Movimiento de Suelo · Transporte · Izaje, Manipulación de Cargas
> y Logística · Herramienta y Equipos de Obra · Construcción

Mais dois cortes comerciais transversais: `/category/ventas` (16 produtos) e
`/category/alquileres` (13 produtos).

Caminho típico: **Home → Categoria → Produto = 3 cliques.**
Com breadcrumb visível (`Inicio > Izaje… > Grúa Araña`) para voltar.

### 4.2 Cliques até o contato

- **De qualquer página:** widget flutuante de WhatsApp (Chaty) → **1 clique.**
- **Da página de produto:** botão **"Cotizar por WhatsApp"** → **1 clique.** Aparece 3× na página.
- **Total, entrada fria do Google direto no produto → conversa:** **1 clique.**

Isso é bom. É o padrão certo para B2B paraguaio: sem formulário, sem cadastro, sem
carrinho. O visitante cai na página, vê o preço, aperta um botão e está no WhatsApp.

### 4.3 Canais

| Canal | Valor |
|---|---|
| WhatsApp | **+595 971 192735** (widget + botão por produto) |
| E-mail | logistica@lume.com.py |
| Endereço | Tte. Alcorta 360 c/ Luis Patri, Edif. ABIBA, Piso 8 |
| Compartilhamento | Facebook, WhatsApp, Twitter, Pinterest por produto |

Sem formulário de contato na página de produto — deliberado, e correto.

### 4.4 Especificações técnicas

Aqui está a **maior fraqueza deles**, e é onde eu atacaria primeiro.

A "especificação" da grúa araña é **um bloco de texto corrido de 1.420 caracteres** em
bullets de marketing:

> Características principales
> • Diseño compacto para espacios reducidos
> • Estabilizadores hidráulicos tipo araña
> • Sistema de elevación de alta precisión
> • Excelente alcance y maniobrabilidad

**Não há uma única tabela de especificações. Nenhum número.** Sem capacidade por raio,
sem altura de elevação, sem peso, sem dimensões fechadas, sem motorização, sem largura
de passagem — que é *o* dado que decide a compra de uma grúa araña, já que o argumento de
venda inteiro é caber onde outra grua não cabe.

O único dado quantitativo em toda a página são os modelos disponíveis: **SC-1.5T, SC-3T,
SC-5C, SC-8T, SC-10T, SC-12T** (1,5 a 12 toneladas). E há um "Ver Certificados".

E 26 das 59 páginas têm menos de 400 caracteres de descrição — várias com 105–150
(`manguito-de-unión-sleeve-coupler`, `abrazadera-para-viga-beam-clamp`,
`escalera-metálica-steel-staircase-ladder`).

**O que eles fazem bem e nós devemos copiar:** preço público em guaranis, no HTML, no
schema. Venda: Gs. 115.000.000 a Gs. 390.000.000. Aluguel: diária de Gs. 120.000 a
Gs. 820.000. Num mercado onde quase todo mundo esconde atrás de "consulte", preço aberto
é filtro de lead e íman de long tail ("precio grúa araña Paraguay").

### 4.5 Veredito

**Empate no fluxo, com vantagem nossa disponível na profundidade técnica.**

O fluxo deles (3 cliques até o produto, 1 até o WhatsApp, preço aberto) é sólido e não
temos como superá-lo por muito — no máximo igualar. Mas **uma tabela de especificações
real é uma vantagem que eles não têm e que o Wix não vai dar de presente.** É também o
que faz o comprador industrial confiar, e o que gera as buscas de cauda longa
("grúa araña 3 toneladas altura", "plataforma tijera 16m peso") que convertem melhor.

---

## 5. Catálogo

### 5.1 O que eles têm (59 produtos, 4 marcas)

Marcas: **ZYL** (12), **FORTRAX** (12), **HATAX** (6), **JOVOO** (3).

**VENTAS — 16 produtos**

| Preço | Marca | Produto |
|---|---|---|
| Gs. 390.000.000 | ZYL | Retroexcavadora ZT388HV Premium |
| Gs. 330.000.000 | FORTRAX | Plataforma elevadora de brazo articulado y telescópico |
| Gs. 285.000.000 | ZYL | Retroexcavadora industrial serie 388 |
| Gs. 285.000.000 | ZYL | Mini excavadora hidráulica sobre orugas |
| Gs. 178.000.000 | FORTRAX | Montacargas todo terreno |
| Gs. 151.000.000 | FORTRAX | Plataforma elevadora tipo tijera a orugas |
| **Gs. 135.600.000** | **ZYL** | **Grúa araña (Spider Crane)** |
| Gs. 115.000.000 | ZYL | Retroexcavadora SLA 15-26 |
| Gs. 49.000.000 | FORTRAX | Plataforma elevadora tipo tijera eléctrica |
| Gs. 46.200.000 | FORTRAX | Montacargas eléctrico |
| Gs. 43.900.000 | ZYL | Mini excavadora |
| Gs. 38.600.000 | ZYL | Grúa hidráulica de brazo plegable |
| Gs. 25.900.000 | ZYL | Dumper sobre orugas |
| Gs. 22.700.000 | FORTRAX | Elevador manual eléctrico mástil doble |
| Gs. 13.500.000 | FORTRAX | Elevador manual eléctrico mástil simple |
| — | ZYL | Minicargador compacto (skid steer loader) |

**ALQUILERES — 13 produtos (preço = diária)**

Plataformas de tijera elétricas de **6, 10, 12, 14, 16 m** (Gs. 240.000 a 820.000),
tijera todo terreno 14 m, grúa araña (Gs. 450.000), montacargas 3,5 t, retroexcavadoras,
elevadores de mástil.

**RESTANTE — 30 produtos:** andaimes Ringlock e Frame com todos os acessórios
(diagonais, verticais, ledgers, abraçadeiras, bases reguláveis, rodapés, escadas,
rodízios), planchas vibratórias 90/120 kg, compactadores tipo sapo 80 kg.

### 5.2 Onde eles são fortes

**Elevação em altura é o núcleo real do negócio deles.** Nove subcategorias só para isso
— mástil simples, mástil duplo, tijera a rodas, tijera com estabilizador, tijera a
esteiras, tijera motorizada, braço articulado, braço telescópico, grua com cesto. Somando
a escada de plataformas de tijera de 6 a 16 m no aluguel, é uma linha completa.

**Andaimes + acessórios (30 SKUs)** é uma cauda longa enorme e barata de manter. Cada
peça é uma URL indexável. É meia dúzia de venda mas dezenas de portas de entrada no site.

### 5.3 Onde estamos cegos

**Não consigo dizer o que temos que eles não têm.** O `/ventas/` está bloqueado e o
repositório do site não está nesta sessão. Não vou preencher essa metade com suposição.

O que dá para afirmar sobre posicionamento, a partir do snippet indexado da nossa home:
o LUME se posiciona como **locadora** (*"soluciones de alquiler de maquinaria y equipos
para obras civiles, industriales y comerciales"*) e a GNH como **importadora e
distribuidora** (*"importación y distribución de productos estratégicos"*,
*"representación de marcas internacionales"*). São intenções de busca diferentes —
"alquiler" versus "venta"/"importación". A sobreposição real é o eixo `/ventas/`, e é
nele que a briga acontece.

**Para fechar esta seção me manda:** a lista de produtos do `/ventas/` (nome, marca,
categoria, e se tem preço). Aí eu faço o diff produto a produto e aponto os buracos nas
duas direções.

### 5.4 Veredito

**Indeterminado por falta de acesso.** Mas com um alerta: mesmo que nosso catálogo seja
maior e melhor, **catálogo que vive numa página só não gera descoberta.** Os 30 SKUs de
andaime deles valem pouco em receita e muito em superfície de busca. Essa é a lição a
copiar.

---

## 6. Ações priorizadas

Ordenadas por (impacto em busca) ÷ (esforço). O grupo P0 é onde está quase todo o retorno.

### P0 — Fazer agora

**1. Uma URL estática por produto, com HTML no servidor.** ⭐ *A ação de maior retorno.*

Esta é a resposta à sua pergunta central: **sim, vale, e é a única coisa que realmente
muda o jogo.** Sem isso, nada mais na lista importa.

- Padrão: `/ventas/grua-arana-spider-crane/`, `/ventas/plataforma-tijera-electrica-16m/`
  — slug em espanhol, sem acento na URL (mais limpo que o `/product-page/` deles),
  hierarquia que comunica a seção.
- **Regra inegociável: o HTML servido contém o conteúdo completo.** Nome, specs, preço,
  CTA — tudo legível com JS desligado. É exatamente o que o Wix faz por eles de graça;
  nós precisamos fazer de propósito. Gere as páginas em build a partir de um JSON do
  catálogo — o esforço é baixo e a manutenção continua sendo editar um arquivo de dados.
- A página `/ventas/` atual vira índice/filtro. O JS pode continuar lá para a navegação,
  mas ele deixa de ser o único caminho até o conteúdo.
- **Comece por:** grúa araña e plataformas de elevação (tijera 6/10/12/14/16 m,
  braço articulado, braço telescópico). Aí é onde eles são mais fracos em conteúdo e o
  ticket é mais alto.

**2. Tabela de especificações real em cada página.** ⭐ *Onde vencemos por competência.*

Eles não têm **um único número**. Publicar capacidade por raio, altura de elevação,
peso, dimensões fechadas, largura de passagem, motorização e norma atendida é uma
diferença que o Wix não tapa e que o comprador industrial procura. Marque como HTML
semântico (`<table>`, `<dl>`) e espelhe no `Product` schema com `additionalProperty`.

**3. Preço público em guaranis, no HTML e no schema.**

Eles publicam de Gs. 13,5 mi a Gs. 390 mi. Se nossa política permitir, iguale — e se não
permitir, publique **faixa** ("desde Gs. X"). Preço é o que captura
"precio grúa araña Paraguay", filtra lead ruim e alimenta rich snippet.

**4. `sitemap.xml` + `robots.txt` + Google Search Console + Bing Webmaster.**

Domínio novo: sem sitemap submetido, a descoberta demora muito mais. GSC é obrigatório —
é o único jeito de saber se as páginas novas estão sendo indexadas em vez de torcer.
Custa uma tarde. Faça hoje, antes mesmo do item 1 ficar pronto.

**5. Corrigir o posicionamento textual da home.**

O snippet indexado da nossa home fala em *"productos estratégicos"* e *"nuevos horizontes
comerciales"*. Isso é linguagem institucional e **não contém uma única palavra que alguém
digitaria no Google.** Ninguém busca "productos estratégicos"; buscam "grúa araña
Paraguay" e "plataforma elevadora precio". O `<title>`, o `<h1>` e o primeiro parágrafo
precisam nomear o que vendemos. É uma edição de texto — talvez a maior relação
retorno/esforço da lista inteira.

### P1 — Próximas semanas

**6. Páginas de categoria indexáveis.** `/ventas/plataformas-elevadoras/`,
`/ventas/gruas/`, `/ventas/movimiento-de-suelo/`. Eles têm 46; capturam a busca genérica
que é onde está o volume. Com texto de categoria próprio, não só uma grade de cards.

**7. Nomenclatura dupla, como eles fazem.** *"Grúa Araña (Spider Crane)"*,
*"Plataforma Elevadora Tipo Tijera (Scissor Lift)"*. Captura as duas variações numa
página só. É o único acerto real de SEO deles — copie sem cerimônia.

**8. `Product` + `Offer` + `BreadcrumbList` em JSON-LD.** Iguale o `Product`/`Offer`
deles e **passe na frente com `BreadcrumbList`, que eles não têm em nenhuma página.**
Adicione `Organization`/`LocalBusiness` na home.

**9. `meta description` em toda página.** Eles têm **zero em 59**. É diferencial gratuito
sobre o snippet do SERP — o único texto que o usuário lê antes de decidir clicar.

**10. WhatsApp a 1 clique, por produto.** Iguale o "Cotizar por WhatsApp" deles, com
mensagem pré-preenchida com o nome do produto
(`https://wa.me/595…?text=Hola, me interesa la Grúa Araña…`). Além do widget flutuante
global. Não coloque formulário no caminho.

### P2 — Trimestre

**11. Versão `pt-BR` com `hreflang`.** Território que eles não disputam. Só faz sentido
se realmente vendemos para o Brasil — confirme antes de investir.

**12. Conteúdo de cauda longa que eles não conseguem produzir.** Guias comparativos
("qué grúa araña elegir según el espacio", "tijera eléctrica vs. todo terreno"),
tabelas de seleção, casos de aplicação. O CMS do Wix torna isso trabalhoso para eles;
para nós é um arquivo Markdown.

**13. Cauda longa de acessórios.** Se vendemos peças de andaime ou implementos, cada um
vira uma URL. Receita pequena, superfície de busca grande — o modelo dos 30 SKUs deles.

**14. Analytics.** Não detectei GA4, GTM nem pixel do Meta no HTML bruto deles. Se eles
não medem e nós medimos, ganhamos o loop de aprendizado — que a médio prazo vale mais
que qualquer item acima.

### Antes de tudo isso — 3 validações

1. **Ver o SERP real do `google.com.py`** para os 10 termos principais. A busca deste
   ambiente é dos EUA e não substitui isso. É possível que o concorrente de verdade seja
   **Rentex / Rentax / Bras Rental / SET Maquinarias**, não o LUME.
2. **Confirmar quantas URLs nossas o Google já indexou** (GSC, ou `site:gnhorizons.com`
   do Paraguai). Toda a análise assume 2 — se forem mais, a prioridade muda.
3. **Liberar `gnhorizons.com` na rede da sessão** (ou me dar o repo do site) para eu
   auditar nosso lado com a mesma régua e fechar o diff de catálogo.

---

## Anexo A — Metodologia

Tudo do lado LUME é medição direta, não estimativa:

- `curl` com UA de Chrome sobre home, página de produto, `/category/ventas`,
  `/category/alquileres` e **todas as 59 páginas de produto do sitemap**.
- Peso: bytes transferidos com `--compressed`, mais tamanho descomprimido; contagem de
  `<script>`/`<link>`/`<img>` por regex sobre o HTML bruto.
- "Sem JS": remoção de `<script>`/`<style>` e strip de tags, contando o texto restante.
- SEO: extração de `<title>`, `meta[name=description]`, `og:*`, `canonical`, `hreflang`,
  `meta[robots]`, `h1`/`h2` e todo `application/ld+json`.
- Duplicatas: MD5 da `description` do JSON-LD das 59 páginas.
- TTFB: 3 medições por página, `time_starttransfer` do `curl`.

**Não medido, e por quê:**

- **Core Web Vitals / Lighthouse:** o Chrome não atravessa o proxy do ambiente
  (`ERR_CONNECTION_RESET`). Sem número de laboratório para nenhum dos dois sites.
- **Bytes dos bundles JS do Wix:** `static.parastorage.com` bloqueado (403 no CONNECT).
  Sei quais arquivos são; não sei quanto pesam, e não chutei.
- **Site GNH inteiro:** `gnhorizons.com` e `www.gnhorizons.com` bloqueados (403 no CONNECT).
- **SERP paraguaio:** a ferramenta de busca é orientada aos EUA e não honra `site:`.

## Anexo B — Placar

| Dimensão | Vencedor | Confiança |
|---|---|---|
| Performance técnica | **GNH** | Alta no lado deles; nosso lado é premissa |
| URLs indexáveis | **LUME** (~110 × ~2) | Alta |
| Conteúdo sem JS | **LUME** | Alta no lado deles; nosso lado é premissa |
| Qualidade do SEO on-page | **Empate ruim** — eles têm schema, nós (talvez) temos títulos; ninguém faz bem | Média |
| Fluxo até o contato | **LUME**, por pouco | Alta |
| Profundidade de especificação | **Aberto** — eles não têm nada; é nosso se quisermos | Alta |
| Amplitude de catálogo | **Indeterminado** | — |
| Autoridade de domínio | **LUME** (domínio antigo) | Média |
