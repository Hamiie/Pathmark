-- Pathmark hosted access-control schema
-- Versioned migration for Supabase-linked GitHub repositories.
--
-- Security boundary:
-- - This schema stores hosted access metadata only: user emails, roles,
--   statuses, feature flags, and audit logs.
-- - It must not store Pathmark goals, routines, task prompts, calendar blocks,
--   Workspace files, OAuth tokens, backups, Markdown files, or on-the-go entries.
-- - RLS is enabled and no public policies are created. The hosted Streamlit app
--   should access these tables server-side with a Supabase Secret API key kept in
--   Streamlit secrets.

create table if not exists public.pathmark_users (
  email text primary key,
  role text not null default 'standard' check (role in ('standard', 'beta_tester', 'developer')),
  status text not null default 'active' check (status in ('active', 'disabled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login timestamptz,
  notes text
);

create table if not exists public.pathmark_feature_flags (
  key text primary key,
  enabled boolean not null default true,
  minimum_role text not null default 'standard' check (minimum_role in ('standard', 'beta_tester', 'developer')),
  updated_at timestamptz not null default now(),
  notes text
);

create table if not exists public.pathmark_audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_email text,
  action text not null,
  target_email text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.pathmark_users enable row level security;
alter table public.pathmark_feature_flags enable row level security;
alter table public.pathmark_audit_log enable row level security;

-- Do not add anon/authenticated RLS policies for these tables in the current architecture.
-- The app uses server-side access only, and public client access should remain blocked.

insert into public.pathmark_feature_flags (key, enabled, minimum_role, notes)
values
  ('on_the_go_beta', true, 'beta_tester', 'Shows the On-the-go beta tab.'),
  ('developer_panel', true, 'developer', 'Shows the Developer settings tab.')
on conflict (key) do update
set
  enabled = excluded.enabled,
  minimum_role = excluded.minimum_role,
  notes = excluded.notes,
  updated_at = now();
