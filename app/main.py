from __future__ import annotations

import csv
import io
import importlib.util
import json
import re
import uuid
import secrets
import hmac
import hashlib
import html
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    from PIL import Image
except Exception:
    Image = None

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "downloads"
VERSION_FILE = ROOT / "latest_version.json"
ICON_PATH = ROOT / "app" / "assets" / "pathmark.png"
SYNC_COLUMNS = [
    "sync_id", "status", "record_type", "action", "title", "area_name", "specific_area",
    "details", "calendar_start", "calendar_end", "recurrence", "created_at", "updated_at",
    "imported_at", "source",
]

ONLINE_TABLES = {
    "settings": ["key", "value", "updated_at", "source"],
    "areas": ["area_id", "area_name", "description", "colour", "status", "default_calendar", "default_task_list", "notes", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "goals": ["goal_id", "area_id", "area_name", "title", "description", "specific_area", "status", "target_date", "purpose", "desired_outcome", "closure_criteria", "notes", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "routines": ["routine_id", "area_id", "area_name", "title", "description", "frequency", "preferred_days", "duration_minutes", "status", "purpose", "next_due", "checklist", "calendar_block", "reminder", "starting_prompt", "task_reminder_time", "calendar_start_time", "calendar_end_time", "calendar_location", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "actions": ["action_id", "goal_id", "routine_id", "area_id", "area_name", "title", "description", "status", "priority", "specific_area", "due_date", "scheduled_date", "activity_days", "estimated_minutes", "calendar_block", "reminder", "include_tasklist", "first_step", "task_reminder_time", "calendar_start_time", "calendar_end_time", "calendar_location", "notes", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id", "archived_at", "archived_reason", "restored_at"],
    "calendar_blocks": ["block_id", "area_name", "title", "description", "start", "end", "recurrence", "linked_record_id", "status", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id"],
    "task_prompts": ["prompt_id", "area_name", "title", "prompt_text", "linked_record_id", "status", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id"],
    "tasklists": ["tasklist_id", "date", "title", "items", "status", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id"],
    "google_tasks_export": ["Task ID", "Task List", "Title", "Notes", "Due Date", "Reference Time", "Status", "Repeat Pattern", "Related Google Calendar Item", "exported_at"],
}

GOOGLE_CALENDAR_COLOURS = [
    ("1", "Lavender", "#7986CB"),
    ("2", "Sage", "#33B679"),
    ("3", "Grape", "#8E24AA"),
    ("4", "Flamingo", "#E67C73"),
    ("5", "Banana", "#F6BF26"),
    ("6", "Tangerine", "#F4511E"),
    ("7", "Peacock", "#039BE5"),
    ("8", "Graphite", "#616161"),
    ("9", "Blueberry", "#3F51B5"),
    ("10", "Basil", "#0B8043"),
    ("11", "Tomato", "#D50000"),
]
GOOGLE_COLOUR_LABELS = [name for _code, name, _hex in GOOGLE_CALENDAR_COLOURS]
GOOGLE_COLOUR_BY_LABEL = {name: {"code": code, "name": name, "hex": _hex} for code, name, _hex in GOOGLE_CALENDAR_COLOURS}
GOOGLE_COLOUR_BY_CODE_OR_NAME = {code.lower(): name for code, name, _hex in GOOGLE_CALENDAR_COLOURS}
GOOGLE_COLOUR_BY_CODE_OR_NAME.update({name.lower(): name for code, name, _hex in GOOGLE_CALENDAR_COLOURS})

ONLINE_THEME_OPTIONS = ["Summer", "Autumn", "Winter", "Spring"]
ONLINE_THEMES = {
    # Seasonal choice controls Pathmark's accent, tint and icon. Light/dark mode
    # is deliberately left to Streamlit's own Settings menu: System, Light or Dark.
    "Summer": {"accent": "#2F5D7C", "soft_light": "#FFF3C4", "soft_dark": "#403A1E", "seasonal_icon": "☀️ 🏖️"},
    "Autumn": {"accent": "#8A5A34", "soft_light": "#F6E7D8", "soft_dark": "#3A2418", "seasonal_icon": "🍂"},
    "Winter": {"accent": "#334E68", "soft_light": "#E7EEF4", "soft_dark": "#1D3142", "seasonal_icon": "❄️ ⛄"},
    "Spring": {"accent": "#7A4E7A", "soft_light": "#F8EAF3", "soft_dark": "#3A2132", "seasonal_icon": "🌸"},
    # Compatibility aliases for existing saved preferences. These are normalised
    # before display, so users no longer choose separate light/dark theme names.
    "Default": {"alias_for": "Winter"},
    "Sage": {"alias_for": "Spring"},
    "Blue": {"alias_for": "Winter"},
    "Plum": {"alias_for": "Spring"},
    "Warm": {"alias_for": "Autumn"},
    "Dark": {"alias_for": "Winter"},
    "Summer dark": {"alias_for": "Summer"},
    "Autumn dark": {"alias_for": "Autumn"},
    "Winter dark": {"alias_for": "Winter"},
    "Spring dark": {"alias_for": "Spring"},
}


def normalise_online_theme(theme_name: str | None) -> str:
    """Return a seasonal Pathmark theme name.

    The seasonal theme is separate from Streamlit's built-in appearance mode.
    Streamlit controls System/Light/Dark; Pathmark controls Summer/Autumn/Winter/Spring.
    """
    name = str(theme_name or "").strip()
    if name in ONLINE_THEME_OPTIONS:
        return name
    info = ONLINE_THEMES.get(name, {})
    alias = str(info.get("alias_for", "") or "") if isinstance(info, dict) else ""
    return alias if alias in ONLINE_THEME_OPTIONS else "Winter"

VALID_FREQUENCIES = ["Daily", "Weekdays", "Weekly", "Monthly", "Custom"]
VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SETUP_STEPS = [
    ("focus", "Weekly Focus", "Choose the main thing this week needs from you before adding more structure."),
    ("review", "Review Queue", "See how Pathmark checks whether the parts of your system are ready to use."),
    ("areas", "Areas", "Create broad life systems so routines, goals and calendar groups have somewhere to belong."),
    ("routines", "Routines", "Add repeating habits and at least one activity so wellbeing and capacity are protected."),
    ("goals", "Goals and Projects", "Define what done looks like, then keep only the next one or two useful actions visible."),
    ("actions", "Goal activities", "Turn goals into concrete one-off activities and first-step prompts that reduce friction."),
    ("tasklist", "Tasklist", "Choose the saved actions and routine activities you want on a printable paper list."),
    ("calendar", "Google Calendar Export", "Preview how selected actions become calendar blocks."),
    ("tasks", "Google Tasks Export", "Preview first-step prompts for Google Tasks or the Google Tasks export tab."),
    ("archive", "Archive", "Move exported or finished work out of the active space, and restore it if you change your mind."),
]
SETUP_STEP_KEYS = [step[0] for step in SETUP_STEPS]
DAY_ALIASES = {d.lower(): d for d in VALID_DAYS}
DAY_ALIASES.update({d[:3].lower(): d for d in VALID_DAYS})

GOOGLE_SHEETS_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
LOGIN_SCOPES = ["openid", "email", "profile"] + GOOGLE_SHEETS_SCOPES
SYNC_SHEET_TITLE = "Pathmark Sync"



def page_icon():
    if Image is not None and ICON_PATH.exists():
        try:
            return Image.open(ICON_PATH)
        except Exception:
            pass
    return "PM"


st.set_page_config(page_title="Pathmark", page_icon=page_icon(), layout="wide")


def inject_pwa_metadata() -> None:
    """Add Pathmark install metadata for mobile/desktop browser shortcuts.

    Streamlit controls the base document head, so this small script updates the
    parent document at runtime. Static files are served from app/static via
    Streamlit's static file serving.
    """
    components.html(
        """
        <script>
        (function () {
          const doc = window.parent.document;
          function setMeta(name, content) {
            let el = doc.querySelector('meta[name="' + name + '"]');
            if (!el) {
              el = doc.createElement('meta');
              el.setAttribute('name', name);
              doc.head.appendChild(el);
            }
            el.setAttribute('content', content);
          }
          function setLink(rel, href, extraAttrs) {
            let el = doc.querySelector('link[rel="' + rel + '"]');
            if (!el) {
              el = doc.createElement('link');
              el.setAttribute('rel', rel);
              doc.head.appendChild(el);
            }
            el.setAttribute('href', href);
            if (extraAttrs) {
              Object.keys(extraAttrs).forEach(function (key) {
                el.setAttribute(key, extraAttrs[key]);
              });
            }
          }
          doc.title = 'Pathmark';
          setMeta('application-name', 'Pathmark');
          setMeta('apple-mobile-web-app-title', 'Pathmark');
          setMeta('apple-mobile-web-app-capable', 'yes');
          setMeta('mobile-web-app-capable', 'yes');
          setMeta('theme-color', '#334E68');
          setLink('manifest', '/app/static/manifest.json');
          setLink('icon', '/app/static/pathmark-icon-192.png', {'type': 'image/png', 'sizes': '192x192'});
          setLink('apple-touch-icon', '/app/static/apple-touch-icon.png', {'sizes': '180x180'});
        })();
        </script>
        """,
        height=0,
    )


inject_pwa_metadata()

def streamlit_appearance_mode() -> str:
    """Return Streamlit's active appearance mode when available.

    Streamlit's Settings menu controls Light/Dark/System. In recent Streamlit
    versions, st.context.theme.type exposes the resolved active theme as
    "light" or "dark". Older versions simply fall back to light. The CSS
    still avoids forcing a light page so Streamlit can take over natively.
    """
    try:
        theme = getattr(st.context, "theme", None)
        value = ""
        if theme is not None:
            if hasattr(theme, "type"):
                value = str(theme.type or "").lower()
            elif isinstance(theme, dict):
                value = str(theme.get("type", "") or "").lower()
        return "dark" if value == "dark" else "light"
    except Exception:
        return "light"


def pathmark_theme_tokens_css(mode: str = "") -> str:
    """Return CSS variables for the resolved Streamlit appearance.

    The important design rule is that Pathmark no longer paints the app shell
    white. Streamlit owns the base page background; Pathmark only supplies
    readable fallback tokens for custom cards and seasonal accents.
    """
    mode = (mode or streamlit_appearance_mode()).lower()
    if mode == "dark":
        return """
          --bg: #05080C;
          --ink: #F8FAFC;
          --muted: #CBD5E1;
          --surface: #111827;
          --surface-2: #0B1220;
          --line: #334155;
          --shadow: rgba(0,0,0,.45);
          --accent-soft: color-mix(in srgb, var(--accent) 24%, var(--surface));
        """
    return """
          --bg: #F7F6F2;
          --ink: #1F2221;
          --muted: #5B6268;
          --surface: #FFFFFF;
          --surface-2: #F2F1EC;
          --line: #D8D4CB;
          --shadow: rgba(0,0,0,.13);
          --accent-soft: color-mix(in srgb, var(--accent) 13%, var(--surface));
        """


CSS = f"""
<style>
/*
Pathmark owns seasonal accent and custom card styling. Streamlit owns the
actual appearance mode. This block deliberately does not force the app shell to
light; the Streamlit Settings menu can therefore turn the whole page dark.
*/
:root {{
  color-scheme: light dark;
  --accent: #334E68;
  --accent-2: #7A4E7A;
  --button-ink: #FFFFFF;
{pathmark_theme_tokens_css()}
}}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stApp"], main {{
  color: var(--ink) !important;
}}
/* Let Streamlit control the page background. Only remove any old forced-white
   Pathmark wash that may remain from a cached style block. */
.stApp, [data-testid="stAppViewContainer"] {{
  background-color: var(--bg) !important;
}}
.block-container {{ max-width: 1180px; padding-top: 2.2rem; padding-bottom: 4rem; }}
h1, h2, h3 {{ letter-spacing: -0.035em; color: var(--ink) !important; }}
p, li {{ font-size: 1.02rem; line-height: 1.62; }}
.hero {{ padding: 2.6rem 0 1.2rem 0; }}
.eyebrow {{ display: inline-flex; padding: .42rem .72rem; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 760; font-size: .92rem; margin-bottom: 1.1rem; }}
.hero h1 {{ font-size: clamp(3.7rem, 8.2vw, 7.2rem); line-height: .84; margin: 0 0 1rem 0; letter-spacing: -.085em; }}
.lead {{ color: var(--ink); font-size: clamp(1.28rem, 2.4vw, 1.9rem); line-height: 1.22; max-width: 920px; font-weight: 680; margin: 0; }}
.sublead {{ color: var(--muted); font-size: 1.12rem; max-width: 850px; margin-top: 1rem; }}
.grid-3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }}
.grid-2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }}
.card, .meta-card, .download-panel, .account-card, .connection-card, .setup-shell, .guide-box, .step-card, .process-card, .pathmark-card, .workspace-card, .issue-card {{
  background: var(--surface) !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important;
  box-shadow: 0 14px 34px var(--shadow);
}}
.card {{ border-radius: 1.35rem; padding: 1.25rem; }}
.card h3 {{ margin-top: 0; margin-bottom: .55rem; }}
.card p {{ margin-bottom: 0; color: var(--muted); }}
.meta-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: .9rem 0 2.1rem; }}
.meta-card {{ border-radius: 1.25rem; padding: 1rem 1.15rem; }}
.meta-label {{ color: var(--muted); font-size: .92rem; font-weight: 700; margin-bottom: .35rem; }}
.meta-value {{ color: var(--ink); font-size: 1.9rem; line-height: 1.05; font-weight: 780; }}
.download-panel {{ border-radius: 1.35rem; padding: 1.2rem; margin: 1.2rem 0 2rem; }}
.account-card, .connection-card {{ border-radius: 1.2rem; padding: 1rem 1.15rem; }}
.safe-rule {{ background: var(--surface-2); border: 1px solid var(--line); border-radius: 1.1rem; padding: 1rem 1.1rem; }}
.profile-pill {{ display: inline-flex; gap: .45rem; align-items: center; padding: .46rem .72rem; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--line); color: var(--muted); font-weight: 700; }}
.kicker {{ color: var(--accent); font-size: .82rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; margin-bottom: .4rem; }}
.small-muted {{ color: var(--muted); font-size: .94rem; }}
.hr {{ height: 1px; background: var(--line); margin: 1.6rem 0; }}
.step-card {{ border-radius: 1.2rem; padding: 1rem 1.05rem; margin-bottom: .8rem; }}
.step-card strong {{ color: var(--ink); }}
.beta-note {{ background: color-mix(in srgb, #F6BF26 18%, var(--surface)); border: 1px solid color-mix(in srgb, #F6BF26 48%, var(--line)); border-radius: 1.1rem; padding: 1rem 1.1rem; color: var(--ink); }}
[data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] li,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] span,
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *, label, label *, .stMarkdown, .stMarkdown * {{
  color: var(--ink) !important;
}}
[data-testid="stTabs"] button, [data-testid="stTabs"] button *, button[data-baseweb="tab"], button[data-baseweb="tab"] * {{
  color: var(--ink) !important;
  opacity: 1 !important;
}}
[data-testid="stTabs"] button[aria-selected="true"], [data-testid="stTabs"] button[aria-selected="true"] *,
button[data-baseweb="tab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] * {{ color: var(--accent) !important; font-weight: 760 !important; }}
input, textarea, [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stDateInput"] input, [data-testid="stTimeInput"] input, [data-baseweb="popover"] div {{
  background: var(--surface) !important;
  color: var(--ink) !important;
  border-color: var(--line) !important;
}}
[role="listbox"], [role="option"] {{ background: var(--surface) !important; color: var(--ink) !important; }}
.setup-shell {{ border-radius: 1.25rem; padding: 1.1rem 1.15rem; margin: 1rem 0 1.2rem 0; }}
.setup-example {{ border-left: 4px solid var(--accent); background: var(--accent-soft); padding: 0.85rem 1rem; border-radius: 12px; margin: 0.75rem 0 1rem 0; color: var(--ink) !important; }}
.setup-step-label {{ display:inline-flex; gap:.35rem; align-items:center; padding:.28rem .62rem; border-radius:999px; background:var(--accent-soft); color:var(--ink); font-weight:760; font-size:.9rem; }}
.setup-progress-wrap {{ width: 100%; max-width: 760px; height: 12px; border-radius: 999px; background: color-mix(in srgb, var(--muted) 20%, transparent); overflow: hidden; margin: 0.75rem 0 1rem 0; border: 1px solid var(--line); }}
.setup-progress-fill {{ height: 100%; background: var(--accent); border-radius: 999px; }}
.stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a, a[data-testid="baseLinkButton-secondary"], a[data-testid="baseLinkButton-primary"], .pathmark-link-button {{
  border-radius: .7rem !important;
  border: 1px solid color-mix(in srgb, var(--accent) 72%, #000) !important;
  background: var(--accent) !important;
  color: var(--button-ink) !important;
  font-weight: 650 !important;
  box-shadow: none !important;
}}
.stButton button *, .stButton button p, .stButton button span, .stDownloadButton button *, .stDownloadButton button p, .stDownloadButton button span,
[data-testid="stLinkButton"] a *, a[data-testid="baseLinkButton-secondary"] *, a[data-testid="baseLinkButton-primary"] *, .pathmark-link-button * {{ color: var(--button-ink) !important; }}
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stLinkButton"] a:hover, .pathmark-link-button:hover {{ filter: brightness(.96); color: var(--button-ink) !important; text-decoration: none !important; }}
.stButton button:disabled, .stDownloadButton button:disabled {{
  background: color-mix(in srgb, var(--surface) 82%, var(--muted)) !important;
  color: var(--muted) !important;
  border-color: var(--line) !important;
}}
.stButton button:disabled *, .stDownloadButton button:disabled * {{ color: var(--muted) !important; }}
.pathmark-link-button {{ display: inline-flex; align-items: center; justify-content: center; width: 100%; padding: .55rem .85rem; }}
@media (max-width: 640px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; padding-top: 1rem; }}
  .hero h1 {{ font-size: clamp(3rem, 17vw, 5.2rem); }}
  .lead {{ font-size: 1.15rem; }}
  .stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a {{ min-height: 3.2rem; font-size: 1rem !important; }}
}}
.pathmark-note, .pathmark-hint {{ background: var(--accent-soft); border: 1px solid var(--line); border-radius: 1rem; padding: .9rem 1rem; margin: .65rem 0 1rem; color: var(--ink); }}
.swatch-row {{ display:flex; flex-wrap:wrap; gap:.45rem; margin:.4rem 0 .7rem; }}
.swatch {{ display:inline-flex; align-items:center; gap:.35rem; border:1px solid var(--line); border-radius:999px; background:var(--surface); padding:.25rem .55rem; font-size:.85rem; }}
.swatch-dot {{ width:.9rem; height:.9rem; border-radius:999px; display:inline-block; border:1px solid rgba(0,0,0,.22); }}
.area-colour-preview {{ display:flex; align-items:center; gap:.6rem; border:1px solid var(--line); border-left:8px solid var(--accent); border-radius:1rem; background:var(--surface); padding:.8rem 1rem; margin:.35rem 0 1rem; color:var(--ink) !important; }}
.area-colour-dot {{ width:1.15rem; height:1.15rem; border-radius:999px; border:1px solid rgba(0,0,0,.22); display:inline-block; flex:0 0 auto; }}
.setup-nav-row {{ margin-top:1.25rem; }}
.setup-skip {{ margin-top:.65rem; opacity:.96; }}
.setup-working-card {{ padding: 0 .1rem; }}
.setup-side-arrow {{ min-height: 10rem; }}

[data-testid="stIFrame"] {{ min-height:0 !important; }}
.process-card {{ border-radius:1rem; padding:1rem; margin:.55rem 0; }}
.process-card h4 {{ margin:.05rem 0 .35rem 0; color:var(--ink); }}
.process-card p {{ margin:0; color:var(--muted); }}
[data-testid="stHeader"] {{ background: transparent !important; }}
section[data-testid="stSidebar"] {{ background: var(--surface) !important; color: var(--ink) !important; }}
@media (max-width: 860px) {{ .grid-3, .grid-2, .meta-grid {{ grid-template-columns: 1fr; }} }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

ROLE_VALUES = ["standard", "beta_tester", "developer"]
STATUS_VALUES = ["active", "disabled"]
ROLE_COLUMNS = ["email", "role", "status", "last_login", "updated_at"]


def _secret_section(name: str):
    try:
        return st.secrets.get(name, {})
    except Exception:
        return {}


def login_config() -> dict[str, str] | None:
    """Return Google login settings for Pathmark's own OIDC flow.

    This deliberately avoids Streamlit's built-in st.login route so the hosted
    page does not depend on the streamlit[auth]/Authlib extra being installed.
    Users still sign in with Google; Pathmark never receives a password.
    """
    auth = _secret_section("auth")
    if not auth:
        return None
    client_id = str(auth.get("client_id", "")).strip()
    client_secret = str(auth.get("client_secret", "")).strip()
    # Prefer an explicit app callback URL. If only the old Streamlit callback is
    # configured, fall back to the app root so this custom flow can complete in
    # Streamlit's normal page code.
    redirect_uri = str(auth.get("login_redirect_uri", "")).strip()
    if not redirect_uri:
        google_cfg = _secret_section("google_oauth")
        redirect_uri = str(google_cfg.get("redirect_uri", "")).strip() if google_cfg else ""
    if not redirect_uri:
        old_uri = str(auth.get("redirect_uri", "")).strip()
        redirect_uri = old_uri[:-len("/oauth2callback")] if old_uri.endswith("/oauth2callback") else old_uri
    if not (client_id and client_secret and redirect_uri):
        return None
    return {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri}


def login_configured() -> bool:
    return login_config() is not None

def _user_claim(user: Any, key: str, default: Any = "") -> Any:
    """Read a claim from Streamlit's OIDC user object defensively."""
    try:
        value = getattr(user, key)
        if value is not None:
            return value
    except Exception:
        pass
    try:
        return user.get(key, default)
    except Exception:
        return default


def current_user() -> dict[str, Any]:
    """Return the Google identity stored in this Streamlit session."""
    user = st.session_state.get("pathmark_user")
    if not isinstance(user, dict):
        return {"email": "", "name": "", "email_verified": False}
    email = str(user.get("email", "") or "").strip().lower()
    if not email:
        return {"email": "", "name": "", "email_verified": False}
    return {
        "email": email,
        "name": str(user.get("name", "") or "").strip(),
        "email_verified": bool(user.get("email_verified", False)),
    }


def oauth_state_secret() -> str:
    """Return a stable secret for signing OAuth state values.

    The hosted page cannot rely on Streamlit session_state surviving a full
    external Google redirect in every deployment. Signed state values let
    Pathmark verify that the callback originated from this app without storing
    the state only in the in-memory session.
    """
    auth = _secret_section("auth")
    secret = str(auth.get("cookie_secret", "") or auth.get("client_secret", "")).strip() if auth else ""
    if not secret:
        google_cfg = _secret_section("google_oauth")
        secret = str(google_cfg.get("client_secret", "")).strip() if google_cfg else ""
    return secret or "pathmark-development-only-state-secret"


def make_signed_oauth_state(kind: str, context: str = "") -> str:
    """Create a short-lived signed OAuth state value.

    The optional context is URL-safe encoded into the signed payload. This lets
    Pathmark recover enough non-secret routing context after a round trip to
    Google, even when Streamlit starts a fresh session.
    """
    ts = str(int(datetime.now(timezone.utc).timestamp()))
    nonce = secrets.token_urlsafe(24)
    context_part = urllib.parse.quote(context or "", safe="")
    payload = f"{kind}:{ts}:{nonce}:{context_part}"
    sig = hmac.new(oauth_state_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def parse_signed_oauth_state(state: str | None, kind: str, max_age_seconds: int = 900) -> dict[str, str] | None:
    if not state:
        return None
    parts = str(state).split(":")
    if len(parts) == 4:
        state_kind, ts, nonce, sig = parts
        context_part = ""
        payload = ":".join(parts[:3])
    elif len(parts) == 5:
        state_kind, ts, nonce, context_part, sig = parts
        payload = ":".join(parts[:4])
    else:
        return None
    if state_kind != kind:
        return None
    expected = hmac.new(oauth_state_secret().encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not secrets.compare_digest(expected, sig):
        return None
    try:
        age = int(datetime.now(timezone.utc).timestamp()) - int(ts)
    except Exception:
        return None
    if not (0 <= age <= max_age_seconds):
        return None
    return {"kind": state_kind, "timestamp": ts, "nonce": nonce, "context": urllib.parse.unquote(context_part or "")}


def verify_signed_oauth_state(state: str | None, kind: str, max_age_seconds: int = 900) -> bool:
    return parse_signed_oauth_state(state, kind, max_age_seconds=max_age_seconds) is not None


def signed_state_context(state: str | None, kind: str, max_age_seconds: int = 900) -> str:
    parsed = parse_signed_oauth_state(state, kind, max_age_seconds=max_age_seconds)
    return parsed.get("context", "") if parsed else ""


def same_tab_link_button(label: str, url: str, help_text: str | None = None) -> None:
    """Render a full-width link styled like a Streamlit button that stays in this tab."""
    safe_label = html.escape(label)
    safe_url = html.escape(url, quote=True)
    title = f' title="{html.escape(help_text, quote=True)}"' if help_text else ""
    st.markdown(f'<a class="pathmark-link-button" href="{safe_url}" target="_self" rel="noopener noreferrer"{title}>{safe_label}</a>', unsafe_allow_html=True)


def same_tab_oauth_button(label: str, url: str) -> None:
    """Render a reliable Google OAuth launch control.

    v0.5.87 attempted a custom same-tab HTML/JS button to reduce extra tabs,
    but that could be blocked by Streamlit component iframe behaviour in the
    deployed app. Streamlit's native link_button is less elegant because it may
    open a new tab, but it is the most reliable option for Google OAuth.
    """
    st.link_button(label, url, use_container_width=True)

def login_auth_url() -> str | None:
    cfg = login_config()
    if not cfg:
        return None
    state = make_signed_oauth_state("login")
    # Also store it in session when possible. The signed value is the fallback
    # used after the browser returns from Google.
    st.session_state["pathmark_login_state"] = state
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(LOGIN_SCOPES),
        "state": state,
        "access_type": "online",
        "include_granted_scopes": "true",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def store_google_credentials_from_token_info(token_info: dict[str, Any], client_id: str) -> None:
    """Store short-lived Google API credentials from the unified login flow.

    The hosted app now requests Google identity and the narrow drive.file scope in
    one consent flow. This keeps the web companion login simple while avoiding a
    separate Google Sheets connection step. No refresh token is requested or
    stored on the hosted app.
    """
    access_token = str(token_info.get("access_token", "") or "").strip()
    if not access_token:
        return
    scope_text = str(token_info.get("scope", "") or "").strip()
    scopes = scope_text.split() if scope_text else LOGIN_SCOPES
    if GOOGLE_SHEETS_SCOPES[0] not in scopes:
        # The identity login can still succeed, but Sheets-backed features need
        # the user to sign in again after Google Cloud consent is corrected.
        return
    expires_at = None
    if token_info.get("expires_in"):
        try:
            expires_at = int(datetime.now(timezone.utc).timestamp()) + int(token_info["expires_in"])
        except Exception:
            expires_at = None
    cred_info: dict[str, Any] = {
        "token": access_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "scopes": scopes,
        "source": "unified_login",
    }
    if expires_at:
        cred_info["expires_at"] = expires_at
        cred_info["expiry"] = datetime.fromtimestamp(expires_at, timezone.utc).isoformat().replace("+00:00", "Z")
    st.session_state["google_sheets_credentials"] = json.dumps(cred_info)
    st.session_state["auto_create_sync_sheet_after_connect"] = True
    st.session_state["sync_sheet_ready_attempted"] = False
    st.session_state["on_the_go_connected_notice"] = ""


def handle_login_redirect() -> bool:
    """Complete Pathmark login when returning from Google.

    Returns True if this callback belonged to the login flow. Google Sheets OAuth
    uses a different state value and is handled separately.
    """
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")
    if isinstance(code, list):
        code = code[0] if code else None
    if isinstance(state, list):
        state = state[0] if state else None
    if isinstance(error, list):
        error = error[0] if error else None
    expected_state = st.session_state.get("pathmark_login_state")
    if not (state and str(state).startswith("login:")):
        return False
    if error:
        st.session_state.pop("pathmark_login_state", None)
        st.query_params.clear()
        st.warning(f"Google login was not completed: {error}")
        return True
    if not code:
        return False
    session_match = bool(expected_state and secrets.compare_digest(str(expected_state), str(state)))
    signed_match = verify_signed_oauth_state(str(state), "login")
    if not (session_match or signed_match):
        st.session_state.pop("pathmark_login_state", None)
        st.query_params.clear()
        st.error("Google login could not be verified. Please try again.")
        return True
    cfg = login_config()
    if not cfg:
        st.session_state.pop("pathmark_login_state", None)
        st.query_params.clear()
        st.error("Google login is not configured yet.")
        return True
    try:
        data = urllib.parse.urlencode({
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": cfg["redirect_uri"],
            "grant_type": "authorization_code",
        }).encode("utf-8")
        request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            token_info = json.loads(response.read().decode("utf-8"))
        store_google_credentials_from_token_info(token_info, cfg["client_id"])
        raw_id_token = token_info.get("id_token")
        if not raw_id_token:
            raise ValueError("Google did not return an ID token.")
        from google.auth.transport import requests as google_requests  # type: ignore
        from google.oauth2 import id_token as google_id_token  # type: ignore
        claims = google_id_token.verify_oauth2_token(raw_id_token, google_requests.Request(), cfg["client_id"])
        email = str(claims.get("email", "") or "").strip().lower()
        if not email:
            raise ValueError("Google login did not return an email address.")
        email_verified = bool(claims.get("email_verified", False))
        st.session_state["pathmark_user"] = {
            "email": email,
            "name": str(claims.get("name", "") or ""),
            "email_verified": email_verified,
        }
        st.session_state.pop("pathmark_login_state", None)
        st.query_params.clear()
        st.success("Signed in with Google.")
        st.rerun()
        return True
    except Exception as exc:
        st.session_state.pop("pathmark_login_state", None)
        st.query_params.clear()
        st.error(f"Could not complete Google login: {exc}")
        return True

def _list_from_secret(section: dict[str, Any], key: str) -> set[str]:
    raw = section.get(key, []) if section else []
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, list):
        values = [str(item).strip() for item in raw]
    else:
        values = []
    return {item.lower() for item in values if item}


def configured_developer_emails() -> set[str]:
    access = _secret_section("pathmark_access")
    return _list_from_secret(access, "developer_emails")


def configured_beta_emails() -> set[str]:
    access = _secret_section("pathmark_access")
    return _list_from_secret(access, "beta_tester_emails")


def configured_disabled_emails() -> set[str]:
    access = _secret_section("pathmark_access")
    return _list_from_secret(access, "disabled_emails")


def supabase_config() -> dict[str, str] | None:
    """Return optional Supabase access-layer settings.

    Supabase is used only for hosted Pathmark access control: users, roles,
    status, feature flags, and audit logs. It is not used for Pathmark planning
    data, goals, routines, task prompts, Workspace files, or on-the-go entries.

    Prefer Supabase's newer `sb_secret_...` Secret API keys for server-side
    hosted role management. The older JWT-based service_role key is still
    accepted as a migration fallback, but should not be used for new setups.
    """
    cfg = _secret_section("supabase") or _secret_section("pathmark_supabase")
    if not cfg:
        return None
    url = str(cfg.get("url", "") or cfg.get("project_url", "")).strip().rstrip("/")
    key = str(
        cfg.get("secret_key", "")
        or cfg.get("secret_api_key", "")
        or cfg.get("key", "")
        or cfg.get("service_role_key", "")
        or cfg.get("service_key", "")
    ).strip()
    if not (url and key):
        return None
    key_kind = "secret" if key.startswith("sb_secret_") else "legacy_service_role"
    return {"url": url, "key": key, "key_kind": key_kind}


def supabase_available() -> bool:
    return supabase_config() is not None


def supabase_request(method: str, table: str, query: str = "", body: Any | None = None, prefer: str = "return=representation") -> tuple[bool, Any]:
    cfg = supabase_config()
    if not cfg:
        return False, "Supabase is not configured."
    url = f"{cfg['url']}/rest/v1/{table}{query}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "apikey": cfg["key"],
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Prefer": prefer,
    }
    # Supabase Secret API keys (`sb_secret_...`) are not JWTs. They should be
    # sent as the `apikey` header and kept server-side only. Legacy service_role
    # keys are JWT-based and continue to use the Authorization bearer header.
    if cfg.get("key_kind") == "legacy_service_role":
        headers["Authorization"] = f"Bearer {cfg['key']}"
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
        if not raw:
            return True, None
        return True, json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"Supabase HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, str(exc)


def normalise_role(role: str) -> str:
    role = (role or "standard").strip()
    return role if role in ROLE_VALUES else "standard"


def normalise_status(status: str) -> str:
    status = (status or "active").strip()
    return status if status in STATUS_VALUES else "active"


def read_supabase_user(email: str) -> dict[str, str] | None:
    email = (email or "").strip().lower()
    if not email or not supabase_available():
        return None
    # v0.5.90 adds theme_preference. During rolling deploys the database may not
    # have the column for a moment, so fall back to the older select if needed.
    query = "?" + urllib.parse.urlencode({"email": f"eq.{email}", "select": "email,role,status,created_at,updated_at,last_login,notes,theme_preference"})
    ok, payload = supabase_request("GET", "pathmark_users", query=query)
    if not ok:
        query = "?" + urllib.parse.urlencode({"email": f"eq.{email}", "select": "email,role,status,created_at,updated_at,last_login,notes"})
        ok, payload = supabase_request("GET", "pathmark_users", query=query)
    if not ok or not isinstance(payload, list) or not payload:
        return None
    rec = payload[0]
    theme = str(rec.get("theme_preference", "") or "Default")
    theme = normalise_online_theme(theme)
    return {
        "email": str(rec.get("email", "")).strip().lower(),
        "role": normalise_role(str(rec.get("role", "standard"))),
        "status": normalise_status(str(rec.get("status", "active"))),
        "created_at": str(rec.get("created_at", "") or ""),
        "updated_at": str(rec.get("updated_at", "") or ""),
        "last_login": str(rec.get("last_login", "") or ""),
        "notes": str(rec.get("notes", "") or ""),
        "theme_preference": theme,
    }


def list_supabase_users() -> list[dict[str, str]]:
    if not supabase_available():
        return []
    query = "?select=email,role,status,created_at,updated_at,last_login,notes,theme_preference&order=email.asc"
    ok, payload = supabase_request("GET", "pathmark_users", query=query)
    if not ok:
        query = "?select=email,role,status,created_at,updated_at,last_login,notes&order=email.asc"
        ok, payload = supabase_request("GET", "pathmark_users", query=query)
    if not ok or not isinstance(payload, list):
        if not ok:
            st.warning(f"Could not read Supabase access table: {payload}")
        return []
    out: list[dict[str, str]] = []
    for rec in payload:
        email = str(rec.get("email", "")).strip().lower()
        if not email:
            continue
        theme = str(rec.get("theme_preference", "") or "Default")
        theme = normalise_online_theme(theme)
        out.append({
            "email": email,
            "role": normalise_role(str(rec.get("role", "standard"))),
            "status": normalise_status(str(rec.get("status", "active"))),
            "created_at": str(rec.get("created_at", "") or ""),
            "updated_at": str(rec.get("updated_at", "") or ""),
            "last_login": str(rec.get("last_login", "") or ""),
            "notes": str(rec.get("notes", "") or ""),
            "theme_preference": theme,
        })
    return out


def write_audit_log(actor_email: str, action: str, target_email: str = "", details: dict[str, Any] | None = None) -> None:
    if not supabase_available():
        return
    row = {
        "actor_email": (actor_email or "").strip().lower(),
        "action": action,
        "target_email": (target_email or "").strip().lower(),
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    supabase_request("POST", "pathmark_audit_log", body=[row], prefer="return=minimal")


def upsert_supabase_user(email: str, role: str, status: str = "active", notes: str = "", actor_email: str = "", update_login: bool = False) -> tuple[bool, str]:
    email = (email or "").strip().lower()
    role = normalise_role(role)
    status = normalise_status(status)
    if not email or "@" not in email:
        return False, "Enter a valid email address."
    if email in configured_developer_emails() and role != "developer":
        return False, "A developer account listed in Streamlit secrets cannot be downgraded from the hosted UI."
    if not supabase_available():
        return False, "Supabase access management is not configured yet."
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    existing = read_supabase_user(email) or {}
    row = {
        "email": email,
        "role": role,
        "status": status,
        "updated_at": now,
        "notes": notes,
    }
    if not existing:
        row["created_at"] = now
    if update_login:
        row["last_login"] = now
    query = "?on_conflict=email"
    ok, payload = supabase_request("POST", "pathmark_users", query=query, body=[row], prefer="resolution=merge-duplicates,return=representation")
    if not ok:
        return False, f"Could not save access record: {payload}"
    write_audit_log(actor_email, "upsert_user", email, {"role": role, "status": status, "update_login": update_login})
    return True, "User access saved."


def update_supabase_user_theme(email: str, theme_name: str, actor_email: str = "") -> tuple[bool, str]:
    """Persist the hosted seasonal theme with the user's Supabase access profile."""
    email = (email or "").strip().lower()
    theme_name = normalise_online_theme(theme_name)
    if not email:
        return False, "No signed-in user."
    if not supabase_available():
        return False, "Supabase access management is not configured yet."
    row = {"theme_preference": theme_name, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    query = "?" + urllib.parse.urlencode({"email": f"eq.{email}"})
    ok, payload = supabase_request("PATCH", "pathmark_users", query=query, body=row, prefer="return=minimal")
    if not ok:
        return False, "Could not save the theme to your Pathmark profile. The app will still use the theme in this session."
    write_audit_log(actor_email or email, "update_theme", email, {"theme": theme_name})
    return True, "Seasonal theme saved to your Pathmark profile."


def theme_for_user(email: str) -> str:
    """Return the user's hosted seasonal theme preference from session/Supabase."""
    cached = st.session_state.get("hosted_theme_preference")
    if cached:
        return normalise_online_theme(cached)
    rec = read_supabase_user(email) if email else None
    theme = rec.get("theme_preference", "Winter") if rec else "Winter"
    theme = normalise_online_theme(theme)
    st.session_state["hosted_theme_preference"] = theme
    return theme


def read_feature_flags() -> list[dict[str, Any]]:
    if not supabase_available():
        return []
    query = "?select=key,enabled,minimum_role,updated_at,notes&order=key.asc"
    ok, payload = supabase_request("GET", "pathmark_feature_flags", query=query)
    if not ok or not isinstance(payload, list):
        return []
    return payload


def role_rank(role: str) -> int:
    return {"public": 0, "standard": 1, "beta_tester": 2, "developer": 3}.get(role, 0)


def feature_enabled(key: str, role: str, default_enabled: bool = True, default_minimum_role: str = "standard") -> bool:
    """Return whether a feature is enabled for the current role.

    If Supabase or the flag row is not configured, the code uses safe defaults
    defined in the caller. This lets the app remain usable while the access
    layer is being set up.
    """
    flags = read_feature_flags()
    for flag in flags:
        if str(flag.get("key", "")) == key:
            enabled = bool(flag.get("enabled", True))
            minimum_role = normalise_role(str(flag.get("minimum_role", default_minimum_role)))
            return enabled and role_rank(role) >= role_rank(minimum_role)
    return default_enabled and role_rank(role) >= role_rank(default_minimum_role)


def resolve_role(email: str, email_verified: bool = False) -> tuple[str, str]:
    """Return (role, status), defaulting unknown logged-in users to standard."""
    email = (email or "").strip().lower()
    if not email:
        return "public", "active"
    if not email_verified:
        return "standard", "active"
    if email in configured_disabled_emails():
        return "standard", "disabled"
    if email in configured_developer_emails():
        return "developer", "active"
    record = read_supabase_user(email)
    if record:
        return record["role"], record["status"]
    if email in configured_beta_emails():
        return "beta_tester", "active"
    return "standard", "active"


def maybe_record_login(email: str, role: str, status: str) -> None:
    if not email or status != "active":
        return
    key = f"login_recorded_{email}"
    if st.session_state.get(key):
        return
    if supabase_available() and role != "public":
        # Create/update a standard record for new users, while preserving existing
        # role/status from Supabase. Bootstrap developers stay developer.
        existing = read_supabase_user(email)
        target_role = "developer" if email in configured_developer_emails() else (existing.get("role") if existing else role)
        target_status = existing.get("status") if existing else status
        notes = existing.get("notes", "") if existing else "Auto-created from Google login."
        if existing and existing.get("theme_preference"):
            st.session_state["hosted_theme_preference"] = normalise_online_theme(existing.get("theme_preference"))
        upsert_supabase_user(email, str(target_role), str(target_status), notes=notes, actor_email="pathmark-system", update_login=True)
    st.session_state[key] = True

def role_label(role: str) -> str:
    return {
        "public": "Public visitor",
        "standard": "Standard",
        "beta_tester": "Beta tester",
        "developer": "Developer",
    }.get(role, str(role or "standard").replace("_", " ").title())


def clear_hosted_login_session() -> None:
    """Clear Pathmark hosted login and temporary Google Sheets session state."""
    for key in [
        "pathmark_user",
        "pathmark_login_state",
        "google_sheets_credentials",
        "sync_sheet_id",
        "google_oauth_state",
        "on_the_go_connected_notice",
        "auto_create_sync_sheet_after_connect",
        "sync_sheet_ready_attempted",
        "hosted_theme_preference",
    ]:
        st.session_state.pop(key, None)


def render_account_bar(role: str, user: dict[str, str]) -> None:
    """Render compact signed-in controls for the hosted page."""
    configured = login_configured()
    cols = st.columns([4.2, 1.4, 1.2])
    with cols[0]:
        if user.get("email"):
            st.markdown(
                f"<div class='account-card'><div class='account-title'>Signed in</div>"
                f"<div class='account-value'>{html.escape(str(user.get('email')))}</div></div>",
                unsafe_allow_html=True,
            )
        elif configured:
            st.caption("Sign in with Google to access beta or developer features. You can download Pathmark without signing in.")
        else:
            st.caption("Login is not configured yet. Download Pathmark below.")
    with cols[1]:
        if user.get("email"):
            st.markdown(
                f"<div class='account-card'><div class='account-title'>Access level</div>"
                f"<div class='account-value'>{html.escape(role_label(role))}</div></div>",
                unsafe_allow_html=True,
            )
    with cols[2]:
        if user.get("email"):
            st.write("")
            if st.button("Log out", use_container_width=True):
                clear_hosted_login_session()
                st.rerun()
        elif configured:
            auth_url = login_auth_url()
            if auth_url:
                same_tab_oauth_button("Log in with Google", auth_url)
            else:
                st.button("Log in unavailable", use_container_width=True, disabled=True)
        else:
            st.button("Log in not configured", use_container_width=True, disabled=True)

def role_can_use_on_the_go(role: str, status: str) -> bool:
    return status == "active" and feature_enabled("on_the_go_beta", role, default_enabled=True, default_minimum_role="beta_tester")


def role_can_develop(role: str, status: str) -> bool:
    return status == "active" and feature_enabled("developer_panel", role, default_enabled=True, default_minimum_role="developer")


def row_to_csv_bytes(row: dict[str, str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SYNC_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerow({col: row.get(col, "") for col in SYNC_COLUMNS})
    return buffer.getvalue().encode("utf-8")


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


def extract_google_sheet_id(value: str) -> str:
    text = (value or "").strip()
    match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", text)
    if match:
        return match.group(1)
    return text.split("?")[0].strip().strip("/")


def blank_sync_row() -> dict[str, str]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {key: "" for key in SYNC_COLUMNS} | {
        "sync_id": f"otg-{uuid.uuid4().hex}",
        "status": "pending",
        "action": "create",
        "created_at": now,
        "updated_at": now,
        "source": "streamlit_on_the_go",
    }





def google_oauth_config() -> dict[str, Any] | None:
    """Return a Google OAuth web-client config for Sheets/Drive features.

    v0.5.81 uses the main Google login consent to request the narrow
    drive.file scope. The older [google_oauth] section is still supported for
    reconnect/fallback flows, but [auth] can now provide the same web client.
    """
    try:
        cfg = st.secrets.get("google_oauth", None)
    except Exception:
        cfg = None
    if cfg:
        client_id = str(cfg.get("client_id", "")).strip()
        client_secret = str(cfg.get("client_secret", "")).strip()
        redirect_uri = str(cfg.get("redirect_uri", "")).strip()
    else:
        auth_cfg = login_config()
        if not auth_cfg:
            return None
        client_id = auth_cfg["client_id"]
        client_secret = auth_cfg["client_secret"]
        redirect_uri = auth_cfg["redirect_uri"]
    if not (client_id and client_secret and redirect_uri):
        return None
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "client_config": {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
    }


def web_oauth_available() -> bool:
    return google_oauth_config() is not None

def google_oauth_diagnostics() -> dict[str, str]:
    """Return non-secret Google Sheets OAuth diagnostics for the hosted setup panel."""
    cfg = google_oauth_config()
    if not cfg:
        return {
            "configured": "no",
            "client_id_prefix": "",
            "redirect_uri": "",
            "scope": ", ".join(GOOGLE_SHEETS_SCOPES),
            "login_scope": " ".join(LOGIN_SCOPES),
            "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
        }
    client_id = cfg.get("client_id", "")
    prefix = client_id[:18] + "..." if len(client_id) > 18 else client_id
    return {
        "configured": "yes",
        "client_id_prefix": prefix,
        "redirect_uri": cfg.get("redirect_uri", ""),
        "scope": ", ".join(GOOGLE_SHEETS_SCOPES),
        "login_scope": " ".join(LOGIN_SCOPES),
        "auth_uri": cfg.get("client_config", {}).get("web", {}).get("auth_uri", "https://accounts.google.com/o/oauth2/v2/auth"),
    }


def render_google_sheets_oauth_diagnostics() -> None:
    """Show a safe checklist for Google Sheets OAuth setup without exposing secrets."""
    diag = google_oauth_diagnostics()
    with st.expander("Google Sheets connection diagnostics", expanded=False):
        if diag["configured"] == "yes":
            st.success("Google Sheets OAuth secrets are present in Streamlit for this deployment.")
        else:
            st.warning("Google Sheets OAuth secrets are not fully configured in Streamlit.")
        st.dataframe(
            pd.DataFrame([
                {"Setting": "Configured", "Value": diag.get("configured", "")},
                {"Setting": "OAuth client ID", "Value": diag.get("client_id_prefix", "")},
                {"Setting": "Redirect URI", "Value": diag.get("redirect_uri", "")},
                {"Setting": "Login scope", "Value": diag.get("login_scope", "")},
                {"Setting": "Sheets scope", "Value": diag.get("scope", "")},
                {"Setting": "Google auth endpoint", "Value": diag.get("auth_uri", "")},
            ]),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("""
        If Google shows an **Access blocked**, **redirect_uri_mismatch**, or **invalid_request** page, check Google Cloud first:

        1. **APIs & Services → Credentials → OAuth 2.0 Client IDs**: use a **Web application** client.
        2. Add this exact authorised redirect URI: `https://pathmark.streamlit.app`
        3. **Google Auth Platform → Audience**: if the app is in Testing, add your Google account as a test user.
        4. **Google Auth Platform → Data Access**: include the requested scope `https://www.googleapis.com/auth/drive.file`.
        5. **APIs & Services → Library**: enable both **Google Sheets API** and **Google Drive API** for the same project.

        Pathmark now requests `drive.file` during Google login so signed-in users can enter the Web Companion with a Pathmark sync sheet already available. The scope lets Pathmark create and update files the user authorises, rather than requesting access to all spreadsheets.
        """)


def google_credentials_from_session():
    """Return short-lived Google credentials stored only in Streamlit session state.

    The hosted page deliberately avoids requesting offline access. If the access
    token expires, the user reconnects rather than Pathmark storing a refresh
    token on the hosted app.

    v0.5.79 deliberately reconstructs credentials from the short-lived access
    token instead of using Credentials.from_authorized_user_info(). Google's
    helper expects an installed-app style authorised-user payload and can reject
    a perfectly valid session token when no refresh token is present. That made
    Pathmark show a green connection notice while immediately falling back to the
    Connect button on the next rerun.
    """
    raw = st.session_state.get("google_sheets_credentials")
    if not raw:
        return None
    try:
        info = json.loads(raw) if isinstance(raw, str) else dict(raw)
        token = str(info.get("token", "") or "")
        if not token:
            st.session_state.pop("google_sheets_credentials", None)
            return None

        expires_at = int(info.get("expires_at", 0) or 0)
        # Treat tokens as expired a minute early so a save operation does not
        # begin with a token that is about to expire.
        if expires_at and expires_at <= int(datetime.now(timezone.utc).timestamp()) + 60:
            st.session_state.pop("google_sheets_credentials", None)
            return None

        from google.oauth2.credentials import Credentials  # type: ignore
        credentials = Credentials(
            token=token,
            scopes=info.get("scopes") or GOOGLE_SHEETS_SCOPES,
        )
        return credentials
    except Exception:
        st.session_state.pop("google_sheets_credentials", None)
        return None


def revoke_google_session_token() -> None:
    raw = st.session_state.get("google_sheets_credentials")
    token = ""
    try:
        if raw:
            token = json.loads(raw).get("token", "")
    except Exception:
        token = ""
    if token:
        try:
            data = urllib.parse.urlencode({"token": token}).encode("utf-8")
            urllib.request.urlopen("https://oauth2.googleapis.com/revoke", data=data, timeout=5)
        except Exception:
            pass
    st.session_state.pop("google_sheets_credentials", None)
    st.session_state.pop("sync_sheet_id", None)
    st.session_state.pop("google_oauth_state", None)

def exchange_google_code_for_credentials(cfg: dict[str, Any], code: str) -> dict[str, Any]:
    """Exchange a Google OAuth code for short-lived credentials.

    The hosted On-the-go flow intentionally does not use PKCE. In Streamlit Cloud,
    Google often returns to a fresh browser/session after the OAuth round trip.
    A PKCE code verifier stored only in st.session_state can then be lost, causing
    Google to reject the token exchange with "Missing code verifier".

    This is a confidential web-client flow: the client secret stays server-side in
    Streamlit secrets, the OAuth state is signed by Pathmark, and only short-lived
    access credentials are kept in the hosted session. No refresh token is stored.
    """
    token_payload = {
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": cfg["redirect_uri"],
        "grant_type": "authorization_code",
    }
    request = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=urllib.parse.urlencode(token_payload).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        token_data = json.loads(response.read().decode("utf-8"))

    expires_at = None
    if token_data.get("expires_in"):
        try:
            expires_at = int(datetime.now(timezone.utc).timestamp()) + int(token_data["expires_in"])
        except Exception:
            expires_at = None

    cred_info = {
        "token": token_data.get("access_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": cfg["client_id"],
        "scopes": token_data.get("scope", " ".join(GOOGLE_SHEETS_SCOPES)).split(),
    }
    if expires_at:
        cred_info["expires_at"] = expires_at
        cred_info["expiry"] = datetime.fromtimestamp(expires_at, timezone.utc).isoformat().replace("+00:00", "Z")
    return cred_info


def handle_google_oauth_redirect() -> None:
    """Complete Google Sheets OAuth callbacks before the gated tabs render."""
    cfg = google_oauth_config()
    if not cfg:
        return
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")
    if isinstance(code, list):
        code = code[0] if code else None
    if isinstance(state, list):
        state = state[0] if state else None
    if isinstance(error, list):
        error = error[0] if error else None
    if error:
        st.warning(f"Google authorisation was not completed: {error}")
        st.query_params.clear()
        return
    if not code:
        return
    expected_state = st.session_state.get("google_oauth_state")
    if not (state and str(state).startswith("sheets:")):
        return
    session_match = bool(expected_state and secrets.compare_digest(str(expected_state), str(state)))
    signed_match = verify_signed_oauth_state(str(state), "sheets")
    if not (session_match or signed_match):
        st.session_state.pop("google_oauth_state", None)
        st.query_params.clear()
        st.error("Google authorisation could not be verified. Please reconnect from the On the go tab.")
        return
    context_values = urllib.parse.parse_qs(signed_state_context(str(state), "sheets"))
    restored_email = (context_values.get("email", [""])[0] or "").strip().lower()
    if restored_email and not current_user().get("email"):
        st.session_state["pathmark_user"] = {"email": restored_email, "name": "", "email_verified": True}
    try:
        cred_info = exchange_google_code_for_credentials(cfg, str(code))
        if not cred_info.get("token"):
            raise RuntimeError("Google did not return an access token.")
        st.session_state["google_sheets_credentials"] = json.dumps(cred_info)
        st.session_state["on_the_go_connected_notice"] = "Google Sheets is connected for this session."
        st.session_state["auto_create_sync_sheet_after_connect"] = True
        st.session_state.pop("google_oauth_state", None)
        st.query_params.clear()
        st.rerun()
    except Exception as exc:
        st.session_state.pop("google_oauth_state", None)
        st.query_params.clear()
        st.warning("Could not complete Google authorisation. Please try logging in again.")


def google_auth_url() -> str | None:
    cfg = google_oauth_config()
    if not cfg:
        return None
    try:
        user = current_user()
        user_email = str(user.get("email", "") or "").strip().lower()
        context = f"return=on_the_go&email={urllib.parse.quote(user_email, safe='')}" if user_email else "return=on_the_go"
        state = make_signed_oauth_state("sheets", context=context)
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(GOOGLE_SHEETS_SCOPES),
            "state": state,
            "access_type": "online",
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
        st.session_state["google_oauth_state"] = state
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    except Exception as exc:
        st.warning("Could not prepare Google authorisation. Please refresh the page and try again.")
        return None

def sheets_service():
    credentials = google_credentials_from_session()
    if not credentials:
        return None
    try:
        from googleapiclient.discovery import build  # type: ignore
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        st.warning(f"Could not connect to Google Sheets: {exc}")
        return None


def drive_service():
    credentials = google_credentials_from_session()
    if not credentials:
        return None
    try:
        from googleapiclient.discovery import build  # type: ignore
        return build("drive", "v3", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        st.warning(f"Could not connect to Google Drive: {exc}")
        return None


def find_existing_sync_sheet() -> tuple[bool, str, str]:
    """Find the newest Pathmark Sync sheet visible to the app.

    With the narrow drive.file scope, Google will only return files this app
    created or files the user explicitly authorised for this app. That is the
    intended privacy boundary for Pathmark Online.
    """
    service = drive_service()
    if service is None:
        return False, "", "Google Drive is not available for this session."
    try:
        # Search by both name and Pathmark appProperties. Older beta sheets only
        # had the name, while v0.5.86+ tags newly created files with appProperties
        # to make them easier to re-find without using a broad Drive scope.
        queries = [
            "appProperties has { key='pathmark_sync' and value='true' } and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            f"name='{SYNC_SHEET_TITLE.replace(chr(39), chr(92)+chr(39))}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        ]
        found_files: list[dict[str, Any]] = []
        for query in queries:
            result = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id,name,modifiedTime,webViewLink,appProperties)",
                orderBy="modifiedTime desc",
                pageSize=10,
            ).execute()
            for file in result.get("files", []):
                if file.get("id") and not any(existing.get("id") == file.get("id") for existing in found_files):
                    found_files.append(file)
        if not found_files:
            return False, "", "No existing Pathmark sync sheet was found for this app. To avoid duplicates, Pathmark will not create another one automatically. Use Create new sync sheet only if this is your first Pathmark Online sheet, or paste the URL of your existing sheet under Advanced."
        file = sorted(found_files, key=lambda f: str(f.get("modifiedTime", "")), reverse=True)[0]
        sheet_id = file.get("id", "")
        if sheet_id:
            st.session_state["sync_sheet_id"] = sheet_id
            return True, sheet_id, file.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{sheet_id}")
        return False, "", "The existing Pathmark sync sheet did not return a file ID."
    except Exception as exc:
        return False, "", f"Could not look for an existing Pathmark sync sheet: {exc}"


def ensure_pathmark_sync_sheet_ready() -> tuple[bool, str, str]:
    """Find or create the user's Pathmark sync sheet for the current session."""
    existing = st.session_state.get("sync_sheet_id", "")
    if existing:
        service = sheets_service()
        if service is None:
            return False, "", "Google Sheets is not available for this session."
        try:
            ensure_pathmark_online_schema(service, existing)
            return True, existing, f"https://docs.google.com/spreadsheets/d/{existing}"
        except Exception as exc:
            return False, "", f"Could not verify the selected Pathmark sync sheet: {exc}"

    found, sheet_id, link_or_message = find_existing_sync_sheet()
    if found and sheet_id:
        service = sheets_service()
        if service is not None:
            ensure_pathmark_online_schema(service, sheet_id)
        return True, sheet_id, link_or_message

    return False, "", link_or_message


def ensure_pending_changes_sheet(service: Any, sheet_id: str) -> None:
    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_titles = [sheet.get("properties", {}).get("title") for sheet in metadata.get("sheets", [])]
    if "pending_changes" not in sheet_titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": "pending_changes"}}}]},
        ).execute()
    values = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="pending_changes!1:1").execute().get("values", [])
    if not values or values[0] != SYNC_COLUMNS:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"pending_changes!A1:{chr(64 + len(SYNC_COLUMNS))}1",
            valueInputOption="RAW",
            body={"values": [SYNC_COLUMNS]},
        ).execute()


def create_user_sync_sheet() -> tuple[bool, str, str]:
    service = sheets_service()
    if service is None:
        return False, "", "Connect Google Sheets first."
    try:
        spreadsheet = service.spreadsheets().create(
            body={
                "properties": {"title": SYNC_SHEET_TITLE},
                "sheets": [{"properties": {"title": "pending_changes"}}],
            },
            fields="spreadsheetId,spreadsheetUrl",
        ).execute()
        sheet_id = spreadsheet.get("spreadsheetId", "")
        try:
            dservice = drive_service()
            if dservice is not None and sheet_id:
                dservice.files().update(
                    fileId=sheet_id,
                    body={"appProperties": {"pathmark_sync": "true", "pathmark_version": "0.6.1"}},
                    fields="id",
                ).execute()
        except Exception:
            pass
        ensure_pathmark_online_schema(service, sheet_id)
        st.session_state["sync_sheet_id"] = sheet_id
        return True, sheet_id, spreadsheet.get("spreadsheetUrl", "")
    except Exception as exc:
        return False, "", f"Could not create a Pathmark sync sheet: {exc}"



def list_pathmark_drive_files_for_deletion(current_sheet_id: str = "") -> tuple[bool, list[dict[str, str]], str]:
    """Return only Drive files Pathmark can identify as Pathmark-owned/authorised.

    Pathmark uses the limited drive.file permission, so Drive only returns files
    this app created or files the user explicitly authorised for this app. This
    deletion list is deliberately stricter: it includes tagged Pathmark Sync
    spreadsheets and the current connected sync sheet. It also includes folders
    only when they carry Pathmark's appProperties tag. It does not delete Drive
    folders simply because they are named "Pathmark".
    """
    service = drive_service()
    if service is None:
        return False, [], "Google Drive is not available for this session."
    found: list[dict[str, str]] = []

    def add_file(file: dict[str, Any]) -> None:
        fid = str(file.get("id", "") or "")
        if not fid or any(existing.get("id") == fid for existing in found):
            return
        found.append({
            "id": fid,
            "name": str(file.get("name", "") or "Untitled Pathmark file"),
            "mimeType": str(file.get("mimeType", "") or ""),
            "modifiedTime": str(file.get("modifiedTime", "") or ""),
            "webViewLink": str(file.get("webViewLink", "") or ""),
        })

    try:
        queries = [
            "appProperties has { key='pathmark_sync' and value='true' } and trashed=false",
            "appProperties has { key='pathmark_folder' and value='true' } and mimeType='application/vnd.google-apps.folder' and trashed=false",
        ]
        for query in queries:
            result = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id,name,mimeType,modifiedTime,webViewLink,appProperties)",
                orderBy="modifiedTime desc",
                pageSize=50,
            ).execute()
            for file in result.get("files", []):
                add_file(file)
        if current_sheet_id:
            try:
                file = service.files().get(
                    fileId=current_sheet_id,
                    fields="id,name,mimeType,modifiedTime,webViewLink,appProperties",
                ).execute()
                is_sheet = file.get("mimeType") == "application/vnd.google-apps.spreadsheet"
                props = file.get("appProperties", {}) or {}
                is_pathmark = props.get("pathmark_sync") == "true" or file.get("name") == SYNC_SHEET_TITLE
                if is_sheet and is_pathmark:
                    add_file(file)
            except Exception:
                pass
        return True, found, f"Found {len(found)} Pathmark file(s) available to this app."
    except Exception as exc:
        return False, [], f"Could not check Google Drive for Pathmark files: {exc}"


def delete_pathmark_drive_files(file_ids: list[str]) -> tuple[bool, str]:
    service = drive_service()
    if service is None:
        return False, "Google Drive is not available for this session."
    deleted = 0
    failed = 0
    for fid in file_ids:
        fid = str(fid or "").strip()
        if not fid:
            continue
        try:
            service.files().delete(fileId=fid).execute()
            deleted += 1
        except Exception:
            failed += 1
    if failed:
        return False, f"Deleted {deleted} Pathmark file(s), but {failed} file(s) could not be deleted. You can remove remaining files from Google Drive."
    return True, f"Deleted {deleted} Pathmark file(s) from Google Drive."


def delete_supabase_profile_data(email: str) -> tuple[bool, str]:
    """Remove the signed-in user's Pathmark Online profile metadata from Supabase."""
    email = (email or "").strip().lower()
    if not email:
        return False, "No signed-in email was found."
    if not supabase_available():
        return True, "No Supabase profile store is configured."
    encoded_email = urllib.parse.quote(email, safe="")
    audit_query = f"?or=(actor_email.eq.{encoded_email},target_email.eq.{encoded_email})"
    supabase_request("DELETE", "pathmark_audit_log", query=audit_query, prefer="return=minimal")
    user_query = "?" + urllib.parse.urlencode({"email": f"eq.{email}"})
    ok, payload = supabase_request("DELETE", "pathmark_users", query=user_query, prefer="return=minimal")
    if not ok:
        return False, "Could not remove the Pathmark access profile from Supabase."
    return True, "Removed the Pathmark access/profile record from Supabase."


def full_google_disconnect_and_data_removal(sheet_id: str, email: str, remove_supabase_profile: bool = True) -> tuple[bool, str]:
    ok_list, files, message = list_pathmark_drive_files_for_deletion(sheet_id)
    if not ok_list:
        return False, safe_user_message(message)
    file_ids = [f["id"] for f in files]
    ok_delete, delete_message = delete_pathmark_drive_files(file_ids) if file_ids else (True, "No Pathmark Google Drive files were found for this app to delete.")
    ok_profile, profile_message = (True, "Supabase profile was not removed.")
    if remove_supabase_profile:
        ok_profile, profile_message = delete_supabase_profile_data(email)
    revoke_google_session_token()
    clear_hosted_login_session()
    combined = f"{delete_message} {profile_message} Google access has been disconnected for this browser session."
    return ok_delete and ok_profile, combined


def append_to_user_oauth_sheet(sheet_id: str, row: dict[str, str]) -> tuple[bool, str]:
    sheet_id = extract_google_sheet_id(sheet_id)
    if not sheet_id:
        return False, "No Google Sheet ID was provided."
    service = sheets_service()
    if service is None:
        return False, "Connect Google Sheets before saving to a sync sheet."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="pending_changes!A:O",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [[row.get(col, "") for col in SYNC_COLUMNS]]},
        ).execute()
        st.session_state["sync_sheet_id"] = sheet_id
        return True, "Saved to your Google Sheet."
    except Exception as exc:
        return False, f"Could not write to the sync sheet: {exc}"


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sheet_col_letter(index: int) -> str:
    """Convert a 1-based column index to an A1 notation column letter."""
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters or "A"


def _online_cache_key(sheet_id: str) -> str:
    return f"online_tables::{sheet_id}"


def clear_online_cache(sheet_id: str | None = None) -> None:
    if sheet_id:
        st.session_state.pop(_online_cache_key(sheet_id), None)
    else:
        for key in list(st.session_state.keys()):
            if str(key).startswith("online_tables::"):
                st.session_state.pop(key, None)


def ensure_sheet_with_header(service: Any, sheet_id: str, title: str, columns: list[str], existing_titles: set[str] | None = None) -> None:
    """Create a sheet tab and header without destroying older user rows.

    Earlier beta builds used narrower headers. From v0.5.84 onwards we append
    missing columns rather than replacing the whole header, so existing data in
    the user's Google Sheet remains aligned.
    """
    if existing_titles is None:
        metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        existing_titles = {sheet.get("properties", {}).get("title") for sheet in metadata.get("sheets", [])}
    if title not in existing_titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        ).execute()
        existing_titles.add(title)
    end_col = sheet_col_letter(max(len(columns), 1))
    values = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{title}!A1:{end_col}1").execute().get("values", [])
    current = list(values[0]) if values else []
    if not current:
        final = columns
    else:
        final = current + [col for col in columns if col not in current]
    if final != current:
        end_col = sheet_col_letter(len(final))
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{title}!A1:{end_col}1",
            valueInputOption="RAW",
            body={"values": [final]},
        ).execute()


def ensure_pathmark_online_schema(service: Any, sheet_id: str) -> None:
    """Prepare the user-owned Google Sheet for Pathmark Online records.

    This is deliberately guarded by session state because repeated Streamlit
    reruns can otherwise spend most of the user's Sheets read quota checking the
    same headers again and again.
    """
    ready_key = f"online_schema_ready::{sheet_id}"
    if st.session_state.get(ready_key):
        return
    ensure_pending_changes_sheet(service, sheet_id)
    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_titles = {sheet.get("properties", {}).get("title") for sheet in metadata.get("sheets", [])}
    for title, columns in ONLINE_TABLES.items():
        ensure_sheet_with_header(service, sheet_id, title, columns, sheet_titles)
    st.session_state[ready_key] = True


def _values_to_dataframe(values: list[list[str]], expected_columns: list[str]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=expected_columns)
    header = list(values[0]) if values and values[0] else list(expected_columns)
    rows = values[1:]
    normalised = []
    for row in rows:
        padded = list(row) + [""] * (len(header) - len(row))
        normalised.append(padded[:len(header)])
    df = pd.DataFrame(normalised, columns=header)
    for col in expected_columns:
        if col not in df.columns:
            df[col] = ""
    df = df[expected_columns]
    if "status" in df.columns:
        df = df[df["status"].fillna("").str.lower().ne("archived")]
    return df.reset_index(drop=True)


def load_online_tables(sheet_id: str, force: bool = False) -> dict[str, pd.DataFrame]:
    """Read all Pathmark Online tables with a single batch request.

    This avoids hitting the Google Sheets per-user read limit when Streamlit
    reruns and several tabs ask for Areas, Goals, Routines, Actions and exports.
    """
    cache_key = _online_cache_key(sheet_id)
    if not force and cache_key in st.session_state:
        return st.session_state[cache_key]
    service = sheets_service()
    if service is None:
        tables = {name: pd.DataFrame(columns=cols) for name, cols in ONLINE_TABLES.items()}
        st.session_state[cache_key] = tables
        return tables
    ensure_pathmark_online_schema(service, sheet_id)
    ranges = [f"{name}!A1:{sheet_col_letter(len(cols))}" for name, cols in ONLINE_TABLES.items()]
    try:
        result = service.spreadsheets().values().batchGet(spreadsheetId=sheet_id, ranges=ranges).execute()
        value_ranges = result.get("valueRanges", [])
        tables: dict[str, pd.DataFrame] = {}
        for (name, columns), vr in zip(ONLINE_TABLES.items(), value_ranges):
            tables[name] = _values_to_dataframe(vr.get("values", []), columns)
        for name, columns in ONLINE_TABLES.items():
            tables.setdefault(name, pd.DataFrame(columns=columns))
        st.session_state[cache_key] = tables
        return tables
    except Exception as exc:
        st.warning("Pathmark could not read your online records from Google Sheets. Please refresh online data from Settings or try again shortly.")
        tables = {name: pd.DataFrame(columns=cols) for name, cols in ONLINE_TABLES.items()}
        st.session_state[cache_key] = tables
        return tables




def read_online_tables(sheet_id: str, force: bool = False) -> dict[str, pd.DataFrame]:
    """Compatibility wrapper for older render paths.

    v0.5.91 accidentally called read_online_tables() after the batch reader
    had been named load_online_tables(). Keeping this wrapper prevents a
    user-facing NameError and preserves the single batch-read cache path.
    """
    return load_online_tables(sheet_id, force=force)


def read_online_table(sheet_id: str, table: str) -> pd.DataFrame:
    columns = ONLINE_TABLES.get(table)
    if not columns:
        return pd.DataFrame()
    if not sheet_id:
        return pd.DataFrame(columns=columns)
    return load_online_tables(sheet_id).get(table, pd.DataFrame(columns=columns)).copy()


def append_online_record(sheet_id: str, table: str, record: dict[str, Any]) -> tuple[bool, str]:
    columns = ONLINE_TABLES.get(table)
    if not columns:
        return False, "Unknown Pathmark table."
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        now = utc_now_text()
        row = {col: str(record.get(col, "") or "") for col in columns}
        if "created_at" in columns and not row.get("created_at"):
            row["created_at"] = now
        if "updated_at" in columns:
            row["updated_at"] = now
        if "status" in columns and not row.get("status"):
            row["status"] = "active"
        if "source" in columns and not row.get("source"):
            row["source"] = "pathmark_online"
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{table}!A:{sheet_col_letter(len(columns))}",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [[row.get(col, "") for col in columns]]},
        ).execute()
        clear_online_cache(sheet_id)
        return True, "Saved to your Pathmark sync sheet."
    except Exception as exc:
        return False, f"Could not save to your Pathmark sync sheet: {exc}"



ONLINE_ID_COLUMNS = {
    "areas": "area_id",
    "goals": "goal_id",
    "routines": "routine_id",
    "actions": "action_id",
    "pending_changes": "sync_id",
}


def append_many_online_records(sheet_id: str, records_by_table: dict[str, list[dict[str, Any]]]) -> tuple[bool, str]:
    """Append starter/example records with one write per table.

    This keeps the online setup guided without consuming lots of Google Sheets
    quota through one request per row.
    """
    sheet_id = extract_google_sheet_id(sheet_id)
    service = sheets_service()
    if service is None:
        return False, "Google Sheets is not available for this session."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        total = 0
        for table, records in records_by_table.items():
            if not records:
                continue
            columns = ONLINE_TABLES.get(table)
            if not columns:
                continue
            now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            rows = []
            for record in records:
                row = dict(record)
                row.setdefault("created_at", now)
                row.setdefault("updated_at", now)
                row.setdefault("source", "Pathmark Online starter examples")
                rows.append([str(row.get(col, "")) for col in columns])
            service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=f"{table}!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": rows},
            ).execute()
            total += len(rows)
        clear_online_cache(sheet_id)
        return True, f"Loaded {total} editable starter records into your Pathmark sync sheet."
    except Exception as exc:
        return False, f"Could not load starter examples: {exc}"


def update_online_record(sheet_id: str, table: str, record_id: str, updates: dict[str, Any]) -> tuple[bool, str]:
    """Update one Google Sheet row by stable record id.

    This gives Pathmark Online the same edit-first behaviour as the desktop app,
    while keeping storage in the user-owned sync sheet rather than local files.
    """
    columns = ONLINE_TABLES.get(table)
    id_col = ONLINE_ID_COLUMNS.get(table)
    if not columns or not id_col:
        return False, "This Pathmark table cannot be edited yet."
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        values = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{table}!A1:{sheet_col_letter(len(columns))}",
        ).execute().get("values", [])
        if not values:
            return False, "Could not find this table in your Pathmark sync sheet."
        header = list(values[0])
        try:
            id_index = header.index(id_col)
        except ValueError:
            return False, f"The {table} table is missing its {id_col} column."
        row_number = None
        row_values = None
        for i, row in enumerate(values[1:], start=2):
            padded = list(row) + [""] * (len(header) - len(row))
            if str(padded[id_index]).strip() == str(record_id).strip():
                row_number = i
                row_values = padded[:len(header)]
                break
        if row_number is None or row_values is None:
            return False, "Could not find that record in your Pathmark sync sheet."
        row_map = {col: row_values[idx] if idx < len(row_values) else "" for idx, col in enumerate(header)}
        for key, value in updates.items():
            if key in header:
                row_map[key] = str(value or "")
        if "updated_at" in header:
            row_map["updated_at"] = utc_now_text()
        new_row = [row_map.get(col, "") for col in header]
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{table}!A{row_number}:{sheet_col_letter(len(header))}{row_number}",
            valueInputOption="USER_ENTERED",
            body={"values": [new_row]},
        ).execute()
        clear_online_cache(sheet_id)
        return True, "Updated in your Pathmark sync sheet."
    except Exception as exc:
        return False, f"Could not update your Pathmark sync sheet: {exc}"


