'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend, Cell,
} from 'recharts';
import {
  Users, MessageCircle, Percent, Search, Globe, FileText, MapPin, Clock, MousePointerClick, Lightbulb,
  Megaphone, Smartphone,
} from 'lucide-react';

export type Dia = { site: string; dia: string; sesiones: number; personas: number; bots: number; con_contacto: number; eventos: number; duracion_media_seg: number };
export type Origen = { origen: string; sesiones: number; contactos: number; sesiones_todas: number; bots: number };
export type Pais = { pais: string; sesiones: number; contactos: number; sesiones_todas: number; bots: number };
export type Busca = { site: string; termino: string; sin_resultado: boolean; veces: number; sesiones: number; ultima: string };
export type Pagina = { site: string; path: string; sesiones: number; contactos: number };
export type Detalhe = { site: string; type: string; detail: string; veces: number; sesiones: number };
export type Hora = { hora: number; sesiones: number; contactos: number };
export type Aparato = { aparato: string; sesiones: number; contactos: number };
export type Campana = { campana: string; origen: string; sesiones: number; contactos: number };
export type Insight = { tono: 'bueno' | 'alerta' | 'neutro'; titulo: string; texto: string; accion: string };

type Props = {
  site: string; dias: number; verBots: boolean; aba: string;
  porDia: Dia[]; origens: Origen[]; paises: Pais[]; buscas: Busca[];
  paginas: Pagina[]; detalhes: Detalhe[]; horas: Hora[];
  aparatos: Aparato[]; campanas: Campana[]; insights: Insight[];
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
  'x': 'X / Twitter',
  'buscador': 'Otro buscador',
  'chatgpt': 'ChatGPT',
  'perplexity': 'Perplexity',
  'gemini': 'Gemini',
  'claude': 'Claude',
  'interno': 'Navegación interna',
};

/** O `type` do evento em palavras de gente. */
const TIPO_LABEL: Record<string, string> = {
  product: 'Producto', producto: 'Producto', promo: 'Promoción', ficha: 'Ficha técnica',
  negocio: 'Unidad de negocio', coleccion: 'Colección', seccion: 'Sección vista',
  filtro: 'Filtro usado', porta: 'Puerta de entrada', idioma: 'Idioma elegido',
};

const APARATO_LABEL: Record<string, string> = {
  celular: 'Celular', computadora: 'Computadora', tablet: 'Tablet',
  'sin dato': 'Sin dato (antes del 10/08)',
};

