# Relatório de validação — estado atual do gnhorizons.com

> **Como usar:** rode isto na sessão que tem acesso ao site/repo da GNH. Cada bloco traz
> o comando exato, o que o número significa e a **régua da LUME já medida** para comparar.
> Preencha a coluna "GNH" e o veredito. No fim há um resumo para colar de volta aqui.
>
> Baseline da LUME: `ANALISE-COMPETITIVA-LUME.md` · Plano de ação: `PROMPT-IMPLEMENTACAO-SEO.md`
>
> **Nada abaixo está preenchido do lado GNH de propósito** — o domínio estava bloqueado
> na sessão que produziu a análise. Preencher por suposição destrói o valor do exercício.

---

## Bloco 1 — Superfície indexável

**É o item que decide a briga.** Eles têm ~110 URLs; se nós temos 2, nada mais importa.

```bash
# 1.1 Existe sitemap? Quantas URLs?
curl -s https://gnhorizons.com/sitemap.xml | grep -c "<loc>"

# 1.2 Existe robots.txt e ele aponta o sitemap?
curl -s https://gnhorizons.com/robots.txt

# 1.3 Quantas URLs reais o site expõe (links internos únicos a partir da home e do /ventas/)
for p in "" "ventas/"; do
  curl -s "https://gnhorizons.com/$p" \
  | grep -oE 'href="(/[^"#?]*)"' | sed 's/href="//;s/"//' | sort -u
done | sort -u | tee /tmp/gnh-urls.txt | wc -l
```

| Métrica | LUME (medido) | GNH | Veredito |
|---|---|---|---|
| URLs no sitemap | **110** | | |
| Páginas de produto indexáveis | **59** | | |
| Páginas de categoria indexáveis | **46** | | |
| `robots.txt` aponta sitemap | ✅ sim | | |

---

## Bloco 2 — Conteúdo sem JavaScript ⚠️ o teste mais importante

Este é **o** teste. Se o catálogo é montado por JS, o crawler pode não ver nada — e o
Wix deles entrega tudo pronto no servidor.

```bash
# 2.1 Texto que sobra na home depois de remover TODO script e style
curl -s https://gnhorizons.com/ \
  | perl -0777 -pe 's/<script.*?<\/script>//gs; s/<style.*?<\/style>//gs; s/<[^>]+>/ /g; s/\s+/ /g' \
  | tee /tmp/gnh-home.txt | wc -c

# 2.2 Mesmo teste no /ventas/
curl -s https://gnhorizons.com/ventas/ \
  | perl -0777 -pe 's/<script.*?<\/script>//gs; s/<style.*?<\/style>//gs; s/<[^>]+>/ /g; s/\s+/ /g' \
  | tee /tmp/gnh-ventas.txt | wc -c

# 2.3 ⚠️ DECISIVO: os nomes dos produtos aparecem nesse texto?
grep -io -E "grúa|grua|plataforma|tijera|elevador|retroexcavadora|excavadora|montacargas" \
  /tmp/gnh-ventas.txt | sort | uniq -c | sort -rn
```

| Métrica | LUME (medido) | GNH | Veredito |
|---|---|---|---|
| Texto sem JS — home | **17.006 caracteres** | | |
| Texto sem JS — catálogo | **4.656 caracteres** (pág. produto) | | |
| **Nomes de produto visíveis sem JS** | ✅ **sim, todos** | | |
| Preço visível sem JS | ✅ sim (`Gs. 135.600.000`) | | |
| Specs/modelos visíveis sem JS | ✅ sim (SC-1.5T … SC-12T) | | |

> **Se o bloco 2.3 vier vazio ou quase vazio, esse é o achado número um do relatório** —
> e confirma que a Fase 1.1 do plano é a prioridade correta.

---

## Bloco 3 — Tags de SEO on-page