def archive_online_record(sheet_id: str, table: str, record_id: str, reason: str = "") -> tuple[bool, str]:
    updates = {"status": "archived"}
    columns = ONLINE_TABLES.get(table, [])
    if "archived_at" in columns:
        updates["archived_at"] = utc_now_text()
    if "archived_reason" in columns:
        updates["archived_reason"] = reason
    if "notes" in columns and reason:
        updates["notes"] = reason
    return update_online_record(sheet_id, table, record_id, updates)


def restore_online_record(sheet_id: str, table: str, record_id: str) -> tuple[bool, str]:
    columns = ONLINE_TABLES.get(table, [])
    updates = {"status": "active"}
    if "restored_at" in columns:
        updates["restored_at"] = utc_now_text()
    if "archived_reason" in columns:
        updates["archived_reason"] = ""
    return update_online_record(sheet_id, table, record_id, updates)


def mark_actions_exported(sheet_id: str, action_ids: list[str], export_type: str, *, archive: bool = True) -> tuple[bool, str]:
    ids = [str(x).strip() for x in action_ids if str(x).strip()]
    if not ids:
        return False, "No exported items were available to move."
    batch_id = f"export-{uuid.uuid4().hex[:12]}"
    stamp = utc_now_text()
    ok_count = 0
    last_message = ""
    for action_id in ids:
        updates = {
            "exported_at": stamp,
            "export_type": export_type,
            "export_batch_id": batch_id,
        }
        if archive:
            updates.update({
                "status": "archived",
                "archived_at": stamp,
                "archived_reason": f"Moved to Archive after {export_type} export.",
            })
        ok, message = update_online_record(sheet_id, "actions", action_id, updates)
        last_message = message
        if ok:
            ok_count += 1
    clear_online_cache(sheet_id)
    if ok_count:
        return True, f"Moved {ok_count} exported item(s) to Archive. Batch: {batch_id}."
    return False, last_message or "Could not move the exported items to Archive."


