# Pathmark Release Hub

This repository deploys the public Streamlit release hub for Pathmark.

Pathmark helps users make time for routines, reduce friction with useful prompts, and keep goals moving. The hosted Streamlit page is the download and update hub; the working app is downloaded and run locally so it can create tasklists, backups, calendar exports, Google Tasks exports, and planning files in the folder the user chooses.

Deploy with Streamlit Community Cloud using:

```text
app/main.py
```

## Repository contents

```text
app/
downloads/
.streamlit/
README.md
latest_version.json
requirements.txt
.gitignore
```

## Local package

The downloadable Pathmark package lives in `downloads/`.

The local package is build-first: it includes `build_launcher_exe.bat`. Run that inside the extracted local package to create `Start Pathmark.exe`. The included `Start Pathmark.cmd` remains available as a fallback launcher.

Do not include an old compiled launcher in the source package. Build the launcher from the current source before preparing a new release download.
