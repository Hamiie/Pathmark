# Pathmark release hub

## v0_6_23 Helper checklist and NZ date repair

This repository hosts the Streamlit release hub and Pathmark Online app for Pathmark.

This release is Windows-only while the local app workflow is stabilised.

### Release notes

- Aligns the manual Projects and Routines sections with the Creation Wizard model.
- Every saved project step or routine activity now automatically creates calendar time, a weekly tasklist row and a Google Tasks checklist item.
- Manual project/routine activity forms now require start date, start time, finish date and finish time before saving.
- Routine activities inherit the routine repeat pattern from the routine container.
- Wizard-created Google Tasks checklist items are not duplicated by derived export rows.
- The updated repository keeps only the latest Windows package in `downloads/`.

## Structure

```text
.gitignore
README.md
requirements.txt
latest_version.json
REPOSITORY_STRUCTURE.txt
app/
  main.py
  assets/
    pathmark.png
  static/
    apple-touch-icon.png
    manifest.json
    pathmark-icon-192.png
    pathmark-icon-512.png
downloads/
  Pathmark_Local_App_Windows_v0_6_23.zip
.streamlit/
  config.toml
supabase/
  README.md
  migrations/
    20260531000000_create_pathmark_access_tables.sql
    20260601000000_add_pathmark_user_theme_preference.sql
```

## Hosted Pathmark release hub and Pathmark Online

The hosted app runs from `app/main.py` and provides:

- the public release hub and homepage
- About & Privacy
- Google login
- Supabase-backed access/profile metadata
- Pathmark Online
- Spending Plan beta
- developer diagnostics where appropriate

Pathmark Online stores user planning records in the user's own Google Sheet named `Pathmark Sync`. Supabase is used only for access/profile metadata, not private planning content.

## Local Windows app package

The downloadable local Windows package remains in `downloads/` and is distinct from Pathmark Online. The local app is the desktop Workspace manager and remains responsible for local files, Markdown creation, `.ics` exports, Google Tasks exports, backups and related desktop workflows.

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

Google login also requests the narrow `https://www.googleapis.com/auth/drive.file` scope so logged-in beta/developer users can enter Pathmark Online with a user-owned Pathmark Sync sheet ready. Enable both Google Sheets API and Google Drive API in the same Google Cloud project, and add the `drive.file` scope to the OAuth consent screen.

Developer access should be bootstrapped through Streamlit secrets, not hard-coded into the public repository.

## Safety notes

GitHub should contain code, release packages, documentation and migrations only. Do not commit secrets, OAuth tokens, private keys, service account JSON, or private planning data.