def active_online_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "status" not in df.columns:
        return df
    return df[df["status"].fillna("").str.lower().ne("archived")].reset_index(drop=True)

def area_options(sheet_id: str) -> list[str]:
    df = read_online_table(sheet_id, "areas") if sheet_id else pd.DataFrame()
    if df.empty or "area_name" not in df.columns:
        return []
    return sorted({str(name).strip() for name in df["area_name"].tolist() if str(name).strip()})


def find_area_id(sheet_id: str, area_name: str) -> str:
    df = read_online_table(sheet_id, "areas") if sheet_id else pd.DataFrame()
    if df.empty:
        return ""
    for _, row in df.iterrows():
        if str(row.get("area_name", "")).strip().lower() == area_name.strip().lower():
            return str(row.get("area_id", ""))
    return ""


def area_defaults(sheet_id: str, area_name: str) -> dict[str, str]:
    df = read_online_table(sheet_id, "areas") if sheet_id else pd.DataFrame()
    if df.empty:
        return {}
    for _, row in df.iterrows():
        if str(row.get("area_name", "")).strip().lower() == area_name.strip().lower():
            return {k: str(row.get(k, "") or "") for k in df.columns}
    return {}


def record_title_map(df: pd.DataFrame, id_col: str) -> dict[str, str]:
    if df.empty or id_col not in df.columns:
        return {}
    out = {}
    for _, row in df.iterrows():
        rid = str(row.get(id_col, "") or "").strip()
        title = str(row.get("title", "") or "Untitled").strip() or "Untitled"
        if rid:
            out[rid] = title
    return out




def safe_user_message(message: str) -> str:
    """Keep low-level API/code details out of the normal user interface."""
    text = str(message or "")
    low = text.lower()
    raw_markers = [
        "<httperror", "traceback", "nameerror", "keyerror", "valueerror",
        "deltagenerator", "streamlit.runtime", "googleapis.com", "returned \"",
        "quota exceeded", "rate limit", "refresh token", "access token",
    ]
    if any(marker in low for marker in raw_markers):
        if "quota" in low or "rate" in low or "429" in low:
            return "Pathmark could not refresh online data just now because Google Sheets is busy. Please wait a moment, then try Refresh online data."
        return "Pathmark could not complete that action. Please refresh online data or reconnect Google access, then try again."
    # Keep very long implementation messages out of the normal UI.
    if len(text) > 500:
        return "Pathmark could not complete that action. Please try again. Developer details are available in diagnostics."
    return text


def render_safe_section(label: str, func, *args, **kwargs) -> None:
    """Render a user-facing section without exposing raw tracebacks in the app."""
    try:
        func(*args, **kwargs)
    except Exception as exc:
        st.warning(f"Pathmark could not open {label} just now. Please refresh online data and try again.")
        user = current_user() if 'current_user' in globals() else {}
        if str(user.get('role', '')).lower() == 'developer':
            with st.expander("Developer diagnostics", expanded=False):
                st.code(repr(exc))
def dataframe_preview(df: pd.DataFrame, columns: list[str]) -> None:
    if df.empty:
        st.info("No records yet.")
    else:
        show_cols = [col for col in columns if col in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)



def online_setting(sheet_id: str, key: str, default: str = "") -> str:
    settings = read_online_table(sheet_id, "settings") if sheet_id else pd.DataFrame()
    if settings.empty or "key" not in settings.columns:
        return default
    matches = settings[settings["key"].fillna("").astype(str).eq(key)]
    if matches.empty:
        return default
    return str(matches.iloc[-1].get("value", default) or default)


def save_online_setting(sheet_id: str, key: str, value: str, source: str = "pathmark_online") -> tuple[bool, str]:
    settings = read_online_table(sheet_id, "settings") if sheet_id else pd.DataFrame()
    if not settings.empty and "key" in settings.columns:
        matches = settings[settings["key"].fillna("").astype(str).eq(key)]
        if not matches.empty:
            service = sheets_service()
            if service is None:
                return False, "Google Sheets access is not available for this session."
            try:
                values = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="settings!A:Z").execute().get("values", [])
                if not values:
                    return append_online_record(sheet_id, "settings", {"key": key, "value": value, "source": source})
                header = values[0]
                try:
                    key_idx = header.index("key")
                except ValueError:
                    return append_online_record(sheet_id, "settings", {"key": key, "value": value, "source": source})
                value_idx = header.index("value") if "value" in header else 1
                updated_idx = header.index("updated_at") if "updated_at" in header else 2
                source_idx = header.index("source") if "source" in header else 3
                row_number = None
                for i, row in enumerate(values[1:], start=2):
                    if len(row) > key_idx and str(row[key_idx]) == key:
                        row_number = i
                        break
                if row_number is None:
                    return append_online_record(sheet_id, "settings", {"key": key, "value": value, "source": source})
                max_idx = max(value_idx, updated_idx, source_idx)
                full_row = values[row_number - 1] + [""] * (max_idx + 1 - len(values[row_number - 1]))
                full_row[value_idx] = value
                full_row[updated_idx] = utc_now_text()
                full_row[source_idx] = source
                service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=f"settings!A{row_number}:{sheet_col_letter(max_idx + 1)}{row_number}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [full_row[:max_idx + 1]]},
                ).execute()
                clear_online_cache(sheet_id)
                return True, "Saved."
            except Exception as exc:
                return False, f"Could not save setting: {exc}"
    return append_online_record(sheet_id, "settings", {"key": key, "value": value, "updated_at": utc_now_text(), "source": source})


