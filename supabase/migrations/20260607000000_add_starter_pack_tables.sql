-- v0.6.85
-- Optional starter-pack library schema.
--
-- These tables are for curated, read-only starter data such as NZ Seasonal
-- Produce, nutrition rows, inventory starters, and recipe starters. They are
-- not for user-owned Pathmark Sync data. User edits still belong in the
-- user's own Google Sheet.

create table if not exists public.pathmark_starter_packs (
  slug text primary key,
  name text not null,
  description text,
  status text not null default 'active' check (status in ('active', 'inactive')),
  price_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  notes text
);

create table if not exists public.pathmark_starter_pack_rows (
  id uuid primary key default gen_random_uuid(),
  pack_slug text not null references public.pathmark_starter_packs(slug) on delete cascade,
  section text not null,
  target_table text not null check (target_table in ('grocery_nutrition', 'grocery_inventory', 'recipes', 'recipe_ingredients')),
  row_data jsonb not null default '{}'::jsonb,
  sort_order integer not null default 0,
  status text not null default 'active' check (status in ('active', 'inactive')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  notes text
);

create index if not exists pathmark_starter_pack_rows_pack_slug_idx
  on public.pathmark_starter_pack_rows (pack_slug, status, section, sort_order);

alter table public.pathmark_starter_packs enable row level security;
alter table public.pathmark_starter_pack_rows enable row level security;

-- No public RLS policies are added. The hosted Streamlit app reads these
-- tables server-side using a Supabase Secret API key held in Streamlit secrets.

insert into public.pathmark_starter_packs (slug, name, description, status, price_note, notes)
values (
  'nz-seasonal-produce',
  'NZ Seasonal Produce',
  'Curated New Zealand produce seasonality, availability and substitution starter pack.',
  'active',
  'Access code required',
  'Populate pathmark_starter_pack_rows with grocery_inventory and grocery_nutrition rows before enabling imports.'
)
on conflict (slug) do update
set
  name = excluded.name,
  description = excluded.description,
  status = excluded.status,
  price_note = excluded.price_note,
  updated_at = now();
