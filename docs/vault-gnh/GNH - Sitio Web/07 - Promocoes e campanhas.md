---
titulo: Promoções e campanhas
tags: [gnh, promo, marketing, utm]
atualizado: 2026-08-07
---

# Promoções e campanhas

[[00 - Indice|← Índice]]

## Campanha ativa: Lanzamiento Generador 38 kVA

| Item | Valor |
|---|---|
| Landing | `https://gnhorizons.com/promo/generador-38kva/` |
| Vídeo | `/video/generador.webm` (705 KB) + `.mp4` (783 KB), 5 s, sem áudio |
| Pôster / OG | `/img/prod/generador-poster.jpg` · `/img/prod/og-generador-38kva.jpg` (1200×630) |
| Etiqueta | **Lanzamiento** (laranja da marca — o vermelho fica para desconto) |
| Início | 07/08/2026 |

### Onde aparece

1. **Primeiro slide do carrossel** em `/ventas/` — vídeo em loop, mudo, com pill
   *Lanzamiento*; o botão leva à landing (não abre WhatsApp direto)
2. **Card na seção "Promociones"** do catálogo
3. **Landing própria** com vídeo, specs essenciais, 3 CTAs de WhatsApp e barra fixa

> [!note] O slide de vídeo é o estático do HTML
> O primeiro slide vive escrito à mão em `gnh-hero/ventas/index.html` (pinta antes
> do JS, é o LCP). Trocar a campanha exige mexer **lá e** em `FEATURED`/`PROMOS`
> do `ventas.ts` — o comentário `LANZAMIENTO ACTIVO` marca os dois pontos.

Links de divulgação com UTM: ver `deploy/LINKS-UTM.md`.

## Campanha encerrada: Plataforma Eléctrica 20% OFF

| Item | Valor |
|---|---|
| Landing | `https://gnhorizons.com/promo/plataforma-electrica/` |
| Arte | `/img/prod/promo-plataforma-art.jpg` (720×900) |
| Imagem de preview | `/img/prod/og-promo-plataforma.jpg` (1200×630) |
| Validade | "solo por esta semana" |
| Início | 28/07/2026 |
| **Encerrada** | **05/08/2026 — landing virou `noindex` e aponta para a ficha do produto** |

### Onde a promoção aparece

1. **Banner do carrossel** em `/ventas/` (arte desktop + versão mobile)
2. **Card na seção "Promociones"** do catálogo → leva à landing
3. **Landing própria** com specs, 3 CTAs de WhatsApp e barra fixa

## Os links de divulgação

> [!important] Use sempre o link com `utm_source`
> É o que faz o resumo diário dizer **de qual rede** veio cada visita.

```
Instagram
https://gnhorizons.com/promo/plataforma-electrica/?utm_source=instagram

Facebook
https://gnhorizons.com/promo/plataforma-electrica/?utm_source=facebook

WhatsApp
https://gnhorizons.com/promo/plataforma-electrica/?utm_source=whatsapp
```

Para o catálogo geral, mesma lógica: `https://gnhorizons.com/ventas/?utm_source=instagram`

> [!warning] Não encurte com bit.ly antes de postar
> Alguns encurtadores cortam tudo depois do `?` e a origem se perde. Instagram e
> Facebook já encurtam internamente sem quebrar o parâmetro.

## Por que a landing tem imagem própria de preview

A arte da promoção é **vertical (4:5)**. Colada no Facebook ou WhatsApp, o card de
preview cortaria em cima e embaixo — comendo justamente o "20% OFF".

Por isso existe `og-promo-plataforma.jpg`, gerada **a partir dos pixels da própria
arte** (arte inteira centralizada sobre um fundo desfocado dela mesma), no formato
1200×630 que as redes esperam. Nada foi retipografado.

> [!tip] Ao trocar a promoção
> Gere também a versão 1200×630. O script usado está no histórico do repo (Pillow:
> fundo = arte ampliada + blur 28 + brilho 0,45; arte inteira por cima, altura 630).

## Como a promoção é medida

| Evento | Dispara quando |
|---|---|
| `promo` | Clique em qualquer CTA de WhatsApp da promoção |
| `product` → "Promo Plataforma Eléctrica" | Clique em "Cotizar" no banner |
| `landing` → `promo-instagram` etc. | Chegada pela rede X |

No resumo diário aparece a linha **🏷 Promoções clicadas**.

> [!note] Estado em 29/07
> Zero cliques registrados até agora — a promoção subiu há pouco e o site recebe
> ~10 pessoas/dia. **Precisa de divulgação para performar.** Se houver visita e
> nenhum clique, aí sim o card ou a oferta precisam de ajuste.

## Criar uma campanha nova

1. Criar `assets/nuevo/promo/<slug>/index.html` (copiar a existente como base)
2. Gerar a imagem OG 1200×630 e pôr em `img/prod/`
3. Atualizar `og:image`, `og:url`, `canonical`, título e descrição
4. Adicionar o card em `PROMOS` no `gnh-hero/src/ventas.ts` (com `url` para a landing)
5. `npm run build` + copiar bundles → `assets/nuevo/` (ver [[03 - Deploy]])
6. `node gnh-hero/tools/build-sitemap.cjs` — pega `/promo/` sozinho
7. `git push` → no ar em ~2 min

> [!tip] Ao republicar um link já compartilhado
> Force o Facebook a reler o preview no
> [Sharing Debugger](https://developers.facebook.com/tools/debug/).

---

**Ver também:** [[05 - Analytics e rastreamento]] · [[09 - Operacao diaria]]
