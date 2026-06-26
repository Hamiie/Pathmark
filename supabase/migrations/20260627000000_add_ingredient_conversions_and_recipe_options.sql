-- Pathmark v0.7.30 ingredient conversions and structured recipe alternatives
-- Adds shared reference tables that let Pathmark convert ingredient-specific
-- household/volume/count measures into preferred calculation units, and model
-- recipe alternatives as structured options rather than text hidden inside an
-- ingredient name.

create table if not exists public.pathmark_ingredient_unit_conversions (
  conversion_id text primary key,
  ingredient_id text references public.pathmark_ingredients(ingredient_id) on delete cascade,
  ingredient_key text,
  ingredient text,
  form text,
  from_quantity numeric not null,
  from_unit text not null,
  to_quantity numeric not null,
  to_unit text not null,
  preferred_unit text,
  confidence text default 'Pathmark default',
  source_note text,
  notes text,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_pathmark_ingredient_unit_conversions_ingredient on public.pathmark_ingredient_unit_conversions(ingredient_id);
create index if not exists idx_pathmark_ingredient_unit_conversions_key on public.pathmark_ingredient_unit_conversions(ingredient_key);
create index if not exists idx_pathmark_ingredient_unit_conversions_status on public.pathmark_ingredient_unit_conversions(status);

create table if not exists public.pathmark_recipe_ingredient_groups (
  recipe_ingredient_group_id text primary key,
  starter_pack_id bigint references public.pathmark_starter_packs(starter_pack_id) on delete cascade,
  recipe_id text,
  recipe_key text,
  recipe_name text,
  group_label text,
  selection_mode text default 'single',
  required text default 'Yes',
  default_option_id text,
  original_line text,
  notes text,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_pathmark_recipe_ingredient_groups_recipe on public.pathmark_recipe_ingredient_groups(recipe_id);
create index if not exists idx_pathmark_recipe_ingredient_groups_pack on public.pathmark_recipe_ingredient_groups(starter_pack_id);
create index if not exists idx_pathmark_recipe_ingredient_groups_status on public.pathmark_recipe_ingredient_groups(status);

create table if not exists public.pathmark_recipe_ingredient_options (
  recipe_ingredient_option_id text primary key,
  recipe_ingredient_group_id text references public.pathmark_recipe_ingredient_groups(recipe_ingredient_group_id) on delete cascade,
  starter_pack_id bigint references public.pathmark_starter_packs(starter_pack_id) on delete cascade,
  recipe_id text,
  recipe_key text,
  recipe_name text,
  ingredient_id text references public.pathmark_ingredients(ingredient_id) on delete set null,
  ingredient_key text,
  ingredient text not null,
  quantity text,
  unit text,
  category_name text,
  preferred_unit text,
  converted_quantity text,
  converted_unit text,
  conversion_status text,
  is_default text,
  option_label text,
  notes text,
  status text default 'active',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_pathmark_recipe_ingredient_options_group on public.pathmark_recipe_ingredient_options(recipe_ingredient_group_id);
create index if not exists idx_pathmark_recipe_ingredient_options_ingredient on public.pathmark_recipe_ingredient_options(ingredient_id);
create index if not exists idx_pathmark_recipe_ingredient_options_key on public.pathmark_recipe_ingredient_options(ingredient_key);
create index if not exists idx_pathmark_recipe_ingredient_options_status on public.pathmark_recipe_ingredient_options(status);
