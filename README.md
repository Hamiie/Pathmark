# Pathmark Release Hub

Current release: **v0.6.30 Spending Plan guided checklist refinement**

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

v0.6.30 reworks the Spending Plan spending setup into a guided checklist. Users can work down common real-world costs grouped by money-flow role, and custom items now start with the item name rather than abstract category fields.

## Security

Do not commit secrets, OAuth client secrets, Google access or refresh tokens, service account JSON, Supabase service keys, private planning data, or developer email addresses.


## v0.6.30 Spending Plan guided checklist refinement

- Reworked Spending Plan spending setup into a guided checklist grouped by money-flow role.
- Users now work down common real-world costs instead of choosing abstract categories first.
- Custom spending items now start with the item name and suggest the money-flow destination based on cost type.
