# Supabase schema for Pathmark

This folder contains the Supabase database schema used by the hosted Pathmark release hub.

Pathmark uses Supabase only for hosted access control:

- user email
- role
- status
- feature flags
- audit logs

It must not store goals, routines, Google Tasks prompts, calendar blocks, Workspace files, backups, Markdown files, OAuth tokens, or on-the-go planning entries.

## Migration

The migration in `migrations/20260531000000_create_pathmark_access_tables.sql` creates:

- `public.pathmark_users`
- `public.pathmark_feature_flags`
- `public.pathmark_audit_log`

It enables Row Level Security on all three tables and deliberately creates no public RLS policies. The hosted Streamlit app should access these tables from server-side code only, using a Supabase Secret API key stored in Streamlit secrets.

## Initial developer account

Do not put personal developer rows or private email allowlists in public migrations.

For initial access, either:

1. keep `[pathmark_access].developer_emails` in Streamlit secrets as a bootstrap route; or
2. manually insert your developer row in the Supabase SQL editor.

Example manual insert:

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

## Required Streamlit secrets

```toml
[supabase]
url = "https://YOUR_PROJECT_ID.supabase.co"
secret_key = "sb_secret_YOUR_SUPABASE_SECRET_API_KEY"
```

Never commit Streamlit secrets, Supabase keys, Google OAuth client secrets, or local `.env` files to GitHub.

## Optional starter-pack library

The migration `20260607000000_add_starter_pack_tables.sql` adds optional read-only starter-pack tables:

- `public.pathmark_starter_packs`
- `public.pathmark_starter_pack_rows`

These can hold curated library data such as NZ Seasonal Produce, nutrition reference rows, and recipe starters. They are for controlled starter-library distribution only. User-edited grocery inventory, recipes, shopping lists, planning records, calendar rows, and spending data still belong in the user's own Pathmark Sync Google Sheet, not in Supabase.

Suggested Streamlit secrets for gated imports:

```toml
[starter_packs]
nz_seasonal_produce_code_hash = "sha256_hex_of_access_code"
# or, for local testing only:
# nz_seasonal_produce_code = "plain-text-code"
```

Imported starter-pack rows are copied into the user's Pathmark Sync sheet and become editable user data. This is controlled distribution, not copy protection.

## Consolidated Meal Plan starter packs

The current Meal Plan import model expects three separate Supabase starter packs:

- `recipes` — recipe metadata and classification rows only
- `ingredients` — pantry/grocery/produce inventory rows, including supermarket category, preferred unit, and seasonality where available
- `nutrition` — nutrition reference rows used for kcal and nutrient lookups

Import the consolidated CSV bundle into Supabase in this order:

1. `pathmark_starter_packs.csv` into `public.pathmark_starter_packs`
2. `pathmark_starter_pack_rows.csv` into `public.pathmark_starter_pack_rows`

The app intentionally does not bundle the curated dataset in the public GitHub repository. Supabase holds the starter-library rows, and Pathmark copies selected packs into the user's own Pathmark Sync sheet after access-code validation.

Suggested access-code secrets:

```toml
[starter_packs]
recipes_code_hash = "sha256_hex_of_recipes_access_code"
ingredients_code_hash = "sha256_hex_of_ingredients_access_code"
nutrition_code_hash = "sha256_hex_of_nutrition_access_code"
```

For local testing only, plain codes are also recognised:

```toml
[starter_packs]
recipes_code = "TEST-RECIPES-CODE"
ingredients_code = "TEST-INGREDIENTS-CODE"
nutrition_code = "TEST-NUTRITION-CODE"
```
