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
