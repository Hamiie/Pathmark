# Pathmark Release Hub

## v0.6.86 Navigation naming cleanup

- Renames **Pathmark Online beta** to **Planner** in user-facing navigation and headings.
- Renames **Spending Plan beta** to **Spending Plan**.
- Renames **Shopping List beta** to **Meal Plan**, while keeping **Shopping Lists** as a tab inside Meal Plan.
- Keeps beta-tester role/access controls unchanged behind the scenes.
- Preserves the v0.6.85 Starter Packs foundation and Supabase-backed NZ Seasonal Produce import model.

# Pathmark Release Hub

## v0.6.85 Starter Packs foundation

- Adds a Shopping List Nutrition tab with kcal and nutrition values by ingredient/portion.
- Loads the uploaded nutrition examples into Pathmark Sync defaults and maps them into grocery inventory categories.
- Recipes now estimate kcal per recipe and per serving when ingredient quantity/unit can be matched to nutrition data.
- Missing nutrition data and unsupported unit conversions are shown on the recipe page.
- Recipes can be exported to Pathmark Projects as a cooking activity.
- Adds a Pathmark Grocery Template Google Sheet workflow for bulk export/import of nutrition, inventory and recipes, with merge and clean import modes.

# Pathmark Release Hub

## v0.6.83 Shopping List beta foundation

- After Google login, Pathmark Online is used as the landing tab without hiding Home, Theme, About & Privacy, Spending Plan beta, or Developer tools.
- Dashboard progress cards no longer repeat the same completion phrase above and inside the progress bar; the card footer carries the phrase and the bar shows the percentage only.
- Preserves the v0.6.78 Terms CSS brace hotfix and the v0.6.77 task progress consistency/dashboard visual changes.


## v0.6.68 Google permissions onboarding and sync diagnostics

Adds a first-connection Google permissions explainer; updates privacy wording for combined Google permissions; adds Calendar Sync validation/results diagnostics; improves Tasks Sync write-back, refresh messaging, and repair by title/date for tasks created before IDs were stored.

# Pathmark release hub

Current release: **v0.6.68 Dark-mode contrast guardrails**

Pathmark is a Streamlit-based planning and export system that supports wellbeing routines, meaningful projects, and a Spending Plan for money-flow planning.

## Current packages

- `pathmark_release_hub_v0_6_51_dark_mode_contrast_guardrails.zip`
- `Pathmark_Local_App_Windows_v0_6_51.zip`

## What changed in v0.6.68

- Improved dark-mode contrast for Pathmark-owned cards, muted text and borders.
- Removed decorative gradients and emoji-style seasonal markers for a cleaner, sleeker interface.
- Kept **Seasonal** as one automatic theme alongside stable accent themes based on Pathmark colour families.
- Kept Streamlit responsible for Light, Dark and System, with Pathmark controlling restrained accent details only.

## Repository layout

See `REPOSITORY_STRUCTURE.txt`.


## v0.6.68
Pathmark Sync backup and restore foundation.
## v0.6.68 Default Areas for fresh Pathmark Sync

Rewrites `requirements.txt` as a dependency-only file so Streamlit Cloud can install dependencies correctly. Preserves the v0.6.68 missing Pathmark Sync recovery, backup/restore, Google Tasks sync, and Google Calendar sync foundations.

## v0.6.68 Missing Pathmark Sync recovery

- Adds a recovery screen when Pathmark Sync cannot be found or verified after Google login.
- Recovery options now include recreating Pathmark Sync, recreating it with starter examples, restoring a Pathmark Backup into a new sync sheet, and opening Google Drive Trash.
- Clears stale session sheet IDs when a linked sync sheet has been deleted or access has changed.
- Keeps Backup & restore in Settings for normal backups, backup restore, and restore-to-default workflows.
- Recreating or restoring Pathmark Sync does not delete Google Tasks or Google Calendar items; linked sync IDs may need review if starting fresh.

## v0.6.68 Google security guardrails

This release adds clearer Google security and consent guardrails: optional Tasks/Calendar scopes at the point of use, a Security & permissions section in Settings, safety-backup options before direct Tasks/Calendar sync, and expanded About & Privacy wording for dedicated Pathmark task lists/calendars, linked IDs, and token handling.



### v0.6.68 Default Areas for fresh Pathmark Sync
- Reworked the missing Pathmark Sync screen so it welcomes new users rather than presenting recovery as an error.
- Keeps the options to create a fresh sheet, create with starter examples, restore from backup, or check Google Drive Trash.
- Clarifies why the screen appears when no Pathmark Sync sheet is visible to the app.

### v0.6.68 Default Areas for fresh Pathmark Sync
- Fresh Pathmark Sync sheets now include editable default Areas so the Creation Wizard can be used immediately.
- Create-with-starter-examples still loads full editable examples without duplicating the default Area set.
- Restore-to-default now rebuilds the default schema and reloads default Areas unless starter examples are selected.
- The wizard can move from “+ Add a new area” into the area creation steps.

