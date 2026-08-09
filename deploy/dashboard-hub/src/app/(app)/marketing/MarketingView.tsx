'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';
import { Users, MessageCircle, Percent, Search, Globe, FileText } from 'lucide-react';

export type Dia = { site: string; dia: string; sesiones: number; personas: number; bots: number; con_contacto: number; eventos: number };
export type Origen = { origen: string; sesiones: number; contactos: number };
export type Busca = { site: string; termino: string; sin_resultado: boolean; veces: number; sesiones: number; ultima: string };
export type Pagina = { site: string; path: string; sesiones: number; contactos: number };
export type Detalhe = { site: string; type: string; detail: string; veces: number; sesiones: number };

type Props = {
  site: string; dias: number;
  porDia: Dia[]; origens: Origen[]; buscas: Busca[]; paginas: Pagina[]; detalhes: Detalhe[];
};

/** Nomes que o time entende, no lugar do slug técnico da coluna `ref`. */
const ORIGEM_LABEL: Record<string, string> = {
  'directo': 'Directo (link, app, QR)',
  'sin dato': 'Sin dato (antes del 09/08)',
  'google': 'Google — búsqueda',
  'google-maps': 'Google Maps',
  'google-business': 'Ficha de Google',
  'instagram': 'Instagram',
  'facebook': 'Facebook',
  'whatsapp': 'WhatsApp',
  'tiktok': 'TikTok',
  'linkedin': 'LinkedIn',
  'buscador': 'Otro buscador',
  'chatgpt': 'ChatGPT',
  'perplexity': 'Perplexity',
  'gemini': 'Gemini',
  'claude': 'Claude',
  'interno': 'Navegación interna',
};

export function MarketingView({ site, dias, porDia, origens, buscas, paginas, detalhes }: Props) {
  const kpi = useMemo(() => {
    const personas = porDia.reduce((s, d) => s + d.personas, 0);
    const contactos = porDia.reduce((s, d) => s + d.con_contacto, 0);
    const bots = porDia.reduce((s, d) => s + d.bots, 0);
    return { personas, contactos, bots, tasa: personas ? (contactos / personas) * 100 : 0 };
  }, [porDia]);

  // uma linha por site no mesmo gráfico: junta os dias das duas séries
  const serie = useMemo(() => {
    const por: Record<string, Record<string, number | string>> = {};
    for (const d of porDia) {
      por[d.dia] ??= { dia: d.dia.slice(5) };
      por[d.dia][d.site] = d.personas;
    }
    return Object.keys(por).sort().map((k) => por[k]);
  }, [porDia]);

  const vazias = buscas.filter((b) => b.sin_resultado);
  const comResultado = buscas.filter((b) => !b.sin_resultado);

  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy">Hub de Marketing</h1>
          <p className="text-sm text-slate-500">
            gnhorizons.com e kasteller.com.py — sesiones, origen, búsquedas y conversión.
          </p>
        </div>
        <div className="flex gap-2">
          <Filtro atual={site} campo="site" opcoes={[['todos', 'Los dos'], ['gnh', 'GNH'], ['kasteller', 'Kasteller']]} dias={dias} site={site} />
          <Filtro atual={String(dias)} campo="dias" opcoes={[['7', '7 días'], ['30', '30 días'], ['90', '90 días']]} dias={dias} site={site} />
        </div>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi icon={<Users size={18} />} label="Personas" valor={kpi.personas.toLocaleString('es-PY')}
             nota={`${kpi.bots} bots filtrados`} />
        <Kpi icon={<MessageCircle size={18} />} label="Contactos" valor={String(kpi.contactos)}
             nota="clics de WhatsApp y leads" />
        <Kpi icon={<Percent size={18} />} label="Conversión" valor={`${kpi.tasa.toFixed(1)}%`}
             nota="contactos por persona" />
        <Kpi icon={<Search size={18} />} label="Búsquedas sin resultado" valor={String(vazias.length)}
             nota="lo que buscan y no está" destaque={vazias.length > 0} />
      </div>

      <Card titulo="Personas por día">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={serie}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E7EAF0" />
              <XAxis dataKey="dia" fontSize={12} />
              <YAxis allowDecimals={false} fontSize={12} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="gnh" name="GNH" stroke="#F26D21" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="kasteller" name="Kasteller" stroke="#2E7D5B" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card titulo="De dónde vienen" icon={<Globe size={16} />}>
          <Tabela cabecalho={['Origen', ['Sesiones', 'num'], ['Contactos', 'num'], ['Conv.', 'num']]}>
            {origens.map((o) => (
              <tr key={o.origen} className="border-t border-slate-100">
                <td className="py-2 pr-3">{ORIGEM_LABEL[o.origen] ?? o.origen}</td>
                <td className="py-2 text-right tabular-nums">{o.sesiones}</td>
                <td className="py-2 text-right tabular-nums">{o.contactos}</td>
                <td className="py-2 text-right tabular-nums text-slate-500">
                  {o.sesiones ? `${((o.contactos / o.sesiones) * 100).toFixed(0)}%` : '—'}
                </td>
              </tr>
            ))}
          </Tabela>
          {origens.some((o) => o.origen === 'sin dato') && (
            <p className="mt-3 text-xs text-slate-500">
              «Sin dato» son sesiones anteriores al 09/08/2026, cuando empezamos a registrar el origen.
              No son visitas directas — simplemente no lo sabemos.
            </p>
          )}
        </Card>

        <Card titulo="Búsquedas sin resultado" icon={<Search size={16} />}>
          {vazias.length === 0 ? (
            <p className="text-sm text-slate-500">Nadie buscó algo que no esté. Buena señal.</p>
          ) : (
            <Tabela cabecalho={['Término', 'Sitio', ['Veces', 'num']]}>
              {vazias.map((b) => (
                <tr key={`${b.site}-${b.termino}`} className="border-t border-slate-100">
                  <td className="py-2 pr-3 font-medium">{b.termino}</td>
                  <td className="py-2 text-slate-500">{b.site}</td>
                  <td className="py-2 text-right tabular-nums">{b.veces}</td>
                </tr>
              ))}
            </Tabela>
          )}
          <p className="mt-3 text-xs text-slate-500">
            Cada línea es alguien que buscó y se fue con las manos vacías: o falta el producto, o falta la palabra.
          </p>
        </Card>

        <Card titulo="Lo más buscado" icon={<Search size={16} />}>
          <Tabela cabecalho={['Término', 'Sitio', ['Veces', 'num']]}>
            {comResultado.slice(0, 15).map((b) => (
              <tr key={`${b.site}-${b.termino}`} className="border-t border-slate-100">
                <td className="py-2 pr-3">{b.termino}</td>
                <td className="py-2 text-slate-500">{b.site}</td>
                <td className="py-2 text-right tabular-nums">{b.veces}</td>
              </tr>
            ))}
          </Tabela>
        </Card>

        <Card titulo="Páginas" icon={<FileText size={16} />}>
          <Tabela cabecalho={['Página', 'Sitio', ['Sesiones', 'num'], ['Contactos', 'num']]}>
            {paginas.map((p) => (
              <tr key={`${p.site}-${p.path}`} className="border-t border-slate-100">
                <td className="max-w-[18rem] truncate py-2 pr-3" title={p.path}>{p.path}</td>
                <td className="py-2 text-slate-500">{p.site}</td>
                <td className="py-2 text-right tabular-nums">{p.sesiones}</td>
                <td className="py-2 text-right tabular-nums">{p.contactos}</td>
              </tr>
            ))}
          </Tabela>
        </Card>
      </div>

      <Card titulo="Lo que abren y clican">
        <Tabela cabecalho={['Qué', 'Tipo', 'Sitio', ['Sesiones', 'num']]}>
          {detalhes.map((d) => (
            <tr key={`${d.site}-${d.type}-${d.detail}`} className="border-t border-slate-100">
              <td className="max-w-[22rem] truncate py-2 pr-3" title={d.detail}>{d.detail}</td>
              <td className="py-2 text-slate-500">{d.type}</td>
              <td className="py-2 text-slate-500">{d.site}</td>
              <td className="py-2 text-right tabular-nums">{d.sesiones}</td>
            </tr>
          ))}
        </Tabela>
      </Card>
    </div>
  );
}