export function MarketingView({
  site, dias, verBots, aba, porDia, origens, paises, buscas, paginas, detalhes, horas,
  aparatos, campanas, insights,
}: Props) {
  // com bots ligado, a coluna de sessões passa a ser o número bruto
  const ses = (r: { sesiones: number; sesiones_todas: number }) => (verBots ? r.sesiones_todas : r.sesiones);
  const kpi = useMemo(() => {
    const personas = porDia.reduce((s, d) => s + d.personas, 0);
    const contactos = porDia.reduce((s, d) => s + d.con_contacto, 0);
    const bots = porDia.reduce((s, d) => s + d.bots, 0);
    const dur = porDia.filter((d) => d.personas > 0);
    const duracion = dur.length ? dur.reduce((s, d) => s + d.duracion_media_seg, 0) / dur.length : 0;
    return { personas, contactos, bots, duracion, tasa: personas ? (contactos / personas) * 100 : 0 };
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

  // horas sem visita nenhuma viram buraco no gráfico — melhor mostrar as 24
  const serieHoras = useMemo(() => {
    const mapa = new Map(horas.map((h) => [h.hora, h]));
    return Array.from({ length: 24 }, (_, h) => ({
      hora: String(h).padStart(2, '0'),
      sesiones: mapa.get(h)?.sesiones ?? 0,
      contactos: mapa.get(h)?.contactos ?? 0,
    }));
  }, [horas]);
  const picoHora = useMemo(
    () => serieHoras.reduce((a, b) => (b.sesiones > a.sesiones ? b : a), serieHoras[0]),
    [serieHoras],
  );

  const vazias = buscas.filter((b) => b.sin_resultado);
  const comResultado = buscas.filter((b) => !b.sin_resultado);

  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-navy">Hub de Marketing</h1>
          <p className="text-sm text-slate-500">
            gnhorizons.com y kasteller.com.py — de dónde vienen, qué buscan, qué tocan y quién habla.
          </p>
        </div>
        <div className="flex gap-2">
          <Filtro atual={site} campo="site" site={site} dias={dias} verBots={verBots} aba={aba}
                  opcoes={[['todos', 'Los dos'], ['gnh', 'GNH'], ['kasteller', 'Kasteller']]} />
          <Filtro atual={String(dias)} campo="dias" site={site} dias={dias} verBots={verBots} aba={aba}
                  opcoes={[['7', '7 días'], ['30', '30 días'], ['90', '90 días']]} />
          <Filtro atual={verBots ? '1' : '0'} campo="bots" site={site} dias={dias} verBots={verBots} aba={aba}
                  opcoes={[['0', 'Sin bots'], ['1', 'Con bots']]} />
        </div>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi icon={<Users size={18} />} label="Personas" valor={kpi.personas.toLocaleString('es-PY')}
             nota={`${kpi.bots} bots filtrados`} />
        <Kpi icon={<MessageCircle size={18} />} label="Contactos" valor={String(kpi.contactos)}
             nota="clics de WhatsApp y leads" />
        <Kpi icon={<Percent size={18} />} label="Conversión" valor={`${kpi.tasa.toFixed(1)}%`}
             nota="contactos por persona" />
        <Kpi icon={<Clock size={18} />} label="Tiempo medio" valor={fmtDur(kpi.duracion)}
             nota={`pico de visitas: ${picoHora?.hora ?? '--'} h`} />
      </div>

      {/* ---------- leitura automática ---------- */}
      <section className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="mb-1 flex items-center gap-2 font-bold text-navy"><Lightbulb size={16} />Qué mirar primero</h2>
        <p className="mb-4 text-xs text-slate-500">
          Reglas fijas sobre los números de abajo — no es adivinanza, y tampoco es verdad absoluta:
          con pocas sesiones, tomalo como pista.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {insights.map((i, k) => (
            <div key={k} className={`rounded-lg border-l-4 bg-slate-50 p-3 ${
              i.tono === 'alerta' ? 'border-orange' : i.tono === 'bueno' ? 'border-[#2E7D5B]' : 'border-slate-300'}`}>
              <div className="font-semibold text-navy">{i.titulo}</div>
              <div className="mt-1 text-sm text-slate-600">{i.texto}</div>
              <div className="mt-2 text-sm font-medium text-slate-700">→ {i.accion}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- abas: a página parou de ser uma pilha de tabelas ---------- */}
      <div className="flex gap-1 border-b border-slate-200">
        {([['resumen', 'Resumen'], ['origen', 'De dónde vienen'], ['conducta', 'Qué hacen']] as [string, string][]).map(([v, label]) => (
          <Link key={v} href={`/marketing?${new URLSearchParams({ site, dias: String(dias), bots: verBots ? '1' : '0', t: v })}`}
                className={`min-h-[44px] px-4 py-2 text-sm ${aba === v
                  ? 'border-b-2 border-orange font-bold text-navy'
                  : 'text-slate-500 hover:text-navy'}`}>
            {label}
          </Link>
        ))}
      </div>

      {aba === 'resumen' && (
        <>
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
        <Card titulo="A qué hora entran" icon={<Clock size={16} />}
              nota="Hora local de Asunción, todo el histórico. Sirve para elegir horario de post y de guardia en el WhatsApp.">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={serieHoras}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E7EAF0" vertical={false} />
                <XAxis dataKey="hora" fontSize={11} interval={1} />
                <YAxis allowDecimals={false} fontSize={11} />
                <Tooltip />
                <Bar dataKey="sesiones" name="Sesiones" radius={[3, 3, 0, 0]}>
                  {serieHoras.map((h) => (
                    <Cell key={h.hora} fill={h.contactos > 0 ? '#2E7D5B' : '#94A3B8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-slate-500">Barra verde = en esa hora alguien llegó a escribir.</p>
        </Card>
        </>
      )}

      {aba === 'origen' && (
        <div className="grid gap-6 lg:grid-cols-2">
        <Card titulo="De dónde vienen" icon={<Globe size={16} />}>
  <Rolagem>
    <Tabela cabecalho={colsBots(verBots, 'Origen')}>
      {origens.map((o) => (
        <tr key={o.origen} className="border-t border-slate-100">
          <td className="py-2 pr-3">{ORIGEM_LABEL[o.origen] ?? o.origen}</td>
          <td className="py-2 text-right tabular-nums">{ses(o)}</td>
          {verBots && <td className="py-2 text-right tabular-nums text-slate-400">{o.bots}</td>}
          <td className="py-2 text-right tabular-nums">{o.contactos}</td>
          <td className="py-2 text-right tabular-nums text-slate-500">{pct(o.contactos, ses(o))}</td>
        </tr>
      ))}
    </Tabela>
  </Rolagem>
  {origens.some((o) => o.origen === 'sin dato') && (
    <p className="mt-3 text-xs text-slate-500">
      «Sin dato» son sesiones anteriores al 09/08/2026, cuando empezamos a registrar el origen.
      No son visitas directas — simplemente no lo sabemos.
    </p>
  )}
</Card>
          <Card titulo="Campañas" icon={<Megaphone size={16} />}
                nota="Sólo aparece acá quien entró por un link con ?utm_campaign=. Sin ese parámetro en el link del post, la visita cae en “sin campaña”.">
            <Rolagem>
              <Tabela cabecalho={['Campaña', 'Red', ['Sesiones', 'num'], ['Contactos', 'num']]}>
                {campanas.map((c) => (
                  <tr key={`${c.campana}-${c.origen}`} className="border-t border-slate-100">
                    <td className="py-2 pr-3">{c.campana === 'sin campaña'
                      ? <span className="text-slate-400">Sin campaña (tráfico normal)</span> : c.campana}</td>
                    <td className="py-2 text-slate-500">{ORIGEM_LABEL[c.origen] ?? c.origen}</td>
                    <td className="py-2 text-right tabular-nums">{c.sesiones}</td>
                    <td className="py-2 text-right tabular-nums">{c.contactos}</td>
                  </tr>
                ))}
              </Tabela>
            </Rolagem>
          </Card>
        <Card titulo="Geografía" icon={<MapPin size={16} />}
      nota={verBots
        ? 'Con bots: los crawlers aparecen como “Américas (otro)”, “Europa”, “Asia (otro)” — son datacenters, no público.'
        : 'Deducida de la zona horaria del navegador — sin IP y sin geolocalización. Los crawlers están fuera.'}>
  <Rolagem>
    <Tabela cabecalho={colsBots(verBots, 'País')}>
      {paises.map((p) => (
        <tr key={p.pais} className="border-t border-slate-100">
          <td className="py-2 pr-3">{p.pais}</td>
          <td className="py-2 text-right tabular-nums">{ses(p)}</td>
          {verBots && <td className="py-2 text-right tabular-nums text-slate-400">{p.bots}</td>}
          <td className="py-2 text-right tabular-nums">{p.contactos}</td>
          <td className="py-2 text-right tabular-nums text-slate-500">{pct(p.contactos, ses(p))}</td>
        </tr>
      ))}
    </Tabela>
  </Rolagem>
</Card>
          <Card titulo="Celular o computadora" icon={<Smartphone size={16} />}
                nota="Empezamos a medir el 10/08/2026 — lo de antes aparece como “sin dato”.">
            <Tabela cabecalho={['Aparato', ['Sesiones', 'num'], ['Contactos', 'num'], ['Conv.', 'num']]}>
              {aparatos.map((a) => (
                <tr key={a.aparato} className="border-t border-slate-100">
                  <td className="py-2 pr-3">{APARATO_LABEL[a.aparato] ?? a.aparato}</td>
                  <td className="py-2 text-right tabular-nums">{a.sesiones}</td>
                  <td className="py-2 text-right tabular-nums">{a.contactos}</td>
                  <td className="py-2 text-right tabular-nums text-slate-500">{pct(a.contactos, a.sesiones)}</td>
                </tr>
              ))}
            </Tabela>
          </Card>
        </div>
      )}

      {aba === 'conducta' && (
        <>
          <div className="grid gap-6 lg:grid-cols-2">
          <Card titulo="Búsquedas sin resultado" icon={<Search size={16} />}
        nota="Cada línea es alguien que buscó y se fue con las manos vacías: o falta el producto, o falta la palabra.">
    {vazias.length === 0 ? (
      <p className="text-sm text-slate-500">Nadie buscó algo que no esté. Buena señal.</p>
    ) : (
      <Rolagem>
        <Tabela cabecalho={['Término', 'Sitio', ['Personas', 'num'], ['Veces', 'num']]}>
          {vazias.map((b) => (
            <tr key={`${b.site}-${b.termino}`} className="border-t border-slate-100">
              <td className="py-2 pr-3 font-medium">{b.termino}</td>
              <td className="py-2 text-slate-500">{b.site}</td>
              <td className="py-2 text-right tabular-nums">{b.sesiones}</td>
              <td className="py-2 text-right tabular-nums text-slate-500">{b.veces}</td>
            </tr>
          ))}
        </Tabela>
      </Rolagem>
    )}
  </Card>
          <Card titulo="Lo más buscado" icon={<Search size={16} />}>
    <Rolagem>
      <Tabela cabecalho={['Término', 'Sitio', ['Personas', 'num'], ['Veces', 'num']]}>
        {comResultado.map((b) => (
          <tr key={`${b.site}-${b.termino}`} className="border-t border-slate-100">
            <td className="py-2 pr-3">{b.termino}</td>
            <td className="py-2 text-slate-500">{b.site}</td>
            <td className="py-2 text-right tabular-nums">{b.sesiones}</td>
            <td className="py-2 text-right tabular-nums text-slate-500">{b.veces}</td>
          </tr>
        ))}
      </Tabela>
    </Rolagem>
  </Card>
          </div>
        <Card titulo="Dónde hacen clic" icon={<MousePointerClick size={16} />}
              nota="Productos, promociones, fichas, secciones y filtros — ordenado por cuánta gente distinta lo tocó.">
          <Rolagem alta>
            <Tabela cabecalho={['Qué', 'Tipo', 'Sitio', ['Personas', 'num'], ['Veces', 'num']]}>
              {detalhes.map((d) => (
                <tr key={`${d.site}-${d.type}-${d.detail}`} className="border-t border-slate-100">
                  <td className="max-w-[24rem] truncate py-2 pr-3" title={d.detail}>{d.detail}</td>
                  <td className="py-2 text-slate-500">{TIPO_LABEL[d.type] ?? d.type}</td>
                  <td className="py-2 text-slate-500">{d.site}</td>
                  <td className="py-2 text-right tabular-nums">{d.sesiones}</td>
                  <td className="py-2 text-right tabular-nums text-slate-500">{d.veces}</td>
                </tr>
              ))}
            </Tabela>
          </Rolagem>
        </Card>
        <Card titulo="Páginas" icon={<FileText size={16} />}>
          <Rolagem alta>
            <Tabela cabecalho={['Página', 'Sitio', ['Sesiones', 'num'], ['Contactos', 'num'], ['Conv.', 'num']]}>
              {paginas.map((p) => (
                <tr key={`${p.site}-${p.path}`} className="border-t border-slate-100">
                  <td className="max-w-[24rem] truncate py-2 pr-3" title={p.path}>{p.path}</td>
                  <td className="py-2 text-slate-500">{p.site}</td>
                  <td className="py-2 text-right tabular-nums">{p.sesiones}</td>
                  <td className="py-2 text-right tabular-nums">{p.contactos}</td>
                  <td className="py-2 text-right tabular-nums text-slate-500">{pct(p.contactos, p.sesiones)}</td>
                </tr>
              ))}
            </Tabela>
          </Rolagem>
        </Card>
        </>
      )}
    </div>
  );
}

/* ---------- peças ---------- */

/** Com bots ligado entra uma coluna a mais, entre sessões e contatos. */
function colsBots(verBots: boolean, primeira: string): Col[] {
  const base: Col[] = [primeira, ['Sesiones', 'num']];
  if (verBots) base.push(['Bots', 'num']);
  return base.concat([['Contactos', 'num'], ['Conv.', 'num']]);
}

function pct(parte: number, total: number) {
  return total ? `${((parte / total) * 100).toFixed(0)}%` : '—';
}
function fmtDur(seg: number) {
  if (!seg) return '—';
  const m = Math.floor(seg / 60);
  return m ? `${m}m ${Math.round(seg % 60)}s` : `${Math.round(seg)}s`;
}

/** Caixa com rolagem própria: a tabela cresce sem empurrar a página inteira. */
function Rolagem({ children, alta }: { children: React.ReactNode; alta?: boolean }) {
  return <div className={`overflow-y-auto overflow-x-auto ${alta ? 'max-h-[28rem]' : 'max-h-72'}`}>{children}</div>;
}

function Filtro({ atual, campo, opcoes, site, dias, verBots, aba }: {
  atual: string; campo: 'site' | 'dias' | 'bots' | 't'; opcoes: [string, string][];
  site: string; dias: number; verBots: boolean; aba: string;
}) {
  return (
    <div className="flex overflow-hidden rounded-lg border border-slate-200">
      {opcoes.map(([valor, label]) => {
        // todo filtro carrega o estado dos outros dois, senão trocar um zera o resto
        const params = new URLSearchParams({ site, dias: String(dias), bots: verBots ? '1' : '0', t: aba });
        params.set(campo, valor);
        const ativo = atual === valor;
        return (
          <Link key={valor} href={`/marketing?${params}`}
                className={`min-h-[44px] px-3 py-2 text-sm ${ativo ? 'bg-orange-soft font-bold text-navy' : 'bg-white text-slate-600 hover:bg-slate-50'}`}>
            {label}
          </Link>
        );
      })}
    </div>
  );
}

function Kpi({ icon, label, valor, nota }: {
  icon: React.ReactNode; label: string; valor: string; nota?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 text-slate-500">{icon}<span className="text-sm">{label}</span></div>
      <div className="mt-1 text-3xl font-bold tabular-nums text-navy">{valor}</div>
      {nota && <div className="mt-1 text-xs text-slate-500">{nota}</div>}
    </div>
  );
}

function Card({ titulo, icon, nota, children }: {
  titulo: string; icon?: React.ReactNode; nota?: string; children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="flex items-center gap-2 font-bold text-navy">{icon}{titulo}</h2>
      {nota && <p className="mb-3 mt-1 text-xs text-slate-500">{nota}</p>}
      {!nota && <div className="mb-3" />}
      {children}
    </section>
  );
}

/** Coluna é `'Nome'` (texto, à esquerda) ou `['Nome', 'num']` (número, à direita). */
type Col = string | [string, 'num'];

function Tabela({ cabecalho, children }: { cabecalho: Col[]; children: React.ReactNode }) {
  return (
    <table className="w-full text-sm">
      {/* cabeçalho fixo: rolando a caixa, ainda se sabe que coluna é qual */}
      <thead className="sticky top-0 z-10 bg-white text-xs uppercase tracking-wide text-slate-400">
        <tr>
          {cabecalho.map((c) => {
            const [label, tipo] = Array.isArray(c) ? c : [c, 'txt'];
            return (
              <th key={label} className={`bg-white pb-2 pt-1 ${tipo === 'num' ? 'text-right' : 'text-left'}`}>
                {label}
              </th>
            );
          })}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  );
}
