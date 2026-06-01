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
    "areas": ["area_id", "area_name", "description", "colour", "status", "default_calendar", "default_task_list", "notes", "created_at", "updated_at", "source"],
    "goals": ["goal_id", "area_id", "area_name", "title", "description", "specific_area", "status", "target_date", "purpose", "desired_outcome", "closure_criteria", "notes", "created_at", "updated_at", "source"],
    "routines": ["routine_id", "area_id", "area_name", "title", "description", "frequency", "preferred_days", "duration_minutes", "status", "purpose", "next_due", "checklist", "calendar_block", "reminder", "starting_prompt", "task_reminder_time", "calendar_start_time", "calendar_end_time", "calendar_location", "created_at", "updated_at", "source"],
    "actions": ["action_id", "goal_id", "routine_id", "area_id", "area_name", "title", "description", "status", "priority", "specific_area", "due_date", "scheduled_date", "activity_days", "estimated_minutes", "calendar_block", "reminder", "include_tasklist", "first_step", "task_reminder_time", "calendar_start_time", "calendar_end_time", "calendar_location", "notes", "created_at", "updated_at", "source"],
    "calendar_blocks": ["block_id", "area_name", "title", "description", "start", "end", "recurrence", "linked_record_id", "status", "created_at", "updated_at", "source"],
    "task_prompts": ["prompt_id", "area_name", "title", "prompt_text", "linked_record_id", "status", "created_at", "updated_at", "source"],
    "tasklists": ["tasklist_id", "date", "title", "items", "status", "created_at", "updated_at", "source"],
    "google_tasks_export": ["Task ID", "Task List", "Title", "Notes", "Due Date", "Reminder Time", "Status", "Repeat Pattern", "Related Google Calendar Item", "exported_at"],
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

