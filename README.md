# Pathmark release hub

Current release: **v0.6.39 Streamlit appearance recognition repair**

Pathmark is a Streamlit-based planning and export system that supports wellbeing routines, meaningful projects, and a Spending Plan for money-flow planning.

## Current packages

- `pathmark_release_hub_v0_6_39_streamlit_appearance_recognition_repair.zip`
- `Pathmark_Local_App_Windows_v0_6_39.zip`

## v0.6.39 Streamlit appearance recognition repair

This release keeps the mobile/PWA branding metadata from v0.6.38, but changes the light/dark handling so Pathmark responds directly to Streamlit appearance menu selections instead of trying to infer the setting from page backgrounds that Pathmark itself may have styled.

Changes:

- Listens for Streamlit **Light**, **Dark** and **System** menu selections and applies the matching Pathmark appearance mode.
- Stores the last selected appearance choice in browser local storage so the mode is reapplied on reload.
- Keeps **System** tied to the browser/OS colour scheme and updates when that event changes.
- Strengthens light and dark contrast for the app shell, header, cards, inputs and Streamlit menu popovers.
- Keeps Pathmark seasonal themes as Summer, Autumn, Winter and Spring, with light/dark variants controlled by Streamlit Light/Dark/System.

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
  Pathmark_Local_App_Windows_v0_6_39.zip
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
