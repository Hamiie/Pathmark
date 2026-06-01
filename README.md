# Pathmark release hub

This repository hosts the Streamlit download page for Pathmark.

This release is Windows-only while the local app workflow is stabilised.

## Structure

```text
app/
  main.py
  assets/pathmark.png
downloads/
  Pathmark_Local_App_Windows_v0_5_81.zip
supabase/
  migrations/
    20260531000000_create_pathmark_access_tables.sql
latest_version.json
requirements.txt
.streamlit/config.toml
```

## Installation model

Pathmark separates the replaceable app files from the user's workspace:

```text
Documents\Pathmark            ← app files; replace on update
Documents\Workspace           ← default workspace; keep user projects and exports here
```

The launcher creates or points to the workspace folder on first launch. The workspace is used for area folders, exports, tasklists, backups, and the local database. Users can choose an existing folder if they already have one.

## Hosted login and role setup

Visitors can download Pathmark without logging in. Beta and developer features are hidden unless the user signs in with Google and has an allowed role. Unknown signed-in users default to `standard`.

The hosted login uses a Pathmark-managed Google OAuth flow rather than Streamlit `st.login()`. This avoids the Streamlit Authlib route issue while still keeping password entry with Google. Pathmark receives the verified Google email claim; it does not collect or store passwords.

Expected Streamlit secrets for hosted login:

```toml
[auth]
client_id = "YOUR_GOOGLE_WEB_CLIENT_ID"
client_secret = "YOUR_GOOGLE_WEB_CLIENT_SECRET"
login_redirect_uri = "https://pathmark.streamlit.app"
cookie_secret = "A_LONG_RANDOM_SECRET_USED_TO_SIGN_OAUTH_STATE"

[pathmark_access]
developer_emails = ["you@example.com"]
# Optional fallback while Supabase is being configured:
beta_tester_emails = []
disabled_emails = []
```

For backward compatibility, if `login_redirect_uri` is not provided, Pathmark will use `[google_oauth].redirect_uri` or strip `/oauth2callback` from `[auth].redirect_uri`.

The Google Cloud OAuth client should be a **Web application**. Add this authorised redirect URI for hosted login:

```text
https://pathmark.streamlit.app
```

From v0.5.81, Google login also requests the narrow `https://www.googleapis.com/auth/drive.file` scope so logged-in beta/developer users can enter Pathmark Online with a user-owned Pathmark sync sheet ready. This replaces the normal separate “Connect Google Sheets” step. Enable both Google Sheets API and Google Drive API in the same Google Cloud project, and add the drive.file scope to the OAuth consent screen.

Developer access should be bootstrapped through Streamlit secrets, not hard-coded into the public repository.


## Pathmark Web Companion direction

The hosted app is moving beyond simple on-the-go capture towards a Google-Sheet-backed web companion. The intended split is:

- **Online Pathmark:** routine and goal management backed by the user-owned Pathmark sync sheet.
- **Desktop Pathmark:** local Workspace folders, Markdown generation, backups, review/import, and heavier export workflows.

Supabase remains limited to access control: users, roles, status, feature flags, and audit logs. It must not store goals, routines, task prompts, calendar blocks, Workspace files, or personal planning content.

## Supabase access layer

From v0.5.74, the Supabase access-control schema is versioned in `supabase/migrations/` so a GitHub-linked Supabase project can track the database structure safely. Persistent role management uses Supabase rather than a Google Sheet service-account key. This version prefers Supabase Secret API keys (`sb_secret_...`) rather than legacy JWT-based `service_role` keys.

Supabase is used only for hosted Pathmark access control:

- user email
- role
- status
- last login
- feature flags
- audit logs

It should **not** store Pathmark goals, routines, Google Tasks prompts, calendar blocks, Workspace files, backups, Markdown files, or on-the-go planning entries.

Add these Streamlit secrets when Supabase is configured. New setups should use a Supabase Secret API key from **Settings → API Keys**:

```toml
[supabase]
url = "https://YOUR_PROJECT_ID.supabase.co"
secret_key = "sb_secret_YOUR_SUPABASE_SECRET_API_KEY"
```