def inject_theme_css(theme_name: str) -> None:
    """Apply Pathmark's seasonal accent without overriding Streamlit appearance."""
    theme_name = normalise_online_theme(theme_name)
    theme = ONLINE_THEMES.get(theme_name, ONLINE_THEMES["Winter"])
    accent = theme.get("accent", "#334E68")
    seasonal_icon = theme.get("seasonal_icon", "")
    mode = streamlit_appearance_mode()
    st.markdown(
        f"""
        <style>
        :root, [data-testid="stAppViewContainer"] {{
          color-scheme: light dark;
          --accent: {accent};
          --pathmark-accent: {accent};
          --pathmark-accent-strong: color-mix(in srgb, var(--pathmark-accent) 76%, #000000);
          --pathmark-button-text: #FFFFFF;
{pathmark_theme_tokens_css(mode)}
          --pathmark-bg: var(--bg);
          --pathmark-surface: var(--surface);
          --pathmark-ink: var(--ink);
          --pathmark-muted: var(--muted);
          --pathmark-line: var(--line);
          --pathmark-season-soft: var(--accent-soft);
        }}
        .stApp, [data-testid="stAppViewContainer"] {{
          background-color: var(--pathmark-bg) !important;
          color: var(--pathmark-ink) !important;
        }}
        .card, .meta-card, .connection-card, .download-panel, .process-card, .step-card,
        .pathmark-card, .issue-card, .setup-shell, .workspace-card {{
          background: var(--pathmark-surface) !important;
          color: var(--pathmark-ink) !important;
          border: 1px solid var(--pathmark-line) !important;
          border-radius: 14px !important;
        }}
        .eyebrow, .pathmark-note, .pathmark-hint, .setup-example, .area-colour-preview {{
          background: var(--pathmark-season-soft) !important;
          color: var(--pathmark-ink) !important;
          border-color: var(--pathmark-line) !important;
        }}
        .seasonal-mark::after {{ content: " {seasonal_icon}"; }}
        .guide-box {{
          border-left: 5px solid var(--pathmark-accent) !important;
          background: var(--pathmark-surface) !important;
          color: var(--pathmark-ink) !important;
        }}
        .setup-progress-wrap {{ width: 100%; height: 10px; border-radius: 999px; background: color-mix(in srgb, var(--pathmark-muted) 20%, transparent); overflow: hidden; margin: 0.7rem 0 0.25rem; }}
        .setup-progress-fill {{ height: 100%; background: var(--pathmark-accent-strong); border-radius: 999px; }}
        .setup-step-label {{ display: inline-flex; gap: .3rem; padding: .25rem .6rem; border-radius: 999px; background: var(--pathmark-season-soft); color: var(--pathmark-ink); font-weight: 720; }}
        .stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a, [data-testid="stLinkButton"] a:visited, [data-testid="stLinkButton"] a:hover,
        a[data-testid="baseLinkButton-secondary"], a[data-testid="baseLinkButton-primary"] {{
          background: var(--pathmark-accent-strong) !important;
          color: var(--pathmark-button-text) !important;
          border-color: color-mix(in srgb, var(--pathmark-accent-strong) 70%, #000000) !important;
          text-decoration: none !important;
          font-weight: 650 !important;
        }}
        .stButton button *, .stButton button p, .stButton button span,
        .stDownloadButton button *, .stDownloadButton button p, .stDownloadButton button span,
        [data-testid="stLinkButton"] a, [data-testid="stLinkButton"] a *,
        a[data-testid="baseLinkButton-secondary"] *, a[data-testid="baseLinkButton-primary"] * {{ color: var(--pathmark-button-text) !important; }}
        .stButton button:disabled, .stDownloadButton button:disabled {{
          background: color-mix(in srgb, var(--pathmark-surface) 82%, var(--pathmark-muted)) !important;
          color: var(--pathmark-muted) !important;
          border-color: var(--pathmark-line) !important;
        }}
        .stButton button:disabled *, .stDownloadButton button:disabled * {{ color: var(--pathmark-muted) !important; }}
        [data-testid="stTabs"] button, [data-testid="stTabs"] button *, button[data-baseweb="tab"], button[data-baseweb="tab"] *,
        [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *, label, label *,
        [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] span {{
          color: var(--pathmark-ink) !important;
          opacity: 1 !important;
        }}
        [data-testid="stTabs"] button[aria-selected="true"], [data-testid="stTabs"] button[aria-selected="true"] *,
        button[data-baseweb="tab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] * {{
          color: var(--pathmark-accent) !important;
          font-weight: 760 !important;
        }}
        input, textarea, [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
        [data-testid="stDateInput"] input, [data-testid="stTimeInput"] input {{
          background: var(--pathmark-surface) !important;
          color: var(--pathmark-ink) !important;
          border-color: var(--pathmark-line) !important;
        }}
        [role="listbox"], [role="option"] {{ background: var(--pathmark-surface) !important; color: var(--pathmark-ink) !important; }}
        .swatch-row {{ display: flex; flex-wrap: wrap; gap: .45rem; margin: .35rem 0 .65rem; }}
        .swatch {{ display: inline-flex; align-items: center; gap: .35rem; padding: .25rem .45rem; border: 1px solid var(--pathmark-line); border-radius: 999px; background: var(--pathmark-surface); }}
        .swatch-dot, .area-colour-dot {{ width: .9rem; height: .9rem; border-radius: 999px; display: inline-block; border: 1px solid color-mix(in srgb, #000 22%, transparent); }}
        .area-colour-preview {{ display:flex; align-items:center; gap:.6rem; padding:.75rem .85rem; border-left: 5px solid var(--pathmark-accent); border-radius: 12px; margin: .5rem 0 1rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_online_theme(sheet_id: str) -> None:
    theme_name = online_setting(sheet_id, "theme", st.session_state.get("hosted_theme_preference", "Winter")) if sheet_id else st.session_state.get("hosted_theme_preference", "Winter")
    inject_theme_css(normalise_online_theme(theme_name))


def google_colour_label(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return GOOGLE_COLOUR_LABELS[0]
    return GOOGLE_COLOUR_BY_CODE_OR_NAME.get(text.lower(), GOOGLE_COLOUR_LABELS[0])


def google_colour_code(label_or_value: str) -> str:
    label = google_colour_label(label_or_value)
    return GOOGLE_COLOUR_BY_LABEL[label]["code"]


def render_google_colour_swatch(selected_label: str | None = None) -> None:
    items = []
    for label in GOOGLE_COLOUR_LABELS:
        info = GOOGLE_COLOUR_BY_LABEL[label]
        weight = "font-weight:760;" if label == selected_label else ""
        items.append(f"<span class='swatch' style='{weight}'><span class='swatch-dot' style='background:{info['hex']}'></span>{html.escape(info['name'])}</span>")
    st.markdown("<div class='swatch-row'>" + "".join(items) + "</div>", unsafe_allow_html=True)


def parse_days_text(days_text: str) -> tuple[list[str], list[str]]:
    text = str(days_text or "").strip()
    if not text:
        return [], []
    parts = [p.strip().lower() for p in re.split(r"[,;/]+|\band\b", text, flags=re.IGNORECASE) if p.strip()]
    valid, invalid = [], []
    for part in parts:
        day = DAY_ALIASES.get(part)
        if day:
            if day not in valid:
                valid.append(day)
        else:
            invalid.append(part)
    return valid, invalid


def normalise_days_text(days_text: str) -> str:
    valid, _invalid = parse_days_text(days_text)
    return ", ".join(valid)


def validate_routine_schedule(frequency: str, preferred_days: str) -> list[str]:
    problems: list[str] = []
    freq = str(frequency or "").strip()
    days = str(preferred_days or "").strip()
    if freq not in VALID_FREQUENCIES:
        problems.append("Choose a frequency from the list so calendar and task exports can interpret it.")
    valid_days, invalid_days = parse_days_text(days)
    if invalid_days:
        problems.append("Preferred days must use weekday names such as Monday, Wednesday, Friday.")
    if freq in {"Weekly", "Weekdays"} and not valid_days:
        problems.append("Weekly and Weekdays routines need preferred days for reliable exports.")
    if freq == "Weekdays":
        weekend = {"Saturday", "Sunday"}.intersection(valid_days)
        if weekend:
            problems.append("A Weekdays routine should not include Saturday or Sunday.")
    if freq == "Monthly" and valid_days:
        problems.append("Monthly routines currently export most reliably when preferred days are blank and a next due date is set.")
    return problems

def truthy_flag(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "checked"}


def parse_online_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(text, fmt).date()
        except Exception:
            pass
    try:
        return pd.to_datetime(text).date()
    except Exception:
        return None


def parse_online_time(value: Any, default: str = "09:00") -> time:
    text = str(value or default).strip().lower().replace(".", ":")
    for suffix in ["am", "pm"]:
        if text.endswith(suffix):
            raw = text[:-2].strip()
            try:
                hour, minute = (raw.split(":") + ["0"])[:2]
                h = int(hour); m = int(minute)
                if suffix == "pm" and h != 12:
                    h += 12
                if suffix == "am" and h == 12:
                    h = 0
                return time(h, m)
            except Exception:
                break
    try:
        hour, minute = (text.split(":") + ["0"])[:2]
        return time(int(hour), int(minute))
    except Exception:
        h, m = default.split(":")[:2]
        return time(int(h), int(m))


def valid_online_date(value: Any, *, allow_blank: bool = True) -> bool:
    text = str(value or "").strip()
    if not text:
        return allow_blank
    return parse_online_date(text) is not None


def normalise_online_date(value: Any) -> str:
    d = parse_online_date(value)
    return d.isoformat() if d else str(value or "").strip()


def valid_online_time(value: Any, *, allow_blank: bool = True) -> bool:
    text = str(value or "").strip()
    if not text:
        return allow_blank
    try:
        parse_online_time(text)
        return True
    except Exception:
        return False


def time_to_text(value: time | None) -> str:
    if value is None:
        return ""
    return f"{value.hour:02d}:{value.minute:02d}"


def calculated_end_time(start_text: Any, minutes: int | float | str | None, *, fallback: str = "10:00") -> str:
    """Calculate a calendar end time from a start time and duration.

    The UI asks users for start time + duration rather than start + end, because
    that is easier to understand and prevents accidental entries such as
    22:30 to 06:30 when the user meant a short evening routine. Overnight
    blocks can still be created by editing exported rows if that is deliberately
    needed later.
    """
    try:
        start_t = parse_online_time(start_text, "09:00")
    except Exception:
        start_t = parse_online_time(fallback, "10:00")
    try:
        mins = int(float(str(minutes or 0)))
    except Exception:
        mins = 0
    if mins <= 0:
        mins = 30
    base = datetime.combine(date.today(), start_t)
    return (base + timedelta(minutes=mins)).strftime("%H:%M")



def validate_online_action_dates_and_times(*, scheduled: str = "", due: str = "", start_time: str = "", end_time: str = "", prompt_time: str = "") -> list[str]:
    problems: list[str] = []
    if not valid_online_date(scheduled):
        problems.append("Scheduled date must be blank or a real date. Use DD-MM-YYYY, for example 08-06-2026.")
    if not valid_online_date(due):
        problems.append("Due date must be blank or a real date. Use DD-MM-YYYY, for example 08-06-2026.")
    for label, value in [("Calendar start time", start_time), ("Calendar end time", end_time), ("Prompt reference time", prompt_time)]:
        if not valid_online_time(value):
            problems.append(f"{label} must be blank or a real time, for example 09:00 or 7:30pm.")
    return problems


def online_event_bounds(date_text: Any, start_text: Any, end_text: Any) -> tuple[str, str]:
    d = parse_online_date(date_text) or (date.today() + timedelta(days=1))
    start_t = parse_online_time(start_text, "09:00")
    end_t = parse_online_time(end_text, "10:00")
    start_dt = datetime.combine(d, start_t)
    end_dt = datetime.combine(d, end_t)
    raw_end = str(end_text or "").strip().lower()
    if end_dt <= start_dt and ("am" not in raw_end and "pm" not in raw_end) and 1 <= end_t.hour <= 7:
        end_dt = datetime.combine(d, time(end_t.hour + 12, end_t.minute))
    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(hours=1)
    return start_dt.strftime("%Y-%m-%d %H:%M"), end_dt.strftime("%Y-%m-%d %H:%M")




def human_calendar_datetime(value: Any) -> str:
    """Return a friendly NZ-style date/time label for staged calendar rows.

    Staged calendar rows are stored internally in export-friendly formats such
    as ``YYYY-MM-DD HH:MM``. This helper keeps the UI preview readable and,
    importantly, prevents raw export values or helper errors from appearing in
    the Streamlit interface.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    normalised = text.replace("T", " ").replace("Z", "").strip()
    normalised = re.sub(r"([+-]\d{2}:?\d{2})$", "", normalised).strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]
    dt: datetime | None = None
    for fmt in formats:
        try:
            dt = datetime.strptime(normalised, fmt)
            break
        except Exception:
            pass
    if dt is None:
        try:
            parsed = pd.to_datetime(text, errors="coerce")
            if pd.notna(parsed):
                dt = parsed.to_pydatetime()
        except Exception:
            dt = None
    if dt is None:
        return text
    has_time = bool(re.search(r"\d{1,2}:\d{2}", text))
    try:
        date_part = dt.strftime("%A %-d %B %Y")
    except Exception:
        date_part = dt.strftime("%A %d %B %Y").replace(" 0", " ")
    if not has_time:
        return date_part
    try:
        time_part = dt.strftime("%-I:%M%p").lower()
    except Exception:
        time_part = dt.strftime("%I:%M%p").lstrip("0").lower()
    return f"{date_part}, {time_part}"


def simple_rrule(frequency: str | None, activity_days: str | None = "") -> str:
    freq = str(frequency or "").strip()
    days = str(activity_days or "").strip()
    day_map = {"monday":"MO","tuesday":"TU","wednesday":"WE","thursday":"TH","friday":"FR","saturday":"SA","sunday":"SU"}
    bydays = []
    day_source = days or freq
    for name, code in day_map.items():
        if name in day_source.lower():
            bydays.append(code)
    if freq.lower() == "daily":
        return "RRULE:FREQ=DAILY"
    if freq.lower() == "weekdays":
        return "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    if "week" in freq.lower() or bydays:
        return "RRULE:FREQ=WEEKLY" + (f";BYDAY={','.join(bydays)}" if bydays else "")
    if "month" in freq.lower():
        return "RRULE:FREQ=MONTHLY"
    return ""


def human_recurrence(value: Any) -> str:
    """Convert an export RRULE into plain English for preview cards.

    The stored recurrence value is kept in Google Calendar-compatible format;
    this helper is used only for user-facing previews.
    """
    text = str(value or "").strip()
    if not text:
        return ""
    rule = text.replace("RRULE:", "").strip()
    parts: dict[str, str] = {}
    for chunk in rule.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
            parts[key.upper().strip()] = val.strip()
    freq = parts.get("FREQ", "").upper()
    day_names = {
        "MO": "Monday", "TU": "Tuesday", "WE": "Wednesday", "TH": "Thursday",
        "FR": "Friday", "SA": "Saturday", "SU": "Sunday",
    }
    byday_codes = [code.strip().upper() for code in parts.get("BYDAY", "").split(",") if code.strip()]
    days = [day_names.get(code, code) for code in byday_codes]

    def join_days(items: list[str]) -> str:
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f" and {items[-1]}"

    if freq == "DAILY":
        return "Repeats every day"
    if freq == "WEEKLY":
        if days:
            if byday_codes == ["MO", "TU", "WE", "TH", "FR"]:
                return "Repeats every weekday"
            return f"Repeats weekly on {join_days(days)}"
        return "Repeats weekly"
    if freq == "MONTHLY":
        return "Repeats monthly"
    if freq == "YEARLY":
        return "Repeats yearly"
    return rule


def parent_lookup(sheet_id: str) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    goals = read_online_table(sheet_id, "goals")
    routines = read_online_table(sheet_id, "routines")
    goal_lookup = {str(r.get("goal_id", "")): {k: str(r.get(k, "") or "") for k in goals.columns} for _, r in goals.iterrows()}
    routine_lookup = {str(r.get("routine_id", "")): {k: str(r.get(k, "") or "") for k in routines.columns} for _, r in routines.iterrows()}
    return goal_lookup, routine_lookup


def staged_calendar_blocks(sheet_id: str) -> pd.DataFrame:
    actions = read_online_table(sheet_id, "actions")
    if actions.empty:
        return pd.DataFrame(columns=["block_id", "area_name", "title", "description", "start", "end", "recurrence", "linked_record_id", "status"])
    goals, routines = parent_lookup(sheet_id)
    rows = []
    for _, action in actions.iterrows():
        if not truthy_flag(action.get("calendar_block")):
            continue
        if str(action.get("status", "")).lower() in {"done", "paused"}:
            continue
        aid = str(action.get("action_id", "") or uuid.uuid4().hex)
        goal_id = str(action.get("goal_id", "") or "")
        routine_id = str(action.get("routine_id", "") or "")
        routine = routines.get(routine_id, {})
        if str(routine.get("status", "")).lower() == "paused":
            continue
        base_date = action.get("scheduled_date") or action.get("due_date") or routine.get("next_due") or ""
        start, end = online_event_bounds(base_date, action.get("calendar_start_time") or routine.get("calendar_start_time") or "09:00", action.get("calendar_end_time") or routine.get("calendar_end_time") or "10:00")
        recurrence = simple_rrule(routine.get("frequency"), action.get("activity_days")) if routine_id else ""
        routine_parent = routines.get(routine_id, {})
        if str(routine_parent.get("status", "")).lower() == "paused":
            continue
        parent = routine_parent.get("title") or goals.get(goal_id, {}).get("title") or ""
        desc_parts = [f"Routine: {parent}" if routine_id and parent else f"Goal: {parent}" if goal_id and parent else "", str(action.get("notes") or action.get("description") or "")]
        rows.append({
            "block_id": f"block-{aid}",
            "area_name": action.get("area_name", "") or routine.get("area_name", "") or goals.get(goal_id, {}).get("area_name", ""),
            "title": action.get("title", "") or "Pathmark block",
            "description": "\n\n".join([p for p in desc_parts if p]),
            "start": start,
            "end": end,
            "recurrence": recurrence,
            "linked_record_id": aid,
            "status": "Staged",
            "created_at": action.get("created_at", ""),
            "updated_at": action.get("updated_at", ""),
            "source": "derived_from_action",
        })
    return pd.DataFrame(rows)


def linked_calendar_summary_for_action(row: pd.Series, blocks: pd.DataFrame) -> str:
    aid = str(row.get("action_id", "") or "")
    if blocks.empty or not aid:
        return ""
    matches = blocks[blocks["linked_record_id"].fillna("") == aid]
    if matches.empty:
        return ""
    block = matches.iloc[0]
    return f"Related Google Calendar item: {block.get('title','Calendar time')} ({block.get('start','')})"


def staged_task_prompts(sheet_id: str) -> pd.DataFrame:
    actions = read_online_table(sheet_id, "actions")
    if actions.empty:
        return pd.DataFrame(columns=["id", "title", "area_name", "due_date", "reminder_time", "task_list", "notes", "repeat_pattern", "linked_calendar_summary"])
    goals, routines = parent_lookup(sheet_id)
    blocks = staged_calendar_blocks(sheet_id)
    rows = []
    for _, action in actions.iterrows():
        if not truthy_flag(action.get("reminder")):
            continue
        if str(action.get("status", "")).lower() in {"done", "paused"}:
            continue
        aid = str(action.get("action_id", "") or uuid.uuid4().hex)
        goal_id = str(action.get("goal_id", "") or "")
        routine_id = str(action.get("routine_id", "") or "")
        routine = routines.get(routine_id, {})
        if str(routine.get("status", "")).lower() == "paused":
            continue
        goal = goals.get(goal_id, {})
        area_name = action.get("area_name", "") or routine.get("area_name", "") or goal.get("area_name", "")
        defaults = area_defaults(sheet_id, str(area_name))
        first = str(action.get("first_step", "") or "").strip() or str(action.get("title", "") or "Pathmark task").strip()
        parent = routine.get("title") or goal.get("title") or ""
        base_note = str(action.get("notes") or action.get("description") or "")
        repeat = routine.get("frequency", "") if routine_id else ""
        linked = linked_calendar_summary_for_action(action, blocks)
        note_parts = [f"Routine: {parent}" if routine_id and parent else f"Goal: {parent}" if goal_id and parent else "", base_note, f"Repeat pattern: {repeat}." if repeat else "", f"Reference time: {action.get('task_reminder_time') or action.get('calendar_start_time') or routine.get('task_reminder_time')}." if (action.get('task_reminder_time') or action.get('calendar_start_time') or routine.get('task_reminder_time')) else "", linked]
        rows.append({
            "id": aid,
            "title": first,
            "area_name": area_name,
            "parent": parent,
            "due_date": action.get("scheduled_date") or action.get("due_date") or routine.get("next_due") or "",
            "reminder_time": action.get("task_reminder_time") or action.get("calendar_start_time") or routine.get("task_reminder_time") or "",
            "task_list": defaults.get("default_task_list") or area_name or "Pathmark",
            "notes": "\n\n".join([p for p in note_parts if str(p).strip()]),
            "repeat_pattern": repeat,
            "linked_calendar_summary": linked,
            "status": "needsAction",
        })
    return pd.DataFrame(rows)


