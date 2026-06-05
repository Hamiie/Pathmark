# Pathmark release hub

## v0_6_25 Spending Plan setup and assessment rebuild

Pathmark is a Streamlit-based planning and export system.

This repository contains the hosted Pathmark release hub and Pathmark Online code. The downloadable local Windows workspace package is kept in `downloads/`.

Current release focuses on:

- rebuilding Spending Plan beta as a setup-and-assessment flow instead of a one-off finance wizard;
- guiding users through maintained income sources, maintained spending categories, cash-flow assessment, and AP/account-role instructions;
- using common income sources and spreadsheet-derived spending buckets/sections for data validation;
- showing safe weekly spending, weekly APs/transfers, surplus or shortfall warnings, and emergency/debt/savings guidance;
- keeping the five account roles fixed while allowing the user to map those roles to their own bank accounts outside Pathmark;
- retaining the wider Pathmark wizard, project, routine, calendar, tasklist and Google Tasks behaviour from the previous release.

## Repository structure

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
  Pathmark_Local_App_Windows_v0_6_25.zip
.streamlit/
  config.toml
supabase/
  README.md
  migrations/
```

## Notes

Do not commit Streamlit secrets, Google client secrets, API keys, OAuth tokens, service account JSON files, private planning data, or downloaded user sync data.
