begin;
create table public.event_sources (
 id text primary key, url text not null unique, name text not null,
 timezone text not null default 'America/New_York', last_success_at timestamptz
);
create table public.ingestion_runs (
 id uuid primary key, source_id text references public.event_sources(id),
 started_at timestamptz not null, finished_at timestamptz,
 status text not null check(status in ('running','success','failed')),
 received integer not null default 0, accepted integer not null default 0,
 rejected integer not null default 0, error text
);
create table public.raw_records (
 id text primary key, source_id text not null references public.event_sources(id),
 source_identifier text, content_hash text not null, collected_at timestamptz not null,
 run_id uuid not null references public.ingestion_runs(id), original_xml text not null,
 error text
);
create table public.events (
 id text primary key, source_id text not null references public.event_sources(id),
 source_identifier text not null, raw_record_id text not null references public.raw_records(id),
 content_hash text not null, title text not null, description text not null,
 url text not null, start_at timestamptz not null, end_at timestamptz,
 date_provenance text not null, location text, organizers text[] not null default '{}',
 source_categories text[] not null default '{}',
 status text not null check(status in ('active','cancelled','unknown')),
 series_id text, related_group text not null, duplicate_key text not null,
 quality_flags text[] not null default '{}', first_seen_at timestamptz not null,
 last_seen_at timestamptz not null, updated_at timestamptz not null,
 unique(source_id,source_identifier), check(end_at is null or end_at >= start_at)
);
create index events_start_idx on public.events(start_at);
create index events_series_idx on public.events(series_id);
create index events_source_idx on public.events(source_id);
create table public.event_tags (
 event_id text primary key references public.events(id) on delete cascade,
 content_hash text not null, topics text[] not null default '{}',
 format text not null default 'unknown' check(format in ('workshop','social','performance','sports','volunteering','meeting','unknown')),
 free_admission text not null default 'unknown' check(free_admission in ('yes','no','unknown')),
 free_food text not null default 'unknown' check(free_food in ('yes','no','unknown')),
 registration_required text not null default 'unknown' check(registration_required in ('yes','no','unknown')),
 audience_restricted text not null default 'unknown' check(audience_restricted in ('yes','no','unknown')),
 audience text[] not null default '{}', evidence jsonb not null default '{}',
 method text not null, model_version text, prompt_version text not null,
 review_status text not null check(review_status in ('pending','approved','rejected')),
 updated_at timestamptz not null,
 check(topics <@ array['technology','arts','sports','wellness','career','community','academic','culture'])
);
create table public.tag_reviews (
 id uuid primary key default gen_random_uuid(), event_id text not null references public.events(id),
 content_hash text not null, reviewer text not null, labels jsonb not null,
 created_at timestamptz not null default now()
);
create index tag_reviews_event_idx on public.tag_reviews(event_id);
create index raw_records_run_idx on public.raw_records(run_id);
create index raw_records_source_idx on public.raw_records(source_id);
create index events_raw_idx on public.events(raw_record_id);
create index ingestion_runs_source_idx on public.ingestion_runs(source_id);
create table public.evaluation_splits (
 event_id text primary key references public.events(id), group_id text not null,
 split text not null check(split in ('train','validation','test')),
 frozen_at timestamptz not null
);
-- Public feed data is read-only. Raw HTML, operational errors and reviewer identities stay private.
alter table public.event_sources enable row level security;
alter table public.events enable row level security;
alter table public.event_tags enable row level security;
alter table public.raw_records enable row level security;
alter table public.ingestion_runs enable row level security;
alter table public.tag_reviews enable row level security;
alter table public.evaluation_splits enable row level security;
revoke all on public.event_sources,public.events,public.event_tags,public.raw_records,public.ingestion_runs,public.tag_reviews,public.evaluation_splits from anon,authenticated;
grant select on public.event_sources,public.events,public.event_tags to anon,authenticated;
create policy public_sources on public.event_sources for select to anon,authenticated using(true);
create policy public_events on public.events for select to anon,authenticated using(true);
create policy public_tags on public.event_tags for select to anon,authenticated using(true);
grant all on public.event_sources,public.events,public.event_tags,public.raw_records,public.ingestion_runs,public.tag_reviews,public.evaluation_splits to service_role;
commit;