def staged_tasklist(sheet_id: str) -> pd.DataFrame:
    actions = read_online_table(sheet_id, "actions")
    if actions.empty:
        return pd.DataFrame(columns=["action_id", "source_type", "title", "area_name", "parent", "status", "scheduled_date", "due_date", "first_step", "estimated_minutes"])
    goals, routines = parent_lookup(sheet_id)
    rows = []
    for _, action in actions.iterrows():
        if not truthy_flag(action.get("include_tasklist", "1")):
            continue
        status = str(action.get("status", "") or "").strip()
        if status.lower() in {"done", "paused"}:
            continue
        goal_id = str(action.get("goal_id", "") or "")
        routine_id = str(action.get("routine_id", "") or "")
        routine_parent = routines.get(routine_id, {})
        if str(routine_parent.get("status", "")).lower() == "paused":
            continue
        parent = routine_parent.get("title") or goals.get(goal_id, {}).get("title") or ""
        rows.append({
            "action_id": action.get("action_id", ""),
            "source_type": "Routine activity" if routine_id else "Goal action",
            "title": action.get("title", ""),
            "area_name": action.get("area_name", "") or routines.get(routine_id, {}).get("area_name", "") or goals.get(goal_id, {}).get("area_name", ""),
            "parent": parent,
            "status": status or ("Included" if routine_id else "Planned"),
            "scheduled_date": action.get("scheduled_date", ""),
            "due_date": action.get("due_date", ""),
            "first_step": action.get("first_step", ""),
            "estimated_minutes": action.get("estimated_minutes", ""),
            "priority": action.get("priority", ""),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["sort_status"] = df["status"].map({"Next": 1, "Scheduled": 2, "Planned": 3, "Included": 4}).fillna(5)
        df = df.sort_values(["source_type", "sort_status", "scheduled_date", "due_date", "title"], na_position="last").drop(columns=["sort_status"])
    return df.reset_index(drop=True)




def next_weekday_iso(day_name: str, *, include_today: bool = False) -> str:
    day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    target = day_map.get(str(day_name).strip().lower(), date.today().weekday())
    today = date.today()
    delta = (target - today.weekday()) % 7
    if delta == 0 and not include_today:
        delta = 7
    return (today + timedelta(days=delta)).isoformat()


def starter_examples_already_loaded(sheet_id: str) -> bool:
    settings = read_online_table(sheet_id, "settings") if sheet_id else pd.DataFrame()
    if settings.empty:
        return False
    loaded = settings[
        settings.get("key", pd.Series(dtype=str)).fillna("").astype(str).eq("starter_examples_loaded")
    ]
    return not loaded.empty and str(loaded.iloc[-1].get("value", "")).strip().lower() in {"yes", "true", "1"}


def build_starter_example_records() -> dict[str, list[dict[str, Any]]]:
    """Editable starter records modelled on the desktop starter-data approach.

    These are deliberately ordinary examples: food, sleep, exercise, admin and
    learning. They guide a new user without requiring everyone to keep the same
    routines or goals.
    """
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    area_body = f"area-{uuid.uuid4().hex}"
    area_food = f"area-{uuid.uuid4().hex}"
    area_admin = f"area-{uuid.uuid4().hex}"
    area_learning = f"area-{uuid.uuid4().hex}"
    areas = [
        {"area_id": area_body, "area_name": "Body And Stability", "description": "Sleep, movement, strength, mobility, health appointments and routines that support energy.", "colour": "sage", "status": "active", "default_calendar": "Body And Stability", "default_task_list": "Pathmark", "notes": "Starter Area. Edit, rename or archive if it does not fit."},
        {"area_id": area_food, "area_name": "Food And Home", "description": "Meals, groceries, household reset, cleaning and the routines that make home life easier.", "colour": "ochre", "status": "active", "default_calendar": "Food And Home", "default_task_list": "Pathmark", "notes": "Starter Area. Edit, rename or archive if it does not fit."},
        {"area_id": area_admin, "area_name": "Work And Admin", "description": "Planning, errands, paperwork, money, work tasks and weekly review.", "colour": "blue", "status": "active", "default_calendar": "Work And Admin", "default_task_list": "Pathmark", "notes": "Starter Area. Edit, rename or archive if it does not fit."},
        {"area_id": area_learning, "area_name": "Learning And Creativity", "description": "Creative practice, study, music, sketching and personal projects.", "colour": "plum", "status": "active", "default_calendar": "Learning And Creativity", "default_task_list": "Pathmark", "notes": "Starter Area. Edit, rename or archive if it does not fit."},
    ]

    def routine(title: str, area_id: str, area_name: str, purpose: str, frequency: str, preferred_days: str, next_due: str, checklist: str = "") -> dict[str, Any]:
        return {"routine_id": f"routine-{uuid.uuid4().hex}", "area_id": area_id, "area_name": area_name, "title": title, "description": purpose, "frequency": frequency, "preferred_days": preferred_days, "duration_minutes": "", "status": "Active", "purpose": purpose, "next_due": next_due, "checklist": checklist, "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."}

    sleep_id = f"routine-{uuid.uuid4().hex}"
    cook_weeknight_id = f"routine-{uuid.uuid4().hex}"
    friday_takeaways_id = f"routine-{uuid.uuid4().hex}"
    sunday_meal_id = f"routine-{uuid.uuid4().hex}"
    strength_id = f"routine-{uuid.uuid4().hex}"
    violin_id = f"routine-{uuid.uuid4().hex}"
    running_id = f"routine-{uuid.uuid4().hex}"
    routines = [
        {"routine_id": sleep_id, "area_id": area_body, "area_name": "Body And Stability", "title": "Protect an 8-hour sleep block", "description": "Give tomorrow a better starting point by protecting enough time for sleep.", "frequency": "Daily", "preferred_days": "Every day", "duration_minutes": "480", "status": "Active", "purpose": "Protect sleep before adding more work to the system.", "next_due": date.today().isoformat(), "checklist": "Set wind-down time\nPut phone away\nPrepare tomorrow's first action", "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."},
        {"routine_id": cook_weeknight_id, "area_id": area_food, "area_name": "Food And Home", "title": "Cook weeknight dinner", "description": "Prepare simple dinners on planned weeknights so food choices are easier.", "frequency": "Weekly", "preferred_days": "Monday, Wednesday", "duration_minutes": "45", "status": "Active", "purpose": "Make ordinary meals easier to start after work.", "next_due": next_weekday_iso("Monday"), "checklist": "Choose meal\nCheck ingredients\nCook and clean down", "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."},
        {"routine_id": friday_takeaways_id, "area_id": area_food, "area_name": "Food And Home", "title": "Friday takeaway dinner", "description": "A deliberately planned low-effort meal slot rather than an accidental fallback.", "frequency": "Weekly", "preferred_days": "Friday", "duration_minutes": "30", "status": "Active", "purpose": "Give the week a simple food decision and avoid over-planning every evening.", "next_due": next_weekday_iso("Friday"), "checklist": "Choose option\nOrder or collect\nReset kitchen afterwards", "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."},
        {"routine_id": sunday_meal_id, "area_id": area_food, "area_name": "Food And Home", "title": "Cook weekend meal", "description": "Cook a more relaxed weekend meal and optionally prepare leftovers.", "frequency": "Weekly", "preferred_days": "Sunday", "duration_minutes": "90", "status": "Active", "purpose": "Create a slower food routine that supports the coming week.", "next_due": next_weekday_iso("Sunday"), "checklist": "Choose recipe\nShop ingredients\nCook\nPack leftovers", "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."},
        {"routine_id": strength_id, "area_id": area_body, "area_name": "Body And Stability", "title": "Strength training", "description": "A four-session weekly strength routine split into A, B, C and D activities.", "frequency": "Weekly", "preferred_days": "Monday, Tuesday, Thursday, Friday", "duration_minutes": "45", "status": "Active", "purpose": "Keep strength work visible and repeatable.", "next_due": next_weekday_iso("Monday"), "checklist": "Warm up\nMain lift\nAccessory work\nLog session", "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."},
        {"routine_id": violin_id, "area_id": area_learning, "area_name": "Learning And Creativity", "title": "Practice violin", "description": "A weekly creative practice block.", "frequency": "Weekly", "preferred_days": "Wednesday", "duration_minutes": "45", "status": "Active", "purpose": "Keep creative practice scheduled rather than only aspirational.", "next_due": next_weekday_iso("Wednesday"), "checklist": "Tune\nScales\nPiece work\nNote next focus", "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."},
        {"routine_id": running_id, "area_id": area_body, "area_name": "Body And Stability", "title": "Run 30 minutes", "description": "A weekday running habit that can be reduced or paused if recovery needs it.", "frequency": "Weekdays", "preferred_days": "Monday, Tuesday, Wednesday, Thursday, Friday", "duration_minutes": "30", "status": "Active", "purpose": "Make regular cardiovascular work easy to see in the calendar.", "next_due": next_weekday_iso("Monday"), "checklist": "Shoes ready\nEasy pace\nLog how it felt", "notes": "Starter routine. Edit, pause, retire or archive if it does not fit."},
    ]

    def activity(routine_id: str, area_id: str, area_name: str, title: str, day: str, start: str, end: str, minutes: str, first_step: str, location: str = "") -> dict[str, Any]:
        return {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": "", "routine_id": routine_id, "area_id": area_id, "area_name": area_name, "title": title, "description": "Starter routine activity. Edit the day, time and prompt to suit you.", "status": "Included", "priority": "Medium", "specific_area": "", "due_date": "", "scheduled_date": "", "activity_days": day, "estimated_minutes": minutes, "calendar_block": "1", "reminder": "1", "include_tasklist": "1", "first_step": first_step, "task_reminder_time": start, "calendar_start_time": start, "calendar_end_time": end, "calendar_location": location, "notes": "Starter routine activity."}

    actions = [
        activity(sleep_id, area_body, "Body And Stability", "Sleep block", "Every day", "22:30", "06:30", "480", "Start wind-down routine"),
        activity(cook_weeknight_id, area_food, "Food And Home", "Cook weeknight dinner", "Monday, Wednesday", "18:00", "18:45", "45", "Open the meal plan and start the first prep step"),
        activity(friday_takeaways_id, area_food, "Food And Home", "Takeaway dinner", "Friday", "18:30", "19:00", "30", "Choose takeaway option"),
        activity(sunday_meal_id, area_food, "Food And Home", "Cook weekend meal", "Sunday", "17:00", "18:30", "90", "Open the recipe and check ingredients"),
        activity(strength_id, area_body, "Body And Stability", "Strength training A", "Monday", "07:00", "07:45", "45", "Start warm-up for strength A"),
        activity(strength_id, area_body, "Body And Stability", "Strength training B", "Tuesday", "07:00", "07:45", "45", "Start warm-up for strength B"),
        activity(strength_id, area_body, "Body And Stability", "Strength training C", "Thursday", "07:00", "07:45", "45", "Start warm-up for strength C"),
        activity(strength_id, area_body, "Body And Stability", "Strength training D", "Friday", "07:00", "07:45", "45", "Start warm-up for strength D"),
        activity(violin_id, area_learning, "Learning And Creativity", "Practice violin", "Wednesday", "19:00", "19:45", "45", "Tune violin and start with scales"),
        activity(running_id, area_body, "Body And Stability", "Run 30 minutes", "Monday, Tuesday, Wednesday, Thursday, Friday", "17:30", "18:00", "30", "Put on running shoes and start easy"),
    ]

    sketch_goal = f"goal-{uuid.uuid4().hex}"
    run_goal = f"goal-{uuid.uuid4().hex}"
    goals = [
        {"goal_id": sketch_goal, "area_id": area_learning, "area_name": "Learning And Creativity", "title": "Learn to sketch", "description": "Build enough basic skill to sketch simple forms confidently.", "specific_area": "Sketching", "status": "Captured", "target_date": "", "purpose": "Create a small creative learning project with clear first actions.", "desired_outcome": "Complete a few beginner sketching exercises and keep the materials ready.", "closure_criteria": "A beginner guide has been started and at least three sketches have been completed.", "notes": "Starter goal. Edit, archive or replace if it does not fit."},
        {"goal_id": run_goal, "area_id": area_body, "area_name": "Body And Stability", "title": "Build running distance", "description": "Increase distance gradually while keeping the next step clear.", "specific_area": "Running", "status": "Captured", "target_date": "", "purpose": "Turn a broad running ambition into visible next actions.", "desired_outcome": "Run 6.5 km comfortably enough to plan the next distance step.", "closure_criteria": "6.5 km run completed and next distance goal chosen.", "notes": "Starter goal. Edit, archive or replace if it does not fit."},
    ]
    actions.extend([
        {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": sketch_goal, "routine_id": "", "area_id": area_learning, "area_name": "Learning And Creativity", "title": "Purchase beginner sketching guide", "description": "Find and purchase a beginner-friendly sketching guide.", "status": "Next", "priority": "Medium", "specific_area": "Sketching", "due_date": "", "scheduled_date": "", "activity_days": "", "estimated_minutes": "30", "calendar_block": "0", "reminder": "1", "include_tasklist": "1", "first_step": "Search for one beginner sketching guide", "task_reminder_time": "09:00", "calendar_start_time": "09:00", "calendar_end_time": "09:30", "calendar_location": "", "notes": "Starter action."},
        {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": sketch_goal, "routine_id": "", "area_id": area_learning, "area_name": "Learning And Creativity", "title": "Purchase sketching materials", "description": "Buy a simple sketchbook, pencils and eraser.", "status": "Planned", "priority": "Medium", "specific_area": "Sketching", "due_date": "", "scheduled_date": "", "activity_days": "", "estimated_minutes": "30", "calendar_block": "0", "reminder": "1", "include_tasklist": "1", "first_step": "Choose a sketchbook and pencil set", "task_reminder_time": "09:00", "calendar_start_time": "09:00", "calendar_end_time": "09:30", "calendar_location": "", "notes": "Starter action."},
        {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": run_goal, "routine_id": "", "area_id": area_body, "area_name": "Body And Stability", "title": "Run 6 km", "description": "Complete one steady 6 km run.", "status": "Next", "priority": "Medium", "specific_area": "Running", "due_date": "", "scheduled_date": "", "activity_days": "", "estimated_minutes": "45", "calendar_block": "1", "reminder": "1", "include_tasklist": "1", "first_step": "Choose the 6 km route", "task_reminder_time": "09:00", "calendar_start_time": "09:00", "calendar_end_time": "09:45", "calendar_location": "", "notes": "Starter action."},
        {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": run_goal, "routine_id": "", "area_id": area_body, "area_name": "Body And Stability", "title": "Run 6.5 km", "description": "Complete one steady 6.5 km run after the 6 km action is done.", "status": "Planned", "priority": "Medium", "specific_area": "Running", "due_date": "", "scheduled_date": "", "activity_days": "", "estimated_minutes": "50", "calendar_block": "1", "reminder": "1", "include_tasklist": "1", "first_step": "Choose the 6.5 km route", "task_reminder_time": "09:00", "calendar_start_time": "09:00", "calendar_end_time": "09:50", "calendar_location": "", "notes": "Starter action."},
    ])

    settings = [{"key": "starter_examples_loaded", "value": "yes", "updated_at": now, "source": "Pathmark Online starter examples"}]
    return {"settings": settings, "areas": areas, "goals": goals, "routines": routines, "actions": actions}


def load_starter_examples(sheet_id: str) -> tuple[bool, str]:
    if starter_examples_already_loaded(sheet_id):
        return False, "Starter examples have already been loaded for this sync sheet. Edit or archive the existing examples instead of loading duplicates."
    return append_many_online_records(sheet_id, build_starter_example_records())


def render_area_manager(sheet_id: str) -> None:
    st.subheader("Areas")
    st.markdown("""
    <div class='guide-box'><strong>Areas become your Google subcalendars.</strong><br>
    Create broad Areas such as Body and Stability, Food and Home, Work and Admin, or Learning and Creativity. Pathmark uses each Area to group related routines and goals, and to keep calendar exports visually organised.</div>
    """, unsafe_allow_html=True)
    df = active_online_df(read_online_table(sheet_id, "areas"))
    col_list, col_main = st.columns([0.34, 0.66])
    with col_list:
        st.markdown("### Areas")
        if df.empty:
            st.info("No Areas yet.")
            selected_id = ""
        else:
            labels = {f"{row.get('area_name','Untitled')} ({row.get('status','active')})": str(row.get("area_id", "")) for _, row in df.iterrows()}
            selected_label = st.radio("Select an Area", list(labels.keys()), label_visibility="collapsed", key="online_area_select")
            selected_id = labels.get(selected_label, "")
        with st.expander("Add Area", expanded=df.empty):
            st.caption("Examples are prompts only. Save the Area when it matches your life.")
            name = st.text_input("Area name", key="add_area_name", placeholder="For example, Body and Stability")
            description = st.text_area("Description", key="add_area_description", height=90, placeholder="Sleep, movement, strength, mobility and health routines.")
            colour_label = st.selectbox("Google Calendar colour", GOOGLE_COLOUR_LABELS, index=0, key="add_area_colour", help="Choose the colour Pathmark should use for this Area in Google Calendar exports.")
            render_google_colour_swatch(colour_label)
            colour = google_colour_code(colour_label)
            default_calendar = st.text_input("Default Google Calendar", key="add_area_calendar", placeholder="Usually the Area name")
            default_task_list = st.text_input("Default Google Tasks list", key="add_area_task_list", placeholder="Usually Pathmark or the Area name")
            notes = st.text_area("Notes", key="add_area_notes", height=70)
            if st.button("Save Area", use_container_width=True, key="add_area_save"):
                if not name.strip():
                    st.error("Add an Area name before saving.")
                else:
                    ok, message = append_online_record(sheet_id, "areas", {
                        "area_id": f"area-{uuid.uuid4().hex}",
                        "area_name": name.strip(),
                        "description": description.strip(),
                        "colour": colour,
                        "default_calendar": default_calendar.strip() or name.strip(),
                        "default_task_list": default_task_list.strip() or "Pathmark",
                        "notes": notes.strip(),
                    })
                    st.success(message) if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
    with col_main:
        if selected_id:
            row = df[df["area_id"] == selected_id].iloc[0].to_dict()
            st.markdown(f"### {row.get('area_name','Area')}")
            name = st.text_input("Area name", value=str(row.get("area_name", "")), key=f"edit_area_name_{selected_id}")
            description = st.text_area("Description", value=str(row.get("description", "")), height=100, key=f"edit_area_description_{selected_id}")
            current_colour = google_colour_label(str(row.get("colour", "")))
            colour_label = st.selectbox("Google Calendar colour", GOOGLE_COLOUR_LABELS, index=GOOGLE_COLOUR_LABELS.index(current_colour) if current_colour in GOOGLE_COLOUR_LABELS else 0, key=f"edit_area_colour_{selected_id}")
            render_google_colour_swatch(colour_label)
            colour = google_colour_code(colour_label)
            default_calendar = st.text_input("Default Google Calendar", value=str(row.get("default_calendar", "")), key=f"edit_area_calendar_{selected_id}")
            default_task_list = st.text_input("Default Google Tasks list", value=str(row.get("default_task_list", "")), key=f"edit_area_task_list_{selected_id}")
            notes = st.text_area("Notes", value=str(row.get("notes", "")), height=90, key=f"edit_area_notes_{selected_id}")
            if st.button("Save changes", use_container_width=True, key=f"edit_area_save_{selected_id}"):
                if not name.strip():
                    st.error("Add an Area name before saving.")
                else:
                    ok, message = update_online_record(sheet_id, "areas", selected_id, {
                        "area_name": name.strip(), "description": description.strip(), "colour": colour,
                        "default_calendar": default_calendar.strip(), "default_task_list": default_task_list.strip(), "notes": notes.strip(), "status": row.get("status", "active") or "active"
                    })
                    st.success(message) if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
            if st.button("Archive Area", key=f"archive_area_{selected_id}"):
                ok, message = archive_online_record(sheet_id, "areas", selected_id, "Archived from Pathmark Online.")
                st.success(message) if ok else st.warning(safe_user_message(message))
                if ok:
                    st.rerun()


def _render_action_list(sheet_id: str, linked: pd.DataFrame, *, goal_id: str = "", routine_id: str = "", default_area: str = "") -> None:
    """Render saved goal activities or routine activities in a user-facing way.

    Earlier releases called this helper from Goals and Routines but did not
    include the implementation, which meant those tabs could fail as soon as a
    goal or routine was selected. Keep this renderer intentionally simple and
    robust: cards first, technical details hidden, edit form only when expanded.
    """
    kind = "routine activities" if routine_id else "goal activities"
    if linked is None or linked.empty:
        st.info(f"No {kind} yet. Add one below when you are ready.")
        return

    st.markdown(f"#### Saved {kind}")
    for _, row in linked.iterrows():
        data = {k: row.get(k, "") for k in linked.columns}
        rid = str(data.get("action_id", "") or "")
        title = str(data.get("title", "") or "Untitled activity")
        outputs: list[str] = []
        if truthy_flag(data.get("include_tasklist", "0")):
            outputs.append("weekly tasklist")
        if truthy_flag(data.get("calendar_block", "0")):
            outputs.append("Calendar block")
        if truthy_flag(data.get("reminder", "0")):
            outputs.append("Google Tasks prompt")
        output_text = ", ".join(outputs) if outputs else "not staged for export yet"
        date_bits: list[str] = []
        if str(data.get("scheduled_date", "") or "").strip():
            date_bits.append(f"Calendar: {human_calendar_datetime(data.get('scheduled_date'))}")
        if str(data.get("due_date", "") or "").strip():
            date_bits.append(f"Task due: {human_calendar_datetime(data.get('due_date'))}")
        if str(data.get("activity_days", "") or "").strip():
            date_bits.append(f"Repeats on {data.get('activity_days')}")
        detail = " · ".join(date_bits)
        st.markdown(
            f"""
            <div class='step-card'>
              <h3>{html.escape(title)}</h3>
              <p>{html.escape(output_text)}</p>
              <p>{html.escape(detail)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"Edit {title}", expanded=False):
            _action_form(
                sheet_id,
                goal_id=goal_id or str(data.get("goal_id", "") or ""),
                routine_id=routine_id or str(data.get("routine_id", "") or ""),
                default_area=default_area or str(data.get("area_name", "") or ""),
                form_key=f"edit_action_{rid or uuid.uuid4().hex}",
                action=data,
            )
            if rid:
                if st.button("Move this activity to Archive", key=f"archive_action_{rid}", use_container_width=True):
                    ok, message = archive_online_record(sheet_id, "actions", rid, "Archived from Pathmark Online.")
                    st.success("Activity archived. You can restore it from Archive.") if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()

def _action_form(sheet_id: str, *, goal_id: str = "", routine_id: str = "", default_area: str = "", form_key: str = "action", action: dict[str, Any] | None = None) -> None:
    """Add or edit a goal activity or routine activity.

    The form is deliberately staged so the user first describes the activity,
    then chooses where it should appear, then completes only the fields needed
    for those selected outputs.
    """
    area_id = find_area_id(sheet_id, default_area) if default_area else ""
    is_routine_activity = bool(routine_id)
    action = action or {}
    record_id = str(action.get("action_id", "") or "")
    title_word = "Routine activity" if is_routine_activity else "Goal activity"
    form_id = f"online_{'edit' if record_id else 'add'}_{form_key}_{record_id or 'new'}"

    current_minutes = 30
    try:
        current_minutes = int(float(str(action.get("estimated_minutes", "30") or 30)))
    except Exception:
        current_minutes = 30
    if current_minutes <= 0:
        current_minutes = 30

    with st.form(form_id, clear_on_submit=not bool(record_id)):
        st.markdown(f"### {'Edit' if record_id else 'Add'} {title_word.lower()}")
        if is_routine_activity:
            st.caption("This is the activity inside the routine. The routine is the container; this row is what can appear on your tasklist, calendar export, and Google Tasks export.")
        else:
            st.caption("Goal activities are usually one-off next steps. If the work repeats, create it as a routine activity instead.")

        st.markdown("#### 1. What is the activity?")
        title = st.text_input("Activity title", value=str(action.get("title", "")), placeholder="For example, Wind-down routine, Strength training A, or Buy sketchbook")
        description = st.text_area("Notes / description", value=str(action.get("description", action.get("notes", "")) or ""), height=80, placeholder="Optional context, checklist notes, or what 'done' looks like.")

        c1, c2, c3 = st.columns([0.34, 0.33, 0.33])
        status_options = ["Next", "Scheduled", "Planned", "Waiting", "Done"] if not is_routine_activity else ["Included", "Paused", "Done"]
        current_status = str(action.get("status", status_options[0]) or status_options[0])
        status = c1.selectbox("Status", status_options, index=status_options.index(current_status) if current_status in status_options else 0)
        priority_options = ["High", "Medium", "Low"]
        current_priority = str(action.get("priority", "Medium") or "Medium")
        priority = c2.selectbox("Priority", priority_options, index=priority_options.index(current_priority) if current_priority in priority_options else 1)
        minutes = c3.number_input("Duration / effort", min_value=5, step=5, value=current_minutes, help="Used to calculate the calendar end time and to show the effort on the tasklist.")

        st.markdown("#### 2. When does it happen?")
        c4, c5 = st.columns(2)
        scheduled = c4.text_input("Calendar date", value=str(action.get("scheduled_date", "") or ""), placeholder="DD-MM-YYYY or YYYY-MM-DD", help="Used only when a Calendar block is created. For repeating routine activities, this is the first date.")
        due = c5.text_input("Google Tasks due date", value=str(action.get("due_date", "") or ""), placeholder="DD-MM-YYYY or YYYY-MM-DD", help="Used only when a Google Tasks prompt is created. Google Tasks receives a date, not a duration.")

        activity_days = ""
        if is_routine_activity:
            current_activity_days, _bad_activity_days = parse_days_text(str(action.get("activity_days", "")))
            selected_activity_days = st.multiselect(
                "Repeat on these days",
                VALID_DAYS,
                default=current_activity_days,
                help="Used for recurring Calendar blocks and date-based Google Tasks prompts. Leave blank only if this activity does not repeat on selected weekdays.",
            )
            activity_days = ", ".join(selected_activity_days)

        st.markdown("#### 3. Choose where Pathmark should put it")
        st.markdown("""
        <div class='pathmark-note'>
        <strong>Calendar block</strong> creates scheduled time with a start, calculated end, duration and repeat pattern.<br>
        <strong>Weekly tasklist</strong> prints the activity so you can tick it off by hand.<br>
        <strong>Google Tasks prompt</strong> creates a date-based first step. Google Tasks does not preserve duration or scheduled time, so time-blocked work belongs in Calendar.
        </div>
        """, unsafe_allow_html=True)
        c6, c7, c8 = st.columns(3)
        include_tasklist = c6.checkbox("Put the activity on the weekly tasklist", value=truthy_flag(action.get("include_tasklist", "1")))
        calendar_block = c7.checkbox("Make calendar time for it", value=truthy_flag(action.get("calendar_block", "0")))
        reminder = c8.checkbox("Create a first-step task prompt", value=truthy_flag(action.get("reminder", "0")))

        start_time = str(action.get("calendar_start_time", "09:00") or "09:00")
        end_time = str(action.get("calendar_end_time", "") or "")
        prompt_time = str(action.get("task_reminder_time", "") or "")
        location = str(action.get("calendar_location", "") or "")
        first_step = str(action.get("first_step", "") or "")

        if calendar_block:
            st.markdown("#### 4. Calendar block details")
            c9, c10 = st.columns([0.42, 0.58])
            start_time = c9.text_input("Start time", value=start_time, placeholder="HH:MM")
            calculated_end = calculated_end_time(start_time, minutes)
            end_time = calculated_end
            c10.markdown(
                f"<div class='pathmark-note'><strong>Calendar end:</strong> {html.escape(calculated_end)}<br>Calculated from the start time and {int(minutes)} minutes.</div>",
                unsafe_allow_html=True,
            )
            location = st.text_input("Calendar location", value=location, placeholder="Optional")
            if is_routine_activity and activity_days:
                st.caption(f"Calendar export will repeat this activity on: {activity_days}.")
            elif is_routine_activity:
                st.caption("Choose repeat days above if this activity should recur in Calendar.")
        else:
            end_time = str(action.get("calendar_end_time", "") or "")

        if reminder:
            st.markdown("#### 5. Google Tasks prompt")
            first_step = st.text_input(
                "First tiny step",
                value=first_step,
                placeholder="For example, put on running shoes, open the sketchbook, or start wind-down routine",
                help="This becomes the Google Tasks title/prompt. It should be smaller and easier to start than the whole activity.",
            )
            default_reference = prompt_time or (start_time if calendar_block else "")
            add_reference_time = st.checkbox(
                "Add a reference time to the task note",
                value=bool(str(default_reference or "").strip()),
                help="Optional. This is written into the Google Tasks note only; it is not exported as a scheduled task time.",
            )
            if add_reference_time:
                prompt_time = st.text_input(
                    "Reference time note",
                    value=default_reference,
                    placeholder="For example, 22:30",
                    help="This is written into the task note only. Google Tasks import uses the due date, not a scheduled time or duration.",
                )
            else:
                prompt_time = ""
        else:
            prompt_time = str(action.get("task_reminder_time", "") or "")

        if include_tasklist or calendar_block or reminder:
            preview_parts = []
            if include_tasklist:
                preview_parts.append("weekly tasklist")
            if calendar_block:
                preview_parts.append(f"Calendar from {start_time} to {end_time}")
            if reminder:
                preview_parts.append("Google Tasks first-step prompt")
            st.caption("Pathmark will use this activity for: " + "; ".join(preview_parts) + ".")

        submitted = st.form_submit_button("Save changes" if record_id else f"Save {title_word.lower()}", use_container_width=True)
        if submitted:
            if calendar_block:
                end_time = calculated_end_time(start_time, minutes)
            problems = validate_online_action_dates_and_times(
                scheduled=scheduled,
                due=due,
                start_time=start_time if calendar_block else "",
                end_time=end_time if calendar_block else "",
                prompt_time=prompt_time if reminder and prompt_time else "",
            )
            if calendar_block and not scheduled.strip():
                problems.append("Add a Calendar date, or untick 'Make calendar time for it'.")
            if reminder and not due.strip():
                problems.append("Add a Google Tasks due date, or untick 'Create a first-step task prompt'.")
            if reminder and not first_step.strip():
                problems.append("Add a first tiny step, or untick the Google Tasks prompt option.")
            if not title.strip():
                st.error("Add an activity title before saving.")
            elif problems:
                for problem in problems:
                    st.error(problem)
            else:
                payload = {
                    "goal_id": goal_id or str(action.get("goal_id", "") or ""),
                    "routine_id": routine_id or str(action.get("routine_id", "") or ""),
                    "area_id": area_id or str(action.get("area_id", "") or ""),
                    "area_name": default_area or str(action.get("area_name", "") or ""),
                    "title": title.strip(),
                    "description": description.strip(),
                    "status": status,
                    "priority": priority,
                    "due_date": normalise_online_date(due) if due.strip() else "",
                    "scheduled_date": normalise_online_date(scheduled) if scheduled.strip() else "",
                    "activity_days": activity_days.strip(),
                    "estimated_minutes": str(int(minutes or 0)) if minutes else "",
                    "calendar_block": "1" if calendar_block else "0",
                    "reminder": "1" if reminder else "0",
                    "include_tasklist": "1" if include_tasklist else "0",
                    "first_step": first_step.strip() if reminder else "",
                    "task_reminder_time": prompt_time.strip() if reminder else "",
                    "calendar_start_time": start_time.strip() if calendar_block else "",
                    "calendar_end_time": end_time.strip() if calendar_block else "",
                    "calendar_location": location.strip() if calendar_block else "",
                    "notes": description.strip(),
                }
                if record_id:
                    ok, message = update_online_record(sheet_id, "actions", record_id, payload)
                else:
                    payload["action_id"] = f"action-{uuid.uuid4().hex}"
                    ok, message = append_online_record(sheet_id, "actions", payload)
                st.success(message) if ok else st.warning(safe_user_message(message))
                if ok:
                    st.rerun()

def render_goal_manager(sheet_id: str) -> None:
    st.subheader("Goals and Projects")
    st.markdown("""
    <div class='guide-box'><strong>Goals need a finish line and a next step.</strong><br>
    It is easy for goals to pile up, compete for attention, or fade before they are finished. Define what “done” means, then choose the next one or two actions that would genuinely move the goal forward. Pathmark can place those actions in the calendar and create a first-step prompt for the moment you need to start.</div>
    """, unsafe_allow_html=True)
    goals = active_online_df(read_online_table(sheet_id, "goals"))
    actions = active_online_df(read_online_table(sheet_id, "actions"))
    areas = area_options(sheet_id)
    col_list, col_main = st.columns([0.34, 0.66])
    with col_list:
        st.markdown("### Goals and projects")
        with st.expander("Add goal or project", expanded=goals.empty):
            with st.form("online_add_goal", clear_on_submit=True):
                area = st.selectbox("Area", options=[""] + areas, format_func=lambda x: x or "Choose an Area") if areas else st.text_input("Area")
                title = st.text_input("Title")
                specific = st.text_input("Specific area", placeholder="Optional sub-area or project folder")
                status = st.selectbox("Status", ["Captured", "Active", "On hold", "Closed", "Abandoned"], index=1)
                target_date = st.text_input("Target date", placeholder="Optional, YYYY-MM-DD. Example: the first day of next month")
                purpose = st.text_area("Why this matters", height=75)
                desired = st.text_area("Specific outcome", height=75, placeholder="What will be different when this is done?")
                closure = st.text_area("Measure of success / definition of done", height=75)
                notes = st.text_area("Notes", height=80)
                submitted = st.form_submit_button("Save goal", use_container_width=True)
                if submitted:
                    if not title.strip():
                        st.error("Add a title before saving.")
                    elif not str(area).strip():
                        st.error("Choose or create an Area before saving this goal.")
                    elif not valid_online_date(target_date):
                        st.error("Target date must be blank or a real date. Use YYYY-MM-DD, for example 2026-06-30.")
                    else:
                        ok, message = append_online_record(sheet_id, "goals", {
                            "goal_id": f"goal-{uuid.uuid4().hex}", "area_id": find_area_id(sheet_id, str(area)), "area_name": str(area).strip(),
                            "title": title.strip(), "description": desired.strip() or purpose.strip(), "specific_area": specific.strip(), "status": status,
                            "target_date": normalise_online_date(target_date) if target_date.strip() else "", "purpose": purpose.strip(), "desired_outcome": desired.strip(), "closure_criteria": closure.strip(), "notes": notes.strip(),
                        })
                        st.success(message) if ok else st.warning(safe_user_message(message))
                        if ok:
                            st.rerun()
        if goals.empty:
            st.info("No goals yet.")
            selected_id = ""
        else:
            labels = {f"{row.get('title','Untitled')} ({row.get('status','')})": str(row.get("goal_id", "")) for _, row in goals.iterrows()}
            selected_label = st.radio("Select a goal", list(labels.keys()), label_visibility="collapsed", key="online_goal_select")
            selected_id = labels.get(selected_label, "")
    with col_main:
        if selected_id:
            g = goals[goals["goal_id"] == selected_id].iloc[0].to_dict()
            st.markdown(f"### {g.get('title','Goal')}")
            tabs = st.tabs(["SMART goal", "Goal activities", "Archive"])
            with tabs[0]:
                with st.form(f"online_edit_goal_{selected_id}"):
                    area = st.selectbox("Area", options=[""] + areas, index=([""] + areas).index(str(g.get("area_name", ""))) if str(g.get("area_name", "")) in areas else 0) if areas else st.text_input("Area", value=str(g.get("area_name", "")))
                    title = st.text_input("Title", value=str(g.get("title", "")))
                    specific = st.text_input("Specific area", value=str(g.get("specific_area", "")))
                    status_options = ["Captured", "Active", "On hold", "Closed", "Abandoned"]
                    cur_status = str(g.get("status", "Active") or "Active")
                    status = st.selectbox("Status", status_options, index=status_options.index(cur_status) if cur_status in status_options else 1)
                    target_date = st.text_input("Target date", value=str(g.get("target_date", "")))
                    purpose = st.text_area("Purpose", value=str(g.get("purpose", "")), height=75)
                    desired = st.text_area("Desired outcome", value=str(g.get("desired_outcome", "")), height=75)
                    closure = st.text_area("Closure criteria", value=str(g.get("closure_criteria", "")), height=75)
                    notes = st.text_area("Notes", value=str(g.get("notes", "")), height=80)
                    submitted = st.form_submit_button("Save changes", use_container_width=True)
                    if submitted:
                        if not title.strip():
                            st.error("Add a goal title before saving.")
                        elif not valid_online_date(target_date):
                            st.error("Target date must be blank or a real date. Use YYYY-MM-DD, for example 2026-06-30.")
                        else:
                            ok, message = update_online_record(sheet_id, "goals", selected_id, {"area_id": find_area_id(sheet_id, str(area)), "area_name": str(area).strip(), "title": title.strip(), "description": desired.strip() or purpose.strip(), "specific_area": specific.strip(), "status": status, "target_date": normalise_online_date(target_date) if target_date.strip() else "", "purpose": purpose.strip(), "desired_outcome": desired.strip(), "closure_criteria": closure.strip(), "notes": notes.strip()})
                            st.success(message) if ok else st.warning(safe_user_message(message))
                            if ok:
                                st.rerun()
            with tabs[1]:
                linked = actions[actions["goal_id"].fillna("") == selected_id] if not actions.empty else pd.DataFrame(columns=ONLINE_TABLES["actions"])
                _render_action_list(sheet_id, linked, goal_id=selected_id, default_area=str(g.get("area_name", "") or ""))
                st.caption("Goal activities are one-off steps toward this goal. Recurring work belongs under Routines.")
                with st.expander("Add goal activity", expanded=linked.empty):
                    _action_form(sheet_id, goal_id=selected_id, default_area=str(g.get("area_name", "") or ""), form_key=f"goal_{selected_id}")
            with tabs[2]:
                st.write("Archive the goal when it is finished or no longer useful. This hides it from active online views.")
                if st.button("Archive goal", key=f"archive_goal_{selected_id}"):
                    ok, message = archive_online_record(sheet_id, "goals", selected_id, "Archived from Pathmark Online.")
                    st.success(message) if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()


def render_routine_manager(sheet_id: str) -> None:
    st.subheader("Routines")
    st.markdown("""
    <div class='guide-box'><strong>Routines are the habits that keep you steady.</strong><br>
    A routine is the container. Routine activities are the specific things you do inside it, and those activities can appear on the tasklist, become Google Calendar blocks, or create date-based Google Tasks first-step prompts.</div>
    """, unsafe_allow_html=True)
    routines = active_online_df(read_online_table(sheet_id, "routines"))
    actions = active_online_df(read_online_table(sheet_id, "actions"))
    areas = area_options(sheet_id)
    col_list, col_main = st.columns([0.34, 0.66])
    with col_list:
        st.markdown("### Routines")
        with st.expander("Add routine", expanded=routines.empty):
            with st.form("online_add_routine", clear_on_submit=True):
                area = st.selectbox("Area", options=[""] + areas, format_func=lambda x: x or "Choose an Area", key="routine_area") if areas else st.text_input("Area", key="routine_area_text")
                title = st.text_input("Routine title")
                frequency = st.selectbox("Repeat pattern for calendar blocks and task prompts", VALID_FREQUENCIES, index=VALID_FREQUENCIES.index("Weekly"))
                if frequency in {"Daily", "Weekdays"}:
                    preferred_day_values = []
                    preferred_days = ""
                else:
                    preferred_day_values = st.multiselect("Repeat on these days", VALID_DAYS, help="Used to generate Google Calendar-compatible weekly recurrence rules.")
                    preferred_days = ", ".join(preferred_day_values)
                next_due = st.text_input("Repeat starts", placeholder="YYYY-MM-DD")
                purpose = st.text_area("Why this matters", height=75)
                checklist = ""
                st.caption("After saving the routine container, add one or more routine activities. Activities drive calendar blocks, tasklist rows and Google Tasks prompts.")
                status = st.selectbox("Status", ["Active", "Paused", "Archived"], index=0)
                notes = st.text_area("Notes", height=80)
                submitted = st.form_submit_button("Save routine", use_container_width=True)
                if submitted:
                    if not title.strip():
                        st.error("Add a routine title before saving.")
                    elif not str(area).strip():
                        st.error("Choose or create an Area before saving this routine.")
                    elif not valid_online_date(next_due):
                        st.error("Repeat starts must be blank or a real date. Use YYYY-MM-DD, for example 2026-06-08.")
                    elif validate_routine_schedule(frequency, preferred_days):
                        for problem in validate_routine_schedule(frequency, preferred_days):
                            st.error(problem)
                    else:
                        ok, message = append_online_record(sheet_id, "routines", {"routine_id": f"routine-{uuid.uuid4().hex}", "area_id": find_area_id(sheet_id, str(area)), "area_name": str(area).strip(), "title": title.strip(), "description": purpose.strip() or notes.strip(), "frequency": frequency.strip() or "Weekly", "preferred_days": preferred_days.strip(), "status": status, "purpose": purpose.strip(), "next_due": normalise_online_date(next_due) if next_due.strip() else "", "checklist": checklist.strip(), "notes": notes.strip()})
                        st.success(message) if ok else st.warning(safe_user_message(message))
                        if ok:
                            st.rerun()
        if routines.empty:
            st.info("No routines yet.")
            selected_id = ""
        else:
            labels = {f"{row.get('title','Untitled')} ({row.get('status','')})": str(row.get("routine_id", "")) for _, row in routines.iterrows()}
            selected_label = st.radio("Select a routine", list(labels.keys()), label_visibility="collapsed", key="online_routine_select")
            selected_id = labels.get(selected_label, "")
    with col_main:
        if selected_id:
            r = routines[routines["routine_id"] == selected_id].iloc[0].to_dict()
            st.markdown(f"### {r.get('title','Routine')}")
            tabs = st.tabs(["Details", "Activities", "Repeat", "Manage"])
            with tabs[0]:
                with st.form(f"online_edit_routine_{selected_id}"):
                    area = st.selectbox("Area", options=[""] + areas, index=([""] + areas).index(str(r.get("area_name", ""))) if str(r.get("area_name", "")) in areas else 0, key=f"edit_r_area_{selected_id}") if areas else st.text_input("Area", value=str(r.get("area_name", "")))
                    title = st.text_input("Routine title", value=str(r.get("title", "")))
                    purpose = st.text_area("Purpose", value=str(r.get("purpose", "")), height=75)
                    st.caption("This is the routine container. Add or edit the actual repeatable work in the Activities tab.")
                    checklist = str(r.get("checklist", "") or "")
                    notes = st.text_area("Notes", value=str(r.get("notes", "")), height=80)
                    status_options = ["Active", "Paused", "Archived"]
                    cur_status = str(r.get("status", "Active") or "Active")
                    status = st.selectbox("Status", status_options, index=status_options.index(cur_status) if cur_status in status_options else 0)
                    submitted = st.form_submit_button("Save changes", use_container_width=True)
                    if submitted:
                        if not title.strip():
                            st.error("Add a routine title before saving.")
                        else:
                            ok, message = update_online_record(sheet_id, "routines", selected_id, {"area_id": find_area_id(sheet_id, str(area)), "area_name": str(area).strip(), "title": title.strip(), "description": purpose.strip() or notes.strip(), "status": status, "purpose": purpose.strip(), "checklist": checklist.strip(), "notes": notes.strip()})
                            st.success(message) if ok else st.warning(safe_user_message(message))
                            if ok:
                                st.rerun()
            with tabs[1]:
                linked = actions[actions["routine_id"].fillna("") == selected_id] if not actions.empty else pd.DataFrame(columns=ONLINE_TABLES["actions"])
                _render_action_list(sheet_id, linked, routine_id=selected_id, default_area=str(r.get("area_name", "") or ""))
                with st.expander("Add routine activity", expanded=linked.empty):
                    _action_form(sheet_id, routine_id=selected_id, default_area=str(r.get("area_name", "") or ""), form_key=f"routine_{selected_id}")
            with tabs[2]:
                with st.form(f"online_repeat_{selected_id}"):
                    current_freq = str(r.get("frequency", "") or "Weekly")
                    frequency = st.selectbox("Repeat pattern for calendar blocks and task prompts", VALID_FREQUENCIES, index=VALID_FREQUENCIES.index(current_freq) if current_freq in VALID_FREQUENCIES else VALID_FREQUENCIES.index("Custom"))
                    current_days, _bad_days = parse_days_text(str(r.get("preferred_days", "")))
                    if frequency in {"Daily", "Weekdays"}:
                        preferred_day_values = []
                        preferred_days = ""
                    else:
                        preferred_day_values = st.multiselect("Repeat on these days", VALID_DAYS, default=current_days, help="Used to generate Google Calendar-compatible weekly recurrence rules.")
                        preferred_days = ", ".join(preferred_day_values)
                    next_due = st.text_input("Repeat starts", value=str(r.get("next_due", "")))
                    duration = st.text_input("Default duration minutes", value=str(r.get("duration_minutes", "")))
                    c1, c2 = st.columns(2)
                    start = c1.text_input("Default start time", value=str(r.get("calendar_start_time", "09:00") or "09:00"))
                    end = c2.text_input("Default end time", value=str(r.get("calendar_end_time", "10:00") or "10:00"))
                    submitted = st.form_submit_button("Save repeat settings", use_container_width=True)
                    if submitted:
                        problems = []
                        if not valid_online_date(next_due):
                            problems.append("Repeat starts must be blank or a real date. Use YYYY-MM-DD, for example 2026-06-08.")
                        for label, value in [("Default start time", start), ("Default end time", end)]:
                            if not valid_online_time(value):
                                problems.append(f"{label} must be blank or a real time, for example 09:00 or 7:30pm.")
                        problems.extend(validate_routine_schedule(frequency, preferred_days))
                        if problems:
                            for problem in problems:
                                st.error(problem)
                        else:
                            ok, message = update_online_record(sheet_id, "routines", selected_id, {"frequency": frequency.strip(), "preferred_days": preferred_days.strip(), "next_due": normalise_online_date(next_due) if next_due.strip() else "", "duration_minutes": duration.strip(), "calendar_start_time": start.strip(), "calendar_end_time": end.strip()})
                            st.success(message) if ok else st.warning(safe_user_message(message))
                            if ok:
                                st.rerun()
            with tabs[3]:
                st.markdown("""
                **Active** routines appear in the workspace and can feed exports.  
                **Paused** routines stay visible here but are not intended for current tasklist or export use.  
                **Archived** routines move out of the active workspace and can be restored later.
                """)
                c1, c2, c3 = st.columns(3)
                if c1.button("Set as active", key=f"active_r_{selected_id}"):
                    ok, message = update_online_record(sheet_id, "routines", selected_id, {"status": "Active"})
                    st.success(message) if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
                if c2.button("Pause routine", key=f"pause_r_{selected_id}"):
                    ok, message = update_online_record(sheet_id, "routines", selected_id, {"status": "Paused"})
                    st.success("Routine paused. It remains here so you can restart it later.") if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
                if c3.button("Archive routine", key=f"archive_r_{selected_id}"):
                    ok, message = archive_online_record(sheet_id, "routines", selected_id, "Archived from Pathmark Online.")
                    st.success("Routine archived. You can restore it from Archive.") if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()


def render_review_queue_manager(sheet_id: str) -> None:
    st.subheader("Review Queue")
    st.write("Review Queue checks whether the parts of your workspace are ready to work together before you export tasklists, calendar blocks or Google Tasks prompts.")
    data = read_online_tables(sheet_id)
    issues = []
    areas = active_online_df(data.get("areas", pd.DataFrame()))
    goals = active_online_df(data.get("goals", pd.DataFrame()))
    routines = active_online_df(data.get("routines", pd.DataFrame()))
    actions = active_online_df(data.get("actions", pd.DataFrame()))

    if areas.empty:
        issues.append({"priority": "High", "kind": "Area", "item": "No Areas yet", "issue": "Create at least one Area so routines, goals and exports have somewhere to belong.", "next": "Add an Area such as Body and Stability, Food and Home, Work and Admin, or Learning and Creativity."})
    for _, r in routines.iterrows():
        rid = str(r.get("routine_id", "") or "")
        linked = actions[actions["routine_id"].fillna("") == rid] if not actions.empty and "routine_id" in actions.columns else pd.DataFrame()
        if str(r.get("frequency", "") or "").strip() == "":
            issues.append({"priority": "Medium", "kind": "Routine", "item": r.get("title", "Untitled"), "issue": "This routine does not have a repeat pattern yet.", "next": "Open the routine and set how often it repeats."})
        if linked.empty:
            issues.append({"priority": "Medium", "kind": "Routine", "item": r.get("title", "Untitled"), "issue": "This routine does not have an activity yet.", "next": "Add at least one routine activity so Pathmark can place it on a tasklist, calendar export or Google Tasks prompt."})
    for _, g in goals.iterrows():
        gid = str(g.get("goal_id", "") or "")
        linked = actions[actions["goal_id"].fillna("") == gid] if not actions.empty and "goal_id" in actions.columns else pd.DataFrame()
        if not str(g.get("closure_criteria", "") or g.get("desired_outcome", "") or "").strip():
            issues.append({"priority": "Medium", "kind": "Goal", "item": g.get("title", "Untitled"), "issue": "This goal does not yet say what done looks like.", "next": "Add a measure of success or definition of done."})
        if linked.empty:
            issues.append({"priority": "Medium", "kind": "Goal", "item": g.get("title", "Untitled"), "issue": "This goal does not have a next activity yet.", "next": "Add one or two concrete goal activities rather than a full project plan."})
    for _, a in actions.iterrows():
        title = a.get("title", "Untitled")
        if truthy_flag(a.get("calendar_block", "0")) and not str(a.get("scheduled_date", "") or "").strip():
            issues.append({"priority": "High", "kind": "Calendar", "item": title, "issue": "This activity is marked for Google Calendar but does not have a date.", "next": "Add a calendar date and start/end time, or untick the Calendar block option."})
        if truthy_flag(a.get("reminder", "0")) and not str(a.get("first_step", "") or "").strip():
            issues.append({"priority": "Medium", "kind": "Google Tasks", "item": title, "issue": "This activity is marked for Google Tasks but does not have a first-action prompt.", "next": "Add a tiny first step such as 'put on running shoes' or untick the Google Tasks prompt option."})

    if not issues:
        st.success("No review issues found. Your active workspace has enough structure for tasklists and exports.")
        return
    st.markdown("### Things to tidy")
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    for issue in sorted(issues, key=lambda x: priority_order.get(x.get("priority", "Medium"), 1)):
        st.markdown(
            f"""
            <div class='issue-card' style='padding: .85rem 1rem; margin: .65rem 0;'>
              <div class='eyebrow'>{html.escape(str(issue.get('priority', 'Medium')))} · {html.escape(str(issue.get('kind', 'Review')))}</div>
              <h3>{html.escape(str(issue.get('item', 'Item')))}</h3>
              <p>{html.escape(str(issue.get('issue', '')))}</p>
              <p><strong>Next:</strong> {html.escape(str(issue.get('next', '')))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

def render_tasklist_manager(sheet_id: str) -> None:
    st.subheader("Tasklist")
    st.write("Use a printed tasklist as the paper alternative to Google Tasks prompts. Choose the routine activities and goal actions you want to tick off by hand.")
    tasklist = staged_tasklist(sheet_id)
    if tasklist.empty:
        st.info("No tasklist rows yet. Add goal actions or routine activities and choose 'Add this activity to the weekly tasklist'.")
        return
    with st.expander("Choose what goes on the tasklist", expanded=True):
        title = st.text_input("Tasklist name", value="Weekly Tasklist", help="This appears at the top of the printable tasklist.")
        notes = st.text_area("Optional notes for the printed tasklist", height=80, help="Add one note per line. These are appended to the end of the tasklist.")
        selected_indices: list[int] = []
        goal_actions = tasklist[tasklist["source_type"] == "Goal action"].reset_index(drop=True)
        routine_rows = tasklist[tasklist["source_type"] == "Routine activity"].reset_index(drop=True)
        if not goal_actions.empty:
            st.markdown("#### Goal actions")
            for parent, group in goal_actions.groupby(goal_actions["parent"].fillna("Unlinked goal"), sort=False):
                st.markdown(f"**{parent or 'Unlinked goal'}**")
                for _, row in group.iterrows():
                    key = f"tasklist_goal_{row.get('id') or row.get('title')}"
                    label_bits = []
                    if str(row.get("scheduled_date", "") or "").strip():
                        label_bits.append(f"scheduled {row.get('scheduled_date')}")
                    if str(row.get("due_date", "") or "").strip():
                        label_bits.append(f"due {row.get('due_date')}")
                    suffix = f" ({'; '.join(label_bits)})" if label_bits else ""
                    if st.checkbox(f"{row.get('title','Untitled')}{suffix}", value=False, key=key):
                        selected_indices.append(int(row.name))
        if not routine_rows.empty:
            st.markdown("#### Routine activities")
            routine_offset = len(goal_actions)
            for parent, group in routine_rows.groupby(routine_rows["parent"].fillna("Unlinked routine"), sort=False):
                st.markdown(f"**{parent or 'Unlinked routine'}**")
                for _, row in group.iterrows():
                    key = f"tasklist_routine_{row.get('id') or row.get('title')}"
                    days = str(row.get("activity_days", "") or "").strip()
                    suffix = f" ({days})" if days else ""
                    if st.checkbox(f"{row.get('title','Untitled')}{suffix}", value=False, key=key):
                        selected_indices.append(routine_offset + int(row.name))
    selected_rows = tasklist.iloc[selected_indices] if selected_indices else pd.DataFrame(columns=tasklist.columns)
    if selected_rows.empty and not st.session_state.get("tasklist_notes_has_content", False):
        st.info("Tick at least one action or activity before downloading the tasklist.")
    if not selected_rows.empty:
        st.markdown("### Preview")
        dataframe_preview(selected_rows, ["source_type", "title", "area_name", "parent", "scheduled_date", "due_date", "first_step", "estimated_minutes"])
    pdf_bytes = build_tasklist_pdf(selected_rows, title=title or "Pathmark Tasklist", notes=notes)
    st.download_button("Download printable PDF tasklist", data=pdf_bytes, file_name="pathmark_tasklist.pdf", mime="application/pdf", use_container_width=True, disabled=selected_rows.empty and not notes.strip())
    if not selected_rows.empty:
        with st.expander("After printing or saving"):
            st.write("Move these rows to Archive when you want them out of your active workspace. You can restore them later.")
            if st.button("Move selected tasklist items to Archive", use_container_width=True):
                ids = selected_rows.get("action_id", pd.Series(dtype=str)).dropna().astype(str).tolist()
                ok, message = mark_actions_exported(sheet_id, ids, "paper_tasklist", archive=True)
                st.success(message) if ok else st.warning(safe_user_message(message))
                st.rerun()

def render_google_calendar_export_manager(sheet_id: str) -> None:
    st.subheader("Google Calendar Export")
    st.write("Calendar export turns selected goal activities and routine activities into time blocks. Repeat settings are used for recurring routine activities where available.")
    blocks = staged_calendar_blocks(sheet_id)
    if blocks.empty:
        st.info("No calendar rows are staged yet. Tick 'Create a Google Calendar time block' on a goal activity or routine activity, then add a date and time.")
    else:
        st.markdown("### Calendar items ready to export")
        for _, row in blocks.iterrows():
            start_text = human_calendar_datetime(str(row.get("start", "")))
            end_text = human_calendar_datetime(str(row.get("end", "")))
            repeat = human_recurrence(row.get("recurrence", ""))
            area = str(row.get("area_name", "") or "")
            area_line = f"Area: {html.escape(area)}" if area else ""
            repeat_line = html.escape(repeat) if repeat else "Does not repeat"
            joiner = " · " if area_line and repeat_line else ""
            st.markdown(
                f"""
                <div class='step-card'>
                  <h3>{html.escape(str(row.get('title', 'Calendar item') or 'Calendar item'))}</h3>
                  <p><strong>{html.escape(start_text)}</strong>{' – ' + html.escape(end_text.split(', ')[-1]) if end_text else ''}</p>
                  <p>{area_line}{joiner}{repeat_line}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with st.expander("Show export details", expanded=False):
            dataframe_preview(blocks, ["title", "area_name", "start", "end", "recurrence"])
    st.download_button("Download Google Calendar .ics", data=build_ics_export(blocks), file_name="pathmark_calendar_blocks.ics", mime="text/calendar", use_container_width=True, disabled=blocks.empty)
    if not blocks.empty:
        st.info("After you have downloaded or imported the calendar file, you can move those exported rows to Archive so they leave the active workspace. You can restore archived items later.")
        if st.button("Move exported calendar items to Archive", use_container_width=True):
            ids = blocks.get("linked_record_id", pd.Series(dtype=str)).dropna().astype(str).tolist()
            ok, message = mark_actions_exported(sheet_id, ids, "google_calendar", archive=True)
            st.success(message) if ok else st.warning(safe_user_message(message))
            st.rerun()



def write_google_tasks_export_tab(sheet_id: str, prompts: pd.DataFrame) -> tuple[bool, str]:
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session."
    try:
        columns = ONLINE_TABLES["google_tasks_export"]
        ensure_pathmark_online_schema(service, sheet_id)
        values = [columns]
        stamp = utc_now_text()
        for _, r in prompts.iterrows():
            row = {
                "Task ID": f"PM_TASK_{r.get('id') or uuid.uuid4().hex}",
                "Task List": r.get("task_list") or "Pathmark",
                "Title": r.get("title") or "",
                "Notes": r.get("notes") or "",
                "Due Date": r.get("due_date") or "",
                "Reference Time": r.get("reminder_time") or "",
                "Status": "completed" if str(r.get("status", "")).lower() == "completed" else "needsAction",
                "Repeat Pattern": r.get("repeat_pattern") or "",
                "Related Google Calendar Item": r.get("linked_calendar_summary") or "",
                "exported_at": stamp,
            }
            values.append([str(row.get(col, "")) for col in columns])
        service.spreadsheets().values().clear(spreadsheetId=sheet_id, range=f"google_tasks_export!A:{sheet_col_letter(len(columns))}").execute()
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"google_tasks_export!A1:{sheet_col_letter(len(columns))}{len(values)}",
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        clear_online_cache(sheet_id)
        return True, "Updated the google_tasks_export tab in your Pathmark Sync sheet."
    except Exception as exc:
        return False, f"Could not write the Google Tasks export tab: {exc}"


def render_google_tasks_export_manager(sheet_id: str) -> None:
    st.subheader("Google Tasks Export")
    st.write("Google Tasks prompts are date-based first steps from goal activities and routine activities. Use Calendar export for time blocks and durations; Google Tasks export does not preserve due times or durations.")
    prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        st.info("No Google Tasks prompts are staged yet. Tick 'Create a Google Tasks first-action prompt' on a goal activity or routine activity.")
    else:
        st.markdown("### Google Tasks prompts ready to export")
        for _, row in prompts.iterrows():
            title = html.escape(str(row.get("title", "Task prompt") or "Task prompt"))
            due = human_calendar_datetime(str(row.get("due_date", "") or ""))
            area = html.escape(str(row.get("area_name", "") or ""))
            task_list = html.escape(str(row.get("task_list", "Pathmark") or "Pathmark"))
            st.markdown(
                f"""
                <div class='step-card'>
                  <h3>{title}</h3>
                  <p><strong>{html.escape(due) if due else 'No due date yet'}</strong></p>
                  <p>{'Area: ' + area + ' · ' if area else ''}Task list: {task_list}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with st.expander("Show Google Tasks export details", expanded=False):
            dataframe_preview(prompts, ["title", "area_name", "due_date", "task_list", "linked_calendar_summary"])
    st.download_button("Download Google Tasks CSV", data=build_google_tasks_csv(prompts), file_name="pathmark_google_tasks.csv", mime="text/csv", use_container_width=True, disabled=prompts.empty)
    if st.button("Write Google Tasks export to my sync sheet", use_container_width=True, disabled=prompts.empty):
        ok, message = write_google_tasks_export_tab(sheet_id, prompts)
        st.success(message) if ok else st.warning(safe_user_message(message))
    if not prompts.empty:
        st.info("After you have downloaded or written the Google Tasks export, you can move those exported rows to Archive so they leave the active workspace.")
        if st.button("Move exported Google Tasks items to Archive", use_container_width=True):
            ids = prompts.get("id", pd.Series(dtype=str)).dropna().astype(str).tolist()
            ok, message = mark_actions_exported(sheet_id, ids, "google_tasks", archive=True)
            st.success(message) if ok else st.warning(safe_user_message(message))
            st.rerun()

def render_archive_manager(sheet_id: str) -> None:
    st.subheader("Archive")
    st.write("Archive keeps exported, completed or paused records out of the active workspace without deleting them. Restore a record when you want to work with it again.")
    table_specs = [
        ("areas", "Areas", "area_id", "area_name", ["area_name", "description", "updated_at", "archived_at", "archived_reason"]),
        ("goals", "Goals", "goal_id", "title", ["title", "area_name", "status", "updated_at", "archived_at", "archived_reason"]),
        ("routines", "Routines", "routine_id", "title", ["title", "area_name", "status", "updated_at", "archived_at", "archived_reason"]),
        ("actions", "Goal and routine activities", "action_id", "title", ["title", "area_name", "status", "export_type", "exported_at", "archived_at", "archived_reason"]),
    ]
    for table, title, id_col, label_col, cols in table_specs:
        df = read_online_table(sheet_id, table)
        if not df.empty and "status" in df.columns:
            archived = df[df["status"].fillna("").str.lower().eq("archived")].reset_index(drop=True)
        else:
            archived = pd.DataFrame(columns=cols)
        with st.expander(title, expanded=False):
            if archived.empty:
                st.caption("Nothing archived here yet.")
                continue
            dataframe_preview(archived, [c for c in cols if c in archived.columns])
            choices = []
            for _, row in archived.iterrows():
                label = str(row.get(label_col, "Untitled") or "Untitled")
                rid = str(row.get(id_col, "") or "")
                choices.append((f"{label} — {rid[-8:] if rid else 'no id'}", rid))
            choice_label = st.selectbox(f"Choose {title.lower()} record to restore", [c[0] for c in choices], key=f"restore_choice_{table}")
            chosen_id = dict(choices).get(choice_label, "")
            if st.button(f"Restore selected {title.lower()}", key=f"restore_button_{table}", use_container_width=True, disabled=not chosen_id):
                ok, message = restore_online_record(sheet_id, table, chosen_id)
                st.success("Restored to the active workspace.") if ok else st.warning(safe_user_message(message))
                st.rerun()


def render_online_settings(sheet_id: str) -> None:
    st.subheader("Settings")
    st.write("Manage your online workspace, seasonal theme, and Google Sheet connection.")
    if sheet_id:
        st.caption("Pathmark Sync sheet is connected for this session.")
    else:
        st.caption("No sync sheet selected.")
    c1, c2, c3 = st.columns(3)
    if sheet_id:
        c1.link_button("Open sync sheet", f"https://docs.google.com/spreadsheets/d/{sheet_id}", use_container_width=True)
    if c2.button("Refresh online data", use_container_width=True):
        clear_online_cache(sheet_id)
        st.rerun()
    if c3.button("Disconnect Google access", use_container_width=True):
        revoke_google_session_token()
        st.rerun()
    with st.expander("Guided setup", expanded=False):
        state = get_setup_state(sheet_id)
        st.write(f"Current setup status: **{state['status'].replace('_', ' ').title()}**")
        st.write(f"Current step: **{state['current_step'].title()}**")
        st.write("You can revisit the setup pathway without deleting any Areas, routines, goals or actions.")
        if st.button("Start setup pathway again", use_container_width=True, key="settings_reset_setup"):
            st.session_state.pop("skip_online_setup_for_session", None)
            ok, message = save_setup_state(sheet_id, reset=True)
            st.success("Guided setup is ready to revisit.") if ok else st.warning(safe_user_message(message))
            st.rerun()
    with st.expander("Advanced Google Sheet settings", expanded=False):
        render_google_sheets_oauth_diagnostics()
        sheet_url_input = st.text_input("Use an existing Pathmark Sync Google Sheet URL or ID", value=st.session_state.get("sync_sheet_id", ""), help="Use a Pathmark Sync sheet that belongs to your Google account. With the safer drive.file permission, Pathmark can only use files it created or files you explicitly authorise.")
        if sheet_url_input:
            st.session_state["sync_sheet_id"] = extract_google_sheet_id(sheet_url_input)
            clear_online_cache(st.session_state.get("sync_sheet_id", ""))
        if st.button("Find or create Pathmark Sync sheet", use_container_width=True):
            ok, new_sheet_id, message = ensure_pathmark_sync_sheet_ready()
            st.success("Pathmark sync sheet is ready.") if ok else st.warning(safe_user_message(message))
            if ok:
                clear_online_cache(new_sheet_id)
                st.rerun()
    with st.expander("Delete Pathmark Online data and revoke access", expanded=False):
        st.warning("This is a permanent cleanup action for Pathmark Online. It does not delete files from your local Pathmark Desktop Workspace.")
        st.write("Disconnect Google access here, or delete Pathmark Online data from the Google files Pathmark can identify. Pathmark will not delete Drive folders just because they are named Pathmark.")
        ok_files, files, files_message = list_pathmark_drive_files_for_deletion(sheet_id) if sheet_id else (True, [], "No sync sheet is currently selected.")
        if ok_files and files:
            rows = []
            for f in files:
                kind = "Google Sheet" if f.get("mimeType") == "application/vnd.google-apps.spreadsheet" else ("Folder" if f.get("mimeType") == "application/vnd.google-apps.folder" else "Drive file")
                rows.append({"Name": f.get("name", ""), "Type": kind, "Modified": f.get("modifiedTime", "")})
            st.write("Pathmark can delete these identified files:")
            dataframe_preview(pd.DataFrame(rows), ["Name", "Type", "Modified"])
        elif ok_files:
            st.info("No Pathmark Google Drive files were found for this app to delete.")
        else:
            st.warning(safe_user_message(files_message))
        remove_profile = st.checkbox("Also remove my Pathmark access/profile record from Supabase", value=True, help="This removes your email, role/status row, theme preference and matching audit records from Pathmark's access system. If your email is still listed in deployment bootstrap settings, that bootstrap access may be recreated next time you sign in.")
        confirm_text = st.text_input("Type DELETE PATHMARK to confirm", value="", key="confirm_delete_pathmark_online")
        delete_disabled = confirm_text.strip() != "DELETE PATHMARK"
        if st.button("Delete Pathmark Online data and revoke Google access", use_container_width=True, disabled=delete_disabled):
            user = current_user()
            ok, message = full_google_disconnect_and_data_removal(sheet_id, user.get("email", ""), remove_supabase_profile=remove_profile)
            if ok:
                st.success(message)
            else:
                st.warning(safe_user_message(message))
            st.rerun()
    st.markdown("### Theme")
    st.write("Choose the seasonal character of Pathmark. Light and dark mode are controlled separately through Streamlit's own Settings menu: System, Light or Dark.")
    current_theme = normalise_online_theme(st.session_state.get("hosted_theme_preference") or online_setting(sheet_id, "theme", "Winter"))
    theme_name = st.selectbox("Seasonal theme", ONLINE_THEME_OPTIONS, index=ONLINE_THEME_OPTIONS.index(current_theme))
    if st.button("Save theme", use_container_width=True):
        theme_name = normalise_online_theme(theme_name)
        ok_sheet, message_sheet = save_online_setting(sheet_id, "theme", theme_name)
        user = current_user()
        ok_profile, message_profile = update_supabase_user_theme(user.get("email", ""), theme_name, actor_email=user.get("email", ""))
        st.session_state["hosted_theme_preference"] = theme_name
        if ok_sheet or ok_profile:
            st.success("Theme saved.")
            st.rerun()
        else:
            st.warning(safe_user_message(message_profile or message_sheet))




def build_tasklist_pdf(rows: pd.DataFrame, title: str = "Pathmark Tasklist", notes: str = "") -> bytes:
    """Build a polished printable tasklist PDF with clean checkbox cells."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.graphics.shapes import Drawing, Rect
    except Exception:
        return build_printable_tasklist_from_rows(rows)

    def checkbox_box() -> Drawing:
        drawing = Drawing(9, 9)
        drawing.add(Rect(0.75, 0.75, 7.5, 7.5, strokeColor=colors.HexColor("#7A827F"), fillColor=colors.white, strokeWidth=0.8))
        return drawing

    def clean_text(value: Any) -> str:
        text = re.sub(r"<\s*br\s*/?\s*>", " · ", str(value or ""), flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        return html.escape(text.strip())

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("PathmarkTitle", parent=styles["Title"], fontSize=21, leading=25, spaceAfter=4, textColor=colors.HexColor("#1F2221"))
    sub_style = ParagraphStyle("PathmarkSub", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#626966"), spaceAfter=8)
    h_style = ParagraphStyle("PathmarkHeading", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#334E68"))
    body = ParagraphStyle("PathmarkBody", parent=styles["BodyText"], fontSize=9.2, leading=12, textColor=colors.HexColor("#1F2221"))
    small = ParagraphStyle("PathmarkSmall", parent=styles["BodyText"], fontSize=8.4, leading=11, textColor=colors.HexColor("#626966"))

    story = [
        Paragraph(clean_text(title or "Pathmark Tasklist"), title_style),
        Paragraph(datetime.now().strftime("Created %d %B %Y"), sub_style),
        Spacer(1, 4),
    ]

    if rows.empty:
        story.append(Paragraph("No tasklist rows selected.", body))
    else:
        for source_type in ["Goal action", "Routine activity"]:
            subset = rows[rows["source_type"] == source_type] if "source_type" in rows.columns else pd.DataFrame()
            if subset.empty:
                continue
            heading = "Goal activities" if source_type == "Goal action" else "Routine activities"
            story.append(Paragraph(clean_text(heading), h_style))
            data = [["", "Task", "When / context", "First action prompt"]]
            for _, row in subset.iterrows():
                context_bits = []
                for label, col in [("Area", "area_name"), ("Parent", "parent"), ("Scheduled", "scheduled_date"), ("Due", "due_date"), ("Time", "estimated_minutes")]:
                    val = str(row.get(col, "") or "").strip()
                    if val:
                        if col == "estimated_minutes":
                            val = f"{val} min"
                        context_bits.append(f"{label}: {val}")
                first = str(row.get("first_step", "") or "").strip()
                data.append([
                    checkbox_box(),
                    Paragraph(clean_text(row.get("title", "Untitled") or "Untitled"), body),
                    Paragraph(clean_text(" · ".join(context_bits)), small),
                    Paragraph(clean_text(first), body),
                ])
            table = Table(data, colWidths=[8*mm, 60*mm, 52*mm, 58*mm], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EEF4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2221")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#334E68")),
                ("GRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#D8D4CB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(table)
            story.append(Spacer(1, 8))

    if notes.strip():
        story.append(Paragraph("Notes", h_style))
        for line in notes.strip().splitlines():
            story.append(Paragraph(clean_text(line), body))
    doc.build(story)
    return buffer.getvalue()

def parse_dt_for_ics(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]:
        try:
            dt = datetime.strptime(text, fmt)
            if fmt == "%Y-%m-%d":
                return dt.strftime("%Y%m%d")
            return dt.strftime("%Y%m%dT%H%M00")
        except Exception:
            pass
    return re.sub(r"[^0-9T]", "", text)


def build_ics_export(blocks: pd.DataFrame) -> bytes:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Pathmark Online//EN"]
    for _, row in blocks.iterrows():
        title = str(row.get("title", "") or "Pathmark block").strip() or "Pathmark block"
        start = parse_dt_for_ics(str(row.get("start", "")))
        end = parse_dt_for_ics(str(row.get("end", "")))
        if not start:
            continue
        lines.extend(["BEGIN:VEVENT", f"UID:{row.get('block_id') or uuid.uuid4().hex}@pathmark", f"SUMMARY:{title}", f"DTSTART:{start}"])
        if end:
            lines.append(f"DTEND:{end}")
        description = str(row.get("description", "") or "").replace("\n", "\\n")
        if description:
            lines.append(f"DESCRIPTION:{description}")
        recurrence = str(row.get("recurrence", "") or "").strip()
        if recurrence.upper().startswith("RRULE:"):
            lines.append(recurrence)
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def build_google_tasks_csv(prompts: pd.DataFrame) -> bytes:
    headers = ["Task ID", "Task List", "Title", "Notes", "Due Date", "Reference Time", "Status", "Repeat Pattern", "Related Google Calendar Item"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for _, r in prompts.iterrows():
        writer.writerow({
            "Task ID": f"PM_TASK_{r.get('id') or uuid.uuid4().hex}",
            "Task List": r.get("task_list") or "Pathmark",
            "Title": r.get("title") or "",
            "Notes": r.get("notes") or "",
            "Due Date": r.get("due_date") or "",
            "Reference Time": r.get("reminder_time") or "",
            "Status": "completed" if str(r.get("status", "")).lower() == "completed" else "needsAction",
            "Repeat Pattern": r.get("repeat_pattern") or "",
            "Related Google Calendar Item": r.get("linked_calendar_summary") or "",
        })
    return out.getvalue().encode("utf-8-sig")


def build_printable_tasklist_from_rows(rows: pd.DataFrame) -> bytes:
    lines = ["Pathmark tasklist", ""]
    if rows.empty:
        lines.append("No tasklist rows.")
        return "\n".join(lines).encode("utf-8")
    for source_type in ["Goal action", "Routine activity"]:
        subset = rows[rows["source_type"] == source_type] if "source_type" in rows.columns else pd.DataFrame()
        if subset.empty:
            continue
        lines.append(source_type + "s")
        current_parent = None
        for _, row in subset.iterrows():
            parent = str(row.get("parent", "") or "").strip()
            if parent and parent != current_parent:
                lines.append(f"\n{parent}")
                current_parent = parent
            bits = []
            if str(row.get("scheduled_date", "") or "").strip():
                bits.append(f"scheduled {row.get('scheduled_date')}")
            if str(row.get("due_date", "") or "").strip():
                bits.append(f"due {row.get('due_date')}")
            if str(row.get("estimated_minutes", "") or "").strip():
                bits.append(f"{row.get('estimated_minutes')} min")
            suffix = f" ({'; '.join(bits)})" if bits else ""
            lines.append(f"☐ {row.get('title','Untitled')}{suffix}")
            first = str(row.get("first_step", "") or "").strip()
            if first:
                lines.append(f"    First action: {first}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")




def render_exports_manager(sheet_id: str) -> None:
    st.subheader("Exports")
    st.write("Use the dedicated Google Calendar Export, Google Tasks Export, and Tasklist tabs to prepare files from your saved actions and routine activities.")
    c1, c2 = st.columns(2)
    with c1:
        render_google_calendar_export_manager(sheet_id)
    with c2:
        render_google_tasks_export_manager(sheet_id)


def get_setup_state(sheet_id: str) -> dict[str, str]:
    status = online_setting(sheet_id, "setup_status", "not_started")
    if status not in {"not_started", "in_progress", "completed"}:
        status = "not_started"
    current = online_setting(sheet_id, "setup_current_step", SETUP_STEP_KEYS[0])
    if current not in SETUP_STEP_KEYS:
        current = SETUP_STEP_KEYS[0]
    return {
        "status": status,
        "current_step": current,
        "completed_at": online_setting(sheet_id, "setup_completed_at", ""),
        "reset_at": online_setting(sheet_id, "setup_reset_at", ""),
    }


def save_setup_state(sheet_id: str, *, status: str | None = None, current_step: str | None = None, completed: bool = False, reset: bool = False) -> tuple[bool, str]:
    ok = True
    messages: list[str] = []
    if status:
        step_ok, msg = save_online_setting(sheet_id, "setup_status", status)
        ok = ok and step_ok; messages.append(msg)
    if current_step:
        step_ok, msg = save_online_setting(sheet_id, "setup_current_step", current_step)
        ok = ok and step_ok; messages.append(msg)
    if completed:
        step_ok, msg = save_online_setting(sheet_id, "setup_status", "completed")
        ok = ok and step_ok; messages.append(msg)
        step_ok, msg = save_online_setting(sheet_id, "setup_completed_at", utc_now_text())
        ok = ok and step_ok; messages.append(msg)
    if reset:
        step_ok, msg = save_online_setting(sheet_id, "setup_status", "in_progress")
        ok = ok and step_ok; messages.append(msg)
        step_ok, msg = save_online_setting(sheet_id, "setup_current_step", SETUP_STEP_KEYS[0])
        ok = ok and step_ok; messages.append(msg)
        step_ok, msg = save_online_setting(sheet_id, "setup_reset_at", utc_now_text())
        ok = ok and step_ok; messages.append(msg)
    clear_online_cache(sheet_id)
    return ok, "Setup guide updated." if ok else safe_user_message(messages[-1] if messages else "Could not update setup guide.")



def setup_step_index(step_key: str) -> int:
    legacy = {"exports": "calendar", "google_calendar": "calendar", "google_tasks": "tasks"}
    step_key = legacy.get(step_key, step_key)
    return SETUP_STEP_KEYS.index(step_key) if step_key in SETUP_STEP_KEYS else 0


def setup_area_options(sheet_id: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    df = active_online_df(read_online_table(sheet_id, "areas"))
    options: list[str] = []
    mapping: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        label = str(row.get("area_name", "") or "").strip()
        if not label:
            continue
        options.append(label)
        mapping[label] = {"area_id": str(row.get("area_id", "") or ""), "area_name": label}
    return options, mapping


def setup_goal_options(sheet_id: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    df = active_online_df(read_online_table(sheet_id, "goals"))
    options: list[str] = []
    mapping: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        label = str(row.get("title", "") or "").strip()
        if not label:
            continue
        options.append(label)
        mapping[label] = {
            "goal_id": str(row.get("goal_id", "") or ""),
            "area_id": str(row.get("area_id", "") or ""),
            "area_name": str(row.get("area_name", "") or ""),
        }
    return options, mapping


def setup_routine_options(sheet_id: str) -> tuple[list[str], dict[str, dict[str, str]]]:
    df = active_online_df(read_online_table(sheet_id, "routines"))
    options: list[str] = []
    mapping: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        label = str(row.get("title", "") or "").strip()
        if not label:
            continue
        options.append(label)
        mapping[label] = {
            "routine_id": str(row.get("routine_id", "") or ""),
            "area_id": str(row.get("area_id", "") or ""),
            "area_name": str(row.get("area_name", "") or ""),
        }
    return options, mapping


def setup_next_step(sheet_id: str, current_idx: int) -> tuple[bool, str]:
    if current_idx >= len(SETUP_STEPS) - 1:
        return save_setup_state(sheet_id, completed=True, current_step=SETUP_STEPS[-1][0])
    return save_setup_state(sheet_id, status="in_progress", current_step=SETUP_STEPS[current_idx + 1][0])


def setup_back_step(sheet_id: str, current_idx: int) -> tuple[bool, str]:
    if current_idx > 0:
        return save_setup_state(sheet_id, status="in_progress", current_step=SETUP_STEPS[current_idx - 1][0])
    return True, "Already at the first setup step."


def setup_skip_for_now() -> None:
    st.session_state["skip_online_setup_for_session"] = True


def display_first_of_next_month() -> str:
    today = date.today()
    year = today.year + (1 if today.month == 12 else 0)
    month = 1 if today.month == 12 else today.month + 1
    return date(year, month, 1).strftime("%d-%m-%Y")


def render_colour_preview(label: str) -> None:
    colour = GOOGLE_COLOUR_BY_LABEL.get(label, {"hex": "#7986CB", "name": label})
    safe_name = html.escape(str(colour.get("name", label)))
    safe_hex = html.escape(str(colour.get("hex", "#7986CB")))
    st.markdown(
        f"<div class='area-colour-preview' style='border-left-color:{safe_hex}'><span class='area-colour-dot' style='background:{safe_hex}'></span><span>Selected calendar colour: <strong>{safe_name}</strong></span></div>",
        unsafe_allow_html=True,
    )


def render_setup_focus_step(sheet_id: str) -> None:
    current_focus = online_setting(sheet_id, "weekly_focus", "")
    st.markdown("""
    <div class='setup-example'><strong>Example:</strong> This week, protect sleep and make time for one small sketching action.</div>
    """, unsafe_allow_html=True)
    st.write("Choose a simple focus for the week. It helps you decide what belongs in the calendar first, before the system fills with details.")
    with st.form("setup_focus_form"):
        focus = st.text_area("Main focus for this week", value=current_focus, placeholder="For example, protect sleep and make time for one sketching action.", height=90)
        save = st.form_submit_button("Save weekly focus", use_container_width=True)
    if save:
        if not focus.strip():
            st.warning("Add a short weekly focus before saving, or move to the next step and come back later.")
        else:
            ok, message = save_online_setting(sheet_id, "weekly_focus", focus.strip())
            st.success("Weekly focus saved.") if ok else st.warning(safe_user_message(message))


def render_setup_area_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Example Area:</strong> Body and Stability — sleep, movement, health appointments and routines that support energy.</div>
    """, unsafe_allow_html=True)
    name = st.text_input("Area name", placeholder="For example, Body and Stability", key="setup_area_name")
    description = st.text_area("What belongs here?", placeholder="Sleep, movement, strength, mobility, health appointments and routines that support energy.", height=90, key="setup_area_description")
    colour_label = st.selectbox("Calendar colour", GOOGLE_COLOUR_LABELS, index=1, key="setup_area_colour", help="Areas form the basis for calendar grouping.")
    render_colour_preview(st.session_state.get("setup_area_colour", colour_label))
    if st.button("Save this Area", use_container_width=True, key="setup_area_save"):
        if not name.strip():
            st.warning("Add an Area name before saving.")
        else:
            chosen_colour = st.session_state.get("setup_area_colour", colour_label)
            colour = GOOGLE_COLOUR_BY_LABEL.get(chosen_colour, {}).get("code", chosen_colour)
            ok, message = append_online_record(sheet_id, "areas", {
                "area_id": f"area-{uuid.uuid4().hex}",
                "area_name": name.strip(),
                "description": description.strip(),
                "colour": colour,
                "status": "active",
                "default_calendar": name.strip(),
                "default_task_list": "Pathmark",
            })
            st.success("Area saved. You can add more Areas now or continue to routines.") if ok else st.warning(safe_user_message(message))
            if ok:
                st.rerun()


def render_setup_routine_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Example routine container:</strong> Strength training. <strong>Example routine activities:</strong> Strength training A on Monday, Strength training B on Tuesday.</div>
    """, unsafe_allow_html=True)
    st.write("Create a routine container, then add one or more routine activities. The activities are what feed the tasklist, Google Calendar blocks and Google Tasks first-step prompts.")
    render_routine_manager(sheet_id)


def render_setup_goal_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>SMART-style example:</strong> Build a sketching habit by completing three beginner exercises by the first day of next month.</div>
    """, unsafe_allow_html=True)
    st.write("Set up the goal or project as the container. Then add goal activities as one-off steps. Recurring work belongs under Routines.")
    render_goal_manager(sheet_id)


def render_setup_action_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Example goal activity:</strong> Purchase a beginner sketching guide. <strong>First-step prompt:</strong> search for one beginner guide and save two options.</div>
    """, unsafe_allow_html=True)
    st.write("Goal activities are usually one-off steps. If the same work repeats, create it as a routine activity instead.")
    goal_options, goal_map = setup_goal_options(sheet_id)
    if not goal_options:
        st.info("Create at least one goal first, then add the next one or two goal activities that would move it forward.")
        return
    goal_label = st.selectbox("Choose the goal to add an activity to", goal_options, key="setup_goal_activity_parent")
    goal = goal_map.get(goal_label, {})
    _action_form(
        sheet_id,
        goal_id=str(goal.get("goal_id", "")),
        default_area=str(goal.get("area_name", "")),
        form_key=f"setup_goal_activity_{goal.get('goal_id', 'new')}",
    )

def render_setup_review_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Why this comes early:</strong> The Review Queue is Pathmark's safety check. It helps you spot missing links before you export anything.</div>
    """, unsafe_allow_html=True)
    st.write("As you add Areas, routines, goals and actions, this page checks whether they have enough information to work together.")
    render_review_queue_manager(sheet_id)


def render_setup_tasklist_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Paper option:</strong> Use the tasklist when you prefer ticking things off by hand instead of using Google Tasks.</div>
    """, unsafe_allow_html=True)
    st.write("Select saved routine activities and goal actions. This uses the same tasklist builder you will use later.")
    render_tasklist_manager(sheet_id)


def render_setup_calendar_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Make time:</strong> Calendar export is how routines and goal actions become time blocks, rather than staying as intentions.</div>
    """, unsafe_allow_html=True)
    st.write("Preview and export the actions that are ready for your calendar. Exported items can then move to Archive so the active workspace stays clear.")
    render_google_calendar_export_manager(sheet_id)


def render_setup_tasks_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Start smaller:</strong> Google Tasks prompts are for the first tiny step: put on running shoes, open the sketchbook, or pack gym clothes.</div>
    """, unsafe_allow_html=True)
    st.write("Preview prompts from your saved routine activities and goal actions. These use the same Google Tasks export flow you will use later.")
    render_google_tasks_export_manager(sheet_id)


def render_setup_archive_step(sheet_id: str) -> None:
    st.markdown("""
    <div class='setup-example'><strong>Keep the workspace clear:</strong> Archive exported, completed or paused work so active Pathmark stays light enough to duck in and out of.</div>
    """, unsafe_allow_html=True)
    st.write("Archive does not have to mean gone forever. Restore an item if you decide it belongs back in the active workspace.")
    render_archive_manager(sheet_id)


def render_setup_step_safe(label: str, func, sheet_id: str) -> None:
    try:
        func(sheet_id)
    except Exception as exc:
        st.warning(f"Pathmark could not open this setup step just now. Please refresh online data and try again.")
        if str(current_user().get('role', '')).lower() == 'developer':
            with st.expander("Developer diagnostics", expanded=False):
                st.code(repr(exc))

def render_setup_pathway_primary(sheet_id: str) -> None:
    state = get_setup_state(sheet_id)
    current_idx = setup_step_index(state["current_step"])
    key, name, desc = SETUP_STEPS[current_idx]

    st.markdown("<div class='setup-step-label'>Guided setup</div>", unsafe_allow_html=True)
    st.markdown("## Set up Pathmark")
    st.write("Work through the real Pathmark flow once. You can edit anything later, skip setup, or return to this guide from Settings.")

    progress = (current_idx + 1) / max(len(SETUP_STEPS), 1)
    pct = round(min(max(progress, 0), 1) * 100)
    st.markdown(f"<div class='setup-progress-wrap'><div class='setup-progress-fill' style='width:{pct}%'></div></div>", unsafe_allow_html=True)
    st.caption(f"Step {current_idx + 1} of {len(SETUP_STEPS)} · {name}")

    nav_left, setup_body, nav_right = st.columns([0.07, 0.86, 0.07], gap="small")
    with nav_left:
        st.markdown("<div class='setup-side-arrow'></div>", unsafe_allow_html=True)
        if current_idx > 0:
            if st.button("‹", use_container_width=True, key=f"setup_back_{key}", help="Back"):
                setup_back_step(sheet_id, current_idx)
                st.rerun()
        else:
            st.button("‹", use_container_width=True, disabled=True, key=f"setup_back_disabled_{key}", help="Back")
    with setup_body:
        st.markdown("<div class='setup-working-card'>", unsafe_allow_html=True)
        st.markdown(f"### {name}")
        st.write(desc)

        if key == "focus":
            render_setup_step_safe("focus", render_setup_focus_step, sheet_id)
        elif key == "review":
            render_setup_step_safe("review", render_setup_review_step, sheet_id)
        elif key == "areas":
            render_setup_step_safe("areas", render_setup_area_step, sheet_id)
        elif key == "routines":
            render_setup_step_safe("routines", render_setup_routine_step, sheet_id)
        elif key == "goals":
            render_setup_step_safe("goals", render_setup_goal_step, sheet_id)
        elif key == "actions":
            render_setup_step_safe("actions", render_setup_action_step, sheet_id)
        elif key == "tasklist":
            render_setup_step_safe("tasklist", render_setup_tasklist_step, sheet_id)
        elif key == "calendar":
            render_setup_step_safe("calendar", render_setup_calendar_step, sheet_id)
        elif key == "tasks":
            render_setup_step_safe("tasks", render_setup_tasks_step, sheet_id)
        elif key == "archive":
            render_setup_step_safe("archive", render_setup_archive_step, sheet_id)
        st.markdown("</div>", unsafe_allow_html=True)
    with nav_right:
        st.markdown("<div class='setup-side-arrow'></div>", unsafe_allow_html=True)
        if current_idx < len(SETUP_STEPS) - 1:
            if st.button("›", use_container_width=True, key=f"setup_next_{key}", help="Next"):
                setup_next_step(sheet_id, current_idx)
                st.rerun()
        else:
            if st.button("›", use_container_width=True, key="setup_continue_workspace", help="Continue to workspace"):
                with st.spinner("Opening your workspace..."):
                    save_setup_state(sheet_id, completed=True, current_step=key)
                st.session_state["skip_online_setup_for_session"] = True
                st.rerun()
    st.caption("Use the right arrow to continue to the next setup step. The final arrow opens your workspace.")
    st.markdown("<div class='setup-skip'></div>", unsafe_allow_html=True)
    if st.button("Skip setup for now", use_container_width=True, key=f"setup_skip_{key}"):
        setup_skip_for_now()
        st.rerun()

def render_setup_pathway(sheet_id: str) -> None:
    """Compatibility wrapper retained for older calls."""
    render_setup_pathway_primary(sheet_id)

def render_online_overview(sheet_id: str) -> None:
    st.subheader("Home")
    data = read_online_tables(sheet_id)
    counts = {name: len(active_online_df(df)) for name, df in data.items() if name in ["areas", "goals", "routines", "actions"]}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Areas", counts.get("areas", 0))
    c2.metric("Goals", counts.get("goals", 0))
    c3.metric("Routines", counts.get("routines", 0))
    c4.metric("Activities", counts.get("actions", 0))

    focus = online_setting(sheet_id, "weekly_focus", "")
    st.markdown("### Main focus this week")
    with st.form("weekly_focus_home_form"):
        new_focus = st.text_area("What should Pathmark protect or move forward this week?", value=focus, placeholder="For example, protect sleep and schedule one sketching action.", height=90)
        save_focus = st.form_submit_button("Save weekly focus", use_container_width=True)
    if save_focus:
        ok, message = save_online_setting(sheet_id, "weekly_focus", new_focus.strip())
        st.success("Weekly focus saved.") if ok else st.warning(safe_user_message(message))

    st.markdown("""
    <div class="guide-box"><strong>Your active workspace.</strong><br>
    Pathmark is designed so you can duck in and out: keep active routines, routine activities and goal activities visible, export the items you are ready to act on, then move exported work to Archive so the workspace stays clear.</div>
    """, unsafe_allow_html=True)
    if not counts.get("areas") and not counts.get("goals") and not counts.get("routines"):
        st.info("Use Settings to revisit guided setup, or start by creating an Area, then routines, then goals.")
    st.markdown("""
    <div class="grid-3">
      <div class="process-card"><h4>Make time</h4><p>Calendar exports turn routines and goal actions into time blocks rather than leaving them as vague intentions.</p></div>
      <div class="process-card"><h4>Start smaller</h4><p>Google Tasks prompts can be written as the first tiny step, such as putting on running shoes or opening the sketchbook.</p></div>
      <div class="process-card"><h4>Keep it clear</h4><p>Move exported or completed items to Archive, then restore them if you need them again.</p></div>
    </div>
    """, unsafe_allow_html=True)

def download_tab() -> None:
    version = load_version()
    windows_package = find_windows_package(version.get("windows_package", ""))
    if ICON_PATH.exists():
        st.image(str(ICON_PATH), width=54)
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">Routines. Prompts. Progress.</div>
      <h1>Pathmark</h1>
      <p class="lead">Make time for routines, keep goals moving, and start the next action with less friction.</p>
      <p class="sublead">Pathmark helps you put routines and goal actions into your calendar, then create Google Tasks prompts or a printable tasklist so the day has a clear first step.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="grid-3">
      <div class="card"><h3>Put it in the calendar</h3><p>Routine activities and goal activities become calendar blocks, so the work has a real place in the week.</p></div>
      <div class="card"><h3>Keep goals from drifting</h3><p>Track competing goals and interests in one place, then define only the next one or two useful actions.</p></div>
      <div class="card"><h3>Lower the activation energy</h3><p>Use Google Tasks prompts for tiny first steps, or print a paper tasklist if ticking things off by hand works better for you.</p></div>
    </div>
    """, unsafe_allow_html=True)
    st.header("Two ways to use Pathmark")
    st.markdown("""
    <div class="grid-2">
      <div class="card"><h3>Pathmark Online</h3><p>Sign in to manage routines, goals, actions, tasklists, and exports from a browser. Your planning records are saved in a Google Sheet that belongs to you.</p></div>
      <div class="card"><h3>Pathmark Desktop</h3><p>Use the Windows app when you want local Workspace folders, Markdown records, backups, and desktop publishing/export workflows.</p></div>
    </div>
    """, unsafe_allow_html=True)
    st.header("Download Pathmark")
    st.markdown(f"""
    <div class="meta-grid">
      <div class="meta-card"><div class="meta-label">Latest version</div><div class="meta-value">{version.get('version', 'unknown')}</div></div>
      <div class="meta-card"><div class="meta-label">Release date</div><div class="meta-value">{version.get('release_date', 'unknown')}</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="download-panel">
      <h3>Windows app</h3>
      <p>Download the package, extract it, move the extracted <strong>Pathmark</strong> app folder into <strong>Documents</strong>, then run <strong>build_launcher_exe.bat</strong> once. The launcher lets you set the Workspace before opening the app.</p>
    </div>
    """, unsafe_allow_html=True)
    if windows_package is not None:
        st.download_button("Download Pathmark for Windows", data=windows_package.read_bytes(), file_name=windows_package.name, mime="application/zip", use_container_width=True, key="download_windows")
    else:
        st.error("The Windows package is missing from this release hub. Check that a file named Pathmark_Local_App_Windows_v*.zip exists in the downloads folder.")
    st.caption("This release is Windows-only for now. Mac package support has been removed while the Windows workflow is stabilised.")
    st.header("How the folders work")
    st.markdown("""
    <div class="grid-2">
      <div class="card"><h3>App folder</h3><p><strong>Documents\\Pathmark</strong> contains the replaceable app files and launcher. This is the folder you replace when updating.</p></div>
      <div class="card"><h3>Workspace folder</h3><p><strong>Documents\\Workspace</strong> is the default place for your projects, numbered Areas, exports, tasklists, backups, and database. You can choose another Workspace in the launcher.</p></div>
    </div>
    """, unsafe_allow_html=True)
    st.header("Install")
    st.markdown("""
    1. Download the Windows package.
    2. Extract the zip file.
    3. Move the extracted `Pathmark` app folder into your Documents folder.
    4. Open the `Pathmark` app folder and run `build_launcher_exe.bat` once to create `Pathmark.exe`.
    5. Open `Pathmark.exe`, review or change the Workspace field, then open Pathmark.

    The default Workspace is `Documents\\Workspace`. Pathmark will create it if needed, or you can choose an existing folder before opening the app.
    """)
    st.header("Update")
    st.markdown("""
    <div class="safe-rule"><strong>Replace the app folder only.</strong><br>Open <strong>Pathmark.exe</strong> and choose <strong>Check for updates</strong>. Then replace only <code>Documents\\Pathmark</code>. Do not replace <code>Documents\\Workspace</code> or whichever Workspace folder you selected.</div>
    """, unsafe_allow_html=True)
    st.info("Privacy, storage, and permission details are now in the separate About & Privacy tab so the homepage stays focused on what Pathmark does.")
    st.header("Release notes")
    for note in version.get("notes", []):
        st.write(f"- {note}")



def about_privacy_tab() -> None:
    st.header("About & Privacy")
    st.write(
        "Pathmark uses a small number of services so the online app can run in a browser while keeping your planning records in a file you own. "
        "This page explains what Pathmark accesses and where each kind of information is stored."
    )

    st.subheader("The short version")
    st.markdown("""
    <div class="grid-2">
      <div class="card"><h3>Your planning records</h3><p>Pathmark Online saves your Areas, routines, goals, actions, setup progress, tasklists, export records and archive status in your <strong>Pathmark Sync</strong> Google Sheet.</p></div>
      <div class="card"><h3>Your Google Drive</h3><p>Pathmark uses Google's limited <strong>drive.file</strong> permission. It can create and update Pathmark files you use with the app; it is not given broad access to every file in your Drive.</p></div>
      <div class="card"><h3>Your access profile</h3><p>Supabase stores only small access/profile details: email, role, account status, feature flags, theme preference and audit records.</p></div>
      <div class="card"><h3>The app code</h3><p>GitHub stores the Pathmark code, release packages, documentation and database migrations. The current release package has been checked for obvious secrets and private planning records.</p></div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("What Google access lets Pathmark do")
    st.markdown("""
    When you sign in, Pathmark uses Google for two jobs:

    1. **Sign-in** — Google confirms your email address so Pathmark can apply the correct access level.
    2. **Your Pathmark Sync sheet** — Pathmark creates or updates the Google Sheet that stores your online planning records.

    Pathmark uses the limited `drive.file` permission. In practical terms, Pathmark works with Pathmark files it creates or files you explicitly use with Pathmark. It does **not** request the broader Google Drive permission that would allow general access to all Drive files.
    """)
    st.markdown("""
    <div class="safe-rule"><strong>Pathmark does not collect your Google password.</strong><br>You sign in on Google's page. Pathmark receives confirmation from Google after you approve access.</div>
    """, unsafe_allow_html=True)

    st.subheader("Where information is stored")
    st.markdown("""
    | Information | Where it is stored | What that means |
    |---|---|---|
    | Areas, routines, goals, actions, setup progress, tasklists, export records and archive status | Your Pathmark Sync Google Sheet | This is your online Pathmark workspace. It sits in your Google Drive and is visible to you. |
    | Local Workspace folders, Markdown files, local exports, backups and desktop tasklists | Your chosen Workspace folder on your computer | These are created by Pathmark Desktop, not by Pathmark Online. |
    | Email, access role, account status, feature flags, theme preference and audit records | Supabase | This controls beta/developer access and basic profile behaviour. It does not contain your planning records. |
    | App code, release files, public documentation and Supabase migration files | GitHub | This is the public/deployment codebase. The current package does not contain Google OAuth tokens, Supabase secret keys, client secrets or private planning records. |
    | Google OAuth client secrets, Supabase secret keys and deployment secrets | Streamlit secrets | These are deployment credentials held outside the GitHub repository. |
    """)

    st.subheader("What Pathmark stores in each service")
    st.markdown("""
    **Google Sheet** stores your online Pathmark records.  
    **Supabase** stores access/profile metadata only.  
    **GitHub** stores code and release files only.  
    **Streamlit** hosts the app and stores deployment secrets outside the repository.

    The current release package has been checked for obvious secret patterns and private planning records before packaging. No real Supabase secret key, Google client secret, OAuth token, private key or private planning sheet was found in the release package.
    """)

    st.subheader("Disconnecting or deleting")
    st.markdown("""
    - You can disconnect Google access from **Pathmark Online → Settings**. This revokes the current Google token and stops Pathmark from writing to your Pathmark Sync sheet until you sign in again.
    - You can also remove Pathmark from your Google Account permissions.
    - Pathmark Online now includes a deletion option in **Settings** for users who want to remove their online Pathmark data from Google Drive and disconnect access.
    - That deletion workflow only lists files Pathmark can identify as Pathmark files available to this app, such as the connected **Pathmark Sync** sheet or app-tagged Pathmark files. Pathmark does not delete Drive folders simply because they are named Pathmark.
    - You can also open, copy, export or delete your Pathmark Sync sheet directly from Google Drive.
    - Deleting online Pathmark data does not delete local Workspace files on your computer.
    """)

    with st.expander("Service-by-service summary", expanded=False):
        st.markdown("""
        **Google**  
        Used for sign-in and for your own Pathmark Sync sheet. Pathmark requests `drive.file`, which limits access to files Pathmark creates or files you explicitly authorise for Pathmark. Pathmark does not have general access to your whole Google Drive.

        **Streamlit**  
        Hosts the Pathmark web app. Deployment credentials are kept in Streamlit secrets, outside the GitHub repository.

        **Supabase**  
        Stores access/profile metadata only: email, role, account status, feature flags, audit logs and theme preference. Supabase does not store your goals, routines, tasklists, calendar rows or private planning content.

        **GitHub**  
        Stores code, release packages, documentation and database migration files. The release package has been checked so it does not contain private planning sheets, Workspace folders, Google OAuth tokens, Supabase secret keys or Google client secrets.
        """)

    with st.expander("Sources behind this explanation", expanded=False):
        st.markdown("""
        This explanation is based on how Pathmark currently uses each service and on the relevant provider documentation:

        - Google API Services User Data Policy: apps need to clearly explain what Google user data they access, use, store, delete or share.
        - Google Drive API scope guidance: `drive.file` is the limited Drive scope for files the app creates or the user authorises for the app.
        - Streamlit secrets management guidance: secrets should be stored in Streamlit's secrets system or another secrets manager rather than committed to the repository.
        - Supabase API key guidance: secret keys are server-side keys and must not be exposed publicly.
        - GitHub secret scanning guidance: repositories should be monitored for hardcoded credentials and tokens.
        """)

    st.caption("This page explains the current Pathmark beta design. It is not a formal legal privacy policy, but it is intended to help beta testers understand what access they are granting and where their information is stored.")

def render_connection_summary(credentials: Any, sheet_id: str, auth_ready: bool) -> None:
    """Show a compact connection state without exposing OAuth plumbing."""
    if credentials and sheet_id:
        st.success("Pathmark Online is ready. Your planning records are saved to your Pathmark Sync sheet, and Google Sheets access is active for this session.")
    elif credentials:
        st.info("Google access is ready. Pathmark is preparing your sync sheet.")
    elif auth_ready:
        st.info("Sign in with Google to use Pathmark Online.")
    else:
        st.warning("Google access is not configured for this deployment.")

def on_the_go_tab() -> None:
    handle_google_oauth_redirect()
    st.header("Pathmark Online beta")
    auth_ready = web_oauth_available()
    credentials = google_credentials_from_session()
    should_prepare_sheet = bool(credentials and not st.session_state.get("sync_sheet_id"))
    if should_prepare_sheet and (st.session_state.pop("auto_create_sync_sheet_after_connect", False) or not st.session_state.get("sync_sheet_ready_attempted")):
        st.session_state["sync_sheet_ready_attempted"] = True
        ok, sheet_id_found, message = ensure_pathmark_sync_sheet_ready()
        if not ok:
            st.warning(safe_user_message(message))

    sheet_id = st.session_state.get("sync_sheet_id", "")
    render_connection_summary(credentials, sheet_id, auth_ready)

    if not credentials and auth_ready:
        auth_url = login_auth_url()
        if auth_url:
            st.link_button("Sign in with Google", auth_url, use_container_width=True)
        st.caption("Pathmark asks for permission to create or update Pathmark files you use with the app. Details are in About & Privacy.")
        return

    if not (credentials and sheet_id):
        st.info("Pathmark is still preparing your online workspace. Refresh online data or reconnect from Settings if this does not resolve.")
        return

    apply_online_theme(sheet_id)

    service = sheets_service()
    if service is not None:
        try:
            with st.spinner("Loading your Pathmark Online workspace from Google Sheets..."):
                ensure_pathmark_online_schema(service, sheet_id)
                load_online_tables(sheet_id)
        except Exception:
            st.warning("Pathmark could not prepare your online workspace. Please refresh online data or reconnect Google access, then try again.")

    setup_state = get_setup_state(sheet_id)
    if setup_state.get("status") != "completed" and not st.session_state.get("skip_online_setup_for_session"):
        render_setup_pathway_primary(sheet_id)
        return

    sections = st.tabs([
        "Home",
        "Review Queue",
        "Areas",
        "Routines",
        "Goals and Projects",
        "Tasklist",
        "Google Calendar Export",
        "Google Tasks Export",
        "Archive",
        "Settings",
    ])
    with sections[0]:
        render_safe_section("Home", render_online_overview, sheet_id)
    with sections[1]:
        render_safe_section("Review Queue", render_review_queue_manager, sheet_id)
    with sections[2]:
        render_safe_section("Areas", render_area_manager, sheet_id)
    with sections[3]:
        render_safe_section("Routines", render_routine_manager, sheet_id)
    with sections[4]:
        render_safe_section("Goals and Projects", render_goal_manager, sheet_id)
    with sections[5]:
        render_safe_section("Tasklist", render_tasklist_manager, sheet_id)
    with sections[6]:
        render_safe_section("Google Calendar Export", render_google_calendar_export_manager, sheet_id)
    with sections[7]:
        render_safe_section("Google Tasks Export", render_google_tasks_export_manager, sheet_id)
    with sections[8]:
        render_safe_section("Archive", render_archive_manager, sheet_id)
    with sections[9]:
        render_safe_section("Settings", render_online_settings, sheet_id)

def developer_tab() -> None:
    st.header("Developer settings")
    st.write("Manage hosted access roles for beta features. Unknown signed-in users default to standard access.")
    st.markdown("""
    Roles:
    - **standard**: download homepage only.
    - **beta_tester**: On-the-go beta access.
    - **developer**: beta access plus this developer panel.
    """)
    actor = current_user().get("email", "")
    if supabase_available():
        st.success("Supabase access management is connected. Supabase is used only for roles, feature flags, and audit logs. It does not store Pathmark goals, routines, task prompts, Workspace files, or on-the-go planning entries.")
    else:
        st.info("Persistent role management is not configured yet. Bootstrap developer and beta access can still be supplied through Streamlit secrets, but role assignments cannot be saved from this page until Supabase is configured.")
        with st.expander("Supabase access-layer setup", expanded=True):
            st.markdown("""
            Create a Supabase project for hosted Pathmark access control, then add the project URL and a Supabase Secret API key to Streamlit secrets. Use an `sb_secret_...` key from Supabase **Settings → API Keys**. Keep it in Streamlit secrets only. Do not commit it to GitHub.

            ```toml
            [supabase]
            url = "https://YOUR_PROJECT_ID.supabase.co"
            secret_key = "sb_secret_YOUR_SUPABASE_SECRET_API_KEY"
            ```

            Legacy `service_role_key` is still accepted as a fallback for older projects, but new setups should use `secret_key`.

            The same schema is now versioned in `supabase/migrations/20260531000000_create_pathmark_access_tables.sql`. If you are not applying migrations through the Supabase GitHub integration, run this SQL in the Supabase SQL editor:

            ```sql
            create table if not exists pathmark_users (
              email text primary key,
              role text not null default 'standard' check (role in ('standard', 'beta_tester', 'developer')),
              status text not null default 'active' check (status in ('active', 'disabled')),
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now(),
              last_login timestamptz,
              notes text,
              theme_preference text not null default 'Default'
            );

            create table if not exists pathmark_feature_flags (
              key text primary key,
              enabled boolean not null default true,
              minimum_role text not null default 'standard' check (minimum_role in ('standard', 'beta_tester', 'developer')),
              updated_at timestamptz not null default now(),
              notes text
            );

            create table if not exists pathmark_audit_log (
              id uuid primary key default gen_random_uuid(),
              actor_email text,
              action text not null,
              target_email text,
              details jsonb not null default '{}'::jsonb,
              created_at timestamptz not null default now()
            );

            alter table pathmark_users enable row level security;
            alter table pathmark_feature_flags enable row level security;
            alter table pathmark_audit_log enable row level security;

            insert into pathmark_feature_flags (key, enabled, minimum_role, notes)
            values
              ('on_the_go_beta', true, 'beta_tester', 'Shows the On-the-go beta tab.'),
              ('developer_panel', true, 'developer', 'Shows the Developer settings tab.')
            on conflict (key) do nothing;
            ```

            Keep this separate from user-owned Pathmark sync sheets. Supabase is the access layer only; user planning data remains in the Workspace and in any user-authorised sync sheet.
            """)

    st.subheader("Bootstrap access from Streamlit secrets")
    access_summary = pd.DataFrame([
        {"list": "developer_emails", "emails": ", ".join(sorted(configured_developer_emails())) or "—"},
        {"list": "beta_tester_emails", "emails": ", ".join(sorted(configured_beta_emails())) or "—"},
        {"list": "disabled_emails", "emails": ", ".join(sorted(configured_disabled_emails())) or "—"},
    ])
    st.dataframe(access_summary, use_container_width=True, hide_index=True)

    records = list_supabase_users()
    if records:
        st.subheader("Supabase user records")
        st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)
    elif supabase_available():
        st.caption("Supabase is connected, but no user records have been saved yet. The first signed-in users may be auto-created as standard users.")

    st.subheader("Assign or update a user role")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        email = st.text_input("User email").strip().lower()
    with c2:
        role = st.selectbox("Role", ROLE_VALUES, index=0)
    with c3:
        status = st.selectbox("Status", STATUS_VALUES, index=0)
    notes = st.text_input("Notes", placeholder="Optional admin note")
    if st.button("Save user access", use_container_width=True):
        ok, msg = upsert_supabase_user(email, role, status, notes=notes, actor_email=actor)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.warning(msg)

    st.subheader("Feature flags")
    flags = read_feature_flags()
    if flags:
        st.dataframe(pd.DataFrame(flags), use_container_width=True, hide_index=True)
    elif supabase_available():
        st.caption("No feature flags found. Use the setup SQL above to add the default flags.")
    else:
        st.caption("Feature flags use default role rules until Supabase is configured.")

    with st.expander("Security model", expanded=False):
        st.markdown("""
        Pathmark uses three separate layers:

        - **Google login** identifies the signed-in user. Pathmark does not collect or store passwords.
        - **Supabase access records** decide whether that verified user is standard, beta tester, developer, active, or disabled.
        - **User-owned Google sync sheets** are separate and are used only for on-the-go planning captures when the user authorises them.

        Supabase should not store goals, routines, Google Tasks prompts, calendar blocks, Workspace files, or other private planning content at this stage.
        """)


def render_app() -> None:
    # Complete Google login first. Handle Google Sheets OAuth immediately after,
    # before gated tabs are created, so a callback cannot fall back to the public
    # homepage if Streamlit starts a fresh session after Google's redirect.
    handle_login_redirect()
    params = st.query_params
    callback_state = params.get("state")
    if isinstance(callback_state, list):
        callback_state = callback_state[0] if callback_state else None
    if callback_state and str(callback_state).startswith("sheets:"):
        handle_google_oauth_redirect()
    user = current_user()
    role, status = resolve_role(user.get("email", ""), bool(user.get("email_verified", False)))
    if user.get("email"):
        inject_theme_css(theme_for_user(user.get("email", "")))
    maybe_record_login(user.get("email", ""), role, status)
    render_account_bar(role, user)
    if status == "disabled":
        st.error("This account has been disabled for the hosted Pathmark page.")
        return

    tabs = ["Home", "About & Privacy"]
    if role_can_use_on_the_go(role, status):
        tabs.append("Pathmark Online beta")
    if role_can_develop(role, status):
        tabs.append("Developer")
    created_tabs = st.tabs(tabs)
    with created_tabs[0]:
        download_tab()
    with created_tabs[1]:
        about_privacy_tab()
    idx = 2
    if role_can_use_on_the_go(role, status):
        with created_tabs[idx]:
            on_the_go_tab()
        idx += 1
    if role_can_develop(role, status):
        with created_tabs[idx]:
            developer_tab()


render_app()

st.caption("Pathmark release hub. Sign in to use Pathmark Online when it is enabled for your account.")
