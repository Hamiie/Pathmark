-- Pathmark v0.7.25 shared ingredient catalogue
-- Reference data lives in Supabase so seasonality and nutrition do not need to
-- be copied into every user's Pathmark Sync Google Sheet.

create table if not exists public.pathmark_ingredients (
  ingredient_id text primary key,
  canonical_name text not null,
  display_name text not null,
  category_name text,
  default_unit text,
  default_shopping_aisle text,
  notes text,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_pathmark_ingredients_status on public.pathmark_ingredients(status);
create index if not exists idx_pathmark_ingredients_display_name on public.pathmark_ingredients(display_name);

create table if not exists public.pathmark_ingredient_aliases (
  alias_id bigserial primary key,
  ingredient_id text references public.pathmark_ingredients(ingredient_id) on delete cascade,
  alias text not null,
  status text default 'active',
  created_at timestamptz default now()
);

create index if not exists idx_pathmark_ingredient_aliases_alias on public.pathmark_ingredient_aliases(alias);
create index if not exists idx_pathmark_ingredient_aliases_ingredient on public.pathmark_ingredient_aliases(ingredient_id);

create table if not exists public.pathmark_produce_seasonality (
  seasonality_id bigserial primary key,
  ingredient_id text references public.pathmark_ingredients(ingredient_id) on delete cascade,
  region text default 'NZ',
  months text,
  season_months text,
  jan text,
  feb text,
  mar text,
  apr text,
  may text,
  jun text,
  jul text,
  aug text,
  sep text,
  oct text,
  nov text,
  dec text,
  season_note text,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_pathmark_produce_seasonality_ingredient on public.pathmark_produce_seasonality(ingredient_id);
create index if not exists idx_pathmark_produce_seasonality_status on public.pathmark_produce_seasonality(status);

create table if not exists public.pathmark_nutrition_reference (
  nutrition_ref_id bigserial primary key,
  ingredient_id text references public.pathmark_ingredients(ingredient_id) on delete cascade,
  per_quantity numeric,
  per_unit text default '100 g',
  kcal numeric,
  protein numeric,
  carbohydrate numeric,
  fat numeric,
  fibre numeric,
  sodium numeric,
  notes text,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_pathmark_nutrition_reference_ingredient on public.pathmark_nutrition_reference(ingredient_id);
create index if not exists idx_pathmark_nutrition_reference_status on public.pathmark_nutrition_reference(status);
