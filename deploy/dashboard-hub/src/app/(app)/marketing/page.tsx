import { sqlMkt } from '@/lib/db-mkt';
import { MarketingView } from './MarketingView';
import type { Dia, Origen, Pais, Busca, Pagina, Detalhe, Hora, Aparato, Campana, Insight } from './MarketingView';

export const dynamic = 'force-dynamic';

const SITES = ['gnh', 'kasteller'] as const;
const PERIODOS = [7, 30, 90] as const;

type Props = { searchParams: Promise<{ site?: string; dias?: string; bots?: string; t?: string }> };

const ABAS = ['resumen', 'origen', 'conducta'] as const;

export default async function Page({ searchParams }: Props) {
  const sp = await searchParams;

  // nunca interpolar querystring em SQL: aqui vira lista fechada
  const site = SITES.includes(sp.site as (typeof SITES)[number]) ? sp.site! : 'todos';
  const dias = PERIODOS.includes(Number(sp.dias) as (typeof PERIODOS)[number]) ? Number(sp.dias) : 30;
  const sitesFiltro = site === 'todos' ? [...SITES] : [site];
  // por padrão os crawlers ficam de fora: 63 sessões en-US sem um clique
  // distorcem qualquer leitura de público. O botão deixa ver o bruto.
  const verBots = sp.bots === '1';
  const aba = ABAS.includes(sp.t as (typeof ABAS)[number]) ? sp.t! : 'resumen';

  const [porDia, anterior, origens, paises, buscas, paginas, detalhes, horas, aparatos, campanas] = await Promise.all([
    sqlMkt`
      select site, dia::text, sesiones::int, personas::int, bots::int,
             con_contacto::int, eventos::int, duracion_media_seg::int
        from hub.v_dia
       where site = any(${sitesFiltro}) and dia > current_date - ${dias}::int
       order by dia`,

    // mesma janela, deslocada para trás — é o que dá sentido ao "subiu/caiu"
    sqlMkt`
      select sum(personas)::int as personas, sum(con_contacto)::int as contactos
        from hub.v_dia
       where site = any(${sitesFiltro})
         and dia > current_date - ${dias * 2}::int and dia <= current_date - ${dias}::int`,

    sqlMkt`
      select origen, sum(sesiones)::int as sesiones, sum(contactos)::int as contactos,
             sum(sesiones_todas)::int as sesiones_todas, sum(bots)::int as bots
        from hub.v_origen
       where site = any(${sitesFiltro}) and dia > current_date - ${dias}::int
       group by origen having sum(sesiones_todas) > 0
       order by sesiones_todas desc`,

    sqlMkt`
      select pais, sum(sesiones)::int as sesiones, sum(contactos)::int as contactos,
             sum(sesiones_todas)::int as sesiones_todas, sum(bots)::int as bots
        from hub.v_pais
       where site = any(${sitesFiltro}) and dia > current_date - ${dias}::int
       group by pais having sum(sesiones_todas) > 0
       order by sesiones_todas desc`,

    sqlMkt`
      select site, termino, sin_resultado, sum(veces)::int as veces,
             sum(sesiones)::int as sesiones, max(ultima) as ultima
        from hub.v_busqueda
       where site = any(${sitesFiltro}) and ultima > now() - (${dias}::int * interval '1 day')
       group by site, termino, sin_resultado
       order by sin_resultado desc, sesiones desc, veces desc
       limit 120`,

    sqlMkt`
      select site, path, sesiones::int, contactos::int
        from hub.v_pagina
       where site = any(${sitesFiltro}) and ultima > now() - (${dias}::int * interval '1 day')
       order by sesiones desc
       limit 60`,

    sqlMkt`
      select site, type, detail, sum(veces)::int as veces, sum(sesiones)::int as sesiones
        from hub.v_detalle
       where site = any(${sitesFiltro})
         and type in ('product','producto','promo','ficha','negocio','coleccion','seccion','filtro','porta','idioma')
         and ultima > now() - (${dias}::int * interval '1 day')
       group by site, type, detail
       order by sesiones desc
       limit 120`,

    sqlMkt`
      select hora::int, sum(sesiones)::int as sesiones, sum(contactos)::int as contactos
        from hub.v_hora
       where site = any(${sitesFiltro})
       group by hora order by hora`,

    sqlMkt`
      select aparato, sum(sesiones)::int as sesiones, sum(contactos)::int as contactos
        from hub.v_aparato
       where site = any(${sitesFiltro}) and dia > current_date - ${dias}::int
       group by aparato having sum(sesiones) > 0
       order by sesiones desc`,

    sqlMkt`
      select campana, origen, sum(sesiones)::int as sesiones, sum(contactos)::int as contactos
        from hub.v_campana
       where site = any(${sitesFiltro}) and dia > current_date - ${dias}::int
       group by campana, origen having sum(sesiones) > 0
       order by sesiones desc
       limit 40`,
  ]);

  const insights = analisar(
    porDia as unknown as Dia[],
    (anterior as unknown as { personas: number | null; contactos: number | null }[])[0],
    origens as unknown as Origen[],
    paises as unknown as Pais[],
    buscas as unknown as Busca[],
    paginas as unknown as Pagina[],
    dias,
  );

  return (
    <MarketingView
      site={site}
      dias={dias}
      verBots={verBots}
      aba={aba}
      aparatos={aparatos as unknown as Aparato[]}
      campanas={campanas as unknown as Campana[]}
      porDia={porDia as unknown as Dia[]}
      origens={origens as unknown as Origen[]}
      paises={paises as unknown as Pais[]}
      buscas={buscas as unknown as Busca[]}
      paginas={paginas as unknown as Pagina[]}
      detalhes={detalhes as unknown as Detalhe[]}
      horas={horas as unknown as Hora[]}
      insights={insights}
    />
  );
}

