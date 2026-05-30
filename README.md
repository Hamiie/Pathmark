# Pathmark release hub

This repository hosts the Streamlit download page for Pathmark.

This release is Windows-only while the local app workflow is stabilised.

## Structure

```text
app/
  main.py
  assets/pathmark.png
downloads/
  Pathmark_Local_App_Windows_v0_5_42.zip
latest_version.json
requirements.txt
.streamlit/config.toml
```

## Installation model

Pathmark separates the replaceable app files from the user's workspace:

```text
Documents\Pathmark App\Pathmark_app   ← app files; replace on update
Documents\Pathmark                    ← workspace; keep user projects and exports here
```

The launcher creates or points to the workspace folder. The workspace is used for area folders, exports, tasklists, backups, and the local database.

## Updating a release

1. Replace the Windows package in `downloads/`.
2. Update `latest_version.json`.
3. Keep `app/main.py` aligned with the file name and installation instructions.

Mac support has been removed for now.

## v0.5.42 focus

This release keeps the Windows-only structure but improves the local update workflow, workspace instructions, Area folder detection, and visual continuity between the release hub, launcher, and local app.
