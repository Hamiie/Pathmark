# Pathmark release hub

Current release: **v0.6.45 Streamlit-native seasonal accent themes**

Pathmark is a Streamlit-based planning and export system that supports wellbeing routines, meaningful projects, and a Spending Plan for money-flow planning.

## Current packages

- `pathmark_release_hub_v0_6_45_streamlit_native_seasonal_accent_themes.zip`
- `Pathmark_Local_App_Windows_v0_6_45.zip`

## v0.6.45 Streamlit-native seasonal accent themes

This release simplifies the theme system so Streamlit owns the full Light, Dark and System appearance mode, while Pathmark seasonal themes only set accents and Pathmark-owned custom component styling.

Changes:

- Removes Pathmark JavaScript appearance watching and Light/Dark/System mirroring.
- Removes Pathmark CSS that attempted to control global page background, global text colour, inputs, popovers and Streamlit settings menu colours.
- Keeps **Theme** as a top-level tab for seasonal accent only: **Summer**, **Autumn**, **Winter** and **Spring**.
- Lets Streamlit's built-in Settings menu control the page's actual light/dark appearance.
- Keeps Pathmark custom cards, badges, progress bars and buttons styled with seasonal accent variables.
- Simplifies `.streamlit/config.toml` so Pathmark no longer defines competing full light and dark theme palettes.

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
  Pathmark_Local_App_Windows_v0_6_45.zip
.streamlit/
  config.toml
supabase/
  README.md
  migrations/
```
