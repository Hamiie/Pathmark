# Pathmark release hub

Current release: **v0.6.44 Streamlit-native appearance cleanup**

Pathmark is a Streamlit-based planning and export system that supports wellbeing routines, meaningful projects, and a Spending Plan for money-flow planning.

## Current packages

- `pathmark_release_hub_v0_6_44_streamlit_native_appearance_cleanup.zip`
- `Pathmark_Local_App_Windows_v0_6_44.zip`

## v0.6.44 Streamlit-native appearance cleanup

This release keeps the top-level **Theme** tab for Pathmark's seasonal accent, while leaving the actual Light/Dark/System appearance entirely to Streamlit's built-in menu.

Changes:

- Removes remaining legacy Pathmark light/dark data-attribute styling that could keep the app looking light after Streamlit Dark was selected.
- Stops the seasonal theme injector from applying a default light token set.
- Uses Streamlit's own CSS variables for page background, card surfaces, text, borders, inputs and popovers.
- Removes the old manual appearance sync approach from the practical theme flow.
- Keeps seasonal themes as accent choices only: **Summer**, **Autumn**, **Winter** and **Spring**.
- Preserves existing mobile/PWA branding metadata and favicon support.

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
  Pathmark_Local_App_Windows_v0_6_44.zip
.streamlit/
  config.toml
supabase/
  README.md
  migrations/
```
