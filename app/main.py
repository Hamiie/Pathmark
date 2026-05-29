from __future__ import annotations

import json
from pathlib import Path
from datetime import date

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "downloads"
VERSION_FILE = ROOT / "latest_version.json"

st.set_page_config(
    page_title="Clearway",
    page_icon="CW",
    layout="wide",
)

CSS = """
<style>
:root {
    --bg: #f5f1e8;
    --ink: #262320;
    --muted: #6e6861;
    --surface: #fffaf0;
    --surface-alt: #efe6d8;
    --line: #c9b89f;
    --accent: #a87a4d;
    --accent-dark: #755536;
    --blue-surface: #e9f2fb;
    --blue-ink: #154f86;
    --green-surface: #e8f4ea;
    --green-ink: #275d33;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg);
    color: var(--ink);
}

.block-container {
    max-width: 1180px;
    padding-top: 3rem;
    padding-bottom: 4rem;
}

h1, h2, h3 {
    letter-spacing: 0.035em;
}

.hero {
    padding: 2rem 0 1.2rem 0;
}

.hero h1 {
    font-size: 4rem;
    line-height: 1.05;
    margin-bottom: 0.6rem;
}

.hero p {
    color: var(--muted);
    font-size: 1.25rem;
    max-width: 860px;
}

.product-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 1.25rem;
    padding: 1.3rem 1.4rem;
    min-height: 150px;
}

.product-card h3 {
    margin-top: 0;
    margin-bottom: 0.45rem;
    font-size: 1.15rem;
}

.product-card p, .product-card li {
    color: var(--muted);
    font-size: 1rem;
}

.notice {
    padding: 1.1rem 1.25rem;
    border-radius: 1rem;
    background: var(--blue-surface);
    color: var(--blue-ink);
    border: 1px solid #c6def2;
    font-size: 1.05rem;
    margin: 1.4rem 0;
}

.update-safe {
    padding: 1rem 1.15rem;
    border-radius: 1rem;
    background: var(--green-surface);
    color: var(--green-ink);
    border: 1px solid #c8e3cb;
    margin: 1rem 0;
}

.path-box {
    background: #25211c;
    color: #f2eadf;
    border-radius: 1rem;
    padding: 1rem 1.2rem;
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    line-height: 1.55;
    overflow-x: auto;
}

.version-pill {
    display: inline-block;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: var(--surface-alt);
    border: 1px solid var(--line);
    color: var(--ink);
    font-weight: 600;
    margin-right: 0.5rem;
}

.stDownloadButton button, .stButton button {
    border-radius: 0.8rem !important;
    min-height: 3rem;
}

.small-muted {
    color: var(--muted);
    font-size: 0.95rem;
}

@media (max-width: 700px) {
    .hero h1 { font-size: 2.6rem; }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


def load_version() -> dict:
    if VERSION_FILE.exists():
        return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    return {"latest_version": "unknown", "release_date": str(date.today()), "package_name": "", "notes": []}


def package_path(version: dict) -> Path:
    name = version.get("package_name") or "Clearway_Local_App.zip"
    return DOWNLOADS / name


def download_bytes(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


version = load_version()
local_package = package_path(version)

st.markdown(
    """
<div class="hero">
    <h1>Clearway</h1>
    <p>A local-first system for making time for healthy habits, reducing friction with prompts, and moving goals forward.</p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="notice">
    This page is the public release hub. The real app runs locally on your computer, so it can safely work with your own Clearway folder and local files.
</div>
""",
    unsafe_allow_html=True,
)

version_col, date_col, package_col = st.columns([1.1, 0.9, 1.1])
with version_col:
    st.metric("Latest local app source", version.get("latest_version", "unknown"))
with date_col:
    st.metric("Release date", version.get("release_date", "unknown"))
with package_col:
    st.metric("Download", local_package.name if local_package.exists() else "Package missing")

st.divider()

st.header("What this app is for")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        """
<div class="product-card">
<h3>Plan meaningful work</h3>
<p>Create goals and projects, keep next actions visible, choose a focus, and close work with a short archive review.</p>
</div>
""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        """
<div class="product-card">
<h3>Maintain routines</h3>
<p>Build repeatable routines with activities, times, and task prompts that support wellbeing and reduce friction to begin.</p>
</div>
""",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        """
<div class="product-card">
<h3>Work with local files</h3>
<p>Generate Markdown files, backups, tasklists, Google Calendar exports, and Google Tasks CSV files into your own folder system, with setup files for the Google Tasks Apps Script importer.</p>
</div>
""",
        unsafe_allow_html=True,
    )

st.header("How it works")

