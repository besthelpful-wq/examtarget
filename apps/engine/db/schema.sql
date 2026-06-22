-- ExamTarget — Supabase Postgres schema
-- Run this against your Supabase project via the SQL editor or psql.
-- Safe to re-run: all statements use IF NOT EXISTS / OR REPLACE.

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
create extension if not exists "pgcrypto";   -- gen_random_uuid()


-- ---------------------------------------------------------------------------
-- users
-- id mirrors the Clerk user id (uuid string Clerk issues).
-- ---------------------------------------------------------------------------
create table if not exists users (
    id                  uuid        primary key,
    email               text        not null,
    plan                text        not null default 'free'
                                    check (plan in ('free', 'pro')),
    stripe_customer_id  text,
    created_at          timestamptz not null default now()
);

comment on column users.plan is '''free'' | ''pro''';


-- ---------------------------------------------------------------------------
-- worksheets
-- ---------------------------------------------------------------------------
create table if not exists worksheets (
    id              uuid        primary key default gen_random_uuid(),
    user_id         uuid        references users(id) on delete cascade,
    title           text,
    topic           text        not null,
    difficulty      text        not null
                                check (difficulty in ('easy', 'medium', 'hard')),
    problem_count   int         not null check (problem_count > 0),
    seed            int         not null,
    version_count   int         not null default 1 check (version_count > 0),
    config          jsonb,
    created_at      timestamptz not null default now()
);

create index if not exists worksheets_user_id_idx on worksheets(user_id);
create index if not exists worksheets_created_at_idx on worksheets(created_at desc);

comment on column worksheets.difficulty   is '''easy'' | ''medium'' | ''hard''';
comment on column worksheets.seed        is 'Deterministic seed — same seed reproduces identical problems.';
comment on column worksheets.config      is 'Arbitrary extra config (e.g. show_steps, include_answer_key).';


-- ---------------------------------------------------------------------------
-- problem_cache
-- One row per unique (topic, seed, params) combination.
-- steps is null until AI generation has run and been verified.
-- ---------------------------------------------------------------------------
create table if not exists problem_cache (
    id               uuid        primary key default gen_random_uuid(),
    problem_hash     text        unique not null,  -- hash(topic + seed + params)
    topic            text        not null,
    problem_latex    text        not null,
    answer_latex     text        not null,
    answer_exact     text        not null,         -- sympy srepr() for exact comparison
    steps            jsonb,                        -- array of step objects; null until generated
    steps_verified   boolean     not null default false,
    standard_codes   text[],                       -- e.g. ARRAY['A-REI.3', 'A-SSE.3']
    created_at       timestamptz not null default now()
);

create index if not exists problem_cache_hash_idx   on problem_cache(problem_hash);
create index if not exists problem_cache_topic_idx  on problem_cache(topic);

comment on column problem_cache.problem_hash   is 'SHA-256 of (topic + seed + params). Used as the cache key.';
comment on column problem_cache.answer_exact   is 'sympy.srepr() string — used for exact AI-output verification, never float comparison.';
comment on column problem_cache.steps          is 'Array of {explanation: str, latex: str} objects. Null until Gemini has generated and SymPy has verified.';
comment on column problem_cache.steps_verified is 'True only after the AI final answer matched SymPy''s exact answer.';


-- ---------------------------------------------------------------------------
-- usage_counts
-- Tracks how many worksheets a user has generated in a given calendar month.
-- Used to enforce the free-tier monthly limit server-side.
-- ---------------------------------------------------------------------------
create table if not exists usage_counts (
    user_id     uuid    not null references users(id) on delete cascade,
    year_month  text    not null,   -- 'YYYY-MM'
    sheet_count int     not null default 0 check (sheet_count >= 0),
    primary key (user_id, year_month)
);

comment on column usage_counts.year_month is 'ISO calendar month, e.g. ''2026-06''. Enforced server-side — do not trust the client.';


-- ---------------------------------------------------------------------------
-- Row-Level Security
-- Enable RLS on every table. The engine uses the service key and bypasses RLS.
-- These policies are a safety net if you ever expose the anon key.
-- ---------------------------------------------------------------------------
alter table users         enable row level security;
alter table worksheets    enable row level security;
alter table problem_cache enable row level security;
alter table usage_counts  enable row level security;

-- problem_cache is not user-scoped — allow read for all authenticated users,
-- writes only via service role (engine).
create policy if not exists "problem_cache: authenticated read"
    on problem_cache for select
    to authenticated
    using (true);
