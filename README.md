# Clearway Release Hub

This repository is the Streamlit Community Cloud release hub for Clearway.

It provides a polished front door and a download for the latest **local app source package**. The source package deliberately does not include a prebuilt `Start Clearway.exe`; run the builder on Windows before publishing a friend-facing app zip.

## Deploy

Deploy with Streamlit Community Cloud using:

```text
app/main.py
```

## Updating the download

1. Build or update the local app source package.
2. Put the zip in `downloads/`.
3. Update `latest_version.json`.
4. Commit to GitHub and reboot the Streamlit app.

## Safety rule

The app folder is replaceable. The Clearway folder is not.

Persistent user data belongs in:

```text
Clearway/00_System
Clearway/01_Body_And_Stability
Clearway/02_Home_And_Garden
...
```

Application files belong in:

```text
Clearway/local_app
```
