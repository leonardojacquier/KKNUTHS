import { sqlMkt } from '@/lib/db-mkt';
import { MarketingView } from './MarketingView';
import type { Dia, Origen, Busca, Pagina, Detalhe } from './MarketingView';

export const dynamic = 'force-dynamic';

const SITES = ['gnh', 'kasteller'] as const;
const PERIODOS = [7, 30, 90] as const;

type Props = { searchParams: Promise<{ site?: string; dias?: string }> };

export default async function Page({ searchParams }: Props) {
  const sp = await searchParams;

  // nunca interpolar querystring em SQL: aqui vira lista fechada
  const site = SITES.includes(sp.site as (typeof SITES)[number]) ? sp.site! : 'todos';
  const dias = PERIODOS.includes(Number(sp.dias) as (typeof PERIODOS)[number]) ? Number(sp.dias) : 30;

  const sitesFiltro = site === 'todos' ? [...SITES] : [site];

  const [porDia, origens, buscas, paginas, detalhes] = await Promise.all([
    sqlMkt`
      select site, dia::text, sesiones::int, personas::int, bots::int,
             con_contacto::int, eventos::int
        from hub.v_dia
       where site = any(${sitesFiltro}) and dia > current_date - ${dias}::int
       order by dia`,

    sqlMkt`
      select origen, sum(sesiones)::int as sesiones, sum(contactos)::int as contactos
        from hub.v_origen
       where site = any(${sitesFiltro}) and dia > current_date - ${dias}::int
       group by origen having sum(sesiones) > 0
       order by sesiones desc`,

    sqlMkt`
      select site, termino, sin_resultado, sum(veces)::int as veces,
             sum(sesiones)::int as sesiones, max(ultima) as ultima
        from hub.v_busqueda
       where site = any(${sitesFiltro}) and ultima > now() - (${dias}::int * interval '1 day')
       group by site, termino, sin_resultado
       order by sin_resultado desc, veces desc
       limit 40`,

    sqlMkt`
      select site, path, sesiones::int, contactos::int
        from hub.v_pagina
       where site = any(${sitesFiltro}) and ultima > now() - (${dias}::int * interval '1 day')
       order by sesiones desc
       limit 25`,

    sqlMkt`
      select site, type, detail, sum(veces)::int as veces, sum(sesiones)::int as sesiones
        from hub.v_detalle
       where site = any(${sitesFiltro})
         and type in ('product','producto','promo','ficha','negocio','coleccion','seccion')
         and ultima > now() - (${dias}::int * interval '1 day')
       group by site, type, detail
       order by sesiones desc
       limit 25`,
  ]);

  return (
    <MarketingView
      site={site}
      dias={dias}
      porDia={porDia as unknown as Dia[]}
      origens={origens as unknown as Origen[]}
      buscas={buscas as unknown as Busca[]}
      paginas={paginas as unknown as Pagina[]}
      detalhes={detalhes as unknown as Detalhe[]}
    />
  );
}
