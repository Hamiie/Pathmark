# Pathmark release hub

This repository hosts the Streamlit download page for Pathmark.

This release is Windows-only while the local app workflow is stabilised.

## Structure

```text
app/
  main.py
  assets/pathmark.png
downloads/
  Pathmark_Local_App_Windows_v0_5_89.zip
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


## Pathmark Online direction

The hosted app is becoming a Google-Sheet-backed version of the Pathmark planning system. It should feel close to the desktop app, with the main difference being storage and publishing:

- **Pathmark Online:** Areas, goals, projects, routines, calendar blocks, task prompts, tasklists, quick captures, and browser downloads backed by the user-owned Pathmark Sync sheet.
- **Pathmark Desktop:** the same planning model plus local Workspace folders, Markdown generation, local backups, review/import, and heavier publishing workflows.

v0.5.88 restores a reliable Google login control after the v0.5.87 custom same-tab OAuth button proved unreliable in deployment. The hosted app keeps the Pathmark Online refinements from v0.5.87, including clearer guidance, Google Calendar colour selection, routine validation, PDF tasklist export, theme saving, and Google Tasks export-to-sheet support. Supabase remains limited to access control: users, roles, status, feature flags, and audit logs. It must not store goals, routines, task prompts, calendar blocks, Workspace files, or personal planning content.

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

## Privacy and storage model

Pathmark separates app code, deployment secrets, hosted access management, and personal planning data. This is important for beta testing and for user trust.

- **User-owned Google Sheet:** Pathmark Online stores Areas, routines, goals, actions, setup progress, tasklist/export records, and archive status in a `Pathmark Sync` spreadsheet owned by the signed-in user. The app uses the narrow Google `drive.file` permission so it can create and update Pathmark files the user authorises without requesting broad access to all spreadsheets.
- **Desktop Workspace:** the Windows app stores local Workspace folders, Markdown files, exports, tasklists, backups, database records, routines, goals, and Areas in the Workspace folder selected by the user.
- **Supabase:** Supabase stores access/profile metadata only: email, role, account status, feature flags, last-login/audit records, and theme preference. It must not store goals, routines, task prompts, calendar plans, Workspace files, Markdown, backups, or private planning content.
- **GitHub:** the public repository stores the app code, release packages, migration files, and documentation. It must not contain OAuth secrets, Supabase keys, tokens, user Workspace files, personal planning sheets, or private planning data.
- **Streamlit secrets:** deployment credentials such as Google OAuth secrets and Supabase secret keys belong in Streamlit secrets, not in GitHub.

The hosted **About & Privacy** tab explains this in user-facing language and identifies how Google, Streamlit, Supabase, and GitHub are used.

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

## v0.5.82 focus

This release rewrites the hosted homepage around the emerging Pathmark Online/Desktop model and adds clearer user-facing privacy and storage guidance.

Pathmark Online is framed as a Google-Sheet-backed routine and goal management system. Pathmark Desktop remains the local Workspace, Markdown, backups, and publishing/export version. The homepage now explains where data is stored:

- local planning files and Markdown live in the user's chosen Workspace;
- Pathmark Online records live in the user's own Pathmark Sync Google Sheet;
- Supabase stores only access-control data such as email, role, status, feature flags, and audit logs;
- GitHub stores code and release packages, not private planning data or secrets.



## v0.5.88 Google login reliability fix

The hosted app now uses Streamlit's native link button for Google OAuth again. This may open Google in a new tab, but it avoids the custom same-tab button behaviour that could be unclickable in deployment. The Pathmark Online feature set from v0.5.87 is otherwise preserved.

## v0.5.87 Pathmark Online refinements

This release continues moving Pathmark Online toward the same routine and goal management model as the desktop app while keeping user planning data in the user's own Google Sheet.

Key refinements:
- More user-facing guidance for routines, goals, calendar blocks, and Google Tasks prompts.
- Same-tab Google sign-in and reconnect controls to reduce duplicate browser tabs.
- Google Calendar colour dropdowns for Areas.
- Stronger routine frequency/preferred-day validation for exports.
- Printable PDF tasklist export.
- Online theme selection saved to the Pathmark Sync sheet.
- Google Tasks export can be written to a `google_tasks_export` tab in the Pathmark Sync sheet.

Security note: Pathmark still does not store goals, routines, task prompts, calendar plans, or Workspace files in Supabase. Supabase remains the access layer only.


## v0.5.92

This release tidies Pathmark Online for beta testing:

- fixes the missing `read_online_tables` wrapper that caused a user-facing NameError;
- moves connection and diagnostic controls into Settings so the main Online workspace starts with the useful tabs;
- removes redundant general guidance from the Online page;
- expands the About & Privacy tab with clearer Google access, storage, disconnect, GitHub and Streamlit secrets explanations;
- keeps personal planning data in the user-owned Google Sheet, not Supabase or GitHub.

## v0.5.91 notes

This release polishes Pathmark Online's user-facing guidance. The online Home page now presents a stepped guide through Areas, routines, goals, actions and exports, rather than describing backend parity with the desktop app. The printable tasklist PDF has been improved and the plain text tasklist export has been removed from the normal interface.


## v0.5.92

This release tidies Pathmark Online for beta testing:

- fixes the missing `read_online_tables` wrapper that caused a user-facing NameError;
- moves connection and diagnostic controls into Settings so the main Online workspace starts with the useful tabs;
- removes redundant general guidance from the Online page;
- expands the About & Privacy tab with clearer Google access, storage, disconnect, GitHub and Streamlit secrets explanations;
- keeps personal planning data in the user-owned Google Sheet, not Supabase or GitHub.

## v0.5.91 hosted theme persistence

Pathmark Online now applies the selected theme across the hosted interface, including high-contrast mobile buttons. The chosen theme is stored as a small `theme_preference` value on the Supabase access profile so it can follow the signed-in user. This is UI metadata only; goals, routines, actions, tasklists, calendar blocks, and other planning records remain in the user's Pathmark Sync Google Sheet.


## v0.5.93

- Improved mobile contrast for Pathmark Online, especially tab labels, field labels, select boxes, and button text in mobile or in-app browsers.
- Kept the existing privacy, Google Sheets, Supabase, and Pathmark Online behaviour unchanged.


## Mobile home-screen install metadata

The hosted Pathmark app includes PWA-style metadata so mobile browsers can save the site with the Pathmark name and icon rather than the default Streamlit branding.

Static files are served from `app/static/` and require:

```toml
[server]
enableStaticServing = true
```

Included files:

```text
app/static/manifest.json
app/static/pathmark-icon-192.png
app/static/pathmark-icon-512.png
app/static/apple-touch-icon.png
```

The hosted app injects the manifest and icon links into the page head at runtime. Browser and in-app-browser behaviour can vary, so users may need to remove an old saved shortcut and add Pathmark again after deployment.


## v0.5.95

Adds the Pathmark Online guided setup pathway and export-to-archive workflow. Setup status and archive/export metadata are stored in the user-owned Pathmark Sync Google Sheet.

## v0.5.96 About & Privacy user-facing revision

This release revises the hosted About & Privacy page so it explains Pathmark's storage and access model in user-facing language rather than backend/developer language. It clarifies how Pathmark uses Google, Streamlit, Supabase and GitHub, and keeps the same privacy boundary: personal planning records belong in the user's Google Sheet or local Workspace, not in Supabase or GitHub.

A release-package safety scan was also run for obvious secrets and private data patterns, including Supabase `sb_secret_...` keys, Google client secrets, Google API keys, private keys, OAuth access/refresh tokens, JWT-like service-role tokens, and the developer's email address. Only documented placeholder text for `sb_secret_...` remained in README/app setup guidance; no real secret values were found.

## v0.5.97 Guided setup as primary first-time experience

- Pathmark Online now greets users with guided setup when setup is not complete, rather than burying setup underneath the Home dashboard.
- Guided setup uses a vertical step-by-step flow: Areas, Routines, Goals, Actions, Exports and Archive.
- Users can go back, move to the next step, finish setup or skip setup for the current session.
- Example text appears as placeholders and guidance only; it is not written to the user's Pathmark Sync Google Sheet unless the user types information and saves it.
- The full Pathmark Online workspace remains available after setup, or for the current session if the user chooses to skip setup.


## v0.5.98 Guided setup polish and NZ validation

- Fixed guided setup navigation so Next, Back and Skip do not call `st.rerun()` from callbacks.
- Kept guided setup as the primary first-time Pathmark Online experience while removing the duplicate full-workspace skip expander.
- Reworked setup progress into a cleaner vertical orientation flow.
- Changed setup examples into placeholders/guidance only; examples are not written to the Pathmark Sync sheet unless the user saves them.
- Updated setup date prompts to use DD-MM-YYYY for New Zealand users while storing normalised dates for export processing.
- Improved routine setup so the example 8-hour sleep block uses 480 minutes and routine setup requires a first-step prompt/activity.
- Added Review Queue orientation into setup and reframed Exports as orientation rather than a setup data-entry step.
