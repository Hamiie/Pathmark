# Supabase schema for Pathmark

This folder contains the Supabase schema used by the hosted Pathmark app.

Pathmark uses Supabase for two different kinds of hosted data:

1. **Access/profile metadata**
   - user email
   - role
   - status
   - feature flags
   - audit logs
   - optional theme preference

2. **Shared reference/library data**
   - optional starter-pack rows
   - shared ingredient catalogue
   - ingredient aliases
   - produce seasonality reference data
   - nutrition reference data

Pathmark should not store user-owned planning, finance, shopping, inventory, recipe edits, calendar rows, Google Tasks prompts, Workspace files, backups, OAuth tokens or private Google Sheet content in Supabase. Those remain in the user's own Pathmark Sync Google Sheet or Google account.

## Migrations

Run the SQL files in `supabase/migrations/` in filename order:

1. `20260531000000_create_pathmark_access_tables.sql`
2. `20260601000000_add_pathmark_user_theme_preference.sql`
3. `20260607000000_add_starter_pack_tables.sql`
4. `20260620000000_add_shared_ingredient_catalogue.sql`

The v0.7.25 migration creates:

- `public.pathmark_ingredients`
- `public.pathmark_ingredient_aliases`
- `public.pathmark_produce_seasonality`
- `public.pathmark_nutrition_reference`

These tables are read by Pathmark as shared reference data. Users can override or add their own ingredient details in their own Pathmark Sync sheet; those user overrides are not written back to Supabase.

## Required Streamlit secrets

Use Streamlit Cloud secrets, not committed files:

```toml
[supabase]
url = "https://YOUR_PROJECT_ID.supabase.co"
secret_key = "sb_secret_YOUR_SUPABASE_SECRET_API_KEY"
```

The app also accepts older service-role style keys as a fallback, but new deployments should prefer Supabase Secret API keys where available.

Never commit `.streamlit/secrets.toml`, Supabase keys, Google OAuth client secrets, Google access tokens, refresh tokens, service account JSON, personal grocery exports, or private Pathmark Sync exports.

## Initial developer account

Do not put personal developer rows or private email allowlists in public migrations.

For initial access, either keep `[pathmark_access].developer_emails` in Streamlit secrets as a bootstrap route, or manually insert your developer row in the Supabase SQL editor:

```sql
insert into public.pathmark_users (email, role, status, notes)
values
  ('you@example.com', 'developer', 'active', 'Initial Pathmark developer account')
on conflict (email) do update
set
  role = excluded.role,
  status = excluded.status,
  notes = excluded.notes,
  updated_at = now();
```

## Shared ingredient catalogue

The shared ingredient catalogue is designed to avoid copying large seasonal/nutrition reference tables into every user's Google Sheet.

Recommended import order for reference data:

1. Insert canonical ingredients into `public.pathmark_ingredients`.
2. Insert aliases into `public.pathmark_ingredient_aliases`.
3. Insert produce seasonality into `public.pathmark_produce_seasonality`.
4. Insert nutrition reference rows into `public.pathmark_nutrition_reference`.

The app resolves ingredient data in this order:

1. User override in Pathmark Sync
2. User-created ingredient row in Pathmark Sync
3. Shared Pathmark Supabase catalogue
4. Not matched / user can add details manually

## Optional starter-pack library

The starter-pack tables remain useful for controlled recipe or dataset releases:

- `public.pathmark_starter_packs`
- `public.pathmark_starter_pack_rows`

Starter packs can still copy selected recipe/package rows into a user's Pathmark Sync sheet. Core ingredient reference data does not need to be copied if it exists in the shared catalogue.

Suggested Streamlit secrets for gated imports:

```toml
[starter_packs]
recipes_code_hash = "sha256_hex_of_recipes_access_code"
ingredients_code_hash = "sha256_hex_of_ingredients_access_code"
nutrition_code_hash = "sha256_hex_of_nutrition_access_code"
```
