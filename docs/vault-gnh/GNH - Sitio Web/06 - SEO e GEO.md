---
titulo: SEO e GEO
tags: [gnh, seo, geo, google]
atualizado: 2026-07-29
---

# SEO e GEO

[[00 - Indice|← Índice]]

> **GEO** = *Generative Engine Optimization* — ser citado por ChatGPT, Gemini e afins,
> não só ranquear no Google.

## O que já está feito

| Item | Estado |
|---|---|
| `sitemap.xml` | ✅ 109 URLs, gerado do filesystem (nunca envelhece) |
| `robots.txt` | ✅ |
| `llms.txt` | ✅ resumo do site para LLMs, com termos em PT |
| Dados estruturados (JSON-LD) | ✅ `Organization`, `Product`, `BreadcrumbList` |
| Meta + Open Graph | ✅ em todas as páginas |
| Canonical | ✅ apontando para `gnhorizons.com` |
| Páginas indexáveis por produto | ✅ 26 |
| Resumo estático bilíngue em `/ventas/` | ✅ dentro de `#catalog` (o JS substitui depois) |
| Peso das páginas | ✅ 7–11 KB (concorrente Wix: ~237 KB) |
| Legível sem JavaScript | ✅ produtos e fichas |

## O gargalo

> [!danger] O Google não sabe que essas 109 URLs existem
> Falta criar a propriedade no **Google Search Console** e enviar o sitemap.
> Todo o resto do trabalho de SEO está pronto **esperando esse passo**.
>
> **Como destravar:** o dono cria a propriedade `https://gnhorizons.com`, copia a
> metatag `google-site-verification` e manda — a instalação nas 3 páginas leva minutos.
> Depois: enviar o sitemap. Em seguida, **Bing Webmaster** importa do GSC com 1 clique.

## O sitemap se mantém sozinho

`tools/build-sitemap.cjs` **varre `assets/nuevo/`** e monta a lista do que realmente
existe — nada de lista manual que envelhece. Cobre:

- 3 páginas principais (`/`, `/ventas/`, `/institucional/`)
- todas as fichas em `/fichas/`
- todas as pastas de produto em `/ventas/`
- todas as landings em `/promo/`

> [!warning] Rode-o **por último**
> Ele lê `assets/nuevo/`. Se rodar antes de sincronizar o build, gera um sitemap
> desatualizado. Foi assim que a landing da promoção sumiu do sitemap uma vez —
> resolvido ensinando o gerador a varrer `/promo/`.

## Estratégia por produto

A lógica é simples: **1 URL por produto**, com specs reais e dados estruturados.
A concorrente (lumelogistica.com.py) já faz isso em Wix; a nossa versão é mais leve,
tem tabela de specs de verdade e liga cada modelo à sua ficha técnica com PDF.

Cada página de produto tem:
- tabela de specs do fabricante
- JSON-LD `Product` com `additionalProperty` por modelo
- breadcrumb
- WhatsApp a 1 clique com mensagem pronta
- link para a ficha técnica de cada modelo

## Oportunidade: os 20 produtos sem página

Cada catálogo de fabricante que chegar vira: tabela → página → ficha → PDF → +1 URL no
sitemap. É o caminho mais direto para crescer a superfície de indexação.
Ver [[04 - Catalogo e fichas tecnicas]].

## Pendências de SEO

1. **Google Search Console** — o bloqueio principal
2. **Bing Webmaster** — depois do GSC
3. **`gnhorizons.com.br` → `gnhorizons.com`** — consolidar autoridade num domínio só
4. **Sinônimos em português** na busca interna — não é SEO externo, mas é conversão
   perdida com o segundo maior público do site

---

**Ver também:** [[10 - Pendencias e roadmap]] · [[04 - Catalogo e fichas tecnicas]]