```bash
for U in "https://gnhorizons.com/" "https://gnhorizons.com/ventas/"; do
  echo "===== $U"
  H=$(curl -s "$U")
  echo "$H" | grep -oE '<title[^>]*>[^<]*' | head -1
  echo "$H" | grep -oE '<meta[^>]*name="description"[^>]*>' | head -1
  echo "$H" | grep -oE '<link[^>]*rel="canonical"[^>]*>' | head -1
  echo "h1 count: $(echo "$H" | grep -c '<h1')"
  echo "og tags:  $(echo "$H" | grep -c 'property="og:')"
  echo "hreflang: $(echo "$H" | grep -c 'hreflang')"
  echo "json-ld:  $(echo "$H" | grep -c 'application/ld+json')"
done
```

| Item | LUME (medido) | GNH | Veredito |
|---|---|---|---|
| `<title>` único e com palavra-chave | ⚠️ `Inicio \| LUME Logística` — sem keyword | | |
| `meta description` | ❌ **0 de 59 páginas** | | |
| Exatamente um `<h1>` | ❌ **home sem `<h1>`** | | |
| `canonical` | ✅ presente | | |
| `og:*` | ✅ 9 tags | | |
| JSON-LD `Product` + `Offer` | ✅ com preço PYG | | |
| JSON-LD `BreadcrumbList` | ❌ **ausente** | | |
| `hreflang` | ❌ ausente | | |
| GA4 / GTM / pixel | ❌ nenhum detectado | | |

> As linhas marcadas ❌ na coluna LUME são **as brechas** — cada uma é vantagem barata
> se do nosso lado vier ✅.

---

## Bloco 4 — Performance

Nossa vantagem esperada. **Confirme com número**, não por impressão.

```bash
# 4.1 Peso transferido e TTFB (3 rodadas para separar cache frio de quente)
for i in 1 2 3; do
  curl -s -o /dev/null --compressed \
    -w "  ttfb=%{time_starttransfer}s total=%{time_total}s transferido=%{size_download}B\n" \
    https://gnhorizons.com/ventas/
done

# 4.2 Peso do DOM entregue e contagem de scripts
curl -s --compressed https://gnhorizons.com/ventas/ -o /tmp/gnh.html
echo "HTML descomprimido: $(wc -c < /tmp/gnh.html) bytes"
echo "<script> tags:      $(grep -o '<script' /tmp/gnh.html | wc -l)"
echo "JS externo:         $(grep -oE '<script[^>]*src=' /tmp/gnh.html | wc -l)"

# 4.3 Lighthouse mobile (rode local — no ambiente da análise o Chrome não passou pelo proxy)
npx lighthouse https://gnhorizons.com/ventas/ --preset=desktop --view
npx lighthouse https://gnhorizons.com/ventas/ --view   # mobile é o que conta para ranking
```

| Métrica | LUME (medido) | GNH | Veredito |
|---|---|---|---|
| HTML transferido (produto) | **237 KB** | | |
| HTML transferido (home) | **323 KB** | | |
| DOM descomprimido (produto) | **1,61 MB** | | |
| DOM descomprimido (home) | **3,09 MB** | | |
| Tags `<script>` | **61** (produto) / **80** (home) | | |
| JS inline | **~500 KB por página** | | |
| TTFB cache frio | **2,90s** | | |
| TTFB cache quente | **0,24s** | | |
| Lighthouse Perf (mobile) | não medido¹ | | |
| LCP / CLS / INP | não medido¹ | | |

¹ O Lighthouse não rodou na análise original: o Chrome não atravessou o proxy do ambiente
(`ERR_CONNECTION_RESET`) e o CDN do Wix estava bloqueado. **Rode nos dois sites a partir
da sua sessão** para fechar essa linha — é a única métrica onde esperamos ganhar de
lavada e ainda não temos número.

---

## Bloco 5 — Catálogo (o diff que ficou em aberto)

Liste o nosso `/ventas/` e cruze com o deles. Este é o único bloco que **não** dá para
automatizar por comando — precisa de olho humano no catálogo.

**Eles têm 16 produtos em VENTAS** (marcas ZYL, FORTRAX, HATAX, JOVOO):

