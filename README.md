# Pathmark Release Hub

Current release: **v0.6.28 Dashboard and finance visual refinement**

Pathmark is a Streamlit-based planning and export system. This repository contains the hosted release hub / Pathmark Online app, documentation, Supabase migrations, and the latest downloadable local Windows package.

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

v0.6.28 refines the Dashboard and Spending Plan layouts with calmer information hierarchy, prioritised attention cards, compact metrics, and plain-English money-flow guidance.

## Security

Do not commit secrets, OAuth client secrets, Google access or refresh tokens, service account JSON, Supabase service keys, private planning data, or developer email addresses.
