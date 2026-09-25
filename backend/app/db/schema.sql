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

-- ───────────────────────── eventos do bot ─────────────────────────
-- Log de toda interação (comandos, uploads) — visibilidade estilo dashboard.
create table if not exists bot_events (
    id          uuid primary key default uuid_generate_v4(),
    telegram_id bigint,
    username    text,
    event       text not null,   -- start|plano|stats|ask|treino|drill_answer|upload|error
    detail      jsonb,
    created_at  timestamptz not null default now()
);
create index if not exists idx_bot_events_time on bot_events (created_at desc);
create index if not exists idx_bot_events_user on bot_events (telegram_id, created_at desc);

-- Drill pendente por usuário (quiz diário + /treino à prova de restart)
create table if not exists pending_drills (
    telegram_id bigint primary key,
    drill       jsonb not null,
    created_at  timestamptz not null default now()
);
alter table pending_drills enable row level security;

-- ───────────────────────── segurança (RLS) ─────────────────────────
-- O acesso é exclusivamente server-side via service role (que ignora RLS). Habilitar
-- RLS sem políticas bloqueia anon/authenticated por completo — default seguro, pois
-- o cliente Telegram nunca fala direto com o banco. Para um futuro painel web com
-- login Supabase, adicionar políticas por usuário (ex.: using auth.uid() = user_id).
alter table public.bot_events     enable row level security;
alter table public.users          enable row level security;
alter table public.subscriptions  enable row level security;
alter table public.usage_events   enable row level security;
alter table public.uploads        enable row level security;
alter table public.hands          enable row level security;
alter table public.hand_analysis  enable row level security;
alter table public.tournaments    enable row level security;
alter table public.player_stats   enable row level security;

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

-- search_path fixo (advisor: function_search_path_mutable).
alter function public.match_hand_analysis(uuid, vector, int)
    set search_path = public, pg_temp;

-- ───────────────────── evolução e caderno do coach ─────────────────────
-- Snapshot das stats a cada lote analisado — alimenta o /evolucao.
create table if not exists player_stats_history (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    hands       integer not null default 0,
    vpip        real,
    pfr         real,
    three_bet   real,
    af          real,
    net_bb      real,
    label       text,
    created_at  timestamptz not null default now()
);
create index if not exists idx_psh_user_time on player_stats_history(user_id, created_at);

-- Observações qualitativas do coach por aluno (leak | progresso | meta | estilo).
create table if not exists player_notes (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    kind        text not null default 'leak',
    note        text not null,
    created_at  timestamptz not null default now()
);
create index if not exists idx_notes_user_time on player_notes(user_id, created_at);

alter table public.player_stats_history enable row level security;
alter table public.player_notes         enable row level security;

-- ───────────── estado de conversa, memória e pendências ─────────────
-- Estas três nasceram direto no banco (ad hoc) e ficaram FORA deste arquivo
-- por semanas: reconstruir o projeto a partir do schema.sql produziria um
-- banco sem memória de conversa e sem ICM salvo. Documentadas aqui.

-- Conversa persistente por usuário: a última mão/contexto do chat sobrevive
-- ao restart do bot (o follow-up "e se ele tivesse QJ?" precisa da mão).
create table if not exists conversation_state (
    telegram_id bigint primary key,
    state       jsonb not null,
    updated_at  timestamptz not null default now()
);
alter table public.conversation_state enable row level security;

-- Memória de longo prazo por aluno, chave/valor (ex.: payouts do torneio
-- para o ICM automático — informados uma vez, aplicados sempre).
create table if not exists user_meta (
    user_id     uuid not null references users(id) on delete cascade,
    key         text not null,
    value       jsonb not null,
    updated_at  timestamptz not null default now(),
    primary key (user_id, key)
);
alter table public.user_meta enable row level security;

-- Simulação em andamento (/simular à prova de restart).
create table if not exists pending_sims (
    telegram_id bigint primary key,
    sim         jsonb not null,
    updated_at  timestamptz not null default now()
);
alter table public.pending_sims enable row level security;

-- MEMÓRIA COLETIVA: o que o coach aprendeu com TODOS os alunos.
-- Todo o resto do produto é por aluno (match_hand_analysis trava em
-- user_id, player_notes idem), então o que um aluno ensinou nunca chegava
-- no outro: o tema "3-bet" aparecia no caderno de 4 alunos distintos e
-- nenhum deles se beneficiava disso. Esta é a única tabela que atravessa
-- alunos — e por isso é anônima por construção: quem escreve generaliza, e
-- o destilador descarta (não "corrige") saber que cite nome.
create table if not exists conhecimento (
    id           uuid primary key default gen_random_uuid(),
    kind         text not null check (kind in ('padrao', 'playbook')),
    titulo       text not null,
    gatilho      text not null,           -- quando este saber se aplica
    texto        text not null,           -- o saber, com o número que prova
    categoria    text,                    -- preflop|flop|turn|river|icm
    ev_bb        numeric,
    alunos       int  not null default 1, -- de quantos alunos distintos veio
    usos         int  not null default 0, -- quantas vezes foi injetado
    embedding    vector(1536),
    origem       jsonb not null default '{}'::jsonb,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);
create index if not exists conhecimento_embedding_idx
    on conhecimento using ivfflat (embedding vector_cosine_ops)
    with (lists = 20);
