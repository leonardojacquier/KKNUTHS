# Prompt de implementação — superar a LUME na busca

> Cole o bloco abaixo numa sessão do Claude Code **que tenha o repositório do site
> gnhorizons.com** (branch `claude/professional-website-design-qqgnfg`).
> A análise que originou este brief está em `ANALISE-COMPETITIVA-LUME.md`.

---

## Contexto

Estamos disputando o mercado paraguaio de equipamentos de elevação e construção contra a
**LUME Logística** (`lumelogistica.com.py`, feito em Wix). Fiz uma auditoria medida do
site deles. O resumo relevante para o seu trabalho:

**A vantagem deles é uma só, e é estrutural:** têm ~110 URLs indexáveis (59 produtos +
46 categorias + 5 páginas) contra as nossas ~2, e o Wix serve **tudo renderizado no
servidor** — com JavaScript desligado, a página de produto deles ainda entrega `h1`,
preço, descrição completa, modelos, breadcrumb e contato. O nosso catálogo é montado por
JS numa página só.

**Fora isso, o site deles é ruim, e é aí que entramos:**

- **0 de 59** páginas de produto têm `meta description`
- A home **não tem `<h1>`**; o title é `Inicio | LUME Logística`
- 2 páginas sem `<title>`; 4 descrições duplicadas byte a byte em 8 páginas
- 26 das 59 páginas têm menos de 400 caracteres de descrição
- Sem `BreadcrumbList`, sem `hreflang`, sem GA4/GTM/pixel detectável
- **Nenhuma tabela de especificações técnicas em nenhuma página** — a "spec" da grúa
  araña são 1.420 caracteres de bullets de marketing, sem um único número
- 3,09 MB de DOM na home, ~500 KB de JS inline por página, TTFB de 2,9s em cache frio

**O que eles fazem certo e devemos copiar:** `Product` + `Offer` em JSON-LD com preço em
PYG; preço público em guaranis (Gs. 13,5 mi a Gs. 390 mi); nomenclatura dupla que captura
as duas variações de busca numa página só (*"Grúa Araña (Spider Crane)"*,
*"Plataforma Elevadora a Ruedas (Elevador Tijera)"*); WhatsApp a 1 clique, sem formulário.

**Nossa vantagem a preservar:** o site é feito à mão e muito mais rápido. Não troque isso
por um framework pesado para resolver SEO — o objetivo é ganhar as duas coisas.

---

## Fase 0 — Auditar o nosso site antes de mexer (obrigatório)

Eu **não consegui acessar `gnhorizons.com`** (bloqueio de rede do ambiente onde rodei),
então tudo que sei do nosso lado é premissa. **Comece medindo, não implementando.**
Se algo abaixo já estiver certo, não refaça — reporte e siga.

1. Quantas URLs indexáveis existem hoje? Existe `sitemap.xml` e `robots.txt`?
2. Baixe o HTML de `/` e de `/ventas/` com `curl` e **remova todo `<script>`**. O que
   sobra de texto? Os produtos aparecem? (Este é o teste que decide tudo.)
3. Liste o que existe hoje de `<title>`, `meta description`, `<h1>`, `canonical`,
   `og:*` e JSON-LD em cada página.
4. Extraia o catálogo atual do `/ventas/` — nome, marca, categoria, preço, specs,
   imagens — e diga **onde esses dados moram** (JSON? hardcoded no JS? CMS?).
5. Meça o peso: HTML transferido, número de requests, tamanho do JS.

**Reporte esses 5 pontos antes de escrever código.** Se a estrutura real for diferente da
que assumi, o plano abaixo se ajusta a ela.

---

## Fase 1 — P0: o que realmente muda o jogo

### 1.1 Uma URL estática por produto ⭐ prioridade máxima

Esta é a tarefa central. Sem ela, nenhuma outra importa.

**Esquema de URL:**

```
/ventas/grua-arana-spider-crane/
/ventas/plataforma-tijera-electrica-16m/
/ventas/plataforma-brazo-articulado/
```

Slug em espanhol, **sem acento na URL**, terminando em barra. Não copie o
`/product-page/` do Wix — a nossa hierarquia já comunica a seção.

**Regra inegociável:** o HTML servido contém o conteúdo completo — nome, specs, preço,
CTA, tudo legível com JS desligado. Verifique com:

```bash
curl -s https://gnhorizons.com/ventas/<slug>/ | sed 's/<script.*<\/script>//g' | grep -c "<palavra do produto>"
```

