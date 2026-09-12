---
titulo: Operação diária
tags: [gnh, operacao, receitas, howto]
atualizado: 2026-07-29
---

# Operação diária

[[00 - Indice|← Índice]]

Receitas prontas para as tarefas que mais aparecem.

---

## Publicar qualquer mudança

```bash
git add -A
git commit -m "descrição do que mudou"
git push -u origin claude/professional-website-design-qqgnfg
```

Pronto — o cron do VPS publica em até 2 minutos. Confira com `Ctrl+Shift+R`.

---

## Adicionar um produto novo ao catálogo

1. Abrir `gnh-hero/src/catalogo-data.ts`
2. Adicionar o produto no array da categoria certa:
   ```ts
   { name: 'Nome do Produto', brand: 'ZS', img: '../img/prod/arquivo.png',
     note: 'Descrição curta e técnica.',
     tags: ['termo1', 'termo2', 'sinônimo em português'] }
   ```
3. Se tiver specs, adicionar a tabela no mapa de specs:
   ```ts
   'Nome do Produto': { h: ['Modelo', 'Capacidad', 'Peso'], r: [
     ['M-1', '100 kg', '230 kg'],
   ] },
   ```
4. Rodar os geradores e publicar:
   ```bash
   cd gnh-hero && npm run build && node tools/build-productos.cjs && cd ..
   # copiar bundles + páginas para assets/nuevo — ver a nota Deploy
   node gnh-hero/tools/build-sitemap.cjs
   ```

> [!tip] Inclua sinônimos em português nas `tags`
> É o que faz o visitante brasileiro achar o produto.

---

## Criar fichas técnicas de uma família nova

Copiar `gnh-hero/tools/build-plataformas.cjs` como base — ele já lê o CSS compartilhado.
Ajustar o array `MODELOS`, a cor da família e os textos. Depois:

```bash
node tools/build-<familia>.cjs
node tools/make-pdfs.cjs
```

---

## Trocar a promoção

Ver o passo a passo completo em [[07 - Promocoes e campanhas]]. Resumo:
nova pasta em `assets/nuevo/promo/`, imagem OG 1200×630, atualizar `PROMOS` em
`ventas.ts`, build, sitemap, push.

---

## Trocar um vídeo ou uma foto do site

> [!warning] Renomeie o arquivo
> Estáticos ficam em cache no navegador. Sobrescrever `hero.webm` não adianta —
> use `hero2.webm` e atualize a referência no HTML.

---

## Ver os números do dia

- **Telegram**: o resumo chega sozinho às 20h
- **Consulta direta** (SQL no Supabase):
  ```sql
  select public.resumen_dia('<token>', 0);  -- 0 = hoje, 1 = ontem
  ```
  O token está em `/opt/gnh_lib/gnh-resumen.env`

---

## Investigar um pico de acessos

```sql
-- sessões do dia com perfil e nº de interações
select session_id,
       max(case when type='landing' then detail end) as landing,
       count(*) filter (where type <> 'landing') as interacoes,
       min(created_at at time zone 'America/Asuncion') as inicio
from events
where (created_at at time zone 'America/Asuncion')::date = '2026-07-27'
group by session_id order by inicio;
```

Várias sessões **no mesmo minuto**, com fuso de nuvem, en-US e zero interação = crawler.
O `resumen_dia` já filtra isso automaticamente ([[05 - Analytics e rastreamento]]).

---

## Ver o que as pessoas digitaram na busca

```sql
select to_char(created_at at time zone 'America/Asuncion','DD/MM HH24:MI') as quando,
       type, detail, left(session_id,4) as sessao
from events
where type in ('busqueda','busqueda-vacia')
  and created_at >= now() - interval '10 days'
order by created_at;
```

`busqueda-vacia` é ouro: é o catálogo dizendo o que falta.

---

## Diagnóstico rápido quando algo parece errado

| Sintoma | Onde olhar |
|---|---|
| Site não atualizou | `tail /var/log/gnh-autodeploy.log` no VPS |
| Site fora do ar | Bloco `gnhorizons.com` ainda existe no Caddyfile? ([[02 - Infraestrutura e DNS]]) |
| Página nova não indexa | Está no `sitemap.xml`? Rodou `build-sitemap.cjs` por último? |
| Ficha sem PDF | Rodou `make-pdfs.cjs` depois de gerar a ficha? |
| Preview do link sem foto | `og:image` é URL absoluta? Passou no Sharing Debugger? |
| Resumo não chegou | Cron das 20h + `/opt/gnh_lib/gnh-resumen.env` |

---

**Ver também:** [[03 - Deploy]] · [[04 - Catalogo e fichas tecnicas]]
