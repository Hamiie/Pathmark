# Pathmark release hub

Current release: **v0.6.42 Streamlit-controlled appearance variant repair**

Pathmark is a Streamlit-based planning and export system that supports wellbeing routines, meaningful projects, and a Spending Plan for money-flow planning.

## Current packages

- `pathmark_release_hub_v0_6_42_streamlit_controlled_appearance_variant_repair.zip`
- `Pathmark_Local_App_Windows_v0_6_42.zip`

## v0.6.42 Streamlit-controlled appearance variant repair

This release removes Pathmark's separate appearance selector and returns the user-facing Light/Dark/System control to Streamlit's built-in menu.

Changes:

- Removes the visible **Pathmark appearance** setting from Pathmark Online Settings.
- Keeps only the seasonal theme selector: **Summer**, **Autumn**, **Winter** and **Spring**.
- Mirrors Streamlit's own **System / Light / Dark** menu into Pathmark's CSS light/dark seasonal variants.
- Strengthens event handling for the visible Streamlit appearance menu, including icon and label clicks.
- Keeps a manual **Sync with Streamlit appearance** fallback in Settings for browsers that do not apply a recent Streamlit appearance change immediately.
- Keeps mobile/PWA branding metadata and favicon support.

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
  Pathmark_Local_App_Windows_v0_6_42.zip
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