`service_role_key` is still accepted as a migration fallback for older projects, but it is not recommended for new setups.

The schema is versioned in `supabase/migrations/20260531000000_create_pathmark_access_tables.sql`. For a new project, either let Supabase apply the migration through the GitHub integration, or run the same SQL manually in the Supabase SQL editor:

```sql
create table if not exists pathmark_users (
  email text primary key,
  role text not null default 'standard' check (role in ('standard', 'beta_tester', 'developer')),
  status text not null default 'active' check (status in ('active', 'disabled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login timestamptz,
  notes text
);

create table if not exists pathmark_feature_flags (
  key text primary key,
  enabled boolean not null default true,
  minimum_role text not null default 'standard' check (minimum_role in ('standard', 'beta_tester', 'developer')),
  updated_at timestamptz not null default now(),
  notes text
);

create table if not exists pathmark_audit_log (
  id uuid primary key default gen_random_uuid(),
  actor_email text,
  action text not null,
  target_email text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table pathmark_users enable row level security;
alter table pathmark_feature_flags enable row level security;
alter table pathmark_audit_log enable row level security;

insert into pathmark_feature_flags (key, enabled, minimum_role, notes)
values
  ('on_the_go_beta', true, 'beta_tester', 'Shows the On-the-go beta tab.'),
  ('developer_panel', true, 'developer', 'Shows the Developer settings tab.')
on conflict (key) do nothing;
```

Keep `[pathmark_access].developer_emails` in Streamlit secrets as an emergency bootstrap route even after Supabase is configured.

## Pathmark Online Google Sheet setup

From v0.5.81, the hosted login flow is also the Google Sheets/Drive authorisation flow. Users no longer need to complete a separate Google Sheets connection step in the normal path.

The main hosted login uses:

```text
openid email profile https://www.googleapis.com/auth/drive.file
```

The `drive.file` scope is deliberately narrow. It lets Pathmark create and update Pathmark sync files the user authorises, rather than requesting access to every spreadsheet in the user’s Google Drive. Private planning data remains in the user-owned Google Sheet, not in Supabase and not in this public repository.

Expected Streamlit secrets for the main Google login:

```toml
[auth]
client_id = "YOUR_GOOGLE_WEB_CLIENT_ID"
client_secret = "YOUR_GOOGLE_WEB_CLIENT_SECRET"
login_redirect_uri = "https://pathmark.streamlit.app"
cookie_secret = "A_LONG_RANDOM_SECRET_USED_TO_SIGN_OAUTH_STATE"
```

The older `[google_oauth]` section is still supported as a fallback/reconnect configuration, but new deployments should be able to use the same `[auth]` web client for both identity and Pathmark sync-sheet access.

Google Cloud checklist:

1. Use a **Web application** OAuth client.
2. Add the exact authorised redirect URI `https://pathmark.streamlit.app`.
3. If the OAuth app is in Testing, add the signed-in user as a test user.
4. Add the scope `https://www.googleapis.com/auth/drive.file` under Data Access.
5. Enable both **Google Sheets API** and **Google Drive API** for the same project.

When a beta/developer user opens the Web Companion, Pathmark attempts to find an existing app-visible `Pathmark Sync` spreadsheet. If it cannot find one, it creates a new user-owned sync sheet and prepares the `pending_changes` tab.

## Updating a release

1. Replace the Windows package in `downloads/`.
2. Update `latest_version.json`.
3. Keep `app/main.py` aligned with the file name and installation instructions.

Mac support has been removed for now.

## v0.5.81 focus

This release starts the Pathmark Online foundation by unifying Google login and Google Sheets/Drive access. Google login now requests identity plus the narrow `drive.file` scope, stores only a short-lived access token in the hosted Streamlit session, and automatically finds or creates the user-owned Pathmark sync sheet for beta/developer users.

The normal Web Companion path no longer requires a separate “Connect Google Sheets” step. Reconnect and diagnostics remain available for recovery and setup troubleshooting.
