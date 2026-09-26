-- FASE 6C — eventos de negocio y leads (proyecto: Base de Dados Resultado - GNH)
-- Aplicar una sola vez. Inserción anónima permitida; lectura solo con service role.

create table if not exists public.events (
  id bigint generated always as identity primary key,
  type text not null check (char_length(type) <= 40),
  detail text default '' check (char_length(detail) <= 200),
  path text default '' check (char_length(path) <= 120),
  session_id text default '' check (char_length(session_id) <= 60),
  created_at timestamptz not null default now()
);

create table if not exists public.leads (
  id bigint generated always as identity primary key,
  nombre text not null check (char_length(nombre) <= 120),
  empresa text default '' check (char_length(empresa) <= 120),
  whatsapp text not null check (char_length(whatsapp) <= 40),
  producto text default '' check (char_length(producto) <= 200),
  mensaje text default '' check (char_length(mensaje) <= 500),
  origen text default '' check (char_length(origen) <= 120),
  session_id text default '' check (char_length(session_id) <= 60),
  created_at timestamptz not null default now()
);

alter table public.events enable row level security;
alter table public.leads enable row level security;

-- el sitio (clave anon) solo puede INSERTAR; nadie lee sin service role
drop policy if exists events_insert_anon on public.events;
create policy events_insert_anon on public.events for insert to anon with check (true);
drop policy if exists leads_insert_anon on public.leads;
create policy leads_insert_anon on public.leads for insert to anon with check (true);

create index if not exists events_created_idx on public.events (created_at desc);
create index if not exists events_type_idx on public.events (type);
create index if not exists leads_created_idx on public.leads (created_at desc);

-- vistas de lectura (Dashboard de Supabase)
create or replace view public.resumen_eventos as
  select type, detail, count(*) as veces, max(created_at) as ultimo
  from public.events group by type, detail order by veces desc;
create or replace view public.leads_semana as
  select * from public.leads where created_at > now() - interval '7 days' order by created_at desc;