/* ============================================================
   Leitura automática dos números — regras explícitas, sem IA.
   Cada regra exige uma amostra mínima: com 30 sessões, "conversão
   caiu 50%" costuma ser uma pessoa a menos, não uma tendência.
   ============================================================ */
function analisar(
  porDia: Dia[],
  anterior: { personas: number | null; contactos: number | null } | undefined,
  origens: Origen[],
  paises: Pais[],
  buscas: Busca[],
  paginas: Pagina[],
  dias: number,
): Insight[] {
  const out: Insight[] = [];
  const personas = porDia.reduce((s, d) => s + d.personas, 0);
  const contactos = porDia.reduce((s, d) => s + d.con_contacto, 0);
  const bots = porDia.reduce((s, d) => s + d.bots, 0);
  const tasa = personas ? contactos / personas : 0;

  // ---- volume vs. período anterior ----
  const antes = anterior?.personas ?? 0;
  if (antes >= 30 && personas >= 30) {
    const var_ = ((personas - antes) / antes) * 100;
    if (Math.abs(var_) >= 20) {
      out.push({
        tono: var_ > 0 ? 'bueno' : 'alerta',
        titulo: `Visitas ${var_ > 0 ? 'subieron' : 'cayeron'} ${Math.abs(var_).toFixed(0)}%`,
        texto: `${personas} personas en ${dias} días, contra ${antes} en los ${dias} anteriores.`,
        accion: var_ > 0 ? 'Mirá abajo qué origen creció y reforzá ahí.' : 'Revisá si alguna campaña terminó o si una página cayó de posición.',
      });
    }
  }

  // ---- buscas sem resultado: o pedido explícito que o site não atendeu ----
  const vazias = buscas.filter((b) => b.sin_resultado);
  const vaziasFortes = vazias.filter((b) => b.sesiones >= 2);
  if (vaziasFortes.length) {
    out.push({
      tono: 'alerta',
      titulo: `${vaziasFortes.length} término${vaziasFortes.length > 1 ? 's' : ''} que más de una persona buscó y no encontró`,
      texto: vaziasFortes.slice(0, 5).map((b) => `“${b.termino}” (${b.sesiones})`).join(', '),
      accion: 'Si el producto existe, falta la palabra en el catálogo. Si no existe, es demanda real sin oferta.',
    });
  }

  // ---- página com público e sem conversa ----
  const paradas = paginas.filter((p) => p.sesiones >= 15 && p.contactos === 0);
  if (paradas.length) {
    out.push({
      tono: 'alerta',
      titulo: `${paradas.length} página${paradas.length > 1 ? 's' : ''} con visitas y cero contactos`,
      texto: paradas.slice(0, 4).map((p) => `${p.path} (${p.sesiones})`).join(', '),
      accion: 'Gente llega y no habla. Revisá si hay CTA de WhatsApp visible sin scroll.',
    });
  }

  // ---- origem que converte muito acima da média ----
  if (tasa > 0) {
    const boas = origens
      .filter((o) => o.sesiones >= 5 && o.contactos > 0 && o.contactos / o.sesiones >= tasa * 2)
      .sort((a, b) => b.contactos / b.sesiones - a.contactos / a.sesiones);
    if (boas.length) {
      const o = boas[0];
      out.push({
        tono: 'bueno',
        titulo: `“${o.origen}” convierte ${((o.contactos / o.sesiones) / tasa).toFixed(1)}× más que el promedio`,
        texto: `${o.contactos} contactos en ${o.sesiones} sesiones (promedio del sitio: ${(tasa * 100).toFixed(1)}%).`,
        accion: 'Poco volumen, buena calidad: vale invertir más ahí.',
      });
    }
  }

  // ---- país com muita gente e nenhuma conversa ----
  const paisMudo = paises.filter((p) => p.pais !== 'Desconocido' && p.sesiones >= 20 && p.contactos === 0);
  for (const p of paisMudo.slice(0, 2)) {
    out.push({
      tono: 'alerta',
      titulo: `${p.sesiones} visitas de ${p.pais}, ningún contacto`,
      texto: 'Público que llega pero no habla.',
      accion: p.pais === 'Brasil'
        ? 'Puede ser idioma: el sitio está en español y el visitante piensa en portugués.'
        : 'Revisá si la oferta encaja con ese mercado.',
    });
  }

  // ---- bots demais ----
  if (personas + bots >= 50 && bots / (personas + bots) >= 0.25) {
    out.push({
      tono: 'neutro',
      titulo: `${((bots / (personas + bots)) * 100).toFixed(0)}% del tráfico son bots`,
      texto: `${bots} sesiones filtradas de ${personas + bots}.`,
      accion: 'No es un problema: son crawlers indexando. Los números de arriba ya los excluyen.',
    });
  }

  // ---- silêncio ----
  const ultimoContacto = [...porDia].reverse().find((d) => d.con_contacto > 0);
  if (personas >= 30 && !ultimoContacto) {
    out.push({
      tono: 'alerta',
      titulo: `Ningún contacto en ${dias} días`,
      texto: `${personas} personas entraron y nadie escribió.`,
      accion: 'Probá el botón de WhatsApp del sitio: puede estar roto.',
    });
  }

  // ---- origem sem dado (histórico) ----
  const semDado = origens.find((o) => o.origen === 'sin dato');
  if (semDado && personas && semDado.sesiones / personas >= 0.5) {
    out.push({
      tono: 'neutro',
      titulo: 'La mitad de las sesiones son anteriores al registro de origen',
      texto: `${semDado.sesiones} sesiones sin origen conocido (empezamos a registrarlo el 09/08/2026).`,
      accion: 'En una semana esta tabla ya se lee sola. No es tráfico directo.',
    });
  }

  if (!out.length) {
    out.push({
      tono: 'neutro',
      titulo: 'Nada que exija acción hoy',
      texto: 'Ninguna regla se disparó con los datos de este período.',
      accion: 'Volvé a mirar en unos días, o ampliá el período arriba.',
    });
  }
  return out;
}
