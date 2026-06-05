# Pathmark Release Hub

Current release: **v0.6.34 Pathmark logo and OAuth branding refinement**

Pathmark is a Streamlit-based planning and export system. This repository contains the hosted release hub / Pathmark Online app, documentation, Supabase migrations, static app icons, and the latest downloadable local Windows package.

## Contexts

### Hosted release hub / Pathmark Online

- Main app: `app/main.py`
- Hosted target: Streamlit Community Cloud
- Includes the public homepage, About & Privacy, Google login, Supabase access roles, Pathmark Online, Spending Plan beta, and developer tools where appropriate.

### Local Windows package

- Stored in `downloads/`
- Contains the desktop Pathmark Workspace manager.
- The repository should include only the latest local package.

## Current focus

v0.6.34 strengthens Pathmark branding in the browser tab, mobile/PWA shortcuts and OAuth callback reloads. It also documents that Google's own account chooser and consent screens are controlled through Google Cloud OAuth branding rather than Streamlit code.

## Security

Do not commit secrets, OAuth client secrets, Google access or refresh tokens, service account JSON, Supabase service keys, private planning data, or developer email addresses.

## v0.6.34 Pathmark logo and OAuth branding refinement

- Added root static icon files for Streamlit static serving.
- Added `favicon.ico` plus 16px, 32px, 192px and 512px PNG icons.
- Reinforced browser-tab and PWA metadata with cache-busted Pathmark icon links.
- Added About & Privacy wording explaining Google sign-in branding.
- Added developer OAuth diagnostics guidance to set the Google Auth Platform branding app name/logo.
