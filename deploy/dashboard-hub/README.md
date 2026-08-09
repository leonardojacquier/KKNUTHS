# Hub de Marketing no portal `dashboard.vortex369.com.br`

Arquivos prontos para o portal Next.js que vive em `/opt/dashboard-gnh` na VPS.
A camada de dados **já está no ar** no Supabase; falta ligar o portal nela.

---

## O que já foi feito (não precisa refazer)

No Supabase `tqvrsusrbnyahpxhnwxe` ("Base de Dados Resultado - GNH"), schema **`hub`**:

| View | O que devolve |
|---|---|
| `hub.evento` | todos os eventos dos dois sites, com coluna `site` |
| `hub.sesion` | **uma linha por sessão**: origem, país, entrada, duração, se converteu, se parece bot |
| `hub.v_dia` | por site e dia: sessões, pessoas, bots, contatos, eventos |
| `hub.v_origen` | por site, dia e origem: sessões e contatos |
| `hub.v_busqueda` | termos buscados, separando **os que não acharam nada** |
| `hub.v_pagina` | por página: sessões, eventos, contatos |
| `hub.v_evento_dia` / `hub.v_detalle` | série por tipo de evento e o que foi clicado |

Mais o papel **`hub_reader`**, criado com `NOLOGIN` de propósito.

> [!note] Site novo entra com um `UNION`
> `hub.evento` é o único lugar que conhece as tabelas de origem. Um terceiro site
> vira mais um `UNION ALL` ali, e as seis views seguintes não mudam.

### O alcance do papel, conferido e não só desenhado

```
public.events (cru)   false      comex                 false
public.dre_mensal     false      public.leads          false
public.transacoes     false      hub.v_dia             TRUE
```

Se a senha do `hub_reader` vazar, o que se perde são seis views de marketing.
Financeiro, comex e leads continuam fechados.

---

## Passo 1 — dar senha ao papel (você, no SQL Editor do Supabase)

Não coloquei senha nesta migration de propósito: senha em arquivo versionado ou em
janela de chat é senha queimada.

```sql
alter role hub_reader login password 'ESCOLHA_UMA_SENHA_FORTE';
```

## Passo 2 — a linha no `.env.local` da VPS

```bash
# /opt/dashboard-gnh/.env.local   (NÃO commitar)
MKT_DATABASE_URL="postgresql://hub_reader.tqvrsusrbnyahpxhnwxe:SENHA@HOST_DO_POOLER:6543/postgres"
```

O `HOST_DO_POOLER` sai do painel: **Project Settings → Database → Connection pooling**,
modo *Transaction*. Copie a string de lá e troque só o usuário e a senha — o usuário
no pooler tem que ser `hub_reader.tqvrsusrbnyahpxhnwxe`, com o ref do projeto colado
depois do ponto. É exigência do Supavisor, não invenção nossa.

> [!warning] Não use a conexão direta `db.<ref>.supabase.co:5432`
> Ela é IPv6 e a VPS pode não ter rota. O pooler é IPv4 e é o caminho certo para
> aplicação. É também por isso que `db-mkt.ts` traz `prepare: false`: em modo
> transação o pooler não guarda prepared statements entre consultas.

Teste antes de mexer no portal:

```bash
psql "$MKT_DATABASE_URL" -c "select site, sum(personas) from hub.v_dia where dia > current_date - 30 group by 1;"
```

## Passo 3 — copiar os arquivos

```
src/lib/db-mkt.ts                              ← novo
src/app/(app)/marketing/page.tsx               ← novo (Server Component)
src/app/(app)/marketing/MarketingView.tsx      ← novo ('use client')
```

Seguem o padrão de `comercial/equipamentos`: a página faz a query, o componente
client desenha. Usam só `recharts` e `lucide-react`, que já são dependências —
**nenhuma biblioteca nova**.

## Passo 4 — menu, em `src/components/Sidebar.tsx`

Novo grupo no array `groups`:

```ts
{
  title: 'MARKETING',
  accent: 'green',
  items: [
    { href: '/marketing', label: 'Hub de Marketing' },
  ],
},
```

## Passo 5 — permissão, em `data/usuarios.json`

Adicione `"/marketing"` ao `allowed` de quem deve enxergar. **Sem isso a página some
até para você** — grupo sem item visível não aparece.

## Passo 6 — build e restart

```bash
cd /opt/dashboard-gnh
npm run build          # revise a saída antes de reiniciar
pm2 restart dashboard-gnh
pm2 logs dashboard-gnh --lines 30
```

Fora do horário comercial: o restart derruba o portal por alguns segundos.

---

## O que ainda não está aqui

- **Performance (Core Web Vitals)** — a view existe no plano mas os sites ainda não
  mandam LCP/INP/CLS. É a Fase 3.
- **Campanhas por `utm_campaign`** — hoje a origem é por rede (`ref`). Campanha
  individual entra junto com o pacote de campanha, na Fase 2.
- **Search Console** — depende de conta ligada.

## Por que estes arquivos vivem no repositório do site

O `/opt/dashboard-gnh` é um git **sem remote**: existe só na VPS. Enquanto for assim,
o código do hub fica versionado aqui e é copiado de lá. Se um dia o portal for para o
GitHub, esta pasta vira o material do primeiro PR e some daqui.

---

**Ver também:** `docs/vault-gnh/GNH - Sitio Web/13 - Plano - Painel e Central de Campanhas.md`