/* ---------- peças ---------- */

function Filtro({ atual, campo, opcoes, site, dias }: {
  atual: string; campo: 'site' | 'dias'; opcoes: [string, string][]; site: string; dias: number;
}) {
  return (
    <div className="flex overflow-hidden rounded-lg border border-slate-200">
      {opcoes.map(([valor, label]) => {
        const params = new URLSearchParams({ site, dias: String(dias) });
        params.set(campo, valor);
        const ativo = atual === valor;
        return (
          <Link
            key={valor}
            href={`/marketing?${params}`}
            className={`px-3 py-2 text-sm ${ativo ? 'bg-orange-soft font-bold text-navy' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
          >
            {label}
          </Link>
        );
      })}
    </div>
  );
}

function Kpi({ icon, label, valor, nota, destaque }: {
  icon: React.ReactNode; label: string; valor: string; nota?: string; destaque?: boolean;
}) {
  return (
    <div className={`rounded-xl border bg-white p-4 ${destaque ? 'border-orange' : 'border-slate-200'}`}>
      <div className="flex items-center gap-2 text-slate-500">{icon}<span className="text-sm">{label}</span></div>
      <div className="mt-1 text-3xl font-bold tabular-nums text-navy">{valor}</div>
      {nota && <div className="mt-1 text-xs text-slate-500">{nota}</div>}
    </div>
  );
}

function Card({ titulo, icon, children }: { titulo: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="mb-3 flex items-center gap-2 font-bold text-navy">{icon}{titulo}</h2>
      {children}
    </section>
  );
}

/** Coluna é `'Nome'` (texto, à esquerda) ou `['Nome', 'num']` (número, à direita).
 *  Sem isso o cabeçalho de "Sitio" ficava à direita e a célula à esquerda. */
type Col = string | [string, 'num'];

function Tabela({ cabecalho, children }: { cabecalho: Col[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-slate-400">
            {cabecalho.map((c) => {
              const [label, tipo] = Array.isArray(c) ? c : [c, 'txt'];
              return (
                <th key={label} className={`pb-2 ${tipo === 'num' ? 'text-right' : 'text-left'}`}>
                  {label}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