left, right = st.columns([1.05, 1])
with left:
    st.markdown(
        """
The hosted page is only the front door. It lets you download the latest local app and see release notes.

The local app opens in your browser, but it runs on your own computer. That is what lets it create and update local folders, Markdown files, backups, calendar exports, and Google Tasks exports.

The local app is designed so application files can be replaced during updates while your personal Clearway folder remains separate.
"""
    )
with right:
    st.markdown(
        """
<div class="path-box">Clearway/
  00_System/
    DEV_DASHBOARD.md
    SYSTEM_GUIDE.md
    development_system.db
    Backups/
    Tasklists/
    Google Calendar Exports/
    Google Tasks Exports/
  01_Body_And_Stability/
  02_Home_And_Garden/
  ...
  local_app/   ← replaceable app files</div>
""",
        unsafe_allow_html=True,
    )

st.divider()

st.header("Choose your path")
new_tab, update_tab, demo_tab = st.tabs(["New installation", "Update existing installation", "Try / understand first"])

with new_tab:
    st.subheader("Install the local app")
    st.write(
        "Use this if Clearway has not been installed on this computer before. "
        "On first run, the app asks where your Clearway folder should live."
    )
    if local_package.exists():
        st.download_button(
            "Download local app source for Windows",
            data=download_bytes(local_package),
            file_name=local_package.name,
            mime="application/zip",
            use_container_width=True,
            key="download_new_installation",
        )
    else:
        st.error("The local app source package is missing from the downloads folder in this release hub.")

    st.markdown("### First-time setup")
    st.markdown(
        """
1. Download the local app zip.
2. Extract the zip.
3. Run **build_launcher_exe.bat** if you are preparing a friend-facing package, then double-click **Start Clearway.exe**. If the EXE has not been built yet, use **Start Clearway.cmd** as the fallback.
4. The launcher prepares the local app and opens it in your browser.
5. Choose where your Clearway folder should live.
6. The app creates only missing folders and files.
"""
    )

with update_tab:
    st.subheader("Update an existing local app")
    st.markdown(
        """
<div class="update-safe"><strong>The app folder is replaceable. The Clearway folder is not.</strong><br>
Before updating, create an update backup in the local app. Then replace only the <code>local_app</code> folder.</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
Your database, Markdown files, backups, tasklists, calendar exports, Google Tasks exports, and area folders should live in `00_System` and the area folders, not inside the replaceable app folder.
"""
    )
    if local_package.exists():
        st.download_button(
            "Download latest local app source",
            data=download_bytes(local_package),
            file_name=local_package.name,
            mime="application/zip",
            use_container_width=True,
            key="download_update_package",
        )
    else:
        st.error("The update package is missing from the downloads folder in this release hub.")

    st.markdown("### Safe update steps")
    st.markdown(
        """
1. Open your current local app.
2. Go to **Settings → Data safety and updates**.
3. Click **Create update backup**.
4. Close the local app.
5. Download the latest update from this page.
6. Extract the zip.
7. If you are publishing a friend-facing package, run **build_launcher_exe.bat** first.
8. Replace only the old **local_app** folder with the new one.
9. Start the app again.
10. Restore from backup only if something has gone wrong.
"""
    )

with demo_tab:
    st.subheader("What to expect")
    st.markdown(
        """
Clearway is local-first because its core benefit is working with real local files.

A cloud-only version can show the interface, but it cannot directly write to your Documents folder, OneDrive, Markdown files, or local backups. The local version is therefore the real product.
"""
    )
    st.markdown("### Main features")
    st.markdown(
        """
- Goals and projects with visible next actions.
- Routines with repeat patterns and timed activities.
- Printable tasklists.
- Google Calendar `.ics` exports.
- Google Tasks `.csv` exports and Apps Script setup guide.
- Markdown generation into a Clearway folder.
- Local backups and restore options.
- Seasonal and custom appearance themes.
"""
    )

st.divider()

st.header("Safety rules")

s1, s2 = st.columns(2)
with s1:
    st.markdown(
        """
<div class="product-card">
<h3>What the app may do</h3>
<ul>
<li>Create missing folders.</li>
<li>Create Markdown files.</li>
<li>Update Markdown after making a backup.</li>
<li>Write exports and backups into <code>00_System</code>.</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )
with s2:
    st.markdown(
        """
<div class="product-card">
<h3>What the app should not do</h3>
<ul>
<li>Delete your files.</li>
<li>Empty existing folders.</li>
<li>Replace your Clearway folder during updates.</li>
<li>Overwrite Markdown without creating a backup first.</li>
</ul>
</div>
""",
        unsafe_allow_html=True,
    )

st.divider()

st.header("Release notes")
notes = version.get("notes", [])
if notes:
    for note in notes:
        st.write(f"- {note}")
else:
    st.write("No release notes found.")

st.caption("Hosted release hub. Local files remain on the user's computer.")
