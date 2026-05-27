# Development System Demo

This is a shareable Streamlit demo build of the Development System app.

It is designed for a friend to try the interface with sample data. It is **not** connected to a personal OneDrive folder and should not be used for private live data on Streamlit Community Cloud.

## What is included

- Goals and project actions
- Routines and routine activities
- Tasklist PDF export
- Google Calendar `.ics` export
- Google Tasks `.csv` export compatible with the Apps Script header structure
- Review Queue
- Archive
- Seasonal/dark theme options
- Demo-safe local workspace under `demo_workspace/`

## Run locally

```bat
py -m pip install -r requirements.txt
py -m streamlit run app\main.py
```

## Deploy to Streamlit Community Cloud

1. Create a new private GitHub repository.
2. Upload the contents of this folder to the repository root.
3. Go to Streamlit Community Cloud.
4. Create a new app from the GitHub repository.
5. Set the main file path to:

```text
app/main.py
```

6. Deploy the app.
7. Share the private app link only with people you want to test it.

## Data safety

This demo uses local app storage. On Streamlit Community Cloud, local data may reset when the app restarts or redeploys.

Do not enter private or sensitive information into the deployed demo.

For a real shared app, the next architecture step would be:

- hosted database such as Supabase/PostgreSQL
- user authentication
- per-user data isolation
- cloud file storage or export-only file handling
- Streamlit secrets for credentials

## Google Tasks CSV compatibility

The app exports the required columns first:

```text
Task ID
Task List
Title
Notes
Due Date
Reminder Time
Status
```

Additional columns may appear after those. The existing Apps Script should still work if it locates columns by header name.
