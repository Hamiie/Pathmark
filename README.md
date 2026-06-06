# Pathmark release hub

Current release: **v0.6.46 Seasonal accent visibility and contrast repair**

Pathmark is a Streamlit-based planning and export system that supports wellbeing routines, meaningful projects, and a Spending Plan for money-flow planning.

## Current packages

- `pathmark_release_hub_v0_6_46_seasonal_accent_visibility_contrast_repair.zip`
- `Pathmark_Local_App_Windows_v0_6_46.zip`

## v0.6.46 Seasonal accent visibility and contrast repair

This release continues the Streamlit-native theme approach. Streamlit still owns Light, Dark and System appearance, while Pathmark seasonal themes control accents only.

Changes:

- Improves contrast for muted text, captions, card borders and Pathmark-owned surfaces in dark mode.
- Makes the seasonal accent preview apply immediately when Summer, Autumn, Winter or Spring is selected, even before saving.
- Uses stronger seasonal accent colours so the selected season is visibly reflected in buttons, selected tabs, progress bars and accent panels.
- Keeps Pathmark from overriding Streamlit's core page background, text, input and settings-menu styling.
- Adds a small seasonal preview card to make it obvious when the selected seasonal accent has changed.

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
  Pathmark_Local_App_Windows_v0_6_46.zip
.streamlit/
  config.toml
supabase/
  README.md
  migrations/
```