| Preço | Produto |
|---|---|
| Gs. 390.000.000 | Retroexcavadora ZT388HV Premium |
| Gs. 330.000.000 | Plataforma elevadora de brazo articulado y telescópico |
| Gs. 285.000.000 | Retroexcavadora industrial serie 388 |
| Gs. 285.000.000 | Mini excavadora hidráulica sobre orugas |
| Gs. 178.000.000 | Montacargas todo terreno |
| Gs. 151.000.000 | Plataforma elevadora tipo tijera a orugas |
| **Gs. 135.600.000** | **Grúa araña (Spider Crane)** — modelos SC-1.5T a SC-12T |
| Gs. 115.000.000 | Retroexcavadora SLA 15-26 |
| Gs. 49.000.000 | Plataforma elevadora tipo tijera eléctrica |
| Gs. 46.200.000 | Montacargas eléctrico |
| Gs. 43.900.000 | Mini excavadora |
| Gs. 38.600.000 | Grúa hidráulica de brazo plegable |
| Gs. 25.900.000 | Dumper sobre orugas |
| Gs. 22.700.000 | Elevador manual eléctrico mástil doble |
| Gs. 13.500.000 | Elevador manual eléctrico mástil simple |
| — | Minicargador compacto (skid steer) |

Mais **13 em ALQUILERES** (tijera 6/10/12/14/16 m, grúa araña a Gs. 450.000/dia,
montacargas, retroexcavadoras) e **30 de andaimes e acessórios**.

**Preencha:**

| Pergunta | Resposta |
|---|---|
| Quantos produtos temos no `/ventas/`? | |
| Quais **eles têm e nós não** (elevação/guindastes primeiro)? | |
| Quais **nós temos e eles não**? | |
| Publicamos preço? Exato, faixa ou nenhum? | |
| Temos tabela de specs com números reais? | |
| Onde moram os dados do catálogo (JSON? hardcoded? CMS?) | |

---

## Bloco 6 — Indexação real

```bash
# Do Paraguai (ou VPN py) — a busca do ambiente da análise é orientada aos EUA
# e não honra o operador site:, então este bloco NÃO foi validado.
```

| Pergunta | Como responder | Resposta |
|---|---|---|
| Quantas URLs nossas o Google indexou? | GSC → Cobertura, ou `site:gnhorizons.com` do PY | |
| Quantas do LUME? | `site:lumelogistica.com.py` do PY | |
| Quem ranqueia para "grúa araña Paraguay"? | google.com.py | |
| Quem ranqueia para "plataforma elevadora Paraguay"? | google.com.py | |
| Quem ranqueia para "alquiler de maquinaria Paraguay"? | google.com.py | |
| GSC está configurado? | | |

> ⚠️ **Achado que precisa de confirmação:** a LUME **não apareceu nem em busca por marca**,
> e para "alquiler de maquinaria Paraguay" quem aparece é **Rentex, Rentax Maquinarias,
> Bras Rental, SET Maquinarias e Construex**. Se isso se confirmar no `google.com.py`,
> **a LUME não é o concorrente de busca principal** e a lista de termos-alvo muda. Valide
> antes de investir pesado.

---

## Resumo para colar de volta

```
BLOCO 1 — URLs indexáveis: ___ (LUME: 110)
BLOCO 2 — Produtos visíveis sem JS: SIM / NÃO   ← o mais importante
BLOCO 3 — meta description: ___ | h1 único: ___ | JSON-LD Product: ___
BLOCO 4 — HTML transferido: ___ KB (LUME: 237) | TTFB: ___ s (LUME: 2,90 frio)
          Lighthouse mobile — GNH: ___ | LUME: ___
BLOCO 5 — Produtos no /ventas/: ___ (LUME ventas: 16)
          Faltam no nosso catálogo: ___
BLOCO 6 — URLs indexadas GNH: ___ | LUME: ___
          Quem ranqueia "grúa araña Paraguay": ___

DECISÃO: a Fase 1.1 (páginas estáticas por produto) segue sendo P0?  SIM / NÃO
```
