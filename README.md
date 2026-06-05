# Pathmark release hub

Current release: **v0.6.38 Event-based theme change repair**

Pathmark is a Streamlit-based planning and export system that supports wellbeing routines, meaningful projects, and a Spending Plan for money-flow planning.

## Current packages

- `pathmark_release_hub_v0_6_38_event_based_theme_change_repair.zip`
- `Pathmark_Local_App_Windows_v0_6_38.zip`

## v0.6.38 Event-based theme change repair

This release keeps the mobile/PWA branding metadata from v0.6.37, but replaces the broad continuous appearance watcher with a safer event-based check.

Changes:

- Checks the active Streamlit appearance once when the app loads.
- Checks again only when Streamlit app-shell theme attributes/styles change, or when the OS colour-scheme event changes.
- Removes the repeated one-second polling loop from v0.6.37.
- Avoids observing broad body subtree mutations, reducing the risk of a deploy/runtime loop.
- Keeps Pathmark seasonal themes as Summer, Autumn, Winter and Spring, with light/dark variants controlled by Streamlit Light/Dark/System.
- Keeps the manual Refresh theme display fallback in Settings.

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
  static/
downloads/
  Pathmark_Local_App_Windows_v0_6_38.zip
.streamlit/
  config.toml
supabase/
  README.md
  migrations/
static/
  manifest.json
  favicon.ico
  pathmark-icon-*.png
```
