# Pathmark v0.7.25 — Shared ingredient catalogue and user overrides

Pathmark helps you decide what matters, then make time for it.

This release adds a shared ingredient reference catalogue model backed by Supabase, with user-owned ingredient overrides stored in the user's own Pathmark Sync Google Sheet. Seasonality and nutrition reference data can now be read centrally without copying the full reference library into each user's Google Sheet. Users can still customise or add their own ingredient data, which is saved as a personal override.

The Nutrition workflow from v0.7.24 is preserved:

- Meal Plan for finding recipes and adding selected recipes to a shopping list
- Recipe Library for recipe data management
- Shopping List for pantry checking, shopping, trolley status and shopping-list cost estimates
- Ingredients for validation, Pathmark catalogue matching, and user overrides
- Inventory for stock, expiry, containers, pantry locations and stock movements

## Deployment notes

- Apply the Supabase migrations in `supabase/migrations/` before relying on shared ingredient catalogue lookups.
- Keep Streamlit secrets out of GitHub. Use Streamlit Cloud secrets for Supabase and Google OAuth credentials.
- The downloadable Windows package is included in `downloads/` because `latest_version.json` currently points to it. If you later move packages to GitHub Releases, update `latest_version.json` accordingly.

## Privacy model

Pathmark reference data can live in Supabase. User-owned planning, finance, nutrition, shopping, inventory and override data remains in the user's own Pathmark Sync Google Sheet. OAuth tokens, Google client secrets, Supabase keys, personal grocery exports and private user data must never be committed to GitHub.