**Como gerar:** um passo de build que lê um `catalogo.json` (fonte única de verdade) e
emite um arquivo HTML estático por produto. Mantenha o stack atual — não introduza
Next.js/Astro só por isso se um script de build de 100 linhas resolve. A manutenção
continua sendo editar um JSON.

A `/ventas/` atual vira índice com filtro. O JS pode continuar lá para a navegação, mas
**deixa de ser o único caminho até o conteúdo**.

**Ordem de implementação** — comece pelo que tem maior ticket e menor concorrência:

1. Grúa araña / spider crane
2. Plataformas de tijera elétricas (uma página por altura: 6, 10, 12, 14, 16 m)
3. Plataforma de braço articulado e telescópico
4. Elevadores de mástil simples e duplo
5. O resto do catálogo

### 1.2 Tabela de especificações técnicas reais ⭐ onde vencemos por competência

**Eles não publicam um único número.** Esta é a vantagem mais difícil de copiar e a que
mais pesa na decisão de um comprador industrial.

Cada página de produto precisa de uma `<table>` semântica com, no mínimo:

| Campo | Por que importa |
|---|---|
| Capacidade máxima de carga | básico |
| **Capacidade por raio de trabalho** | é o dado que decide a compra de uma grua |
| Altura máxima de elevação | básico |
| **Largura de passagem / dimensões fechadas** | todo o argumento da grúa araña é caber onde outra não cabe |
| Peso operacional | transporte e piso |
| Motorização (elétrica/diesel/híbrida) | uso interno vs. externo |
| Norma atendida / certificação | confiança |

**⚠️ Não invente especificação nenhuma.** Estes são equipamentos de elevação — número
técnico errado é risco de segurança e de responsabilidade. Use exclusivamente dados de
catálogo do fabricante ou fornecidos pelo cliente. **Se faltar dado, pare e peça.** Uma
tabela com 5 campos corretos vale mais que uma com 12 campos chutados.

Espelhe no schema com `additionalProperty` (`PropertyValue`).

### 1.3 Preço público em guaranis

No HTML **e** no JSON-LD. A LUME publica tudo aberto. Se a nossa política não permitir
preço exato, publique **faixa** (`"desde Gs. X"`). Preço aberto captura
"precio grúa araña Paraguay", filtra lead ruim e alimenta rich snippet.
Confirme a política com o cliente antes de publicar.

### 1.4 sitemap.xml + robots.txt + Search Console

Domínio novo (registrado há poucos dias). Sem sitemap submetido a descoberta demora muito
mais. Gere o `sitemap.xml` no mesmo passo de build das páginas.
**O Google Search Console e o Bing Webmaster Tools precisam ser configurados hoje** — é o
único jeito de saber se as páginas estão sendo indexadas em vez de torcer.

### 1.5 Reescrever o texto da home

O snippet indexado da nossa home hoje fala em *"importación y distribución de productos
estratégicos"* e *"nuevos horizontes comerciales"*. É linguagem institucional que **não
contém uma única palavra que alguém digitaria no Google**.

O `<title>`, o `<h1>` e o primeiro parágrafo precisam nomear o que vendemos — grúas,
plataformas elevadoras, retroexcavadoras, Paraguai. É uma edição de texto e talvez a
melhor relação retorno/esforço da lista inteira.

---

## Fase 2 — P1

**2.1 Páginas de categoria indexáveis:** `/ventas/plataformas-elevadoras/`,
`/ventas/gruas/`, `/ventas/movimiento-de-suelo/`. Com texto próprio de categoria, não só
uma grade de cards. Eles têm 46 e é onde está o volume de busca genérica.

**2.2 Nomenclatura dupla, como eles fazem:** *"Grúa Araña (Spider Crane)"*,
*"Plataforma Elevadora Tipo Tijera (Scissor Lift)"*. Captura as duas variações numa
página só. É o único acerto real de SEO deles.

**2.3 JSON-LD completo.** Iguale o `Product`/`Offer` deles e **passe na frente com
`BreadcrumbList`, que eles não têm em página nenhuma**:

```json
{"@context":"https://schema.org/","@type":"Product",
 "name":"Grúa Araña (Spider Crane)",
 "brand":{"@type":"Brand","name":"..."},
 "image":["..."],
 "additionalProperty":[{"@type":"PropertyValue","name":"Capacidad máxima","value":"..."}],
 "offers":{"@type":"Offer","priceCurrency":"PYG","price":"...",
           "availability":"https://schema.org/InStock",
           "seller":{"@type":"Organization","name":"GNH"}}}
```

