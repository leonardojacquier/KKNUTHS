---
titulo: Kasteller — SEO, GEO e analytics
tags: [kasteller, seo, geo, analytics, buscador]
atualizado: 2026-08-09
---

# Kasteller — SEO, GEO e analytics

[[01 - Buscador e palavras-chave]] · [[02 - Infraestrutura e DNS]]

> **GEO** = *Generative Engine Optimization* — ser citado por ChatGPT, Gemini,
> Perplexity e afins. Mesmo conceito da [[GNH - Sitio Web/06 - SEO e GEO|nota da GNH]].

## O diagnóstico que originou tudo (09/08/2026)

### O catálogo era invisível

Os 1.018 produtos vivem no `buscador/productos.json`, carregado por JavaScript.
Crawler nenhum executa aquilo. A prova:

| Termo | No HTML servido | No JSON |
|---|---|---|
| Portinari | **1** | 3.480 |
| Ceusa | 1 | 1.146 |
| Castelatto | 1 | 204 |

Sitemap tinha **1 URL** (a GNH tinha 110). Quem perguntasse a uma IA *"onde compro
porcelanato Portinari em Ciudad del Este"* não tinha como chegar aqui.

### Os dados de busca estavam inflados ~4×

O debounce de 1,2 s não distinguia "parou de digitar" de "digita devagar". Uma
sessão real, 43 eventos:

```
poc · poce · porce · porcen · porcenl · porcenla · porn · proc · procel · procela · procelan
```

Onze registros de **uma** busca por "porcelanato". Em 4 sessões: 116 eventos para
~30 buscas reais. O ranking de "mais buscados" media velocidade de digitação.

### O ouro no meio do ruído

Os termos revelaram **visitantes brasileiros**: `cozinha`, `cozina`, `banheiro`,
`pedra`, `grandes`. Português não é detalhe — é público real. Virou seção própria
no `llms.txt`.

## O que foi feito

| Peça | Onde |
|---|---|
| `llms.txt` | `assets/kasteller2/llms.txt` — marcas com contagem, facetas, FAQ, equivalências PT/ES |
| JSON-LD na home | `HomeGoodsStore` (coordenadas do showroom, 6 marcas, `parentOrganization` GNH), `WebSite` + `SearchAction`, `FAQPage` |
| `robots.txt` | libera GPTBot, OAI-SearchBot, PerplexityBot, ClaudeBot, Google-Extended **de propósito** |
| Páginas por marca | `/marcas/<slug>/` — 6 páginas + índice, geradas do JSON |
| Sitemap | 1 → **8 URLs** |
| Correção do debounce | `buscador/kasteller-buscador.js` |

### As páginas de marca

Geradas por `preview-kasteller/buscador-fonte/build-marcas.py`:

```bash
cd preview-kasteller/buscador-fonte
python3 build-marcas.py ../../assets/kasteller2
```

Idempotente — reescreve páginas e sitemap do zero. **Rodar de novo depois de todo
re-scrape do catálogo**, junto com o `enriquecer_ambientes.py`.

Cada página tem: perfil próprio da marca (texto único — repetir descrição vira
conteúdo raso), facetas reais calculadas do JSON, todos os produtos com nome +
tipo + acabado + formato, CTA de WhatsApp, links para as outras marcas, JSON-LD
`CollectionPage` + `BreadcrumbList`.

Resultado: "Portinari" passou de **1 para 1.176** menções em HTML.

> [!important] Marca com menos de 5 produtos não gera página
> Página com 2 itens é conteúdo raso e o Google penaliza o site inteiro, não só
> aquela URL. O filtro está no `main()` do gerador.

> [!warning] Link interno é obrigatório
> Página gerada que ninguém aponta não é descoberta. Por isso a coluna **Marcas**
> no rodapé da home — são 7 links (6 marcas + índice). Se um dia o rodapé for
> refeito, **manter esses links**.

### A correção do rastreio de busca

O termo fica **pendente** e só é gravado se o seguinte não começar com ele —
ou seja, quando a digitação estabiliza. Sair do campo ou 2,6 s de silêncio fecham
na hora. O evento passa a levar a contagem de resultados: `porcelanato [895]`.

Medido no navegador digitando "porcelanato" letra a letra: **1 evento, era 11**.

## O que ainda falta

- [ ] **Páginas por produto** (`/marcas/<marca>/<produto>/`) — o passo seguinte
      natural; 1.018 URLs. Mesmo padrão das 26 páginas de produto da GNH.
- [ ] **124 produtos sem foto** (Castelli 84 + Castelatto 40). As páginas mostram
      "Consultar" no lugar — funciona, mas foto converte mais.
- [ ] **Google Business Profile** da Kasteller no endereço do showroom. Resolve de
      vez o mapa do rodapé (hoje o Google rotula o ponto com a ficha da Transcamilo)
      e entra nas buscas locais de "revestimientos Ciudad del Este".
- [ ] **Reavaliar as buscas** daqui a ~1 semana, agora com dados limpos e com a
      contagem de resultados — mostra onde o catálogo é raso.
- [ ] Sitemap ainda é escrito à mão pelo gerador; se surgirem mais seções, revisar.

## Como medir se o GEO está funcionando

Perguntar direto às IAs, de tempos em tempos:

> "¿Dónde puedo comprar porcelanato Portinari en Ciudad del Este?"
> "Tiendas de revestimientos de alto padrón en Paraguay"

Se a Kasteller aparecer citada, o `llms.txt` + JSON-LD + páginas de marca estão
cumprindo o papel. É o mesmo teste que vale para a GNH.

---

**Ver também:** [[01 - Buscador e palavras-chave]] · [[GNH - Sitio Web/06 - SEO e GEO]]
