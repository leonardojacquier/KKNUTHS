-- Poker Hand Analyzer — schema Postgres (Supabase) + pgvector
-- Aplicar via Supabase migration. Embeddings dimensionados para 1536 (ajustar ao modelo).

create extension if not exists vector;
create extension if not exists "uuid-ossp";

-- ───────────────────────── usuários & billing ─────────────────────────
create table if not exists users (
    id           uuid primary key default uuid_generate_v4(),
    telegram_id  bigint unique not null,
    username     text,
    lang         text not null default 'pt',
    currency     text not null default 'USD',
    plan         text not null default 'free',   -- free | pro | premium
    credits      integer not null default 0,
    created_at   timestamptz not null default now()
);

create table if not exists subscriptions (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null references users(id) on delete cascade,
    stripe_customer text,
    stripe_sub_id   text unique,
    plan            text not null,
    status          text not null,               -- active | trialing | past_due | canceled
    period_end      timestamptz,
    created_at      timestamptz not null default now()
);

create table if not exists usage_events (
    id           uuid primary key default uuid_generate_v4(),
    user_id      uuid not null references users(id) on delete cascade,
    type         text not null,                  -- hand_analysis | tournament_report | deep_dive
    cost_credits integer not null default 0,
    created_at   timestamptz not null default now()
);

-- ───────────────────────── ingestão & mãos ─────────────────────────
create table if not exists uploads (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references users(id) on delete cascade,
    file_url    text,
    format      text not null,                   -- txt | csv | pdf | image
    site        text,
    status      text not null default 'received',-- received | parsing | analyzed | failed
    confidence  real,
    created_at  timestamptz not null default now()
);

create table if not exists hands (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references users(id) on delete cascade,
    upload_id   uuid references uploads(id) on delete set null,
    site        text,
    hand_id     text,                            -- id da sala
    format      text,                            -- tournament | sng | cash
    canonical   jsonb not null,                  -- CanonicalHand serializado
    played_at   timestamptz,
    created_at  timestamptz not null default now(),
    unique (user_id, site, hand_id)
);
create index if not exists idx_hands_user_time on hands (user_id, played_at desc);

create table if not exists hand_analysis (
    id          uuid primary key default uuid_generate_v4(),
    hand_id     uuid not null references hands(id) on delete cascade,
    ev_loss     real,                            -- perda estimada em fichas/bb
    mistakes    jsonb,                           -- lista de leaks detectados
    summary     text,                            -- leitura em linguagem natural
    embedding   vector(1536),                    -- p/ busca semântica (RAG)
    created_at  timestamptz not null default now()
);
create index if not exists idx_hand_analysis_embedding
    on hand_analysis using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create table if not exists tournaments (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references users(id) on delete cascade,
    site        text,
    tournament_id text,
    buyin       real,
    result      text,                            -- posição / prize
    itm         boolean,
    report      jsonb,                           -- relatório agregado
    played_at   timestamptz,
    created_at  timestamptz not null default now()
);

-- ───────────────────────── perfil de estilo ─────────────────────────
create table if not exists player_stats (
    user_id     uuid primary key references users(id) on delete cascade,
    hands       integer not null default 0,
    vpip        real,
    pfr         real,
    three_bet   real,
    af          real,
    label       text,
    detail      jsonb,
    updated_at  timestamptz not null default now()
);

-- Busca semântica nas análises do usuário (RAG da base de conhecimento).
-- Uso: select * from match_hand_analysis(:user, :embedding, 8);
create or replace function match_hand_analysis(
    p_user_id uuid,
    p_query vector(1536),
    p_limit int default 8
) returns table (hand_id uuid, summary text, similarity real)
language sql stable as $$
    select ha.hand_id, ha.summary,
           1 - (ha.embedding <=> p_query) as similarity
    from hand_analysis ha
    join hands h on h.id = ha.hand_id
    where h.user_id = p_user_id and ha.embedding is not null
    order by ha.embedding <=> p_query
    limit p_limit;
$$;