ONLINE_THEMES = {
    "Default": {"accent": "#334E68", "soft": "#E7EEF4", "surface": "#FFFFFF", "background": "#F7F6F2"},
    "Sage": {"accent": "#3F6F5C", "soft": "#EAF3EE", "surface": "#FFFFFF", "background": "#F7F8F3"},
    "Blue": {"accent": "#2F5D7C", "soft": "#E8F0F6", "surface": "#FFFFFF", "background": "#F6F8FA"},
    "Plum": {"accent": "#6B4E71", "soft": "#F0EAF2", "surface": "#FFFFFF", "background": "#F8F5F8"},
    "Warm": {"accent": "#8A5A34", "soft": "#F4EEE7", "surface": "#FFFFFF", "background": "#FAF7F1"},
}
VALID_FREQUENCIES = ["Daily", "Weekdays", "Weekly", "Monthly", "Custom"]
VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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
.hero { padding: 2.6rem 0 1.2rem 0; }
.eyebrow { display: inline-flex; padding: .42rem .72rem; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 760; font-size: .92rem; margin-bottom: 1.1rem; }
.hero h1 { font-size: clamp(3.7rem, 8.2vw, 7.2rem); line-height: .84; margin: 0 0 1rem 0; letter-spacing: -.085em; }
.lead { color: var(--ink); font-size: clamp(1.28rem, 2.4vw, 1.9rem); line-height: 1.22; max-width: 920px; font-weight: 680; margin: 0; }
.sublead { color: var(--muted); font-size: 1.12rem; max-width: 850px; margin-top: 1rem; }
.grid-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }
.grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }
.card { background: rgba(255,255,255,.88); border: 1px solid var(--line); border-radius: 1.35rem; padding: 1.25rem; box-shadow: 0 14px 34px var(--shadow); }
.card h3 { margin-top: 0; margin-bottom: .55rem; }
.card p { margin-bottom: 0; color: var(--muted); }
.meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: .9rem 0 2.1rem; }
.meta-card { background: rgba(255,255,255,.80); border: 1px solid var(--line); border-radius: 1.25rem; padding: 1rem 1.15rem; box-shadow: 0 10px 26px var(--shadow); }
.meta-label { color: var(--muted); font-size: .92rem; font-weight: 700; margin-bottom: .35rem; }
.meta-value { color: var(--ink); font-size: 1.9rem; line-height: 1.05; font-weight: 780; letter-spacing: -.045em; }
.download-panel { background: rgba(255,255,255,.70); border: 1px solid var(--line); border-radius: 1.25rem; padding: 1rem 1.1rem; margin-bottom: .75rem; }
.safe-rule { background: var(--surface-2); border: 1px solid var(--line); border-radius: 1.1rem; padding: 1rem 1.1rem; }
.profile-pill { display: inline-flex; gap: .45rem; align-items: center; padding: .46rem .72rem; border-radius: 999px; background: rgba(255,255,255,.78); border: 1px solid var(--line); color: var(--muted); font-weight: 700; }
.account-card { background: rgba(255,255,255,.72); border: 1px solid var(--line); border-radius: 1rem; padding: .75rem .9rem; margin-bottom: 1rem; }
.account-title { color: var(--muted); font-size: .84rem; font-weight: 760; text-transform: uppercase; letter-spacing: .03em; margin-bottom: .2rem; }
.account-value { color: var(--ink); font-weight: 720; }
.connection-card { background: rgba(255,255,255,.78); border: 1px solid var(--line); border-radius: 1.1rem; padding: 1rem 1.1rem; margin: .7rem 0 1rem; }
.connection-ok { color: #006B2E; font-weight: 760; }
.connection-warn { color: #7A4E00; font-weight: 760; }
.beta-note { background: #FFF8E6; border: 1px solid #E7D49B; border-radius: 1.1rem; padding: 1rem 1.1rem; color: #3B3325; }
/* High-contrast controls, especially on mobile. Streamlit can otherwise inherit low-contrast theme colours. */
.stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a {
  border-radius: .85rem !important;
  min-height: 3rem;
  font-weight: 760 !important;
  background: var(--accent) !important;
  color: #FFFFFF !important;
  border: 1px solid rgba(31,34,33,.18) !important;
  box-shadow: 0 8px 22px var(--shadow);
}
.stButton button *, .stDownloadButton button *, [data-testid="stLinkButton"] a * { color: #FFFFFF !important; }
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stLinkButton"] a:hover { filter: brightness(.96); color: #FFFFFF !important; }
.stButton button:disabled, .stDownloadButton button:disabled {
  background: #E2E5E3 !important;
  color: #4B5350 !important;
  border-color: #C9D0CC !important;
  box-shadow: none !important;
}
.stButton button:disabled *, .stDownloadButton button:disabled * { color: #4B5350 !important; }
.pathmark-link-button { display: inline-flex; align-items: center; justify-content: center; width: 100%; min-height: 3rem; padding: .55rem .85rem; border-radius: .85rem; background: var(--accent); color: #FFFFFF !important; text-decoration: none !important; font-weight: 760; border: 1px solid rgba(31,34,33,.18); box-shadow: 0 8px 22px var(--shadow); }
.pathmark-link-button:hover { filter: brightness(.96); text-decoration: none !important; color: #FFFFFF !important; }
@media (max-width: 640px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: 1.1rem; }
  .grid-3, .grid-2, .meta-grid { grid-template-columns: 1fr; }
  .hero h1 { font-size: clamp(3rem, 16vw, 4.6rem); }
  .stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a { min-height: 3.2rem; font-size: 1rem !important; }
}
.guide-box { background: rgba(255,255,255,.82); border: 1px solid var(--line); border-left: 6px solid var(--accent); border-radius: 1rem; padding: 1rem 1.1rem; margin: .7rem 0 1rem; }
.guide-box strong { color: var(--ink); }
.step-card { background: rgba(255,255,255,.86); border: 1px solid var(--line); border-radius: 1.15rem; padding: 1rem 1.1rem; margin: .45rem 0 1rem; box-shadow: 0 8px 20px var(--shadow); }
.step-card h3 { margin-top: 0; margin-bottom: .35rem; }
.step-card p { color: var(--muted); margin-bottom: .45rem; }
.pathmark-note { background: var(--accent-soft); border: 1px solid var(--line); border-radius: 1rem; padding: .9rem 1rem; margin: .65rem 0 1rem; color: var(--ink); }
.swatch-row { display:flex; gap:.45rem; flex-wrap:wrap; align-items:center; margin:.35rem 0 .85rem; }
.swatch { display:inline-flex; align-items:center; gap:.35rem; border:1px solid var(--line); border-radius:999px; background:white; padding:.25rem .55rem; font-size:.85rem; }
.swatch-dot { width:.8rem; height:.8rem; border-radius:50%; display:inline-block; border:1px solid rgba(0,0,0,.18); }
.swatch-row { display:flex; flex-wrap:wrap; gap:.45rem; margin:.5rem 0 .8rem; }
.process-card { background: rgba(255,255,255,.86); border:1px solid var(--line); border-radius:1rem; padding:1rem; margin:.55rem 0; }
.process-card h4 { margin:.05rem 0 .35rem 0; color:var(--ink); }
.process-card p { margin:0; color:var(--muted); }

[data-testid="stHeader"] { background: transparent; }
@media (max-width: 860px) { .grid-3, .grid-2, .meta-grid { grid-template-columns: 1fr; } }
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
    st.session_state["on_the_go_connected_notice"] = "Google Sheets access is ready for this session."


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
    if theme not in ONLINE_THEMES:
        theme = "Default"
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
        if theme not in ONLINE_THEMES:
            theme = "Default"
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
    """Persist the hosted theme with the user's Supabase access profile."""
    email = (email or "").strip().lower()
    theme_name = theme_name if theme_name in ONLINE_THEMES else "Default"
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
    return True, "Theme saved to your Pathmark profile."


def theme_for_user(email: str) -> str:
    """Return the user's hosted theme preference from session/Supabase."""
    cached = st.session_state.get("hosted_theme_preference")
    if cached in ONLINE_THEMES:
        return str(cached)
    rec = read_supabase_user(email) if email else None
    theme = rec.get("theme_preference", "Default") if rec else "Default"
    if theme not in ONLINE_THEMES:
        theme = "Default"
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
        if existing and existing.get("theme_preference") in ONLINE_THEMES:
            st.session_state["hosted_theme_preference"] = existing.get("theme_preference")
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
                    body={"appProperties": {"pathmark_sync": "true", "pathmark_version": "0.5.86"}},
                    fields="id",
                ).execute()
        except Exception:
            pass
        ensure_pathmark_online_schema(service, sheet_id)
        st.session_state["sync_sheet_id"] = sheet_id
        return True, sheet_id, spreadsheet.get("spreadsheetUrl", "")
    except Exception as exc:
        return False, "", f"Could not create a Pathmark sync sheet: {exc}"


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
    if "notes" in ONLINE_TABLES.get(table, []):
        updates["notes"] = reason
    return update_online_record(sheet_id, table, record_id, updates)


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
    if "<HttpError" in text or "Traceback" in text or "returned \"" in text or "googleapis.com" in text:
        return "Pathmark could not complete that action. Please refresh the online data or reconnect Google access, then try again."
    return text
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
    """Apply a Pathmark theme across the hosted page.

    Streamlit theme changes are not dynamic at runtime, so Pathmark uses CSS
    variables and a small set of overrides. These are deliberately applied to
    the whole app container, not just the settings section.
    """
    theme_name = theme_name if theme_name in ONLINE_THEMES else "Default"
    theme = ONLINE_THEMES.get(theme_name, ONLINE_THEMES["Default"])
    st.markdown(
        f"""
        <style>
        :root, [data-testid="stAppViewContainer"] {{
          --accent: {theme['accent']} !important;
          --accent-soft: {theme['soft']} !important;
          --surface: {theme['surface']} !important;
          --bg: {theme['background']} !important;
        }}
        [data-testid="stAppViewContainer"] {{
          background: radial-gradient(circle at 12% 0%, color-mix(in srgb, {theme['accent']} 16%, transparent), transparent 26rem),
                      radial-gradient(circle at 92% 8%, rgba(122,78,122,.12), transparent 24rem),
                      linear-gradient(180deg, #FBFAF7 0%, {theme['background']} 100%) !important;
        }}
        .eyebrow, .pathmark-note {{ background: {theme['soft']} !important; color: {theme['accent']} !important; }}
        .guide-box {{ border-left-color: {theme['accent']} !important; }}
        .stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a {{
          background: {theme['accent']} !important;
          color: #FFFFFF !important;
          border-color: rgba(31,34,33,.18) !important;
        }}
        .stButton button *, .stDownloadButton button *, [data-testid="stLinkButton"] a * {{ color: #FFFFFF !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_online_theme(sheet_id: str) -> None:
    theme_name = online_setting(sheet_id, "theme", st.session_state.get("hosted_theme_preference", "Default")) if sheet_id else st.session_state.get("hosted_theme_preference", "Default")
    inject_theme_css(theme_name)


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
    if freq == "Daily" and valid_days:
        problems.append("Daily routines should usually leave preferred days blank, because they repeat every day.")
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


def validate_online_action_dates_and_times(*, scheduled: str = "", due: str = "", start_time: str = "", end_time: str = "", prompt_time: str = "") -> list[str]:
    problems: list[str] = []
    if not valid_online_date(scheduled):
        problems.append("Scheduled date must be blank or a real date. Use YYYY-MM-DD, for example 2026-06-08.")
    if not valid_online_date(due):
        problems.append("Due date must be blank or a real date. Use YYYY-MM-DD, for example 2026-06-08.")
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
        base_date = action.get("scheduled_date") or action.get("due_date") or routine.get("next_due") or ""
        start, end = online_event_bounds(base_date, action.get("calendar_start_time") or routine.get("calendar_start_time") or "09:00", action.get("calendar_end_time") or routine.get("calendar_end_time") or "10:00")
        recurrence = simple_rrule(routine.get("frequency"), action.get("activity_days")) if routine_id else ""
        parent = routines.get(routine_id, {}).get("title") or goals.get(goal_id, {}).get("title") or ""
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
        goal = goals.get(goal_id, {})
        area_name = action.get("area_name", "") or routine.get("area_name", "") or goal.get("area_name", "")
        defaults = area_defaults(sheet_id, str(area_name))
        first = str(action.get("first_step", "") or "").strip() or str(action.get("title", "") or "Pathmark task").strip()
        parent = routine.get("title") or goal.get("title") or ""
        base_note = str(action.get("notes") or action.get("description") or "")
        repeat = routine.get("frequency", "") if routine_id else ""
        linked = linked_calendar_summary_for_action(action, blocks)
        note_parts = [f"Routine: {parent}" if routine_id and parent else f"Goal: {parent}" if goal_id and parent else "", base_note, f"Repeat pattern: {repeat}." if repeat else "", linked]
        rows.append({
            "id": aid,
            "title": first,
            "area_name": area_name,
            "parent": parent,
            "due_date": action.get("scheduled_date") or action.get("due_date") or routine.get("next_due") or "",
            "reminder_time": action.get("task_reminder_time") or action.get("calendar_start_time") or routine.get("task_reminder_time") or "09:00",
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
        return pd.DataFrame(columns=["source_type", "title", "area_name", "parent", "status", "scheduled_date", "due_date", "first_step", "estimated_minutes"])
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
        parent = routines.get(routine_id, {}).get("title") or goals.get(goal_id, {}).get("title") or ""
        rows.append({
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
    df = read_online_table(sheet_id, "areas")
    df = active_online_df(df)
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
            with st.form("online_add_area", clear_on_submit=True):
                name = st.text_input("Area name")
                description = st.text_area("Description", height=90)
                colour_label = st.selectbox("Google Calendar colour", GOOGLE_COLOUR_LABELS, index=0, help="Choose the colour Pathmark should use for this Area in Google Calendar exports.")
                render_google_colour_swatch(colour_label)
                colour = google_colour_code(colour_label)
                c1, c2 = st.columns(2)
                default_calendar = c1.text_input("Default Google Calendar", placeholder="Usually the Area name")
                default_task_list = c2.text_input("Default Google Tasks list", placeholder="Usually Pathmark or the Area name")
                notes = st.text_area("Notes", height=70)
                submitted = st.form_submit_button("Save Area", use_container_width=True)
                if submitted:
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
            with st.form(f"online_edit_area_{selected_id}"):
                name = st.text_input("Area name", value=str(row.get("area_name", "")))
                description = st.text_area("Description", value=str(row.get("description", "")), height=100)
                colour_label = st.selectbox("Google Calendar colour", GOOGLE_COLOUR_LABELS, index=GOOGLE_COLOUR_LABELS.index(google_colour_label(str(row.get("colour", "")))) if google_colour_label(str(row.get("colour", ""))) in GOOGLE_COLOUR_LABELS else 0)
                render_google_colour_swatch(colour_label)
                colour = google_colour_code(colour_label)
                c1, c2 = st.columns(2)
                default_calendar = c1.text_input("Default Google Calendar", value=str(row.get("default_calendar", "")))
                default_task_list = c2.text_input("Default Google Tasks list", value=str(row.get("default_task_list", "")))
                notes = st.text_area("Notes", value=str(row.get("notes", "")), height=90)
                submitted = st.form_submit_button("Save changes", use_container_width=True)
                if submitted:
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


def _action_form(sheet_id: str, *, goal_id: str = "", routine_id: str = "", default_area: str = "", form_key: str = "action", action: dict[str, Any] | None = None) -> None:
    """Add or edit an action block using the same core fields as the desktop app."""
    area_id = find_area_id(sheet_id, default_area) if default_area else ""
    is_routine_activity = bool(routine_id)
    action = action or {}
    record_id = str(action.get("action_id", "") or "")
    with st.form(f"online_{'edit' if record_id else 'add'}_{form_key}_{record_id or 'new'}", clear_on_submit=not bool(record_id)):
        st.markdown("**Edit action block**" if record_id and not is_routine_activity else "**Edit routine activity**" if record_id else "**Add action block**" if not is_routine_activity else "**Add routine activity**")
        title = st.text_input("Action title" if not is_routine_activity else "Activity title", value=str(action.get("title", "")))
        description = st.text_area("Notes / description", value=str(action.get("description", action.get("notes", "")) or ""), height=90)
        c1, c2, c3 = st.columns(3)
        status_options = ["Next", "Scheduled", "Planned", "Waiting", "Done"] if not is_routine_activity else ["Included", "Paused", "Done"]
        current_status = str(action.get("status", status_options[0]) or status_options[0])
        status_index = status_options.index(current_status) if current_status in status_options else 0
        status = c1.selectbox("Status", status_options, index=status_index)
        priority_options = ["High", "Medium", "Low"]
        current_priority = str(action.get("priority", "Medium") or "Medium")
        priority = c2.selectbox("Priority", priority_options, index=priority_options.index(current_priority) if current_priority in priority_options else 1)
        try:
            default_minutes = int(float(str(action.get("estimated_minutes", "30") or 30)))
        except Exception:
            default_minutes = 30
        minutes = c3.number_input("Estimated minutes", min_value=0, step=5, value=default_minutes)
        c4, c5 = st.columns(2)
        scheduled = c4.text_input("Scheduled date", value=str(action.get("scheduled_date", "") or ""), placeholder="YYYY-MM-DD")
        due = c5.text_input("Due date", value=str(action.get("due_date", "") or ""), placeholder="YYYY-MM-DD")
        activity_days = ""
        if is_routine_activity:
            activity_days = st.text_input("Activity days", value=str(action.get("activity_days", "") or ""), placeholder="Optional, for example Monday, Wednesday")
        st.markdown("**Tasklist and exports**")
        st.caption("The Google Tasks prompt should be the tiny first step that makes the action easier to start, such as putting on running clothes, packing gym gear, opening the sketchbook, or showing up at the gym.")
        c6, c7, c8 = st.columns(3)
        include_tasklist = c6.checkbox("Include on tasklist", value=truthy_flag(action.get("include_tasklist", "1")))
        calendar_block = c7.checkbox("Prepare Google Calendar time", value=truthy_flag(action.get("calendar_block", "0")))
        reminder = c8.checkbox("Prepare Google Tasks first-action prompt", value=truthy_flag(action.get("reminder", "0")))
        first_step = st.text_input("First-step prompt for Google Tasks", value=str(action.get("first_step", "") or ""), placeholder="For example, put on running clothes, pack gym gear, or open the sketchbook")
        c9, c10, c11 = st.columns(3)
        start_time = c9.text_input("Calendar start time", value=str(action.get("calendar_start_time", "09:00") or "09:00"))
        end_time = c10.text_input("Calendar end time", value=str(action.get("calendar_end_time", "10:00") or "10:00"))
        prompt_time = c11.text_input("Prompt reference time", value=str(action.get("task_reminder_time", start_time or "09:00") or "09:00"))
        location = st.text_input("Calendar location", value=str(action.get("calendar_location", "") or ""), placeholder="Optional")
        submitted = st.form_submit_button("Save changes" if record_id else "Save action block", use_container_width=True)
        if submitted:
            problems = validate_online_action_dates_and_times(
                scheduled=scheduled, due=due, start_time=start_time, end_time=end_time, prompt_time=prompt_time
            )
            if not title.strip():
                st.error("Add an action title before saving.")
            elif problems:
                for problem in problems:
                    st.error(problem)
            else:
                payload = {
                    "goal_id": goal_id or str(action.get("goal_id", "") or ""),
                    "routine_id": routine_id or str(action.get("routine_id", "") or ""),
                    "area_id": area_id or str(action.get("area_id", "") or ""),
                    "area_name": default_area or str(action.get("area_name", "") or ""),
                    "title": title.strip(), "description": description.strip(), "status": status, "priority": priority,
                    "due_date": normalise_online_date(due) if due.strip() else "", "scheduled_date": normalise_online_date(scheduled) if scheduled.strip() else "", "activity_days": activity_days.strip(),
                    "estimated_minutes": str(int(minutes or 0)) if minutes else "", "calendar_block": "1" if calendar_block else "0",
                    "reminder": "1" if reminder else "0", "include_tasklist": "1" if include_tasklist else "0",
                    "first_step": first_step.strip(), "task_reminder_time": prompt_time.strip(), "calendar_start_time": start_time.strip(),
                    "calendar_end_time": end_time.strip(), "calendar_location": location.strip(), "notes": description.strip(),
                }
                if record_id:
                    ok, message = update_online_record(sheet_id, "actions", record_id, payload)
                else:
                    payload["action_id"] = f"action-{uuid.uuid4().hex}"
                    ok, message = append_online_record(sheet_id, "actions", payload)
                st.success(message) if ok else st.warning(safe_user_message(message))
                if ok:
                    st.rerun()


def _render_action_list(sheet_id: str, actions: pd.DataFrame, *, goal_id: str = "", routine_id: str = "", default_area: str = "") -> None:
    if actions.empty:
        st.info("No activities yet." if routine_id else "No actions yet.")
    else:
        for _, a in actions.iterrows():
            state = str(a.get("status", "") or ("Included" if routine_id else "Planned"))
            title = str(a.get("title", "Untitled") or "Untitled")
            when = str(a.get("scheduled_date", "") or a.get("due_date", "") or "")
            suffix = f" · {when}" if when else ""
            with st.expander(f"{title}{suffix} — {state}", expanded=False):
                _action_form(sheet_id, goal_id=goal_id, routine_id=routine_id, default_area=default_area, form_key=f"action_{a.get('action_id')}", action=a.to_dict())
                if st.button("Archive action" if not routine_id else "Archive activity", key=f"archive_action_{a.get('action_id')}"):
                    ok, message = archive_online_record(sheet_id, "actions", str(a.get("action_id", "")), "Archived from Pathmark Online.")
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
        st.markdown("### Goals")
        with st.expander("Add goal or project", expanded=goals.empty):
            with st.form("online_add_goal", clear_on_submit=True):
                area = st.selectbox("Area", options=[""] + areas, format_func=lambda x: x or "Choose an Area") if areas else st.text_input("Area")
                title = st.text_input("Title")
                specific = st.text_input("Specific area", placeholder="Optional sub-area or project folder")
                status = st.selectbox("Status", ["Captured", "Active", "On hold", "Closed", "Abandoned"], index=1)
                target_date = st.text_input("Target date", placeholder="Optional, for example 2026-09-30")
                purpose = st.text_area("Purpose", height=75)
                desired = st.text_area("Desired outcome", height=75)
                closure = st.text_area("Closure criteria", height=75)
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
            tabs = st.tabs(["Details", "Actions", "Archive"])
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
                with st.expander("Add action", expanded=linked.empty):
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
    Use routines for sleep, meals, movement, practice, planning, admin, and other basics that protect your energy and capacity. A routine activity can create calendar time and a Google Tasks prompt for the first small step, such as putting on gym clothes or simply showing up.</div>
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
                frequency = st.selectbox("Frequency", VALID_FREQUENCIES, index=VALID_FREQUENCIES.index("Weekly"))
                preferred_day_values = st.multiselect("Preferred days", VALID_DAYS, help="Use weekday names so exports can generate consistent repeat rules.")
                preferred_days = ", ".join(preferred_day_values)
                next_due = st.text_input("Next due", placeholder="YYYY-MM-DD")
                purpose = st.text_area("Purpose", height=75)
                checklist = st.text_area("Checklist", placeholder="One activity per line. You can add detailed activities after saving.", height=100)
                status = st.selectbox("Status", ["Active", "Paused", "Retired"], index=0)
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
                    checklist = st.text_area("Checklist", value=str(r.get("checklist", "")), height=100)
                    notes = st.text_area("Notes", value=str(r.get("notes", "")), height=80)
                    status_options = ["Active", "Paused", "Retired"]
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
                    frequency = st.selectbox("Frequency", VALID_FREQUENCIES, index=VALID_FREQUENCIES.index(current_freq) if current_freq in VALID_FREQUENCIES else VALID_FREQUENCIES.index("Custom"))
                    current_days, _bad_days = parse_days_text(str(r.get("preferred_days", "")))
                    preferred_day_values = st.multiselect("Preferred days", VALID_DAYS, default=current_days, help="Use weekday names so exports can generate consistent repeat rules.")
                    preferred_days = ", ".join(preferred_day_values)
                    next_due = st.text_input("Next due", value=str(r.get("next_due", "")))
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
                c1, c2 = st.columns(2)
                if c1.button("Pause routine", key=f"pause_r_{selected_id}"):
                    ok, message = update_online_record(sheet_id, "routines", selected_id, {"status": "Paused"})
                    st.success(message) if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
                if c2.button("Archive routine", key=f"archive_r_{selected_id}"):
                    ok, message = archive_online_record(sheet_id, "routines", selected_id, "Archived from Pathmark Online.")
                    st.success(message) if ok else st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()


def render_review_queue_manager(sheet_id: str) -> None:
    st.subheader("Review Queue")
    st.write("Review checks look for missing fields that could make tasklists, Google Calendar exports or Google Tasks prompts less useful.")
    goals = active_online_df(read_online_table(sheet_id, "goals"))
    routines = active_online_df(read_online_table(sheet_id, "routines"))
    actions = active_online_df(read_online_table(sheet_id, "actions"))
    issues = []
    for _, g in goals.iterrows():
        if not str(g.get("area_name", "") or "").strip():
            issues.append({"Priority": "Medium", "Type": "Goal", "Item": g.get("title", "Untitled"), "Issue": "No Area is selected.", "Suggested action": "Assign an Area."})
        if not str(g.get("desired_outcome", "") or g.get("description", "") or "").strip():
            issues.append({"Priority": "Low", "Type": "Goal", "Item": g.get("title", "Untitled"), "Issue": "No desired outcome is recorded.", "Suggested action": "Add the outcome or definition of done."})
    for _, r in routines.iterrows():
        if not str(r.get("frequency", "") or "").strip():
            issues.append({"Priority": "Medium", "Type": "Routine", "Item": r.get("title", "Untitled"), "Issue": "No repeat pattern is recorded.", "Suggested action": "Add the frequency or preferred days."})
    for _, a in actions.iterrows():
        if truthy_flag(a.get("reminder")) and not str(a.get("first_step", "") or "").strip():
            issues.append({"Priority": "High", "Type": "Action", "Item": a.get("title", "Untitled"), "Issue": "Google Tasks is ticked but no first action prompt is recorded.", "Suggested action": "Add a short first action."})
        if truthy_flag(a.get("calendar_block")) and not (str(a.get("scheduled_date", "") or a.get("due_date", "") or "").strip()):
            issues.append({"Priority": "High", "Type": "Action", "Item": a.get("title", "Untitled"), "Issue": "Calendar export is ticked but there is no scheduled or due date.", "Suggested action": "Add a date before exporting."})
    if issues:
        st.dataframe(pd.DataFrame(issues), use_container_width=True, hide_index=True)
    else:
        st.success("No obvious online review issues found.")


def render_tasklist_manager(sheet_id: str) -> None:
    st.subheader("Tasklist")
    st.write("Use a printed tasklist as an alternative to Google Tasks prompts when you prefer ticking things off on paper. Select the goal actions and routine activities you want to work through, then download the PDF.")
    tasklist = staged_tasklist(sheet_id)
    title = st.text_input("Tasklist name", value="Weekly Tasklist", help="This appears at the top of the printable tasklist.")
    notes = st.text_area("Optional notes for the printed tasklist", height=80, help="Add one note per line. These are appended to the end of the tasklist.")
    if tasklist.empty:
        st.info("No tasklist rows yet. Add goal actions or routine activities and tick 'Include on tasklist'.")
        return

    selected_indices: list[int] = []
    st.markdown("### Goal actions")
    goal_actions = tasklist[tasklist["source_type"] == "Goal action"].reset_index(drop=True)
    if goal_actions.empty:
        st.markdown("No planned goal actions found.")
    else:
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
                checked = st.checkbox(f"{row.get('title','Untitled')}{suffix}", value=False, key=key)
                if checked:
                    selected_indices.append(int(row.name))

    st.markdown("### Routine activities")
    routine_rows = tasklist[tasklist["source_type"] == "Routine activity"].reset_index(drop=True)
    routine_offset = len(goal_actions)
    if routine_rows.empty:
        st.markdown("No included routine activities found.")
    else:
        for parent, group in routine_rows.groupby(routine_rows["parent"].fillna("Unlinked routine"), sort=False):
            st.markdown(f"**{parent or 'Unlinked routine'}**")
            for _, row in group.iterrows():
                key = f"tasklist_routine_{row.get('id') or row.get('title')}"
                days = str(row.get("activity_days", "") or "").strip()
                suffix = f" ({days})" if days else ""
                checked = st.checkbox(f"{row.get('title','Untitled')}{suffix}", value=False, key=key)
                if checked:
                    selected_indices.append(routine_offset + int(row.name))

    selected_rows = tasklist.iloc[selected_indices] if selected_indices else pd.DataFrame(columns=tasklist.columns)
    st.markdown("### Preview")
    dataframe_preview(selected_rows if not selected_rows.empty else tasklist.head(0), ["source_type", "title", "area_name", "parent", "status", "scheduled_date", "due_date", "first_step", "estimated_minutes"])
    if selected_rows.empty and not notes.strip():
        st.warning("Tick at least one action or activity, or add a note, before downloading the tasklist.")
    content_rows = selected_rows if not selected_rows.empty else pd.DataFrame(columns=tasklist.columns)
    content = build_printable_tasklist_from_rows(content_rows).decode("utf-8")
    if title:
        content = content.replace("Pathmark tasklist", title, 1)
    if notes.strip():
        content += "\nNotes\n" + notes.strip() + "\n"
    pdf_bytes = build_tasklist_pdf(content_rows, title=title or "Pathmark Tasklist", notes=notes)
    st.download_button("Download printable PDF tasklist", data=pdf_bytes, file_name="pathmark_tasklist.pdf", mime="application/pdf", use_container_width=True, disabled=selected_rows.empty and not notes.strip())

def render_google_calendar_export_manager(sheet_id: str) -> None:
    st.subheader("Google Calendar Export")
    st.write("Calendar export rows are staged from goal actions and routine activities marked 'Prepare Google Calendar time'.")
    blocks = staged_calendar_blocks(sheet_id)
    dataframe_preview(blocks, ["title", "area_name", "start", "end", "recurrence", "linked_record_id"])
    st.download_button("Download Google Calendar .ics", data=build_ics_export(blocks), file_name="pathmark_calendar_blocks.ics", mime="text/calendar", use_container_width=True, disabled=blocks.empty)




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
                "Reminder Time": r.get("reminder_time") or "",
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
    st.write("Google Tasks prompts are staged from goal actions and routine activities marked for a first-step prompt. These are intended to make the action easier to start and satisfying to tick off once complete.")
    prompts = staged_task_prompts(sheet_id)
    dataframe_preview(prompts, ["title", "area_name", "due_date", "reminder_time", "task_list", "linked_calendar_summary"])
    st.download_button("Download Google Tasks CSV", data=build_google_tasks_csv(prompts), file_name="pathmark_google_tasks.csv", mime="text/csv", use_container_width=True, disabled=prompts.empty)
    if st.button("Write Google Tasks export to my sync sheet", use_container_width=True, disabled=prompts.empty):
        ok, message = write_google_tasks_export_tab(sheet_id, prompts)
        st.success(message) if ok else st.warning(safe_user_message(message))


def render_archive_manager(sheet_id: str) -> None:
    st.subheader("Archive")
    st.write("Archived online records remain in your Google Sheet with status 'archived'. They are hidden from active Pathmark Online views.")
    for table, title, cols in [("areas", "Areas", ["area_name", "description", "updated_at"]), ("goals", "Goals", ["title", "area_name", "status", "updated_at"]), ("routines", "Routines", ["title", "area_name", "status", "updated_at"]), ("actions", "Actions and activities", ["title", "area_name", "status", "updated_at"])]:
        df = read_online_table(sheet_id, table)
        if not df.empty and "status" in df.columns:
            archived = df[df["status"].fillna("").str.lower().eq("archived")]
        else:
            archived = pd.DataFrame(columns=cols)
        with st.expander(title, expanded=False):
            dataframe_preview(archived, cols)


def render_online_settings(sheet_id: str) -> None:
    st.subheader("Settings")
    st.write("Manage your online workspace, theme, and Google Sheet connection.")
    if sheet_id:
        st.caption(f"Sync sheet connected: …{sheet_id[-8:]}")
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
    with st.expander("Starter examples", expanded=False):
        st.write("Starter examples give you editable Areas, routines, goals and actions so you are not starting from a blank sheet.")
        if st.button("Load suggested starter examples", use_container_width=True, key="load_online_starter_examples_settings"):
            ok, message = load_starter_examples(sheet_id)
            st.success(message) if ok else st.warning(safe_user_message(message))
            if ok:
                st.rerun()
    st.markdown("### Theme")
    st.write("Choose how Pathmark Online looks on this device. The theme is saved to your Pathmark profile so it follows your Google login.")
    current_theme = st.session_state.get("hosted_theme_preference") or online_setting(sheet_id, "theme", "Default")
    if current_theme not in ONLINE_THEMES:
        current_theme = "Default"
    theme_name = st.selectbox("Online theme", list(ONLINE_THEMES.keys()), index=list(ONLINE_THEMES.keys()).index(current_theme))
    if st.button("Save theme", use_container_width=True):
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
    """Build a polished printable tasklist PDF with real checkbox symbols."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except Exception:
        return build_printable_tasklist_from_rows(rows)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("PathmarkTitle", parent=styles["Title"], fontSize=21, leading=25, spaceAfter=4, textColor=colors.HexColor("#1F2221"))
    sub_style = ParagraphStyle("PathmarkSub", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#626966"), spaceAfter=8)
    h_style = ParagraphStyle("PathmarkHeading", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#334E68"))
    body = ParagraphStyle("PathmarkBody", parent=styles["BodyText"], fontSize=9.2, leading=12, textColor=colors.HexColor("#1F2221"))
    small = ParagraphStyle("PathmarkSmall", parent=styles["BodyText"], fontSize=8.4, leading=11, textColor=colors.HexColor("#626966"))

    story = [
        Paragraph(html.escape(title or "Pathmark Tasklist"), title_style),
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
            story.append(Paragraph(html.escape(source_type + "s"), h_style))
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
                    "☐",
                    Paragraph(html.escape(str(row.get("title", "Untitled") or "Untitled")), body),
                    Paragraph(html.escape("<br/>".join(context_bits)), small),
                    Paragraph(html.escape(first), body),
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
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
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
            story.append(Paragraph(html.escape(line), body))
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
    headers = ["Task ID", "Task List", "Title", "Notes", "Due Date", "Reminder Time", "Status", "Repeat Pattern", "Related Google Calendar Item"]
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
            "Reminder Time": r.get("reminder_time") or "",
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


def render_online_overview(sheet_id: str) -> None:
    st.subheader("Home")
    data = read_online_tables(sheet_id)
    counts = {name: len(active_online_df(df)) for name, df in data.items() if name in ["areas", "goals", "routines", "actions"]}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Areas", counts.get("areas", 0))
    c2.metric("Goals", counts.get("goals", 0))
    c3.metric("Routines", counts.get("routines", 0))
    c4.metric("Actions", counts.get("actions", 0))
    st.markdown("""
    <div class="guide-box"><strong>Your planning system at a glance.</strong><br>
    Use the tabs below to create Areas, routines, goals, actions, tasklists and exports. Each section includes the guidance needed for that step, so Home stays as a simple dashboard.</div>
    """, unsafe_allow_html=True)
    if not counts.get("areas") and not counts.get("goals") and not counts.get("routines"):
        st.info("New to Pathmark Online? Start in Areas, then add routines and goals. You can load optional starter examples from Settings.")
    st.markdown("""
    <div class="grid-3">
      <div class="process-card"><h4>Make time</h4><p>Calendar exports turn routines and goal actions into time blocks rather than leaving them as vague intentions.</p></div>
      <div class="process-card"><h4>Start smaller</h4><p>Google Tasks prompts can be written as the first tiny step, such as putting on running shoes or opening the sketchbook.</p></div>
      <div class="process-card"><h4>Tick it off</h4><p>Use Google Tasks prompts or the printable PDF tasklist when you want a visible checklist for the day.</p></div>
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
      <div class="card"><h3>Put it in the calendar</h3><p>Routines and goal actions become calendar blocks, so the work has a real place in the week.</p></div>
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
    st.write("Pathmark helps you make time for routines and goal actions, then gives you first-step prompts or printable checklists so the work is easier to start and finish.")
    st.markdown("""
    <div class="grid-2">
      <div class="card"><h3>Pathmark Online</h3><p>Use the signed-in web version to manage routines, goals, actions, tasklists, Google Calendar exports and Google Tasks prompts from a Google Sheet you own.</p></div>
      <div class="card"><h3>Pathmark Desktop</h3><p>Use the Windows app when you want local Workspace folders, Markdown generation, local backups, and file-based publishing.</p></div>
    </div>
    """, unsafe_allow_html=True)
    st.header("What access you grant")
    st.markdown("""
    <div class="safe-rule"><strong>Google access:</strong> Pathmark uses Google sign-in to identify you and asks for the narrow Google Drive permission needed to create or update Pathmark files you use with the app. Pathmark does not ask for your Google password.</div>
    """, unsafe_allow_html=True)
    st.write("Pathmark Online uses your permission to create or update a Pathmark Sync spreadsheet in your Google Drive. Your routines, goals, actions, tasklists and export records are saved there so you can inspect, copy, or delete them yourself.")
    st.header("Where your information is stored")
    st.markdown("""
    <div class="grid-3">
      <div class="card"><h3>Your Google Sheet</h3><p>Pathmark Online planning records are saved to your Pathmark Sync spreadsheet in your own Google Drive.</p></div>
      <div class="card"><h3>Your local Workspace</h3><p>Pathmark Desktop stores Workspace files, generated Markdown, exports, tasklists and backups in the folder you choose.</p></div>
      <div class="card"><h3>Access settings</h3><p>Supabase stores hosted access information only: email, role, status, feature flags, audit logs and theme preference.</p></div>
    </div>
    """, unsafe_allow_html=True)
    st.header("What Pathmark does not store")
    st.markdown("""
    <div class="safe-rule"><strong>Privacy rule:</strong> Pathmark should not store your goals, routines, task prompts, calendar blocks, Workspace files, backups, or Markdown content in Supabase or GitHub. Personal planning data belongs in your local Workspace or in your user-owned Google Sheet.</div>
    """, unsafe_allow_html=True)
    st.header("Disconnecting")
    st.write("You can disconnect Google access from Pathmark Online Settings. You can also remove Pathmark's access from your Google Account permissions page. Disconnecting stops Pathmark from writing to your Pathmark Sync sheet until you sign in again.")
    st.header("GitHub and Streamlit secrets")
    st.write("GitHub stores the app code and release packages. Streamlit secrets are used for deployment credentials. Secret keys, OAuth client secrets, Supabase keys, OAuth tokens and private planning records should not be committed to GitHub.")

def render_connection_summary(credentials: Any, sheet_id: str, auth_ready: bool) -> None:
    """Show a compact connection state without exposing OAuth plumbing."""
    if credentials and sheet_id:
        st.success("Pathmark Online is ready. Your planning records are saved to your Pathmark Sync sheet.")
    elif credentials:
        st.info("Google access is ready. Pathmark is preparing your sync sheet.")
    elif auth_ready:
        st.info("Sign in with Google to use Pathmark Online.")
    else:
        st.warning("Google access is not configured for this deployment.")

def on_the_go_tab() -> None:
    handle_google_oauth_redirect()
    st.header("Pathmark Online beta")
    notice = st.session_state.pop("on_the_go_connected_notice", "")
    if notice:
        st.success(notice)

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
        render_online_overview(sheet_id)
    with sections[1]:
        render_review_queue_manager(sheet_id)
    with sections[2]:
        render_area_manager(sheet_id)
    with sections[3]:
        render_routine_manager(sheet_id)
    with sections[4]:
        render_goal_manager(sheet_id)
    with sections[5]:
        render_tasklist_manager(sheet_id)
    with sections[6]:
        render_google_calendar_export_manager(sheet_id)
    with sections[7]:
        render_google_tasks_export_manager(sheet_id)
    with sections[8]:
        render_archive_manager(sheet_id)
    with sections[9]:
        render_online_settings(sheet_id)

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
