# Kasteller — Buscador de produtos e palavras-chave

> Site: https://kasteller.com.py/ (provisório enquanto o DNS não sobe: https://gnh.vortex369.com.br/assets/kasteller2/)
> Fonte: repo KKNUTHS, `assets/kasteller2/buscador/` · branch `claude/professional-website-design-qqgnfg`

## O que é

Busca instantânea do catálogo multi-marcas na seção **#buscador** ("Catálogo" no menu):
**1.018 produtos** de 6 fábricas (Portinari 580, Ceusa 191, Castelli 84, Roca 75,
Incepa 48, Castelatto 40), com 894 fotos WebP servidas do nosso domínio.
Filtra enquanto digita, insensível a acentos, termos combinam em **E**
("madera terraza" → só o que é os dois). Sugestões por faceta viram chips.

## Taxonomia de palavras-chave (3 camadas)

Cada produto carrega, além de nome/marca/linha:

1. **Facetas** (viram chip de filtro): Marca · Tipo · Visual (mármol/madera/piedra/
   cemento/ladrillo/metal/artesanal) · Acabado (polido/mate/acetinado/natural/externo)
   · Formato · **Uso/Ambiente**.
2. **Ambientes** (na faceta Uso/Ambiente, derivados por regra técnica):
   - `cocina`, `baño` → catálogo todo (parede sempre serve; triagem fina é showroom)
   - `living` → tem piso · `dormitorio` → piso interno (não-externo)
   - `exterior`, `terraza`, `cochera`, `fachada` → acabado externo/hard/grip
   - `piscina` → borda/atérmico/fulget + pedras Castelatto (26 produtos, restrito de propósito)
3. **Sinônimos e estilo** (invisíveis, só buscáveis, nas tags):
   - **Trilíngue ES/PT/EN**: banheiro/baño/bathroom, cozinha/cocina, cinza/gris/grey,
     preto/negro, mármore/marmol/marble, madeira/madera/wood, pulido/brilhante,
     fosco/mate, antiderrapante/antideslizante/grip, garagem/garaje,
     quincho/churrasqueira/varanda, pileta/piscina, tijolo/ladrillo…
   - **Estilo/caráter** (classificado por visual+acabado+cor+formato):
     sofisticado, clásico/clássico, moderno, minimalista, elegante, rústico,
     industrial, lujo/luxo, acogedor/aconchegante, atemporal, clean, vintage,
     urbano, dramático, luminoso… Ex.: mármol polido → elegante+clásico+luxo;
     cemento → industrial+moderno+minimalista; negro → dramático+sofisticado.
   - **Typos reais capturados**: `cozina` (visto no analytics 02/08).

## Ciclo de melhoria (a lógica da GNH)

O buscador registra sozinho no Supabase (projeto **Base de Dados Resultado - GNH**,
`tqvrsusrbnyahpxhnwxe`, tabela `kasteller_events`, INSERT-only):
`busqueda` · `busqueda-vacia` · `filtro` · `producto` (+ landing, seccion, menu,
coleccion, unicci, hero-payoff, clone).

**Revisão periódica** — o que buscar e não achar vira palavra-chave nova:

```sql
select detail, count(*) n, max(created_at) ultimo
from kasteller_events
where type = 'busqueda-vacia'
group by detail order by n desc;
```

Caso real (02/08/2026): "Sofisti…" buscado 5× sem resultado, "Classico" e "Cozina"
idem → viraram a camada de estilos + typo no dia seguinte.

## Como acrescentar palavras-chave

1. Editar `preview-kasteller/buscador-fonte/enriquecer_ambientes.py`
   (mapas `SINONIMOS`, `SIN_AMBIENTE`, função `estilos_de`).
2. Rodar: `python3 enriquecer_ambientes.py ../../assets/kasteller2/buscador/productos.json`
   — é **idempotente** (rodar 2× não duplica).
3. Commit + push → autodeploy publica em ~2 min.

Após re-scrape do catálogo (pasta `scraper/` em `buscador-fonte/`), rodar o
script de novo — o JSON novo chega cru.

## Pendências

- [ ] 124 produtos sem foto (Castelli 84 + Castelatto 40 — bloqueiam download);
      buscar manualmente pelas páginas de produto (`img_origen` no JSON)
- [ ] Tolerância a typo no próprio JS do buscador (tipo o `casiIgual` da GNH) —
      hoje typos são cobertos só por sinônimos estáticos
- [ ] Confirmar com o dono se Mondialle fica no carrossel de marcas
