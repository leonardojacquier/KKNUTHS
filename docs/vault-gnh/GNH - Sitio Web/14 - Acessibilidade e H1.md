---
titulo: GNH — Acessibilidade e o H1 que sumia
tags: [gnh, acessibilidade, seo, a11y, toque]
atualizado: 2026-08-09
---

# GNH — Acessibilidade e o H1 que sumia

[[06 - SEO e GEO]] · [[01 - Arquitetura do site]] · [[10 - Pendencias e roadmap]]

Correções de 09/08/2026, saídas da avaliação dos dois sites. Tudo medido no navegador
(Chromium, viewport Pixel 5), antes e depois — não é estimativa.

## 1. A página /ventas/ ficava sem `<h1>`

**O sintoma:** o HTML servido tinha 1 `<h1>`; a página renderizada tinha **zero**.

**A causa:** o `<h1>` morava no bloco `.v-seo` dentro de `<main id="catalog">` — um
resumo escrito de propósito para buscadores e IAs. O `renderCatalog()` faz
`root.innerHTML = ...` e **substitui** esse bloco pelo catálogo interativo. Como o
Google renderiza JavaScript, a versão que ele indexa é a de depois do JS: sem H1.

> [!warning] O padrão que causou isso
> Conteúdo estático de SEO dentro de um contêiner que o JS vai sobrescrever é uma
> armadilha silenciosa: funciona no "ver código-fonte" e falha no que importa.
> Se um bloco existe para o buscador, ou ele fica **fora** do alvo do `innerHTML`,
> ou o que o JS pinta precisa carregar a mesma informação.

**A correção:** `renderCatalog()` agora abre com um cabeçalho real e visível —
`.v-cat-head` com eyebrow, `<h1>` e subtítulo. O H1 sobrevive ao JS porque **é**
o JS que o escreve.

```
Equipos y materiales para construcción e industria en Paraguay y Brasil
```

Junto veio `#catalog { scroll-margin-top: 88px }` — o header é sticky e sem isso o
link "Catálogo" do menu jogava o H1 para trás dele.

Medido depois: `h1: 1` em `/`, `/ventas/` e `/institucional/`.

## 2. Alvos de toque abaixo de 44px

**Antes:** 111 elementos clicáveis com menos de 44px em `/ventas/`, 10 em
`/institucional/`. **Depois: 8 e 0.**

Os 8 que sobraram são as barrinhas de progresso do carrossel: 27×44. Estreitas,
mas com 44px de altura e 10px de espaçamento entre elas — o caso que a
WCAG 2.5.8 aceita explicitamente.

| O que | Era | Virou | Como |
|---|---|---|---|
| `.v-cta` "Consultar" (36×) | 40px | 44px | `min-height` |
| `.v-name a` nome do produto (32×) | 19px | 45px | `padding: 13px 0; margin: -13px 0` |
| `.v-specs td a` "Ver ficha" (20×) | 14px | 44px | idem, dentro da célula |
| `.v-doc` "Ver detalles" (21×) | 34px | 44px | `min-height` |
| `.vh-seg` barra do carrossel | 4px | 44px | `padding: 20px 0` + `background-clip: content-box` |
| `.vh-pause`, `.foot-social` | 40/42px | 44px | tamanho direto |
| links de texto do rodapé | 16px | 44px | classe `.foot-link` |
| botões de idioma (institucional) | 30px | 44px | `min-width/height` |

> [!tip] O truque que não mexe no layout
> `padding: 13px 0; margin: -13px 0` num `inline-block` dá 26px extras de área de
> toque e devolve exatamente o mesmo espaço em margem negativa. O cartão não muda
> de altura, o dedo ganha o alvo. Serve para qualquer link de texto **isolado** —
> em listas com pouco espaçamento as áreas se sobrepõem e viram toque errado; ali
> o certo é aumentar o espaçamento e usar `min-height` (foi o caso do rodapé).
>
> Para a barrinha de 4px, o equivalente é `padding` transparente com
> `background-clip: content-box`: o traço continua com 4px, o botão tem 44.

## 3. Kasteller — `alt` nas fotos do catálogo

30 das 50 imagens da home chegavam ao navegador sem `alt`. Duas origens:

- **Cartões do buscador** (`cardHTML`) emitiam `alt=""` fixo. Agora montam
  `nome — marca, tipo · formato · acabado`:
  `Community Sgr Nat — Ceusa, porcelanato · 80X80 · natural`. Serve ao leitor de
  tela **e** ao Google Imagens, que até então não tinha o que indexar.
- **Mosaico do hero** (14 fotos rotativas): são decorativas mesmo. Ganharam
  `alt=""` **mais** `aria-hidden="true"` — a forma correta de dizer "pule isto",
  em vez de deixar ambíguo se o `alt` foi esquecido.

As 6 fotos de projeto (`Residencia AV`, `Casa Patio`…) tinham `alt=""` com legenda
ao lado; ganharam descrição própria.

De quebra, o `cardHTML` passou a escapar tudo que entra em HTML (`esc()`), e o
fallback de imagem quebrada saiu do `outerHTML` com string interpolada para
`data-n` + `textContent` — nome de produto com apóstrofo quebrava a tag.

Medido depois: **0 imagens sem `alt`** em toda a home.

## Como medir de novo

Os scripts são curtos e vale reescrevê-los quando precisar; o que importa é o
método: **medir no navegador, depois do JS rodar**. Contar no arquivo `.html`
mede a coisa errada — foi exatamente assim que o H1 passou despercebido.

```js
// alvos de toque, em contexto mobile
[...document.querySelectorAll('a,button,input,select,[role=button]')]
  .filter(el => { const b = el.getBoundingClientRect()
    return b.width && b.height && (b.width < 44 || b.height < 44) })

// imagens sem alt (atributo ausente ≠ alt vazio proposital)
[...document.images].filter(i => !i.hasAttribute('alt'))
```

---

**Ver também:** [[06 - SEO e GEO]] · [[10 - Pendencias e roadmap]]
