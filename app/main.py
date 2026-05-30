from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

try:
    from PIL import Image
except Exception:
    Image = None

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "downloads"
VERSION_FILE = ROOT / "latest_version.json"
ICON_PATH = ROOT / "app" / "assets" / "pathmark.png"


def page_icon():
    if Image is not None and ICON_PATH.exists():
        try:
            return Image.open(ICON_PATH)
        except Exception:
            pass
    return "PM"


st.set_page_config(page_title="Pathmark", page_icon=page_icon(), layout="wide")

CSS = """
<style>
:root {
  --bg: #F7F6F2;
  --ink: #1F2221;
  --muted: #626966;
  --surface: #FFFFFF;
  --surface-2: #EFEEE8;
  --line: #D8D4CB;
  --accent: #334E68;
  --accent-2: #7A4E7A;
  --accent-soft: #E7EEF4;
  --shadow: rgba(31,34,33,.10);
}
html, body, [data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 12% 0%, rgba(51,78,104,.16), transparent 26rem), radial-gradient(circle at 92% 8%, rgba(122,78,122,.14), transparent 24rem), linear-gradient(180deg, #FBFAF7 0%, var(--bg) 100%);
  color: var(--ink);
}
.block-container { max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem; }
h1, h2, h3 { letter-spacing: -0.035em; }
p, li { font-size: 1.02rem; line-height: 1.62; }
.hero { padding: 3.2rem 0 1.7rem 0; }
.eyebrow { display: inline-flex; padding: .42rem .72rem; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 760; font-size: .92rem; margin-bottom: 1.1rem; }
.hero h1 { font-size: clamp(3.7rem, 8.2vw, 7.2rem); line-height: .84; margin: 0 0 1rem 0; letter-spacing: -.085em; }
.lead { color: var(--ink); font-size: clamp(1.28rem, 2.4vw, 1.9rem); line-height: 1.22; max-width: 920px; font-weight: 680; margin: 0; }
.sublead { color: var(--muted); font-size: 1.12rem; max-width: 850px; margin-top: 1rem; }
.grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }
.card { background: rgba(255,255,255,.88); border: 1px solid var(--line); border-radius: 1.35rem; padding: 1.25rem; box-shadow: 0 14px 34px var(--shadow); }
.card h3 { margin-top: 0; margin-bottom: .55rem; }
.card p { margin-bottom: 0; color: var(--muted); }
.path-box { background: #151817; color: #EEE9E0; border-radius: 1.15rem; padding: 1.05rem 1.2rem; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; line-height: 1.65; overflow-x: auto; }
.meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: .9rem 0 2.1rem; }
.meta-card { background: rgba(255,255,255,.80); border: 1px solid var(--line); border-radius: 1.25rem; padding: 1rem 1.15rem; box-shadow: 0 10px 26px var(--shadow); }
.meta-label { color: var(--muted); font-size: .92rem; font-weight: 700; margin-bottom: .35rem; }
.meta-value { color: var(--ink); font-size: 1.9rem; line-height: 1.05; font-weight: 780; letter-spacing: -.045em; }
.download-panel { background: rgba(255,255,255,.70); border: 1px solid var(--line); border-radius: 1.25rem; padding: 1rem 1.1rem; margin-bottom: .75rem; }
.download-panel h3 { margin: 0 0 .45rem 0; }
.download-panel p { color: var(--muted); margin-bottom: 0; }
.safe-rule { background: var(--surface-2); border: 1px solid var(--line); border-radius: 1.1rem; padding: 1rem 1.1rem; }
.stDownloadButton button, .stButton button { border-radius: .85rem !important; min-height: 3rem; font-weight: 700 !important; }
[data-testid="stHeader"] { background: transparent; }
@media (max-width: 860px) { .grid-3, .grid-2, .meta-grid { grid-template-columns: 1fr; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def load_version() -> dict:
    if VERSION_FILE.exists():
        return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    return {"app_name": "Pathmark", "version": "unknown", "release_date": "unknown", "notes": []}


def find_windows_package(configured_name: str | None) -> Path | None:
    if configured_name:
        configured_path = DOWNLOADS / configured_name
        if configured_path.exists():
            return configured_path
    candidates = sorted(DOWNLOADS.glob("Pathmark_Local_App_Windows*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


version = load_version()
windows_package = find_windows_package(version.get("windows_package", ""))

if ICON_PATH.exists():
    st.image(str(ICON_PATH), width=54)

st.markdown("""
<div class="hero">
  <div class="eyebrow">Windows local app</div>
  <h1>Pathmark</h1>
  <p class="lead">Plan recurring work, organise projects into Areas, and export calendar blocks and task prompts from one local Workspace.</p>
  <p class="sublead">Pathmark is designed for goals that need repeated attention: routines, weekly resets, study plans, creative projects, admin cycles, and other work that benefits from a clear starting point.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="grid-3">
  <div class="card">
    <h3>Organise by Area</h3>
    <p>Create numbered Area folders such as <strong>01_Body_And_Stability</strong> or <strong>03_Making_And_Craft</strong>. Pathmark uses these folders to keep app records and project files aligned.</p>
  </div>
  <div class="card">
    <h3>Build routines and actions</h3>
    <p>Turn broad goals into routines, tasklists, next actions, and review prompts so the next step is easier to start.</p>
  </div>
  <div class="card">
    <h3>Export when ready</h3>
    <p>Prepare calendar blocks, Google Tasks exports, tasklists, backups, and local files inside the Workspace rather than scattering them through Downloads.</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.header("Download Pathmark")
