# Pathmark Release Hub

Current release: **v0.6.37 Mobile branding and theme variant repair**

Pathmark is a Streamlit-based planning and export system. It supports wellbeing routines, progress projects, calendar/task exports, and a Spending Plan beta for money-flow planning.

## Hosted Pathmark Online

The hosted release hub lives in `app/main.py` and runs on Streamlit Cloud. It provides the public homepage, About & Privacy, Google login, Pathmark Online, Spending Plan beta, and developer/diagnostic tools where appropriate.

Pathmark Online stores planning records in the user's own Google Sheet called **Pathmark Sync**. Supabase is used only for access/profile metadata.

## Local Windows package

The latest local Windows package is stored in `downloads/`:

- `Pathmark_Local_App_Windows_v0_6_37.zip`

## v0.6.37 Mobile branding and theme variant repair

This release strengthens Pathmark's mobile/PWA branding metadata and repairs the relationship between Pathmark seasonal themes and Streamlit's Light/Dark/System setting.

Key changes:

- Adds stronger Pathmark manifest and mobile icon metadata.
- Adds cache-busted Pathmark icon references for mobile install prompts and browser tabs.
- Separates seasonal theme choice from appearance mode.
- Provides light and dark variants for each seasonal theme.
- Adds a browser-side appearance watcher so Pathmark can respond when Streamlit's theme menu changes without a full Python rerun.
- Adds a manual theme refresh fallback in Settings.

## Notes

Google's own sign-in and consent screens are controlled by Google Cloud OAuth branding, not by this repository. Mobile browsers may also cache an old Streamlit install prompt; clearing site data or reinstalling may be needed after deployment.