create index if not exists conhecimento_kind_idx on conhecimento (kind);
alter table public.conhecimento enable row level security;

-- busca GLOBAL — de propósito SEM p_user_id. É o oposto de
-- match_hand_analysis, e é essa diferença que faz a ferramenta aprender com
-- os usuários (plural) em vez de sobre cada um em separado.
create or replace function public.match_conhecimento(
    p_query vector, p_limit integer default 4, p_min_alunos integer default 1)
returns table (id uuid, kind text, titulo text, gatilho text, texto text,
               categoria text, ev_bb numeric, alunos int, similarity real)
language sql stable
set search_path to 'public', 'pg_temp'
as $$
    select c.id, c.kind, c.titulo, c.gatilho, c.texto, c.categoria,
           c.ev_bb, c.alunos, 1 - (c.embedding <=> p_query) as similarity
    from conhecimento c
    where c.embedding is not null and c.alunos >= p_min_alunos
    order by c.embedding <=> p_query
    limit p_limit;
$$;

-- "temos uma base" e "a base é usada" são coisas diferentes: sem contador
-- não dá para descobrir que a memória virou outro /ask que ninguém chama.
create or replace function public.incrementar_uso_conhecimento(p_ids uuid[])
returns void
language sql volatile
set search_path to 'public', 'pg_temp'
as $$
    update public.conhecimento
       set usos = usos + 1, updated_at = now()
     where id = any(p_ids);
$$;

-- ──────────────── biblioteca de lições e glossário vivo ────────────────
-- Estas duas nasceram FORA deste arquivo (criadas direto no banco) e por
-- isso escaparam do bloco de RLS lá em cima: eram as duas únicas tabelas de
-- `public` sem row level security, com grant de SELECT/INSERT/UPDATE/DELETE
-- para `anon`. Sem RLS a grant vale direto — qualquer um com a URL do
-- projeto e a chave anon (que é pública por desenho) escrevia nelas.
--
-- O que isso dá a um estranho não é ler dado de aluno: é ESCREVER na boca do
-- coach. Lição é o objeto que fala com todos de uma vez e leva a assinatura
-- da ferramenta; termo de glossário aprovado vira troca determinística no
-- texto entregue.
create table if not exists licoes (
    id               serial primary key,
    hand_analysis_id uuid references hand_analysis(id) on delete set null,
    titulo           text not null,
    spot             text not null,
    licao            text not null,
    ev_bb            real,
    categoria        text,
    aprovada         boolean not null default false,
    publicada        boolean not null default false,
    enviada_em       timestamptz,
    created_at       timestamptz not null default now()
);

create table if not exists glossario (
    id         serial primary key,
    errado     text not null,
    certo      text not null,
    tipo       text not null default 'vigiar',
    aprovado   boolean not null default false,
    origem     text not null default 'linguista',
    exemplo    text,
    created_at timestamptz not null default now()
);

alter table public.licoes    enable row level security;
alter table public.glossario enable row level security;

-- ─────────────────────── ciclo de problema (PBL) ───────────────────────
-- `player_notes` continua sendo o caderno QUALITATIVO do coach (texto livre
-- de LLM) e não pode alimentar estatística: número que sai de nota narrativa
-- é o incidente do VPIP por outro caminho. Por isso o problema é entidade
-- estruturada separada, com evidência numérica rastreável.
create table if not exists problemas (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references users(id) on delete cascade,
    codigo       text not null,
    estado       text not null,
    causa        text,
    por_que      text,
    -- CRITÉRIO PRÉ-REGISTRADO, escrito ANTES da intervenção
    alta_limiar        real,
    alta_n_minimo      int,
    alta_registrado_em timestamptz,
    alta_por_extenso   text,
    -- a janela que DIAGNOSTICOU não pode ser a linha de base (regressão à
    -- média: o problema foi escolhido por estar no extremo)
    diagnostico_ate  date,
    baseline_de      date,
    baseline_oport   int,
    baseline_erros   int,
    detector_versao  text not null default 'v1',
    bloqueado_por    uuid references problemas(id),
    aberto_em        timestamptz not null default now(),
    intervencao_em   timestamptz,
    alta_em          timestamptz,
    unique (user_id, codigo, aberto_em)
);
create index if not exists idx_problemas_user on problemas (user_id, estado);

create table if not exists problema_evidencia (
    id          uuid primary key default gen_random_uuid(),
    problema_id uuid not null references problemas(id) on delete cascade,
    hand_id     uuid references hands(id) on delete set null,
    fase        text not null,
    oportunidade bool not null,
    escorregada  bool not null,
    custo_bb     real,
    amostra_tipo text not null,
    detector_versao text not null default 'v1',
    played_at   timestamptz,
    created_at  timestamptz not null default now()
);
create index if not exists idx_evid_problema on problema_evidencia (problema_id, fase);

create table if not exists problema_medicao (
    id          uuid primary key default gen_random_uuid(),
    problema_id uuid not null references problemas(id) on delete cascade,
    oportunidades int, erros int,
    post_lo real, post_mean real, post_hi real,
    veredito    text,
    motivo      text,
    controle_codigo text, controle_delta real,
    created_at  timestamptz not null default now()
);
create index if not exists idx_medicao_problema on problema_medicao (problema_id, created_at desc);

alter table public.problemas          enable row level security;
alter table public.problema_evidencia enable row level security;
alter table public.problema_medicao   enable row level security;