Mais `Organization` / `LocalBusiness` na home (com endereço e telefone).

**2.4 `meta description` única em toda página.** Eles têm **zero em 59**. É diferencial
grátis no snippet do SERP — o único texto que o usuário lê antes de decidir clicar.
Escreva uma por página; não gere por template repetido.

**2.5 WhatsApp a 1 clique por produto,** com mensagem pré-preenchida:

```
https://wa.me/595XXXXXXXXX?text=Hola,%20me%20interesa%20la%20Gr%C3%BAa%20Ara%C3%B1a...
```

Mais o botão flutuante global. **Não coloque formulário no caminho** — o padrão B2B
paraguaio é WhatsApp direto, e é o que eles fazem.

---

## Fase 3 — P2

**3.1 Versão `pt-BR` com `hreflang`** (`es` ↔ `pt-BR`, mais `x-default`). A LUME é 100%
espanhol e não disputa nada em português. **Só faça se realmente vendemos para o Brasil —
confirme antes.**

**3.2 Conteúdo de cauda longa que o Wix deles torna caro:** guias comparativos
("qué grúa araña elegir según el espacio", "tijera eléctrica vs. todo terreno"), tabelas
de seleção, casos de aplicação. Para nós é um arquivo Markdown.

**3.3 Cauda longa de acessórios.** Eles têm 30 SKUs de andaime — receita pequena,
superfície de busca grande. Se vendemos peças ou implementos, cada um vira uma URL.

**3.4 Analytics.** Não detectei GA4, GTM nem pixel do Meta no HTML deles. Se eles não
medem e nós medimos, ganhamos o loop de aprendizado — que a médio prazo vale mais que
qualquer item acima. Instale GA4 de forma leve (sem quebrar o item de performance).

---

## Critérios de aceitação

Verificáveis por comando, não por opinião:

- [ ] `curl -s <url-produto> | sed 's/<script.*<\/script>//g'` mostra nome, specs, preço e CTA
- [ ] `sitemap.xml` lista **todas** as páginas de produto e categoria
- [ ] Toda página tem `<title>` único, `meta description` única, exatamente um `<h1>`, `canonical`
- [ ] Toda página de produto tem JSON-LD `Product` + `Offer` + `BreadcrumbList` válido no [Rich Results Test](https://search.google.com/test/rich-results)
- [ ] Toda página de produto tem `<table>` de specs com dados reais e verificados
- [ ] WhatsApp acessível em 1 clique de qualquer página
- [ ] **HTML transferido por página de produto < 100 KB** (eles gastam 237 KB; a nossa vantagem tem que aparecer no número)
- [ ] Lighthouse ≥ 95 em Performance e SEO em mobile
- [ ] GSC configurado e sitemap submetido

---

## Regras

1. **Não sacrifique a performance para resolver SEO.** Ela é a nossa única vantagem
   estrutural e as duas coisas são compatíveis: HTML estático é simultaneamente o mais
   rápido e o mais indexável. Se a solução proposta engorda a página, está errada.
2. **Não invente dado técnico nem preço.** Pergunte. Ver seção 1.2.
3. **Uma fonte de verdade** para o catálogo (`catalogo.json`), consumida tanto pelo build
   estático quanto pelo JS do índice. Nada de dados duplicados em dois lugares.
4. **Não repita os erros deles:** nada de descrição duplicada entre páginas, nada de
   slug tipo `copia-de-...`, nada de página sem título.
5. **Faça a Fase 0 primeiro** e reporte antes de codar.

---

## Validações que dependem do cliente (peça, não assuma)

1. **O SERP real do `google.com.py`** para os 10 termos principais, consultado do Paraguai.
   A busca que usei é orientada aos EUA. Há indício de que os concorrentes de busca de
   verdade sejam **Rentex, Rentax Maquinarias, Bras Rental e SET Maquinarias** — a LUME
   não apareceu nem em busca por marca. Isso pode mudar a priorização de termos.
2. **Quantas URLs nossas o Google já indexou** (via GSC).
3. **Política de preço público:** exato, faixa, ou nada.
4. **Vendemos para o Brasil?** Decide a Fase 3.1.
5. **Specs reais de catálogo** dos produtos prioritários.