st.markdown(f"""
<div class="meta-grid">
  <div class="meta-card">
    <div class="meta-label">Latest version</div>
    <div class="meta-value">{version.get('version', 'unknown')}</div>
  </div>
  <div class="meta-card">
    <div class="meta-label">Release date</div>
    <div class="meta-value">{version.get('release_date', 'unknown')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="download-panel">
  <h3>Windows local app</h3>
  <p>Download the package, extract it, move the extracted <strong>Pathmark</strong> app folder into <strong>Documents</strong>, then run <strong>build_launcher_exe.bat</strong> once. The launcher lets you review the Workspace and theme before opening the app.</p>
</div>
""", unsafe_allow_html=True)

if windows_package is not None:
    st.download_button(
        "Download Pathmark for Windows",
        data=windows_package.read_bytes(),
        file_name=windows_package.name,
        mime="application/zip",
        use_container_width=True,
        key="download_windows",
    )
else:
    st.error("The Windows package is missing from this release hub. Check that a file named Pathmark_Local_App_Windows_v*.zip exists in the downloads folder.")

st.caption("This release is Windows-only for now. Mac package support has been removed while the Windows workflow is stabilised.")

st.header("How the folders work")
st.markdown("""
<div class="grid-2">
  <div class="card">
    <h3>App folder</h3>
    <p><strong>Documents\\Pathmark</strong> contains the replaceable app files and launcher. This is the folder you replace when updating.</p>
  </div>
  <div class="card">
    <h3>Workspace folder</h3>
    <p><strong>Documents\\Workspace</strong> is the default place for your projects, numbered Areas, exports, tasklists, backups, and local database. You can choose another Workspace in the launcher.</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.header("Install")
st.markdown("""
1. Download the Windows package.
2. Extract the zip file.
3. Move the extracted `Pathmark` app folder into your Documents folder.
4. Open the `Pathmark` app folder and run `build_launcher_exe.bat` once to create `Pathmark.exe`.
5. Open `Pathmark.exe`, review the Workspace field, choose the default theme, then open Pathmark.

The default Workspace is `Documents\\Workspace`. Pathmark will create it if needed, or you can choose an existing folder before opening the app.
""")

st.header("Update")
st.markdown("""
<div class="safe-rule"><strong>Replace the app folder only.</strong><br>Open <strong>Pathmark.exe</strong> and choose <strong>Update</strong>. Then replace only <code>Documents\\Pathmark</code>. Do not replace <code>Documents\\Workspace</code> or whichever Workspace folder you selected.</div>
""", unsafe_allow_html=True)

st.header("Release notes")
for note in version.get("notes", []):
    st.write(f"- {note}")

st.caption("Pathmark release hub. User files stay on the user's computer.")
