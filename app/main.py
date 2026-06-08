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
import base64
import urllib.parse
import urllib.request
import traceback
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from typing import Any

import pandas as pd
import streamlit as st

try:
    import yaml
except Exception:
    yaml = None

try:
    from PIL import Image
except Exception:
    Image = None

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / "downloads"
VERSION_FILE = ROOT / "latest_version.json"
ICON_PATH = ROOT / "app" / "assets" / "pathmark.png"
ASSETS_DIR = ROOT / "app" / "assets"
SEASONAL_BANNER_DIR = ASSETS_DIR / "seasonal_banners"
SEASONAL_BANNER_LOCATIONS = {
    "Summer": "Paihia",
    "Autumn": "Arrowtown",
    "Winter": "The Remarkables",
    "Spring": "The Waikato",
}
SEASONAL_BANNER_FILES = {
    "Summer": SEASONAL_BANNER_DIR / "summer.jpg",
    "Autumn": SEASONAL_BANNER_DIR / "autumn.jpg",
    "Winter": SEASONAL_BANNER_DIR / "winter.jpg",
    "Spring": SEASONAL_BANNER_DIR / "spring.jpg",
}
ROOT_STATIC = ROOT / "static"
FAVICON_PATH = ROOT_STATIC / "favicon.ico"
THEME_CONFIG_PATH = ROOT / "app" / "config" / "themes.yaml"
SYNC_COLUMNS = [
    "sync_id", "status", "record_type", "action", "title", "area_name", "specific_area",
    "details", "calendar_start", "calendar_end", "recurrence", "created_at", "updated_at",
    "imported_at", "source",
]

ONLINE_TABLES = {
    "settings": ["key", "value", "updated_at", "source"],
    "areas": ["area_id", "area_name", "description", "colour", "status", "default_calendar", "default_task_list", "google_calendar_id", "google_calendar_name", "google_calendar_colour_id", "google_calendar_synced_at", "notes", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "goals": ["goal_id", "area_id", "area_name", "title", "description", "specific_area", "planning_mode", "status", "target_date", "purpose", "desired_outcome", "closure_criteria", "notes", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "routines": ["routine_id", "area_id", "area_name", "title", "description", "frequency", "preferred_days", "duration_minutes", "status", "purpose", "next_due", "checklist", "calendar_block", "reminder", "starting_prompt", "task_reminder_time", "calendar_start_time", "calendar_end_time", "calendar_end_date", "calendar_location", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "actions": ["action_id", "goal_id", "routine_id", "area_id", "area_name", "title", "description", "item_type", "contributes_to_progress", "parent_progress_item_id", "status", "priority", "specific_area", "due_date", "scheduled_date", "activity_days", "estimated_minutes", "calendar_block", "reminder", "include_tasklist", "first_step", "task_reminder_time", "calendar_start_time", "calendar_end_time", "calendar_end_date", "calendar_location", "notes", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id", "google_task_list_id", "google_task_id", "google_task_status", "google_task_completed_at", "google_task_updated_at", "google_task_synced_at", "sync_status", "google_calendar_id", "google_calendar_event_id", "google_calendar_status", "google_calendar_updated_at", "google_calendar_synced_at", "google_calendar_recurrence", "calendar_sync_status", "archived_at", "archived_reason", "restored_at"],
    "calendar_blocks": ["block_id", "area_name", "title", "description", "start", "end", "recurrence", "linked_record_id", "status", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id"],
    "task_prompts": ["prompt_id", "area_name", "title", "prompt_text", "due_date", "task_kind", "linked_record_id", "linked_record_type", "linked_parent_id", "linked_parent_type", "task_list", "notes", "status", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id", "google_task_list_id", "google_task_id", "google_task_status", "google_task_completed_at", "google_task_updated_at", "google_task_synced_at", "sync_status"],
    "tasklists": ["tasklist_id", "date", "title", "items", "status", "created_at", "updated_at", "source", "exported_at", "export_type", "export_batch_id"],
    "google_tasks_export": ["Task ID", "Task List", "Title", "Notes", "Due Date", "Reference Time", "Status", "Repeat Pattern", "Related Google Calendar Item", "exported_at"],
    "wizard_drafts": ["draft_id", "wizard_type", "current_step_key", "answers_json", "activity_drafts_json", "status", "created_at", "updated_at", "saved_at", "source"],
    "spending_income": ["income_id", "person", "category", "weekly_amount", "fortnightly_amount", "monthly_amount", "yearly_amount", "annual_amount", "notes", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "spending_expenses": ["expense_id", "expense_kind", "group_name", "item", "weekly_amount", "fortnightly_amount", "monthly_amount", "quarterly_amount", "yearly_amount", "annual_amount", "notes", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "spending_accounts": ["account_id", "account_name", "purpose", "bank", "account_number_hint", "transfer_per_week", "target_balance", "current_balance", "notes", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "grocery_categories": ["category_id", "category_name", "description", "colour", "sort_order", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "grocery_inventory": ["inventory_id", "category_name", "item", "quantity", "unit", "expiry_date", "storage", "is_frozen", "requires_substitute", "suggested_substitute", "must_be_homegrown", "unavailable", "imported", "canned", "in_season", "limited_in_season", "months", "notes", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "grocery_nutrition": ["nutrition_id", "item", "category_name", "portion_quantity", "portion_unit", "kcal_per_portion", "total_carbohydrate", "total_fat", "protein", "saturated_fat", "trans_fat", "monounsat_fat", "polyunsat_fat", "cholesterol", "sodium", "potassium", "dietary_fibre", "sugars", "vitamin_a", "vitamin_c", "calcium", "iron", "vitamin_d", "caffeine", "magnesium", "phosphorus", "zinc", "copper", "manganese", "thiamine", "riboflavin", "niacin", "folate", "notes", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "recipes": ["recipe_id", "recipe_name", "category_name", "course", "meal_categories", "cuisine_tags", "dish_style_tags", "dietary_tags", "servings", "time_mins", "source_url", "source_title", "page", "author", "protein", "vegetarian_vegan", "vegetarian", "vegan", "gluten_free", "allergens", "months", "seasonality_summary", "imported_notes", "frozen_or_canned_notes", "substitute_notes", "homegrown_notes", "unavailable_notes", "notes", "exported_goal_id", "exported_action_id", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "recipe_ingredients": ["recipe_ingredient_id", "recipe_id", "recipe_name", "inventory_id", "ingredient", "quantity", "unit", "category_name", "is_fresh_produce", "lookup_seasonality", "seasonality_status", "substitute_required", "suggested_substitute", "purchased_quantity", "purchased_unit", "purchased_price", "cost_estimate", "missing_price_data", "kcal_estimate", "nutrition_status", "missing_nutrition_data", "notes", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "recipe_courses": ["course_id", "course_name", "description", "sort_order", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "recipe_meal_categories": ["meal_category_id", "meal_category_name", "description", "sort_order", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "recipe_cuisine_tags": ["cuisine_tag_id", "cuisine_tag_name", "description", "sort_order", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "recipe_dish_style_tags": ["dish_style_tag_id", "dish_style_tag_name", "description", "sort_order", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "recipe_dietary_tags": ["dietary_tag_id", "dietary_tag_name", "description", "sort_order", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "shopping_lists": ["shopping_list_id", "list_name", "planned_date", "status", "notes", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
    "shopping_items": ["shopping_item_id", "shopping_list_id", "shopping_list_name", "category_name", "quantity", "unit", "ingredient", "inventory_id", "recipe_id", "recipe_name", "checked", "notes", "status", "created_at", "updated_at", "source", "archived_at", "archived_reason", "restored_at"],
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

ONLINE_THEME_OPTIONS = [
    "Seasonal",
    "Cyan",
    "Sky",
    "Blue",
    "Indigo",
    "Violet",
    "Plum",
    "Rose",
    "Terracotta",
    "Clay",
    "Amber",
    "Olive",
    "Sage",
    "Teal",
    "Steel",
    "Graphite",
    "Pearl",
    "Custom",
]
ONLINE_APPEARANCE_OPTIONS = ["System", "Light", "Dark"]
SEASONAL_ACCENTS = {
    # Southern Hemisphere seasons, suitable for New Zealand as Pathmark's initial hosted audience.
    # Seasonal is one theme: the accent automatically follows the current season.
    "Summer": {"accent": "#B66A00", "accent_2": "#1B8EA8", "seasonal_icon": ""},
    "Autumn": {"accent": "#A33A16", "accent_2": "#7A4E2A", "seasonal_icon": ""},
    "Winter": {"accent": "#334E9E", "accent_2": "#6BA2B8", "seasonal_icon": ""},
    "Spring": {"accent": "#2F7D50", "accent_2": "#1B8EA8", "seasonal_icon": ""},
}
ONLINE_THEMES = {
    # Pathmark themes are accent themes only. Streamlit owns Light, Dark and System.
    # Seasonal is the default Pathmark accent and updates automatically by Southern Hemisphere season.
    "Seasonal": {"accent": "#334E9E", "accent_2": "#6BA2B8", "seasonal_icon": "", "auto": True},
    "Moss": {"accent": "#637D2E", "accent_2": "#B4C577", "seasonal_icon": ""},
    "Lagoon": {"accent": "#1D7F74", "accent_2": "#8FC7BE", "seasonal_icon": ""},
    "Persimmon": {"accent": "#B65335", "accent_2": "#D79E82", "seasonal_icon": ""},
    "Marigold": {"accent": "#A87216", "accent_2": "#D8B85E", "seasonal_icon": ""},
    "Iris": {"accent": "#5B4BA0", "accent_2": "#B9A9DB", "seasonal_icon": ""},
    "Rosewood": {"accent": "#A33D6A", "accent_2": "#D79BB3", "seasonal_icon": ""},
    "Cyan": {"accent": "#1B8EA8", "accent_2": "#334E9E", "seasonal_icon": ""},
    "Sky": {"accent": "#0284C7", "accent_2": "#38BDF8", "seasonal_icon": ""},
    "Blue": {"accent": "#334E9E", "accent_2": "#6BA2B8", "seasonal_icon": ""},
    "Indigo": {"accent": "#4F46E5", "accent_2": "#334E9E", "seasonal_icon": ""},
    "Violet": {"accent": "#7C3AED", "accent_2": "#8B5CF6", "seasonal_icon": ""},
    "Plum": {"accent": "#8B4E9F", "accent_2": "#B05A7A", "seasonal_icon": ""},
    "Rose": {"accent": "#BE4B6A", "accent_2": "#B05A7A", "seasonal_icon": ""},
    "Terracotta": {"accent": "#A33A16", "accent_2": "#C2410C", "seasonal_icon": ""},
    "Clay": {"accent": "#8A5A44", "accent_2": "#A33A16", "seasonal_icon": ""},
    "Amber": {"accent": "#B66A00", "accent_2": "#D97706", "seasonal_icon": ""},
    "Olive": {"accent": "#4D7C0F", "accent_2": "#0B8043", "seasonal_icon": ""},
    "Sage": {"accent": "#5D7F61", "accent_2": "#2F7D50", "seasonal_icon": ""},
    "Teal": {"accent": "#0F766E", "accent_2": "#1B8EA8", "seasonal_icon": ""},
    "Steel": {"accent": "#4F7F95", "accent_2": "#334E9E", "seasonal_icon": ""},
    "Graphite": {"accent": "#475569", "accent_2": "#7FA9B8", "seasonal_icon": ""},
    "Pearl": {"accent": "#7FA9B8", "accent_2": "#4F7F95", "seasonal_icon": ""},
    "Custom": {"accent": "#334E9E", "accent_2": "#6BA2B8", "seasonal_icon": "", "custom": True},
    # Compatibility aliases for old saved preferences.
    "Default": {"alias_for": "Seasonal"},
    "Pathmark": {"alias_for": "Seasonal"},
    "Primary Navy": {"alias_for": "Blue"},
    "Primary Cyan": {"alias_for": "Cyan"},
    "Secondary Steel": {"alias_for": "Steel"},
    "Tertiary Mist": {"alias_for": "Cyan"},
    "Tertiary Pearl": {"alias_for": "Pearl"},
    "Navy": {"alias_for": "Blue"},
    "Mist": {"alias_for": "Cyan"},
    "Summer": {"alias_for": "Seasonal"},
    "Autumn": {"alias_for": "Seasonal"},
    "Winter": {"alias_for": "Seasonal"},
    "Spring": {"alias_for": "Seasonal"},
    "Warm": {"alias_for": "Terracotta"},
    "Dark": {"alias_for": "Graphite"},
    "Summer dark": {"alias_for": "Seasonal"},
    "Autumn dark": {"alias_for": "Seasonal"},
    "Winter dark": {"alias_for": "Seasonal"},
    "Spring dark": {"alias_for": "Seasonal"},
}


def load_theme_presets_from_config() -> None:
    """Load built-in accent themes from app/config/themes.yaml when available."""
    global ONLINE_THEME_OPTIONS, SEASONAL_ACCENTS, ONLINE_THEMES
    if yaml is None or not THEME_CONFIG_PATH.exists():
        return
    try:
        data = yaml.safe_load(THEME_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        options = [str(item).strip() for item in data.get("options", []) if str(item).strip()]
        seasonal = data.get("seasonal_accents", {}) if isinstance(data.get("seasonal_accents", {}), dict) else {}
        themes = data.get("themes", {}) if isinstance(data.get("themes", {}), dict) else {}
        aliases = data.get("aliases", {}) if isinstance(data.get("aliases", {}), dict) else {}
        if options and themes:
            cleaned_themes: dict[str, dict[str, Any]] = {}
            for name, info in themes.items():
                if isinstance(info, dict):
                    cleaned = {str(k): v for k, v in info.items()}
                    cleaned.setdefault("seasonal_icon", "")
                    cleaned_themes[str(name)] = cleaned
            for old_name, target in aliases.items():
                cleaned_themes[str(old_name)] = {"alias_for": str(target)}
            cleaned_seasonal: dict[str, dict[str, str]] = {}
            for season, info in seasonal.items():
                if isinstance(info, dict):
                    cleaned_seasonal[str(season)] = {
                        "accent": str(info.get("accent", "#334E9E")),
                        "accent_2": str(info.get("accent_2", info.get("accent", "#6BA2B8"))),
                        "seasonal_icon": str(info.get("seasonal_icon", "")),
                    }
            if cleaned_seasonal:
                SEASONAL_ACCENTS = cleaned_seasonal
            ONLINE_THEME_OPTIONS = options
            ONLINE_THEMES = cleaned_themes
    except Exception:
        return


load_theme_presets_from_config()


def current_southern_hemisphere_season(today: date | None = None) -> str:
    """Return the current Southern Hemisphere season.

    Pathmark currently defaults to New Zealand/Southern Hemisphere timing:
    Spring = Sep-Nov, Summer = Dec-Feb, Autumn = Mar-May, Winter = Jun-Aug.
    """
    today = today or date.today()
    month = today.month
    if month in (12, 1, 2):
        return "Summer"
    if month in (3, 4, 5):
        return "Autumn"
    if month in (6, 7, 8):
        return "Winter"
    return "Spring"


def normalise_online_theme(theme_name: str | None) -> str:
    """Return a supported Pathmark accent theme name.

    Streamlit controls System/Light/Dark. Pathmark controls accent themes only.
    """
    name = str(theme_name or "").strip()
    if name in ONLINE_THEME_OPTIONS:
        return name
    info = ONLINE_THEMES.get(name, {})
    alias = str(info.get("alias_for", "") or "") if isinstance(info, dict) else ""
    return alias if alias in ONLINE_THEME_OPTIONS else "Seasonal"



def normalise_appearance_mode(value: str | None) -> str:
    """Normalise a legacy Pathmark appearance setting.

    v0.6.44 keeps to Streamlit's own System/Light/Dark menu as the
    user-facing control. This helper remains only for compatibility with old
    saved settings.
    """
    text = str(value or "").strip().lower()
    if text in {"dark", "night"}:
        return "Dark"
    if text in {"light", "day"}:
        return "Light"
    return "System"


def resolved_appearance_mode(value: str | None = None) -> str:
    mode = normalise_appearance_mode(value)
    if mode == "Dark":
        return "dark"
    if mode == "Light":
        return "light"
    return "system"

VALID_FREQUENCIES = ["Daily", "Weekdays", "Weekly", "Monthly", "Custom"]
VALID_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHLY_REPEAT_PATTERNS = [
    "First Monday", "First Tuesday", "First Wednesday", "First Thursday", "First Friday", "First Saturday", "First Sunday",
    "Second Monday", "Second Tuesday", "Second Wednesday", "Second Thursday", "Second Friday", "Second Saturday", "Second Sunday",
    "Third Monday", "Third Tuesday", "Third Wednesday", "Third Thursday", "Third Friday", "Third Saturday", "Third Sunday",
    "Fourth Monday", "Fourth Tuesday", "Fourth Wednesday", "Fourth Thursday", "Fourth Friday", "Fourth Saturday", "Fourth Sunday",
    "Last Monday", "Last Tuesday", "Last Wednesday", "Last Thursday", "Last Friday", "Last Saturday", "Last Sunday",
    "Same day of month as start date",
]
DAY_ALIASES = {d.lower(): d for d in VALID_DAYS}
DAY_ALIASES.update({d[:3].lower(): d for d in VALID_DAYS})

GOOGLE_SHEETS_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
GOOGLE_TASKS_SCOPES = ["https://www.googleapis.com/auth/tasks"]
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
BASE_LOGIN_SCOPES = ["openid", "email", "profile"]
LOGIN_SCOPES = BASE_LOGIN_SCOPES + GOOGLE_SHEETS_SCOPES + GOOGLE_TASKS_SCOPES + GOOGLE_CALENDAR_SCOPES
SYNC_SHEET_TITLE = "Pathmark Sync"



def page_icon():
    # Streamlit sets the favicon in the first HTML response. Prefer a small
    # PNG payload because some browsers do not refresh an ICO/PIL favicon when
    # the app is redeployed on the same Streamlit Cloud domain.
    icon32 = ROOT_STATIC / "pathmark-icon-32.png"
    if icon32.exists():
        try:
            return icon32.read_bytes()
        except Exception:
            pass
    if Image is not None and ICON_PATH.exists():
        try:
            return Image.open(ICON_PATH)
        except Exception:
            pass
    if FAVICON_PATH.exists():
        try:
            return FAVICON_PATH.read_bytes()
        except Exception:
            return str(FAVICON_PATH)
    return "PM"


st.set_page_config(page_title="Pathmark", page_icon=page_icon(), layout="wide")


def _static_icon_data_uri(filename: str, mime_type: str = "image/png") -> str:
    path = ROOT_STATIC / filename
    try:
        if path.exists():
            return f"data:{mime_type};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        pass
    return ""


@st.cache_data(show_spinner=False)
def _local_file_data_uri(path_text: str, mime_type: str) -> str:
    path = Path(path_text)
    try:
        if path.exists():
            return f"data:{mime_type};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception:
        return ""
    return ""


def seasonal_banner_data_uri(season: str) -> str:
    label = season if season in SEASONAL_BANNER_FILES else current_southern_hemisphere_season()
    banner_path = SEASONAL_BANNER_FILES.get(label)
    if not banner_path:
        return ""
    return _local_file_data_uri(str(banner_path), "image/jpeg")


def seasonal_banner_season(theme_name: str | None = None) -> str:
    choice = normalise_online_theme(theme_name or st.session_state.get("hosted_theme_preference", "Seasonal"))
    if choice == "Seasonal":
        return current_southern_hemisphere_season()
    if choice in SEASONAL_BANNER_FILES:
        return choice
    return current_southern_hemisphere_season()


def theme_uses_seasonal_banner(theme_name: str | None = None) -> bool:
    choice = normalise_online_theme(theme_name or st.session_state.get("hosted_theme_preference", "Seasonal"))
    return choice == "Seasonal" or choice in SEASONAL_BANNER_FILES


def render_seasonal_banner(title: str = "", subtitle: str = "", season: str | None = None, compact: bool = False, force: bool = False, theme_name: str | None = None, show_label: bool | None = None) -> None:
    """Render a restrained seasonal image strip.

    Plain banners are intentionally textless so they read as atmosphere rather
    than an extra card. A label/panel is used only when there is explanatory
    content, such as on the Theme preview page.
    """
    if not force and not theme_uses_seasonal_banner(theme_name):
        return
    active_season = season or seasonal_banner_season(theme_name)
    image_uri = seasonal_banner_data_uri(active_season)
    if not image_uri:
        return
    location = SEASONAL_BANNER_LOCATIONS.get(active_season, "")
    classes = "seasonal-banner seasonal-banner-compact" if compact else "seasonal-banner"
    title_html = f"<h3>{html.escape(title)}</h3>" if title else ""
    subtitle_html = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    label = html.escape(f"{active_season} · {location}" if location else active_season)
    show_panel = bool(title_html or subtitle_html or show_label)
    panel_html = ""
    if show_panel:
        label_html = f'<div class="seasonal-banner-label">{label}</div>' if show_label is not False else ""
        panel_html = (
            '<div class="seasonal-banner-content">'
            '<div class="seasonal-banner-panel">'
            f'{label_html}{title_html}{subtitle_html}'
            '</div></div>'
        )
    st.markdown(
        f"""
        <div class="{classes}" style="background-image:url('{image_uri}');">
          <div class="seasonal-banner-overlay"></div>
          {panel_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def inject_pwa_metadata() -> None:
    """Compatibility hook retained after removing phone-app/PWA support.

    Pathmark now treats phones as ordinary browser clients using the same desktop UI/data canvas. It no longer
    tries to inject a web-app manifest or mobile shortcut metadata because that
    half-supported behaviour made the hosted app appear less polished.
    """
    return


def inject_appearance_watcher() -> None:
    """No-op compatibility hook.

    Pathmark no longer watches or mirrors Streamlit Light/Dark/System. Streamlit
    owns full appearance; Pathmark only supplies seasonal accents for custom
    Pathmark components.
    """
    return


inject_appearance_watcher()


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
    """Return paired surface/text tokens for Pathmark custom styling.

    Pathmark does not guess contrast from Light/Dark labels alone. Tokens are
    paired against Streamlit's actual background and text variables, so if the
    Streamlit Settings menu changes appearance, Pathmark-owned cards, muted
    text, borders and accents resolve together against the surface they sit on.
    """
    return """
          --bg: var(--background-color, #F7F6F2);
          --ink: var(--text-color, #1F2221);
          --surface: color-mix(in srgb, var(--background-color, #F7F6F2) 92%, var(--text-color, #1F2221) 8%);
          --surface-2: color-mix(in srgb, var(--background-color, #F7F6F2) 86%, var(--text-color, #1F2221) 14%);
          --line: color-mix(in srgb, var(--text-color, #1F2221) 32%, var(--background-color, #F7F6F2));
          --muted: color-mix(in srgb, var(--text-color, #1F2221) 76%, var(--background-color, #F7F6F2));
          --shadow: color-mix(in srgb, #000000 18%, transparent);
          --accent-soft: color-mix(in srgb, var(--accent) 14%, var(--surface));
        """



CSS = f"""
<style>
/*
Pathmark v0.6.56 theme model
--------------------------------
Streamlit owns the full appearance mode: page background, text, widgets,
inputs, popovers and the Settings menu. Pathmark only adds a restrained accent
and styles Pathmark-owned custom cards/badges. Avoid global body/app/text/input
colour overrides so Streamlit's Light/Dark/System menu behaves natively.
*/
:root {{
  --accent: #334E68;
  --accent-2: #7A4E7A;
  --button-ink: #FFFFFF;
{pathmark_theme_tokens_css(streamlit_appearance_mode())}
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0E1117;
    --ink: #F8FAFC;
    --surface: #171B22;
    --surface-2: #202632;
    --line: #46505F;
    --muted: #D1D5DB;
    --shadow: color-mix(in srgb, #000000 42%, transparent);
    --accent-soft: color-mix(in srgb, var(--accent) 20%, var(--surface));
  }}
}}
.block-container {{ max-width: 1180px; padding-top: 2.25rem; padding-bottom: 4rem; }}
h1, h2, h3 {{ letter-spacing: -0.035em; }}
p, li {{ font-size: 1.02rem; line-height: 1.62; }}
.hero {{ padding: 2.6rem 0 1.2rem 0; }}
.eyebrow {{ display: inline-flex; padding: .42rem .72rem; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 760; font-size: .92rem; margin-bottom: 1.1rem; }}
.seasonal-preview-card {{
  border: 1px solid var(--line);
  border-left: 8px solid var(--accent);
  background: var(--accent-soft);
  border-radius: 1rem;
  padding: .9rem 1rem;
  margin: .8rem 0 1.1rem;
  color: var(--ink);
  font-weight: 760;
}}
.seasonal-banner {{ position: relative; overflow: hidden; border-radius: 1.25rem; min-height: 156px; margin: .35rem 0 1.05rem; border: 1px solid var(--line); background-size: cover; background-position: center center; box-shadow: 0 10px 22px color-mix(in srgb, #000000 8%, transparent); }}
.seasonal-banner-compact {{ min-height: 58px; margin: .55rem 0 1rem; border-radius: 1rem; }}
.seasonal-banner-overlay {{ position: absolute; inset: 0; background: linear-gradient(135deg, color-mix(in srgb, var(--background-color, #F7F6F2) 20%, transparent) 0%, color-mix(in srgb, var(--background-color, #F7F6F2) 28%, transparent) 34%, rgba(255,255,255,0.04) 100%); }}
.seasonal-banner-content {{ position: relative; z-index: 1; padding: .9rem .95rem; min-height: inherit; display: flex; align-items: flex-end; }}
.seasonal-banner-panel {{ display: inline-flex; flex-direction: column; gap: .38rem; max-width: 760px; background: color-mix(in srgb, var(--surface) 88%, transparent); border: 1px solid color-mix(in srgb, var(--line) 74%, transparent); border-radius: .95rem; padding: .72rem .9rem; backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); box-shadow: 0 8px 20px color-mix(in srgb, #000000 10%, transparent); }}
.seasonal-banner-label {{ display: inline-flex; width: fit-content; align-items: center; gap: .35rem; padding: .34rem .62rem; border-radius: 999px; background: color-mix(in srgb, var(--surface-2) 90%, transparent); color: var(--muted); font-size: .78rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }}
.seasonal-banner h3 {{ margin: 0; font-size: clamp(1.15rem, 2vw, 1.55rem); line-height: 1.12; letter-spacing: -.035em; color: var(--ink); }}
.seasonal-banner p {{ margin: 0; color: var(--muted); font-size: .96rem; line-height: 1.42; }}
.hero h1 {{ font-size: clamp(3.7rem, 8.2vw, 7.2rem); line-height: .84; margin: 0 0 1rem 0; letter-spacing: -.085em; }}
.lead {{ font-size: clamp(1.28rem, 2.4vw, 1.9rem); line-height: 1.22; max-width: 920px; font-weight: 680; margin: 0; }}
.sublead {{ color: var(--muted); font-size: 1.12rem; max-width: 850px; margin-top: 1rem; }}
.grid-3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }}
.grid-2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: 1.2rem 0 2rem; }}
.card, .meta-card, .download-panel, .account-card, .connection-card, .setup-shell, .guide-box, .step-card, .process-card, .pathmark-card, .workspace-card, .issue-card {{
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: 0 8px 18px color-mix(in srgb, #000000 8%, transparent);
}}
.card {{ border-radius: 1.35rem; padding: 1.25rem; }}
.card h3 {{ margin-top: 0; margin-bottom: .55rem; color: var(--ink); }}
.card p {{ margin-bottom: 0; color: var(--muted); }}
.card, .pillar-card, .pathmark-card, .workspace-card, .download-panel {{ border-top: 1px solid var(--line); }}
.meta-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin: .9rem 0 2.1rem; }}
.meta-card {{ border-radius: 1.25rem; padding: 1rem 1.15rem; }}
.meta-label {{ color: var(--muted); font-size: .92rem; font-weight: 700; margin-bottom: .35rem; }}
.meta-value {{ font-size: 1.9rem; line-height: 1.05; font-weight: 780; }}
.download-panel {{ border-radius: 1.35rem; padding: 1.2rem; margin: 1.2rem 0 2rem; }}
.account-card, .connection-card {{ border-radius: .9rem; padding: .5rem .72rem; box-shadow:none !important; }}
.account-card {{ background: transparent !important; border-color: transparent !important; padding: .15rem 0 !important; }}
.account-title {{ color: var(--muted); font-size: .78rem; font-weight: 760; letter-spacing: .04em; text-transform: uppercase; }}
.account-value {{ color: var(--muted); font-size: .9rem; }}
.account-chip-row {{ display:flex; align-items:center; gap:.42rem; flex-wrap:wrap; min-height:1.8rem; opacity:.82; }}
.account-chip {{ display:inline-flex; align-items:center; gap:.32rem; border:1px solid color-mix(in srgb, var(--line) 70%, transparent); background:color-mix(in srgb, var(--surface) 72%, transparent); border-radius:999px; padding:.18rem .52rem; color:var(--muted); font-size:.8rem; box-shadow:none; }}
.account-chip strong {{ color:var(--ink); font-weight:680; }}
.connection-strip {{ display:inline-flex; align-items:center; gap:.42rem; border:1px solid color-mix(in srgb, var(--line) 72%, transparent); background:color-mix(in srgb, var(--surface) 78%, transparent); border-radius:999px; padding:.24rem .62rem; color:var(--muted); font-size:.84rem; margin:.1rem 0 .65rem; }}
.connection-strip strong {{ color:var(--ink); font-weight:700; }}
.connection-strip.warn {{ border-color: color-mix(in srgb, #B45309 44%, var(--line)); }}
.safe-rule {{ background: var(--surface-2); border: 1px solid var(--line); border-radius: 1.1rem; padding: 1rem 1.1rem; }}
.profile-pill {{ display: inline-flex; gap: .45rem; align-items: center; padding: .46rem .72rem; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--line); color: var(--muted); font-weight: 700; }}
.kicker {{ color: var(--accent); font-size: .82rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; margin-bottom: .4rem; }}
.small-muted {{ color: var(--muted); font-size: .94rem; }}
.hr {{ height: 1px; background: var(--line); margin: 1.6rem 0; }}
.step-card {{ border-radius: 1.2rem; padding: 1rem 1.05rem; margin-bottom: .8rem; }}
.wizard-shell {{ max-width: 860px; margin: 0 auto 3rem auto; }}
.wizard-hero {{ padding: .25rem 0 .8rem 0; margin: 0 0 .35rem 0; border-bottom: 1px solid var(--line); }}
.wizard-hero h2 {{ margin: .05rem 0 .18rem 0; font-size: clamp(1.85rem, 3.2vw, 2.45rem); letter-spacing: -.05em; }}
.wizard-hero p {{ margin: 0; color: var(--muted); font-size: 1rem; line-height: 1.45; }}
.wizard-progress {{ margin: .75rem 0 1.1rem 0; }}
.wizard-progress-text {{ color: var(--muted); font-size: .9rem; font-weight: 700; letter-spacing: .01em; margin-bottom: .45rem; }}
.wizard-progress-track {{ height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--muted) 18%, transparent); overflow: hidden; border: 1px solid var(--line); }}
.wizard-progress-fill {{ height: 100%; background: var(--accent); border-radius: 999px; }}
.wizard-entry-card {{ border-radius: 1.15rem; padding: 1rem 1.05rem; margin: 1rem 0 1.2rem 0; background: var(--surface); border: 1px solid var(--line); box-shadow: 0 10px 22px var(--shadow); }}
.wizard-nav-note {{ margin: .1rem 0; color: var(--muted); font-size: .92rem; text-align: center; }}
.wizard-exit-note {{ color: var(--muted); font-size: .9rem; margin-top: .35rem; }}
.beta-note {{ background: color-mix(in srgb, #F6BF26 18%, var(--surface)); border: 1px solid color-mix(in srgb, #F6BF26 48%, var(--line)); border-radius: 1.1rem; padding: 1rem 1.1rem; }}
.setup-shell {{ border-radius: 1.25rem; padding: 1.1rem 1.15rem; margin: 1rem 0 1.2rem 0; }}
.setup-example {{ border-left: 4px solid var(--accent); background: var(--accent-soft); padding: 0.85rem 1rem; border-radius: 12px; margin: 0.75rem 0 1rem 0; }}
.setup-step-label {{ display:inline-flex; gap:.35rem; align-items:center; padding:.28rem .62rem; border-radius:999px; background:var(--accent-soft); font-weight:760; font-size:.9rem; }}
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
.stButton button *, .stDownloadButton button *, [data-testid="stLinkButton"] a *, a[data-testid="baseLinkButton-secondary"] *, a[data-testid="baseLinkButton-primary"] *, .pathmark-link-button * {{ color: var(--button-ink) !important; }}
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stLinkButton"] a:hover, .pathmark-link-button:hover {{ filter: brightness(.96); color: var(--button-ink) !important; text-decoration: none !important; }}
.stButton button:disabled, .stDownloadButton button:disabled {{ filter: grayscale(.25); opacity: .55; }}
.pathmark-link-button {{ display: inline-flex; align-items: center; justify-content: center; width: 100%; padding: .55rem .85rem; }}
.pathmark-note, .pathmark-hint {{ background: var(--accent-soft); border: 1px solid var(--line); border-radius: 1rem; padding: .9rem 1rem; margin: .65rem 0 1rem; }}
.swatch-row {{ display:flex; flex-wrap:wrap; gap:.45rem; margin:.4rem 0 .7rem; }}
.swatch {{ display:inline-flex; align-items:center; gap:.35rem; border:1px solid var(--line); border-radius:999px; background:var(--surface); padding:.25rem .55rem; font-size:.85rem; }}
.swatch-dot {{ width:.9rem; height:.9rem; border-radius:999px; display:inline-block; border:1px solid rgba(0,0,0,.22); }}
.area-colour-preview {{ display:flex; align-items:center; gap:.6rem; border:1px solid var(--line); border-left:8px solid var(--accent); border-radius:1rem; background:var(--surface); padding:.8rem 1rem; margin:.35rem 0 1rem; }}
.area-colour-dot {{ width:1.15rem; height:1.15rem; border-radius:999px; border:1px solid rgba(0,0,0,.22); display:inline-block; flex:0 0 auto; }}
.process-card {{ border-radius:1rem; padding:1rem; margin:.55rem 0; }}
.process-card h4 {{ margin:.05rem 0 .35rem 0; }}
.process-card p {{ margin:0; color:var(--muted); }}
.dashboard-hero {{ padding:.15rem 0 .55rem 0; margin:0 0 .85rem 0; border-bottom:1px solid var(--line); }}
.dashboard-hero h2 {{ margin:.05rem 0 .25rem 0; font-size:clamp(1.9rem,3vw,2.55rem); letter-spacing:-.055em; }}
.dashboard-hero p {{ margin:0; color:var(--muted); max-width:820px; line-height:1.48; }}
.pillar-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.9rem; margin:1rem 0 1.35rem; align-items:stretch; }}
.pillar-card {{ background:var(--surface); border:1px solid var(--line); border-radius:1.05rem; padding:1rem 1.05rem; box-shadow:0 8px 20px var(--shadow), inset 0 0 0 1px color-mix(in srgb, var(--text-color, #1F2221) 6%, transparent); min-height:230px; display:flex; flex-direction:column; }}
.pillar-card h3 {{ margin:.1rem 0 .35rem; font-size:1.15rem; letter-spacing:-.025em; }}
.pillar-label {{ color:var(--muted); font-size:.78rem; font-weight:850; letter-spacing:.09em; text-transform:uppercase; margin-bottom:.55rem; }}
.pillar-card p {{ margin:0; color:var(--muted); font-size:.98rem; line-height:1.45; }}
@media (prefers-color-scheme: dark) {{
  :root {{
    --surface: color-mix(in srgb, var(--background-color, #0E1117) 84%, var(--text-color, #FAFAFA) 10%);
    --surface-2: color-mix(in srgb, var(--background-color, #0E1117) 78%, var(--text-color, #FAFAFA) 13%);
    --line: color-mix(in srgb, var(--text-color, #FAFAFA) 42%, var(--background-color, #0E1117));
    --muted: color-mix(in srgb, var(--text-color, #FAFAFA) 90%, var(--background-color, #0E1117));
  }}
}}
.pillar-metric {{ margin-top:auto; padding-top:.9rem; border-top:1px solid var(--line); }}
.pillar-stat {{ font-size:1.55rem; font-weight:780; line-height:1.1; }}
.pillar-foot {{ color:var(--muted); font-size:.88rem; margin-top:.2rem; }}
.dashboard-section {{ margin:1.45rem 0 .65rem; }}
.dashboard-section h3 {{ margin-bottom:.25rem; }}
.metric-strip {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.7rem; margin:.85rem 0 1.2rem; }}
.metric-tile {{ background:var(--surface); border:1px solid var(--line); border-radius:.95rem; padding:.9rem .95rem; box-shadow:none; }}
.metric-label {{ color:var(--muted); font-size:.84rem; font-weight:750; margin-bottom:.35rem; }}
.metric-value {{ font-size:1.35rem; font-weight:780; line-height:1.1; }}
.attention-card {{ background:var(--surface); border:1px solid var(--line); border-radius:1rem; padding:1rem 1.05rem; margin:.55rem 0; box-shadow:none; }}
.attention-card.high {{ border-left:5px solid #C2410C; }}

.overcommit-panel {{ background: color-mix(in srgb, #B45309 13%, var(--surface)); border:1px solid color-mix(in srgb, #B45309 45%, var(--line)); border-left:5px solid #B45309; border-radius:1rem; padding:1rem 1.05rem; margin:.9rem 0 1.2rem; }}
.overcommit-panel h4 {{ margin:.05rem 0 .3rem; letter-spacing:-.025em; }}
.overcommit-panel p {{ margin:.25rem 0 0; color:var(--muted); font-size:.98rem; line-height:1.48; }}
.overcommit-panel strong {{ color:var(--ink); }}
.pillar-card.warning {{ border-left:5px solid #B45309; }}
.metric-tile.warning {{ border-left:5px solid #B45309; }}
.attention-card.medium {{ border-left:5px solid var(--accent); }}
.attention-label {{ color:var(--muted); font-size:.78rem; font-weight:800; text-transform:uppercase; letter-spacing:.06em; margin-bottom:.2rem; }}
.attention-text {{ font-size:.98rem; line-height:1.45; }}
.next-action-card {{ background:var(--accent-soft); border:1px solid color-mix(in srgb,var(--accent) 35%,var(--line)); border-radius:1rem; padding:1rem 1.05rem; margin:.9rem 0 1.2rem; }}
.money-summary-card {{ background:var(--surface); border:1px solid var(--line); border-radius:1rem; padding:1rem 1.05rem; margin:.8rem 0 1.1rem; box-shadow:none; }}
.money-flow-table {{ width:100%; border-collapse:collapse; font-size:.96rem; }}
.money-flow-table th {{ text-align:left; color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.055em; padding:.55rem .45rem; border-bottom:1px solid var(--line); }}
.money-flow-table td {{ padding:.7rem .45rem; border-bottom:1px solid var(--line); }}
.money-flow-table tr:last-child td {{ border-bottom:none; }}
.money-amount {{ font-weight:780; white-space:nowrap; }}
.helper-row-card {{ background:var(--surface-2); border:1px solid var(--line); border-radius:.95rem; padding:.85rem .9rem; margin:.55rem 0; }}
.helper-row-card p {{ margin:0 0 .5rem 0; color:var(--muted); font-size:.92rem; }}
.repeat-summary {{ background:var(--surface-2); border:1px solid var(--line); border-radius:.95rem; padding:.85rem .95rem; margin:.65rem 0 1rem; }}
@media (max-width: 760px) {{
  .block-container {{ padding-left: .85rem; padding-right: .85rem; padding-top: .65rem; padding-bottom: 2.8rem; max-width: 100%; }}
  h1 {{ font-size: clamp(1.85rem, 8.5vw, 2.55rem); line-height: 1.08; margin-top: .75rem; }}
  h2 {{ font-size: clamp(1.55rem, 7.2vw, 2.15rem); line-height: 1.12; }}
  h3 {{ font-size: clamp(1.15rem, 5.4vw, 1.45rem); }}
  p, li {{ font-size: .98rem; line-height: 1.52; }}
  .hero {{ padding: 1.2rem 0 .8rem 0; }}
  .hero h1 {{ font-size: clamp(3.25rem, 20vw, 5.1rem); line-height: .88; margin-bottom: .7rem; }}
  .lead {{ font-size: 1.05rem; line-height: 1.32; }}
  .sublead {{ font-size: .98rem; margin-top: .45rem; }}
  .eyebrow {{ font-size: .82rem; padding: .34rem .6rem; margin-bottom: .85rem; }}
  .seasonal-banner {{ min-height: 82px; margin: .45rem 0 .95rem; border-radius: .95rem; box-shadow: 0 8px 18px color-mix(in srgb, #000000 7%, transparent); background-position: center center; }}
  .seasonal-banner-compact {{ min-height: 48px; margin: .4rem 0 .75rem; border-radius: .82rem; }}
  .seasonal-banner-content {{ padding: .65rem .7rem; }}
  .seasonal-banner-panel {{ padding: .55rem .65rem; border-radius: .75rem; max-width: calc(100vw - 2.2rem); }}
  .seasonal-banner-label {{ font-size: .68rem; padding: .25rem .48rem; }}
  .grid-3, .grid-2, .meta-grid, .pillar-grid {{ grid-template-columns: 1fr !important; gap: .75rem; margin: .85rem 0 1.1rem; }}
  .metric-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: .55rem; }}
  .card, .pillar-card, .meta-card, .download-panel, .setup-shell, .step-card, .process-card, .pathmark-card, .workspace-card, .issue-card, .attention-card, .money-summary-card, .focus-block-shell, .project-select-card {{ border-radius: .95rem; padding: .9rem; box-shadow: 0 5px 14px color-mix(in srgb, #000000 7%, transparent); }}
  .pillar-card {{ min-height: 0; }}
  .pillar-stat, .metric-value {{ font-size: 1.28rem; }}
  .project-due-card {{ align-items:flex-start; padding:.72rem .82rem; }}
  .support-block-group {{ margin-left: .45rem; padding: .55rem .55rem .65rem .7rem; }}
  .account-chip-row {{ gap: .35rem; opacity: .78; margin-bottom: .25rem; }}
  .account-chip {{ font-size: .72rem; padding: .16rem .46rem; max-width: calc(100vw - 2rem); }}
  .account-chip strong {{ display:inline-block; max-width: 12.5rem; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; white-space: nowrap; }}
  .connection-strip {{ font-size: .78rem; padding: .2rem .52rem; max-width: 100%; }}
  .stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a {{ min-height: 2.75rem; font-size: .95rem !important; border-radius: .82rem !important; }}
  [data-testid="stTabs"] > div:first-child {{ overflow-x: auto; overflow-y: hidden; white-space: nowrap; gap: .25rem; scrollbar-width: none; padding-bottom: .25rem; }}
  [data-testid="stTabs"] > div:first-child::-webkit-scrollbar {{ display: none; }}
  [data-testid="stTabs"] button[role="tab"], button[data-baseweb="tab"] {{ flex: 0 0 auto; border: 1px solid var(--line) !important; border-radius: 999px !important; margin-right: .28rem !important; min-height: 2.15rem !important; padding: .22rem .7rem !important; background: var(--surface) !important; color: var(--muted) !important; }}
  [data-testid="stTabs"] button[aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] {{ background: var(--accent-soft) !important; color: var(--pathmark-accent-ui, var(--accent)) !important; border-color: color-mix(in srgb, var(--pathmark-accent-ui, var(--accent)) 42%, var(--line)) !important; }}
  [data-testid="stTabs"] button[role="tab"] p, button[data-baseweb="tab"] p {{ font-size: .84rem !important; font-weight: 700 !important; }}
  div[data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; min-width: 0 !important; }}
  .stDataFrame, [data-testid="stDataFrame"] {{ overflow-x: auto; max-width: 100%; }}
  .step-card, .focus-block-shell, .focus-block-card, .support-card, .project-select-card, .card, .pillar-card, .metric-tile {{ max-width: 100%; overflow: hidden; }}
  .step-card *, .focus-block-shell *, .focus-block-card *, .support-card *, .project-select-card *, .card *, .pillar-card *, .metric-tile * {{ max-width: 100%; overflow-wrap: anywhere; word-break: normal; white-space: normal; }}
  .support-block-group {{ margin-left: .65rem; padding-left: .75rem; }}
  .support-block-group .support-card {{ padding: .8rem; }}
  .status-chip {{ max-width: 100%; white-space: normal; align-items: flex-start; }}
  .project-card-meta {{ max-width: 100%; overflow-wrap: anywhere; }}
}}

[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{
  color: var(--muted) !important;
}}
@media (max-width: 860px) {{ .pillar-grid, .metric-strip, .grid-3, .grid-2, .meta-grid {{ grid-template-columns:1fr; }} }}

/* Dark-safe contrast guardrails for Pathmark-owned components.
   Body/muted text must remain readable in Streamlit Dark mode, even when
   Streamlit's CSS variable names or browser System settings differ. */
.sublead, .small-muted, .pillar-card p, .card p, .process-card p, .dashboard-hero p,
.metric-label, .pillar-foot, .helper-row-card p, .wizard-hero p, .attention-label,
.meta-label, .wizard-progress-text, .wizard-nav-note, .wizard-exit-note, .money-flow-table th {{
  color: var(--muted) !important;
}}
.card, .meta-card, .download-panel, .account-card, .connection-card, .setup-shell, .guide-box,
.step-card, .process-card, .pathmark-card, .workspace-card, .issue-card, .pillar-card,
.metric-tile, .attention-card, .money-summary-card, .helper-row-card, .repeat-summary {{
  background: var(--surface) !important;
  border-color: var(--line) !important;
  color: var(--ink) !important;
}}
.card h3, .meta-card h3, .download-panel h3, .account-card h3, .connection-card h3, .setup-shell h3, .guide-box h3,
.step-card h3, .process-card h3, .pathmark-card h3, .workspace-card h3, .issue-card h3, .pillar-card h3,
.metric-tile h3, .attention-card h3, .money-summary-card h3, .helper-row-card h3, .repeat-summary h3,
.card h4, .meta-card h4, .download-panel h4, .account-card h4, .connection-card h4, .setup-shell h4, .guide-box h4,
.step-card h4, .process-card h4, .pathmark-card h4, .workspace-card h4, .issue-card h4, .pillar-card h4,
.metric-tile h4, .attention-card h4, .money-summary-card h4, .helper-row-card h4, .repeat-summary h4 {{
  color: var(--ink) !important;
}}
.helper-row-card, .repeat-summary, .metric-tile {{ background: var(--surface-2) !important; }}
.pillar-card, .card, .pathmark-card, .workspace-card, .download-panel {{
  border-top: 1px solid var(--line) !important;
}}
.pillar-card::before, .card::before, .pathmark-card::before, .workspace-card::before {{ content: none !important; }}

.progress-summary {{ margin:.65rem 0 1rem; }}
.progress-head {{ display:flex; justify-content:space-between; gap:.8rem; align-items:baseline; margin-bottom:.35rem; color:var(--muted); font-size:.92rem; font-weight:720; }}
.progress-track {{ height:9px; border-radius:999px; background:color-mix(in srgb, var(--muted) 18%, transparent); overflow:hidden; border:1px solid var(--line); }}
.progress-fill {{ height:100%; background:var(--accent); border-radius:999px; min-width:0; }}
.status-chip {{ display:inline-flex; align-items:center; border-radius:999px; border:1px solid var(--line); background:var(--surface-2); color:var(--muted); padding:.22rem .58rem; font-size:.82rem; font-weight:760; margin:.15rem .25rem .15rem 0; }}
.status-chip.done {{ background:color-mix(in srgb, #16A34A 18%, var(--surface)); color:var(--ink); border-color:color-mix(in srgb, #16A34A 45%, var(--line)); }}
.status-chip.pending {{ background:color-mix(in srgb, var(--accent) 13%, var(--surface)); color:var(--ink); border-color:color-mix(in srgb, var(--accent) 45%, var(--line)); }}
.status-chip.review {{ background:color-mix(in srgb, #B45309 15%, var(--surface)); color:var(--ink); border-color:color-mix(in srgb, #B45309 45%, var(--line)); }}
.status-chip.overdue {{ background:color-mix(in srgb, #DC2626 16%, var(--surface)); color:var(--ink); border-color:color-mix(in srgb, #DC2626 52%, var(--line)); }}
.status-chip.muted {{ background:var(--surface-2); color:var(--muted); }}
.item-status-row {{ margin-top:.55rem; display:flex; flex-wrap:wrap; gap:.2rem; }}
.project-due-card {{ margin:.45rem 0 .9rem; padding:.82rem .95rem; border-radius:1rem; border:1px solid var(--line); background:var(--surface-2); display:flex; justify-content:space-between; gap:.8rem; align-items:center; flex-wrap:wrap; }}
.project-due-card.overdue {{ border-left:5px solid #DC2626; background:color-mix(in srgb, #DC2626 9%, var(--surface)); }}
.project-due-card.due-soon {{ border-left:5px solid #B45309; background:color-mix(in srgb, #B45309 9%, var(--surface)); }}
.project-due-card.clear {{ border-left:5px solid var(--accent); }}
.project-due-label {{ color:var(--muted); font-size:.82rem; font-weight:800; letter-spacing:.055em; text-transform:uppercase; }}
.project-due-main {{ font-size:1.05rem; font-weight:780; color:var(--ink); }}
.focus-block-shell {{ border:1px solid color-mix(in srgb, var(--accent) 42%, var(--line)); border-left:5px solid color-mix(in srgb, var(--accent) 62%, var(--line)); border-radius:1.18rem; background:color-mix(in srgb, var(--surface) 94%, var(--accent-soft) 6%); padding:1rem; margin:1rem 0 1.25rem; overflow:hidden; }}
.focus-block-shell .focus-block-card {{ margin:0 0 .85rem 0; box-shadow:none; border-radius:1rem; background:var(--surface) !important; }}
.support-block-group {{ margin:.45rem 0 0 1.45rem; padding:.15rem 0 .05rem 1rem; border-left:3px solid color-mix(in srgb, var(--accent) 42%, var(--line)); background:transparent; }}
.support-block-group .support-card {{ margin:.65rem 0 0 0; box-shadow:none; border-radius:.95rem; background:var(--surface-2) !important; border-left:4px solid color-mix(in srgb, var(--muted) 40%, var(--line)); }}
.support-block-group-label {{ color:var(--muted); font-size:.76rem; font-weight:850; letter-spacing:.075em; text-transform:uppercase; margin:.05rem 0 .25rem; }}
.support-block-empty {{ color:var(--muted); font-size:.92rem; padding:.45rem .2rem; }}
.project-select-card {{ border:1px solid var(--line); border-left:5px solid var(--line); border-radius:.95rem; background:var(--surface); padding:.72rem .85rem; margin:.45rem 0; }}
.project-select-card.overdue {{ border-left-color:#DC2626; background:color-mix(in srgb, #DC2626 7%, var(--surface)); }}
.project-select-card.due-soon {{ border-left-color:#B45309; background:color-mix(in srgb, #B45309 7%, var(--surface)); }}
.project-select-card.clear {{ border-left-color:var(--accent); }}
.project-select-title {{ font-weight:780; color:var(--ink); margin-bottom:.22rem; }}
.project-select-meta {{ color:var(--muted); font-size:.88rem; line-height:1.35; }}

/* Appearance contrast is paired through Streamlit CSS variables above.
   Avoid separate dark-mode text rules; they can place light text on a light
   card if the menu changes before a full rerun. */


.pathmark-terms-box {{ max-height: 420px; overflow-y: auto; padding: 1rem 1.1rem; border: 1px solid var(--pm-border); border-radius: 16px; background: var(--pm-card-bg); color: var(--pm-card-text); }}
.pathmark-terms-box h3, .pathmark-terms-box h4 {{ color: var(--pm-card-text); margin-top: .7rem; margin-bottom: .35rem; }}
.pathmark-terms-box p {{ color: var(--pm-card-muted); margin: 0 0 .65rem 0; line-height: 1.45; }}
.policy-link-row {{ display:flex; flex-wrap:wrap; gap:.55rem; margin:1rem 0 1.2rem; }}
.policy-link-row a {{ display:inline-flex; align-items:center; border:1px solid var(--line); background:var(--surface); border-radius:999px; padding:.42rem .72rem; color:var(--ink); text-decoration:none; font-weight:650; font-size:.92rem; }}
.policy-link-row a:hover {{ border-color:var(--accent); color:var(--accent); text-decoration:none; }}
.oauth-domain-card {{ border:1px solid var(--line); background:var(--surface); border-radius:1rem; padding:1rem 1.05rem; margin:.8rem 0; }}
.oauth-domain-card code {{ background:var(--surface-2); border:1px solid var(--line); border-radius:.35rem; padding:.08rem .25rem; }}
.theme-config-preview {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: .85rem; white-space: pre-wrap; border: 1px solid var(--pm-border); border-radius: 14px; padding: .8rem; background: var(--pm-card-bg); color: var(--pm-card-text); max-height: 260px; overflow: auto; }}

/* Mobile containment and polished project hierarchy */
html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
  max-width: 100vw !important;
  overflow-x: hidden !important;
}}
*, *::before, *::after {{ box-sizing: border-box; }}
.block-container, .main .block-container {{ width: 100% !important; max-width: min(1180px, calc(100vw - 2rem)) !important; overflow-x: hidden !important; }}
.card, .pillar-card, .step-card, .focus-block-shell, .focus-block-card, .support-card, .project-select-card, .metric-tile, .attention-card, .money-summary-card, .seasonal-banner, .download-panel, .setup-shell, .pathmark-card, .workspace-card {{
  max-width: 100% !important;
  overflow-wrap: anywhere;
  word-break: normal;
}}
.step-card p, .focus-block-card p, .support-card p, .project-card-meta, .item-status-row, .status-chip, .small-muted {{
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: normal;
  white-space: normal;
}}
.item-status-row {{ display:flex; flex-wrap:wrap; gap:.35rem; align-items:center; }}
.status-chip {{ max-width: 100%; }}
.focus-block-shell {{
  border: 1px solid var(--line);
  border-left: 5px solid color-mix(in srgb, var(--accent) 62%, var(--line));
  border-radius: 1.15rem;
  background: color-mix(in srgb, var(--surface) 94%, var(--accent-soft) 6%);
  padding: 1rem;
  margin: .9rem 0 1.15rem;
  box-shadow: 0 8px 20px var(--shadow);
}}
.focus-block-card, .support-card {{
  border: 1px solid var(--line);
  background: var(--surface);
  border-radius: 1rem;
  padding: 1rem;
  margin: .35rem 0 .7rem;
}}
.focus-block-card {{ border-left: 5px solid var(--accent); }}
.support-block-group {{
  margin: .85rem 0 .25rem 1.15rem;
  padding: .25rem 0 .15rem 1rem;
  border-left: 2px solid color-mix(in srgb, var(--accent) 35%, var(--line));
}}
.support-block-group-label {{
  color: var(--muted);
  font-size: .76rem;
  font-weight: 850;
  letter-spacing: .095em;
  text-transform: uppercase;
  margin: .2rem 0 .45rem;
}}
.support-card {{ background: var(--surface-2); border-left: 4px solid color-mix(in srgb, var(--accent) 42%, var(--line)); }}
.project-card-meta {{ color: var(--muted); font-size:.94rem; line-height:1.42; margin:.45rem 0; }}
@media (max-width: 760px) {{
  html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{ overflow-x: hidden !important; width: 100vw !important; }}
  .block-container, .main .block-container {{ padding-left: .85rem !important; padding-right: .85rem !important; max-width: 100vw !important; }}
  .hero h1 {{ font-size: clamp(3rem, 18vw, 4.6rem) !important; overflow-wrap: normal; }}
  .lead, .sublead {{ max-width: 100% !important; }}
  .focus-block-shell {{ padding: .85rem; margin: .75rem 0 1rem; border-radius: 1rem; }}
  .focus-block-card, .support-card {{ padding: .85rem; border-radius:.9rem; }}
  .focus-block-card h3, .support-card h3 {{ font-size: clamp(1.25rem, 7vw, 1.75rem) !important; line-height: 1.12; }}
  .support-block-group {{ margin-left: .55rem; padding-left: .7rem; }}
  .project-card-meta {{ font-size:.9rem; }}
  .stDataFrame, [data-testid="stDataFrame"], div[data-testid="stTable"] {{ max-width: 100% !important; overflow-x: auto !important; }}
}}



/* v0.7.4 responsive containment + focus hierarchy final overrides */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
  max-width: 100vw !important;
  overflow-x: hidden !important;
}}
.block-container, .main .block-container {{
  width: 100% !important;
  max-width: min(1280px, calc(100vw - 2rem)) !important;
  overflow-x: hidden !important;
}}
.element-container, [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"], div[data-testid="column"] {{
  max-width: 100% !important;
  min-width: 0 !important;
}}
.card, .pillar-card, .step-card, .focus-block-shell, .focus-block-card, .support-card, .project-select-card, .metric-tile, .attention-card, .money-summary-card, .seasonal-banner, .download-panel, .setup-shell, .pathmark-card, .workspace-card {{
  max-width: 100% !important;
  overflow-wrap: anywhere !important;
  word-break: normal !important;
}}
.step-card *, .focus-block-shell *, .focus-block-card *, .support-card *, .project-select-card *, .project-card-meta, .item-status-row, .status-chip {{
  max-width: 100% !important;
  overflow-wrap: anywhere !important;
  white-space: normal !important;
}}
.focus-block-shell {{
  border: 1px solid color-mix(in srgb, var(--accent) 42%, var(--line)) !important;
  border-left: 5px solid color-mix(in srgb, var(--accent) 62%, var(--line)) !important;
  border-radius: 1.18rem !important;
  background: color-mix(in srgb, var(--surface) 94%, var(--accent-soft) 6%) !important;
  padding: 1rem !important;
  margin: 1rem 0 1.25rem !important;
  overflow: hidden !important;
}}
.focus-block-shell .focus-block-card {{
  margin: 0 0 .8rem 0 !important;
  border-radius: 1rem !important;
  background: var(--surface) !important;
  box-shadow: none !important;
}}
.support-block-group {{
  margin: .45rem 0 0 1.45rem !important;
  padding: .15rem 0 .05rem 1rem !important;
  border-left: 3px solid color-mix(in srgb, var(--accent) 42%, var(--line)) !important;
  background: transparent !important;
}}
.support-block-group .support-card {{
  margin: .65rem 0 0 0 !important;
  border-radius: .95rem !important;
  background: var(--surface-2) !important;
  border-left: 4px solid color-mix(in srgb, var(--muted) 40%, var(--line)) !important;
  box-shadow: none !important;
}}
.support-block-empty {{
  color: var(--muted);
  font-size: .92rem;
  padding: .45rem .2rem;
}}
@media (max-width: 760px) {{
  .block-container, .main .block-container {{
    max-width: 100vw !important;
    padding-left: .85rem !important;
    padding-right: .85rem !important;
  }}
  .support-block-group {{
    margin-left: .55rem !important;
    padding-left: .7rem !important;
  }}
  .focus-block-shell {{
    padding: .85rem !important;
    border-radius: 1rem !important;
  }}
  .focus-block-card h3, .support-card h3 {{
    font-size: clamp(1.25rem, 7vw, 1.75rem) !important;
    line-height: 1.12 !important;
  }}
  .status-chip {{
    max-width: 100% !important;
    white-space: normal !important;
  }}
}}



/* v0.7.6 polished focus hierarchy and mobile containment */
.focus-block-card, .support-card {{
  overflow: hidden !important;
}}
.focus-block-card h3, .support-card h3 {{
  overflow-wrap: anywhere !important;
  word-break: normal !important;
}}
.support-block-group-label {{
  color: var(--muted) !important;
  font-size: .76rem !important;
  font-weight: 850 !important;
  letter-spacing: .095em !important;
  text-transform: uppercase !important;
  margin: .35rem 0 .4rem !important;
}}
.support-nesting-rail {{
  min-height: 100%;
  height: 100%;
  border-left: 3px solid color-mix(in srgb, var(--accent) 42%, var(--line));
  margin: .25rem auto;
}}
.support-card {{
  background: var(--surface-2) !important;
  border-left: 5px solid color-mix(in srgb, var(--accent) 38%, var(--line)) !important;
  margin: .3rem 0 .75rem !important;
}}
.project-card-meta {{
  overflow-wrap: anywhere !important;
  word-break: normal !important;
  white-space: normal !important;
}}
@media (max-width: 760px) {{
  .block-container, .main .block-container {{
    max-width: 100vw !important;
    overflow-x: hidden !important;
  }}
  .focus-block-card, .support-card {{
    padding: .82rem !important;
  }}
  .support-nesting-rail {{
    border-left-width: 2px;
  }}
}}




/* v0.7.8 desktop parity on narrow browsers
   Pathmark no longer presents a separate phone-app experience. Phones load the
   same desktop browser UI/data canvas; narrow browsers may pan horizontally
   rather than receiving a half-supported mobile layout. */
@media (max-width: 760px) {{
  html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
    width: auto !important;
    min-width: 1180px !important;
    max-width: none !important;
    overflow-x: auto !important;
  }}
  .block-container, .main .block-container {{
    width: 1180px !important;
    min-width: 1180px !important;
    max-width: 1180px !important;
    padding-left: 2.25rem !important;
    padding-right: 2.25rem !important;
    padding-top: 2.25rem !important;
    overflow-x: visible !important;
  }}
  [data-testid="stHorizontalBlock"] {{
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    width: 100% !important;
    min-width: 0 !important;
  }}
  div[data-testid="column"] {{
    flex: 1 1 0 !important;
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
  }}
  .hero h1 {{
    font-size: clamp(3.7rem, 8.2vw, 7.2rem) !important;
    line-height: .84 !important;
    overflow-wrap: normal !important;
    white-space: normal !important;
  }}
  .lead {{
    font-size: clamp(1.28rem, 2.4vw, 1.9rem) !important;
    max-width: 920px !important;
  }}
  .sublead {{
    font-size: 1.12rem !important;
    max-width: 850px !important;
  }}
  .grid-3 {{
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  }}
  .grid-2, .meta-grid {{
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }}
  .pillar-grid, .metric-strip {{
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  }}
  .seasonal-banner {{
    min-height: 156px !important;
    border-radius: 1.25rem !important;
  }}
  .seasonal-banner-compact {{
    min-height: 58px !important;
  }}
  .focus-block-shell {{
    padding: 1rem !important;
    border-radius: 1.18rem !important;
  }}
  .focus-block-card, .support-card {{
    padding: 1rem !important;
    border-radius: 1rem !important;
  }}
  .support-block-group {{
    margin-left: 1.45rem !important;
    padding-left: 1rem !important;
  }}
}}

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

    The hosted app now requests Google identity, the narrow drive.file scope,
    Google Tasks, and Google Calendar in one consent flow. This keeps the web companion login simple while avoiding a
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
        st.session_state["post_login_show_dashboard"] = True
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
    data, projects, routines, checklist items, Workspace files, or on-the-go entries.

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
    return True, "Theme saved to your Pathmark profile."


def theme_for_user(email: str) -> str:
    """Return the user's hosted seasonal theme preference from session/Supabase."""
    cached = st.session_state.get("hosted_theme_preference")
    if cached:
        return normalise_online_theme(cached)
    rec = read_supabase_user(email) if email else None
    theme = rec.get("theme_preference", "Seasonal") if rec else "Seasonal"
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
    """Render quiet signed-in controls for the hosted page."""
    configured = login_configured()
    cols = st.columns([6.6, 1.25])
    with cols[0]:
        if user.get("email"):
            st.markdown(
                f"<div class='account-chip-row'>"
                f"<span class='account-chip'>Signed in <strong>{html.escape(str(user.get('email')))}</strong></span>"
                f"<span class='account-chip'>Access <strong>{html.escape(role_label(role))}</strong></span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        elif configured:
            st.caption("Sign in with Google to access beta or developer features. You can download Pathmark without signing in.")
        else:
            st.caption("Login is not configured yet. Download Pathmark below.")
    with cols[1]:
        if user.get("email"):
            if st.button("Log out", use_container_width=True, key="hosted_logout_button"):
                clear_hosted_login_session()
                st.rerun()
        elif configured:
            if st.button("Log in with Google", use_container_width=True, key="hosted_login_button"):
                st.session_state["show_login_terms"] = True
                st.rerun()
        else:
            st.button("Log in not configured", use_container_width=True, disabled=True, key="hosted_login_disabled")


def render_google_permissions_onboarding(compact: bool = False) -> None:
    """Terms and privacy acceptance step shown before launching Google OAuth."""
    st.markdown("## Pathmark Online Terms & Privacy")
    st.caption("Please review and accept this notice before continuing to Google permissions.")
    terms_html = """
    <div class="pathmark-terms-box">
      <h3>Pathmark Online Terms & Privacy Notice</h3>
      <p><strong>Last updated:</strong> June 2026</p>
      <h4>1. What Pathmark is</h4>
      <p>Pathmark is a planning, wellbeing, project, calendar, task and spending-plan tool. It helps you organise routines, projects, tasklists, calendar time and money-flow planning.</p>
      <h4>2. Use of Google services</h4>
      <p>Pathmark Online uses Google sign-in and Google APIs so your active planning records can stay in files and services owned by your Google account. Google may show a permissions screen after you continue.</p>
      <h4>3. Pathmark Sync and Google Sheets</h4>
      <p>Pathmark creates or updates a Google Sheet called Pathmark Sync. This sheet stores your Pathmark Online records, including areas, projects, routines, tasklist rows, settings, sync metadata and Spending Plan rows.</p>
      <h4>4. Google Tasks Sync</h4>
      <p>When you use Google Tasks Sync, Pathmark can create checklist items in Google Tasks and read their status so Pathmark can show whether a task is not sent, pending, completed, missing or needs review. Pathmark does not create tasks unless you choose a sync action.</p>
      <h4>5. Google Calendar Sync</h4>
      <p>When you use Google Calendar Sync, Pathmark can create or reuse calendars named after your Pathmark Areas and create or update project and routine calendar events within those calendars. Pathmark stores linked calendar IDs and event IDs in Pathmark Sync. Pathmark does not create calendar events unless you choose a sync action.</p>
      <h4>6. Spending Plan disclaimer</h4>
      <p>The Spending Plan is a budgeting and planning tool only. It is not financial, legal, tax, mortgage, insurance, KiwiSaver, investment or debt advice. If you are in financial hardship, consider seeking support from an appropriate budgeting or financial-support service.</p>
      <h4>7. Backups and restore</h4>
      <p>Pathmark can create backup Google Sheets and can restore or reset Pathmark Sync when you ask it to. Some actions may create a safety backup first. Resetting Pathmark Sync does not automatically delete Google Tasks or Google Calendar events.</p>
      <h4>8. What Supabase stores</h4>
      <p>Supabase is used for access/profile metadata, such as email, role, status, feature flags, theme preference and audit records. Supabase may also hold optional read-only starter-pack library rows, such as grocery, nutrition, produce or recipe starter data. Supabase is not used to store your private planning, task, calendar, spending-plan content, or your edited grocery inventory.</p>
      <h4>9. What Pathmark does not do</h4>
      <p>Pathmark does not sell your data, does not store your Google password, does not store OAuth tokens in Supabase, does not use your planning or finance content for advertising, and does not intentionally scan unrelated Google Drive, Tasks or Calendar content.</p>
      <h4>10. User responsibility</h4>
      <p>You are responsible for the accuracy of information you enter, the Google files you share, and any changes you make through import, restore, reset, sync or delete actions. Review warnings before running bulk or destructive actions.</p>
      <h4>11. Revoking access</h4>
      <p>You can revoke Pathmark's Google access from your Google Account. If you revoke access, Pathmark Online will not be able to update Pathmark Sync, Google Tasks or Google Calendar until you reconnect.</p>
      <h4>12. Changes to Pathmark</h4>
      <p>Pathmark is under active development. Features, wording and data structures may change as the beta is refined. Backups are recommended before major imports, resets or sync changes.</p>
    </div>
    """
    st.markdown(terms_html, unsafe_allow_html=True)
    st.checkbox("I have read and accept the Pathmark Online Terms & Privacy notice.", key="google_permissions_ack")
    auth_url = login_auth_url()
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Back", use_container_width=True):
            st.session_state.pop("show_login_terms", None)
            st.session_state.pop("google_permissions_ack", None)
            st.rerun()
    with c2:
        if auth_url and st.session_state.get("google_permissions_ack"):
            same_tab_oauth_button("Continue to Google permissions", auth_url)
        elif auth_url:
            st.button("Continue to Google permissions", use_container_width=True, disabled=True)
        else:
            st.button("Google login unavailable", use_container_width=True, disabled=True)

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
        3. **Google Auth Platform → Branding**: set the app name to **Pathmark** and upload the Pathmark logo so Google's account/consent screens use Pathmark branding.
        4. **Google Auth Platform → Audience**: if the app is in Testing, add your Google account as a test user.
        5. **Google Auth Platform → Data Access**: include the requested scopes `https://www.googleapis.com/auth/drive.file`, `https://www.googleapis.com/auth/tasks`, and `https://www.googleapis.com/auth/calendar`.
        6. **APIs & Services → Library**: enable both **Google Sheets API** and **Google Drive API** for the same project.

        Pathmark requests Google identity, `drive.file`, Tasks and Calendar during sign-in so the user can approve the full Pathmark Google connection before entering the workspace. Tasks and Calendar sync actions remain user-controlled: Pathmark does not create Google Tasks or Calendar events unless the user chooses a sync action. The Drive scope lets Pathmark create and update files the user authorises, rather than requesting access to all spreadsheets.
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


def google_auth_url(extra_scopes: list[str] | None = None, return_hint: str = "on_the_go") -> str | None:
    cfg = google_oauth_config()
    if not cfg:
        return None
    try:
        user = current_user()
        user_email = str(user.get("email", "") or "").strip().lower()
        context = f"return={return_hint}&email={urllib.parse.quote(user_email, safe='')}" if user_email else f"return={return_hint}"
        state = make_signed_oauth_state("sheets", context=context)
        scopes: list[str] = []
        for scope in GOOGLE_SHEETS_SCOPES + list(extra_scopes or []):
            if scope not in scopes:
                scopes.append(scope)
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "online",
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
        st.session_state["google_oauth_state"] = state
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    except Exception:
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


def google_session_scopes() -> set[str]:
    raw = st.session_state.get("google_sheets_credentials")
    try:
        info = json.loads(raw) if raw else {}
        return {str(scope).strip() for scope in (info.get("scopes") or []) if str(scope).strip()}
    except Exception:
        return set()


def google_tasks_scope_ready() -> bool:
    scopes = google_session_scopes()
    return all(scope in scopes for scope in GOOGLE_TASKS_SCOPES)


def tasks_service():
    credentials = google_credentials_from_session()
    if not credentials:
        return None
    if not google_tasks_scope_ready():
        return None
    try:
        from googleapiclient.discovery import build  # type: ignore
        return build("tasks", "v1", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        st.warning(f"Could not connect to Google Tasks: {exc}")
        return None


def google_calendar_scope_ready() -> bool:
    scopes = google_session_scopes()
    return all(scope in scopes for scope in GOOGLE_CALENDAR_SCOPES)


def calendar_service():
    credentials = google_credentials_from_session()
    if not credentials:
        return None
    if not google_calendar_scope_ready():
        return None
    try:
        from googleapiclient.discovery import build  # type: ignore
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
    except Exception as exc:
        st.warning(f"Could not connect to Google Calendar: {exc}")
        return None


def pathmark_tasks_auth_available() -> bool:
    return web_oauth_available() and bool(google_auth_url())


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
            return False, "", "No Pathmark Sync sheet was found for this Google account. This is normal if you are new to Pathmark Online, or if you deleted the sheet while testing. You can create a fresh sheet, create one with starter examples, restore from a Pathmark Backup, or check Google Drive Trash."
        file = sorted(found_files, key=lambda f: str(f.get("modifiedTime", "")), reverse=True)[0]
        sheet_id = file.get("id", "")
        if sheet_id:
            st.session_state["sync_sheet_id"] = sheet_id
            return True, sheet_id, file.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{sheet_id}")
        return False, "", "The existing Pathmark sync sheet did not return a file ID."
    except Exception as exc:
        return False, "", f"Could not look for an existing Pathmark sync sheet: {exc}"


def ensure_pathmark_sync_sheet_ready() -> tuple[bool, str, str]:
    """Find or create the user's Pathmark sync sheet for the current session.

    If a previously linked sheet cannot be verified, clear the stale ID so the
    recovery screen can offer a fresh create/restore path. This is important
    when a user deletes Pathmark Sync from Google Drive: recovery must not
    depend on the missing sheet still being present.
    """
    existing = st.session_state.get("sync_sheet_id", "")
    if existing:
        service = sheets_service()
        if service is None:
            return False, "", "Google Sheets is not available for this session."
        try:
            ensure_pathmark_online_schema(service, existing)
            return True, existing, f"https://docs.google.com/spreadsheets/d/{existing}"
        except Exception as exc:
            st.session_state.pop("sync_sheet_id", None)
            st.session_state["sync_sheet_recovery_message"] = f"Pathmark could not verify the previously linked Pathmark Sync sheet. It may have been deleted, moved, or no longer authorised. Details: {safe_user_message(str(exc))}"
            return False, "", st.session_state["sync_sheet_recovery_message"]

    found, sheet_id, link_or_message = find_existing_sync_sheet()
    if found and sheet_id:
        service = sheets_service()
        if service is not None:
            ensure_pathmark_online_schema(service, sheet_id)
        return True, sheet_id, link_or_message

    st.session_state["sync_sheet_recovery_message"] = link_or_message
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


def create_user_sync_sheet(include_default_areas: bool = True) -> tuple[bool, str, str]:
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
                    body={"appProperties": {"pathmark_sync": "true", "pathmark_version": "0.6.74"}},
                    fields="id",
                ).execute()
        except Exception:
            pass
        ensure_pathmark_online_schema(service, sheet_id)
        if include_default_areas:
            load_default_areas(sheet_id)
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
    for key in list(st.session_state.keys()):
        if str(key).startswith(f"online_header::{sheet_id}::"):
            st.session_state.pop(key, None)
    st.session_state[ready_key] = True


def online_sheet_header(service: Any, sheet_id: str, table: str) -> list[str]:
    """Return the live header row for a Pathmark Sync tab.

    Older beta sheets can have a different valid column order. Saves must use
    the live header so values such as annual income do not shift when optional
    notes are blank.
    """
    fallback = list(ONLINE_TABLES.get(table, []))
    if not fallback:
        return []
    cache_key = f"online_header::{sheet_id}::{table}"
    cached = st.session_state.get(cache_key)
    if cached:
        return list(cached)
    end_col = sheet_col_letter(max(len(fallback) + 8, 1))
    try:
        values = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{table}!A1:{end_col}1",
        ).execute().get("values", [])
        header = [str(v) for v in values[0]] if values and values[0] else fallback
        header = header + [col for col in fallback if col not in header]
    except Exception:
        header = fallback
    st.session_state[cache_key] = header
    return header


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
    """Read all Planner tables with a single batch request.

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
        header = online_sheet_header(service, sheet_id, table) or columns
        now = utc_now_text()
        row = {col: str(record.get(col, "") or "") for col in header}
        if "created_at" in header and not row.get("created_at"):
            row["created_at"] = now
        if "updated_at" in header:
            row["updated_at"] = now
        if "status" in header and not row.get("status"):
            row["status"] = "active"
        if "source" in header and not row.get("source"):
            row["source"] = "pathmark_online"
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{table}!A:{sheet_col_letter(len(header))}",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [[row.get(col, "") for col in header]]},
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
    "spending_income": "income_id",
    "spending_expenses": "expense_id",
    "spending_accounts": "account_id",
    "wizard_drafts": "draft_id",
    "pending_changes": "sync_id",
    "task_prompts": "prompt_id",
    "grocery_categories": "category_id",
    "grocery_inventory": "inventory_id",
    "grocery_nutrition": "nutrition_id",
    "recipes": "recipe_id",
    "recipe_ingredients": "recipe_ingredient_id",
    "shopping_lists": "shopping_list_id",
    "shopping_items": "shopping_item_id",
}


def append_many_online_records(sheet_id: str, records_by_table: dict[str, list[dict[str, Any]]]) -> tuple[bool, str]:
    """Append starter/example records using the live header order for each tab."""
    sheet_id = extract_google_sheet_id(sheet_id)
    service = sheets_service()
    if service is None:
        return False, "Google Sheets is not available for this session."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        total = 0
        now = utc_now_text()
        for table, records in records_by_table.items():
            if not records:
                continue
            columns = ONLINE_TABLES.get(table)
            if not columns:
                continue
            header = online_sheet_header(service, sheet_id, table) or columns
            rows = []
            for record in records:
                row = {col: str(record.get(col, "") or "") for col in header}
                if "created_at" in header and not row.get("created_at"):
                    row["created_at"] = now
                if "updated_at" in header:
                    row["updated_at"] = now
                if "status" in header and not row.get("status"):
                    row["status"] = "active"
                if "source" in header and not row.get("source"):
                    row["source"] = "Pathmark Online starter examples"
                rows.append([row.get(col, "") for col in header])
            if rows:
                service.spreadsheets().values().append(
                    spreadsheetId=sheet_id,
                    range=f"{table}!A:{sheet_col_letter(len(header))}",
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


def mark_actions_exported(sheet_id: str, action_ids: list[str], export_type: str, *, archive: bool = False) -> tuple[bool, str]:
    ids = [str(x).strip() for x in action_ids if str(x).strip()]
    if not ids:
        return False, "No exported items were available to mark."
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
        if archive:
            return True, f"Archived {ok_count} selected item(s). Batch: {batch_id}."
        return True, f"Marked {ok_count} item(s) as exported. They remain in their project or routine until you pause or archive them. Batch: {batch_id}."
    return False, last_message or "Could not update the exported item records."


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
        role, status = resolve_role(user.get("email", ""), bool(user.get("email_verified", False))) if user else ("", "")
        if role_can_develop(role, status):
            with st.expander("Developer details", expanded=False):
                st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip())
        return
def dataframe_preview(df: pd.DataFrame, columns: list[str]) -> None:
    if df.empty:
        st.info("No records yet.")
    else:
        show_cols = [col for col in columns if col in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)



def pathmark_column_config(kind: str, label: str, **kwargs):
    """Return a Streamlit column_config object with a safe fallback.

    Some deployments can lag behind the current Streamlit column_config API.
    Pathmark should not fail a whole section just because an optional editor
    column type such as SelectboxColumn is unavailable.
    """
    config = getattr(st, "column_config", None)
    if config is None:
        return None
    kind_name = str(kind or "TextColumn")
    factory = getattr(config, kind_name, None)
    if factory is None and kind_name == "SelectboxColumn":
        factory = getattr(config, "TextColumn", None)
        kwargs = {k: v for k, v in kwargs.items() if k not in {"options"}}
    if factory is None:
        return None
    try:
        return factory(label, **kwargs)
    except Exception:
        fallback = getattr(config, "TextColumn", None)
        if fallback is not None:
            try:
                return fallback(label)
            except Exception:
                return None
    return None



def pathmark_column_config_map(config_map: dict[str, Any]) -> dict[str, Any] | None:
    cleaned = {k: v for k, v in (config_map or {}).items() if v is not None}
    return cleaned or None


def safe_data_editor(df: pd.DataFrame, *, column_order: list[str] | None = None, column_config: dict[str, Any] | None = None, **kwargs) -> pd.DataFrame:
    """Render st.data_editor with compatibility fallbacks for older Streamlit builds."""
    frame = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame(df)
    for col in column_order or []:
        if col not in frame.columns:
            frame[col] = ""
    safe_config = pathmark_column_config_map(column_config or {})
    try:
        return st.data_editor(frame, column_order=column_order, column_config=safe_config, **kwargs)
    except TypeError:
        try:
            return st.data_editor(frame, column_order=column_order, **kwargs)
        except Exception:
            return st.data_editor(frame, **{k: v for k, v in kwargs.items() if k not in {"column_order", "column_config"}})
    except Exception:
        return st.data_editor(frame, **{k: v for k, v in kwargs.items() if k not in {"column_order", "column_config"}})


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


def resolved_accent_theme(theme_name: str | None = None) -> tuple[str, dict[str, str]]:
    """Return the display name and accent tokens for the selected Pathmark theme."""
    theme_name = normalise_online_theme(theme_name)
    if theme_name == "Seasonal":
        season = current_southern_hemisphere_season()
        return f"Seasonal — {season}", SEASONAL_ACCENTS.get(season, SEASONAL_ACCENTS["Winter"])
    if theme_name == "Custom":
        custom = str(st.session_state.get("hosted_custom_accent", "#334E9E") or "#334E9E")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", custom):
            custom = "#334E9E"
        return "Custom", {"accent": custom, "accent_2": custom, "seasonal_icon": "", "custom": True}
    return theme_name, ONLINE_THEMES.get(theme_name, ONLINE_THEMES["Blue"])


def inject_theme_css(theme_name: str, appearance_mode: str = "System") -> None:
    """Apply Pathmark accent variables only.

    Streamlit owns System/Light/Dark. Pathmark accent themes affect only
    Pathmark-owned affordances such as buttons, tabs, card accent strips,
    progress bars, badges and highlight panels.
    """
    display_name, theme = resolved_accent_theme(theme_name)
    accent = theme.get("accent", "#334E68")
    accent_2 = theme.get("accent_2", accent)
    seasonal_icon = theme.get("seasonal_icon", "")
    st.markdown(
        f"""
        <style>
        :root {{
          --accent: {accent};
          --accent-2: {accent_2};
          --pathmark-accent: {accent};
          --pathmark-accent-2: {accent_2};
          --pathmark-accent-ui: color-mix(in srgb, var(--pathmark-accent) 76%, var(--text-color, #1F2221) 24%);
          --pathmark-accent-strong: color-mix(in srgb, var(--pathmark-accent) 72%, black);
          --accent-soft: color-mix(in srgb, var(--pathmark-accent-ui) 10%, var(--surface));
          --accent-soft-2: color-mix(in srgb, var(--pathmark-accent-2) 8%, var(--surface));
        }}
        .seasonal-theme-name::after {{ content: "{display_name}"; }}
        .eyebrow, .pathmark-note, .pathmark-hint, .setup-example, .area-colour-preview, .next-action-card {{
          background: var(--accent-soft);
        }}
        .guide-box {{
          border-left: 4px solid var(--pathmark-accent-ui);
          padding-left: 1.45rem;
        }}
        .setup-progress-fill, .wizard-progress-fill {{ background: var(--pathmark-accent-ui); }}
        .kicker, [data-testid="stTabs"] button[aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] {{
          color: var(--pathmark-accent-ui) !important;
        }}
        [data-testid="stTabs"] button[aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"] {{
          border-bottom-color: var(--pathmark-accent-ui) !important;
        }}
        .card, .pillar-card, .pathmark-card, .workspace-card, .download-panel {{
          border-top-color: color-mix(in srgb, var(--text-color, #1F2221) 32%, transparent) !important;
        }}
        .stButton button, .stDownloadButton button, [data-testid="stLinkButton"] a,
        a[data-testid="baseLinkButton-secondary"], a[data-testid="baseLinkButton-primary"], .pathmark-link-button {{
          background: var(--pathmark-accent-ui) !important;
          border-color: color-mix(in srgb, var(--pathmark-accent-ui) 60%, black) !important;
          color: #FFFFFF !important;
        }}
        .stButton button *, .stDownloadButton button *, [data-testid="stLinkButton"] a *,
        a[data-testid="baseLinkButton-secondary"] *, a[data-testid="baseLinkButton-primary"] *, .pathmark-link-button * {{
          color: #FFFFFF !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_online_theme(sheet_id: str) -> None:
    theme_name = online_setting(sheet_id, "theme", st.session_state.get("hosted_theme_preference", "Seasonal")) if sheet_id else st.session_state.get("hosted_theme_preference", "Seasonal")
    if sheet_id:
        st.session_state["hosted_custom_accent"] = online_setting(sheet_id, "custom_accent", st.session_state.get("hosted_custom_accent", "#334E9E"))
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


def monthly_pattern_to_rrule_part(pattern: Any) -> str:
    text = str(pattern or "").strip()
    if not text or text == "Same day of month as start date":
        return ""
    m = re.match(r"^(First|Second|Third|Fourth|Last)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$", text, flags=re.I)
    if not m:
        return ""
    ordinal_map = {"first": "1", "second": "2", "third": "3", "fourth": "4", "last": "-1"}
    day_map = {"monday": "MO", "tuesday": "TU", "wednesday": "WE", "thursday": "TH", "friday": "FR", "saturday": "SA", "sunday": "SU"}
    return ordinal_map[m.group(1).lower()] + day_map[m.group(2).lower()]


def is_monthly_pattern_text(value: Any) -> bool:
    text = str(value or "").strip()
    return text in MONTHLY_REPEAT_PATTERNS or bool(monthly_pattern_to_rrule_part(text))


def validate_routine_schedule(frequency: str, preferred_days: str) -> list[str]:
    problems: list[str] = []
    freq = str(frequency or "").strip()
    days = str(preferred_days or "").strip()
    if freq not in VALID_FREQUENCIES:
        problems.append("Choose a frequency from the list so calendar and task exports can interpret it.")
    if freq == "Weekly":
        valid_days, invalid_days = parse_days_text(days)
        if invalid_days:
            problems.append("Weekly repeat days must use weekday names such as Monday, Wednesday, Friday.")
        if not valid_days:
            problems.append("Weekly routines need at least one repeat day for reliable exports.")
    elif freq == "Weekdays":
        valid_days, invalid_days = parse_days_text(days)
        if invalid_days:
            problems.append("Weekdays routines should use weekday names only.")
        weekend = {"Saturday", "Sunday"}.intersection(valid_days)
        if weekend:
            problems.append("A Weekdays routine should not include Saturday or Sunday.")
    elif freq == "Monthly":
        if days and not is_monthly_pattern_text(days):
            problems.append("Monthly routines need a supported pattern, such as First Monday or Same day of month as start date.")
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


def nz_date_text(value: Any) -> str:
    """Return a user-facing New Zealand date string while preserving ISO storage elsewhere."""
    d = parse_online_date(value)
    return d.strftime("%d/%m/%Y") if d else str(value or "").strip()


def display_date(value: Any) -> str:
    """User-facing date label for simple date-only previews."""
    return nz_date_text(value)


def date_input_nz(label: str, value: date | None = None, *, key: str | None = None, help: str | None = None) -> date:
    """Streamlit date input with New Zealand day/month/year display."""
    kwargs: dict[str, Any] = {"value": value or date.today(), "format": "DD/MM/YYYY"}
    if key is not None:
        kwargs["key"] = key
    if help is not None:
        kwargs["help"] = help
    return st.date_input(label, **kwargs)


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
        problems.append("Scheduled date must be blank or a real date. Use DD/MM/YYYY, for example 08/06/2026.")
    if not valid_online_date(due):
        problems.append("Due date must be blank or a real date. Use DD/MM/YYYY, for example 08/06/2026.")
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
    if freq.lower() == "weekly" or (bydays and freq.lower() != "monthly"):
        return "RRULE:FREQ=WEEKLY" + (f";BYDAY={','.join(bydays)}" if bydays else "")
    if freq.lower() == "monthly":
        part = monthly_pattern_to_rrule_part(days)
        return "RRULE:FREQ=MONTHLY" + (f";BYDAY={part}" if part else "")
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
        if byday_codes:
            code = byday_codes[0]
            m = re.match(r"^(-?\d)(MO|TU|WE|TH|FR|SA|SU)$", code)
            if m:
                ord_label = {"1": "first", "2": "second", "3": "third", "4": "fourth", "-1": "last"}.get(m.group(1), m.group(1))
                return f"Repeats monthly on the {ord_label} {day_names.get(m.group(2), m.group(2))}"
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


def _pathmark_now_local() -> datetime:
    try:
        if ZoneInfo is not None:
            return datetime.now(ZoneInfo("Pacific/Auckland")).replace(tzinfo=None)
    except Exception:
        pass
    return datetime.now()


def _calendar_end_as_datetime(value: str, *, all_day: bool = False) -> datetime | None:
    text_value = str(value or "").strip()
    if not text_value:
        return None
    try:
        if all_day and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text_value):
            return datetime.combine(date.fromisoformat(text_value), time(23, 59))
        normalised = text_value.replace("T", " ").replace("Z", "").strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalised):
            return datetime.combine(date.fromisoformat(normalised), time(23, 59) if all_day else time(0, 0))
        return datetime.fromisoformat(normalised)
    except Exception:
        return None


def _should_stage_calendar_block(action: pd.Series, *, end_text: str, recurrence: str, all_day: bool) -> bool:
    """Return False for elapsed, unlinked one-off calendar blocks.

    Google Calendar is most useful for upcoming or still-active planned time.
    Completed past one-off blocks without an existing Google link stay out of
    the staging count so Google Sync does not make the page look busier than it
    is. Existing linked events and repeating routines are still included for
    status/repair/update workflows.
    """
    if str(recurrence or "").strip():
        return True
    if str(action.get("google_calendar_event_id", "") or "").strip():
        return True
    end_dt = _calendar_end_as_datetime(end_text, all_day=all_day)
    if end_dt is None:
        return True
    return end_dt >= _pathmark_now_local()


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
        item_type = str(action.get("item_type", "") or "").strip().lower()
        is_all_day_focus = item_type in {"project_focus", "focus_block", "focus block"}
        end_date_override = str(action.get("calendar_end_date", "") or "").strip()
        if is_all_day_focus:
            start_d = parse_online_date(base_date) or date.today()
            end_d = parse_online_date(end_date_override) or start_d
            if end_d < start_d:
                end_d = start_d
            start = start_d.isoformat()
            end = end_d.isoformat()
        else:
            start, end = online_event_bounds(base_date, action.get("calendar_start_time") or "09:00", action.get("calendar_end_time") or "10:00")
            if end_date_override:
                start_t = parse_online_time(action.get("calendar_start_time") or "09:00", "09:00")
                end_t = parse_online_time(action.get("calendar_end_time") or "10:00", "10:00")
                start_d = parse_online_date(base_date) or date.today()
                end_d = parse_online_date(end_date_override) or start_d
                start = datetime.combine(start_d, start_t).strftime("%Y-%m-%d %H:%M")
                end = datetime.combine(end_d, end_t).strftime("%Y-%m-%d %H:%M")
        recurrence = simple_rrule(routine.get("frequency"), routine.get("preferred_days") or action.get("activity_days")) if routine_id else ""
        if not _should_stage_calendar_block(action, end_text=end, recurrence=recurrence, all_day=is_all_day_focus):
            continue
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
            "all_day": "1" if is_all_day_focus else "0",
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
    extra_prompts = read_online_table(sheet_id, "task_prompts")
    goals, routines = parent_lookup(sheet_id)
    blocks = staged_calendar_blocks(sheet_id)
    rows = []
    action_by_id: dict[str, dict[str, Any]] = {}
    if not actions.empty and "action_id" in actions.columns:
        for _, action_row in actions.iterrows():
            aid_key = str(action_row.get("action_id", "") or "").strip()
            if aid_key:
                action_by_id[aid_key] = {k: action_row.get(k, "") for k in actions.columns}

    explicit_activity_linked_ids: set[str] = set()
    if not extra_prompts.empty:
        for _, prompt in extra_prompts.iterrows():
            prompt_status = str(prompt.get("status", "")).lower()
            prompt_has_google_link = bool(str(prompt.get("google_task_id", "") or "").strip())
            if prompt_status == "archived" or (prompt_status in {"done", "completed"} and not prompt_has_google_link):
                continue
            if str(prompt.get("task_kind", "")).strip().lower() == "activity":
                linked_id = str(prompt.get("linked_record_id", "") or "").strip()
                if linked_id:
                    explicit_activity_linked_ids.add(linked_id)

    if not actions.empty:
        for _, action in actions.iterrows():
            if not truthy_flag(action.get("reminder")):
                continue
            action_status = str(action.get("status", "")).lower()
            action_has_google_link = bool(str(action.get("google_task_id", "") or "").strip())
            if action_status == "paused" or (action_status == "done" and not action_has_google_link):
                continue
            aid = str(action.get("action_id", "") or uuid.uuid4().hex)
            if aid in explicit_activity_linked_ids:
                # Wizard-created records already have a dedicated activity checklist
                # item in task_prompts. Avoid creating a duplicate derived row.
                continue
            goal_id = str(action.get("goal_id", "") or "")
            routine_id = str(action.get("routine_id", "") or "")
            routine = routines.get(routine_id, {})
            if str(routine.get("status", "")).lower() == "paused":
                continue
            goal = goals.get(goal_id, {})
            area_name = action.get("area_name", "") or routine.get("area_name", "") or goal.get("area_name", "")
            defaults = area_defaults(sheet_id, str(area_name))
            title = str(action.get("title", "") or "Pathmark checklist item").strip()
            parent = routine.get("title") or goal.get("title") or ""
            base_note = str(action.get("notes") or action.get("description") or "")
            repeat = routine.get("frequency", "") if routine_id else ""
            linked = linked_calendar_summary_for_action(action, blocks)
            note_parts = [f"Routine: {parent}" if routine_id and parent else f"Project: {parent}" if goal_id and parent else "", base_note, f"Repeat pattern: {repeat}." if repeat else "", f"Reference calendar time: {action.get('calendar_start_time')}." if action.get('calendar_start_time') else "", linked]
            rows.append({
                "id": aid,
                "title": title,
                "area_name": area_name,
                "parent": parent,
                "due_date": action.get("scheduled_date") or action.get("due_date") or routine.get("next_due") or "",
                "reminder_time": "",
                "task_list": defaults.get("default_task_list") or area_name or "Pathmark",
                "notes": "\n\n".join([p for p in note_parts if str(p).strip()]),
                "repeat_pattern": repeat,
                "linked_calendar_summary": linked,
                "status": str(action.get("google_task_status", "") or "needsAction"),
                "source_table": "actions",
                "source_id": aid,
                "linked_record_id": aid,
                "linked_record_type": "routine_activity" if routine_id else str(action.get("item_type", "") or "project_progress"),
                "linked_parent_id": routine_id or goal_id,
                "linked_parent_type": "routine" if routine_id else "project" if goal_id else "",
                "source_record_type": "routine_activity" if routine_id else str(action.get("item_type", "") or "project_progress"),
                "google_task_list_id": str(action.get("google_task_list_id", "") or ""),
                "google_task_id": str(action.get("google_task_id", "") or ""),
                "google_task_status": str(action.get("google_task_status", "") or ""),
                "google_task_completed_at": str(action.get("google_task_completed_at", "") or ""),
                "google_task_updated_at": str(action.get("google_task_updated_at", "") or ""),
                "google_task_synced_at": str(action.get("google_task_synced_at", "") or ""),
                "sync_status": str(action.get("sync_status", "") or ""),
            })

    if not extra_prompts.empty:
        for _, prompt in extra_prompts.iterrows():
            prompt_status = str(prompt.get("status", "")).lower()
            prompt_has_google_link = bool(str(prompt.get("google_task_id", "") or "").strip())
            if prompt_status == "archived" or (prompt_status in {"done", "completed"} and not prompt_has_google_link):
                continue
            pid = str(prompt.get("prompt_id", "") or uuid.uuid4().hex)
            title = str(prompt.get("prompt_text", "") or prompt.get("title", "") or "Pathmark checklist item").strip()
            if not title:
                continue
            area_name = str(prompt.get("area_name", "") or "")
            linked_id = str(prompt.get("linked_record_id", "") or "")
            linked_action = action_by_id.get(linked_id, {})
            parent_activity_title = str(linked_action.get("title", "") or "").strip()
            linked_record_type = str(prompt.get("linked_record_type", "") or "").replace("_", " ").strip()
            linked = ""
            if linked_id and not blocks.empty:
                match = blocks[blocks["linked_record_id"].fillna("") == linked_id]
                if not match.empty:
                    b = match.iloc[0]
                    linked = f"Related Google Calendar item: {b.get('title','Calendar time')} ({b.get('start','')})"
            note_parts = [
                str(prompt.get("notes", "") or "Checklist item created by Pathmark."),
                f"Parent {linked_record_type}: {parent_activity_title}" if parent_activity_title and linked_record_type else f"Parent activity: {parent_activity_title}" if parent_activity_title else "",
                f"Linked record ID: {linked_id}" if linked_id else "",
                linked,
            ]
            rows.append({
                "id": pid,
                "title": title,
                "area_name": area_name,
                "parent": parent_activity_title or str(prompt.get("linked_parent_type", "") or ""),
                "due_date": str(prompt.get("due_date", "") or ""),
                "reminder_time": "",
                "task_list": str(prompt.get("task_list", "") or "Pathmark"),
                "notes": "\n\n".join([p for p in note_parts if str(p).strip()]),
                "repeat_pattern": "",
                "linked_calendar_summary": linked,
                "status": str(prompt.get("google_task_status", "") or prompt.get("status", "") or "needsAction"),
                "source_table": "task_prompts",
                "source_id": pid,
                "linked_record_id": linked_id,
                "linked_record_type": str(prompt.get("linked_record_type", "") or ""),
                "linked_parent_id": str(prompt.get("linked_parent_id", "") or ""),
                "linked_parent_type": str(prompt.get("linked_parent_type", "") or ""),
                "task_kind": str(prompt.get("task_kind", "") or ""),
                "source_record_type": str(prompt.get("linked_record_type", "") or prompt.get("task_kind", "") or "task_prompt"),
                "google_task_list_id": str(prompt.get("google_task_list_id", "") or ""),
                "google_task_id": str(prompt.get("google_task_id", "") or ""),
                "google_task_status": str(prompt.get("google_task_status", "") or ""),
                "google_task_completed_at": str(prompt.get("google_task_completed_at", "") or ""),
                "google_task_updated_at": str(prompt.get("google_task_updated_at", "") or ""),
                "google_task_synced_at": str(prompt.get("google_task_synced_at", "") or ""),
                "sync_status": str(prompt.get("sync_status", "") or ""),
            })
    return pd.DataFrame(rows)


def helper_prompts_for_action(sheet_id: str, action_id: str) -> pd.DataFrame:
    """Return active helper Google Tasks checklist items linked to a manual step/activity."""
    prompts = read_online_table(sheet_id, "task_prompts")
    if prompts.empty or not action_id:
        return pd.DataFrame(columns=ONLINE_TABLES["task_prompts"])
    df = prompts.copy()
    mask = (
        (df.get("linked_record_id", pd.Series(dtype=str)).fillna("").astype(str) == str(action_id))
        & (df.get("task_kind", pd.Series(dtype=str)).fillna("").astype(str).str.lower() == "helper")
        & (~df.get("status", pd.Series(dtype=str)).fillna("").astype(str).str.lower().isin({"archived", "done", "completed"}))
    )
    return df[mask].copy()


def _helper_state_key(form_id: str) -> str:
    return f"helper_rows_state_{form_id}"


def helper_rows_state_for_form(form_id: str, existing_helpers: pd.DataFrame, default_due: str = "") -> list[dict[str, str]]:
    key = _helper_state_key(form_id)
    if key not in st.session_state:
        rows: list[dict[str, str]] = []
        if existing_helpers is not None and not existing_helpers.empty:
            for _, row in existing_helpers.iterrows():
                title = str(row.get("title", "") or row.get("prompt_text", "") or "").strip()
                due = nz_date_text(row.get("due_date", "") or default_due)
                if title or due:
                    rows.append({"title": title, "due": due})
        if not rows:
            rows = [{"title": "", "due": nz_date_text(default_due or date.today().isoformat())}]
        st.session_state[key] = rows
    return st.session_state[key]


def reset_helper_rows_state(form_id: str) -> None:
    st.session_state.pop(_helper_state_key(form_id), None)


def helper_prompt_editor_rows(existing_helpers: pd.DataFrame, default_due: str = "") -> pd.DataFrame:
    """Build editable helper-checklist rows with one due date per item."""
    rows: list[dict[str, str]] = []
    if existing_helpers is not None and not existing_helpers.empty:
        for _, row in existing_helpers.iterrows():
            title = str(row.get("title", "") or row.get("prompt_text", "") or "").strip()
            due = nz_date_text(row.get("due_date", "") or default_due)
            if title:
                rows.append({"Checklist item": title, "Date to appear": due})
    # Keep a blank row visible so users discover that multiple helper items are possible.
    rows.append({"Checklist item": "", "Date to appear": nz_date_text(default_due) if default_due else ""})
    return pd.DataFrame(rows, columns=["Checklist item", "Date to appear"])


def clean_helper_prompt_rows(raw_rows: Any, default_due: str = "") -> tuple[list[dict[str, str]], list[str]]:
    """Normalise helper rows from the manual project/routine activity editor."""
    problems: list[str] = []
    cleaned: list[dict[str, str]] = []
    try:
        rows = raw_rows.to_dict("records") if isinstance(raw_rows, pd.DataFrame) else list(raw_rows or [])
    except Exception:
        rows = []
    for idx, row in enumerate(rows, start=1):
        title = str(row.get("Checklist item", "") or row.get("title", "") or "").strip(" -•\t")
        due_text = str(row.get("Date to appear", "") or row.get("due_date", "") or "").strip()
        if not title and not due_text:
            continue
        if not title:
            problems.append(f"Small checklist item {idx} needs a title, or remove its date.")
            continue
        if not due_text:
            due_text = default_due
        if not valid_online_date(due_text, allow_blank=False):
            problems.append(f"Small checklist item {idx} has an invalid date. Use DD/MM/YYYY, for example 08/06/2026.")
            continue
        cleaned.append({"title": title, "due_date": normalise_online_date(due_text)})
    return cleaned, problems


def replace_helper_prompts_for_action(
    sheet_id: str,
    *,
    action_id: str,
    action_title: str,
    area_name: str,
    linked_record_type: str,
    linked_parent_id: str,
    linked_parent_type: str,
    helper_rows: list[dict[str, str]] | None = None,
    helper_text: str = "",
    helper_due: str = "",
) -> None:
    """Replace helper checklist items for a manual action without touching the automatic activity item.

    Each helper item is saved as a separate Google Tasks export row with its own
    due date and a stable link back to the project step or routine activity it
    came from. ``helper_text``/``helper_due`` are retained for compatibility with
    older callers, but new UI code should pass ``helper_rows``.
    """
    if not action_id:
        return
    existing = helper_prompts_for_action(sheet_id, action_id)
    for _, prompt in existing.iterrows():
        pid = str(prompt.get("prompt_id", "") or "")
        if pid:
            update_online_record(sheet_id, "task_prompts", pid, {"status": "Archived", "updated_at": now_iso()})

    rows_in = helper_rows
    if rows_in is None:
        default_due = normalise_online_date(helper_due) if str(helper_due or "").strip() else ""
        rows_in = []
        for line in str(helper_text or "").splitlines():
            title = line.strip(" -•	")
            if title:
                rows_in.append({"title": title, "due_date": default_due})

    rows = []
    parent_label = linked_record_type.replace("_", " ")
    for item in rows_in or []:
        title = str(item.get("title", "") or item.get("Checklist item", "") or "").strip(" -•	")
        if not title:
            continue
        due = normalise_online_date(item.get("due_date", "") or item.get("Date to appear", "") or helper_due)
        rows.append({
            "prompt_id": f"prompt-{uuid.uuid4().hex}",
            "area_name": area_name,
            "title": title,
            "prompt_text": title,
            "due_date": due,
            "task_kind": "helper",
            "linked_record_id": action_id,
            "linked_record_type": linked_record_type,
            "linked_parent_id": linked_parent_id,
            "linked_parent_type": linked_parent_type,
            "task_list": "Pathmark",
            "notes": f"Helper checklist item for {parent_label}: {action_title}",
            "status": "Staged",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source": "manual_project_routine_form",
        })
    if rows:
        append_many_online_records(sheet_id, {"task_prompts": rows})



def _tasklist_is_supporting_row(row: pd.Series | dict[str, Any]) -> bool:
    item_type = str(row.get("item_type", "") or row.get("source_record_type", "") or "").strip().lower()
    return item_type in {"supporting_time", "supporting time", "supporting time block", "time_block", "time block"}


def _tasklist_human_date(value: Any) -> str:
    parsed = parse_online_date(value)
    if parsed is not None:
        return parsed.strftime("%d/%m/%Y")
    return str(value or "").strip()


def _tasklist_duration_label(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        minutes = int(float(raw))
        if minutes >= 1440:
            days = max(1, round(minutes / 1440))
            return "All day" if days == 1 else f"{days} days"
        if minutes >= 60 and minutes % 60 == 0:
            return f"{minutes // 60} hr" if minutes == 60 else f"{minutes // 60} hrs"
        return f"{minutes} min"
    except Exception:
        return raw


def tasklist_notes_text(row: pd.Series | dict[str, Any]) -> str:
    area = str(row.get("area_name", "") or "").strip()
    parent = str(row.get("parent", "") or "").strip()
    parent_focus = str(row.get("parent_progress_title", "") or "").strip()
    scheduled = _tasklist_human_date(row.get("scheduled_date", ""))
    due = _tasklist_human_date(row.get("due_date", ""))
    start_time = str(row.get("calendar_start_time", "") or "").strip()
    end_time = str(row.get("calendar_end_time", "") or "").strip()
    end_date = _tasklist_human_date(row.get("calendar_end_date", ""))
    duration = _tasklist_duration_label(row.get("estimated_minutes", ""))
    lines: list[str] = []
    top = " · ".join([bit for bit in [area, parent] if bit])
    if top:
        lines.append(top)
    if _tasklist_is_supporting_row(row) and parent_focus:
        lines.append(f"Supports: {parent_focus}")
    timing_bits = []
    if scheduled:
        timing_bits.append(f"Scheduled: {scheduled}")
    if due and due != scheduled:
        timing_bits.append(f"Due: {due}")
    elif due and not scheduled:
        timing_bits.append(f"Due: {due}")
    if timing_bits:
        lines.append(" · ".join(timing_bits))
    time_bits = []
    if start_time and end_time:
        finish = end_time if not end_date or end_date == scheduled else f"{end_date} {end_time}"
        time_bits.append(f"Time: {start_time}–{finish}")
    elif duration:
        time_bits.append(f"Time: {duration}")
    if duration and start_time and end_time:
        time_bits.append(f"Duration: {duration}")
    if time_bits:
        lines.append(" · ".join(time_bits))
    return "<br/>".join(lines)

def staged_tasklist(sheet_id: str) -> pd.DataFrame:
    actions = read_online_table(sheet_id, "actions")
    base_columns = ["action_id", "source_type", "title", "display_title", "area_name", "parent", "status", "scheduled_date", "due_date", "first_step", "estimated_minutes", "item_type", "parent_progress_item_id", "parent_progress_title", "calendar_start_time", "calendar_end_time", "calendar_end_date", "notes", "priority"]
    if actions.empty:
        return pd.DataFrame(columns=base_columns)
    goals, routines = parent_lookup(sheet_id)
    action_title_lookup: dict[str, str] = {}
    if "action_id" in actions.columns:
        for _, arow in actions.iterrows():
            aid = str(arow.get("action_id", "") or "").strip()
            if aid:
                action_title_lookup[aid] = str(arow.get("title", "") or "").strip()
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
        item_type = str(action.get("item_type", "") or "").strip()
        parent_progress_id = str(action.get("parent_progress_item_id", "") or "").strip()
        parent_progress_title = action_title_lookup.get(parent_progress_id, "")
        is_support = item_type.strip().lower() in {"supporting_time", "supporting time", "supporting time block", "time_block", "time block"}
        title = str(action.get("title", "") or "").strip()
        parent = routine_parent.get("title") or goals.get(goal_id, {}).get("title") or ""
        rows.append({
            "action_id": action.get("action_id", ""),
            "source_type": "Routine activity" if routine_id else "Goal action",
            "title": title,
            "display_title": title,
            "area_name": action.get("area_name", "") or routines.get(routine_id, {}).get("area_name", "") or goals.get(goal_id, {}).get("area_name", ""),
            "parent": parent,
            "status": status or ("Included" if routine_id else "Planned"),
            "scheduled_date": action.get("scheduled_date", ""),
            "due_date": action.get("due_date", ""),
            "first_step": action.get("first_step", ""),
            "estimated_minutes": action.get("estimated_minutes", ""),
            "item_type": item_type,
            "parent_progress_item_id": parent_progress_id,
            "parent_progress_title": parent_progress_title,
            "calendar_start_time": action.get("calendar_start_time", ""),
            "calendar_end_time": action.get("calendar_end_time", ""),
            "calendar_end_date": action.get("calendar_end_date", ""),
            "notes": action.get("notes", ""),
            "priority": action.get("priority", ""),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["sort_status"] = df["status"].map({"Next": 1, "Scheduled": 2, "Planned": 3, "Included": 4}).fillna(5)
        df["is_supporting_time_block"] = df.apply(_tasklist_is_supporting_row, axis=1)
        df["support_sort_anchor"] = df.apply(lambda r: str(r.get("parent_progress_item_id", "") or r.get("action_id", "") or ""), axis=1)
        # Keep supporting time blocks directly under the focus/progress item they support,
        # even when the support session is dated before the broader focus block.
        df = df.sort_values(["source_type", "parent", "support_sort_anchor", "is_supporting_time_block", "scheduled_date", "sort_status", "due_date", "title"], na_position="last").drop(columns=["sort_status", "support_sort_anchor"])
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


def build_default_area_records() -> dict[str, list[dict[str, Any]]]:
    """Create the default Area containers used by a fresh Pathmark Sync sheet.

    These are not full starter examples. They are broad, editable containers so
    a new user can use the wizard immediately without first inventing an Area
    taxonomy from an empty sheet.
    """
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    default_areas = [
        ("Body And Stability", "Sleep, movement, strength, mobility, appointments and routines that support energy.", "Sage"),
        ("Home, Relationships, and Admin", "Household reset, relationships, life admin, appointments, planning and everyday obligations.", "Basil"),
        ("Making And Craft", "Practical making, craft, tools, materials and hands-on projects.", "Tangerine"),
        ("Expression And Culture", "Creative practice, language, culture, reading and artistic development.", "Grape"),
        ("Skills And Tools", "Learning systems, software, techniques, equipment and practical capabilities you want to build.", "Teal"),
        ("Rest And Play", "Rest, play, low-pressure enjoyment, hobbies, recovery and unstructured time.", "Sky"),
    ]
    areas = []
    for name, description, colour in default_areas:
        areas.append({
            "area_id": f"area-{uuid.uuid4().hex}",
            "area_name": name,
            "description": description,
            "colour": colour,
            "status": "active",
            "default_calendar": name,
            "default_task_list": "Pathmark",
            "google_calendar_id": "",
            "google_calendar_name": name,
            "google_calendar_colour_id": GOOGLE_COLOUR_BY_LABEL.get(colour, {}).get("code", ""),
            "google_calendar_synced_at": "",
            "notes": "Default Area. Edit, rename, archive, or delete if it does not fit.",
            "created_at": now,
            "updated_at": now,
            "source": "Pathmark default areas",
        })
    settings = [{"key": "default_areas_loaded", "value": "yes", "updated_at": now, "source": "Pathmark default areas"}]
    return {"settings": settings, "areas": areas}


def load_default_areas(sheet_id: str) -> tuple[bool, str]:
    """Load default Areas only when the Areas table is empty."""
    try:
        existing = active_online_df(read_online_table(sheet_id, "areas"))
        if not existing.empty:
            return True, "Default areas were not added because this sync sheet already has Areas."
    except Exception:
        pass
    return append_many_online_records(sheet_id, build_default_area_records())


def build_starter_example_records() -> dict[str, list[dict[str, Any]]]:
    """Editable starter records modelled on the desktop starter-data approach.

    These are deliberately ordinary examples: food, sleep, exercise, admin and
    learning. They guide a new user without requiring everyone to keep the same
    routines or goals.
    """
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    area_body = f"area-{uuid.uuid4().hex}"
    area_home = f"area-{uuid.uuid4().hex}"
    area_making = f"area-{uuid.uuid4().hex}"
    area_expression = f"area-{uuid.uuid4().hex}"
    area_skills = f"area-{uuid.uuid4().hex}"
    area_rest = f"area-{uuid.uuid4().hex}"
    areas = [
        {"area_id": area_body, "area_name": "Body And Stability", "description": "Sleep, movement, strength, mobility, health appointments and routines that support energy.", "colour": "Sage", "status": "active", "default_calendar": "Body And Stability", "default_task_list": "Pathmark", "google_calendar_id": "", "google_calendar_name": "Body And Stability", "google_calendar_colour_id": "2", "google_calendar_synced_at": "", "notes": "Starter Area. Edit, rename, deactivate, or delete if it does not fit."},
        {"area_id": area_home, "area_name": "Home, Relationships, and Admin", "description": "Household reset, relationships, life admin, appointments, planning and everyday obligations.", "colour": "Basil", "status": "active", "default_calendar": "Home, Relationships, and Admin", "default_task_list": "Pathmark", "google_calendar_id": "", "google_calendar_name": "Home, Relationships, and Admin", "google_calendar_colour_id": "10", "google_calendar_synced_at": "", "notes": "Starter Area. Edit, rename, deactivate, or delete if it does not fit."},
        {"area_id": area_making, "area_name": "Making And Craft", "description": "Practical making, craft, tools, materials and hands-on projects.", "colour": "Tangerine", "status": "active", "default_calendar": "Making And Craft", "default_task_list": "Pathmark", "google_calendar_id": "", "google_calendar_name": "Making And Craft", "google_calendar_colour_id": "6", "google_calendar_synced_at": "", "notes": "Starter Area. Edit, rename, deactivate, or delete if it does not fit."},
        {"area_id": area_expression, "area_name": "Expression And Culture", "description": "Creative practice, language, culture, reading and artistic development.", "colour": "Grape", "status": "active", "default_calendar": "Expression And Culture", "default_task_list": "Pathmark", "google_calendar_id": "", "google_calendar_name": "Expression And Culture", "google_calendar_colour_id": "3", "google_calendar_synced_at": "", "notes": "Starter Area. Edit, rename, deactivate, or delete if it does not fit."},
        {"area_id": area_skills, "area_name": "Skills And Tools", "description": "Learning systems, software, techniques, equipment and practical capabilities you want to build.", "colour": "Teal", "status": "active", "default_calendar": "Skills And Tools", "default_task_list": "Pathmark", "google_calendar_id": "", "google_calendar_name": "Skills And Tools", "google_calendar_colour_id": "7", "google_calendar_synced_at": "", "notes": "Starter Area. Edit, rename, deactivate, or delete if it does not fit."},
        {"area_id": area_rest, "area_name": "Rest And Play", "description": "Rest, play, low-pressure enjoyment, hobbies, recovery and unstructured time.", "colour": "Sky", "status": "active", "default_calendar": "Rest And Play", "default_task_list": "Pathmark", "google_calendar_id": "", "google_calendar_name": "Rest And Play", "google_calendar_colour_id": "9", "google_calendar_synced_at": "", "notes": "Starter Area. Edit, rename, deactivate, or delete if it does not fit."},
    ]

    def routine(title: str, area_id: str, area_name: str, purpose: str, frequency: str, preferred_days: str, next_due: str, checklist: str = "") -> dict[str, Any]:
        return {"routine_id": f"routine-{uuid.uuid4().hex}", "area_id": area_id, "area_name": area_name, "title": title, "description": purpose, "frequency": frequency, "preferred_days": preferred_days, "duration_minutes": "", "status": "Active", "purpose": purpose, "next_due": next_due, "checklist": checklist, "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."}

    sleep_id = f"routine-{uuid.uuid4().hex}"
    cook_weeknight_id = f"routine-{uuid.uuid4().hex}"
    friday_takeaways_id = f"routine-{uuid.uuid4().hex}"
    sunday_meal_id = f"routine-{uuid.uuid4().hex}"
    strength_id = f"routine-{uuid.uuid4().hex}"
    violin_id = f"routine-{uuid.uuid4().hex}"
    running_id = f"routine-{uuid.uuid4().hex}"
    routines = [
        {"routine_id": sleep_id, "area_id": area_body, "area_name": "Body And Stability", "title": "Protect an 8-hour sleep block", "description": "Give tomorrow a better starting point by protecting enough time for sleep.", "frequency": "Daily", "preferred_days": "Every day", "duration_minutes": "480", "status": "Active", "purpose": "Protect sleep before adding more work to the system.", "next_due": date.today().isoformat(), "checklist": "Set wind-down time\nPut phone away\nPrepare tomorrow's first action", "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."},
        {"routine_id": cook_weeknight_id, "area_id": area_home, "area_name": "Home, Relationships, and Admin", "title": "Cook weeknight dinner", "description": "Prepare simple dinners on planned weeknights so food choices are easier.", "frequency": "Weekly", "preferred_days": "Monday, Wednesday", "duration_minutes": "45", "status": "Active", "purpose": "Make ordinary meals easier to start after work.", "next_due": next_weekday_iso("Monday"), "checklist": "Choose meal\nCheck ingredients\nCook and clean down", "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."},
        {"routine_id": friday_takeaways_id, "area_id": area_home, "area_name": "Home, Relationships, and Admin", "title": "Friday takeaway dinner", "description": "A deliberately planned low-effort meal slot rather than an accidental fallback.", "frequency": "Weekly", "preferred_days": "Friday", "duration_minutes": "30", "status": "Active", "purpose": "Give the week a simple food decision and avoid over-planning every evening.", "next_due": next_weekday_iso("Friday"), "checklist": "Choose option\nOrder or collect\nReset kitchen afterwards", "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."},
        {"routine_id": sunday_meal_id, "area_id": area_home, "area_name": "Home, Relationships, and Admin", "title": "Cook weekend meal", "description": "Cook a more relaxed weekend meal and optionally prepare leftovers.", "frequency": "Weekly", "preferred_days": "Sunday", "duration_minutes": "90", "status": "Active", "purpose": "Create a slower food routine that supports the coming week.", "next_due": next_weekday_iso("Sunday"), "checklist": "Choose recipe\nShop ingredients\nCook\nPack leftovers", "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."},
        {"routine_id": strength_id, "area_id": area_body, "area_name": "Body And Stability", "title": "Strength training", "description": "A four-session weekly strength routine split into A, B, C and D activities.", "frequency": "Weekly", "preferred_days": "Monday, Tuesday, Thursday, Friday", "duration_minutes": "45", "status": "Active", "purpose": "Keep strength work visible and repeatable.", "next_due": next_weekday_iso("Monday"), "checklist": "Warm up\nMain lift\nAccessory work\nLog session", "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."},
        {"routine_id": violin_id, "area_id": area_expression, "area_name": "Expression And Culture", "title": "Practice violin", "description": "A weekly creative practice block.", "frequency": "Weekly", "preferred_days": "Wednesday", "duration_minutes": "45", "status": "Active", "purpose": "Keep creative practice scheduled rather than only aspirational.", "next_due": next_weekday_iso("Wednesday"), "checklist": "Tune\nScales\nPiece work\nNote next focus", "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."},
        {"routine_id": running_id, "area_id": area_body, "area_name": "Body And Stability", "title": "Run 30 minutes", "description": "A weekday running habit that can be reduced or paused if recovery needs it.", "frequency": "Weekdays", "preferred_days": "Monday, Tuesday, Wednesday, Thursday, Friday", "duration_minutes": "30", "status": "Active", "purpose": "Make regular cardiovascular work easy to see in the calendar.", "next_due": next_weekday_iso("Monday"), "checklist": "Shoes ready\nEasy pace\nLog how it felt", "notes": "Starter routine. Edit, pause, retire, or delete if it does not fit."},
    ]

    def activity(routine_id: str, area_id: str, area_name: str, title: str, day: str, start: str, end: str, minutes: str, first_step: str, location: str = "") -> dict[str, Any]:
        return {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": "", "routine_id": routine_id, "area_id": area_id, "area_name": area_name, "title": title, "description": "Starter routine activity. Edit the day, time and prompt to suit you.", "status": "Included", "priority": "Medium", "specific_area": "", "due_date": "", "scheduled_date": "", "activity_days": day, "estimated_minutes": minutes, "calendar_block": "1", "reminder": "1", "include_tasklist": "1", "first_step": first_step, "task_reminder_time": start, "calendar_start_time": start, "calendar_end_time": end, "calendar_location": location, "notes": "Starter routine activity."}

    actions = [
        activity(sleep_id, area_body, "Body And Stability", "Sleep block", "Every day", "22:30", "06:30", "480", "Start wind-down routine"),
        activity(cook_weeknight_id, area_home, "Home, Relationships, and Admin", "Cook weeknight dinner", "Monday, Wednesday", "18:00", "18:45", "45", "Open the meal plan and start the first prep step"),
        activity(friday_takeaways_id, area_home, "Home, Relationships, and Admin", "Takeaway dinner", "Friday", "18:30", "19:00", "30", "Choose takeaway option"),
        activity(sunday_meal_id, area_home, "Home, Relationships, and Admin", "Cook weekend meal", "Sunday", "17:00", "18:30", "90", "Open the recipe and check ingredients"),
        activity(strength_id, area_body, "Body And Stability", "Strength training A", "Monday", "07:00", "07:45", "45", "Start warm-up for strength A"),
        activity(strength_id, area_body, "Body And Stability", "Strength training B", "Tuesday", "07:00", "07:45", "45", "Start warm-up for strength B"),
        activity(strength_id, area_body, "Body And Stability", "Strength training C", "Thursday", "07:00", "07:45", "45", "Start warm-up for strength C"),
        activity(strength_id, area_body, "Body And Stability", "Strength training D", "Friday", "07:00", "07:45", "45", "Start warm-up for strength D"),
        activity(violin_id, area_expression, "Expression And Culture", "Practice violin", "Wednesday", "19:00", "19:45", "45", "Tune violin and start with scales"),
        activity(running_id, area_body, "Body And Stability", "Run 30 minutes", "Monday, Tuesday, Wednesday, Thursday, Friday", "17:30", "18:00", "30", "Put on running shoes and start easy"),
    ]

    sketch_goal = f"goal-{uuid.uuid4().hex}"
    run_goal = f"goal-{uuid.uuid4().hex}"
    goals = [
        {"goal_id": sketch_goal, "area_id": area_expression, "area_name": "Expression And Culture", "title": "Learn to sketch", "description": "Build enough basic skill to sketch simple forms confidently.", "specific_area": "Sketching", "status": "Captured", "target_date": "", "purpose": "Create a small creative learning project with clear first actions.", "desired_outcome": "Complete a few beginner sketching exercises and keep the materials ready.", "closure_criteria": "A beginner guide has been started and at least three sketches have been completed.", "notes": "Starter goal. Edit, archive or replace if it does not fit."},
        {"goal_id": run_goal, "area_id": area_body, "area_name": "Body And Stability", "title": "Build running distance", "description": "Increase distance gradually while keeping the next step clear.", "specific_area": "Running", "status": "Captured", "target_date": "", "purpose": "Turn a broad running ambition into visible next actions.", "desired_outcome": "Run 6.5 km comfortably enough to plan the next distance step.", "closure_criteria": "6.5 km run completed and next distance goal chosen.", "notes": "Starter goal. Edit, archive or replace if it does not fit."},
    ]
    actions.extend([
        {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": sketch_goal, "routine_id": "", "area_id": area_expression, "area_name": "Expression And Culture", "title": "Purchase beginner sketching guide", "description": "Find and purchase a beginner-friendly sketching guide.", "status": "Next", "priority": "Medium", "specific_area": "Sketching", "due_date": "", "scheduled_date": "", "activity_days": "", "estimated_minutes": "30", "calendar_block": "0", "reminder": "1", "include_tasklist": "1", "first_step": "Search for one beginner sketching guide", "task_reminder_time": "09:00", "calendar_start_time": "09:00", "calendar_end_time": "09:30", "calendar_location": "", "notes": "Starter action."},
        {"action_id": f"action-{uuid.uuid4().hex}", "goal_id": sketch_goal, "routine_id": "", "area_id": area_expression, "area_name": "Expression And Culture", "title": "Purchase sketching materials", "description": "Buy a simple sketchbook, pencils and eraser.", "status": "Planned", "priority": "Medium", "specific_area": "Sketching", "due_date": "", "scheduled_date": "", "activity_days": "", "estimated_minutes": "30", "calendar_block": "0", "reminder": "1", "include_tasklist": "1", "first_step": "Choose a sketchbook and pencil set", "task_reminder_time": "09:00", "calendar_start_time": "09:00", "calendar_end_time": "09:30", "calendar_location": "", "notes": "Starter action."},
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
    Create broad Areas such as Body And Stability, Expression And Culture, Home, Relationships, and Admin, or Making And Craft. Pathmark uses each Area to group related routines and projects, and to place synced calendar time into the matching Google calendar.</div>
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
            name = st.text_input("Area name", key="add_area_name", placeholder="For example, Body And Stability")
            description = st.text_area("Description", key="add_area_description", height=90, placeholder="Sleep, movement, strength, mobility and health routines.")
            colour_label = st.selectbox("Google Calendar colour", GOOGLE_COLOUR_LABELS, index=0, key="add_area_colour", help="Choose the colour Pathmark should use for this Area in Google Calendar exports.")
            render_google_colour_swatch(colour_label)
            colour = google_colour_code(colour_label)
            default_calendar = name.strip()
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
                        "default_calendar": name.strip(),
                        "default_task_list": default_task_list.strip() or "Pathmark",
                        "google_calendar_id": "",
                        "google_calendar_name": name.strip(),
                        "google_calendar_colour_id": GOOGLE_COLOUR_BY_LABEL.get(colour_label, {}).get("code", ""),
                        "google_calendar_synced_at": "",
                        "notes": notes.strip(),
                    })
                    if ok:
                        st.success(message)
                    else:
                        st.warning(safe_user_message(message))
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
            default_calendar = name.strip()
            default_task_list = st.text_input("Default Google Tasks list", value=str(row.get("default_task_list", "")), key=f"edit_area_task_list_{selected_id}")
            notes = st.text_area("Notes", value=str(row.get("notes", "")), height=90, key=f"edit_area_notes_{selected_id}")
            if st.button("Save changes", use_container_width=True, key=f"edit_area_save_{selected_id}"):
                if not name.strip():
                    st.error("Add an Area name before saving.")
                else:
                    ok, message = update_online_record(sheet_id, "areas", selected_id, {
                        "area_name": name.strip(), "description": description.strip(), "colour": colour,
                        "default_calendar": name.strip(), "default_task_list": default_task_list.strip(), "google_calendar_name": name.strip(), "google_calendar_colour_id": GOOGLE_COLOUR_BY_LABEL.get(colour_label, {}).get("code", ""), "notes": notes.strip(), "status": row.get("status", "active") or "active"
                    })
                    if ok:
                        st.success(message)
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
            if st.button("Archive Area", key=f"archive_area_{selected_id}"):
                ok, message = archive_online_record(sheet_id, "areas", selected_id, "Archived from Pathmark Online.")
                if ok:
                    st.success(message)
                else:
                    st.warning(safe_user_message(message))
                if ok:
                    st.rerun()



def _calendar_finish_validation(*, start_date: str, start_time: str, end_date: str, end_time: str) -> list[str]:
    """Validate that a mandatory Pathmark calendar entry has real start and finish details."""
    problems: list[str] = []
    if not str(start_date or "").strip():
        problems.append("Add the calendar start date.")
    elif not valid_online_date(start_date, allow_blank=False):
        problems.append("Calendar start date must be a real date. Use DD-MM-YYYY or YYYY-MM-DD.")
    if not str(end_date or "").strip():
        problems.append("Add the calendar finish date.")
    elif not valid_online_date(end_date, allow_blank=False):
        problems.append("Calendar finish date must be a real date. Use DD-MM-YYYY or YYYY-MM-DD.")
    if not str(start_time or "").strip():
        problems.append("Add the calendar start time.")
    elif not valid_online_time(start_time, allow_blank=False):
        problems.append("Calendar start time must be a real time, for example 09:00 or 7:30pm.")
    if not str(end_time or "").strip():
        problems.append("Add the calendar finish time.")
    elif not valid_online_time(end_time, allow_blank=False):
        problems.append("Calendar finish time must be a real time, for example 10:00 or 8:15pm.")
    if problems:
        return problems
    start_d = parse_online_date(start_date)
    end_d = parse_online_date(end_date)
    start_t = parse_online_time(start_time)
    end_t = parse_online_time(end_time)
    if start_d and end_d:
        start_dt = datetime.combine(start_d, start_t)
        end_dt = datetime.combine(end_d, end_t)
        if end_dt <= start_dt:
            problems.append("Calendar finish must be after the calendar start.")
    return problems


def _minutes_between_calendar_bounds(start_date: str, start_time: str, end_date: str, end_time: str) -> str:
    """Return an estimated minute duration for tasklist context, leaving blank if invalid."""
    try:
        start_d = parse_online_date(start_date)
        end_d = parse_online_date(end_date)
        if not start_d or not end_d:
            return ""
        start_dt = datetime.combine(start_d, parse_online_time(start_time))
        end_dt = datetime.combine(end_d, parse_online_time(end_time))
        minutes = int((end_dt - start_dt).total_seconds() // 60)
        return str(minutes) if minutes > 0 else ""
    except Exception:
        return ""




def is_focus_project_action(row: pd.Series | dict[str, Any]) -> bool:
    item_type = str(row.get("item_type", "") or "").strip().lower() if row is not None else ""
    return item_type in {"project_focus", "focus_block", "focus block"}


def is_supporting_project_action(row: pd.Series | dict[str, Any]) -> bool:
    item_type = str(row.get("item_type", "") or "").strip().lower() if row is not None else ""
    return item_type in {"supporting_time", "supporting time", "supporting time block", "time_block", "time block"}


def project_has_focus_blocks(actions: pd.DataFrame, project_id: str) -> bool:
    if actions is None or actions.empty or "goal_id" not in actions.columns:
        return False
    project_rows = actions[actions["goal_id"].fillna("").astype(str) == str(project_id)]
    if project_rows.empty:
        return False
    return any(is_focus_project_action(row) for _, row in project_rows.iterrows())



def project_due_summary_html(project: pd.Series | dict[str, Any]) -> str:
    raw = str(project.get("target_date", "") or "").strip()
    if not raw:
        return "<div class='project-due-card clear'><div><div class='project-due-label'>Target date</div><div class='project-due-main'>No target date set</div></div><span class='status-chip muted'>No due date</span></div>"
    parsed = parse_online_date(raw)
    display = _tasklist_human_date(raw)
    status = str(project.get("status", "") or "").strip().lower()
    if parsed is None:
        return f"<div class='project-due-card'><div><div class='project-due-label'>Target date</div><div class='project-due-main'>{html.escape(display)}</div></div><span class='status-chip review'>Check date</span></div>"
    today = _today_nz()
    days = (parsed - today).days
    complete_statuses = {"closed", "done", "completed", "archived", "abandoned"}
    if status in complete_statuses:
        chip = status_chip("Closed")
        card_class = "clear"
        helper = "Target retained for reference"
    elif days < 0:
        chip = status_chip(f"Overdue by {abs(days)} day" + ("" if abs(days) == 1 else "s"))
        card_class = "overdue"
        helper = "Needs review"
    elif days == 0:
        chip = status_chip("Due today")
        card_class = "due-soon"
        helper = "Due today"
    elif days <= 7:
        chip = status_chip(f"Due in {days} day" + ("" if days == 1 else "s"))
        card_class = "due-soon"
        helper = "Coming up"
    else:
        chip = status_chip(f"Due in {days} days")
        card_class = "clear"
        helper = "On the horizon"
    return f"<div class='project-due-card {card_class}'><div><div class='project-due-label'>{html.escape(helper)}</div><div class='project-due-main'>Target: {html.escape(display)}</div></div>{chip}</div>"


def project_due_sort_label(project: pd.Series | dict[str, Any]) -> str:
    raw = str(project.get("target_date", "") or "").strip()
    parsed = parse_online_date(raw)
    if parsed is None:
        return "No target date"
    today = _today_nz()
    days = (parsed - today).days
    if days < 0:
        return f"Overdue · {parsed.strftime('%d/%m/%Y')}"
    if days == 0:
        return "Due today"
    if days <= 7:
        return f"Due soon · {parsed.strftime('%d/%m/%Y')}"
    return f"Due {parsed.strftime('%d/%m/%Y')}"


def project_due_class(project: pd.Series | dict[str, Any]) -> str:
    raw = str(project.get("target_date", "") or "").strip()
    parsed = parse_online_date(raw)
    status = str(project.get("status", "") or "").strip().lower()
    if status in {"closed", "done", "completed", "archived", "abandoned"}:
        return "clear"
    if parsed is None:
        return "clear"
    days = (parsed - _today_nz()).days
    if days < 0:
        return "overdue"
    if days <= 7:
        return "due-soon"
    return "clear"


def render_project_visibility_cards(projects: pd.DataFrame, selected_id: str = "") -> None:
    if projects is None or projects.empty:
        return
    st.markdown("#### Due dates at a glance")
    for _, prow in projects.iterrows():
        pid = str(prow.get("goal_id", "") or "")
        cls = project_due_class(prow)
        selected = " · selected" if pid == selected_id else ""
        title = str(prow.get("title", "Untitled project") or "Untitled project")
        status = str(prow.get("status", "") or "").strip()
        due = project_due_sort_label(prow)
        st.markdown(
            f"<div class='project-select-card {cls}'><div class='project-select-title'>{html.escape(title)}</div><div class='project-select-meta'>{html.escape(status)} · {html.escape(due)}{html.escape(selected)}</div></div>",
            unsafe_allow_html=True,
        )


def project_action_counts_toward_progress(row: pd.Series | dict[str, Any]) -> bool:
    """Return whether a project action should count toward project completion.

    Older Pathmark rows do not have these fields, so project actions count by
    default. New supporting time blocks explicitly store contributes_to_progress
    as 0/No and are excluded from project progress.
    """
    if row is None:
        return True
    item_type = str(row.get("item_type", "") or "").strip().lower()
    flag = str(row.get("contributes_to_progress", "") or "").strip().lower()
    if is_supporting_project_action(row):
        return False
    if flag in {"0", "no", "false", "n", "support", "supporting", "not counted"}:
        return False
    return True


def project_action_type_label(row: pd.Series | dict[str, Any]) -> str:
    if is_focus_project_action(row):
        return "Focus block"
    return "Progress item" if project_action_counts_toward_progress(row) else "Supporting time block"


def project_progress_action_ids(sheet_id: str, project_id: str) -> set[str]:
    actions = active_online_df(read_online_table(sheet_id, "actions"))
    if actions.empty or "goal_id" not in actions.columns:
        return set()
    project_actions = actions[actions["goal_id"].fillna("").astype(str) == str(project_id)]
    ids = set()
    for _, row in project_actions.iterrows():
        if project_action_counts_toward_progress(row):
            aid = str(row.get("action_id", "") or "").strip()
            if aid:
                ids.add(aid)
    return ids


def project_supporting_actions_for_parent(actions: pd.DataFrame, parent_action_id: str) -> pd.DataFrame:
    if actions is None or actions.empty:
        return pd.DataFrame(columns=ONLINE_TABLES["actions"])
    if "parent_progress_item_id" not in actions.columns:
        return pd.DataFrame(columns=actions.columns)
    return actions[actions["parent_progress_item_id"].fillna("").astype(str) == str(parent_action_id)].copy()

def _project_work_card_html(sheet_id: str, row: pd.Series | dict[str, Any], linked: pd.DataFrame, *, blocks: pd.DataFrame | None = None, card_class: str = "focus-block-card") -> str:
    data = row.to_dict() if isinstance(row, pd.Series) else dict(row or {})
    rid = str(data.get("action_id", "") or "")
    title = str(data.get("title", "") or "Untitled").strip()
    item_label = project_action_type_label(data)
    sync_label = "Calendar time · tasklist · Google Tasks"
    date_bits: list[str] = []
    scheduled = str(data.get("scheduled_date", "") or "").strip()
    if scheduled:
        date_bits.append(f"Starts {human_calendar_datetime(scheduled)}")
    start_t = str(data.get("calendar_start_time", "") or "").strip()
    end_t = str(data.get("calendar_end_time", "") or "").strip()
    end_d = str(data.get("calendar_end_date", "") or scheduled or "").strip()
    if start_t and end_t:
        if end_d and end_d != scheduled:
            date_bits.append(f"{start_t} to {end_d} {end_t}")
        else:
            date_bits.append(f"{start_t} to {end_t}")
    recurrence = ""
    try:
        recurrence = linked_calendar_summary_for_action(pd.Series(data), blocks if blocks is not None else staged_calendar_blocks(sheet_id))
    except Exception:
        recurrence = ""
    if recurrence:
        date_bits.append(recurrence)
    parent_note = ""
    if is_supporting_project_action(data):
        parent_id = str(data.get("parent_progress_item_id", "") or "").strip()
        parent_title = ""
        if parent_id and linked is not None and not linked.empty and "action_id" in linked.columns:
            match = linked[linked["action_id"].fillna("").astype(str) == parent_id]
            if not match.empty:
                parent_title = str(match.iloc[0].get("title", "") or "").strip()
        if parent_title:
            parent_note = f"<div class='project-card-meta'><strong>Supports:</strong> {html.escape(parent_title)}</div>"
    helper_line = ""
    try:
        helper_df = helper_prompts_for_action(sheet_id, rid) if rid else pd.DataFrame()
        helper_titles = [str(r.get("title", "") or r.get("prompt_text", "") or "").strip() for _, r in helper_df.iterrows() if str(r.get("title", "") or r.get("prompt_text", "") or "").strip()]
        if helper_titles:
            helper_line = "<div class='project-card-meta'><strong>Small checklist items:</strong> " + html.escape("; ".join(helper_titles)) + "</div>"
    except Exception:
        helper_line = ""
    task_status_bits: list[str] = []
    try:
        task_items = action_task_items(sheet_id, rid) if rid else pd.DataFrame()
        if not task_items.empty:
            for _, task_row in task_items.iterrows():
                task_title = str(task_row.get("title", "") or "Checklist item").strip()
                task_status_bits.append(status_chip(f"{task_title}: {plain_task_label_for_status(task_row)}"))
        elif str(data.get("google_task_id", "") or "").strip() or str(data.get("google_task_status", "") or "").strip():
            task_status_bits.append(status_chip(_task_sync_user_label(pd.Series(data))))
        else:
            task_status_bits.append(status_chip("Not sent to Google Tasks"))
    except Exception:
        task_status_bits.append(status_chip("Task status unavailable"))
    detail = " · ".join([bit for bit in date_bits if str(bit).strip()])
    return f"""
    <div class='{html.escape(card_class)}'>
      <h3>{html.escape(title)}</h3>
      <div class='project-card-meta'>{html.escape(sync_label)}</div>
      <div class='project-card-meta'><strong>{html.escape(item_label)}</strong></div>
      {f"<div class='project-card-meta'>{html.escape(detail)}</div>" if detail else ""}
      {parent_note}
      <div class='item-status-row'>{''.join(task_status_bits)}</div>
      {helper_line}
    </div>
    """

def _render_action_list(sheet_id: str, linked: pd.DataFrame, *, goal_id: str = "", routine_id: str = "", default_area: str = "", show_heading: bool = True) -> None:
    """Render saved project steps or routine activities in a user-facing way."""
    kind = "routine activities" if routine_id else "project steps"
    if linked is None or linked.empty:
        st.info(f"No {kind} yet. Add one below when you are ready.")
        return

    blocks = staged_calendar_blocks(sheet_id)
    if show_heading:
        st.markdown(f"#### Saved {kind}")
    for _, row in linked.iterrows():
        data = {k: row.get(k, "") for k in linked.columns}
        rid = str(data.get("action_id", "") or "")
        title = str(data.get("title", "") or "Untitled activity")
        outputs = "Calendar time · weekly tasklist · Google Tasks checklist item"
        progress_label = ""
        if goal_id or str(data.get("goal_id", "") or "").strip():
            progress_label = project_action_type_label(data)
            if not project_action_counts_toward_progress(data):
                parent_id = str(data.get("parent_progress_item_id", "") or "").strip()
                if parent_id and "action_id" in linked.columns:
                    parent_match = linked[linked["action_id"].fillna("").astype(str) == parent_id]
                    if not parent_match.empty:
                        progress_label += f" · supports {parent_match.iloc[0].get('title', 'progress item')}"
        date_bits: list[str] = []
        if str(data.get("scheduled_date", "") or "").strip():
            date_bits.append(f"Starts {human_calendar_datetime(data.get('scheduled_date'))}")
        if str(data.get("calendar_start_time", "") or "").strip() or str(data.get("calendar_end_time", "") or "").strip():
            end_date = str(data.get("calendar_end_date", "") or data.get("scheduled_date", "") or "")
            date_bits.append(f"{data.get('calendar_start_time', '')} to {data.get('calendar_end_time', '')}" + (f" on {end_date}" if end_date and end_date != str(data.get('scheduled_date', '') or '') else ""))
        if str(data.get("activity_days", "") or "").strip():
            date_bits.append(f"Repeats on {data.get('activity_days')}")
        recurrence = linked_calendar_summary_for_action(row, blocks)
        if recurrence:
            date_bits.append(recurrence)
        detail = " · ".join([str(x) for x in date_bits if str(x).strip()])
        helper_df = helper_prompts_for_action(sheet_id, rid) if rid else pd.DataFrame(columns=ONLINE_TABLES["task_prompts"])
        helper_titles = [str(r.get("title", "") or r.get("prompt_text", "") or "").strip() for _, r in helper_df.iterrows() if str(r.get("title", "") or r.get("prompt_text", "") or "").strip()]
        helper_line = ""
        if helper_titles:
            helper_line = "<p><strong>Small action checklist items:</strong> " + html.escape("; ".join(helper_titles)) + "</p>"
        task_items_for_action = action_task_items(sheet_id, rid) if rid else pd.DataFrame()
        task_status_bits = []
        if not task_items_for_action.empty:
            for _, task_row in task_items_for_action.iterrows():
                task_title = str(task_row.get("title", "") or "Checklist item").strip()
                task_status_bits.append(status_chip(f"{task_title}: {plain_task_label_for_status(task_row)}"))
        elif str(data.get("google_task_id", "") or "").strip() or str(data.get("google_task_status", "") or "").strip():
            task_status_bits.append(status_chip(_task_sync_user_label(pd.Series(data))))
        else:
            task_status_bits.append(status_chip("Not sent to Google Tasks"))
        task_status_line = "<div class='item-status-row'>" + "".join(task_status_bits) + "</div>"
        st.markdown(
            f"""
            <div class='step-card'>
              <h3>{html.escape(title)}</h3>
              <p>{html.escape(outputs)}</p>
              {f"<p><strong>{html.escape(progress_label)}</strong></p>" if progress_label else ""}
              <p>{html.escape(detail)}</p>
              {task_status_line}
              {helper_line}
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
                if st.button("Archive this completed activity", key=f"archive_action_{rid}", use_container_width=True):
                    ok, message = archive_online_record(sheet_id, "actions", rid, "Completed or retired activity archived from Pathmark Online.")
                    if ok:
                        st.success("Activity archived. You can restore it from Archive.")
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()


def _action_form(sheet_id: str, *, goal_id: str = "", routine_id: str = "", default_area: str = "", form_key: str = "action", action: dict[str, Any] | None = None) -> None:
    """Add or edit a project step or routine activity.

    This form now follows the same Pathmark rule used by the Creation Wizard:
    every saved project step/routine activity automatically receives calendar
    time, a weekly tasklist row, and a Google Tasks checklist item. These are no
    longer optional switches in the manual Goals/Projects and Routines sections.
    """
    area_id = find_area_id(sheet_id, default_area) if default_area else ""
    is_routine_activity = bool(routine_id)
    action = action or {}
    record_id = str(action.get("action_id", "") or "")
    title_word = "Routine activity" if is_routine_activity else "Project step"
    form_id = f"online_{'edit' if record_id else 'add'}_{form_key}_{record_id or 'new'}"

    routine: dict[str, str] = {}
    if is_routine_activity and routine_id:
        routines_df = read_online_table(sheet_id, "routines")
        if not routines_df.empty and "routine_id" in routines_df.columns:
            match = routines_df[routines_df["routine_id"].fillna("") == routine_id]
            if not match.empty:
                routine = {k: str(match.iloc[0].get(k, "") or "") for k in routines_df.columns}

    project_mode = "Task-based"
    if goal_id and not is_routine_activity:
        goals_df = read_online_table(sheet_id, "goals")
        if not goals_df.empty and "goal_id" in goals_df.columns:
            gm = goals_df[goals_df["goal_id"].fillna("").astype(str) == str(goal_id)]
            if not gm.empty:
                project_mode = str(gm.iloc[0].get("planning_mode", "Task-based") or "Task-based")
    if project_mode not in {"Task-based", "Focus-based"}:
        project_mode = "Task-based"
    action_item_type = str(action.get("item_type", "") or "").strip().lower()
    is_supporting_time_block = (action_item_type in {"supporting_time", "supporting time", "supporting time block", "time_block", "time block"})
    is_focus_block = (not is_routine_activity and project_mode == "Focus-based" and not is_supporting_time_block)

    default_start_date = str(action.get("scheduled_date", "") or action.get("due_date", "") or routine.get("next_due", "") or "")
    default_end_date = str(action.get("calendar_end_date", "") or default_start_date or "")
    default_start_time = str(action.get("calendar_start_time", "") or "")
    default_end_time = str(action.get("calendar_end_time", "") or "")
    existing_helpers = helper_prompts_for_action(sheet_id, record_id) if record_id else pd.DataFrame(columns=ONLINE_TABLES["task_prompts"])
    helper_editor_default_due = default_start_date or date.today().isoformat()
    if not is_routine_activity:
        if project_mode == "Focus-based":
            title_word = "Supporting time block" if is_supporting_time_block else "Focus block"
        else:
            title_word = "Project step"

    with st.form(form_id, clear_on_submit=not bool(record_id)):
        st.markdown(f"### {'Edit' if record_id else 'Add'} {title_word.lower()}")
        if is_routine_activity:
            st.caption("Routine activities repeat according to the routine's repeat settings. Pathmark will automatically make calendar time and create tasklist/Google Tasks checklist items for this activity.")
        elif project_mode == "Focus-based" and is_supporting_time_block:
            st.caption("Supporting time blocks make time to work on a focus block. They appear in Calendar and Google Tasks, but do not count toward project completion.")
        elif project_mode == "Focus-based":
            st.caption("Focus blocks are the progress-tracked milestones for this project. They can span several days and sync to Google Calendar as all-day events.")
        else:
            st.caption("Project steps are one-off pieces of work. Each project step counts toward project progress automatically.")

        st.markdown("#### 1. What is this?")
        if is_routine_activity:
            title_placeholder = "For example, Sleep"
        elif project_mode == "Focus-based" and is_supporting_time_block:
            title_placeholder = "For example, Monday practice for Tune 1"
        elif project_mode == "Focus-based":
            title_placeholder = "For example, Learn Tune 1"
        else:
            title_placeholder = "For example, Choose a sketching guide"
        title = st.text_input(title_word, value=str(action.get("title", "")), placeholder=title_placeholder)
        description = st.text_area("Notes / description", value=str(action.get("description", action.get("notes", "")) or ""), height=80, placeholder="Optional context or notes.")

        c1, c2 = st.columns([0.5, 0.5])
        status_options = ["Next", "Scheduled", "Planned", "Waiting", "Done"] if not is_routine_activity else ["Included", "Paused", "Done"]
        current_status = str(action.get("status", status_options[0]) or status_options[0])
        status = c1.selectbox("Status", status_options, index=status_options.index(current_status) if current_status in status_options else 0)
        priority_options = ["High", "Medium", "Low"]
        current_priority = str(action.get("priority", "Medium") or "Medium")
        priority = c2.selectbox("Priority", priority_options, index=priority_options.index(current_priority) if current_priority in priority_options else 1)

        item_type = "routine_activity" if is_routine_activity else "project_progress"
        contributes_to_progress = "1"
        parent_progress_item_id = str(action.get("parent_progress_item_id", "") or "")
        if not is_routine_activity:
            st.markdown("#### Project tracking")
            if project_mode == "Focus-based" and is_supporting_time_block:
                item_type = "supporting_time"
                contributes_to_progress = "0"
                all_actions = active_online_df(read_online_table(sheet_id, "actions"))
                parent_options = []
                if not all_actions.empty and goal_id:
                    project_actions = all_actions[all_actions.get("goal_id", pd.Series(dtype=str)).fillna("").astype(str) == str(goal_id)]
                    for _, pa in project_actions.iterrows():
                        pa_id = str(pa.get("action_id", "") or "").strip()
                        if pa_id and pa_id != record_id and project_action_counts_toward_progress(pa):
                            parent_options.append((pa_id, str(pa.get("title", "") or "Focus block")))
                labels = ["No parent focus block"] + [label for _pid, label in parent_options]
                current_label = "No parent focus block"
                for pid, label in parent_options:
                    if pid == parent_progress_item_id:
                        current_label = label
                chosen_parent = st.selectbox("Which focus block does this support?", labels, index=labels.index(current_label) if current_label in labels else 0)
                parent_progress_item_id = next((pid for pid, label in parent_options if label == chosen_parent), "") if chosen_parent != "No parent focus block" else ""
                st.caption("Supporting time blocks create calendar/task time, but never change the project completion percentage.")
            elif project_mode == "Focus-based":
                item_type = "project_focus"
                contributes_to_progress = "1"
                parent_progress_item_id = ""
                st.caption("This focus block counts toward project progress when its Google Task is completed. Pathmark will sync it as an all-day calendar item spanning the dates you choose.")
            else:
                item_type = "project_progress"
                contributes_to_progress = "1"
                parent_progress_item_id = ""
                st.caption("This project step counts toward project progress when its Google Task is completed.")

        st.markdown("#### 2. Make time in your calendar")
        if is_focus_block:
            st.markdown("<div class='pathmark-note'>Focus blocks span one or more days and sync to Google Calendar as all-day events. They count toward project progress.</div>", unsafe_allow_html=True)
            c3, c4 = st.columns(2)
            scheduled = c3.text_input("Focus starts", value=nz_date_text(default_start_date), placeholder="DD/MM/YYYY")
            end_date = c4.text_input("Focus finishes", value=nz_date_text(default_end_date), placeholder="DD/MM/YYYY")
            start_time = ""
            end_time = ""
            location = st.text_input("Calendar location", value=str(action.get("calendar_location", "") or ""), placeholder="Optional")
            helper_rows_input: list[dict[str, str]] = []
            st.caption("Small action helpers belong on supporting time blocks, not on the focus block itself.")
        else:
            st.markdown("<div class='pathmark-note'>Calendar time, the weekly tasklist row and the Google Tasks checklist item are created automatically for every saved project step, supporting time block, or routine activity.</div>", unsafe_allow_html=True)
            c3, c4 = st.columns(2)
            scheduled = c3.text_input("Start date", value=nz_date_text(default_start_date), placeholder="DD/MM/YYYY")
            start_time = c4.text_input("Start time", value=default_start_time, placeholder="HH:MM, for example 09:00")
            c5, c6 = st.columns(2)
            end_date = c5.text_input("Finish date", value=nz_date_text(default_end_date), placeholder="DD/MM/YYYY")
            end_time = c6.text_input("Finish time", value=default_end_time, placeholder="HH:MM, for example 10:00")
            location = st.text_input("Calendar location", value=str(action.get("calendar_location", "") or ""), placeholder="Optional")

            st.markdown("#### 3. Optional small action checklist items")
            with st.popover("ⓘ Why add small actions?"):
                st.write("Pathmark already creates a Google Tasks checklist item for the step or activity itself. Extra small actions reduce activation energy, can each have their own date, and remain linked to this parent step or activity for future editing/export.")
            helper_state_rows = helper_rows_state_for_form(form_id, existing_helpers, helper_editor_default_due)
            helper_count_default = max(1, min(6, len(helper_state_rows)))
            helper_count = st.selectbox("How many extra small checklist items?", [0, 1, 2, 3, 4, 5, 6], index=[0, 1, 2, 3, 4, 5, 6].index(helper_count_default if helper_state_rows and any((r.get("title") or "").strip() for r in helper_state_rows) else 0), help="Optional. Pathmark will still create the main Google Tasks checklist item automatically.")
            while len(helper_state_rows) < helper_count:
                helper_state_rows.append({"title": "", "due": nz_date_text(helper_editor_default_due)})
            helper_rows_input: list[dict[str, str]] = []
            for idx in range(helper_count):
                row = helper_state_rows[idx] if idx < len(helper_state_rows) else {"title": "", "due": nz_date_text(helper_editor_default_due)}
                st.markdown(f"<div class='helper-row-card'><p>Small action {idx + 1}</p></div>", unsafe_allow_html=True)
                hc1, hc2 = st.columns([0.68, 0.32])
                title_val = hc1.text_input("Checklist item", value=str(row.get("title", "")), placeholder="For example, put phone outside the bedroom", key=f"{form_id}_helper_title_{idx}")
                due_val = hc2.text_input("Appears on", value=str(row.get("due", nz_date_text(helper_editor_default_due))), placeholder="DD/MM/YYYY", key=f"{form_id}_helper_due_{idx}")
                helper_rows_input.append({"title": title_val, "due": due_val})
            st.caption("Helper items export as separate Google Tasks rows and include the parent step/activity ID in the notes.")

        activity_days = ""
        if is_routine_activity:
            frequency = str(routine.get("frequency", "") or "Weekly")
            preferred = str(routine.get("preferred_days", "") or "")
            if frequency.lower() == "weekdays":
                inherited = "Monday, Tuesday, Wednesday, Thursday, Friday"
            elif frequency.lower() == "daily":
                inherited = "Daily"
            else:
                inherited = preferred or frequency
            activity_days = preferred
            st.caption(f"This activity inherits the routine repeat pattern: {inherited or 'set in the routine Repeat tab'}. Edit the routine's Repeat tab to change the pattern for its activities.")

        submitted = st.form_submit_button("Save changes" if record_id else f"Save {title_word.lower()}", use_container_width=True)
        if submitted:
            if is_focus_block:
                problems = []
                start_d = parse_online_date(normalise_online_date(scheduled) if scheduled else scheduled)
                end_d = parse_online_date(normalise_online_date(end_date) if end_date else end_date)
                if start_d is None:
                    problems.append("Add a valid start date for the focus block.")
                if end_d is None:
                    problems.append("Add a valid finish date for the focus block.")
                if start_d is not None and end_d is not None and end_d < start_d:
                    problems.append("The focus block finish date must be on or after the start date.")
            else:
                problems = _calendar_finish_validation(start_date=scheduled, start_time=start_time, end_date=end_date, end_time=end_time)
            if not title.strip():
                st.error(f"Add a {title_word.lower()} title before saving.")
            elif problems:
                for problem in problems:
                    st.error(problem)
            else:
                helper_rows_clean, helper_row_problems = clean_helper_prompt_rows(helper_rows_input, scheduled)
                if helper_row_problems:
                    for problem in helper_row_problems:
                        st.error(problem)
                    return
                start_date_norm = normalise_online_date(scheduled)
                end_date_norm = normalise_online_date(end_date)
                minutes = _minutes_between_calendar_bounds(scheduled, start_time, end_date, end_time)
                payload = {
                    "goal_id": goal_id or str(action.get("goal_id", "") or ""),
                    "routine_id": routine_id or str(action.get("routine_id", "") or ""),
                    "area_id": area_id or str(action.get("area_id", "") or ""),
                    "area_name": default_area or str(action.get("area_name", "") or ""),
                    "title": title.strip(),
                    "description": description.strip(),
                    "item_type": item_type,
                    "contributes_to_progress": contributes_to_progress,
                    "parent_progress_item_id": parent_progress_item_id,
                    "status": status,
                    "priority": priority,
                    "due_date": start_date_norm,
                    "scheduled_date": start_date_norm,
                    "activity_days": activity_days.strip(),
                    "estimated_minutes": minutes,
                    "calendar_block": "1",
                    "reminder": "1",
                    "include_tasklist": "1",
                    "first_step": title.strip(),
                    "task_reminder_time": "",
                    "calendar_start_time": start_time.strip(),
                    "calendar_end_time": end_time.strip(),
                    "calendar_end_date": end_date_norm,
                    "calendar_location": location.strip(),
                    "notes": description.strip(),
                }
                saved_action_id = record_id
                if record_id:
                    ok, message = update_online_record(sheet_id, "actions", record_id, payload)
                else:
                    payload["action_id"] = f"action-{uuid.uuid4().hex}"
                    saved_action_id = payload["action_id"]
                    ok, message = append_online_record(sheet_id, "actions", payload)
                if ok:
                    replace_helper_prompts_for_action(
                        sheet_id,
                        action_id=saved_action_id,
                        action_title=title.strip(),
                        area_name=default_area or str(action.get("area_name", "") or ""),
                        linked_record_type="routine_activity" if is_routine_activity else "project_step",
                        linked_parent_id=routine_id or goal_id,
                        linked_parent_type="routine" if is_routine_activity else "project",
                        helper_rows=helper_rows_clean,
                        helper_due=scheduled,
                    )
                    st.success(message)
                    reset_helper_rows_state(form_id)
                else:
                    st.warning(safe_user_message(message))
                if ok:
                    st.rerun()


def render_focus_based_project_work(sheet_id: str, linked: pd.DataFrame, *, goal_id: str, default_area: str = "") -> None:
    """Render focus blocks as parent containers with supporting time nested underneath."""
    if linked is None or linked.empty:
        st.info("No focus blocks yet. Add one below when you are ready.")
        return

    progress_rows = linked[linked.apply(project_action_counts_toward_progress, axis=1)].copy()
    support_rows = linked[linked.apply(lambda r: not project_action_counts_toward_progress(r), axis=1)].copy()
    blocks = staged_calendar_blocks(sheet_id)

    if progress_rows.empty:
        st.info("No focus blocks yet. Add one below when you are ready.")
    else:
        st.markdown("#### Focus blocks")

    for _, focus_row in progress_rows.iterrows():
        focus_id = str(focus_row.get("action_id", "") or "").strip()
        title = str(focus_row.get("title", "") or "Untitled focus block")
        supports = project_supporting_actions_for_parent(support_rows, focus_id)
        support_label = "Supporting time blocks" if len(supports.index) != 1 else "Supporting time block"

        # Use Streamlit containers rather than one large nested HTML string.
        # This avoids raw HTML appearing when Streamlit re-renders complex nested cards.
        with st.container(border=True):
            st.markdown(
                _project_work_card_html(sheet_id, focus_row, linked, blocks=blocks, card_class="focus-block-card"),
                unsafe_allow_html=True,
            )
            st.markdown(f"<div class='support-block-group-label'>{html.escape(support_label)}</div>", unsafe_allow_html=True)
            if supports.empty:
                st.markdown("<div class='support-block-empty'>No supporting time blocks have been added under this focus block yet.</div>", unsafe_allow_html=True)
            else:
                left, right = st.columns([0.06, 0.94])
                with left:
                    st.markdown("<div class='support-nesting-rail'></div>", unsafe_allow_html=True)
                with right:
                    for _, support_row in supports.iterrows():
                        st.markdown(
                            _project_work_card_html(sheet_id, support_row, linked, blocks=blocks, card_class="support-card"),
                            unsafe_allow_html=True,
                        )

        with st.expander(f"Edit focus block · {title}", expanded=False):
            _action_form(
                sheet_id,
                goal_id=goal_id,
                default_area=default_area,
                form_key=f"edit_focus_{focus_id or uuid.uuid4().hex}",
                action={k: focus_row.get(k, "") for k in linked.columns},
            )
        with st.expander(f"Add supporting time block for {title}", expanded=False):
            st.caption("This sits under the focus block, syncs to Google Calendar and Google Tasks, and stays out of the project completion percentage.")
            _action_form(
                sheet_id,
                goal_id=goal_id,
                default_area=default_area,
                form_key=f"goal_{goal_id}_support_{focus_id}",
                action={"item_type": "supporting_time", "contributes_to_progress": "0", "parent_progress_item_id": focus_id},
            )
        for _, support_row in supports.iterrows():
            support_id = str(support_row.get("action_id", "") or "").strip()
            support_title = str(support_row.get("title", "") or "Supporting time block")
            with st.expander(f"Edit supporting time block · {support_title}", expanded=False):
                _action_form(
                    sheet_id,
                    goal_id=goal_id,
                    default_area=default_area,
                    form_key=f"edit_support_{support_id or uuid.uuid4().hex}",
                    action={k: support_row.get(k, "") for k in linked.columns},
                )

    unassigned = support_rows.copy()
    if not unassigned.empty and "parent_progress_item_id" in unassigned.columns:
        unassigned = unassigned[unassigned["parent_progress_item_id"].fillna("").astype(str).str.strip() == ""].copy()
    if not unassigned.empty:
        with st.expander("Supporting time blocks without a focus block", expanded=False):
            st.caption("Edit these and choose the focus block they support so Pathmark can nest them clearly.")
            _render_action_list(sheet_id, unassigned, goal_id=goal_id, default_area=default_area)


def render_goal_manager(sheet_id: str) -> None:
    st.subheader("Projects")
    st.markdown("""
    <div class='guide-box'><strong>Projects have a definition of done.</strong><br>
    Define what finished means, then add one-off project steps. Pathmark automatically makes time for each step in Google Calendar, keeps it available for the weekly tasklist, and creates a date-based Google Tasks checklist item.</div>
    """, unsafe_allow_html=True)
    goals = active_online_df(read_online_table(sheet_id, "goals"))
    actions = active_online_df(read_online_table(sheet_id, "actions"))
    areas = area_options(sheet_id)
    col_list, col_main = st.columns([0.34, 0.66])
    with col_list:
        st.markdown("### Projects")
        with st.expander("Add project", expanded=goals.empty):
            with st.form("online_add_goal", clear_on_submit=True):
                area = st.selectbox("Area", options=[""] + areas, format_func=lambda x: x or "Choose an Area") if areas else st.text_input("Area")
                title = st.text_input("Title")
                specific = st.text_input("Specific area", placeholder="Optional sub-area or project folder")
                planning_mode = st.selectbox("Planning style", ["Task-based", "Focus-based"], index=0, help="Task-based uses discrete completion steps. Focus-based uses larger focus blocks with optional supporting time blocks.")
                status = st.selectbox("Status", ["Captured", "Active", "On hold", "Closed", "Abandoned"], index=1)
                target_date = st.text_input("Target date", placeholder="Optional, DD/MM/YYYY")
                purpose = st.text_area("Why this matters", height=75)
                desired = st.text_area("Specific outcome", height=75, placeholder="What will be different when this is done?")
                closure = st.text_area("Measure of success / definition of done", height=75)
                notes = st.text_area("Notes", height=80)
                submitted = st.form_submit_button("Save project", use_container_width=True)
                if submitted:
                    if not title.strip():
                        st.error("Add a title before saving.")
                    elif not str(area).strip():
                        st.error("Choose or create an Area before saving this goal.")
                    elif not valid_online_date(target_date):
                        st.error("Target date must be blank or a real date. Use DD/MM/YYYY, for example 30/06/2026.")
                    else:
                        ok, message = append_online_record(sheet_id, "goals", {
                            "goal_id": f"goal-{uuid.uuid4().hex}", "area_id": find_area_id(sheet_id, str(area)), "area_name": str(area).strip(),
                            "title": title.strip(), "description": desired.strip() or purpose.strip(), "specific_area": specific.strip(), "planning_mode": planning_mode, "status": status,
                            "target_date": normalise_online_date(target_date) if target_date.strip() else "", "purpose": purpose.strip(), "desired_outcome": desired.strip(), "closure_criteria": closure.strip(), "notes": notes.strip(),
                        })
                        if ok:
                            st.success(message)
                        else:
                            st.warning(safe_user_message(message))
                        if ok:
                            st.rerun()
        if goals.empty:
            st.info("No projects yet.")
            selected_id = ""
        else:
            labels = {f"{row.get('title','Untitled')} ({row.get('status','')}) — {project_due_sort_label(row)}": str(row.get("goal_id", "")) for _, row in goals.iterrows()}
            selected_label = st.radio("Select a project", list(labels.keys()), label_visibility="collapsed", key="online_goal_select")
            selected_id = labels.get(selected_label, "")
            render_project_visibility_cards(goals, selected_id)
    with col_main:
        if selected_id:
            g = goals[goals["goal_id"] == selected_id].iloc[0].to_dict()
            st.markdown(f"### {g.get('title','Project')}")
            st.markdown(project_due_summary_html(g), unsafe_allow_html=True)
            project_items = project_task_items(sheet_id, selected_id)
            project_done, project_total = completion_counts(project_items)
            if project_total:
                render_completion_summary(project_done, project_total, f"{project_done} of {project_total} project progress items complete")
            else:
                st.caption("No Google Tasks checklist items are linked to this project yet.")
            planning_mode_for_tabs = str(g.get("planning_mode", "Task-based") or "Task-based")
            steps_tab_label = "Focus blocks & supporting time" if planning_mode_for_tabs == "Focus-based" else "Project steps"
            tabs = st.tabs(["Project details", steps_tab_label, "Manage"])
            with tabs[0]:
                with st.form(f"online_edit_goal_{selected_id}"):
                    area = st.selectbox("Area", options=[""] + areas, index=([""] + areas).index(str(g.get("area_name", ""))) if str(g.get("area_name", "")) in areas else 0) if areas else st.text_input("Area", value=str(g.get("area_name", "")))
                    title = st.text_input("Title", value=str(g.get("title", "")))
                    specific = st.text_input("Specific area", value=str(g.get("specific_area", "")))
                    planning_options = ["Task-based", "Focus-based"]
                    cur_planning = str(g.get("planning_mode", "Task-based") or "Task-based")
                    has_focus_blocks = project_has_focus_blocks(actions, selected_id)
                    if has_focus_blocks and cur_planning == "Focus-based":
                        planning_options = ["Focus-based"]
                        st.caption("This project already has focus blocks. Remove those focus blocks before switching it back to task-based planning.")
                    planning_mode = st.selectbox("Planning style", planning_options, index=planning_options.index(cur_planning) if cur_planning in planning_options else 0, help="Task-based uses discrete steps. Focus-based uses larger focus blocks with supporting time blocks.")
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
                            st.error("Add a project title before saving.")
                        elif not valid_online_date(target_date):
                            st.error("Target date must be blank or a real date. Use DD/MM/YYYY, for example 30/06/2026.")
                        else:
                            ok, message = update_online_record(sheet_id, "goals", selected_id, {"area_id": find_area_id(sheet_id, str(area)), "area_name": str(area).strip(), "title": title.strip(), "description": desired.strip() or purpose.strip(), "specific_area": specific.strip(), "planning_mode": planning_mode, "status": status, "target_date": normalise_online_date(target_date) if target_date.strip() else "", "purpose": purpose.strip(), "desired_outcome": desired.strip(), "closure_criteria": closure.strip(), "notes": notes.strip()})
                            if ok:
                                st.success(message)
                            else:
                                st.warning(safe_user_message(message))
                            if ok:
                                st.rerun()
            with tabs[1]:
                linked = actions[actions["goal_id"].fillna("") == selected_id] if not actions.empty else pd.DataFrame(columns=ONLINE_TABLES["actions"])
                planning_mode = str(g.get("planning_mode", "Task-based") or "Task-based")
                default_area_for_project = str(g.get("area_name", "") or "")
                if planning_mode == "Focus-based":
                    st.caption("This project is focus-based. Focus blocks count toward completion. Supporting time blocks sit under the focus block they support, sync to Calendar and Google Tasks, and do not change project progress.")
                    render_focus_based_project_work(sheet_id, linked, goal_id=selected_id, default_area=default_area_for_project)
                else:
                    _render_action_list(sheet_id, linked, goal_id=selected_id, default_area=default_area_for_project)
                    st.caption("Project steps are one-off steps toward this project. Calendar time, tasklist rows and Google Tasks checklist items are created automatically.")
                with st.expander("Add focus block" if planning_mode == "Focus-based" else "Add project step", expanded=linked.empty):
                    _action_form(sheet_id, goal_id=selected_id, default_area=default_area_for_project, form_key=f"goal_{selected_id}_progress")
            with tabs[2]:
                st.markdown("""
                **Active** projects appear in the workspace and count toward progress.  
                **On hold** projects remain here but are not treated as current work.  
                **Archived** projects are for completed or retired work you no longer want in the Projects tab.
                """)
                c1, c2, c3 = st.columns(3)
                if c1.button("Set as active", key=f"active_goal_{selected_id}", use_container_width=True):
                    ok, message = update_online_record(sheet_id, "goals", selected_id, {"status": "Active"})
                    if ok:
                        st.success("Project set as active.")
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
                if c2.button("Pause project", key=f"pause_goal_{selected_id}", use_container_width=True):
                    ok, message = update_online_record(sheet_id, "goals", selected_id, {"status": "On hold"})
                    if ok:
                        st.success("Project paused. It remains here so you can restart it later.")
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
                if c3.button("Archive completed project", key=f"archive_goal_{selected_id}", use_container_width=True):
                    ok, message = archive_online_record(sheet_id, "goals", selected_id, "Completed or retired project archived from Pathmark Online.")
                    if ok:
                        st.success("Project archived. You can restore it from Archive.")
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()


def _routine_repeat_inputs(prefix: str, current_frequency: str = "Weekly", current_preferred_days: str = "", current_next_due: str = "") -> tuple[str, str, str]:
    freq = current_frequency if current_frequency in VALID_FREQUENCIES else "Weekly"
    frequency = st.selectbox("Repeat pattern for activities", VALID_FREQUENCIES, index=VALID_FREQUENCIES.index(freq), key=f"{prefix}_frequency")
    preferred_days = ""
    current_days, _bad_days = parse_days_text(str(current_preferred_days or ""))
    if frequency == "Weekdays":
        preferred_days = "Monday, Tuesday, Wednesday, Thursday, Friday"
        st.markdown("<div class='repeat-summary'>Repeats on weekdays: Monday to Friday.</div>", unsafe_allow_html=True)
    elif frequency == "Daily":
        preferred_days = ""
        st.markdown("<div class='repeat-summary'>Repeats every day.</div>", unsafe_allow_html=True)
    elif frequency == "Weekly":
        selected = st.multiselect("Repeat on these days", VALID_DAYS, default=current_days, key=f"{prefix}_weekly_days", help="These days will become the Google-compatible weekly recurrence for every activity in this routine.")
        preferred_days = ", ".join(selected)
    elif frequency == "Monthly":
        current_pattern = str(current_preferred_days or "Same day of month as start date").strip()
        if current_pattern not in MONTHLY_REPEAT_PATTERNS:
            current_pattern = "Same day of month as start date"
        preferred_days = st.selectbox("Repeat monthly", MONTHLY_REPEAT_PATTERNS, index=MONTHLY_REPEAT_PATTERNS.index(current_pattern), key=f"{prefix}_monthly_pattern", help="Google Calendar imports support patterns such as the first Monday or last Friday of each month.")
    else:
        preferred_days = st.text_input("Custom repeat description", value=str(current_preferred_days or ""), key=f"{prefix}_custom_repeat", help="Used for notes only unless it can be converted to a standard export rule.")
    next_due = st.text_input("Repeat starts", value=nz_date_text(current_next_due), placeholder="DD/MM/YYYY", key=f"{prefix}_next_due")
    return frequency, preferred_days, next_due


def render_routine_manager(sheet_id: str) -> None:
    st.subheader("Routines")
    st.markdown("""
    <div class='guide-box'><strong>Routines are the habits that keep you steady.</strong><br>
    A routine sets the repeat pattern. Each activity inside it sets its own start and finish time, then inherits the routine repeat pattern for calendar export.</div>
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
                frequency, preferred_days, next_due = _routine_repeat_inputs("add_routine", "Weekly", "", "")
                purpose = st.text_area("Why this matters", height=75)
                checklist = ""
                st.caption("After saving the routine container, add one or more routine activities. Activities drive calendar blocks, tasklist rows and Google Tasks checklist items.")
                status = st.selectbox("Status", ["Active", "Paused", "Archived"], index=0)
                notes = st.text_area("Notes", height=80)
                submitted = st.form_submit_button("Save routine", use_container_width=True)
                if submitted:
                    if not title.strip():
                        st.error("Add a routine title before saving.")
                    elif not str(area).strip():
                        st.error("Choose or create an Area before saving this routine.")
                    elif not valid_online_date(next_due):
                        st.error("Repeat starts must be blank or a real date. Use DD/MM/YYYY, for example 08/06/2026.")
                    elif validate_routine_schedule(frequency, preferred_days):
                        for problem in validate_routine_schedule(frequency, preferred_days):
                            st.error(problem)
                    else:
                        ok, message = append_online_record(sheet_id, "routines", {"routine_id": f"routine-{uuid.uuid4().hex}", "area_id": find_area_id(sheet_id, str(area)), "area_name": str(area).strip(), "title": title.strip(), "description": purpose.strip() or notes.strip(), "frequency": frequency.strip() or "Weekly", "preferred_days": preferred_days.strip(), "duration_minutes": "", "calendar_start_time": "", "calendar_end_time": "", "status": status, "purpose": purpose.strip(), "next_due": normalise_online_date(next_due) if next_due.strip() else "", "checklist": checklist.strip(), "notes": notes.strip()})
                        if ok:
                            st.success(message)
                        else:
                            st.warning(safe_user_message(message))
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
            routine_items_week = routine_task_items(sheet_id, selected_id, current_week_only=True)
            routine_done, routine_total = completion_counts(routine_items_week)
            week_start_dt, week_end_dt, _week_pref = _week_bounds_for_settings(sheet_id)
            if routine_total:
                render_completion_summary(routine_done, routine_total, f"{routine_done} of {routine_total} routine checklist items complete this week")
                st.caption(f"Current week: {week_start_dt.strftime('%d/%m/%Y')} to {week_end_dt.strftime('%d/%m/%Y')}")
            else:
                st.caption("No Google Tasks checklist items are due for this routine this week.")
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
                            if ok:
                                st.success(message)
                            else:
                                st.warning(safe_user_message(message))
                            if ok:
                                st.rerun()
            with tabs[1]:
                linked = actions[actions["routine_id"].fillna("") == selected_id] if not actions.empty else pd.DataFrame(columns=ONLINE_TABLES["actions"])
                _render_action_list(sheet_id, linked, routine_id=selected_id, default_area=str(r.get("area_name", "") or ""))
                with st.expander("Add routine activity", expanded=linked.empty):
                    _action_form(sheet_id, routine_id=selected_id, default_area=str(r.get("area_name", "") or ""), form_key=f"routine_{selected_id}")
            with tabs[2]:
                with st.form(f"online_repeat_{selected_id}"):
                    st.caption("The routine repeat pattern is inherited by each activity. Activity start and finish times are set in the Activities tab, not here.")
                    current_freq = str(r.get("frequency", "") or "Weekly")
                    frequency, preferred_days, next_due = _routine_repeat_inputs(f"edit_routine_{selected_id}", current_freq, str(r.get("preferred_days", "")), str(r.get("next_due", "")))
                    submitted = st.form_submit_button("Save repeat settings", use_container_width=True)
                    if submitted:
                        problems = []
                        if not valid_online_date(next_due):
                            problems.append("Repeat starts must be blank or a real date. Use DD/MM/YYYY, for example 08/06/2026.")
                        problems.extend(validate_routine_schedule(frequency, preferred_days))
                        if problems:
                            for problem in problems:
                                st.error(problem)
                        else:
                            ok, message = update_online_record(sheet_id, "routines", selected_id, {"frequency": frequency.strip(), "preferred_days": preferred_days.strip(), "next_due": normalise_online_date(next_due) if next_due.strip() else ""})
                            if ok:
                                st.success(message)
                            else:
                                st.warning(safe_user_message(message))
                            if ok:
                                st.rerun()
            with tabs[3]:
                st.markdown("""
                **Active** routines appear in the workspace and can feed exports.  
                **Paused** routines stay visible here but are not intended for current tasklist or export use.  
                **Archived** routines are for completed or retired routines you no longer want in the Routines tab. They can be restored later.
                """)
                c1, c2, c3 = st.columns(3)
                if c1.button("Set as active", key=f"active_r_{selected_id}"):
                    ok, message = update_online_record(sheet_id, "routines", selected_id, {"status": "Active"})
                    if ok:
                        st.success(message)
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
                if c2.button("Pause routine", key=f"pause_r_{selected_id}"):
                    ok, message = update_online_record(sheet_id, "routines", selected_id, {"status": "Paused"})
                    if ok:
                        st.success("Routine paused. It remains here so you can restart it later.")
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()
                if c3.button("Archive completed routine", key=f"archive_r_{selected_id}"):
                    ok, message = archive_online_record(sheet_id, "routines", selected_id, "Completed or retired routine archived from Pathmark Online.")
                    if ok:
                        st.success("Routine archived. You can restore it from Archive.")
                    else:
                        st.warning(safe_user_message(message))
                    if ok:
                        st.rerun()


def render_review_queue_manager(sheet_id: str) -> None:
    st.subheader("Review Queue")
    st.write("Review Queue checks whether the parts of your workspace are ready to work together before you export tasklists, calendar blocks or Google Tasks checklist items.")
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
            issues.append({"priority": "Medium", "kind": "Routine", "item": r.get("title", "Untitled"), "issue": "This routine does not have an activity yet.", "next": "Add at least one routine activity so Pathmark can place it on a tasklist, calendar export or Google Tasks checklist item."})
    for _, g in goals.iterrows():
        gid = str(g.get("goal_id", "") or "")
        linked = actions[actions["goal_id"].fillna("") == gid] if not actions.empty and "goal_id" in actions.columns else pd.DataFrame()
        if not str(g.get("closure_criteria", "") or g.get("desired_outcome", "") or "").strip():
            issues.append({"priority": "Medium", "kind": "Goal", "item": g.get("title", "Untitled"), "issue": "This goal does not yet say what done looks like.", "next": "Add a measure of success or definition of done."})
        if linked.empty:
            issues.append({"priority": "Medium", "kind": "Goal", "item": g.get("title", "Untitled"), "issue": "This goal does not have a next activity yet.", "next": "Add one or two concrete project steps rather than a full project plan."})
    for _, a in actions.iterrows():
        title = a.get("title", "Untitled")
        if truthy_flag(a.get("calendar_block", "0")) and not str(a.get("scheduled_date", "") or "").strip():
            issues.append({"priority": "High", "kind": "Calendar", "item": title, "issue": "This activity needs calendar time but does not have a start date yet.", "next": "Open the project step or routine activity and add a start date, start time, finish date and finish time."})
        if truthy_flag(a.get("reminder", "0")) and not str(a.get("first_step", "") or "").strip():
            issues.append({"priority": "Medium", "kind": "Google Tasks", "item": title, "issue": "This activity is marked for Google Tasks but does not have a checklist title.", "next": "Add a tiny first step such as 'put on running shoes' or untick the Google Tasks checklist item option."})

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


def money_value(value: Any) -> float:
    """Parse a money-like value without showing low-level conversion errors."""
    try:
        text = str(value or "").replace("$", "").replace(",", "").strip()
        return float(text) if text else 0.0
    except Exception:
        return 0.0


def money_text(value: Any) -> str:
    amount = money_value(value)
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def annualise_amount(amount: float, frequency: str) -> float:
    freq = str(frequency or "").strip().lower()
    if freq == "weekly":
        return amount * 52
    if freq == "fortnightly":
        return amount * 26
    if freq == "monthly":
        return amount * 12
    if freq == "quarterly":
        return amount * 4
    if freq == "yearly":
        return amount
    return 0.0


def annual_from_row(row: pd.Series) -> float:
    explicit = money_value(row.get("annual_amount", ""))
    if explicit:
        return explicit
    return (
        money_value(row.get("weekly_amount", "")) * 52
        + money_value(row.get("fortnightly_amount", "")) * 26
        + money_value(row.get("monthly_amount", "")) * 12
        + money_value(row.get("quarterly_amount", "")) * 4
        + money_value(row.get("yearly_amount", ""))
    )


def amount_columns_for_frequency(amount: float, frequency: str, include_quarterly: bool = False) -> dict[str, str]:
    values = {
        "weekly_amount": "0",
        "fortnightly_amount": "0",
        "monthly_amount": "0",
        "yearly_amount": "0",
    }
    if include_quarterly:
        values["quarterly_amount"] = "0"
    key_map = {
        "Weekly": "weekly_amount",
        "Fortnightly": "fortnightly_amount",
        "Monthly": "monthly_amount",
        "Quarterly": "quarterly_amount",
        "Yearly": "yearly_amount",
    }
    key = key_map.get(str(frequency or ""), "weekly_amount")
    if key in values:
        values[key] = str(amount)
    values["annual_amount"] = str(annualise_amount(amount, frequency))
    return values


def render_money_metric(label: str, value: float, help_text: str = "") -> None:
    st.metric(label, money_text(value), help=help_text or None)


SPENDING_BUCKET_ORDER = ["Everyday spend", "Fixed cost", "Sinking fund"]
SPENDING_BUCKET_LABELS = {
    "Everyday spend": "Weekly spend money",
    "Fixed cost": "Regular bills and commitments",
    "Sinking fund": "Planned irregular costs",
}
SPENDING_BUCKET_EXPLANATIONS = {
    "Everyday spend": "Transfer this to the card/account you actually use during the week.",
    "Fixed cost": "Leave this in the hub account so bills and direct debits can come out automatically.",
    "Sinking fund": "Set this aside for predictable irregular costs, such as birthdays, Christmas, clothes, holidays and travel.",
}
SPENDING_FREQUENCIES = ["Weekly", "Fortnightly", "Monthly", "Quarterly", "Yearly"]

SPENDING_INCOME_STARTERS = [
    "After-tax employment income",
    "Other income",
    "Government benefits",
    "Child support",
    "Investment property income",
    "Other investment income",
]

SPENDING_ACCOUNT_ROLES = [
    ("Hub account", "All income lands here. Fixed bills and direct debits come from here."),
    ("Everyday card account", "Only weekly spend money moves here for groceries, fuel, cafes, eating out and day-to-day card spending."),
    ("Emergency savings", "Money for genuine unexpected costs. Rebuild this before increasing optional savings."),
    ("Planned irregular costs", "Money set aside for gifts, Christmas, clothes, holidays, annual fees and other predictable but less frequent costs."),
    ("Debt reduction or savings goals", "The real leftover after planned spending. Use this for debt first, then emergency savings, then longer-term goals."),
]


def normalise_spending_kind(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "everyday" in text or "weekly" in text or "blow" in text or "spend money" in text:
        return "Everyday spend"
    if "sinking" in text or "irregular" in text or "gift" in text or "holiday" in text or "travel" in text or "christmas" in text:
        return "Sinking fund"
    return "Fixed cost"


def spending_bucket_label(value: Any) -> str:
    return SPENDING_BUCKET_LABELS.get(normalise_spending_kind(value), "Regular bills and commitments")


def amount_and_frequency_from_row(row: pd.Series) -> tuple[float, str]:
    checks = [
        ("weekly_amount", "Weekly"),
        ("fortnightly_amount", "Fortnightly"),
        ("monthly_amount", "Monthly"),
        ("quarterly_amount", "Quarterly"),
        ("yearly_amount", "Yearly"),
    ]
    for column, frequency in checks:
        amount = money_value(row.get(column, ""))
        if amount:
            return amount, frequency
    annual = money_value(row.get("annual_amount", ""))
    if annual:
        return annual, "Yearly"
    return 0.0, "Weekly"


def spending_sections_for_kind(kind: str) -> list[str]:
    sections: list[str] = []
    for starter_kind, group, _item in SPENDING_STARTER_EXPENSES:
        if normalise_spending_kind(starter_kind) == normalise_spending_kind(kind) and group not in sections:
            sections.append(group)
    return sections or [SPENDING_BUCKET_LABELS.get(normalise_spending_kind(kind), kind)]


def spending_flow_destination_for_kind(kind: str) -> str:
    normalised = normalise_spending_kind(kind)
    if normalised == "Everyday spend":
        return "Account 2 — Everyday card account"
    if normalised == "Sinking fund":
        return "Account 4 — Gifts, holidays, clothes and Christmas"
    return "Account 1 — Hub account"


def render_spending_success(message: str) -> None:
    """Avoid bare Streamlit DeltaGenerator expressions being rendered by magic."""
    st.success(message)


def spending_save_and_refresh(message: str) -> None:
    """Show a save notice and rerun so the freshly-written Google Sheet rows are visible.

    Google Sheets writes clear Pathmark's session cache, but the current Streamlit
    run may already have loaded the old DataFrame. A controlled rerun reloads the
    sheet immediately. The Spending Plan uses stateful radio navigation rather than
    plain tabs, so the user stays in the same area after saving.
    """
    st.session_state["spending_notice"] = message
    st.rerun()


def render_spending_flow_guidance(summary: dict[str, float]) -> None:
    """Show the cash-flow logic in a compact, readable format."""
    st.markdown("#### Money-flow instructions")
    st.caption(
        "Pathmark keeps the account roles fixed so the assessment stays clear. "
        "Use your own bank accounts for these roles if you already have them."
    )
    flow_rows = pd.DataFrame(
        [
            {
                "Account role": "Hub account",
                "What it is for": "Income lands here; fixed bills and direct debits stay here.",
                "Suggested weekly amount": money_text(summary.get("fixed_weekly", 0.0)),
            },
            {
                "Account role": "Everyday card account",
                "What it is for": "Groceries, fuel, cafes, eating out and normal weekly card spending.",
                "Suggested weekly amount": money_text(summary.get("everyday_weekly", 0.0)),
            },
            {
                "Account role": "Planned irregular costs",
                "What it is for": "Birthdays, Christmas, clothes, holidays, travel and other known irregular costs.",
                "Suggested weekly amount": money_text(summary.get("sinking_weekly", 0.0)),
            },
            {
                "Account role": "Emergency savings",
                "What it is for": "Unexpected costs. A useful first target is three months of planned outflows.",
                "Suggested weekly amount": "Use surplus after essentials/debt",
            },
            {
                "Account role": "Debt reduction or savings goals",
                "What it is for": "The real leftover after planned spending. Use for debt first, then emergency savings, then goals.",
                "Suggested weekly amount": money_text(summary.get("surplus_weekly", 0.0)),
            },
        ]
    )
    st.dataframe(flow_rows, use_container_width=True, hide_index=True)

def spending_summary(sheet_id: str) -> dict[str, float]:
    income = active_online_df(read_online_table(sheet_id, "spending_income"))
    expenses = active_online_df(read_online_table(sheet_id, "spending_expenses"))
    income_annual = sum(annual_from_row(row) for _, row in income.iterrows()) if not income.empty else 0.0
    expense_annual = sum(annual_from_row(row) for _, row in expenses.iterrows()) if not expenses.empty else 0.0
    everyday_annual = 0.0
    sinking_annual = 0.0
    fixed_annual = 0.0
    if not expenses.empty:
        for _, row in expenses.iterrows():
            annual = annual_from_row(row)
            kind = str(row.get("expense_kind", "") or "").lower()
            normalised_kind = normalise_spending_kind(kind)
            if normalised_kind == "Everyday spend":
                everyday_annual += annual
            elif normalised_kind == "Sinking fund":
                sinking_annual += annual
            else:
                fixed_annual += annual
    surplus = income_annual - expense_annual
    return {
        "income_annual": income_annual,
        "expense_annual": expense_annual,
        "everyday_annual": everyday_annual,
        "fixed_annual": fixed_annual,
        "sinking_annual": sinking_annual,
        "surplus_annual": surplus,
        "income_weekly": income_annual / 52 if income_annual else 0.0,
        "expense_weekly": expense_annual / 52 if expense_annual else 0.0,
        "everyday_weekly": everyday_annual / 52 if everyday_annual else 0.0,
        "fixed_weekly": fixed_annual / 52 if fixed_annual else 0.0,
        "sinking_weekly": sinking_annual / 52 if sinking_annual else 0.0,
        "surplus_weekly": surplus / 52 if surplus else 0.0,
        "emergency_target": expense_annual / 4 if expense_annual else 0.0,
    }


SPENDING_STARTER_EXPENSES = [
    # Account 2: weekly everyday spend money / blow money
    ("Everyday spend", "Weekly spend money", "Food / Groceries"),
    ("Everyday spend", "Weekly spend money", "Hello Fresh / Lite & Easy / meal kits"),
    ("Everyday spend", "Weekly spend money", "Fuel"),
    ("Everyday spend", "Weekly spend money", "Eating out"),
    ("Everyday spend", "Weekly spend money", "Cafes and coffee"),
    ("Everyday spend", "Weekly spend money", "Alcohol"),
    ("Everyday spend", "Weekly spend money", "Cigarettes"),
    ("Everyday spend", "Weekly spend money", "Personal care"),
    ("Everyday spend", "Weekly spend money", "Recreation / hobbies"),
    ("Everyday spend", "Weekly spend money", "Work expenses"),
    ("Everyday spend", "Weekly spend money", "Parking"),
    ("Everyday spend", "Weekly spend money", "Weekly sport not direct debited"),
    ("Everyday spend", "Weekly spend money", "Movies"),
    ("Everyday spend", "Weekly spend money", "Weekly medical"),
    ("Everyday spend", "Weekly spend money", "Other entertainment"),
    ("Everyday spend", "Weekly spend money", "Uber"),
    ("Everyday spend", "Weekly spend money", "Other"),
    # Account 4: annual/irregular planned irregular costs
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Gifts - Birthdays - Family"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Gifts - Birthdays - Friends"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Gifts - Christmas"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Clothes - Work"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Clothes - Casual"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Other clothes"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Holiday season entertainment"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Shoes"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Weekends away"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Planned annual holidays"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Big international trip"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Weddings and engagements"),
    ("Sinking fund", "Gifts, clothes, Christmas and travel", "Other"),
    # Account 1: fixed bills and commitments
    ("Fixed cost", "Accommodation costs", "Mortgage repayments / rent"),
    ("Fixed cost", "Accommodation costs", "Rates"),
    ("Fixed cost", "Accommodation costs", "Water"),
    ("Fixed cost", "Accommodation costs", "Electricity"),
    ("Fixed cost", "Accommodation costs", "Gas"),
    ("Fixed cost", "Accommodation costs", "House and contents insurance"),
    ("Fixed cost", "Accommodation costs", "Strata / body corporate"),
    ("Fixed cost", "Accommodation costs", "Maintenance fees"),
    ("Fixed cost", "Accommodation costs", "Yard"),
    ("Fixed cost", "Accommodation costs", "Pool maintenance"),
    ("Fixed cost", "Accommodation costs", "House cleaner / keeper"),
    ("Fixed cost", "Accommodation costs", "Pest control"),
    ("Fixed cost", "Bills and subscriptions", "Home telephone"),
    ("Fixed cost", "Bills and subscriptions", "Mobile phone"),
    ("Fixed cost", "Bills and subscriptions", "Internet"),
    ("Fixed cost", "Bills and subscriptions", "Foxtel / Sky"),
    ("Fixed cost", "Bills and subscriptions", "Netflix"),
    ("Fixed cost", "Bills and subscriptions", "Stan"),
    ("Fixed cost", "Bills and subscriptions", "Prime Video"),
    ("Fixed cost", "Bills and subscriptions", "iTunes"),
    ("Fixed cost", "Bills and subscriptions", "Spotify"),
    ("Fixed cost", "Bills and subscriptions", "Online dating services"),
    ("Fixed cost", "Bills and subscriptions", "Bank fees"),
    ("Fixed cost", "Bills and subscriptions", "Audible"),
    ("Fixed cost", "Other living costs", "School fees"),
    ("Fixed cost", "Other living costs", "Education costs"),
    ("Fixed cost", "Other living costs", "Child day care"),
    ("Fixed cost", "Other living costs", "Nanny services / babysitting"),
    ("Fixed cost", "Other living costs", "Haircare / beauty"),
    ("Fixed cost", "Loan repayments", "Credit card minimum repayments"),
    ("Fixed cost", "Loan repayments", "Car loan minimum repayments"),
    ("Fixed cost", "Loan repayments", "Personal loan repayments"),
    ("Fixed cost", "Health costs", "Private health insurance"),
    ("Fixed cost", "Health costs", "Doctor"),
    ("Fixed cost", "Health costs", "Medication"),
    ("Fixed cost", "Health costs", "Optometrist"),
    ("Fixed cost", "Health costs", "Dental"),
    ("Fixed cost", "Health costs", "Physiotherapist"),
    ("Fixed cost", "Health costs", "Osteopath"),
    ("Fixed cost", "Health costs", "Chiropractor"),
    ("Fixed cost", "Health costs", "Psychologist"),
    ("Fixed cost", "Health costs", "Nutritionist"),
    ("Fixed cost", "Health costs", "Naturopath"),
    ("Fixed cost", "Health costs", "Massage"),
    ("Fixed cost", "Health costs", "Yoga / Pilates / gym membership"),
    ("Fixed cost", "Health costs", "Trauma insurance"),
    ("Fixed cost", "Vehicle costs", "Car registration"),
    ("Fixed cost", "Vehicle costs", "WoF"),
    ("Fixed cost", "Vehicle costs", "Car insurance"),
    ("Fixed cost", "Vehicle costs", "Roadside assistance"),
    ("Fixed cost", "Vehicle costs", "Tyres"),
    ("Fixed cost", "Vehicle costs", "Car servicing / repairs"),
    ("Fixed cost", "Vehicle costs", "Driver licence"),
    ("Fixed cost", "Boat / motorcycle costs", "Boat licence"),
    ("Fixed cost", "Boat / motorcycle costs", "Boat insurance"),
    ("Fixed cost", "Boat / motorcycle costs", "Motorcycle registration"),
    ("Fixed cost", "Boat / motorcycle costs", "Motorcycle insurance"),
    ("Fixed cost", "Miscellaneous expenses", "Self-employed income tax allocation"),
    ("Fixed cost", "Miscellaneous expenses", "Tax"),
    ("Fixed cost", "Miscellaneous expenses", "PlayStation Plus"),
    ("Fixed cost", "Miscellaneous expenses", "Steam"),
    ("Fixed cost", "Miscellaneous expenses", "Charity"),
    ("Fixed cost", "Miscellaneous expenses", "Pet and vet"),
    ("Fixed cost", "Investment property", "Mortgage repayments"),
    ("Fixed cost", "Investment property", "Strata / body corporate"),
    ("Fixed cost", "Investment property", "Maintenance fees"),
    ("Fixed cost", "Investment property", "Agent fees"),
    ("Fixed cost", "Investment property", "Insurance - building"),
    ("Fixed cost", "Investment property", "Insurance - landlord"),
    ("Fixed cost", "Investment property", "Water"),
    ("Fixed cost", "Investment property", "Rates"),
]


def load_spending_starter_categories(sheet_id: str) -> tuple[bool, str]:
    existing = active_online_df(read_online_table(sheet_id, "spending_expenses"))
    if not existing.empty:
        return False, "Spending categories already exist. Add or edit records below rather than loading another starter set."
    records = []
    for kind, group, item in SPENDING_STARTER_EXPENSES:
        records.append({
            "expense_id": f"expense-{uuid.uuid4().hex[:12]}",
            "expense_kind": kind,
            "group_name": group,
            "item": item,
            "weekly_amount": "0",
            "fortnightly_amount": "0",
            "monthly_amount": "0",
            "quarterly_amount": "0",
            "yearly_amount": "0",
            "annual_amount": "0",
            "notes": "Starter category. Edit the amount, set it to 0, or delete it if it does not fit.",
            "status": "active",
            "source": "Pathmark Spending Plan starter categories",
        })
    return append_many_online_records(sheet_id, {"spending_expenses": records})



def spending_account_role_records(summary: dict[str, float]) -> list[dict[str, Any]]:
    now_note = "Created by Spending Plan setup."
    return [
        {
            "account_id": f"account-{uuid.uuid4().hex[:12]}",
            "account_name": "Account 1 — Hub account",
            "purpose": "All income lands here. Fixed bills and direct debits are paid from here.",
            "transfer_per_week": str(summary.get("fixed_weekly", 0.0)),
            "target_balance": "0",
            "current_balance": "0",
            "notes": f"Keep at least {money_text(summary.get('fixed_weekly', 0.0))} per week available for regular bills and commitments. {now_note}",
            "status": "active",
            "source": "Spending Plan setup",
        },
        {
            "account_id": f"account-{uuid.uuid4().hex[:12]}",
            "account_name": "Account 2 — Everyday card account",
            "purpose": "Weekly spending money for groceries, fuel, cafes, eating out and other day-to-day spending.",
            "transfer_per_week": str(summary.get("everyday_weekly", 0.0)),
            "target_balance": "0",
            "current_balance": "0",
            "notes": f"Set up a weekly automatic payment of {money_text(summary.get('everyday_weekly', 0.0))} from the hub account. {now_note}",
            "status": "active",
            "source": "Spending Plan setup",
        },
        {
            "account_id": f"account-{uuid.uuid4().hex[:12]}",
            "account_name": "Account 3 — Emergency savings",
            "purpose": "Unexpected costs that cannot sensibly be predicted.",
            "transfer_per_week": "0",
            "target_balance": str(summary.get("emergency_target", 0.0)),
            "current_balance": "0",
            "notes": f"Suggested emergency target: {money_text(summary.get('emergency_target', 0.0))}. Build this after minimum debt repayments are covered. {now_note}",
            "status": "active",
            "source": "Spending Plan setup",
        },
        {
            "account_id": f"account-{uuid.uuid4().hex[:12]}",
            "account_name": "Account 4 — Gifts, holidays, clothes and Christmas",
            "purpose": "Predictable irregular costs that should build quietly over time.",
            "transfer_per_week": str(summary.get("sinking_weekly", 0.0)),
            "target_balance": "0",
            "current_balance": "0",
            "notes": f"Set up a weekly automatic payment of {money_text(summary.get('sinking_weekly', 0.0))} from the hub account. {now_note}",
            "status": "active",
            "source": "Spending Plan setup",
        },
        {
            "account_id": f"account-{uuid.uuid4().hex[:12]}",
            "account_name": "Account 5 — Debt reduction or savings goals",
            "purpose": "The money left after planned spending. Use it for extra debt repayment first, then emergency savings, then longer-term goals.",
            "transfer_per_week": str(max(summary.get("surplus_weekly", 0.0), 0.0)),
            "target_balance": "0",
            "current_balance": "0",
            "notes": f"Potential leftover after planned spending: {money_text(summary.get('surplus_weekly', 0.0))} per week. {now_note}",
            "status": "active",
            "source": "Spending Plan setup",
        },
    ]


def load_spending_income_starters(sheet_id: str) -> tuple[bool, str]:
    existing = active_online_df(read_online_table(sheet_id, "spending_income"))
    if not existing.empty:
        return False, "Income sources already exist. Edit the income setup table rather than loading another starter set."
    records = []
    for category in SPENDING_INCOME_STARTERS:
        records.append({
            "income_id": f"income-{uuid.uuid4().hex[:12]}",
            "person": "Me",
            "category": category,
            "weekly_amount": "0",
            "fortnightly_amount": "0",
            "monthly_amount": "0",
            "yearly_amount": "0",
            "annual_amount": "0",
            "notes": "Starter income source. Add an amount if this applies, set it to $0.00, deactivate it, or delete the row if it does not fit.",
            "status": "active",
            "source": "Pathmark Spending Plan income setup",
        })
    return append_many_online_records(sheet_id, {"spending_income": records})


def ensure_spending_plan_default_rows(sheet_id: str) -> None:
    """Ensure the Spending Plan opens with editable starter rows.

    This avoids making users press separate "load common sources" buttons before
    they can set up income, spending, AP roles, or projections. Existing data is
    never overwritten.
    """
    if not sheet_id:
        return
    cache_key = f"spending_defaults_checked::{sheet_id}"
    if st.session_state.get(cache_key):
        return
    st.session_state[cache_key] = True
    try:
        changed = False
        if active_online_df(read_online_table(sheet_id, "spending_income")).empty:
            ok, _msg = load_spending_income_starters(sheet_id)
            changed = changed or ok
        if active_online_df(read_online_table(sheet_id, "spending_expenses")).empty:
            ok, _msg = load_spending_starter_categories(sheet_id)
            changed = changed or ok
        if active_online_df(read_online_table(sheet_id, "spending_accounts")).empty:
            summary = spending_summary(sheet_id)
            ok, _msg = append_many_online_records(sheet_id, {"spending_accounts": spending_account_role_records(summary)})
            changed = changed or ok
        if changed:
            clear_online_cache(sheet_id)
    except Exception:
        # The individual Spending Plan tabs will still show editable controls and
        # user-facing warnings if Google Sheets is temporarily unavailable.
        pass


def render_spending_plan_disclaimer(compact: bool = False) -> None:
    """Display the Spending Plan non-advice notice in a consistent way."""
    if compact:
        st.info(
            "Spending Plan is a budgeting and planning tool only. Its suggested money flows are based only on the amounts you enter; "
            "they are not financial, investment, tax, legal, mortgage, insurance, KiwiSaver or debt advice."
        )
    else:
        st.markdown("""
        <div class="safe-rule"><strong>Spending Plan is a budgeting and planning tool only.</strong><br>
        Pathmark helps you organise income, spending, planned costs and account flows based on the information you enter.
        It does not provide financial, investment, legal, tax, mortgage, insurance, KiwiSaver or debt advice. Pathmark is not a financial adviser and does not assess whether any financial decision is suitable for your personal circumstances. For personalised advice, speak with a licensed financial adviser or an appropriate professional.</div>
        """, unsafe_allow_html=True)


def render_spending_assessment(sheet_id: str) -> None:
    summary = spending_summary(sheet_id)
    st.markdown("""
    <div class="dashboard-hero">
      <h2>Money-flow dashboard</h2>
      <p><strong>Direct income before it disappears.</strong> Spending Plan turns income and outflows into a weekly view, safe-to-spend amount, and suggested APs.</p>
    </div>
    """, unsafe_allow_html=True)

    overcommitted = summary["surplus_weekly"] < -0.005
    shortfall_weekly = abs(summary["surplus_weekly"]) if overcommitted else 0.0
    safe_to_spend_weekly = 0.0 if overcommitted else summary["everyday_weekly"]
    balanced = abs(summary["surplus_weekly"]) <= 0.005
    result_label = "OVERCOMMITTED" if overcommitted else ("BALANCED" if balanced else "AVAILABLE")
    result_title = "Shortfall / week" if overcommitted else ("Money flow balanced" if balanced else "Money available to allocate")
    result_body = (
        "Your planned outflows are higher than your income. Treat safe-to-spend as $0.00 until the plan is adjusted."
        if overcommitted
        else ("Income is fully allocated across spending, bills, irregular costs, debt and savings." if balanced else "Money left after planned spending. Direct this toward emergency, savings, debt, or planned costs.")
    )
    result_amount = shortfall_weekly if overcommitted else max(summary["surplus_weekly"], 0.0)
    result_foot = "weekly shortfall" if overcommitted else ("nothing left to allocate" if balanced else "available to allocate")
    result_class = "pillar-card warning" if overcommitted else "pillar-card"

    st.markdown(f"""
    <div class="pillar-grid">
      <div class="pillar-card">
        <div class="pillar-label">INCOME</div>
        <h3>What comes in</h3>
        <p>Active income sources converted to a weekly equivalent.</p>
        <div class="pillar-metric"><div class="pillar-stat">{html.escape(money_text(summary['income_weekly']))}</div><div class="pillar-foot">income per week</div></div>
      </div>
      <div class="pillar-card">
        <div class="pillar-label">OUTFLOWS</div>
        <h3>What goes out</h3>
        <p>Everyday spending, regular bills, and planned irregular costs.</p>
        <div class="pillar-metric"><div class="pillar-stat">{html.escape(money_text(summary['expense_weekly']))}</div><div class="pillar-foot">planned outflows per week</div></div>
      </div>
      <div class="{result_class}">
        <div class="pillar-label">{html.escape(result_label)}</div>
        <h3>{html.escape(result_title)}</h3>
        <p>{html.escape(result_body)}</p>
        <div class="pillar-metric"><div class="pillar-stat">{html.escape(money_text(result_amount))}</div><div class="pillar-foot">{html.escape(result_foot)}</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if overcommitted:
        st.markdown(f"""
        <div class="overcommit-panel">
          <h4>Plan is overcommitted by {html.escape(money_text(shortfall_weekly))} / week</h4>
          <p><strong>Safe-to-spend is shown as $0.00 for planning purposes.</strong> Your entered everyday spending is still recorded, but the current plan does not have enough income to fund all outflows. Review regular bills, irregular costs and weekly spend money before relying on the suggested APs.</p>
          <p>This is a budgeting signal only, not financial advice. If this reflects hardship or debt pressure, consider seeking budgeting support from an appropriate service.</p>
        </div>
        """, unsafe_allow_html=True)

    unallocated_label = "Shortfall / week" if overcommitted else "Unallocated / week"
    unallocated_value = shortfall_weekly if overcommitted else summary["surplus_weekly"]
    unallocated_class = "metric-tile warning" if overcommitted else "metric-tile"
    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-tile"><div class="metric-label">Regular bills / week</div><div class="metric-value">{html.escape(money_text(summary['fixed_weekly']))}</div></div>
      <div class="metric-tile"><div class="metric-label">Irregular costs / week</div><div class="metric-value">{html.escape(money_text(summary['sinking_weekly']))}</div></div>
      <div class="metric-tile"><div class="metric-label">Suggested APs / week</div><div class="metric-value">{html.escape(money_text(summary['fixed_weekly'] + summary['sinking_weekly']))}</div></div>
      <div class="{unallocated_class}"><div class="metric-label">{html.escape(unallocated_label)}</div><div class="metric-value">{html.escape(money_text(unallocated_value))}</div></div>
    </div>
    """, unsafe_allow_html=True)

    render_spending_plan_disclaimer(compact=True)

    income = active_online_df(read_online_table(sheet_id, "spending_income"))
    expenses = active_online_df(read_online_table(sheet_id, "spending_expenses"))
    high: list[str] = []
    medium: list[str] = []
    if income.empty or summary["income_annual"] <= 0:
        high.append("Add at least one active income source before relying on the assessment.")
    if summary["surplus_annual"] < 0:
        high.append("Planned outflows are higher than income. Reduce costs or adjust the plan before adding savings goals.")
    if expenses.empty:
        medium.append("Load the common spending checklist and enter amounts for the items that apply.")
    if summary["sinking_weekly"] <= 0 and not expenses.empty:
        medium.append("No planned irregular costs are funded yet. Predictable annual costs can become emergencies if they are not smoothed through the year.")
    if summary["everyday_weekly"] <= 0 and not expenses.empty:
        medium.append("No everyday spending allowance is set. Add a realistic weekly amount for groceries, fuel, cafes and day-to-day spending.")

    if high or medium:
        st.markdown("##### Needs attention")
        for item in high:
            st.markdown(f"<div class='attention-card high'><div class='attention-label'>High priority</div><div class='attention-text'>{html.escape(item)}</div></div>", unsafe_allow_html=True)
        for item in medium[:4]:
            st.markdown(f"<div class='attention-card medium'><div class='attention-label'>Medium priority</div><div class='attention-text'>{html.escape(item)}</div></div>", unsafe_allow_html=True)
    elif summary["income_annual"] > 0:
        st.success("The plan has income, spending categories and a weekly money-flow result.")

    st.markdown("##### Recommended weekly money flow")
    st.caption("These suggested APs and transfers are generated from your entered income and outflows. Review them carefully before changing bank payments.")
    rows = [
        ("Income lands in", "Hub account", summary["income_weekly"], "Starting point for bills, APs and transfers"),
        ("Transfer to", "Everyday card account", safe_to_spend_weekly, "Safe weekly spend money; held at $0.00 while the plan is overcommitted" if overcommitted else "Safe weekly spend money"),
        ("Keep/transfer for", "Regular bills and commitments", summary["fixed_weekly"], "Rent, utilities, subscriptions, insurance and minimum repayments"),
        ("Transfer to", "Planned irregular costs", summary["sinking_weekly"], "Christmas, clothes, car costs, annual fees and other predictable irregular costs"),
        ("Resolve shortfall", "Review entered costs and APs", shortfall_weekly, "Planned outflows exceed income" if overcommitted else "No shortfall in the current plan"),
    ] if overcommitted else [
        ("Income lands in", "Hub account", summary["income_weekly"], "Starting point for bills, APs and transfers"),
        ("Transfer to", "Everyday card account", safe_to_spend_weekly, "Safe weekly spend money"),
        ("Keep/transfer for", "Regular bills and commitments", summary["fixed_weekly"], "Rent, utilities, subscriptions, insurance and minimum repayments"),
        ("Transfer to", "Planned irregular costs", summary["sinking_weekly"], "Christmas, clothes, car costs, annual fees and other predictable irregular costs"),
        ("Direct surplus to", "Debt, emergency fund, then savings/goals", max(summary["surplus_weekly"], 0.0), "Extra repayment first, then resilience, then longer-term goals"),
    ]
    body = "".join(
        f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td class='money-amount'>{html.escape(money_text(c))}</td><td>{html.escape(d)}</td></tr>"
        for a,b,c,d in rows
    )
    st.markdown(f"""
    <div class="money-summary-card">
      <table class="money-flow-table">
        <thead><tr><th>Action</th><th>Destination</th><th>Weekly amount</th><th>Purpose</th></tr></thead>
        <tbody>{body}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("How to use this assessment", expanded=False):
        render_spending_flow_guidance(summary)


def render_spending_income_form(sheet_id: str) -> None:
    st.markdown("#### Setup income")
    st.write(
        "Work through the income sources once, then return here only when income changes. "
        "Each row is converted to weekly and annual equivalents for the assessment."
    )
    income = active_online_df(read_online_table(sheet_id, "spending_income"))
    if income.empty:
        st.info("No income rows were found yet. Pathmark normally creates starter income rows automatically; refresh this page or add an income source below.")

    editor_rows = []
    for _, row in income.iterrows():
        amount, frequency = amount_and_frequency_from_row(row)
        editor_rows.append({
            "_record_id": row.get("income_id", ""),
            "Income source": row.get("category", ""),
            "Amount": float(amount),
            "Frequency": frequency,
            "Notes": row.get("notes", ""),
            "Active": True,
        })
    edit_df = pd.DataFrame(editor_rows, columns=["_record_id", "Income source", "Amount", "Frequency", "Notes", "Active"])
    with st.form("spending_income_editor", clear_on_submit=False):
        edited = safe_data_editor(
            edit_df,
            hide_index=True,
            use_container_width=True,
            column_order=["Income source", "Amount", "Frequency", "Notes", "Active"],
            column_config={
                "Income source": pathmark_column_config("TextColumn", "Income source"),
                "Amount": pathmark_column_config("NumberColumn", "Amount", min_value=0.0, step=10.0, format="$%.2f"),
                "Frequency": pathmark_column_config("SelectboxColumn", "Frequency", options=["Weekly", "Fortnightly", "Monthly", "Yearly"]),
                "Notes": pathmark_column_config("TextColumn", "Notes"),
                "Active": pathmark_column_config("CheckboxColumn", "Active", help="Untick to remove this source from the current assessment."),
            },
        )
        save_income = st.form_submit_button("Save income setup", use_container_width=True)
    if save_income:
        failures = []
        updated_count = 0
        for _, edited_row in edited.iterrows():
            record_id = str(edited_row.get("_record_id", "")).strip()
            if not record_id:
                continue
            category = str(edited_row.get("Income source", "")).strip()
            amount = money_value(edited_row.get("Amount", 0.0))
            frequency = str(edited_row.get("Frequency", "Weekly") or "Weekly")
            active = bool(edited_row.get("Active", True))
            if not category:
                failures.append("One row was missing an income source.")
                continue
            updates = {
                "person": "Me",
                "category": category,
                "notes": str(edited_row.get("Notes", "") or "").strip(),
                "status": "active" if active else "archived",
            }
            updates.update(amount_columns_for_frequency(amount, frequency, include_quarterly=False))
            ok, msg = update_online_record(sheet_id, "spending_income", record_id, updates)
            if ok:
                updated_count += 1
            else:
                failures.append(safe_user_message(msg))
        if failures:
            st.warning("Some income rows could not be saved: " + "; ".join(failures[:3]))
        else:
            spending_save_and_refresh(f"Saved {updated_count} income row(s).")

    st.markdown("#### Add a new income source")
    with st.expander("Add income source", expanded=False):
        with st.form("spending_custom_income_form", clear_on_submit=False):
            category_choice = st.selectbox("Income source", SPENDING_INCOME_STARTERS + ["Other"])
            custom_category = st.text_input("Custom income source", placeholder="Optional")
            c1, c2 = st.columns(2)
            with c1:
                frequency = st.selectbox("How often does it arrive?", ["Weekly", "Fortnightly", "Monthly", "Yearly"], key="custom_income_frequency")
            with c2:
                amount = st.number_input("Amount received", min_value=0.0, step=10.0, format="%.2f", key="custom_income_amount")
            notes = st.text_area("Notes", placeholder="Optional")
            submitted = st.form_submit_button("Add income source", use_container_width=True)
        if submitted:
            category = custom_category.strip() or category_choice
            if not category.strip() or amount <= 0:
                st.warning("Add an income source and an amount before saving.")
            else:
                record = {
                    "income_id": f"income-{uuid.uuid4().hex[:12]}",
                    "person": "Me",
                    "category": category.strip(),
                    "notes": notes.strip(),
                    "status": "active",
                    "source": "Pathmark Spending Plan income setup",
                }
                record.update(amount_columns_for_frequency(amount, frequency, include_quarterly=False))
                ok, msg = append_online_record(sheet_id, "spending_income", record)
                if ok:
                    spending_save_and_refresh("Saved income source.")
                else:
                    st.warning(safe_user_message(msg))


def spending_kind_help(kind: str) -> str:
    normalised = normalise_spending_kind(kind)
    if normalised == "Everyday spend":
        return "Use this for costs you manage during the week, such as groceries, fuel, cafes, eating out and personal spending. Suggested account: Everyday card account."
    if normalised == "Sinking fund":
        return "Use this for predictable costs that do not happen every week, such as Christmas, clothes, dental, gifts, holidays, car registration and larger planned costs. Suggested account: Planned irregular costs."
    return "Use this for regular commitments, bills, subscriptions, minimum debt repayments and direct debits that should remain funded from the hub account. Suggested account: Hub account."


def spending_default_frequency(kind: str) -> str:
    normalised = normalise_spending_kind(kind)
    if normalised == "Sinking fund":
        return "Yearly"
    return "Monthly" if normalised == "Fixed cost" else "Weekly"


def spending_bucket_options(kind: str, existing: pd.DataFrame | None = None) -> list[str]:
    """Return predefined and user-created buckets for a fixed money-flow type."""
    options = spending_sections_for_kind(kind)
    if existing is not None and not existing.empty and "group_name" in existing.columns:
        kind_rows = existing[existing["expense_kind"].apply(normalise_spending_kind) == normalise_spending_kind(kind)].copy()
        for value in kind_rows["group_name"].fillna("").tolist():
            bucket = str(value or "").strip()
            if bucket and bucket not in options:
                options.append(bucket)
    return options or [SPENDING_BUCKET_LABELS.get(normalise_spending_kind(kind), kind)]


def spending_editor_dataframe(rows: pd.DataFrame, fallback_label: str) -> pd.DataFrame:
    editor_rows: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        amount, frequency = amount_and_frequency_from_row(row)
        editor_rows.append(
            {
                "_record_id": row.get("expense_id", ""),
                "Item": row.get("item", ""),
                "Amount": float(amount),
                "Frequency": frequency,
                "Notes": row.get("notes", ""),
                "Active": True,
                "Section": row.get("group_name", fallback_label) or fallback_label,
            }
        )
    return pd.DataFrame(editor_rows)


def save_spending_editor_rows(sheet_id: str, edited: pd.DataFrame, kind: str, section: str) -> tuple[int, list[str]]:
    failures: list[str] = []
    updates_count = 0
    for _, edited_row in edited.iterrows():
        record_id = str(edited_row.get("_record_id", "")).strip()
        if not record_id:
            continue
        item = str(edited_row.get("Item", "")).strip()
        frequency = str(edited_row.get("Frequency", spending_default_frequency(kind)) or spending_default_frequency(kind))
        amount = money_value(edited_row.get("Amount", 0.0))
        active = bool(edited_row.get("Active", True))
        if not item:
            failures.append("One row was missing an item name.")
            continue
        update = {
            "expense_kind": kind,
            "group_name": section,
            "item": item,
            "notes": str(edited_row.get("Notes", "") or "").strip(),
            "status": "active" if active else "archived",
        }
        update.update(amount_columns_for_frequency(amount, frequency, include_quarterly=True))
        ok, msg = update_online_record(sheet_id, "spending_expenses", record_id, update)
        if ok:
            updates_count += 1
        else:
            failures.append(safe_user_message(msg))
    return updates_count, failures


def render_add_custom_spending_item(sheet_id: str, kind: str, existing: pd.DataFrame) -> None:
    """Add a custom item to the current fixed money-flow type and chosen bucket."""
    label = SPENDING_BUCKET_LABELS.get(normalise_spending_kind(kind), kind)
    with st.expander(f"Add custom item to {label.lower()}", expanded=False):
        with st.form(f"spending_custom_expense_form_{normalise_spending_kind(kind).replace(' ', '_').lower()}", clear_on_submit=False):
            item_name = st.text_input("What is the item?", placeholder="e.g. Vet appointment, pottery clay, software subscription")
            bucket_options = spending_bucket_options(kind, existing)
            bucket_choice = st.selectbox("Which bucket should it sit under?", bucket_options + ["Create new bucket"])
            new_bucket = ""
            if bucket_choice == "Create new bucket":
                new_bucket = st.text_input("New bucket name", placeholder="e.g. Pet costs, pottery costs, garden costs")
            c1, c2 = st.columns(2)
            with c1:
                frequency = st.selectbox(
                    "How often is it paid or set aside?",
                    SPENDING_FREQUENCIES,
                    index=SPENDING_FREQUENCIES.index(spending_default_frequency(kind)) if spending_default_frequency(kind) in SPENDING_FREQUENCIES else 0,
                )
            with c2:
                amount = st.number_input("Amount", min_value=0.0, step=5.0, format="%.2f")
            notes = st.text_area("Notes", placeholder="Optional")
            st.caption(spending_kind_help(kind))
            submitted = st.form_submit_button("Add this spending item", use_container_width=True)
        if submitted:
            item = item_name.strip()
            section = (new_bucket.strip() if bucket_choice == "Create new bucket" else bucket_choice).strip()
            if not item:
                st.warning("Add an item name before saving.")
            elif not section:
                st.warning("Choose a bucket or enter a new bucket name before saving.")
            else:
                record = {
                    "expense_id": f"expense-{uuid.uuid4().hex[:12]}",
                    "expense_kind": kind,
                    "group_name": section,
                    "item": item,
                    "notes": notes.strip(),
                    "status": "active",
                    "source": "Pathmark Spending Plan spending setup",
                }
                record.update(amount_columns_for_frequency(amount, frequency, include_quarterly=True))
                ok, msg = append_online_record(sheet_id, "spending_expenses", record)
                if ok:
                    spending_save_and_refresh(f"Saved {item} in {section}.")
                else:
                    st.warning(safe_user_message(msg))


def render_spending_expense_form(sheet_id: str) -> None:
    st.markdown("#### Spending checklist")
    st.caption(
        "Work down the common costs and enter amounts only where they apply. "
        "The money-flow type is fixed; buckets organise the real-world costs inside it."
    )
    expenses = active_online_df(read_online_table(sheet_id, "spending_expenses"))
    if expenses.empty:
        st.info("No spending checklist rows were found yet. Pathmark normally creates starter spending rows automatically; refresh this page or add a custom spending item below.")
        render_add_custom_spending_item(sheet_id, "Everyday spend", expenses)
        return

    kind_labels = [SPENDING_BUCKET_LABELS[k] for k in SPENDING_BUCKET_ORDER]
    selected_label = st.radio(
        "Choose spending type",
        kind_labels,
        horizontal=True,
        label_visibility="collapsed",
        key="spending_expense_type",
    )
    kind = SPENDING_BUCKET_ORDER[kind_labels.index(selected_label)]
    label = selected_label
    bucket_rows = expenses[expenses["expense_kind"].apply(normalise_spending_kind) == normalise_spending_kind(kind)].copy()
    bucket_total = sum(annual_from_row(row) for _, row in bucket_rows.iterrows()) / 52 if not bucket_rows.empty else 0.0
    st.markdown(f"##### {label}")
    st.caption(spending_kind_help(kind))
    st.metric("Weekly equivalent", money_text(bucket_total))
    if bucket_rows.empty:
        st.info(f"No {label.lower()} rows yet.")
        render_add_custom_spending_item(sheet_id, kind, expenses)
        return
    for section, section_df in bucket_rows.groupby(bucket_rows["group_name"].fillna(label), sort=False):
        section_name = str(section or label)
        section_weekly = sum(annual_from_row(row) for _, row in section_df.iterrows()) / 52 if not section_df.empty else 0.0
        with st.expander(f"{section_name} — {money_text(section_weekly)} / week", expanded=False):
            st.caption("Enter or adjust amounts. Leave an amount as $0.00 if the item does not apply. Untick Active to remove a row from the current assessment.")
            edit_df = spending_editor_dataframe(section_df, section_name)
            with st.form(f"spending_editor_{kind}_{section_name}".replace(" ", "_").replace("/", "_").lower(), clear_on_submit=False):
                edited = safe_data_editor(
                    edit_df,
                    hide_index=True,
                    use_container_width=True,
                    column_order=["Item", "Amount", "Frequency", "Notes", "Active"],
                    column_config={
                        "Item": pathmark_column_config("TextColumn", "Item", help="Rename the item if your wording is more useful."),
                        "Amount": pathmark_column_config("NumberColumn", "Amount", min_value=0.0, step=5.0, format="$%.2f"),
                        "Frequency": pathmark_column_config("SelectboxColumn", "Frequency", options=SPENDING_FREQUENCIES),
                        "Notes": pathmark_column_config("TextColumn", "Notes", help="Optional"),
                        "Active": pathmark_column_config("CheckboxColumn", "Active", help="Untick to remove this row from the assessment."),
                    },
                )
                save = st.form_submit_button(f"Save {section_name}", use_container_width=True)
            if save:
                updates_count, failures = save_spending_editor_rows(sheet_id, edited, kind, section_name)
                if failures:
                    st.warning("Some rows could not be saved: " + "; ".join(failures[:3]))
                else:
                    spending_save_and_refresh(f"Saved {updates_count} {section_name.lower()} row(s).")
    render_add_custom_spending_item(sheet_id, kind, expenses)

def render_spending_account_form(sheet_id: str) -> None:
    st.markdown("#### APs and fixed account roles")
    st.write(
        "Keep the five roles fixed so the cash-flow logic stays clear. You can use your own bank accounts for these roles; "
        "Pathmark is naming the job each account does."
    )
    summary = spending_summary(sheet_id)
    render_spending_flow_guidance(summary)
    st.markdown("#### Account role checklist")
    for title, purpose in SPENDING_ACCOUNT_ROLES:
        st.markdown(f"- **{html.escape(title)}** — {html.escape(purpose)}")
    if st.button("Save / refresh AP account role rows", use_container_width=True):
        records = {"spending_accounts": []}
        existing_accounts = active_online_df(read_online_table(sheet_id, "spending_accounts"))
        existing_names = {str(row.get("account_name", "")).strip().lower() for _, row in existing_accounts.iterrows()} if not existing_accounts.empty else set()
        for account in spending_account_role_records(summary):
            if str(account.get("account_name", "")).strip().lower() not in existing_names:
                records["spending_accounts"].append(account)
        if not records["spending_accounts"]:
            st.info("The fixed account role rows already exist. Edit the current plan records if needed.")
        else:
            ok, msg = append_many_online_records(sheet_id, records)
            if ok:
                spending_save_and_refresh(msg)
            else:
                st.warning(safe_user_message(msg))



def _frequency_from_amount_row(row: pd.Series, include_quarterly: bool = False) -> tuple[float, str]:
    frequency_columns = [
        ("weekly_amount", "Weekly"),
        ("fortnightly_amount", "Fortnightly"),
        ("monthly_amount", "Monthly"),
    ]
    if include_quarterly:
        frequency_columns.append(("quarterly_amount", "Quarterly"))
    frequency_columns.append(("yearly_amount", "Yearly"))
    for col, label in frequency_columns:
        amount = money_value(row.get(col, ""))
        if abs(amount) > 0.005:
            return amount, label
    annual = money_value(row.get("annual_amount", ""))
    if abs(annual) > 0.005:
        return annual, "Yearly"
    return 0.0, "Weekly"


FINANCE_TEMPLATE_TITLE = "Pathmark Finance Template"


def _template_sheet_title(kind: str) -> str:
    return "Income" if kind == "income" else "Outflows"


def _backup_sheet_title(table: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Backup {table} {stamp}"[:95]


def _sheet_metadata_by_title(service: Any, sheet_id: str) -> dict[str, dict[str, Any]]:
    metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    out = {}
    for sheet in metadata.get("sheets", []):
        props = sheet.get("properties", {})
        title = str(props.get("title", "") or "")
        if title:
            out[title] = props
    return out


def _ensure_template_sheet(service: Any, sheet_id: str, title: str, headers: list[str]) -> None:
    titles = _sheet_metadata_by_title(service, sheet_id)
    if title not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        ).execute()
    end_col = sheet_col_letter(len(headers))
    service.spreadsheets().values().clear(spreadsheetId=sheet_id, range=f"'{title}'!A:{end_col}").execute()
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"'{title}'!A1:{end_col}1",
        valueInputOption="RAW",
        body={"values": [headers]},
    ).execute()


def _create_spending_backup_tabs(service: Any, sheet_id: str) -> tuple[bool, str]:
    backed_up = []
    try:
        for table in ["spending_income", "spending_expenses"]:
            columns = ONLINE_TABLES.get(table, [])
            if not columns:
                continue
            source_values = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=f"{table}!A1:{sheet_col_letter(len(columns))}",
            ).execute().get("values", [])
            if not source_values:
                source_values = [columns]
            title = _backup_sheet_title(table)
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
            ).execute()
            end_col = sheet_col_letter(max(len(source_values[0]), 1))
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"'{title}'!A1:{end_col}{len(source_values)}",
                valueInputOption="RAW",
                body={"values": source_values},
            ).execute()
            backed_up.append(title)
        return True, "Created backup tabs in Pathmark Sync: " + "; ".join(backed_up)
    except Exception as exc:
        return False, f"Could not create backup tabs: {exc}"

BACKUP_SHEET_PREFIX = "Pathmark Backup - "


def _backup_timestamp_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _values_for_sheet_backup(service: Any, sheet_id: str, title: str, columns: list[str]) -> list[list[str]]:
    end_col = sheet_col_letter(max(len(columns) + 10, 1))
    try:
        values = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"'{title}'!A1:{end_col}",
        ).execute().get("values", [])
        if values:
            return values
    except Exception:
        pass
    return [columns]


def create_pathmark_sync_backup(sheet_id: str) -> tuple[bool, str, str]:
    """Create a separate Google Sheet backup of the current Pathmark Sync data."""
    service = sheets_service()
    drive = drive_service()
    sheet_id = extract_google_sheet_id(sheet_id)
    if service is None:
        return False, "", "Google Sheets access is not available for this session."
    if not sheet_id:
        return False, "", "No Pathmark Sync sheet is selected."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        stamp = _backup_timestamp_label()
        backup_title = f"{BACKUP_SHEET_PREFIX}{stamp}"
        spreadsheet = service.spreadsheets().create(
            body={
                "properties": {"title": backup_title},
                "sheets": [{"properties": {"title": "README"}}],
            },
            fields="spreadsheetId,spreadsheetUrl",
        ).execute()
        backup_id = spreadsheet.get("spreadsheetId", "")
        backup_url = spreadsheet.get("spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{backup_id}")
        if drive is not None and backup_id:
            try:
                drive.files().update(
                    fileId=backup_id,
                    body={"appProperties": {"pathmark_backup": "true", "pathmark_backup_source": sheet_id}},
                    fields="id",
                ).execute()
            except Exception:
                pass
        readme = [
            ["Pathmark backup"],
            ["Created", stamp],
            ["Source sheet", sheet_id],
            ["Note", "This file is a user-owned backup of Pathmark Sync. Restore from Planner Settings if needed."],
        ]
        service.spreadsheets().values().update(
            spreadsheetId=backup_id,
            range="README!A1:B4",
            valueInputOption="RAW",
            body={"values": readme},
        ).execute()
        tables = {"pending_changes": SYNC_COLUMNS, **ONLINE_TABLES}
        requests = [{"addSheet": {"properties": {"title": title}}} for title in tables]
        if requests:
            service.spreadsheets().batchUpdate(spreadsheetId=backup_id, body={"requests": requests}).execute()
        copied = 0
        for title, columns in tables.items():
            values = _values_for_sheet_backup(service, sheet_id, title, columns)
            end_col = sheet_col_letter(max(len(values[0]) if values and values[0] else len(columns), 1))
            service.spreadsheets().values().update(
                spreadsheetId=backup_id,
                range=f"'{title}'!A1:{end_col}{len(values)}",
                valueInputOption="RAW",
                body={"values": values},
            ).execute()
            copied += max(len(values) - 1, 0)
        return True, backup_url, f"Created backup Google Sheet **{backup_title}** with {copied} data row(s)."
    except Exception as exc:
        return False, "", f"Could not create a Pathmark Sync backup: {exc}"


def list_pathmark_backup_sheets(source_sheet_id: str = "") -> tuple[bool, list[dict[str, str]], str]:
    service = drive_service()
    if service is None:
        return False, [], "Google Drive access is not available for this session."
    source_sheet_id = extract_google_sheet_id(source_sheet_id)
    found: list[dict[str, str]] = []

    def add_file(file: dict[str, Any]) -> None:
        fid = str(file.get("id", "") or "")
        if not fid or any(existing.get("id") == fid for existing in found):
            return
        found.append({
            "id": fid,
            "name": str(file.get("name", "") or "Untitled backup"),
            "modifiedTime": str(file.get("modifiedTime", "") or ""),
            "webViewLink": str(file.get("webViewLink", "") or f"https://docs.google.com/spreadsheets/d/{fid}"),
        })

    try:
        queries = [
            "appProperties has { key='pathmark_backup' and value='true' } and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            f"name contains '{BACKUP_SHEET_PREFIX.replace(chr(39), chr(92)+chr(39))}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        ]
        if source_sheet_id:
            queries.insert(0, f"appProperties has {{ key='pathmark_backup_source' and value='{source_sheet_id}' }} and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false")
        for query in queries:
            result = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id,name,modifiedTime,webViewLink,appProperties)",
                orderBy="modifiedTime desc",
                pageSize=25,
            ).execute()
            for file in result.get("files", []):
                add_file(file)
        found = sorted(found, key=lambda f: f.get("modifiedTime", ""), reverse=True)
        return True, found, f"Found {len(found)} Pathmark backup sheet(s)."
    except Exception as exc:
        return False, [], f"Could not list Pathmark backup sheets: {exc}"


def _clear_and_write_sheet_values(service: Any, sheet_id: str, title: str, values: list[list[str]], fallback_columns: list[str]) -> None:
    if not values:
        values = [fallback_columns]
    if not values[0]:
        values[0] = fallback_columns
    end_col = sheet_col_letter(max(len(values[0]), len(fallback_columns), 1))
    service.spreadsheets().values().clear(spreadsheetId=sheet_id, range=f"'{title}'!A:{end_col}").execute()
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"'{title}'!A1:{end_col}{len(values)}",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def cleanup_old_pathmark_backups(source_sheet_id: str = "", keep_latest: int = 5) -> tuple[bool, str]:
    """Move older Pathmark backup sheets to Drive trash, keeping the latest N."""
    ok, backups, msg = list_pathmark_backup_sheets(source_sheet_id)
    if not ok:
        return False, msg
    keep_latest = max(1, int(keep_latest or 5))
    if len(backups) <= keep_latest:
        return True, f"No cleanup needed. {len(backups)} backup sheet(s) found; keeping latest {keep_latest}."
    drive = drive_service()
    if drive is None:
        return False, "Google Drive access is not available for backup cleanup."
    old = backups[keep_latest:]
    removed = 0
    errors = 0
    for b in old:
        try:
            drive.files().update(fileId=b.get("id", ""), body={"trashed": True}).execute()
            removed += 1
        except Exception:
            errors += 1
    if errors:
        return False, f"Moved {removed} old backup sheet(s) to Google Drive Trash; {errors} could not be moved."
    return True, f"Moved {removed} old backup sheet(s) to Google Drive Trash. Kept the latest {keep_latest}."


def restore_missing_pathmark_sync_from_backup(backup_sheet_id: str) -> tuple[bool, str, str]:
    """Create a new Pathmark Sync sheet and restore data from a selected backup.

    This supports the deleted-sheet recovery path where there is no current
    sheet to restore into. A safety backup is not created because the active
    sheet is missing; the selected backup remains unchanged.
    """
    service = sheets_service()
    backup_sheet_id = extract_google_sheet_id(backup_sheet_id)
    if service is None:
        return False, "", "Google Sheets access is not available for this session."
    if not backup_sheet_id:
        return False, "", "Choose a Pathmark Backup sheet first."
    ok_create, new_sheet_id, new_url = create_user_sync_sheet()
    if not ok_create or not new_sheet_id:
        return False, "", new_url or "Could not create a new Pathmark Sync sheet."
    try:
        backup_tables = {"pending_changes": SYNC_COLUMNS, **ONLINE_TABLES}
        restored = 0
        for title, columns in backup_tables.items():
            ensure_sheet_with_header(service, new_sheet_id, title, columns)
            values = _values_for_sheet_backup(service, backup_sheet_id, title, columns)
            _clear_and_write_sheet_values(service, new_sheet_id, title, values, columns)
            restored += max(len(values) - 1, 0)
        clear_online_cache(new_sheet_id)
        st.session_state["sync_sheet_id"] = new_sheet_id
        st.session_state.pop("sync_sheet_recovery_message", None)
        return True, new_sheet_id, f"Created a new Pathmark Sync sheet and restored {restored} row(s) from backup."
    except Exception as exc:
        return False, new_sheet_id, f"Created a new Pathmark Sync sheet, but could not restore the selected backup: {exc}"


def restore_pathmark_sync_from_backup(sheet_id: str, backup_sheet_id: str) -> tuple[bool, str]:
    service = sheets_service()
    sheet_id = extract_google_sheet_id(sheet_id)
    backup_sheet_id = extract_google_sheet_id(backup_sheet_id)
    if service is None:
        return False, "Google Sheets access is not available for this session."
    if not sheet_id or not backup_sheet_id:
        return False, "Choose a Pathmark Sync sheet and a backup sheet first."
    try:
        ok_backup, backup_url, backup_msg = create_pathmark_sync_backup(sheet_id)
        if not ok_backup:
            return False, backup_msg
        ensure_pathmark_online_schema(service, sheet_id)
        backup_tables = {"pending_changes": SYNC_COLUMNS, **ONLINE_TABLES}
        restored = 0
        for title, columns in backup_tables.items():
            ensure_sheet_with_header(service, sheet_id, title, columns)
            values = _values_for_sheet_backup(service, backup_sheet_id, title, columns)
            _clear_and_write_sheet_values(service, sheet_id, title, values, columns)
            restored += max(len(values) - 1, 0)
        for key in list(st.session_state.keys()):
            if str(key).startswith(f"online_schema_ready::{sheet_id}") or str(key).startswith(f"online_header::{sheet_id}::"):
                st.session_state.pop(key, None)
        clear_online_cache(sheet_id)
        return True, f"Restored {restored} row(s) from backup. A safety backup was created first: {backup_url}"
    except Exception as exc:
        return False, f"Could not restore from backup: {exc}"


def restore_pathmark_sync_to_default(sheet_id: str, include_starter_examples: bool = False) -> tuple[bool, str]:
    """Reset the selected Pathmark Sync sheet to the default Pathmark tab structure."""
    service = sheets_service()
    sheet_id = extract_google_sheet_id(sheet_id)
    if service is None:
        return False, "Google Sheets access is not available for this session."
    if not sheet_id:
        return False, "No Pathmark Sync sheet is selected."
    try:
        ok_backup, backup_url, backup_msg = create_pathmark_sync_backup(sheet_id)
        if not ok_backup:
            return False, backup_msg
        # Make sure tabs exist, then replace only the live Pathmark tabs with headers.
        for key in list(st.session_state.keys()):
            if str(key).startswith(f"online_schema_ready::{sheet_id}") or str(key).startswith(f"online_header::{sheet_id}::"):
                st.session_state.pop(key, None)
        ensure_pathmark_online_schema(service, sheet_id)
        default_tables = {"pending_changes": SYNC_COLUMNS, **ONLINE_TABLES}
        for title, columns in default_tables.items():
            ensure_sheet_with_header(service, sheet_id, title, columns)
            _clear_and_write_sheet_values(service, sheet_id, title, [columns], columns)
        clear_online_cache(sheet_id)
        message = f"Restored Pathmark Sync to the default structure. A backup was created first: {backup_url}"
        if include_starter_examples:
            ok_starter, starter_msg = append_many_online_records(sheet_id, build_starter_example_records())
            message += "\n" + (starter_msg if ok_starter else safe_user_message(starter_msg))
        else:
            ok_default, default_msg = append_many_online_records(sheet_id, build_default_area_records())
            message += "\n" + (default_msg if ok_default else safe_user_message(default_msg))
            ensure_spending_plan_default_rows(sheet_id)
        return True, message
    except Exception as exc:
        return False, f"Could not restore Pathmark Sync to default: {exc}"


def _finance_template_session_id() -> str:
    return str(st.session_state.get("spending_finance_template_id", "") or "")


def _find_existing_finance_template() -> tuple[bool, str, str]:
    service = drive_service()
    if service is None:
        return False, "", ""
    try:
        title = FINANCE_TEMPLATE_TITLE.replace("'", "\\'")
        queries = [
            "appProperties has { key='pathmark_finance_template' and value='true' } and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            f"name='{title}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        ]
        found: list[dict[str, Any]] = []
        for query in queries:
            result = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id,name,modifiedTime,webViewLink,appProperties)",
                orderBy="modifiedTime desc",
                pageSize=10,
            ).execute()
            for file in result.get("files", []):
                if file.get("id") and not any(existing.get("id") == file.get("id") for existing in found):
                    found.append(file)
        if not found:
            return False, "", ""
        file = sorted(found, key=lambda f: str(f.get("modifiedTime", "")), reverse=True)[0]
        fid = str(file.get("id", "") or "")
        url = str(file.get("webViewLink", "") or f"https://docs.google.com/spreadsheets/d/{fid}/edit")
        if fid:
            st.session_state["spending_finance_template_id"] = fid
            return True, fid, url
        return False, "", ""
    except Exception:
        return False, "", ""


def _ensure_finance_template_file() -> tuple[bool, str, str, str]:
    sheets = sheets_service()
    if sheets is None:
        return False, "", "", "Google Sheets access is not available for this session."
    found, template_id, template_url = _find_existing_finance_template()
    if found and template_id:
        return True, template_id, template_url, "Using your existing Pathmark Finance Template."
    try:
        spreadsheet = sheets.spreadsheets().create(
            body={
                "properties": {"title": FINANCE_TEMPLATE_TITLE},
                "sheets": [
                    {"properties": {"title": _template_sheet_title("income")}},
                    {"properties": {"title": _template_sheet_title("outflows")}},
                ],
            },
            fields="spreadsheetId,spreadsheetUrl",
        ).execute()
        template_id = str(spreadsheet.get("spreadsheetId", "") or "")
        template_url = str(spreadsheet.get("spreadsheetUrl", "") or f"https://docs.google.com/spreadsheets/d/{template_id}/edit")
        try:
            dservice = drive_service()
            if dservice is not None and template_id:
                dservice.files().update(
                    fileId=template_id,
                    body={"appProperties": {"pathmark_finance_template": "true", "pathmark_version": "0.6.74"}},
                    fields="id,webViewLink",
                ).execute()
        except Exception:
            pass
        st.session_state["spending_finance_template_id"] = template_id
        return True, template_id, template_url, "Created a separate Pathmark Finance Template sheet."
    except Exception as exc:
        return False, "", "", f"Could not create the Pathmark Finance Template: {exc}"


def create_spending_plan_template(sheet_id: str) -> tuple[bool, str, str]:
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session.", ""
    sheet_id = extract_google_sheet_id(sheet_id)
    ok_file, template_id, template_url, file_msg = _ensure_finance_template_file()
    if not ok_file:
        return False, file_msg, ""
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        income = active_online_df(read_online_table(sheet_id, "spending_income"))
        expenses = active_online_df(read_online_table(sheet_id, "spending_expenses"))
        income_headers = ["Income source", "Amount", "Frequency", "Notes", "Active"]
        outflow_headers = ["Item", "Kind", "Bucket", "Amount", "Frequency", "Notes", "Active"]
        income_values = [income_headers]
        if income.empty:
            income_values.append(["Main income", "", "Weekly", "", "Yes"])
        else:
            for _, row in income.iterrows():
                amount, freq = _frequency_from_amount_row(row, include_quarterly=False)
                income_values.append([
                    str(row.get("category", "") or "Income"),
                    money_text(amount) if amount else "",
                    freq,
                    str(row.get("notes", "") or ""),
                    "Yes" if str(row.get("status", "") or "active").lower() != "inactive" else "No",
                ])
        outflow_values = [outflow_headers]
        if expenses.empty:
            for kind, group, item, _amount, freq in SPENDING_STARTER_CATEGORIES[:8]:
                outflow_values.append([item, spending_bucket_label(kind), group, "", freq, "", "Yes"])
        else:
            for _, row in expenses.iterrows():
                amount, freq = _frequency_from_amount_row(row, include_quarterly=True)
                outflow_values.append([
                    str(row.get("item", "") or "Spending item"),
                    spending_bucket_label(row.get("expense_kind", "")),
                    str(row.get("group_name", "") or spending_bucket_label(row.get("expense_kind", ""))),
                    money_text(amount) if amount else "",
                    freq,
                    str(row.get("notes", "") or ""),
                    "Yes" if str(row.get("status", "") or "active").lower() != "inactive" else "No",
                ])
        income_title = _template_sheet_title("income")
        outflows_title = _template_sheet_title("outflows")
        _ensure_template_sheet(service, template_id, income_title, income_headers)
        _ensure_template_sheet(service, template_id, outflows_title, outflow_headers)
        service.spreadsheets().values().update(
            spreadsheetId=template_id,
            range=f"'{income_title}'!A1:{sheet_col_letter(len(income_headers))}{len(income_values)}",
            valueInputOption="USER_ENTERED",
            body={"values": income_values},
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=template_id,
            range=f"'{outflows_title}'!A1:{sheet_col_letter(len(outflow_headers))}{len(outflow_values)}",
            valueInputOption="USER_ENTERED",
            body={"values": outflow_values},
        ).execute()
        st.session_state["spending_finance_template_id"] = template_id
        return True, f"{file_msg} Populated it with your current Spending Plan data.", template_url
    except Exception as exc:
        return False, f"Could not populate the Pathmark Finance Template: {exc}", ""


def _active_from_template(value: Any) -> str:
    text = str(value or "").strip().lower()
    return "inactive" if text in {"no", "n", "false", "0", "inactive", "archive", "archived"} else "active"


def _records_from_spending_template(template_sheet_id: str) -> tuple[bool, str, dict[str, list[dict[str, Any]]]]:
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session.", {}
    template_sheet_id = extract_google_sheet_id(template_sheet_id)
    if not template_sheet_id:
        return False, "Create the Pathmark Finance Template first, then edit it and import it back.", {}
    try:
        income_title = _template_sheet_title("income")
        outflows_title = _template_sheet_title("outflows")
        income_values = service.spreadsheets().values().get(spreadsheetId=template_sheet_id, range=f"'{income_title}'!A1:E").execute().get("values", [])
        outflow_values = service.spreadsheets().values().get(spreadsheetId=template_sheet_id, range=f"'{outflows_title}'!A1:G").execute().get("values", [])
        records = {"spending_income": [], "spending_expenses": []}
        for row in income_values[1:]:
            row = list(row) + [""] * (5 - len(row))
            source, amount_raw, freq, notes, active = row[:5]
            source = str(source or "").strip()
            amount = money_value(amount_raw)
            if not source and amount <= 0:
                continue
            vals = amount_columns_for_frequency(amount, str(freq or "Weekly"), include_quarterly=False)
            records["spending_income"].append({
                "income_id": f"income-{uuid.uuid4().hex[:10]}",
                "category": source or "Income",
                **vals,
                "annual_amount": str(annualise_amount(amount, str(freq or "Weekly"))),
                "notes": str(notes or ""),
                "status": _active_from_template(active),
                "source": "Pathmark Finance Template import",
            })
        for row in outflow_values[1:]:
            row = list(row) + [""] * (7 - len(row))
            item, kind_label, bucket, amount_raw, freq, notes, active = row[:7]
            item = str(item or "").strip()
            amount = money_value(amount_raw)
            if not item and amount <= 0:
                continue
            kind = normalise_spending_kind(kind_label)
            vals = amount_columns_for_frequency(amount, str(freq or spending_default_frequency(kind)), include_quarterly=True)
            records["spending_expenses"].append({
                "expense_id": f"expense-{uuid.uuid4().hex[:10]}",
                "expense_kind": kind,
                "group_name": str(bucket or spending_bucket_label(kind)).strip() or spending_bucket_label(kind),
                "item": item or "Spending item",
                **vals,
                "annual_amount": str(annualise_amount(amount, str(freq or spending_default_frequency(kind)))),
                "notes": str(notes or ""),
                "status": _active_from_template(active),
                "source": "Pathmark Finance Template import",
            })
        return True, "Read the Pathmark Finance Template.", records
    except Exception as exc:
        return False, f"Could not read the Pathmark Finance Template. Create it first, then try again. Details: {exc}", {}


def _clear_spending_table_rows(service: Any, sheet_id: str, table: str) -> None:
    columns = ONLINE_TABLES.get(table, [])
    if columns:
        service.spreadsheets().values().clear(spreadsheetId=sheet_id, range=f"{table}!A2:{sheet_col_letter(len(columns))}").execute()


def import_spending_plan_template(sheet_id: str, template_sheet_id: str, mode: str = "merge") -> tuple[bool, str]:
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session."
    sheet_id = extract_google_sheet_id(sheet_id)
    template_sheet_id = extract_google_sheet_id(template_sheet_id or _finance_template_session_id())
    if not template_sheet_id:
        found, found_id, _url = _find_existing_finance_template()
        template_sheet_id = found_id if found else ""
    ok, msg, records = _records_from_spending_template(template_sheet_id)
    if not ok:
        return False, msg
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        ok_backup, backup_msg = _create_spending_backup_tabs(service, sheet_id)
        if not ok_backup:
            return False, backup_msg
        if mode == "clean":
            _clear_spending_table_rows(service, sheet_id, "spending_income")
            _clear_spending_table_rows(service, sheet_id, "spending_expenses")
            clear_online_cache(sheet_id)
            ok_append, append_msg = append_many_online_records(sheet_id, records)
            return ok_append, (backup_msg + "\n" + append_msg if ok_append else append_msg)
        # Merge mode: update matching named rows where possible, append the rest.
        existing_income = active_online_df(read_online_table(sheet_id, "spending_income"))
        existing_expenses = active_online_df(read_online_table(sheet_id, "spending_expenses"))
        append_records = {"spending_income": [], "spending_expenses": []}
        updated = 0
        for record in records.get("spending_income", []):
            key = str(record.get("category", "") or "").strip().lower()
            match = existing_income[existing_income.get("category", pd.Series(dtype=str)).fillna("").astype(str).str.strip().str.lower().eq(key)] if not existing_income.empty else pd.DataFrame()
            if not match.empty:
                rid = str(match.iloc[0].get("income_id", "") or "")
                update = {k: v for k, v in record.items() if k != "income_id"}
                ok_update, _ = update_online_record(sheet_id, "spending_income", rid, update)
                updated += 1 if ok_update else 0
            else:
                append_records["spending_income"].append(record)
        for record in records.get("spending_expenses", []):
            key_kind = normalise_spending_kind(record.get("expense_kind", ""))
            key_group = str(record.get("group_name", "") or "").strip().lower()
            key_item = str(record.get("item", "") or "").strip().lower()
            if not existing_expenses.empty:
                match = existing_expenses[
                    existing_expenses.get("expense_kind", pd.Series(dtype=str)).apply(normalise_spending_kind).eq(key_kind)
                    & existing_expenses.get("group_name", pd.Series(dtype=str)).fillna("").astype(str).str.strip().str.lower().eq(key_group)
                    & existing_expenses.get("item", pd.Series(dtype=str)).fillna("").astype(str).str.strip().str.lower().eq(key_item)
                ]
            else:
                match = pd.DataFrame()
            if not match.empty:
                rid = str(match.iloc[0].get("expense_id", "") or "")
                update = {k: v for k, v in record.items() if k != "expense_id"}
                ok_update, _ = update_online_record(sheet_id, "spending_expenses", rid, update)
                updated += 1 if ok_update else 0
            else:
                append_records["spending_expenses"].append(record)
        ok_append, append_msg = append_many_online_records(sheet_id, append_records)
        clear_online_cache(sheet_id)
        total_new = len(append_records["spending_income"]) + len(append_records["spending_expenses"])
        return ok_append, f"{backup_msg}\nImported from Pathmark Finance Template: updated {updated} existing row(s) and added {total_new} new row(s)."
    except Exception as exc:
        return False, f"Could not import the Pathmark Finance Template: {exc}"


def render_spending_template_tools(sheet_id: str) -> None:
    st.markdown("#### Template import")
    st.write(
        "Create a separate **Pathmark Finance Template** Google Sheet from your current Spending Plan, edit income and outflows in that sheet, then import it back into Pathmark."
    )
    st.caption("Imports create backup tabs in your Pathmark Sync sheet first. Clean import replaces current income and outflow rows; merge import updates matching rows and adds new ones.")
    if st.button("Create / refresh Pathmark Finance Template", use_container_width=True):
        ok, msg, url = create_spending_plan_template(sheet_id)
        if ok:
            st.session_state["spending_finance_template_url"] = url
            st.success(msg)
        else:
            st.warning(safe_user_message(msg))

    template_id = _finance_template_session_id()
    template_url = str(st.session_state.get("spending_finance_template_url", "") or "")
    if not template_id:
        found, found_id, found_url = _find_existing_finance_template()
        if found:
            template_id = found_id
            template_url = found_url
            st.session_state["spending_finance_template_url"] = found_url
    if template_id:
        st.link_button("Open Pathmark Finance Template in Google Sheets", template_url or f"https://docs.google.com/spreadsheets/d/{template_id}/edit", use_container_width=True)
    else:
        st.info("Create the template first. Pathmark will populate it with the income and outflow rows you have already entered.")

    mode = st.radio("Import mode", ["Merge/update existing data", "Clean import: replace current income and outflows"], horizontal=False)
    confirm = st.checkbox("I understand Pathmark will create backup tabs in Pathmark Sync before importing.")
    if st.button("Import from Pathmark Finance Template", use_container_width=True, disabled=not confirm):
        import_mode = "clean" if mode.startswith("Clean") else "merge"
        ok, msg = import_spending_plan_template(sheet_id, template_id, import_mode)
        if ok:
            spending_save_and_refresh(msg)
        else:
            st.warning(safe_user_message(msg))


PROJECTION_ACCOUNT_NAMES = {
    "debt": "Projection — Debt payoff",
    "emergency": "Account 3 — Emergency savings",
    "savings": "Account 5 — Debt reduction or savings goals",
}

PROJECTION_ACCOUNT_ROLE_NAMES = [
    "Account 1 — Hub account",
    "Account 2 — Everyday card account",
    "Account 3 — Emergency savings",
    "Account 4 — Gifts, holidays, clothes and Christmas",
    "Account 5 — Debt reduction or savings goals",
]

DEBT_PROJECTION_NAME = "Projection — Debt payoff"


def _account_rows_by_name(sheet_id: str) -> dict[str, pd.Series]:
    accounts = active_online_df(read_online_table(sheet_id, "spending_accounts"))
    out: dict[str, pd.Series] = {}
    if accounts.empty or "account_name" not in accounts.columns:
        return out
    for _, row in accounts.iterrows():
        name = str(row.get("account_name", "") or "").strip()
        if name:
            out[name] = row
    return out


def _projection_row(sheet_id: str, key: str) -> pd.Series | None:
    return _account_rows_by_name(sheet_id).get(PROJECTION_ACCOUNT_NAMES[key])


def _projection_value(row: pd.Series | None, column: str, default: float = 0.0) -> float:
    if row is None:
        return default
    return money_value(row.get(column, default))


def _upsert_spending_account_by_name(sheet_id: str, account_name: str, updates: dict[str, Any]) -> tuple[bool, str]:
    accounts = active_online_df(read_online_table(sheet_id, "spending_accounts"))
    now = utc_now_text()
    if not accounts.empty and "account_name" in accounts.columns:
        matches = accounts[accounts["account_name"].fillna("").astype(str).str.strip().str.lower().eq(account_name.strip().lower())]
        if not matches.empty:
            record_id = str(matches.iloc[0].get("account_id", "") or "").strip()
            updates = {**updates, "updated_at": now, "status": "active"}
            return update_online_record(sheet_id, "spending_accounts", record_id, updates)
    record = {
        "account_id": f"account-{uuid.uuid4().hex[:12]}",
        "account_name": account_name,
        "purpose": updates.get("purpose", "Spending Plan projection."),
        "bank": updates.get("bank", ""),
        "account_number_hint": updates.get("account_number_hint", ""),
        "transfer_per_week": updates.get("transfer_per_week", "0"),
        "target_balance": updates.get("target_balance", "0"),
        "current_balance": updates.get("current_balance", "0"),
        "notes": updates.get("notes", ""),
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "source": updates.get("source", "Spending Plan projections"),
    }
    return append_online_record(sheet_id, "spending_accounts", record)


def _payday_date_from_settings(sheet_id: str, weeks_from_now: int) -> date:
    today = _today_nz()
    day_name = online_setting(sheet_id, "spending_pay_day", "Monday").strip().title() or "Monday"
    weekday_lookup = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    target = weekday_lookup.get(day_name, 0)
    days_until = (target - today.weekday()) % 7
    first_pay_day = today + timedelta(days=days_until)
    return first_pay_day + timedelta(weeks=max(int(weeks_from_now or 0), 0))


def _projection_weeks_to_target(kind: str, current: float, target: float, weekly: float) -> int | None:
    weekly = float(weekly or 0.0)
    if weekly <= 0.005:
        return None
    if kind == "debt":
        remaining = max(float(current or 0.0), 0.0)
    else:
        remaining = max(float(target or 0.0) - float(current or 0.0), 0.0)
    if remaining <= 0.005:
        return 0
    import math
    return int(math.ceil(remaining / weekly))


def _projection_summary(sheet_id: str) -> dict[str, Any]:
    summary = spending_summary(sheet_id)
    surplus_weekly = max(float(summary.get("surplus_weekly", 0.0) or 0.0), 0.0)
    rows = _account_rows_by_name(sheet_id)
    debt_row = rows.get(DEBT_PROJECTION_NAME)
    emergency_row = rows.get("Account 3 — Emergency savings") or rows.get(PROJECTION_ACCOUNT_NAMES["emergency"])
    savings_row = rows.get("Account 5 — Debt reduction or savings goals") or rows.get(PROJECTION_ACCOUNT_NAMES["savings"])
    debt_balance = _projection_value(debt_row, "current_balance", 0.0)
    debt_weekly = _projection_value(debt_row, "transfer_per_week", 0.0)
    emergency_current = _projection_value(emergency_row, "current_balance", 0.0)
    emergency_target = _projection_value(emergency_row, "target_balance", float(summary.get("emergency_target", 0.0) or 0.0))
    emergency_weekly = _projection_value(emergency_row, "transfer_per_week", 0.0)
    savings_current = _projection_value(savings_row, "current_balance", 0.0)
    savings_target = _projection_value(savings_row, "target_balance", 0.0)
    savings_weekly = _projection_value(savings_row, "transfer_per_week", 0.0)
    return {
        "surplus_weekly": surplus_weekly,
        "debt_balance": debt_balance,
        "debt_weekly": debt_weekly,
        "debt_weeks": _projection_weeks_to_target("debt", debt_balance, 0.0, debt_weekly),
        "emergency_current": emergency_current,
        "emergency_target": emergency_target,
        "emergency_weekly": emergency_weekly,
        "emergency_weeks": _projection_weeks_to_target("emergency", emergency_current, emergency_target, emergency_weekly),
        "savings_current": savings_current,
        "savings_target": savings_target,
        "savings_weekly": savings_weekly,
        "savings_weeks": _projection_weeks_to_target("savings", savings_current, savings_target, savings_weekly),
        "pay_day": online_setting(sheet_id, "spending_pay_day", "Monday").strip().title() or "Monday",
        "pay_frequency": online_setting(sheet_id, "spending_pay_frequency", "Weekly").strip().title() or "Weekly",
    }


def render_projection_card(title: str, current: float, target: float, weekly: float, weeks: int | None, sheet_id: str, kind: str) -> None:
    if kind == "debt":
        total = max(current, 0.0)
        done = 0.0 if total else 0.0
        headline = f"{money_text(max(current, 0.0))} remaining"
    else:
        total = max(target, 0.0)
        done = min(max(current, 0.0), total) if total else 0.0
        headline = f"{money_text(current)} of {money_text(target)} saved"
    percent = int(round((done / total) * 100)) if total > 0 else 0
    if weeks is None:
        date_line = "Add a weekly amount to project a date."
    elif weeks <= 0:
        date_line = "Target already reached."
    else:
        projected = _payday_date_from_settings(sheet_id, weeks)
        date_line = f"About {weeks} week{'s' if weeks != 1 else ''} — around {projected.strftime('%d/%m/%Y')}."
    st.markdown(f"""
    <div class="card projection-card">
      <div class="kicker">{html.escape(title)}</div>
      <h3>{html.escape(headline)}</h3>
      <p>{html.escape(date_line)}</p>
      <div class="progress-summary"><div class="progress-head percent-only"><span></span><span>{percent}%</span></div><div class="progress-track"><div class="progress-fill" style="width:{max(min(percent,100),0)}%;"></div></div></div>
      <div class="pillar-foot">Weekly allocation: {html.escape(money_text(weekly))}</div>
    </div>
    """, unsafe_allow_html=True)


def render_spending_projections(sheet_id: str) -> None:
    st.markdown("#### Projections")
    st.write(
        "Use balances and targets to estimate how long debt, emergency savings and savings goals may take if the Spending Plan is followed. Income and planned outflows are pulled from the Income, Spending and APs tabs."
    )
    st.caption("These are budgeting estimates only. They are based on the figures you enter and are not financial advice.")
    summary = spending_summary(sheet_id)
    available = max(float(summary.get("surplus_weekly", 0.0) or 0.0), 0.0)
    shortfall = float(summary.get("surplus_weekly", 0.0) or 0.0) < -0.005
    if shortfall:
        st.warning("Your planned outflows are higher than income. Projections are paused until the plan has money available to allocate.")
    else:
        st.info(f"Current money available to allocate from the Assessment tab: **{money_text(available)} / week**.")

    proj = _projection_summary(sheet_id)
    day_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    frequency_options = ["Weekly", "Fortnightly", "Monthly"]
    accounts = _account_rows_by_name(sheet_id)

    st.markdown("##### Pay timing")
    with st.form("spending_projection_payday_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        pay_frequency = c1.selectbox("Pay frequency", frequency_options, index=frequency_options.index(proj.get("pay_frequency", "Weekly")) if proj.get("pay_frequency", "Weekly") in frequency_options else 0, key="spending_projection_pay_frequency")
        pay_day = c2.selectbox("Pay day money arrives in the hub account", day_options, index=day_options.index(proj.get("pay_day", "Monday")) if proj.get("pay_day", "Monday") in day_options else 0, key="spending_projection_pay_day")
        save_payday = st.form_submit_button("Save pay timing", use_container_width=True)
    if save_payday:
        ok1, msg1 = save_online_setting(sheet_id, "spending_pay_frequency", pay_frequency, source="spending_projections")
        ok2, msg2 = save_online_setting(sheet_id, "spending_pay_day", pay_day, source="spending_projections")
        if ok1 and ok2:
            spending_save_and_refresh("Saved projection pay timing.")
        else:
            st.warning("Could not save pay timing: " + "; ".join([safe_user_message(m) for ok,m in [(ok1,msg1),(ok2,msg2)] if not ok]))

    st.markdown("##### Account balances")
    st.caption("These are optional. Enter the current balances of the five Spending Plan account roles, plus any separate debt balance if relevant.")
    with st.form("spending_projection_balances_form", clear_on_submit=False):
        balance_values: dict[str, float] = {}
        target_values: dict[str, float] = {}
        transfer_values: dict[str, float] = {}
        for account_name in PROJECTION_ACCOUNT_ROLE_NAMES:
            row = accounts.get(account_name)
            st.markdown(f"**{account_name}**")
            b1, b2, b3 = st.columns(3)
            balance_values[account_name] = b1.number_input(f"Current balance — {account_name}", min_value=0.0, step=50.0, value=_projection_value(row, "current_balance", 0.0), format="%.2f", key=f"proj_balance_{account_name}")
            target_default = _projection_value(row, "target_balance", float(summary.get("emergency_target", 0.0) or 0.0) if "Emergency" in account_name else 0.0)
            target_values[account_name] = b2.number_input(f"Target balance — {account_name}", min_value=0.0, step=50.0, value=target_default, format="%.2f", key=f"proj_target_{account_name}")
            transfer_default = _projection_value(row, "transfer_per_week", float(summary.get("surplus_weekly", 0.0) or 0.0) if "Debt reduction" in account_name else 0.0)
            transfer_values[account_name] = b3.number_input(f"Weekly transfer — {account_name}", min_value=0.0, step=10.0, value=max(transfer_default, 0.0), format="%.2f", key=f"proj_transfer_{account_name}")
        st.markdown("**Separate debt balance**")
        debt_row = accounts.get(DEBT_PROJECTION_NAME)
        d1, d2 = st.columns(2)
        debt_balance = d1.number_input("Current debt balance", min_value=0.0, step=100.0, value=_projection_value(debt_row, "current_balance", 0.0), format="%.2f", key="spending_projection_debt_balance")
        debt_weekly = d2.number_input("Weekly debt repayment from available money", min_value=0.0, step=10.0, value=_projection_value(debt_row, "transfer_per_week", 0.0), format="%.2f", key="spending_projection_debt_weekly")
        total_allocated = sum(transfer_values.values()) + debt_weekly
        st.caption(f"Weekly projection allocations: {money_text(total_allocated)}. Current available to allocate: {money_text(available)}.")
        save_balances = st.form_submit_button("Save balances and projection amounts", use_container_width=True)
    if save_balances:
        warnings = []
        if not shortfall and total_allocated > available + 0.005:
            warnings.append("Projection allocations are higher than the current money available to allocate. Pathmark will save them, but the estimate assumes you can actually fund those amounts.")
        failures = []
        for account_name in PROJECTION_ACCOUNT_ROLE_NAMES:
            updates = {
                "current_balance": str(balance_values[account_name]),
                "target_balance": str(target_values[account_name]),
                "transfer_per_week": str(transfer_values[account_name]),
                "notes": "Balance and target updated from Spending Plan projections.",
                "source": "Spending Plan projections",
            }
            ok, msg = _upsert_spending_account_by_name(sheet_id, account_name, updates)
            if not ok:
                failures.append(safe_user_message(msg))
        ok_debt, msg_debt = _upsert_spending_account_by_name(sheet_id, DEBT_PROJECTION_NAME, {"purpose": "Projected debt payoff based on the weekly amount entered.", "current_balance": str(debt_balance), "target_balance": "0", "transfer_per_week": str(debt_weekly), "notes": "Budgeting estimate only.", "source": "Spending Plan projections"})
        if not ok_debt:
            failures.append(safe_user_message(msg_debt))
        if failures:
            st.warning("Some projection settings could not be saved: " + "; ".join(failures[:3]))
        else:
            if warnings:
                st.warning(" ".join(warnings))
            spending_save_and_refresh("Saved Spending Plan balances and projections.")

    proj = _projection_summary(sheet_id)
    st.markdown("#### Estimated pathway")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_projection_card("Debt payoff", proj["debt_balance"], max(proj["debt_balance"], 0.0), proj["debt_weekly"], proj["debt_weeks"], sheet_id, "debt")
    with c2:
        render_projection_card("Emergency fund", proj["emergency_current"], proj["emergency_target"], proj["emergency_weekly"], proj["emergency_weeks"], sheet_id, "emergency")
    with c3:
        render_projection_card("Savings goal", proj["savings_current"], proj["savings_target"], proj["savings_weekly"], proj["savings_weeks"], sheet_id, "savings")

def render_spending_records(sheet_id: str) -> None:
    st.markdown("#### Spending Plan records")
    st.caption("These are the live rows in your Pathmark Sync sheet. Use this tab for checking what has been saved.")
    tables = [
        ("Income", "spending_income", ["category", "weekly_amount", "fortnightly_amount", "monthly_amount", "yearly_amount", "annual_amount", "notes", "status"]),
        ("Spending", "spending_expenses", ["expense_kind", "group_name", "item", "weekly_amount", "fortnightly_amount", "monthly_amount", "quarterly_amount", "yearly_amount", "annual_amount", "notes", "status"]),
        ("Account roles", "spending_accounts", ["account_name", "purpose", "bank", "account_number_hint", "transfer_per_week", "target_balance", "current_balance", "notes", "status"]),
    ]
    for label, table, columns in tables:
        with st.expander(label, expanded=(label != "Account roles")):
            df = active_online_df(read_online_table(sheet_id, table))
            if df.empty:
                st.info(f"No {label.lower()} records yet.")
            else:
                dataframe_preview(df, columns)


def render_spending_plan_manager(sheet_id: str) -> None:
    try:
        ensure_spending_plan_default_rows(sheet_id)
    except Exception as exc:
        st.warning("Pathmark could not check Spending Plan starter rows just now, but the Spending Plan can still open.")
        user = current_user() if 'current_user' in globals() else {}
        role, status = resolve_role(user.get("email", ""), bool(user.get("email_verified", False))) if user else ("", "")
        if role_can_develop(role, status):
            with st.expander("Developer details", expanded=False):
                st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip())
    if st.session_state.get("spending_notice"):
        st.success(st.session_state.pop("spending_notice"))

    st.caption("Set up income and outflows once, then use Assessment for a calm money-flow summary.")
    section_options = ["Assessment", "Income", "Spending", "APs", "Projections", "Template", "Records"]

    def _render_spending_summary_strip() -> None:
        summary = spending_summary(sheet_id)
        surplus = float(summary.get("surplus_weekly", 0.0) or 0.0)
        result_label = "Shortfall / week" if surplus < -0.005 else "Available to allocate / week"
        result_value = abs(surplus) if surplus < -0.005 else surplus
        st.markdown(f"""
        <div class="metric-strip">
          <div class="metric-tile"><div class="metric-label">Income / week</div><div class="metric-value">{html.escape(money_text(summary['income_weekly']))}</div></div>
          <div class="metric-tile"><div class="metric-label">Outflows / week</div><div class="metric-value">{html.escape(money_text(summary['expense_weekly']))}</div></div>
          <div class="metric-tile"><div class="metric-label">Suggested APs / week</div><div class="metric-value">{html.escape(money_text(summary['fixed_weekly'] + summary['sinking_weekly']))}</div></div>
          <div class="metric-tile {'warning' if surplus < -0.005 else ''}"><div class="metric-label">{result_label}</div><div class="metric-value">{html.escape(money_text(result_value))}</div></div>
        </div>
        """, unsafe_allow_html=True)

    def _spending_piece(label: str, body_func, *, summary: bool = True) -> None:
        try:
            if summary:
                _render_spending_summary_strip()
            body_func(sheet_id)
        except Exception as exc:
            st.warning(f"Pathmark could not open the {label} part of Spending Plan just now. The other tabs should still work.")
            user = current_user() if 'current_user' in globals() else {}
            role, status = resolve_role(user.get("email", ""), bool(user.get("email_verified", False))) if user else ("", "")
            if role_can_develop(role, status):
                with st.expander("Developer details", expanded=False):
                    st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip())

    choice = st.radio("Finance section", section_options, horizontal=True, label_visibility="collapsed", key="finance_section_select")
    dispatch = {
        "Assessment": (render_spending_assessment, False),
        "Income": (render_spending_income_form, True),
        "Spending": (render_spending_expense_form, True),
        "APs": (render_spending_account_form, True),
        "Projections": (render_spending_projections, True),
        "Template": (render_spending_template_tools, True),
        "Records": (render_spending_records, True),
    }
    body_func, show_summary = dispatch.get(choice, (render_spending_assessment, False))
    _spending_piece(choice, body_func, summary=show_summary)

def fallback_staged_tasklist(sheet_id: str) -> pd.DataFrame:
    """Build a simple tasklist directly from actions if the richer tasklist builder fails."""
    cols = ["action_id", "source_type", "title", "display_title", "area_name", "parent", "status", "scheduled_date", "due_date", "first_step", "estimated_minutes", "item_type", "parent_progress_item_id", "parent_progress_title", "calendar_start_time", "calendar_end_time", "calendar_end_date", "notes", "priority"]
    try:
        actions = read_online_table(sheet_id, "actions")
        if actions is None or actions.empty:
            return pd.DataFrame(columns=cols)
        rows = []
        for _, a in actions.iterrows():
            if not truthy_flag(a.get("include_tasklist", "1")):
                continue
            title = str(a.get("title", "") or "").strip()
            if not title:
                continue
            item_type = str(a.get("item_type", "") or "")
            is_support = is_supporting_project_action(a)
            rows.append({
                "action_id": str(a.get("action_id", "") or ""),
                "source_type": "Routine activity" if str(a.get("routine_id", "") or "").strip() else "Goal action",
                "title": title,
                "display_title": title,
                "area_name": str(a.get("area_name", "") or ""),
                "parent": str(a.get("goal_id", "") or a.get("routine_id", "") or "Unlinked"),
                "status": str(a.get("status", "") or "Planned"),
                "scheduled_date": str(a.get("scheduled_date", "") or ""),
                "due_date": str(a.get("due_date", "") or ""),
                "first_step": str(a.get("first_step", "") or ""),
                "estimated_minutes": str(a.get("estimated_minutes", "") or ""),
                "item_type": item_type,
                "parent_progress_item_id": str(a.get("parent_progress_item_id", "") or ""),
                "parent_progress_title": "",
                "calendar_start_time": str(a.get("calendar_start_time", "") or ""),
                "calendar_end_time": str(a.get("calendar_end_time", "") or ""),
                "calendar_end_date": str(a.get("calendar_end_date", "") or ""),
                "notes": str(a.get("notes", "") or a.get("description", "") or ""),
                "priority": str(a.get("priority", "") or ""),
            })
        return pd.DataFrame(rows, columns=cols)
    except Exception:
        return pd.DataFrame(columns=cols)


def render_tasklist_manager(sheet_id: str) -> None:
    st.subheader("Tasklist")
    st.write("Use this as a printable paper copy. Google Sync is the main working sync for Google Calendar and Google Tasks.")

    base_columns = ["action_id", "source_type", "title", "display_title", "area_name", "parent", "status", "scheduled_date", "due_date", "first_step", "estimated_minutes", "item_type", "parent_progress_item_id", "parent_progress_title", "calendar_start_time", "calendar_end_time", "calendar_end_date", "notes", "priority"]

    def _safe_tasklist_dataframe() -> pd.DataFrame:
        try:
            df = staged_tasklist(sheet_id)
        except Exception as exc:
            try:
                df = fallback_staged_tasklist(sheet_id)
            except Exception:
                df = pd.DataFrame(columns=base_columns)
            st.warning("Pathmark opened a simplified printable tasklist view because the richer tasklist builder could not be loaded.")
            user = current_user() if 'current_user' in globals() else {}
            role, status = resolve_role(user.get("email", ""), bool(user.get("email_verified", False))) if user else ("", "")
            if role_can_develop(role, status):
                with st.expander("Developer details", expanded=False):
                    st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip())
        if df is None:
            df = pd.DataFrame(columns=base_columns)
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        for col in base_columns:
            if col not in df.columns:
                df[col] = ""
        return df[base_columns + [c for c in df.columns if c not in base_columns]].copy()

    try:
        tasklist = _safe_tasklist_dataframe()
    except Exception:
        tasklist = pd.DataFrame(columns=base_columns)

    if tasklist.empty:
        st.info("No tasklist rows yet. Add project steps or routine activities; Pathmark will stage printable tasklist rows automatically.")
        return

    title = "Weekly Tasklist"
    notes = ""
    selected_action_ids: list[str] = []
    st.session_state["tasklist_render_instance"] = int(st.session_state.get("tasklist_render_instance", 0)) + 1
    tasklist_key_prefix = f"tasklist_{st.session_state['tasklist_render_instance']}"

    try:
        with st.expander("Choose what goes on the tasklist", expanded=True):
            title = st.text_input("Tasklist name", value="Weekly Tasklist", help="This appears at the top of the printable tasklist.", key=f"{tasklist_key_prefix}_print_title")
            notes = st.text_area("Optional notes for the printed tasklist", height=80, help="Add one note per line. These are appended to the end of the tasklist.", key=f"{tasklist_key_prefix}_print_notes")
            source_series = tasklist["source_type"].fillna("").astype(str) if "source_type" in tasklist.columns else pd.Series([""] * len(tasklist), index=tasklist.index)
            goal_actions = tasklist[source_series == "Goal action"].copy()
            routine_rows = tasklist[source_series == "Routine activity"].copy()

            def _render_checkbox_rows(rows_df: pd.DataFrame, prefix: str) -> None:
                if rows_df.empty:
                    return
                try:
                    groups = rows_df.groupby(rows_df.get("parent", pd.Series("Unlinked", index=rows_df.index)).fillna("Unlinked"), sort=False)
                except Exception:
                    groups = [("Unlinked", rows_df)]
                for parent, group in groups:
                    parent_label = str(parent or "Unlinked").strip() or "Unlinked"
                    st.markdown(f"**{html.escape(parent_label)}**")
                    for _, row in group.iterrows():
                        action_id = str(row.get("action_id", "") or row.name)
                        title_text = str(row.get("display_title", "") or row.get("title", "Untitled") or "Untitled")
                        is_support = _tasklist_is_supporting_row(row)
                        label_bits = []
                        scheduled = str(row.get("scheduled_date", "") or "").strip()
                        due = str(row.get("due_date", "") or "").strip()
                        if scheduled:
                            label_bits.append(f"scheduled {_tasklist_human_date(scheduled)}")
                        if due and due != scheduled:
                            label_bits.append(f"due {_tasklist_human_date(due)}")
                        suffix = f" ({'; '.join(label_bits)})" if label_bits else ""
                        label = f"{title_text}{suffix}"
                        if is_support:
                            spacer, check_col = st.columns([0.08, 0.92])
                            with check_col:
                                checked = st.checkbox(label, value=False, key=f"tasklist_{prefix}_{action_id}_{row.name}")
                        else:
                            checked = st.checkbox(label, value=False, key=f"tasklist_{prefix}_{action_id}_{row.name}")
                        if checked:
                            selected_action_ids.append(action_id)

            if not goal_actions.empty:
                st.markdown("#### Project work")
                _render_checkbox_rows(goal_actions, "goal")
            if not routine_rows.empty:
                st.markdown("#### Routine activities")
                _render_checkbox_rows(routine_rows, "routine")
    except Exception as exc:
        st.warning("Pathmark could not render the grouped selector, so it is showing a simple selector instead.")
        user = current_user() if 'current_user' in globals() else {}
        role, status = resolve_role(user.get("email", ""), bool(user.get("email_verified", False))) if user else ("", "")
        if role_can_develop(role, status):
            with st.expander("Developer details", expanded=False):
                st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip())
        for _, row in tasklist.iterrows():
            action_id = str(row.get("action_id", "") or row.name)
            title_text = str(row.get("display_title", "") or row.get("title", "Untitled") or "Untitled")
            if st.checkbox(title_text, value=False, key=f"tasklist_simple_{action_id}_{row.name}"):
                selected_action_ids.append(action_id)

    if selected_action_ids and "action_id" in tasklist.columns:
        action_series = tasklist["action_id"].fillna("").astype(str)
        selected_rows = tasklist[action_series.isin(selected_action_ids)].copy()
    else:
        selected_rows = pd.DataFrame(columns=tasklist.columns)

    if selected_rows.empty:
        st.info("Tick at least one action or activity before downloading the tasklist.")
    else:
        st.markdown("### Preview")
        try:
            preview = selected_rows.copy()
            preview["notes_preview"] = preview.apply(tasklist_notes_text, axis=1).astype(str).str.replace("<br/>", " · ", regex=False)
            dataframe_preview(preview, ["source_type", "display_title", "notes_preview", "status"])
        except Exception:
            st.dataframe(selected_rows[[c for c in ["source_type", "display_title", "title", "status"] if c in selected_rows.columns]], use_container_width=True, hide_index=True)

    try:
        pdf_bytes = build_tasklist_pdf(selected_rows, title=title or "Pathmark Tasklist", notes=notes)
        mime = "application/pdf"
        filename = "pathmark_tasklist.pdf"
    except Exception:
        pdf_bytes = build_printable_tasklist_from_rows(selected_rows)
        mime = "text/plain"
        filename = "pathmark_tasklist.txt"

    st.download_button("Download printable tasklist", data=pdf_bytes, file_name=filename, mime=mime, use_container_width=True, disabled=selected_rows.empty and not str(notes or "").strip(), key=f"{tasklist_key_prefix}_print_download")

    if not selected_rows.empty:
        with st.expander("After printing or saving"):
            st.write("Printing or saving a tasklist does not move items to Archive. Project steps and routine activities remain in their Projects or Routines tabs until you pause or archive them deliberately.")
            if st.button("Mark selected rows as exported", use_container_width=True, key=f"{tasklist_key_prefix}_mark_selected_exported"):
                ids = selected_rows.get("action_id", pd.Series(dtype=str)).dropna().astype(str).tolist()
                ok, message = mark_actions_exported(sheet_id, ids, "paper_tasklist", archive=False)
                if ok:
                    st.success(message)
                else:
                    st.warning(safe_user_message(message))
                st.rerun()

def _parse_calendar_block_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    # Google Calendar often returns RFC3339 strings with an offset or Z. Parse
    # those before trying fixed-width local formats, otherwise a UTC value such
    # as 2026-06-06T21:00:00Z can be misread as a local 21:00 event.
    try:
        if "T" in raw and (raw.endswith("Z") or re.search(r"[+-]\d\d:?\d\d$", raw)):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(raw[:19] if fmt.endswith(":%S") else raw[:16], fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None



def _pathmark_nz_timezone():
    if ZoneInfo is not None:
        return ZoneInfo("Pacific/Auckland")
    return timezone(timedelta(hours=12))


def _calendar_value_to_nz_naive(value: Any) -> datetime | None:
    dt = _parse_calendar_block_datetime(value)
    if dt is None:
        return None
    nz_tz = _pathmark_nz_timezone()
    try:
        if dt.tzinfo is not None:
            dt = dt.astimezone(nz_tz).replace(tzinfo=None)
    except Exception:
        try:
            dt = dt.replace(tzinfo=None)
        except Exception:
            pass
    return dt.replace(second=0, microsecond=0)


def _calendar_key_from_any(value: Any) -> str:
    dt = _calendar_value_to_nz_naive(value)
    if dt is not None:
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(value or "")[:16].replace("T", " ")

def _google_calendar_datetime_body(value: Any) -> dict[str, str]:
    dt = _parse_calendar_block_datetime(value)
    if dt is None:
        dt = datetime.now().replace(second=0, microsecond=0)
    # Google Calendar expects RFC3339 datetimes. Provide an explicit NZ
    # timezone offset as well as the named timezone so one-off and recurring
    # events are accepted consistently.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_pathmark_nz_timezone())
    return {"dateTime": dt.isoformat(timespec="seconds"), "timeZone": "Pacific/Auckland"}


def get_or_create_pathmark_calendar(title: str = "Pathmark") -> tuple[bool, str, str]:
    service = calendar_service()
    if service is None:
        return False, "", "Google Calendar access is not available for this session. Reconnect Google to enable Calendar sync."
    wanted = (title or "Pathmark").strip() or "Pathmark"
    try:
        token = None
        while True:
            result = service.calendarList().list(maxResults=250, pageToken=token).execute()
            for item in result.get("items", []) or []:
                if str(item.get("summary", "")).strip().lower() == wanted.lower():
                    return True, str(item.get("id", "")), f"Using existing Google Calendar: {wanted}."
            token = result.get("nextPageToken")
            if not token:
                break
        created = service.calendars().insert(body={"summary": wanted, "description": "Calendar time created by Pathmark."}).execute()
        return True, str(created.get("id", "")), f"Created Google Calendar: {wanted}."
    except Exception as exc:
        return False, "", f"Could not find or create the Google Calendar: {exc}"


def _google_calendar_colour_code_from_area(area: dict[str, str]) -> str:
    raw = str(area.get("colour", "") or area.get("google_calendar_colour_id", "") or "").strip()
    if not raw:
        return ""
    if raw.lower() in GOOGLE_COLOUR_BY_CODE_OR_NAME:
        label = GOOGLE_COLOUR_BY_CODE_OR_NAME.get(raw.lower(), "")
        return GOOGLE_COLOUR_BY_LABEL.get(label, {}).get("code", "")
    if raw in {code for code, _name, _hex in GOOGLE_CALENDAR_COLOURS}:
        return raw
    return str(area.get("google_calendar_colour_id", "") or "").strip()


def _maybe_apply_calendar_colour(service: Any, calendar_id: str, colour_code: str) -> None:
    if not colour_code:
        return
    try:
        service.calendarList().patch(calendarId=calendar_id, body={"colorId": str(colour_code)}).execute()
    except Exception:
        # Calendar colour support differs slightly between Google calendar/event palettes.
        # A failed colour update should not prevent event sync.
        pass


def get_or_create_area_calendar(sheet_id: str, area_name: str) -> tuple[bool, str, str]:
    """Create or reuse a Google Calendar named exactly after the Pathmark Area."""
    service = calendar_service()
    if service is None:
        return False, "", "Google Calendar access is not available for this session. Reconnect Google to enable Calendar sync."
    wanted = str(area_name or "").strip() or "Pathmark"
    area = area_defaults(sheet_id, wanted) if sheet_id else {}
    stored_id = str(area.get("google_calendar_id", "") or "").strip()
    colour_code = _google_calendar_colour_code_from_area(area)
    area_id = str(area.get("area_id", "") or "").strip()
    try:
        if stored_id:
            try:
                existing = service.calendarList().get(calendarId=stored_id).execute()
                _maybe_apply_calendar_colour(service, stored_id, colour_code)
                return True, stored_id, f"Using Area calendar: {existing.get('summary', wanted)}."
            except Exception:
                # Stored ID may be stale if the Google calendar was deleted. Fall through and re-find/create.
                pass
        token = None
        while True:
            result = service.calendarList().list(maxResults=250, pageToken=token).execute()
            for item in result.get("items", []) or []:
                if str(item.get("summary", "")).strip().lower() == wanted.lower():
                    calendar_id = str(item.get("id", "") or "")
                    _maybe_apply_calendar_colour(service, calendar_id, colour_code)
                    if area_id:
                        update_online_record(sheet_id, "areas", area_id, {"google_calendar_id": calendar_id, "google_calendar_name": wanted, "google_calendar_colour_id": colour_code, "google_calendar_synced_at": utc_now_text(), "default_calendar": wanted})
                    return True, calendar_id, f"Using Area calendar: {wanted}."
            token = result.get("nextPageToken")
            if not token:
                break
        created = service.calendars().insert(body={"summary": wanted, "description": f"Pathmark calendar time for the {wanted} Area."}).execute()
        calendar_id = str(created.get("id", "") or "")
        _maybe_apply_calendar_colour(service, calendar_id, colour_code)
        if area_id:
            update_online_record(sheet_id, "areas", area_id, {"google_calendar_id": calendar_id, "google_calendar_name": wanted, "google_calendar_colour_id": colour_code, "google_calendar_synced_at": utc_now_text(), "default_calendar": wanted})
        return True, calendar_id, f"Created Area calendar: {wanted}."
    except Exception as exc:
        return False, "", f"Could not find or create the Area calendar {wanted}: {exc}"


def _calendar_update_for_block(event: dict[str, Any], calendar_id: str, recurrence: str, sync_status: str) -> dict[str, str]:
    return {
        "google_calendar_id": calendar_id,
        "google_calendar_event_id": str(event.get("id", "") or ""),
        "google_calendar_status": str(event.get("status", "") or "confirmed"),
        "google_calendar_updated_at": str(event.get("updated", "") or ""),
        "google_calendar_synced_at": utc_now_text(),
        "google_calendar_recurrence": recurrence or "",
        "calendar_sync_status": sync_status,
    }


def _action_calendar_lookup(sheet_id: str) -> dict[str, dict[str, str]]:
    actions = read_online_table(sheet_id, "actions")
    lookup: dict[str, dict[str, str]] = {}
    if actions.empty:
        return lookup
    for _, row in actions.iterrows():
        aid = str(row.get("action_id", "") or "").strip()
        if aid:
            lookup[aid] = {k: str(row.get(k, "") or "") for k in actions.columns}
    return lookup



def _sync_error_detail(exc: Exception) -> str:
    """Return a useful but token-safe error message for Google API failures."""
    try:
        if hasattr(exc, "resp") and getattr(exc, "resp", None) is not None:
            status = getattr(exc.resp, "status", "")
            reason = getattr(exc.resp, "reason", "")
            content = getattr(exc, "content", b"")
            detail = ""
            if content:
                try:
                    payload = json.loads(content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else str(content))
                    detail = str(payload.get("error", {}).get("message", "") or payload.get("message", ""))
                except Exception:
                    detail = str(content)[:200]
            msg = " ".join(str(x) for x in [status, reason, detail] if str(x).strip())
            return safe_user_message(msg or str(exc))[:500]
    except Exception:
        pass
    return safe_user_message(str(exc))[:500]

def _google_calendar_event_body(block: pd.Series) -> dict[str, Any]:
    title = str(block.get("title", "Pathmark calendar time") or "Pathmark calendar time").strip()
    area = str(block.get("area_name", "") or "").strip()
    description = str(block.get("description", "") or "")
    linked = str(block.get("linked_record_id", "") or "")
    notes = [description]
    if area:
        notes.append(f"Area: {area}")
    if linked:
        notes.append(f"Pathmark linked record ID: {linked}")
    if truthy_flag(block.get("all_day", "")):
        start_d = parse_online_date(block.get("start")) or date.today()
        end_d = parse_online_date(block.get("end")) or start_d
        # Google Calendar all-day event end dates are exclusive. Pathmark stores
        # the user's finish date inclusively, so add one day for Google.
        body: dict[str, Any] = {
            "summary": title,
            "description": "\n\n".join([n for n in notes if n]),
            "start": {"date": start_d.isoformat()},
            "end": {"date": (end_d + timedelta(days=1)).isoformat()},
        }
    else:
        body: dict[str, Any] = {
            "summary": title,
            "description": "\n\n".join([n for n in notes if n]),
            "start": _google_calendar_datetime_body(block.get("start", "")),
            "end": _google_calendar_datetime_body(block.get("end", "")),
        }
    recurrence = str(block.get("recurrence", "") or "").strip()
    if recurrence:
        body["recurrence"] = [f"RRULE:{recurrence}" if not recurrence.upper().startswith("RRULE:") else recurrence]
    return body



def _calendar_block_validation_row(block: pd.Series) -> dict[str, str]:
    title = str(block.get("title", "") or "").strip()
    start_raw = str(block.get("start", "") or "").strip()
    end_raw = str(block.get("end", "") or "").strip()
    recurrence = str(block.get("recurrence", "") or "").strip()
    linked_id = str(block.get("linked_record_id", "") or "").strip()
    reasons: list[str] = []
    fixes: list[str] = []
    if not title:
        reasons.append("Missing title")
        fixes.append("Add a project step or routine activity title")
    if not linked_id:
        reasons.append("Missing Pathmark record link")
        fixes.append("Re-save the step or activity")
    if truthy_flag(block.get("all_day", "")):
        start_d = parse_online_date(start_raw)
        end_d = parse_online_date(end_raw)
        if start_d is None:
            reasons.append("Missing or invalid start")
            fixes.append("Add a start date")
        if end_d is None:
            reasons.append("Missing or invalid finish")
            fixes.append("Add a finish date")
        if start_d is not None and end_d is not None and end_d < start_d:
            reasons.append("Finish is before start")
            fixes.append("Set the finish date on or after the start date")
    else:
        start_dt = _parse_calendar_block_datetime(start_raw)
        end_dt = _parse_calendar_block_datetime(end_raw)
        if start_dt is None:
            reasons.append("Missing or invalid start")
            fixes.append("Add a start date and time")
        if end_dt is None:
            reasons.append("Missing or invalid finish")
            fixes.append("Add a finish date and time")
        if start_dt is not None and end_dt is not None and end_dt <= start_dt:
            reasons.append("Finish is not after start")
            fixes.append("Set a finish time after the start time")
    if recurrence:
        rec_upper = recurrence.upper().replace("RRULE:", "")
        if "FREQ=" not in rec_upper:
            reasons.append("Invalid repeat rule")
            fixes.append("Edit the routine repeat pattern")
    return {
        "Item": title or "Untitled calendar item",
        "Type": "Routine activity" if recurrence else "Project step",
        "Start": start_raw,
        "End": end_raw,
        "Repeat": recurrence or "Does not repeat",
        "Status": "Ready" if not reasons else "Needs review",
        "Reason": "; ".join(reasons),
        "Suggested fix": "; ".join(dict.fromkeys(fixes)),
        "linked_record_id": linked_id,
    }


def validate_calendar_blocks_for_google(blocks: pd.DataFrame) -> pd.DataFrame:
    if blocks.empty:
        return pd.DataFrame(columns=["Item", "Type", "Start", "End", "Repeat", "Status", "Reason", "Suggested fix", "linked_record_id"])
    return pd.DataFrame([_calendar_block_validation_row(row) for _, row in blocks.iterrows()])

def push_pathmark_calendar_to_google(sheet_id: str, blocks: pd.DataFrame) -> tuple[bool, str]:
    service = calendar_service()
    if service is None:
        return False, "Google Calendar access is not available for this session. Use the reconnect button to enable Calendar sync."
    if blocks.empty:
        return False, "No calendar items are ready to sync."
    validation = validate_calendar_blocks_for_google(blocks)
    invalid_ids = set(validation.loc[validation["Status"] != "Ready", "linked_record_id"].astype(str).tolist()) if not validation.empty else set()
    valid_blocks = blocks[~blocks.get("linked_record_id", pd.Series(dtype=str)).fillna("").astype(str).isin(invalid_ids)].copy() if invalid_ids else blocks.copy()
    results: list[dict[str, str]] = []
    for _, row in validation.iterrows():
        if row.get("Status") != "Ready":
            results.append({
                "Item": str(row.get("Item", "") or "Untitled calendar item"),
                "Type": str(row.get("Type", "") or ""),
                "Start": str(row.get("Start", "") or ""),
                "End": str(row.get("End", "") or ""),
                "Repeat": str(row.get("Repeat", "") or ""),
                "Status": "Needs review",
                "Reason": str(row.get("Reason", "") or ""),
                "Suggested fix": str(row.get("Suggested fix", "") or ""),
                "Sync stage": "Validation",
            })
    if valid_blocks.empty:
        st.session_state["calendar_sync_results"] = pd.DataFrame(results)
        return False, "No calendar items passed validation. Open the sync details table to see what needs fixing."
    action_lookup = _action_calendar_lookup(sheet_id)
    created = updated = failed = skipped = 0
    for _, block in valid_blocks.iterrows():
        linked_id = str(block.get("linked_record_id", "") or "").strip()
        title = str(block.get("title", "Calendar item") or "Calendar item")
        recurrence = str(block.get("recurrence", "") or "").strip()
        block_type = "Routine activity" if recurrence else "Project step"
        start_text = str(block.get("start", "") or "")
        end_text = str(block.get("end", "") or "")
        action = action_lookup.get(linked_id, {})
        base_result = {
            "Item": title,
            "Type": block_type,
            "Start": start_text,
            "End": end_text,
            "Repeat": recurrence or "Does not repeat",
            "Suggested fix": "",
        }
        ok_cal, calendar_id, cal_msg = get_or_create_area_calendar(sheet_id, str(block.get("area_name", "") or ""))
        if not ok_cal or not calendar_id:
            failed += 1
            result = dict(base_result)
            result.update({"Status": "Could not sync", "Reason": cal_msg, "Suggested fix": "Check the Area name and Google Calendar permission, then try again.", "Sync stage": "Area calendar"})
            results.append(result)
            continue
        existing_id = str(action.get("google_calendar_event_id", "") or "").strip()
        existing_calendar_id = str(action.get("google_calendar_id", "") or "").strip()
        body = _google_calendar_event_body(block)
        try:
            if existing_id and (not existing_calendar_id or existing_calendar_id == calendar_id):
                event = service.events().patch(calendarId=calendar_id, eventId=existing_id, body=body).execute()
                updated += 1
                status = "Updated"
                stage = "Google API update"
            else:
                event = service.events().insert(calendarId=calendar_id, body=body).execute()
                created += 1
                status = "Created"
                stage = "Google API insert"
            event_id = str(event.get("id", "") or "").strip()
            if not event_id:
                failed += 1
                result = dict(base_result)
                result.update({"Status": "Needs review", "Reason": "Google Calendar did not return an event ID", "Suggested fix": "Try again, then use repair if the event appears in Google Calendar", "Sync stage": stage})
                results.append(result)
                continue
            updates = _calendar_update_for_block(event, calendar_id, recurrence, "synced")
            ok_update, update_msg = update_online_record(sheet_id, "actions", linked_id, updates)
            if not ok_update:
                failed += 1
                result = dict(base_result)
                result.update({"Status": "Needs review", "Reason": "Google Calendar event was created/updated, but Pathmark could not store the event ID", "Suggested fix": safe_user_message(update_msg), "Sync stage": "Pathmark Sync write-back"})
                results.append(result)
            else:
                result = dict(base_result)
                result.update({"Status": status, "Reason": f"Google event ID stored: {event_id}", "Suggested fix": "", "Sync stage": "Synced"})
                results.append(result)
        except Exception as exc:
            failed += 1
            result = dict(base_result)
            result.update({"Status": "Could not sync", "Reason": _sync_error_detail(exc), "Suggested fix": "Check Google Calendar permission and the event start/finish times. If the event was created, use Repair missing Google Calendar links.", "Sync stage": "Google API"})
            results.append(result)
    clear_online_cache(sheet_id)
    st.session_state["calendar_sync_results"] = pd.DataFrame(results)
    msg = f"Created {created} new calendar item(s) and updated {updated} existing item(s) across Area calendars."
    skipped = len([r for r in results if r.get("Sync stage") == "Validation"])
    if skipped:
        msg += f" {skipped} item(s) were skipped because they need review."
    if failed:
        msg += f" {failed} item(s) could not be fully synced; see the sync results table."
    else:
        msg += " Pathmark stored the returned Google Calendar event IDs."
    return failed == 0 and skipped == 0, msg

def _event_time_string(value: dict[str, Any]) -> str:
    raw = str(value.get("dateTime") or value.get("date") or "")
    if not raw:
        return ""
    return _calendar_key_from_any(raw)


def _calendar_event_key_from_values(title: Any, start: Any, end: Any) -> tuple[str, str, str]:
    return (_normalise_match_text(title), _calendar_key_from_any(start), _calendar_key_from_any(end))


def repair_google_calendar_links_by_title_time(sheet_id: str, blocks: pd.DataFrame | None = None) -> tuple[int, str]:
    """Repair Pathmark calendar rows when Area calendar events exist but IDs were not stored."""
    service = calendar_service()
    if service is None:
        return 0, "Google Calendar access is not available for repair."
    if blocks is None:
        blocks = staged_calendar_blocks(sheet_id)
    if blocks.empty:
        return 0, "No Pathmark calendar items are available for repair."
    actions = read_online_table(sheet_id, "actions")
    existing_linked = set(actions.get("google_calendar_event_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().tolist()) if not actions.empty else set()
    diagnostics: list[dict[str, str]] = []
    try:
        repaired = 0
        considered = 0
        events_checked = 0
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=365)).isoformat(timespec="seconds")
        time_max = (now + timedelta(days=730)).isoformat(timespec="seconds")
        for _, block in blocks.iterrows():
            linked_id = str(block.get("linked_record_id", "") or "").strip()
            if not linked_id:
                continue
            action_match = actions[actions.get("action_id", pd.Series(dtype=str)).fillna("").astype(str).eq(linked_id)] if not actions.empty else pd.DataFrame()
            current_event_id = ""
            if not action_match.empty:
                current_event_id = str(action_match.iloc[0].get("google_calendar_event_id", "") or "").strip()
            if current_event_id:
                continue
            considered += 1
            ok_cal, calendar_id, cal_msg = get_or_create_area_calendar(sheet_id, str(block.get("area_name", "") or ""))
            if not ok_cal or not calendar_id:
                diagnostics.append({"Pathmark item": str(block.get("title", "") or ""), "Pathmark start": str(block.get("start", "") or ""), "Google candidate": "", "Google start": "", "Result": "Not matched", "Reason": cal_msg})
                continue
            token = None
            events: list[dict[str, Any]] = []
            while True:
                result = service.events().list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max, singleEvents=False, showDeleted=False, maxResults=250, pageToken=token).execute()
                events.extend(result.get("items", []) or [])
                token = result.get("nextPageToken")
                if not token:
                    break
            events_checked += len(events)
            by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
            by_title: dict[str, list[dict[str, Any]]] = {}
            for ev in events:
                start_s = _event_time_string(ev.get("start", {}) or {})
                end_s = _event_time_string(ev.get("end", {}) or {})
                key = _calendar_event_key_from_values(ev.get("summary", ""), start_s, end_s)
                by_key.setdefault(key, []).append(ev)
                by_title.setdefault(key[0], []).append(ev)
            key = _calendar_event_key_from_values(block.get("title", ""), block.get("start", ""), block.get("end", ""))
            exact = [ev for ev in by_key.get(key, []) if str(ev.get("id", "") or "") not in existing_linked]
            title_matches = [ev for ev in by_title.get(key[0], []) if str(ev.get("id", "") or "") not in existing_linked]
            match = None
            match_type = ""
            reason = ""
            if len(exact) == 1:
                match = exact[0]
                match_type = "title + start/end time"
            elif len(exact) > 1:
                reason = "Multiple Google Calendar events matched the same title and time"
            elif len(title_matches) == 1:
                match = title_matches[0]
                match_type = "unique title in the Area calendar"
            elif len(title_matches) > 1:
                reason = "Multiple Google Calendar events matched the title in this Area calendar; start/end times did not identify one clear event"
            else:
                reason = "No Google Calendar event with the same title was found in the Area calendar"
            if match is not None:
                recurrence = ";".join(match.get("recurrence", []) or [])
                ok_update, update_msg = update_online_record(sheet_id, "actions", linked_id, _calendar_update_for_block(match, calendar_id, recurrence, "repaired_google_calendar_link"))
                if ok_update:
                    repaired += 1
                    diagnostics.append({"Pathmark item": str(block.get("title", "") or ""), "Pathmark start": str(block.get("start", "") or ""), "Google candidate": str(match.get("summary", "") or ""), "Google start": _event_time_string(match.get("start", {}) or {}), "Result": "Repaired", "Reason": f"Matched by {match_type}"})
                else:
                    diagnostics.append({"Pathmark item": str(block.get("title", "") or ""), "Pathmark start": str(block.get("start", "") or ""), "Google candidate": str(match.get("summary", "") or ""), "Google start": _event_time_string(match.get("start", {}) or {}), "Result": "Could not write back", "Reason": safe_user_message(update_msg)})
            else:
                diagnostics.append({"Pathmark item": str(block.get("title", "") or ""), "Pathmark start": str(block.get("start", "") or ""), "Google candidate": ", ".join([str(i.get("summary", "") or "") for i in title_matches[:3]]), "Google start": ", ".join([_event_time_string(i.get("start", {}) or {}) for i in title_matches[:3]]), "Result": "Not matched", "Reason": reason})
        if repaired:
            clear_online_cache(sheet_id)
        st.session_state["calendar_repair_results"] = pd.DataFrame(diagnostics)
        return repaired, f"Checked {events_checked} Google Calendar event(s) across Area calendars, checked {considered} unlinked Pathmark item(s), and repaired {repaired} link(s)."
    except Exception as exc:
        return 0, f"Could not repair Google Calendar links: {_sync_error_detail(exc)}"


def pull_google_calendar_status_to_pathmark(sheet_id: str) -> tuple[bool, str]:
    service = calendar_service()
    if service is None:
        return False, "Google Calendar access is not available for this session. Use the reconnect button to enable Calendar sync."
    actions = read_online_table(sheet_id, "actions")
    if actions.empty or "google_calendar_event_id" not in actions.columns:
        return False, "No linked Google Calendar events are stored in Pathmark yet. Push calendar items first."
    linked = actions[actions.get("google_calendar_event_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("")]
    blocks = staged_calendar_blocks(sheet_id)
    if linked.empty:
        repaired, repair_msg = repair_google_calendar_links_by_title_time(sheet_id, blocks)
        if repaired:
            actions = read_online_table(sheet_id, "actions")
            linked = actions[actions.get("google_calendar_event_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("")] if not actions.empty else pd.DataFrame()
        if linked.empty:
            return False, "No linked Google Calendar events are stored in Pathmark yet. " + repair_msg + " Push calendar items first, or use Repair missing Google Calendar links if they already exist in Google Calendar."
    block_lookup = {str(r.get("linked_record_id", "") or ""): r for _, r in blocks.iterrows()}
    checked = moved = missing = 0
    for _, row in linked.iterrows():
        aid = str(row.get("action_id", "") or "").strip()
        cal_id = str(row.get("google_calendar_id", "") or "").strip()
        event_id = str(row.get("google_calendar_event_id", "") or "").strip()
        if not aid or not cal_id or not event_id:
            continue
        try:
            event = service.events().get(calendarId=cal_id, eventId=event_id).execute()
            checked += 1
            status = str(event.get("status", "") or "confirmed")
            sync_status = "pulled_from_google_calendar"
            block = block_lookup.get(aid)
            if block is not None:
                google_start = _event_time_string(event.get("start", {}) or {})
                google_end = _event_time_string(event.get("end", {}) or {})
                pathmark_start = _calendar_key_from_any(block.get("start", ""))
                pathmark_end = _calendar_key_from_any(block.get("end", ""))
                if google_start and pathmark_start and (google_start != pathmark_start or google_end != pathmark_end):
                    moved += 1
                    sync_status = "moved_in_google_calendar_review_needed"
            updates = {
                "google_calendar_status": status,
                "google_calendar_updated_at": str(event.get("updated", "") or ""),
                "google_calendar_synced_at": utc_now_text(),
                "calendar_sync_status": sync_status,
            }
            update_online_record(sheet_id, "actions", aid, updates)
        except Exception:
            missing += 1
            update_online_record(sheet_id, "actions", aid, {"google_calendar_synced_at": utc_now_text(), "calendar_sync_status": "missing_in_google_calendar"})
    clear_online_cache(sheet_id)
    msg = f"Checked {checked} linked Google Calendar event(s)."
    if moved:
        msg += f" {moved} moved event(s) were flagged for review."
    if missing:
        msg += f" {missing} linked event(s) could not be found and were marked for review."
    return True, msg


def google_calendar_sync_summary(sheet_id: str) -> dict[str, int]:
    blocks = staged_calendar_blocks(sheet_id)
    actions = read_online_table(sheet_id, "actions")
    if actions.empty:
        return {"total": int(len(blocks)), "linked": 0, "review": 0, "recurring": int(blocks.get("recurrence", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("").sum()) if not blocks.empty else 0}
    linked = actions.get("google_calendar_event_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("")
    review = actions.get("calendar_sync_status", pd.Series(dtype=str)).fillna("").astype(str).str.contains("review|missing", case=False, regex=True)
    recurring = blocks.get("recurrence", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("") if not blocks.empty else pd.Series(dtype=bool)
    return {"total": int(len(blocks)), "linked": int(linked.sum()), "review": int(review.sum()), "recurring": int(recurring.sum())}


def render_google_calendar_export_manager(sheet_id: str) -> None:
    st.subheader("Google Calendar Sync")
    st.write("Send Pathmark calendar time directly to Google Calendar. Project steps sync as one-off events; routine activities sync as recurring events so your calendar stays clean.")
    st.info("Calendar Sync creates or reuses Google calendars named after your Pathmark Areas, then places each project step or routine activity into its matching Area calendar. Sync actions remain user-controlled.")

    scopes_ready = google_calendar_scope_ready()
    if not scopes_ready:
        st.warning("Google Calendar permission is not available in this session. Reconnect Google to use direct Calendar sync.")
        auth_url = google_auth_url(GOOGLE_CALENDAR_SCOPES, return_hint="calendar_sync")
        if auth_url:
            st.link_button("Reconnect Google and enable Calendar sync", auth_url, use_container_width=True)
        st.caption("Pathmark uses Calendar access to create or reuse Area calendars and to update linked Pathmark events only. No refresh token is stored by the hosted app.")

    blocks = staged_calendar_blocks(sheet_id)
    stats = google_calendar_sync_summary(sheet_id)
    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-tile"><div class="metric-label">Ready to sync</div><div class="metric-value">{stats['total']}</div></div>
      <div class="metric-tile"><div class="metric-label">Linked to Google</div><div class="metric-value">{stats['linked']}</div></div>
      <div class="metric-tile"><div class="metric-label">Recurring events</div><div class="metric-value">{stats['recurring']}</div></div>
      <div class="metric-tile {'warning' if stats['review'] else ''}"><div class="metric-label">Needs review</div><div class="metric-value">{stats['review']}</div></div>
    </div>
    """, unsafe_allow_html=True)

    validation = validate_calendar_blocks_for_google(blocks)
    invalid_count = int((validation["Status"] != "Ready").sum()) if not validation.empty else 0
    if invalid_count:
        st.warning(f"{invalid_count} calendar item(s) need review before they can sync. Open the validation table below for details.")

    backup_before_calendar_sync = st.checkbox("Create a safety backup before Calendar sync", value=False, key="backup_before_calendar_sync", help="Recommended. This backs up Pathmark Sync before sync metadata is written back to the sheet.")
    c1, c2 = st.columns(2)
    if c1.button("Push Pathmark calendar time to Google Calendar", use_container_width=True, disabled=blocks.empty or not scopes_ready):
        if backup_before_calendar_sync:
            create_pathmark_sync_backup(sheet_id)
        ok, message = push_pathmark_calendar_to_google(sheet_id, blocks)
        if ok:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()
    if c2.button("Pull Calendar status from Google", use_container_width=True, disabled=not scopes_ready):
        if backup_before_calendar_sync:
            create_pathmark_sync_backup(sheet_id)
        ok, message = pull_google_calendar_status_to_pathmark(sheet_id)
        if ok:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()

    if st.button("Repair missing Google Calendar links", use_container_width=True, disabled=blocks.empty or not scopes_ready, help="Use this if events were created in Google Calendar but Pathmark did not store their event IDs. It matches Pathmark calendar items to events in their Area calendars by title and start/end time."):
        repaired, message = repair_google_calendar_links_by_title_time(sheet_id, blocks)
        if repaired:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()

    st.caption("Pathmark remains the planning source of truth. If a linked event is moved or deleted in Google Calendar, Pathmark flags it for review rather than silently overwriting your plan.")

    if blocks.empty:
        st.info("No calendar rows are staged yet. Add a project step or routine activity with start and finish times.")
    else:
        st.markdown("### Calendar items ready to sync")
        action_lookup = _action_calendar_lookup(sheet_id)
        for _, row in blocks.iterrows():
            start_text = human_calendar_datetime(str(row.get("start", "")))
            end_text = human_calendar_datetime(str(row.get("end", "")))
            repeat = human_recurrence(row.get("recurrence", ""))
            area = str(row.get("area_name", "") or "")
            area_line = f"Area: {html.escape(area)}" if area else ""
            repeat_line = html.escape(repeat) if repeat else "Does not repeat"
            linked_id = str(row.get("linked_record_id", "") or "")
            action = action_lookup.get(linked_id, {})
            raw_sync = str(action.get("calendar_sync_status", "") or "")
            event_id = str(action.get("google_calendar_event_id", "") or "")
            if event_id:
                if "moved" in raw_sync or "changed" in raw_sync:
                    sync_line = "Changed in Google Calendar"
                elif "missing" in raw_sync:
                    sync_line = "Missing from Google Calendar"
                elif "review" in raw_sync:
                    sync_line = "Needs review"
                else:
                    sync_line = "Synced"
                sync_line += " · Linked to Google Calendar"
            else:
                sync_line = "Not synced"
            joiner = " · " if area_line and repeat_line else ""
            st.markdown(
                f"""
                <div class='step-card'>
                  <h3>{html.escape(str(row.get('title', 'Calendar item') or 'Calendar item'))}</h3>
                  <p><strong>{html.escape(start_text)}</strong>{' – ' + html.escape(end_text.split(', ')[-1]) if end_text else ''}</p>
                  <p>{area_line}{joiner}{repeat_line}</p>
                  <p>{html.escape(sync_line)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with st.expander("Show sync details", expanded=invalid_count > 0):
            st.write("Validation checks title, linked Pathmark record, start/finish times, and repeat rule before Pathmark tries to send anything to Google Calendar.")
            if not validation.empty:
                dataframe_preview(validation.drop(columns=["linked_record_id"], errors="ignore"), ["Item", "Type", "Start", "End", "Repeat", "Status", "Reason", "Suggested fix"])
            details = blocks.copy()
            if not details.empty:
                details["calendar_sync_status"] = details["linked_record_id"].map(lambda x: action_lookup.get(str(x), {}).get("calendar_sync_status", ""))
                details["google_calendar_event_id"] = details["linked_record_id"].map(lambda x: action_lookup.get(str(x), {}).get("google_calendar_event_id", ""))
            dataframe_preview(details, ["title", "area_name", "start", "end", "recurrence", "google_calendar_event_id", "calendar_sync_status"])
        if "calendar_sync_results" in st.session_state:
            with st.expander("Last Google Calendar sync results", expanded=True):
                results = st.session_state.get("calendar_sync_results")
                if isinstance(results, pd.DataFrame):
                    dataframe_preview(results, ["Item", "Type", "Start", "End", "Repeat", "Status", "Reason", "Suggested fix", "Sync stage"])
    if "calendar_repair_results" in st.session_state:
        with st.expander("Last Google Calendar repair diagnostics", expanded=False):
            diag = st.session_state.get("calendar_repair_results")
            if isinstance(diag, pd.DataFrame):
                dataframe_preview(diag, ["Pathmark item", "Pathmark start", "Google candidate", "Google start", "Result", "Reason"])

    with st.expander("ICS fallback", expanded=False):
        st.write("Keep this fallback if you want a file-based import instead of direct Google Calendar sync.")
        st.download_button("Download Google Calendar .ics", data=build_ics_export(blocks), file_name="pathmark_calendar_blocks.ics", mime="text/calendar", use_container_width=True, disabled=blocks.empty)

    if not blocks.empty:
        st.info("Calendar sync does not archive items. Linked project steps and routine activities remain in their Projects or Routines tabs until you pause or archive them deliberately.")
        if st.button("Mark calendar items as synced/exported", use_container_width=True):
            ids = blocks.get("linked_record_id", pd.Series(dtype=str)).dropna().astype(str).tolist()
            ok, message = mark_actions_exported(sheet_id, ids, "google_calendar", archive=False)
            if ok:
                st.success(message)
            else:
                st.warning(safe_user_message(message))
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


def _normalise_google_task_due(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed: date | None = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(raw[:10], fmt).date()
            break
        except Exception:
            pass
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except Exception:
            return ""
    return parsed.isoformat() + "T00:00:00.000Z"


def _google_task_date_label(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return raw[:10]


def get_or_create_google_task_list(title: str = "Pathmark") -> tuple[bool, str, str]:
    service = tasks_service()
    if service is None:
        return False, "", "Google Tasks access is not available for this session. Reconnect Google to enable Tasks sync."
    wanted = (title or "Pathmark").strip() or "Pathmark"
    try:
        token = None
        while True:
            result = service.tasklists().list(maxResults=100, pageToken=token).execute()
            for item in result.get("items", []) or []:
                if str(item.get("title", "")).strip().lower() == wanted.lower():
                    return True, str(item.get("id", "")), f"Using existing Google Tasks list: {wanted}."
            token = result.get("nextPageToken")
            if not token:
                break
        created = service.tasklists().insert(body={"title": wanted}).execute()
        return True, str(created.get("id", "")), f"Created Google Tasks list: {wanted}."
    except Exception as exc:
        return False, "", f"Could not find or create the Google Tasks list: {exc}"


def _task_update_target(row: pd.Series) -> tuple[str, str]:
    table = str(row.get("source_table", "") or "").strip()
    rid = str(row.get("source_id", "") or row.get("id", "") or "").strip()
    if table not in {"actions", "task_prompts"}:
        table = "task_prompts" if str(row.get("id", "")).startswith("prompt-") else "actions"
    return table, rid


def _updates_from_google_task(item: dict[str, Any], list_id: str, *, sync_status: str = "synced") -> dict[str, str]:
    return {
        "google_task_list_id": list_id,
        "google_task_id": str(item.get("id", "") or ""),
        "google_task_status": str(item.get("status", "") or "needsAction"),
        "google_task_completed_at": str(item.get("completed", "") or ""),
        "google_task_updated_at": str(item.get("updated", "") or ""),
        "google_task_synced_at": utc_now_text(),
        "sync_status": sync_status,
    }


def update_task_sync_metadata(sheet_id: str, row: pd.Series, updates: dict[str, Any]) -> tuple[bool, str]:
    """Write Google Tasks sync metadata and keep action/task_prompt mirrors aligned.

    Some Pathmark items can be represented by an action row and by the explicit
    task_prompts row that was created for Google Tasks. Pulling status from
    Google must update both views so the Google Tasks Sync tab, Projects tab,
    Routines tab and Dashboard all show the same completion state.
    """
    table, rid = _task_update_target(row)
    ok, message = update_online_record(sheet_id, table, rid, updates)
    linked_record_id = str(row.get("linked_record_id", "") or "").strip()
    linked_record_type = str(row.get("linked_record_type", "") or row.get("source_record_type", "") or "").strip().lower()
    source_id = str(row.get("source_id", "") or row.get("id", "") or "").strip()

    # If the sync row is an explicit activity checklist item, update the parent
    # action row as well. Helper checklist items intentionally remain separate.
    if table == "task_prompts" and linked_record_id and "helper" not in linked_record_type:
        task_kind = str(row.get("task_kind", "") or "").strip().lower()
        if task_kind in {"activity", ""} or "project_step" in linked_record_type or "routine_activity" in linked_record_type:
            update_online_record(sheet_id, "actions", linked_record_id, updates)

    # If the sync row is derived from an action, update any explicit activity
    # prompt linked to that action so detailed task views stay consistent.
    if table == "actions" and source_id:
        prompts = read_online_table(sheet_id, "task_prompts")
        if not prompts.empty:
            for _, prompt in prompts.iterrows():
                pid = str(prompt.get("prompt_id", "") or "").strip()
                if not pid:
                    continue
                if str(prompt.get("linked_record_id", "") or "").strip() != source_id:
                    continue
                prompt_kind = str(prompt.get("task_kind", "") or "").strip().lower()
                prompt_type = str(prompt.get("linked_record_type", "") or "").strip().lower()
                if prompt_kind == "helper" or "helper" in prompt_type:
                    continue
                update_online_record(sheet_id, "task_prompts", pid, updates)
    return ok, message


def push_pathmark_tasks_to_google(sheet_id: str, prompts: pd.DataFrame) -> tuple[bool, str]:
    service = tasks_service()
    if service is None:
        return False, "Google Tasks access is not available for this session. Use the reconnect button to enable Google Tasks sync."
    if prompts.empty:
        return False, "No checklist items are ready to sync."
    ok, task_list_id, list_msg = get_or_create_google_task_list("Pathmark")
    if not ok or not task_list_id:
        return False, list_msg
    created = 0
    updated = 0
    failed = 0
    for _, row in prompts.iterrows():
        title = str(row.get("title", "") or "Pathmark checklist item").strip() or "Pathmark checklist item"
        notes = str(row.get("notes", "") or "")
        due = _normalise_google_task_due(row.get("due_date", ""))
        existing_id = str(row.get("google_task_id", "") or "").strip()
        body = {"title": title, "notes": notes}
        if due:
            body["due"] = due
        try:
            if existing_id:
                item = service.tasks().patch(tasklist=task_list_id, task=existing_id, body=body).execute()
                updated += 1
            else:
                item = service.tasks().insert(tasklist=task_list_id, body=body).execute()
                created += 1
            table, rid = _task_update_target(row)
            updates = _updates_from_google_task(item, task_list_id, sync_status="synced")
            ok_update, update_msg = update_task_sync_metadata(sheet_id, row, updates)
            if not ok_update:
                failed += 1
                st.session_state["google_tasks_last_issue"] = f"Created in Google Tasks but could not save the task ID back to Pathmark: {safe_user_message(update_msg)}"
        except Exception as exc:
            failed += 1
            st.session_state["google_tasks_last_issue"] = safe_user_message(str(exc))[:240]
    clear_online_cache(sheet_id)
    ok_all = failed == 0
    msg = f"{list_msg} Pushed {created} new item(s) and updated {updated} existing item(s) in Google Tasks."
    if failed:
        msg += f" {failed} item(s) could not be fully synced. If tasks were created but still show as staged, use Repair missing Google Task links."
    else:
        msg += " Pathmark stored the returned Google Task IDs and refreshed sync data."
    return ok_all, msg



def _google_task_due_key(item: dict[str, Any]) -> str:
    due = str(item.get("due", "") or "").strip()
    return due[:10]


def _normalise_match_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def repair_google_task_links_by_title_due(sheet_id: str, prompts: pd.DataFrame | None = None) -> tuple[int, str]:
    """Repair Pathmark rows created in Google Tasks before IDs were written back."""
    service = tasks_service()
    if service is None:
        return 0, "Google Tasks access is not available for repair."
    if prompts is None:
        prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        return 0, "No Pathmark checklist items are available for repair."
    ok, task_list_id, list_msg = get_or_create_google_task_list("Pathmark")
    if not ok or not task_list_id:
        return 0, list_msg
    diagnostics: list[dict[str, str]] = []
    try:
        google_items: list[dict[str, Any]] = []
        token = None
        while True:
            result = service.tasks().list(tasklist=task_list_id, showCompleted=True, showHidden=True, showDeleted=False, maxResults=100, pageToken=token).execute()
            google_items.extend(result.get("items", []) or [])
            token = result.get("nextPageToken")
            if not token:
                break
        by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        by_title: dict[str, list[dict[str, Any]]] = {}
        for item in google_items:
            title_key = _normalise_match_text(item.get("title", ""))
            due_key = _google_task_due_key(item)
            by_key.setdefault((title_key, due_key), []).append(item)
            by_title.setdefault(title_key, []).append(item)
        repaired = 0
        considered = 0
        for _, row in prompts.iterrows():
            if str(row.get("google_task_id", "") or "").strip():
                continue
            considered += 1
            title_key = _normalise_match_text(row.get("title", ""))
            due_key = (_normalise_google_task_due(row.get("due_date", "")) or "")[:10]
            exact = by_key.get((title_key, due_key), [])
            title_matches = by_title.get(title_key, [])
            match = None
            match_type = ""
            reason = ""
            if len(exact) == 1:
                match = exact[0]
                match_type = "title + due date"
            elif len(exact) > 1:
                reason = "Multiple Google Tasks matched the same title and due date"
            elif len(title_matches) == 1:
                match = title_matches[0]
                match_type = "unique title"
            elif len(title_matches) > 1:
                reason = "Multiple Google Tasks matched the title; due dates did not identify one clear task"
            else:
                reason = "No Google Task with the same title was found in the Pathmark task list"
            if match is not None:
                table, rid = _task_update_target(row)
                ok_update, update_msg = update_task_sync_metadata(sheet_id, row, _updates_from_google_task(match, task_list_id, sync_status="repaired_google_task_link"))
                if ok_update:
                    repaired += 1
                    diagnostics.append({"Pathmark item": str(row.get("title", "") or ""), "Pathmark due": due_key, "Google candidate": str(match.get("title", "") or ""), "Google due": _google_task_due_key(match), "Result": "Repaired", "Reason": f"Matched by {match_type}"})
                else:
                    diagnostics.append({"Pathmark item": str(row.get("title", "") or ""), "Pathmark due": due_key, "Google candidate": str(match.get("title", "") or ""), "Google due": _google_task_due_key(match), "Result": "Could not write back", "Reason": safe_user_message(update_msg)})
            else:
                diagnostics.append({"Pathmark item": str(row.get("title", "") or ""), "Pathmark due": due_key, "Google candidate": ", ".join([str(i.get("title", "") or "") for i in title_matches[:3]]), "Google due": ", ".join([_google_task_due_key(i) for i in title_matches[:3]]), "Result": "Not matched", "Reason": reason})
        if repaired:
            clear_online_cache(sheet_id)
        st.session_state["google_tasks_repair_results"] = pd.DataFrame(diagnostics)
        return repaired, f"{list_msg} Found {len(google_items)} Google Task(s), checked {considered} unlinked Pathmark item(s), and repaired {repaired} link(s)."
    except Exception as exc:
        return 0, f"Could not repair Google Task links: {_sync_error_detail(exc)}"

def pull_google_task_status_to_pathmark(sheet_id: str) -> tuple[bool, str]:
    service = tasks_service()
    if service is None:
        return False, "Google Tasks access is not available for this session. Use the reconnect button to enable Google Tasks sync."
    prompts = staged_task_prompts(sheet_id)
    linked = prompts[prompts.get("google_task_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("")] if not prompts.empty else pd.DataFrame()
    if linked.empty:
        repaired, repair_msg = repair_google_task_links_by_title_due(sheet_id, prompts)
        if repaired:
            prompts = staged_task_prompts(sheet_id)
            linked = prompts[prompts.get("google_task_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("")] if not prompts.empty else pd.DataFrame()
        if linked.empty:
            return False, "No stored Google Task IDs were found. " + repair_msg + " Push items to Google Tasks, or use Repair missing Google Task links if they already exist in Google Tasks."
    checked = 0
    completed = 0
    missing = 0
    for _, row in linked.iterrows():
        task_id = str(row.get("google_task_id", "") or "").strip()
        list_id = str(row.get("google_task_list_id", "") or "").strip()
        if not task_id or not list_id:
            continue
        table, rid = _task_update_target(row)
        try:
            item = service.tasks().get(tasklist=list_id, task=task_id).execute()
            checked += 1
            updates = _updates_from_google_task(item, list_id, sync_status="pulled_from_google_tasks")
            status = str(item.get("status", "") or "needsAction")
            if status == "completed":
                completed += 1
            # Keep the original Pathmark planning/checklist row visible. Google
            # completion is stored in google_task_status/completed_at; do not
            # mark the source row Done/completed here because those statuses can
            # hide it from Pathmark sync views.
            update_task_sync_metadata(sheet_id, row, updates)
        except Exception:
            missing += 1
            update_task_sync_metadata(sheet_id, row, {"google_task_synced_at": utc_now_text(), "sync_status": "missing_in_google_tasks"})
    clear_online_cache(sheet_id)
    load_online_tables(sheet_id, force=True)
    msg = f"Checked {checked} linked Google Task(s). {completed} completed item(s) were reflected in Pathmark."
    if missing:
        msg += f" {missing} linked item(s) could not be found in Google Tasks and were marked for review."
    return True, msg


def google_tasks_sync_summary(sheet_id: str) -> dict[str, int]:
    prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        return {"total": 0, "linked": 0, "completed": 0, "missing": 0}
    linked = prompts.get("google_task_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("")
    completed = prompts.get("google_task_status", pd.Series(dtype=str)).fillna("").astype(str).str.lower().eq("completed")
    missing = prompts.get("sync_status", pd.Series(dtype=str)).fillna("").astype(str).str.lower().eq("missing_in_google_tasks")
    return {"total": int(len(prompts)), "linked": int(linked.sum()), "completed": int(completed.sum()), "missing": int(missing.sum())}


def _task_sync_user_label(row: pd.Series) -> str:
    """Plain-language status for Google Tasks cards."""
    task_id = str(row.get("google_task_id", "") or "").strip()
    google_status = str(row.get("google_task_status", "") or "").strip().lower()
    sync_status = str(row.get("sync_status", "") or "").strip().lower()
    if not task_id:
        return "Not sent to Google Tasks"
    if "missing" in sync_status:
        return "Missing from Google Tasks"
    if "review" in sync_status:
        return "Needs review"
    if google_status == "completed":
        return "Completed in Google Tasks"
    if google_status in {"needsaction", "needs_action", "pending", ""}:
        return "Pending in Google Tasks"
    return google_status.replace("_", " ").title()


def _normalise_status_for_chip(label: str) -> str:
    text = str(label or "").lower()
    if "completed" in text or text in {"done", "complete"}:
        return "done"
    if "pending" in text or "synced" in text or "linked" in text or "needsaction" in text:
        return "pending"
    if "overdue" in text:
        return "overdue"
    if "missing" in text or "review" in text or "changed" in text:
        return "review"
    return "muted"


def status_chip(label: str) -> str:
    cls = _normalise_status_for_chip(label)
    return f"<span class='status-chip {cls}'>{html.escape(str(label or 'Not sent'))}</span>"


def progress_bar_html(done: int, total: int, label: str = "", show_label: bool = True) -> str:
    total = max(int(total or 0), 0)
    done = max(min(int(done or 0), total), 0) if total else 0
    percent = int(round((done / total) * 100)) if total else 0
    display = label or (f"{done} of {total} complete" if total else "No items planned")
    head = f"<div class='progress-head'><span>{html.escape(display)}</span><span>{percent}%</span></div>" if show_label else f"<div class='progress-head percent-only'><span></span><span>{percent}%</span></div>"
    return (
        "<div class='progress-summary'>"
        f"{head}"
        "<div class='progress-track'>"
        f"<div class='progress-fill' style='width:{percent}%;'></div>"
        "</div></div>"
    )


def _today_nz() -> date:
    try:
        return datetime.now(_pathmark_nz_timezone()).date()
    except Exception:
        return date.today()


def _week_bounds_for_settings(sheet_id: str, ref_date: date | None = None) -> tuple[date, date, str]:
    start_pref = online_setting(sheet_id, "week_starts_on", "Monday").strip().title() or "Monday"
    if start_pref not in {"Monday", "Sunday"}:
        start_pref = "Monday"
    ref = ref_date or _today_nz()
    start_weekday = 6 if start_pref == "Sunday" else 0
    delta = (ref.weekday() - start_weekday) % 7
    start = ref - timedelta(days=delta)
    return start, start + timedelta(days=6), start_pref


def _row_date_in_range(row: pd.Series, start: date, end: date) -> bool:
    raw = str(row.get("due_date", "") or row.get("scheduled_date", "") or "").strip()
    dt = parse_online_date(raw)
    return bool(dt and start <= dt <= end)


def task_prompt_matches_parent(row: pd.Series, parent_id: str, parent_kind: str) -> bool:
    parent_id = str(parent_id or "").strip()
    if not parent_id:
        return False
    parent_kind = str(parent_kind or "").strip().lower()
    linked_parent_id = str(row.get("linked_parent_id", "") or "").strip()
    linked_parent_type = str(row.get("linked_parent_type", "") or "").strip().lower()
    linked_record_id = str(row.get("linked_record_id", "") or "").strip()
    source_id = str(row.get("source_id", "") or row.get("id", "") or "").strip()
    source_type = str(row.get("source_record_type", "") or row.get("linked_record_type", "") or "").strip().lower()
    if linked_parent_id == parent_id and (not linked_parent_type or parent_kind in linked_parent_type):
        return True
    if linked_record_id == parent_id:
        return True
    if source_id == parent_id and parent_kind in source_type:
        return True
    return False


def task_prompt_matches_action(row: pd.Series, action_id: str) -> bool:
    action_id = str(action_id or "").strip()
    if not action_id:
        return False
    return action_id in {
        str(row.get("source_id", "") or row.get("id", "") or "").strip(),
        str(row.get("linked_record_id", "") or "").strip(),
    }


def is_task_completed_row(row: pd.Series) -> bool:
    google_status = str(row.get("google_task_status", "") or row.get("status", "") or "").strip().lower()
    sync_status = str(row.get("sync_status", "") or "").strip().lower()
    return google_status == "completed" or sync_status in {"completed", "done"}


def completion_counts(items: pd.DataFrame) -> tuple[int, int]:
    if items is None or items.empty:
        return 0, 0
    total = len(items)
    done = int(sum(1 for _, row in items.iterrows() if is_task_completed_row(row)))
    return done, total


def project_task_items(sheet_id: str, project_id: str) -> pd.DataFrame:
    prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        return prompts
    progress_action_ids = project_progress_action_ids(sheet_id, project_id)
    def _project_progress_prompt(row: pd.Series) -> bool:
        if not task_prompt_matches_parent(row, project_id, "project"):
            return False
        source_id = str(row.get("linked_record_id", "") or row.get("source_id", "") or "").strip()
        task_kind = str(row.get("task_kind", "") or "").strip().lower()
        source_type = str(row.get("source_record_type", "") or row.get("linked_record_type", "") or "").strip().lower()
        # Project progress is measured from progress items/focus milestones, not
        # from helper prompts or supporting practice/work sessions.
        if "helper" in task_kind or "helper" in source_type:
            return False
        if source_type in {"supporting_time", "supporting time", "supporting time block", "time_block", "time block"}:
            return False
        if source_id and progress_action_ids and source_id not in progress_action_ids:
            return False
        return source_type in {"project_progress", "project_step", "project_focus", "focus_block", "focus block", ""}
    mask = prompts.apply(_project_progress_prompt, axis=1)
    return prompts[mask].copy()


def routine_task_items(sheet_id: str, routine_id: str, *, current_week_only: bool = False) -> pd.DataFrame:
    prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        return prompts
    mask = prompts.apply(lambda r: task_prompt_matches_parent(r, routine_id, "routine"), axis=1)
    df = prompts[mask].copy()
    if current_week_only and not df.empty:
        start, end, _ = _week_bounds_for_settings(sheet_id)
        df = df[df.apply(lambda r: _row_date_in_range(r, start, end), axis=1)].copy()
    return df


def action_task_items(sheet_id: str, action_id: str) -> pd.DataFrame:
    prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        return prompts
    mask = prompts.apply(lambda r: task_prompt_matches_action(r, action_id), axis=1)
    return prompts[mask].copy()


def plain_task_label_for_status(row: pd.Series) -> str:
    try:
        return _task_sync_user_label(row)
    except Exception:
        status = str(row.get("google_task_status", "") or row.get("status", "") or "").strip()
        return "Completed in Google Tasks" if status.lower() == "completed" else "Pending in Google Tasks" if status else "Not sent to Google Tasks"


def render_completion_summary(done: int, total: int, label: str) -> None:
    st.markdown(progress_bar_html(done, total, label), unsafe_allow_html=True)


def routine_weekly_completion_summary(sheet_id: str) -> tuple[int, int, str]:
    prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        return 0, 0, "Monday"
    start, end, week_start = _week_bounds_for_settings(sheet_id)
    def _routine_week_row(row: pd.Series) -> bool:
        source_type = str(row.get("source_record_type", "") or row.get("linked_record_type", "") or "").lower()
        parent_type = str(row.get("linked_parent_type", "") or "").lower()
        return ("routine" in source_type or "routine" in parent_type) and _row_date_in_range(row, start, end)
    weekly = prompts[prompts.apply(_routine_week_row, axis=1)].copy()
    done, total = completion_counts(weekly)
    return done, total, week_start


def project_overall_completion_summary(sheet_id: str) -> tuple[int, int]:
    goals = active_online_df(read_online_table(sheet_id, "goals"))
    if goals.empty or "goal_id" not in goals.columns:
        return 0, 0
    done_total = 0
    item_total = 0
    for _, goal in goals.iterrows():
        status = str(goal.get("status", "") or "").strip().lower()
        if status in {"on hold", "paused", "closed", "abandoned", "archived"}:
            continue
        items = project_task_items(sheet_id, str(goal.get("goal_id", "") or ""))
        done, total = completion_counts(items)
        done_total += done
        item_total += total
    return done_total, item_total

def render_google_tasks_export_manager(sheet_id: str) -> None:
    st.subheader("Google Tasks Sync")
    st.write("Use Google Tasks as the daily checklist surface. Pathmark remains the planning source of truth, while Google Tasks can carry completion status back into Pathmark.")
    st.info("Tasks Sync actions are optional and user-controlled. Your Google connection may already include Tasks permission, but Pathmark only creates or updates Pathmark checklist items when you press a sync button.")

    scopes_ready = google_tasks_scope_ready()
    if not scopes_ready:
        st.warning("Google Tasks permission is not available in this session. Reconnect Google to use direct Tasks sync.")
        auth_url = google_auth_url(GOOGLE_TASKS_SCOPES, return_hint="tasks_sync")
        if auth_url:
            st.link_button("Reconnect Google and enable Tasks sync", auth_url, use_container_width=True)
        st.caption("Pathmark uses Tasks access only for Pathmark Tasks Sync actions. No refresh token is stored by the hosted app.")

    prompts = staged_task_prompts(sheet_id)
    sync_stats = google_tasks_sync_summary(sheet_id)
    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-tile"><div class="metric-label">Ready to sync</div><div class="metric-value">{sync_stats['total']}</div></div>
      <div class="metric-tile"><div class="metric-label">Linked to Google</div><div class="metric-value">{sync_stats['linked']}</div></div>
      <div class="metric-tile"><div class="metric-label">Completed in Google</div><div class="metric-value">{sync_stats['completed']}</div></div>
      <div class="metric-tile {'warning' if sync_stats['missing'] else ''}"><div class="metric-label">Needs review</div><div class="metric-value">{sync_stats['missing']}</div></div>
    </div>
    """, unsafe_allow_html=True)

    backup_before_tasks_sync = st.checkbox("Create a safety backup before Tasks sync", value=False, key="backup_before_tasks_sync", help="Recommended. This backs up Pathmark Sync before sync metadata or completion status is written back to the sheet.")
    c1, c2 = st.columns(2)
    if c1.button("Push Pathmark checklist items to Google Tasks", use_container_width=True, disabled=prompts.empty or not scopes_ready):
        if backup_before_tasks_sync:
            create_pathmark_sync_backup(sheet_id)
        ok, message = push_pathmark_tasks_to_google(sheet_id, prompts)
        if ok:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()
    if c2.button("Pull completion status from Google Tasks", use_container_width=True, disabled=not scopes_ready):
        if backup_before_tasks_sync:
            create_pathmark_sync_backup(sheet_id)
        ok, message = pull_google_task_status_to_pathmark(sheet_id)
        if ok:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()

    if st.button("Repair missing Google Task links", use_container_width=True, disabled=prompts.empty or not scopes_ready, help="Use this if Google Tasks were created but Pathmark did not store their IDs. It matches Pathmark checklist items to Google Tasks by title and due date."):
        repaired, message = repair_google_task_links_by_title_due(sheet_id, prompts)
        if repaired:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()
    if st.session_state.get("google_tasks_last_issue"):
        st.caption("Last Tasks sync issue: " + str(st.session_state.get("google_tasks_last_issue")))

    st.caption("Google Tasks due dates are date-based. Calendar time and durations stay in Pathmark/Google Calendar. Deleted or missing Google Tasks are flagged for review rather than deleted from Pathmark.")

    if prompts.empty:
        st.info("No Google Tasks checklist items are staged yet. Add a project step or routine activity.")
    else:
        st.markdown("### Checklist items")
        for _, row in prompts.iterrows():
            title = html.escape(str(row.get("title", "Checklist item") or "Checklist item"))
            due = human_calendar_datetime(str(row.get("due_date", "") or ""))
            area = html.escape(str(row.get("area_name", "") or ""))
            task_list = html.escape(str(row.get("task_list", "Pathmark") or "Pathmark"))
            user_status = _task_sync_user_label(row)
            synced = str(row.get("google_task_synced_at", "") or "")
            status_line = user_status
            if synced:
                status_line += f" · Last checked: {synced}"
            st.markdown(
                f"""
                <div class='step-card'>
                  <h3>{title}</h3>
                  <p><strong>{html.escape(due) if due else 'No due date yet'}</strong></p>
                  <p>{'Area: ' + area + ' · ' if area else ''}Task list: {task_list}</p>
                  <p>{html.escape(status_line)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with st.expander("Show sync details", expanded=False):
            dataframe_preview(prompts, ["title", "area_name", "due_date", "source_record_type", "google_task_id", "google_task_status", "google_task_completed_at", "sync_status"])
    if "google_tasks_repair_results" in st.session_state:
        with st.expander("Last Google Tasks repair diagnostics", expanded=False):
            diag = st.session_state.get("google_tasks_repair_results")
            if isinstance(diag, pd.DataFrame):
                dataframe_preview(diag, ["Pathmark item", "Pathmark due", "Google candidate", "Google due", "Result", "Reason"])

    with st.expander("CSV / Sheet fallback", expanded=False):
        st.write("Keep this fallback if you want to inspect or manually process the staged task rows outside Pathmark.")
        st.download_button("Download Google Tasks CSV", data=build_google_tasks_csv(prompts), file_name="pathmark_google_tasks.csv", mime="text/csv", use_container_width=True, disabled=prompts.empty)
        if st.button("Write Google Tasks export to my sync sheet", use_container_width=True, disabled=prompts.empty):
            ok, message = write_google_tasks_export_tab(sheet_id, prompts)
            if ok:
                st.success(message)
            else:
                st.warning(safe_user_message(message))

    if not prompts.empty:
        st.info("Google Tasks sync does not archive items. Tasks can be pending or completed in Google Tasks while the source project step or routine activity remains visible in Pathmark.")
        if st.button("Mark Google Tasks rows as synced/exported", use_container_width=True):
            ids = prompts.get("id", pd.Series(dtype=str)).dropna().astype(str).tolist()
            ok, message = mark_actions_exported(sheet_id, ids, "google_tasks", archive=False)
            if ok:
                st.success(message)
            else:
                st.warning(safe_user_message(message))
            st.rerun()


def sync_pathmark_calendar_and_tasks(sheet_id: str, *, create_backup: bool = False) -> tuple[bool, str]:
    """Push Pathmark's current plan to Google Calendar and Google Tasks together.

    Pathmark is treated as the planning source of truth: if stored Google IDs
    exist, the matching Calendar event or Task is patched with the current
    Pathmark title/date/notes. If no ID is stored, Pathmark creates the missing
    Google item and writes the returned ID back to Pathmark Sync.
    """
    messages: list[str] = []
    overall_ok = True
    if create_backup:
        backup_ok, _backup_url, backup_msg = create_pathmark_sync_backup(sheet_id)
        messages.append(backup_msg)
        if not backup_ok:
            return False, "Could not create the requested backup, so sync was not run. " + safe_user_message(backup_msg)
    blocks = staged_calendar_blocks(sheet_id)
    prompts = staged_task_prompts(sheet_id)
    if blocks.empty and prompts.empty:
        return False, "No calendar time or Google Tasks checklist items are staged yet."
    if blocks.empty:
        messages.append("No Google Calendar items were staged.")
    else:
        ok_cal, msg_cal = push_pathmark_calendar_to_google(sheet_id, blocks)
        overall_ok = overall_ok and ok_cal
        messages.append(msg_cal)
    # Refresh after calendar sync so Google Task notes can include any updated calendar reference.
    prompts = staged_task_prompts(sheet_id)
    if prompts.empty:
        messages.append("No Google Tasks checklist items were staged.")
    else:
        ok_tasks, msg_tasks = push_pathmark_tasks_to_google(sheet_id, prompts)
        overall_ok = overall_ok and ok_tasks
        messages.append(msg_tasks)
    clear_online_cache(sheet_id)
    return overall_ok, " ".join([m for m in messages if str(m).strip()])


def pull_google_sync_status_to_pathmark(sheet_id: str, *, pull_calendar: bool = True, pull_tasks: bool = True) -> tuple[bool, str]:
    messages: list[str] = []
    overall_ok = True
    if pull_calendar:
        ok_cal, msg_cal = pull_google_calendar_status_to_pathmark(sheet_id)
        overall_ok = overall_ok and ok_cal
        messages.append(msg_cal)
    if pull_tasks:
        ok_tasks, msg_tasks = pull_google_task_status_to_pathmark(sheet_id)
        overall_ok = overall_ok and ok_tasks
        messages.append(msg_tasks)
    clear_online_cache(sheet_id)
    return overall_ok, " ".join([m for m in messages if str(m).strip()])




def google_sync_manageable_items(sheet_id: str) -> pd.DataFrame:
    """Return Pathmark actions that can be moved or deleted with their linked Google items."""
    actions = read_online_table(sheet_id, "actions")
    if actions.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    goals, routines = parent_lookup(sheet_id)
    for _, action in actions.iterrows():
        status = str(action.get("status", "") or "").strip().lower()
        if status in {"archived", "retired"}:
            continue
        has_calendar = truthy_flag(action.get("calendar_block")) or bool(str(action.get("google_calendar_event_id", "") or "").strip())
        has_task = truthy_flag(action.get("reminder")) or bool(str(action.get("google_task_id", "") or "").strip())
        if not (has_calendar or has_task):
            continue
        aid = str(action.get("action_id", "") or "").strip()
        if not aid:
            continue
        goal_id = str(action.get("goal_id", "") or "")
        routine_id = str(action.get("routine_id", "") or "")
        parent = routines.get(routine_id, {}).get("title") or goals.get(goal_id, {}).get("title") or ""
        item_type = str(action.get("item_type", "") or "project_step").replace("_", " ").strip().title()
        scheduled = str(action.get("scheduled_date", "") or action.get("due_date", "") or "").strip()
        if not scheduled and routine_id:
            scheduled = str(routines.get(routine_id, {}).get("next_due", "") or "").strip()
        rows.append({
            "action_id": aid,
            "title": str(action.get("title", "") or "Untitled planning item"),
            "parent": str(parent or ""),
            "area_name": str(action.get("area_name", "") or ""),
            "item_type": item_type,
            "scheduled_date": scheduled,
            "calendar_start_time": str(action.get("calendar_start_time", "") or "09:00"),
            "calendar_end_time": str(action.get("calendar_end_time", "") or "10:00"),
            "calendar_end_date": str(action.get("calendar_end_date", "") or ""),
            "google_calendar_event_id": str(action.get("google_calendar_event_id", "") or ""),
            "google_calendar_id": str(action.get("google_calendar_id", "") or ""),
            "google_task_id": str(action.get("google_task_id", "") or ""),
            "google_task_list_id": str(action.get("google_task_list_id", "") or ""),
            "label": f"{action.get('title', 'Untitled')} — {item_type}{' · ' + str(parent) if parent else ''}",
        })
    return pd.DataFrame(rows)


def _delete_google_calendar_event_for_action(action: pd.Series) -> tuple[bool, str]:
    event_id = str(action.get("google_calendar_event_id", "") or "").strip()
    calendar_id = str(action.get("google_calendar_id", "") or "").strip()
    if not event_id:
        return True, "No linked Google Calendar event to delete."
    if not calendar_id:
        return False, "This item has a Google Calendar event ID but no stored calendar ID. Pull or repair Google status first."
    service = calendar_service()
    if service is None:
        return False, "Google Calendar access is not available for this session."
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True, "Deleted the linked Google Calendar event."
    except Exception as exc:
        detail = _sync_error_detail(exc)
        if "404" in detail or "not found" in detail.lower() or "gone" in detail.lower():
            return True, "The linked Google Calendar event was already missing."
        return False, "Could not delete the linked Google Calendar event: " + safe_user_message(detail)


def _delete_google_task_by_ids(task_list_id: str, task_id: str) -> tuple[bool, str]:
    if not task_id:
        return True, "No linked Google Task to delete."
    service = tasks_service()
    if service is None:
        return False, "Google Tasks access is not available for this session."
    list_id = str(task_list_id or "").strip()
    if not list_id:
        ok, list_id, msg = get_or_create_google_task_list("Pathmark")
        if not ok or not list_id:
            return False, msg
    try:
        service.tasks().delete(tasklist=list_id, task=task_id).execute()
        return True, "Deleted a linked Google Task."
    except Exception as exc:
        detail = _sync_error_detail(exc)
        if "404" in detail or "not found" in detail.lower() or "gone" in detail.lower():
            return True, "A linked Google Task was already missing."
        return False, "Could not delete a linked Google Task: " + safe_user_message(detail)


def delete_linked_google_items_for_action(sheet_id: str, action_id: str, *, archive_pathmark_item: bool = False) -> tuple[bool, str]:
    """Delete the Google Calendar event and Google Task(s) linked to one Pathmark action."""
    actions = read_online_table(sheet_id, "actions")
    if actions.empty or "action_id" not in actions.columns:
        return False, "Could not find Pathmark actions."
    matches = actions[actions["action_id"].fillna("").astype(str).eq(str(action_id))]
    if matches.empty:
        return False, "Could not find that planning item in Pathmark."
    action = matches.iloc[0]
    messages: list[str] = []
    overall_ok = True
    ok_cal, msg_cal = _delete_google_calendar_event_for_action(action)
    overall_ok = overall_ok and ok_cal
    messages.append(msg_cal)
    ok_task, msg_task = _delete_google_task_by_ids(str(action.get("google_task_list_id", "") or ""), str(action.get("google_task_id", "") or ""))
    overall_ok = overall_ok and ok_task
    messages.append(msg_task)

    prompts = read_online_table(sheet_id, "task_prompts")
    linked_prompt_ids: list[str] = []
    if not prompts.empty and "linked_record_id" in prompts.columns:
        linked = prompts[prompts["linked_record_id"].fillna("").astype(str).eq(str(action_id))].copy()
        for _, prompt in linked.iterrows():
            pid = str(prompt.get("prompt_id", "") or "").strip()
            if not pid:
                continue
            linked_prompt_ids.append(pid)
            ok_prompt, msg_prompt = _delete_google_task_by_ids(str(prompt.get("google_task_list_id", "") or ""), str(prompt.get("google_task_id", "") or ""))
            overall_ok = overall_ok and ok_prompt
            messages.append(msg_prompt)
            prompt_updates = {
                "google_task_list_id": "",
                "google_task_id": "",
                "google_task_status": "",
                "google_task_completed_at": "",
                "google_task_updated_at": "",
                "google_task_synced_at": "",
                "sync_status": "not_synced",
            }
            if archive_pathmark_item:
                prompt_updates["status"] = "Archived"
                prompt_updates["archived_at"] = utc_now_text()
                prompt_updates["archived_reason"] = "Deleted with linked planning item."
            update_online_record(sheet_id, "task_prompts", pid, prompt_updates)

    action_updates = {
        "google_calendar_event_id": "",
        "google_calendar_id": "",
        "google_calendar_status": "deleted_in_google",
        "google_calendar_updated_at": "",
        "google_calendar_synced_at": utc_now_text(),
        "calendar_sync_status": "not_synced",
        "google_task_list_id": "",
        "google_task_id": "",
        "google_task_status": "",
        "google_task_completed_at": "",
        "google_task_updated_at": "",
        "google_task_synced_at": utc_now_text(),
        "sync_status": "not_synced",
    }
    if archive_pathmark_item:
        action_updates["status"] = "Archived"
        action_updates["archived_at"] = utc_now_text()
        action_updates["archived_reason"] = "Deleted from Google Calendar and Google Tasks together."
    ok_update, update_msg = update_online_record(sheet_id, "actions", str(action_id), action_updates)
    overall_ok = overall_ok and bool(ok_update)
    if not ok_update:
        messages.append("Google cleanup ran, but Pathmark could not update the source row: " + safe_user_message(update_msg))
    clear_online_cache(sheet_id)
    suffix = " The Pathmark item was archived." if archive_pathmark_item else " The Pathmark item remains in Pathmark and can be synced again later."
    return overall_ok, " ".join([m for m in messages if str(m).strip()]) + suffix


def move_linked_planning_item(sheet_id: str, action_id: str, *, start_date: date, end_date: date | None, start_time: time, end_time: time, create_backup: bool = False) -> tuple[bool, str]:
    """Move a Pathmark action and resync its paired Google Calendar/Tasks items."""
    if create_backup:
        backup_ok, _backup_url, backup_msg = create_pathmark_sync_backup(sheet_id)
        if not backup_ok:
            return False, "Could not create the requested backup, so the item was not moved. " + safe_user_message(backup_msg)
    actions = read_online_table(sheet_id, "actions")
    if actions.empty or "action_id" not in actions.columns:
        return False, "Could not find Pathmark actions."
    matches = actions[actions["action_id"].fillna("").astype(str).eq(str(action_id))]
    if matches.empty:
        return False, "Could not find that planning item in Pathmark."
    action = matches.iloc[0]
    item_type = str(action.get("item_type", "") or "").strip().lower()
    is_focus = item_type in {"project_focus", "focus_block", "focus block"}
    start_iso = start_date.isoformat()
    end_iso = (end_date or start_date).isoformat()
    updates = {
        "scheduled_date": start_iso,
        "due_date": start_iso,
        "calendar_start_time": start_time.strftime("%H:%M"),
        "calendar_end_time": end_time.strftime("%H:%M"),
    }
    if is_focus:
        updates["calendar_end_date"] = end_iso
    else:
        updates["calendar_end_date"] = end_iso if end_iso != start_iso else ""
    ok_update, msg_update = update_online_record(sheet_id, "actions", str(action_id), updates)
    if not ok_update:
        return False, safe_user_message(msg_update)

    prompts = read_online_table(sheet_id, "task_prompts")
    if not prompts.empty and "linked_record_id" in prompts.columns:
        linked = prompts[prompts["linked_record_id"].fillna("").astype(str).eq(str(action_id))].copy()
        for _, prompt in linked.iterrows():
            pid = str(prompt.get("prompt_id", "") or "").strip()
            if pid:
                update_online_record(sheet_id, "task_prompts", pid, {"due_date": start_iso})
    clear_online_cache(sheet_id)
    ok_sync, msg_sync = sync_pathmark_calendar_and_tasks(sheet_id, create_backup=False)
    if ok_sync:
        return True, "Moved the Pathmark item and updated its linked Google Calendar/Tasks items. " + msg_sync
    return False, "The Pathmark item was moved, but Google sync needs review: " + safe_user_message(msg_sync)


def render_linked_item_move_delete_manager(sheet_id: str) -> None:
    st.markdown("### Move or delete a linked planning item")
    st.caption("Use this when a calendar block and its Google Task should move or be removed together. Pathmark updates its own row first, then updates or deletes the linked Google items.")
    items = google_sync_manageable_items(sheet_id)
    if items.empty:
        st.info("No linked planning items are available to move or delete yet.")
        return
    labels = [str(row.get("label", "Untitled")) for _, row in items.iterrows()]
    choice = st.selectbox("Planning item", labels, key="linked_item_move_delete_choice")
    selected = items[items["label"].astype(str).eq(str(choice))].iloc[0]
    aid = str(selected.get("action_id", "") or "")
    st.markdown(
        f"""
        <div class='pathmark-note'>
          <strong>{html.escape(str(selected.get('title', '') or 'Untitled'))}</strong><br>
          {html.escape(str(selected.get('item_type', '') or 'Planning item'))}
          {(' · ' + html.escape(str(selected.get('parent', '') or ''))) if str(selected.get('parent', '') or '').strip() else ''}<br>
          Calendar link: {'yes' if str(selected.get('google_calendar_event_id', '') or '').strip() else 'not yet'} · Google Task link: {'yes' if str(selected.get('google_task_id', '') or '').strip() else 'not yet'}
        </div>
        """,
        unsafe_allow_html=True,
    )
    tab_move, tab_delete = st.tabs(["Move / reschedule", "Delete / remove"])
    with tab_move:
        d_default = parse_online_date(selected.get("scheduled_date")) or date.today()
        end_default = parse_online_date(selected.get("calendar_end_date")) or d_default
        t_start = parse_online_time(selected.get("calendar_start_time") or "09:00", "09:00")
        t_end = parse_online_time(selected.get("calendar_end_time") or "10:00", "10:00")
        c1, c2 = st.columns(2)
        new_start = c1.date_input("Start date", value=d_default, format="DD/MM/YYYY", key=f"move_start_{aid}")
        new_end = c2.date_input("Finish date", value=end_default, format="DD/MM/YYYY", key=f"move_end_{aid}")
        c3, c4 = st.columns(2)
        new_start_time = c3.time_input("Start time", value=t_start, key=f"move_start_time_{aid}")
        new_end_time = c4.time_input("Finish time", value=t_end, key=f"move_end_time_{aid}")
        backup_move = st.checkbox("Create a safety backup before moving", value=True, key=f"move_backup_{aid}")
        if st.button("Move Pathmark item and linked Google items", use_container_width=True, key=f"move_linked_item_{aid}"):
            ok, message = move_linked_planning_item(sheet_id, aid, start_date=new_start, end_date=new_end, start_time=new_start_time, end_time=new_end_time, create_backup=backup_move)
            if ok:
                st.success(message)
            else:
                st.warning(safe_user_message(message))
            st.rerun()
    with tab_delete:
        st.write("Remove the linked Google Calendar event and Google Task together. You can either keep the Pathmark item for later resyncing, or archive it at the same time.")
        archive_item = st.checkbox("Also archive the Pathmark item", value=False, key=f"delete_archive_{aid}")
        confirm = st.text_input("Type DELETE to confirm", key=f"delete_confirm_{aid}")
        disabled = confirm.strip().upper() != "DELETE"
        if st.button("Delete linked Google Calendar event and Google Task", type="primary", use_container_width=True, disabled=disabled, key=f"delete_linked_item_{aid}"):
            ok, message = delete_linked_google_items_for_action(sheet_id, aid, archive_pathmark_item=archive_item)
            if ok:
                st.success(message)
            else:
                st.warning(safe_user_message(message))
            st.rerun()

def render_google_sync_manager(sheet_id: str) -> None:
    st.subheader("Google Sync")
    st.write("Sync Google Calendar and Google Tasks together so the planned time and checklist item stay paired. Pathmark is the planning source of truth; existing linked Google items are updated from Pathmark rather than duplicated.")

    calendar_ready = google_calendar_scope_ready()
    tasks_ready = google_tasks_scope_ready()
    if not calendar_ready or not tasks_ready:
        st.warning("Google Calendar and Google Tasks permissions are both needed for combined sync.")
        needed_scopes: list[str] = []
        if not calendar_ready:
            needed_scopes += GOOGLE_CALENDAR_SCOPES
        if not tasks_ready:
            needed_scopes += GOOGLE_TASKS_SCOPES
        auth_url = google_auth_url(needed_scopes, return_hint="combined_sync")
        if auth_url:
            st.link_button("Reconnect Google and enable Calendar + Tasks sync", auth_url, use_container_width=True)
        st.caption("Pathmark only creates or updates Google Calendar events and Google Tasks when you run a sync action.")

    blocks = staged_calendar_blocks(sheet_id)
    prompts = staged_task_prompts(sheet_id)
    cal_stats = google_calendar_sync_summary(sheet_id)
    task_stats = google_tasks_sync_summary(sheet_id)
    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-tile"><div class="metric-label">Calendar ready</div><div class="metric-value">{len(blocks) if not blocks.empty else 0}</div></div>
      <div class="metric-tile"><div class="metric-label">Calendar linked</div><div class="metric-value">{cal_stats.get('linked', 0)}</div></div>
      <div class="metric-tile"><div class="metric-label">Tasks ready</div><div class="metric-value">{len(prompts) if not prompts.empty else 0}</div></div>
      <div class="metric-tile"><div class="metric-label">Tasks linked</div><div class="metric-value">{task_stats.get('linked', 0)}</div></div>
    </div>
    """, unsafe_allow_html=True)

    backup_before_sync = st.checkbox("Create a safety backup before combined sync", value=False, key="backup_before_combined_sync")
    disabled = (blocks.empty and prompts.empty) or not (calendar_ready and tasks_ready)
    if st.button("Sync Google Calendar and Google Tasks", use_container_width=True, disabled=disabled):
        ok, message = sync_pathmark_calendar_and_tasks(sheet_id, create_backup=backup_before_sync)
        if ok:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()

    st.caption("If a Pathmark row already has a stored Google Calendar event ID or Google Task ID, Pathmark updates that matched Google item. If no ID is stored, Pathmark creates the item and saves the returned ID for next time.")

    with st.expander("Move or delete linked items", expanded=False):
        render_linked_item_move_delete_manager(sheet_id)

    c1, c2 = st.columns(2)
    if c1.button("Pull Google status", use_container_width=True, disabled=not (calendar_ready and tasks_ready)):
        ok, message = pull_google_sync_status_to_pathmark(sheet_id)
        if ok:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()
    if c2.button("Repair missing Google links", use_container_width=True, disabled=not (calendar_ready and tasks_ready)):
        repaired_cal, cal_msg = repair_google_calendar_links_by_title_time(sheet_id, blocks)
        repaired_tasks, task_msg = repair_google_task_links_by_title_due(sheet_id, prompts)
        message = f"{cal_msg} {task_msg}"
        if repaired_cal or repaired_tasks:
            st.success(message)
        else:
            st.warning(safe_user_message(message))
        st.rerun()

    with st.expander("Calendar details", expanded=False):
        if blocks.empty:
            st.info("No Google Calendar items are staged yet.")
        else:
            dataframe_preview(blocks, ["title", "area_name", "start", "end", "recurrence", "linked_record_id", "all_day"])
    with st.expander("Google Tasks details", expanded=False):
        if prompts.empty:
            st.info("No Google Tasks checklist items are staged yet.")
        else:
            dataframe_preview(prompts, ["title", "area_name", "due_date", "source_record_type", "google_task_id", "google_task_status", "sync_status"])
    st.caption("Printable tasklists now live in the Tasklist tab so Google Sync stays focused on Calendar and Tasks.")


def render_archive_manager(sheet_id: str) -> None:
    st.subheader("Archive")
    st.write("Archive is for completed or retired projects, routines and activities that you no longer want in the active tabs. Paused items stay in their original tabs so they can be restarted later, and exports do not move anything here automatically.")
    table_specs = [
        ("areas", "Areas", "area_id", "area_name", ["area_name", "description", "updated_at", "archived_at", "archived_reason"]),
        ("goals", "Projects", "goal_id", "title", ["title", "area_name", "status", "updated_at", "archived_at", "archived_reason"]),
        ("routines", "Routines", "routine_id", "title", ["title", "area_name", "status", "updated_at", "archived_at", "archived_reason"]),
        ("actions", "Project and routine activities", "action_id", "title", ["title", "area_name", "status", "export_type", "exported_at", "archived_at", "archived_reason"]),
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
                if ok:
                    st.success("Restored to the active workspace.")
                else:
                    st.warning(safe_user_message(message))
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

    with st.expander("Week and completion settings", expanded=False):
        st.write("Choose how Pathmark groups weekly routine completion on the Dashboard and Routines tab.")
        current_week_start = online_setting(sheet_id, "week_starts_on", "Monday").strip().title() or "Monday"
        options = ["Monday", "Sunday"]
        selected_week_start = st.selectbox("Week starts on", options, index=options.index(current_week_start) if current_week_start in options else 0, key="settings_week_starts_on")
        if st.button("Save week setting", use_container_width=True):
            ok, msg = save_online_setting(sheet_id, "week_starts_on", selected_week_start, source="pathmark_settings")
            if ok:
                st.success("Week setting saved.")
                st.rerun()
            else:
                st.warning(safe_user_message(msg))

    with st.expander("Security & permissions", expanded=False):
        st.write("Pathmark keeps Google permissions as narrow and visible as possible.")
        st.markdown("""
        - Google login uses identity plus the limited `drive.file` permission so Pathmark can create and update Pathmark-owned Google Sheets.
        - Google Tasks Sync and Google Calendar Sync are optional. Their extra permissions are requested from the relevant sync tab when you choose to enable them.
        - Pathmark uses a dedicated Pathmark task list and calendars named after your Areas, with stored Google IDs so sync actions focus on linked Pathmark items.
        - OAuth tokens are used for the current session and should never be stored in Supabase, GitHub, logs, or user-visible error messages.
        - Backup, restore, reset, template import, and bulk sync actions include safety-backup options.
        - Resetting Pathmark Sync does not delete Google Tasks or Google Calendar items; those can be reviewed separately in Google.
        """)
        st.caption("You can revoke Pathmark's Google access from your Google Account at any time, or use Disconnect Google access in this settings page for the current session.")

    with st.expander("Backup & restore", expanded=False):
        st.write("Create a separate Google Sheet backup before making larger changes, or restore Pathmark Sync if something goes wrong.")
        st.caption("Backups copy Pathmark Online planning, tasklist, archive, spending-plan, Google Tasks and Google Calendar sync metadata into a separate user-owned Google Sheet. They do not copy or delete Google Calendar events or Google Tasks themselves.")
        bc1, bc2 = st.columns(2)
        if bc1.button("Create backup now", use_container_width=True, disabled=not bool(sheet_id)):
            ok, url, msg = create_pathmark_sync_backup(sheet_id)
            if ok:
                st.success(msg)
                st.link_button("Open backup Google Sheet", url, use_container_width=True)
            else:
                st.warning(safe_user_message(msg))
        ok_backups, backups, backup_msg = list_pathmark_backup_sheets(sheet_id) if sheet_id else (True, [], "No sync sheet selected.")
        if ok_backups and backups:
            labels = [f"{b.get('name','Untitled backup')} — {b.get('modifiedTime','')}" for b in backups]
            selected_label = st.selectbox("Restore from backup", labels, key="restore_backup_choice")
            selected = backups[labels.index(selected_label)] if selected_label in labels else backups[0]
            st.link_button("Open selected backup", selected.get("webViewLink", ""), use_container_width=True)
            confirm_restore = st.checkbox("I understand Pathmark will create a safety backup before restoring the selected backup.", key="confirm_restore_backup")
            if bc2.button("Restore selected backup", use_container_width=True, disabled=not confirm_restore):
                ok, msg = restore_pathmark_sync_from_backup(sheet_id, selected.get("id", ""))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.warning(safe_user_message(msg))
        elif ok_backups:
            st.info("No Pathmark backup sheets were found yet.")
        else:
            st.warning(safe_user_message(backup_msg))

        st.markdown("#### Backup cleanup")
        st.caption("Normal Google Tasks and Calendar sync no longer creates safety backups by default. Use this if earlier testing created too many backup sheets.")
        keep_n = st.number_input("Keep latest backups", min_value=1, max_value=50, value=5, step=1, key="backup_keep_latest")
        if st.button("Move older Pathmark backups to Google Drive Trash", use_container_width=True, disabled=not bool(sheet_id)):
            ok, msg = cleanup_old_pathmark_backups(sheet_id, int(keep_n))
            if ok:
                st.success(msg)
            else:
                st.warning(safe_user_message(msg))

    with st.expander("Restore Pathmark Sync to default", expanded=False):
        st.warning("This resets the active Pathmark Sync sheet back to Pathmark's default tab structure. Pathmark creates a separate backup first, but active projects, routines, areas, tasklist rows, Spending Plan rows and sync metadata will be cleared from the live sheet.")
        st.write("This does **not** delete Google Calendar events or Google Tasks. Any previously synced Google links may become stale after a reset.")
        include_examples = st.checkbox("Load starter examples after reset", value=False, key="restore_default_examples")
        confirm_default = st.text_input("Type RESTORE DEFAULT to confirm", value="", key="confirm_restore_default")
        if st.button("Restore Pathmark Sync to default", use_container_width=True, disabled=confirm_default.strip() != "RESTORE DEFAULT"):
            ok, msg = restore_pathmark_sync_to_default(sheet_id, include_starter_examples=include_examples)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.warning(safe_user_message(msg))

    with st.expander("Creation wizard", expanded=False):
        st.write("The creation wizard now has its own Planner tab beside Home.")
        latest = _latest_wizard_draft(sheet_id)
        if latest:
            label = latest.get("project", {}).get("title") if latest.get("wizard_type") == "project" else latest.get("routine", {}).get("title")
            label = label or ("Project draft" if latest.get("wizard_type") == "project" else "Routine draft")
            st.write(f"Unfinished draft available: **{label}**. Open the Creation Wizard tab to continue editing it.")
        else:
            st.write("No unfinished creation wizard draft is currently saved.")
    with st.expander("Advanced Google Sheet settings", expanded=False):
        render_google_sheets_oauth_diagnostics()
        sheet_url_input = st.text_input("Use an existing Pathmark Sync Google Sheet URL or ID", value=st.session_state.get("sync_sheet_id", ""), help="Use a Pathmark Sync sheet that belongs to your Google account. With the safer drive.file permission, Pathmark can only use files it created or files you explicitly authorise.")
        if sheet_url_input:
            st.session_state["sync_sheet_id"] = extract_google_sheet_id(sheet_url_input)
            clear_online_cache(st.session_state.get("sync_sheet_id", ""))
        if st.button("Find or create Pathmark Sync sheet", use_container_width=True):
            ok, new_sheet_id, message = ensure_pathmark_sync_sheet_ready()
            if ok:
                st.success("Pathmark sync sheet is ready.")
            else:
                st.warning(safe_user_message(message))
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
    st.info("Theme controls now sit in the top-level Theme tab beside Home and About & Privacy. Use Streamlit's built-in menu for System, Light or Dark, and use the Theme tab for the seasonal Pathmark accent.")




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
    task_title_style = ParagraphStyle("PathmarkTaskTitle", parent=body, fontSize=9.4, leading=12, textColor=colors.HexColor("#1F2221"))
    support_task_style = ParagraphStyle("PathmarkSupportTask", parent=body, fontSize=9.0, leading=11.5, leftIndent=7*mm, firstLineIndent=0, textColor=colors.HexColor("#1F2221"))
    small = ParagraphStyle("PathmarkSmall", parent=styles["BodyText"], fontSize=8.4, leading=11, textColor=colors.HexColor("#626966"))
    support_small = ParagraphStyle("PathmarkSupportSmall", parent=small, fontSize=8.1, leading=10.5, leftIndent=2*mm, textColor=colors.HexColor("#626966"))

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
            heading = "Project work" if source_type == "Goal action" else "Routine activities"
            story.append(Paragraph(clean_text(heading), h_style))
            data = [["", "Task", "Notes"]]
            table_commands = [
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
            ]
            for _, row in subset.iterrows():
                row_is_support = _tasklist_is_supporting_row(row)
                task_title = clean_text(row.get("title", "") or row.get("display_title", "") or "Untitled")
                notes_text = clean_text(tasklist_notes_text(row))
                row_number = len(data)
                if row_is_support:
                    task_para = Paragraph(f"<font color='#626966' size='7'>Supporting time block</font><br/><b>{task_title}</b>", support_task_style)
                    notes_para = Paragraph(notes_text, support_small)
                    table_commands.extend([
                        ("BACKGROUND", (1, row_number), (-1, row_number), colors.HexColor("#F4F6F5")),
                        ("LINEBEFORE", (1, row_number), (1, row_number), 1.6, colors.HexColor("#9BA7A1")),
                        ("LEFTPADDING", (1, row_number), (1, row_number), 16),
                    ])
                else:
                    task_para = Paragraph(f"<b>{task_title}</b>", task_title_style)
                    notes_para = Paragraph(notes_text, small)
                data.append([checkbox_box(), task_para, notes_para])
            table = Table(data, colWidths=[8*mm, 70*mm, 100*mm], repeatRows=1)
            table.setStyle(TableStyle(table_commands))
            story.append(table)
            story.append(Spacer(1, 8))

    if notes.strip():
        story.append(Paragraph("Notes", h_style))
        for line in notes.strip().splitlines():
            story.append(Paragraph(clean_text(line), body))
    try:
        doc.build(story)
        return buffer.getvalue()
    except Exception:
        return build_printable_tasklist_from_rows(rows)

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
        lines.append("Project work" if source_type == "Goal action" else "Routine activities")
        current_parent = None
        for _, row in subset.iterrows():
            parent = str(row.get("parent", "") or "").strip()
            if parent and parent != current_parent:
                lines.append(f"\n{parent}")
                current_parent = parent
            is_support = _tasklist_is_supporting_row(row)
            indent = "    " if is_support else ""
            title_text = row.get('title') or row.get('display_title') or 'Untitled'
            lines.append(f"{indent}☐ {title_text}")
            notes = re.sub(r"<br\s*/?>", " | ", tasklist_notes_text(row))
            if notes:
                lines.append(f"{indent}   {notes}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")




def render_exports_manager(sheet_id: str) -> None:
    st.subheader("Exports")
    st.write("Use the dedicated Google Calendar Sync, Google Tasks Sync, and Tasklist tabs to prepare files from your saved actions and routine activities.")
    c1, c2 = st.columns(2)
    with c1:
        render_google_calendar_export_manager(sheet_id)
    with c2:
        render_google_tasks_export_manager(sheet_id)


# ---------------------------------------------------------------------------
# Pathmark creation wizard
# ---------------------------------------------------------------------------

WIZARD_STATES = {"in_progress", "saved", "cancelled", "discarded"}
WIZARD_FREQ_OPTIONS = ["Daily", "Selected days", "Weekly"]
DAY_CODE = {"Monday": "MO", "Tuesday": "TU", "Wednesday": "WE", "Thursday": "TH", "Friday": "FR", "Saturday": "SA", "Sunday": "SU"}
CODE_DAY = {v: k for k, v in DAY_CODE.items()}


def _time_to_text(value: Any) -> str:
    if isinstance(value, time):
        return value.strftime("%H:%M")
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return datetime.strptime(text, "%H:%M").strftime("%H:%M")
    except Exception:
        pass
    try:
        return datetime.strptime(text, "%H:%M:%S").strftime("%H:%M")
    except Exception:
        return text


def _text_to_time(value: Any, fallback: time = time(9, 0)) -> time:
    text = str(value or "").strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M%p", "%I:%M %p"):
        try:
            return datetime.strptime(text, fmt).time()
        except Exception:
            pass
    return fallback


def _is_valid_time_text(value: Any) -> bool:
    """Return True only for an explicit, parseable clock time."""
    text = str(value or "").strip()
    if not text:
        return False
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M%p", "%I:%M %p"):
        try:
            datetime.strptime(text, fmt)
            return True
        except Exception:
            pass
    return False


def _date_to_text(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return normalise_online_date(value)


def _text_to_date(value: Any, fallback: date | None = None) -> date:
    text = _date_to_text(value)
    if text:
        try:
            return date.fromisoformat(text)
        except Exception:
            pass
    return fallback or date.today()


def _minutes_between(start_text: str, end_text: str, ends_next_day: bool = False) -> int:
    start = _text_to_time(start_text, time(9, 0))
    end = _text_to_time(end_text, time(10, 0))
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today() + timedelta(days=1 if ends_next_day else 0), end)
    if end_dt <= start_dt:
        return 0
    return int((end_dt - start_dt).total_seconds() // 60)


def _calendar_minutes(start_date: Any, start_text: Any, end_date: Any, end_text: Any) -> int:
    start_d = _text_to_date(start_date)
    end_d = _text_to_date(end_date, start_d)
    start_dt = datetime.combine(start_d, _text_to_time(start_text, time(9, 0)))
    end_dt = datetime.combine(end_d, _text_to_time(end_text, time(10, 0)))
    if end_dt <= start_dt:
        return 0
    return int((end_dt - start_dt).total_seconds() // 60)


def _calendar_end_date_default(item: dict[str, Any], start_date_value: Any) -> date:
    start_d = _text_to_date(start_date_value)
    existing = str(item.get("calendar_end_date", "") or "").strip()
    if existing:
        return _text_to_date(existing, start_d)
    if bool(item.get("ends_next_day")):
        return start_d + timedelta(days=1)
    return start_d


def _format_time_range(start_text: str, end_text: str, ends_next_day: bool = False) -> str:
    start = _text_to_time(start_text).strftime("%-I:%M%p").lower().replace(":00", "")
    end = _text_to_time(end_text).strftime("%-I:%M%p").lower().replace(":00", "")
    return f"{start} to {end}{' next day' if ends_next_day else ''}"


def _format_time_range_with_dates(start_date: Any, start_text: Any, end_date: Any, end_text: Any) -> str:
    start_d = _text_to_date(start_date)
    end_d = _text_to_date(end_date, start_d)
    start = _text_to_time(start_text).strftime("%-I:%M%p").lower().replace(":00", "")
    end = _text_to_time(end_text).strftime("%-I:%M%p").lower().replace(":00", "")
    if end_d == start_d:
        return f"{start} to {end}"
    return f"{start} to {end} on {display_date(end_d.isoformat()) if 'display_date' in globals() else end_d.isoformat()}"


def _new_wizard_draft(wizard_type: str | None = None) -> dict[str, Any]:
    return {
        "draft_id": f"draft-{uuid.uuid4().hex}",
        "wizard_type": wizard_type or "",
        "current_step_key": "choose_type",
        "area": {"mode": "existing", "area_id": "", "area_name": "", "calendar_colour_id": "2", "calendar_colour_name": "Sage"},
        "project": {"title": "", "reason": "", "definition_of_done": "", "target_date": "", "target_label": "", "planning_mode": "Task-based"},
        "project_steps": [],
        "routine": {"title": "", "purpose": "", "frequency": "Daily", "preferred_days": [], "start_date": date.today().isoformat()},
        "routine_activities": [],
        "current_step_id": "",
        "current_activity_id": "",
        "current_task_id": "",
        "status": "in_progress",
        "created_at": utc_now_text(),
        "updated_at": utc_now_text(),
    }


def _wizard_to_record(draft: dict[str, Any]) -> dict[str, Any]:
    answers = {
        "area": draft.get("area", {}),
        "project": draft.get("project", {}),
        "routine": draft.get("routine", {}),
    }
    activities = {
        "project_steps": draft.get("project_steps", []),
        "routine_activities": draft.get("routine_activities", []),
    }
    return {
        "draft_id": draft.get("draft_id", f"draft-{uuid.uuid4().hex}"),
        "wizard_type": draft.get("wizard_type", ""),
        "current_step_key": draft.get("current_step_key", "choose_type"),
        "answers_json": json.dumps(answers, ensure_ascii=False),
        "activity_drafts_json": json.dumps(activities, ensure_ascii=False),
        "status": draft.get("status", "in_progress"),
        "created_at": draft.get("created_at", utc_now_text()),
        "updated_at": utc_now_text(),
        "saved_at": draft.get("saved_at", ""),
        "source": "pathmark_creation_wizard",
    }


def _wizard_from_record(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    rec = {k: str(row.get(k, "") or "") for k in ONLINE_TABLES.get("wizard_drafts", [])}
    answers: dict[str, Any] = {}
    activities: dict[str, Any] = {}
    try:
        answers = json.loads(rec.get("answers_json", "") or "{}")
    except Exception:
        answers = {}
    try:
        activities = json.loads(rec.get("activity_drafts_json", "") or "{}")
    except Exception:
        activities = {}
    draft = _new_wizard_draft(rec.get("wizard_type") or None)
    draft.update({
        "draft_id": rec.get("draft_id") or draft["draft_id"],
        "wizard_type": rec.get("wizard_type") or draft.get("wizard_type", ""),
        "current_step_key": rec.get("current_step_key") or "choose_type",
        "status": rec.get("status") or "in_progress",
        "created_at": rec.get("created_at") or utc_now_text(),
        "updated_at": rec.get("updated_at") or utc_now_text(),
        "saved_at": rec.get("saved_at") or "",
    })
    draft["area"].update(answers.get("area", {}) if isinstance(answers.get("area"), dict) else {})
    draft["project"].update(answers.get("project", {}) if isinstance(answers.get("project"), dict) else {})
    draft["routine"].update(answers.get("routine", {}) if isinstance(answers.get("routine"), dict) else {})
    draft["project_steps"] = activities.get("project_steps", []) if isinstance(activities.get("project_steps"), list) else []
    draft["routine_activities"] = activities.get("routine_activities", []) if isinstance(activities.get("routine_activities"), list) else []
    return draft


def _save_wizard_draft(sheet_id: str, draft: dict[str, Any]) -> tuple[bool, str]:
    draft["updated_at"] = utc_now_text()
    record = _wizard_to_record(draft)
    existing = read_online_table(sheet_id, "wizard_drafts")
    draft_id = str(record.get("draft_id", ""))
    if not existing.empty and draft_id and existing["draft_id"].fillna("").astype(str).eq(draft_id).any():
        return update_online_record(sheet_id, "wizard_drafts", draft_id, record)
    return append_online_record(sheet_id, "wizard_drafts", record)


def _latest_wizard_draft(sheet_id: str) -> dict[str, Any] | None:
    drafts = read_online_table(sheet_id, "wizard_drafts")
    if drafts.empty:
        return None
    active = drafts[drafts.get("status", pd.Series(dtype=str)).fillna("").str.lower().eq("in_progress")]
    if active.empty:
        return None
    active = active.copy()
    active["_updated"] = pd.to_datetime(active.get("updated_at", ""), errors="coerce")
    active = active.sort_values("_updated", ascending=False)
    return _wizard_from_record(active.iloc[0])


def _wizard_state() -> dict[str, Any] | None:
    draft = st.session_state.get("pathmark_creation_wizard")
    return draft if isinstance(draft, dict) else None


def _set_wizard_state(draft: dict[str, Any]) -> None:
    st.session_state["pathmark_creation_wizard"] = draft


def _clear_wizard_state() -> None:
    st.session_state.pop("pathmark_creation_wizard", None)


def _area_options(sheet_id: str) -> list[dict[str, str]]:
    areas = active_online_df(read_online_table(sheet_id, "areas"))
    rows = []
    for _, r in areas.iterrows():
        name = str(r.get("area_name", "") or "").strip()
        if name:
            rows.append({"area_id": str(r.get("area_id", "") or ""), "area_name": name, "colour": str(r.get("colour", "") or "")})
    return rows


def _wizard_area_ready(draft: dict[str, Any]) -> bool:
    area = draft.get("area", {})
    if area.get("mode") == "new":
        return bool(str(area.get("area_name", "")).strip() and str(area.get("calendar_colour_name", "")).strip())
    return bool(str(area.get("area_name", "")).strip())


def _find_step_by_id(items: list[dict[str, Any]], id_key: str, item_id: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get(id_key, "")) == str(item_id):
            return item
    return None


def _append_project_step(draft: dict[str, Any]) -> dict[str, Any]:
    planning_mode = str(draft.get("project", {}).get("planning_mode", "Task-based") or "Task-based")
    is_focus = planning_mode == "Focus-based"
    step = {
        "step_id": f"step-{uuid.uuid4().hex}",
        "title": "",
        "calendar_date": date.today().isoformat(),
        "calendar_start_time": "" if is_focus else "09:00",
        "calendar_end_time": "" if is_focus else "10:00",
        "calendar_end_date": date.today().isoformat(),
        "ends_next_day": False,
        "include_on_tasklist": True,
        "item_type": "project_focus" if is_focus else "project_progress",
        "contributes_to_progress": "1",
        "parent_progress_item_id": "",
        "has_helper_tasks": False,
        "helper_tasks": [],
    }
    draft.setdefault("project_steps", []).append(step)
    draft["current_step_id"] = step["step_id"]
    draft["current_task_id"] = ""
    return step


def _append_routine_activity(draft: dict[str, Any]) -> dict[str, Any]:
    activity = {
        "activity_id": f"activity-{uuid.uuid4().hex}",
        "title": "",
        # Routine activity times are deliberately blank until the user sets them.
        # These activities become mandatory calendar time, so the wizard should not
        # silently accept default times.
        "calendar_start_time": "",
        "calendar_end_time": "",
        "calendar_end_date": "",
        "ends_next_day": False,
        "location": "",
        "include_on_tasklist": True,
        "item_type": "project_progress",
        "contributes_to_progress": "1",
        "parent_progress_item_id": "",
        "has_helper_tasks": False,
        "helper_tasks": [],
    }
    draft.setdefault("routine_activities", []).append(activity)
    draft["current_activity_id"] = activity["activity_id"]
    draft["current_task_id"] = ""
    return activity


def _append_helper_task(parent: dict[str, Any]) -> dict[str, Any]:
    task = {"task_id": f"task-{uuid.uuid4().hex}", "title": "", "due": date.today().isoformat(), "task_kind": "helper"}
    parent.setdefault("helper_tasks", []).append(task)
    return task


def _routine_rrule(routine: dict[str, Any]) -> str:
    freq = str(routine.get("frequency", "Daily") or "Daily")
    if freq == "Daily":
        return "RRULE:FREQ=DAILY"
    days = routine.get("preferred_days", []) or []
    codes = [DAY_CODE.get(d, d) for d in days if d]
    if codes:
        return "RRULE:FREQ=WEEKLY;BYDAY=" + ",".join(codes)
    if freq == "Weekly":
        return "RRULE:FREQ=WEEKLY"
    return "RRULE:FREQ=DAILY"


def _routine_days_text(routine: dict[str, Any]) -> str:
    freq = str(routine.get("frequency", "Daily") or "Daily")
    if freq == "Daily":
        return "Every day"
    days = routine.get("preferred_days", []) or []
    return ", ".join(days) if days else "Weekly"


def _validate_project_step(step: dict[str, Any]) -> list[str]:
    problems = []
    is_focus = str(step.get("item_type", "") or "").strip().lower() in {"project_focus", "focus_block", "focus block"}
    if not str(step.get("title", "")).strip():
        problems.append("Add a focus block." if is_focus else "Add a project step.")
    if not _date_to_text(step.get("calendar_date")):
        problems.append("Choose the day this focus block starts." if is_focus else "Choose the day you will make time for this step.")
    if not _date_to_text(step.get("calendar_end_date")):
        problems.append("Choose the date this focus block finishes." if is_focus else "Choose the date this calendar time will finish.")
    if is_focus:
        start_d = _text_to_date(step.get("calendar_date"))
        end_d = _text_to_date(step.get("calendar_end_date"), start_d)
        if end_d < start_d:
            problems.append("The focus block finish date must be on or after the start date.")
        return problems
    if not _time_to_text(step.get("calendar_start_time")):
        problems.append("Choose a start time.")
    if not _time_to_text(step.get("calendar_end_time")):
        problems.append("Choose an end time.")
    if _calendar_minutes(step.get("calendar_date"), step.get("calendar_start_time", ""), step.get("calendar_end_date"), step.get("calendar_end_time", "")) <= 0:
        problems.append("The finish date and time must be after the start date and time.")
    return problems


def _validate_routine_activity(activity: dict[str, Any], routine_start_date: Any = None) -> list[str]:
    problems = []
    if not str(activity.get("title", "")).strip():
        problems.append("Add a routine activity.")
    if not _is_valid_time_text(activity.get("calendar_start_time")):
        problems.append("Choose a valid start time, such as 22:30.")
    if not _is_valid_time_text(activity.get("calendar_end_time")):
        problems.append("Choose a valid end time, such as 06:30.")
    if not _date_to_text(activity.get("calendar_end_date")):
        problems.append("Choose the date this calendar time will finish.")
    start_date_value = routine_start_date or activity.get("start_date", date.today().isoformat())
    if _calendar_minutes(start_date_value, activity.get("calendar_start_time", ""), activity.get("calendar_end_date"), activity.get("calendar_end_time", "")) <= 0:
        problems.append("The finish date and time must be after the start date and time.")
    return problems


def _validate_helper_task(task: dict[str, Any]) -> list[str]:
    problems = []
    if not str(task.get("title", "")).strip():
        problems.append("Add the checklist item text.")
    if not _date_to_text(task.get("due")):
        problems.append("Choose the date the checklist item should appear.")
    return problems


def _wizard_next_step(draft: dict[str, Any], current: str, answer: Any = None) -> str:
    wt = draft.get("wizard_type")
    if current == "choose_type":
        return "choose_area"
    if current == "choose_area":
        if draft.get("area", {}).get("mode") == "new":
            return "area_name"
        return "project_title" if wt == "project" else "routine_title"
    if current == "area_name":
        return "area_colour"
    if current == "area_colour":
        return "area_review"
    if current == "area_review":
        return "project_title" if wt == "project" else "routine_title"
    if wt == "project":
        planning_mode = str(draft.get("project", {}).get("planning_mode", "Task-based") or "Task-based")
        if planning_mode == "Focus-based":
            order = ["project_title", "project_reason", "project_done", "project_target", "project_planning_mode", "project_step_title", "project_calendar_date", "project_calendar_end_time", "project_add_step"]
        else:
            order = ["project_title", "project_reason", "project_done", "project_target", "project_planning_mode", "project_step_title", "project_calendar_date", "project_calendar_start_time", "project_calendar_end_time", "project_helper_task_choice"]
        if current in order:
            if current == "project_helper_task_choice":
                return "project_helper_task_item" if answer else "project_add_step"
            if current == "project_add_step":
                return "project_step_title" if answer else "project_review"
            return order[order.index(current)+1]
        if current == "project_helper_task_item":
            return "project_helper_task_due"
        if current == "project_helper_task_due":
            return "project_add_helper_task_item"
        if current == "project_add_helper_task_item":
            return "project_helper_task_item" if answer else "project_add_step"
    else:
        order = ["routine_title", "routine_purpose", "routine_frequency"]
        if current in order:
            if current == "routine_frequency":
                return "routine_days" if str(draft.get("routine", {}).get("frequency")) == "Selected days" else "routine_start_date"
            return order[order.index(current)+1]
        if current == "routine_days":
            return "routine_start_date"
        if current == "routine_start_date":
            return "routine_activity_title"
        order2 = ["routine_activity_title", "routine_calendar_start_time", "routine_calendar_end_time", "routine_calendar_location", "routine_helper_task_choice"]
        if current in order2:
            if current == "routine_helper_task_choice":
                return "routine_helper_task_item" if answer else "routine_add_activity"
            return order2[order2.index(current)+1]
        if current == "routine_helper_task_item":
            return "routine_helper_task_due"
        if current == "routine_helper_task_due":
            return "routine_add_helper_task_item"
        if current == "routine_add_helper_task_item":
            return "routine_helper_task_item" if answer else "routine_add_activity"
        if current == "routine_add_activity":
            return "routine_activity_title" if answer else "routine_review"
    return current


def _wizard_back_stack_key(draft_id: str) -> str:
    return f"wizard_back_stack::{draft_id}"


def _wizard_go(sheet_id: str, draft: dict[str, Any], next_step: str, push_current: bool = True) -> None:
    current = draft.get("current_step_key", "choose_type")
    if push_current and next_step != current:
        stack_key = _wizard_back_stack_key(str(draft.get("draft_id", "")))
        st.session_state.setdefault(stack_key, []).append(current)
    draft["current_step_key"] = next_step
    _set_wizard_state(draft)
    _save_wizard_draft(sheet_id, draft)
    st.rerun()


def _wizard_back(sheet_id: str, draft: dict[str, Any]) -> None:
    stack_key = _wizard_back_stack_key(str(draft.get("draft_id", "")))
    stack = st.session_state.get(stack_key, [])
    if stack:
        draft["current_step_key"] = stack.pop()
        st.session_state[stack_key] = stack
        _set_wizard_state(draft)
        _save_wizard_draft(sheet_id, draft)
        st.rerun()


def _wizard_area_id(sheet_id: str, draft: dict[str, Any]) -> tuple[str, str, str]:
    area = draft.get("area", {})
    if area.get("mode") == "new":
        name = str(area.get("area_name", "")).strip()
        existing = find_area_id(sheet_id, name)
        if existing:
            return existing, name, str(area.get("calendar_colour_name", "") or "Sage")
        area_id = f"area-{uuid.uuid4().hex}"
        colour = str(area.get("calendar_colour_name", "") or "Sage")
        append_online_record(sheet_id, "areas", {"area_id": area_id, "area_name": name, "description": "Created from the Pathmark creation wizard.", "colour": colour, "status": "Active", "default_calendar": name, "default_task_list": "Pathmark", "notes": "Created from the Pathmark creation wizard."})
        return area_id, name, colour
    name = str(area.get("area_name", "")).strip()
    return str(area.get("area_id", "") or find_area_id(sheet_id, name)), name, str(area.get("calendar_colour_name", "") or "")


def _append_task_prompt_records(sheet_id: str, prompts: list[dict[str, Any]]) -> tuple[bool, str]:
    if not prompts:
        return True, "No helper checklist items to save."
    return append_many_online_records(sheet_id, {"task_prompts": prompts})


def _final_save_wizard(sheet_id: str, draft: dict[str, Any]) -> tuple[bool, str]:
    if not _wizard_area_ready(draft):
        return False, "Choose or create an Area before saving."
    area_id, area_name, _colour = _wizard_area_id(sheet_id, draft)
    now = utc_now_text()
    records: dict[str, list[dict[str, Any]]] = {"goals": [], "routines": [], "actions": [], "task_prompts": []}
    if draft.get("wizard_type") == "project":
        project = draft.get("project", {})
        if not str(project.get("title", "")).strip() or not str(project.get("definition_of_done", "")).strip():
            return False, "Project title and definition of done are required."
        steps = draft.get("project_steps", []) or []
        if not steps:
            return False, "Add at least one project step before saving."
        for step in steps:
            problems = _validate_project_step(step)
            if problems:
                return False, " ".join(problems)
        goal_id = f"goal-{uuid.uuid4().hex}"
        records["goals"].append({"goal_id": goal_id, "area_id": area_id, "area_name": area_name, "title": str(project.get("title", "")).strip(), "description": str(project.get("reason", "")).strip(), "specific_area": "", "planning_mode": str(project.get("planning_mode", "Task-based") or "Task-based"), "status": "Active", "target_date": _date_to_text(project.get("target_date")), "purpose": str(project.get("reason", "")).strip(), "desired_outcome": str(project.get("definition_of_done", "")).strip(), "closure_criteria": str(project.get("definition_of_done", "")).strip(), "notes": "Created from the Pathmark creation wizard."})
        for idx, step in enumerate(steps, start=1):
            action_id = f"action-{uuid.uuid4().hex}"
            scheduled = _date_to_text(step.get("calendar_date"))
            end_date = _date_to_text(step.get("calendar_end_date")) or scheduled
            step_item_type = str(step.get("item_type", "project_progress") or "project_progress")
            is_focus_step = step_item_type == "project_focus"
            minutes = "" if is_focus_step else str(_calendar_minutes(scheduled, step.get("calendar_start_time"), end_date, step.get("calendar_end_time")))
            helper_titles = [] if is_focus_step else [str(t.get("title", "")).strip() for t in step.get("helper_tasks", []) if str(t.get("title", "")).strip()]
            notes = "Created from the Pathmark creation wizard."
            if is_focus_step:
                notes += " Focus block: all-day calendar item. Supporting time blocks can be added in the Projects tab."
            if end_date and end_date != scheduled:
                notes += f" Ends on {end_date}."
            if helper_titles:
                notes += "\nHelper checklist items:\n- " + "\n- ".join(helper_titles)
            title = str(step.get("title", "")).strip()
            linked_type = "project_focus" if is_focus_step else "project_step"
            records["task_prompts"].append({"prompt_id": f"prompt-{uuid.uuid4().hex}", "area_name": area_name, "title": title, "prompt_text": title, "due_date": scheduled, "task_kind": "activity", "linked_record_id": action_id, "linked_record_type": linked_type, "linked_parent_id": goal_id, "linked_parent_type": "project", "task_list": "Pathmark", "notes": f"Automatic checklist item for {'focus block' if is_focus_step else 'project step'}: {title}", "status": "Staged", "created_at": now, "updated_at": now, "source": "pathmark_creation_wizard"})
            records["actions"].append({"action_id": action_id, "goal_id": goal_id, "routine_id": "", "area_id": area_id, "area_name": area_name, "title": title, "description": title, "item_type": step_item_type, "contributes_to_progress": "1", "parent_progress_item_id": "", "status": "Scheduled", "priority": "Medium", "specific_area": "", "due_date": scheduled, "scheduled_date": scheduled, "activity_days": "", "estimated_minutes": minutes, "calendar_block": "1", "reminder": "1", "include_tasklist": "1", "first_step": title, "task_reminder_time": "", "calendar_start_time": "" if is_focus_step else _time_to_text(step.get("calendar_start_time")), "calendar_end_time": "" if is_focus_step else _time_to_text(step.get("calendar_end_time")), "calendar_end_date": end_date, "calendar_location": "", "notes": notes})
            for task in step.get("helper_tasks", []) or []:
                if str(task.get("title", "")).strip():
                    records["task_prompts"].append({"prompt_id": f"prompt-{uuid.uuid4().hex}", "area_name": area_name, "title": str(task.get("title", "")).strip(), "prompt_text": str(task.get("title", "")).strip(), "due_date": _date_to_text(task.get("due")) or scheduled, "task_kind": "helper", "linked_record_id": action_id, "linked_record_type": "project_step", "linked_parent_id": goal_id, "linked_parent_type": "project", "task_list": "Pathmark", "notes": f"Helper checklist item for project step: {title}", "status": "Staged", "created_at": now, "updated_at": now, "source": "pathmark_creation_wizard"})
    else:
        routine = draft.get("routine", {})
        if not str(routine.get("title", "")).strip():
            return False, "Routine title is required."
        if str(routine.get("frequency", "")) == "Selected days" and not routine.get("preferred_days"):
            return False, "Choose at least one day for this routine."
        activities = draft.get("routine_activities", []) or []
        if not activities:
            return False, "Add at least one routine activity before saving."
        for activity in activities:
            problems = _validate_routine_activity(activity, routine.get("start_date"))
            if problems:
                return False, " ".join(problems)
        routine_id = f"routine-{uuid.uuid4().hex}"
        preferred = ", ".join(routine.get("preferred_days", []) or [])
        freq = str(routine.get("frequency") or "Daily")
        start_date = _date_to_text(routine.get("start_date")) or date.today().isoformat()
        records["routines"].append({"routine_id": routine_id, "area_id": area_id, "area_name": area_name, "title": str(routine.get("title", "")).strip(), "description": str(routine.get("purpose", "")).strip(), "frequency": "Daily" if freq == "Daily" else "Weekly", "preferred_days": preferred or ("Every day" if freq == "Daily" else ""), "duration_minutes": "", "status": "Active", "purpose": str(routine.get("purpose", "")).strip(), "next_due": start_date, "checklist": "", "notes": "Created from the Pathmark creation wizard."})
        activity_days = preferred or ("Every day" if freq == "Daily" else "")
        for activity in activities:
            action_id = f"action-{uuid.uuid4().hex}"
            end_date = _date_to_text(activity.get("calendar_end_date")) or start_date
            minutes = str(_calendar_minutes(start_date, activity.get("calendar_start_time"), end_date, activity.get("calendar_end_time")))
            helper_titles = [str(t.get("title", "")).strip() for t in activity.get("helper_tasks", []) if str(t.get("title", "")).strip()]
            notes = "Created from the Pathmark creation wizard."
            if end_date and end_date != start_date:
                notes += f" Ends on {end_date}."
            if helper_titles:
                notes += "\nHelper checklist items:\n- " + "\n- ".join(helper_titles)
            title = str(activity.get("title", "")).strip()
            records["task_prompts"].append({"prompt_id": f"prompt-{uuid.uuid4().hex}", "area_name": area_name, "title": title, "prompt_text": title, "due_date": start_date, "task_kind": "activity", "linked_record_id": action_id, "linked_record_type": "routine_activity", "linked_parent_id": routine_id, "linked_parent_type": "routine", "task_list": "Pathmark", "notes": f"Automatic checklist item for routine activity: {title}", "status": "Staged", "created_at": now, "updated_at": now, "source": "pathmark_creation_wizard"})
            records["actions"].append({"action_id": action_id, "goal_id": "", "routine_id": routine_id, "area_id": area_id, "area_name": area_name, "title": title, "description": title, "status": "Included", "priority": "Medium", "specific_area": "", "due_date": start_date, "scheduled_date": "", "activity_days": activity_days, "estimated_minutes": minutes, "calendar_block": "1", "reminder": "1", "include_tasklist": "1", "first_step": title, "task_reminder_time": "", "calendar_start_time": _time_to_text(activity.get("calendar_start_time")), "calendar_end_time": _time_to_text(activity.get("calendar_end_time")), "calendar_end_date": end_date, "calendar_location": str(activity.get("location", "")).strip(), "notes": notes})
            for task in activity.get("helper_tasks", []) or []:
                if str(task.get("title", "")).strip():
                    records["task_prompts"].append({"prompt_id": f"prompt-{uuid.uuid4().hex}", "area_name": area_name, "title": str(task.get("title", "")).strip(), "prompt_text": str(task.get("title", "")).strip(), "due_date": _date_to_text(task.get("due")) or start_date, "task_kind": "helper", "linked_record_id": action_id, "linked_record_type": "routine_activity", "linked_parent_id": routine_id, "linked_parent_type": "routine", "task_list": "Pathmark", "notes": f"Helper checklist item for routine activity: {title}", "status": "Staged", "created_at": now, "updated_at": now, "source": "pathmark_creation_wizard"})
    ok, msg = append_many_online_records(sheet_id, records)
    if ok:
        draft["status"] = "saved"
        draft["saved_at"] = utc_now_text()
        _save_wizard_draft(sheet_id, draft)
        clear_online_cache(sheet_id)
        return True, "Saved from the Pathmark creation wizard."
    return ok, msg



def _open_pathmark_wizard_view(draft: dict[str, Any] | None = None) -> None:
    """Switch Pathmark Online into its dedicated wizard workspace."""
    if draft is not None:
        _set_wizard_state(draft)
    elif not _wizard_state():
        _set_wizard_state(_new_wizard_draft())
    st.session_state["pathmark_online_view"] = "wizard"


def _return_to_pathmark_dashboard() -> None:
    """Return Pathmark Online to the normal workspace dashboard."""
    st.session_state["pathmark_online_view"] = "dashboard"


def _wizard_enable_next_when_text_nonempty() -> None:
    """Deprecated compatibility hook.

    Earlier releases used browser-side JavaScript to enable disabled Next
    buttons while a required text box was being typed into. That made the UI
    feel responsive, but it also risked interfering with Streamlit/React button
    state. Required wizard text questions now use form submission instead: the
    user types the answer and presses Next, and that click both commits the
    text and advances the wizard after server-side validation.
    """
    return None


def render_pathmark_creation_wizard_entry(sheet_id: str) -> bool:
    """Render the dashboard entry point for the dedicated wizard workspace."""
    latest = _latest_wizard_draft(sheet_id)
    st.markdown("""
    <div class="wizard-entry-card">
      <div class="kicker">Create</div>
      <h3>Pathmark creation wizard</h3>
      <p>Start a project or routine in an immersive wizard workspace. Pathmark will make time in your calendar, keep each step available for your weekly tasklist, and add each step or activity to Google Tasks as a checklist item.</p>
    </div>
    """, unsafe_allow_html=True)
    if latest:
        label = latest.get("project", {}).get("title") if latest.get("wizard_type") == "project" else latest.get("routine", {}).get("title")
        label = label or ("Project draft" if latest.get("wizard_type") == "project" else "Routine draft")
        st.info(f"You have an unfinished Pathmark creation draft: {label}.")
        c1, c2, c3 = st.columns(3)
        if c1.button("Restore draft in wizard", use_container_width=True):
            _open_pathmark_wizard_view(latest)
            st.rerun()
        if c2.button("Discard draft", use_container_width=True):
            latest["status"] = "discarded"
            _save_wizard_draft(sheet_id, latest)
            _clear_wizard_state()
            st.rerun()
        if c3.button("Start new wizard", use_container_width=True):
            _open_pathmark_wizard_view(_new_wizard_draft())
            st.rerun()
    else:
        if st.button("Start Pathmark creation wizard", use_container_width=True):
            _open_pathmark_wizard_view(_new_wizard_draft())
            st.rerun()
    return False

def _wizard_info_button(label: str, text: str) -> None:
    """Small inline information control for wizard guidance.

    This avoids large dropdown-style guidance boxes in the main wizard flow.
    """
    try:
        with st.popover(f"ⓘ {label}"):
            st.write(text)
    except Exception:
        st.caption(f"ⓘ {label}: {text}")


def _render_wizard_nav(sheet_id: str, draft: dict[str, Any], can_next: bool, next_step: str | None = None, next_answer: Any = None) -> tuple[bool, bool]:
    back_disabled = not bool(st.session_state.get(_wizard_back_stack_key(str(draft.get('draft_id',''))), []))
    back_col, note_col, next_col = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
    with back_col:
        go_back = st.button("‹ Back", key=f"wiz_back_{draft.get('current_step_key')}", use_container_width=True, disabled=back_disabled, help="Back", type="primary")
    with note_col:
        if can_next:
            st.markdown("<div class='wizard-nav-note'>Ready to continue.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='wizard-nav-note'>Complete the required question to continue.</div>", unsafe_allow_html=True)
    with next_col:
        go_next = st.button("Next ›", key=f"wiz_next_{draft.get('current_step_key')}", use_container_width=True, disabled=not can_next, help="Next", type="primary")
    if go_back:
        _wizard_back(sheet_id, draft)
    if go_next:
        if next_step is None:
            next_step = _wizard_next_step(draft, draft.get("current_step_key", "choose_type"), next_answer)
        _wizard_go(sheet_id, draft, next_step, push_current=True)
    return go_back, go_next


def _wizard_required_text_form(
    *,
    draft: dict[str, Any],
    step_key: str,
    label: str,
    value: str = "",
    placeholder: str = "",
    multiline: bool = False,
    note: str = "Required before continuing.",
    helper_text: str = "",
) -> tuple[str, bool, bool]:
    """Render a required text question where Next also commits the typed text."""
    back_disabled = not bool(st.session_state.get(_wizard_back_stack_key(str(draft.get('draft_id',''))), []))
    with st.form(key=f"wiz_text_{step_key}_{draft.get('draft_id','')}"):
        if multiline:
            text = st.text_area(label, value=value, placeholder=placeholder)
        else:
            text = st.text_input(label, value=value, placeholder=placeholder)
        if helper_text:
            st.markdown(f"<div class='pathmark-hint'>{html.escape(helper_text)}</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
        with c1:
            go_back = st.form_submit_button("‹ Back", use_container_width=True, disabled=back_disabled, type="primary")
        with c2:
            st.markdown(f"<div class='wizard-nav-note'>{html.escape(note)}</div>", unsafe_allow_html=True)
        with c3:
            go_next = st.form_submit_button("Next ›", use_container_width=True, type="primary")
    return str(text or ""), bool(go_back), bool(go_next)


def _wizard_progress_context(draft: dict[str, Any], step: str) -> tuple[list[str], str, str]:
    wt = draft.get("wizard_type", "project")
    stages = ["Choose type", "Area", "Details", "Steps/activities", "Review"]
    if step == "choose_type":
        return stages, "Choose type", "Step 1"
    if step in {"choose_area", "area_name", "area_colour", "area_review"}:
        return stages, "Area", "Area setup"
    if step in {"project_title", "project_reason", "project_done", "project_target", "project_planning_mode", "routine_title", "routine_purpose", "routine_frequency", "routine_days", "routine_start_date"}:
        return stages, "Details", "Project details" if wt == "project" else "Routine details"
    if step in {"project_review", "routine_review"}:
        return stages, "Review", "Review and save"
    if wt == "routine":
        idx = 1
        current_id = draft.get("current_activity_id")
        for i, item in enumerate(draft.get("routine_activities", []) or [], start=1):
            if item.get("activity_id") == current_id:
                idx = i
                break
        return stages, "Steps/activities", f"Routine activity {idx}"
    idx = 1
    current_id = draft.get("current_step_id")
    for i, item in enumerate(draft.get("project_steps", []) or [], start=1):
        if item.get("step_id") == current_id:
            idx = i
            break
    return stages, "Steps/activities", f"Project step {idx}"


def _render_wizard_progress(draft: dict[str, Any], step: str) -> None:
    stages, current, label = _wizard_progress_context(draft, step)
    try:
        index = stages.index(current)
    except ValueError:
        index = 0
    percent = int(((index + 1) / max(len(stages), 1)) * 100)
    stage_text = " → ".join(stages)
    st.markdown(
        f"<div class='wizard-progress'>"
        f"<div class='wizard-progress-text'>{html.escape(label)} · {html.escape(current)} · {html.escape(stage_text)}</div>"
        f"<div class='wizard-progress-track'><div class='wizard-progress-fill' style='width:{percent}%;'></div></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_wizard_header(draft: dict[str, Any], step: str) -> None:
    st.markdown("""
    <div class='wizard-hero'>
      <div class='kicker'>Creation wizard</div>
      <h2>Pathmark creation wizard</h2>
      <p><strong>Projects have a definition of done. Routines repeat.</strong> Pathmark helps you decide what matters, then make time for it.</p>
    </div>
    """, unsafe_allow_html=True)
    _render_wizard_progress(draft, step)


def render_pathmark_creation_wizard(sheet_id: str) -> None:
    draft = _wizard_state() or _new_wizard_draft()
    step = draft.get("current_step_key", "choose_type")
    _render_wizard_header(draft, step)

    if step == "choose_type":
        st.subheader("What are you creating?")
        _wizard_info_button("Which should I choose?", "Project: something you want to complete, finish, build, resolve, or move forward. Routine: something repeating that protects your wellbeing, energy, home, learning, work, or creative life. In both cases, the project or routine is the container; the steps, focus blocks, supporting time blocks, or routine activities are what become calendar/task items.")
        st.markdown("<div class='pathmark-hint'><strong>Container first, activities next.</strong><br>The name you choose here gives the work a home. Calendar blocks and reminders are created from the steps, focus blocks, supporting time blocks, or routine activities you add underneath it.</div>", unsafe_allow_html=True)
        choice = st.radio("Choose one", ["Project", "Routine"], horizontal=True, index=0 if draft.get("wizard_type") != "routine" else 1)
        draft["wizard_type"] = "project" if choice == "Project" else "routine"
        _set_wizard_state(draft)
        _render_wizard_nav(sheet_id, draft, bool(choice))

    elif step == "choose_area":
        st.subheader("Which area of your life does this belong to?")
        _wizard_info_button("What is an Area?", "Areas help Pathmark keep similar projects and routines together. This area can also become the Google Calendar grouping or subcalendar where you place related time in your calendar.")
        options = _area_options(sheet_id)
        names = [o["area_name"] for o in options]
        choices = names + ["+ Add a new area"]
        existing = draft.get("area", {}).get("area_name", "")
        idx = choices.index(existing) if existing in choices else (len(choices)-1 if not names else 0)
        selected = st.selectbox("Area", choices, index=idx)
        if selected == "+ Add a new area":
            draft["area"].update({"mode": "new", "area_id": "", "area_name": ""})
        else:
            match = next((o for o in options if o["area_name"] == selected), {})
            colour = normalise_google_colour_label(match.get("colour", "Sage")) if 'normalise_google_colour_label' in globals() else (match.get("colour") or "Sage")
            draft["area"].update({"mode": "existing", "area_id": match.get("area_id", ""), "area_name": selected, "calendar_colour_name": colour})
        _set_wizard_state(draft)
        _render_wizard_nav(sheet_id, draft, bool(selected))

    elif step in {"area_name", "area_colour", "area_review"}:
        area = draft.setdefault("area", {"mode": "new"})
        if step == "area_name":
            st.subheader("What should this area be called?")
            _wizard_info_button("Naming an Area", "Use a broad name that could hold several related projects or routines. This may become the calendar grouping or subcalendar for similar types of time.")
            text, go_back, go_next = _wizard_required_text_form(
                draft=draft,
                step_key="area_name",
                label="Area name",
                value=str(area.get("area_name", "")),
                placeholder="Body And Stability",
            )
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                area["area_name"] = text.strip()
                _set_wizard_state(draft)
                if area["area_name"]:
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
                else:
                    st.warning("Add an area name before continuing.")
        elif step == "area_colour":
            st.subheader("What calendar colour should this area use?")
            current = str(area.get("calendar_colour_name", "Sage") or "Sage")
            idx = GOOGLE_COLOUR_LABELS.index(current) if current in GOOGLE_COLOUR_LABELS else 1
            colour = st.selectbox("Calendar colour", GOOGLE_COLOUR_LABELS, index=idx)
            area["calendar_colour_name"] = colour
            area["calendar_colour_id"] = GOOGLE_COLOUR_BY_LABEL.get(colour, {}).get("code", "2")
            hx = GOOGLE_COLOUR_BY_LABEL.get(colour, {}).get("hex", "#33B679")
            st.markdown(f"<div style='border-left: 12px solid {hx}; padding: 0.6rem 0.8rem; border-radius: 0.6rem; background: var(--secondary-background-color);'>Selected colour: <strong>{html.escape(colour)}</strong></div>", unsafe_allow_html=True)
            _set_wizard_state(draft)
            _render_wizard_nav(sheet_id, draft, True)
        else:
            st.subheader("Review this area")
            st.write(f"Area: **{area.get('area_name','')}**")
            st.write(f"Calendar colour: **{area.get('calendar_colour_name','Sage')}**")
            _render_wizard_nav(sheet_id, draft, True)

    elif step.startswith("project_"):
        render_project_wizard_step(sheet_id, draft, step)
    elif step.startswith("routine_"):
        render_routine_wizard_step(sheet_id, draft, step)
    if step != "choose_type":
        st.markdown("<div class='wizard-exit-note'>You can leave the wizard without saving final Pathmark records.</div>", unsafe_allow_html=True)
        exit_col, _ = st.columns([0.24, 0.76])
        with exit_col:
            if st.button("Exit wizard", use_container_width=True):
                st.session_state["wizard_cancel_confirm"] = True
    if step != "choose_type" and st.session_state.get("wizard_cancel_confirm"):
        st.warning("Do you want to keep this draft for later?")
        c1, c2, c3 = st.columns(3)
        if c1.button("Keep draft", use_container_width=True):
            draft["status"] = "in_progress"
            _save_wizard_draft(sheet_id, draft)
            _clear_wizard_state()
            _return_to_pathmark_dashboard()
            st.session_state.pop("wizard_cancel_confirm", None)
            st.rerun()
        if c2.button("Discard draft", use_container_width=True):
            draft["status"] = "discarded"
            _save_wizard_draft(sheet_id, draft)
            _clear_wizard_state()
            _return_to_pathmark_dashboard()
            st.session_state.pop("wizard_cancel_confirm", None)
            st.rerun()
        if c3.button("Continue editing", use_container_width=True):
            st.session_state.pop("wizard_cancel_confirm", None)
            st.rerun()


def render_project_wizard_step(sheet_id: str, draft: dict[str, Any], step: str) -> None:
    project = draft.setdefault("project", {})
    if step == "project_title":
        st.subheader("What project do you want to move forward?")
        text, go_back, go_next = _wizard_required_text_form(
            draft=draft,
            step_key="project_title",
            label="Project",
            value=str(project.get("title", "")),
            placeholder="Complete a beginner sketching course",
            helper_text="This is the project container. It gives the work a home, but it does not become a calendar block or reminder. The project steps, focus blocks, and supporting time blocks you add next are what appear on your calendar and task list.",
        )
        if go_back:
            _wizard_back(sheet_id, draft)
        if go_next:
            project["title"] = text.strip()
            _set_wizard_state(draft)
            if project["title"]:
                _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
            else:
                st.warning("Add a project title before continuing.")
    elif step == "project_reason":
        st.subheader("Why does this project matter?")
        project["reason"] = st.text_area("Why it matters", value=str(project.get("reason", "")), placeholder="I want to sketch stronger pottery forms before decorating them.")
        _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
    elif step == "project_done":
        st.subheader("What would “done” look like?")
        text, go_back, go_next = _wizard_required_text_form(
            draft=draft,
            step_key="project_done",
            label="Definition of done",
            value=str(project.get("definition_of_done", "")),
            placeholder="I have completed 10 exercises and saved the sketches in my design folder.",
            multiline=True,
        )
        if go_back:
            _wizard_back(sheet_id, draft)
        if go_next:
            project["definition_of_done"] = text.strip()
            _set_wizard_state(draft)
            if project["definition_of_done"]:
                _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
            else:
                st.warning("Describe what done looks like before continuing.")
    elif step == "project_target":
        st.subheader("When would you like this project to be done?")
        st.caption("This is optional, but Pathmark now uses a date field by default. Dates are shown in New Zealand day/month/year format.")
        project["target_date"] = date_input_nz("Target date", value=_text_to_date(project.get("target_date"))).isoformat()
        project["target_label"] = ""
        _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
    elif step == "project_planning_mode":
        st.subheader("How would you like to plan this project?")
        _wizard_info_button("What counts toward progress?", "Task-based projects count each discrete project step. Focus-based projects count larger milestones or weekly focuses; supporting time blocks can be added later and do not change completion percentage.")
        options = ["Task-based", "Focus-based"]
        current = str(project.get("planning_mode", "Task-based") or "Task-based")
        if current not in options:
            current = "Task-based"
        choice = st.radio(
            "Planning style",
            options,
            index=options.index(current),
            captions=[
                "Create discrete steps. Each step has calendar time and counts toward completion.",
                "Create focus blocks that span one or more days, then schedule supporting work sessions underneath them.",
            ],
        )
        project["planning_mode"] = choice
        if choice == "Task-based":
            st.markdown("<div class='pathmark-note'>Use this when the project is best tracked by ticking off concrete actions. Each project step counts toward progress automatically.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='pathmark-note'>Use this when progress is measured by completing larger focus outcomes. Focus blocks count toward progress; supporting time blocks help you work on them but do not count toward completion.</div>", unsafe_allow_html=True)
        _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
    elif step in {"project_step_title", "project_calendar_date", "project_calendar_start_time", "project_calendar_end_time", "project_helper_task_choice", "project_helper_task_item", "project_helper_task_due", "project_add_helper_task_item", "project_add_step"}:
        if not draft.get("current_step_id") or _find_step_by_id(draft.get("project_steps", []), "step_id", draft.get("current_step_id")) is None:
            _append_project_step(draft)
        current = _find_step_by_id(draft.get("project_steps", []), "step_id", draft.get("current_step_id")) or draft["project_steps"][-1]
        if step == "project_step_title":
            planning_mode = str(project.get("planning_mode", "Task-based") or "Task-based")
            if planning_mode == "Focus-based":
                current["item_type"] = "project_focus"
                current["contributes_to_progress"] = "1"
                st.subheader("What is the first or next focus block?")
                st.caption("This focus block is a scheduled project item. It can span several days as an all-day calendar block and counts toward project completion. Supporting time blocks can be added from the Projects tab after saving.")
                step_label = "Focus block"
                placeholder = "Learn Tune 1"
            else:
                st.subheader("What is the first or next step in your project?")
                current["item_type"] = "project_progress"
                current["contributes_to_progress"] = "1"
                st.caption("Project steps are the scheduled actions inside the project. Each step becomes calendar/task time and counts toward progress automatically.")
                step_label = "Project step"
                placeholder = "Choose a beginner sketching guide"
            text, go_back, go_next = _wizard_required_text_form(
                draft=draft,
                step_key=f"project_step_title_{current.get('step_id','')}",
                label=step_label,
                value=str(current.get("title", "")),
                placeholder=placeholder,
            )
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                current["title"] = text.strip()
                _set_wizard_state(draft)
                if current["title"]:
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
                else:
                    st.warning("Add a project step before continuing.")
        elif step == "project_calendar_date":
            planning_mode = str(project.get("planning_mode", "Task-based") or "Task-based")
            if planning_mode == "Focus-based":
                st.subheader("When does this focus block start?")
                st.caption("Focus blocks are all-day calendar items. Choose the first day this focus should be active.")
                current["item_type"] = "project_focus"
                current["contributes_to_progress"] = "1"
                current["calendar_date"] = date_input_nz("Start date", value=_text_to_date(current.get("calendar_date"))).isoformat()
                if not str(current.get("calendar_end_date", "") or "").strip():
                    current["calendar_end_date"] = current["calendar_date"]
            else:
                st.subheader("What day will you make time for this step?")
                current["calendar_date"] = date_input_nz("Date", value=_text_to_date(current.get("calendar_date"))).isoformat()
            _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
        elif step == "project_calendar_start_time":
            st.subheader("What time will you start?")
            st.caption("Enter the start time once, then continue. Use 24-hour time, for example 09:00.")
            back_disabled = not bool(st.session_state.get(_wizard_back_stack_key(str(draft.get('draft_id',''))), []))
            with st.form(key=f"wiz_form_project_start_{current.get('step_id','')}"):
                start_text = st.text_input("Start time", value=str(current.get("calendar_start_time", "") or ""), placeholder="09:00", key=f"project_start_text_{current.get('step_id','')}")
                c1, c2, c3 = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
                with c1:
                    go_back = st.form_submit_button("‹ Back", use_container_width=True, disabled=back_disabled, type="primary")
                with c2:
                    st.markdown("<div class='wizard-nav-note'>Required because this step will become calendar time.</div>", unsafe_allow_html=True)
                with c3:
                    go_next = st.form_submit_button("Next ›", use_container_width=True, type="primary")
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                current["calendar_start_time"] = _time_to_text(start_text) if _is_valid_time_text(start_text) else str(start_text or "").strip()
                _set_wizard_state(draft)
                if _is_valid_time_text(current.get("calendar_start_time")):
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
                else:
                    st.warning("Enter a valid start time, such as 09:00.")
        elif step == "project_calendar_end_time":
            planning_mode = str(project.get("planning_mode", "Task-based") or "Task-based")
            start_date = _text_to_date(current.get("calendar_date"))
            back_disabled = not bool(st.session_state.get(_wizard_back_stack_key(str(draft.get('draft_id',''))), []))
            if planning_mode == "Focus-based":
                st.subheader("When does this focus block finish?")
                st.caption("The focus block will appear in Google Calendar as an all-day event across these dates.")
                with st.form(key=f"wiz_form_project_focus_finish_{current.get('step_id','')}"):
                    end_date_value = date_input_nz("Finish date", value=_calendar_end_date_default(current, start_date), key=f"project_focus_end_date_{current.get('step_id','')}")
                    c1, c2, c3 = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
                    with c1:
                        go_back = st.form_submit_button("‹ Back", use_container_width=True, disabled=back_disabled, type="primary")
                    with c2:
                        st.markdown("<div class='wizard-nav-note'>Focus blocks are all-day calendar events.</div>", unsafe_allow_html=True)
                    with c3:
                        go_next = st.form_submit_button("Next ›", use_container_width=True, type="primary")
                if go_back:
                    _wizard_back(sheet_id, draft)
                if go_next:
                    current["calendar_end_date"] = end_date_value.isoformat()
                    current["calendar_start_time"] = ""
                    current["calendar_end_time"] = ""
                    current["item_type"] = "project_focus"
                    current["contributes_to_progress"] = "1"
                    problems = _validate_project_step(current)
                    _set_wizard_state(draft)
                    if problems:
                        for p in problems:
                            st.warning(p)
                    else:
                        _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
            else:
                st.subheader("When will you finish?")
                st.caption("Set the finish date and time. Dates are shown in New Zealand day/month/year format.")
                with st.form(key=f"wiz_form_project_finish_{current.get('step_id','')}"):
                    end_date_value = date_input_nz("Finish date", value=_calendar_end_date_default(current, start_date), key=f"project_end_date_{current.get('step_id','')}")
                    end_text = st.text_input("Finish time", value=str(current.get("calendar_end_time", "") or ""), placeholder="10:00", key=f"project_finish_text_{current.get('step_id','')}")
                    c1, c2, c3 = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
                    with c1:
                        go_back = st.form_submit_button("‹ Back", use_container_width=True, disabled=back_disabled, type="primary")
                    with c2:
                        st.markdown("<div class='wizard-nav-note'>Required because this step will become calendar time.</div>", unsafe_allow_html=True)
                    with c3:
                        go_next = st.form_submit_button("Next ›", use_container_width=True, type="primary")
                if go_back:
                    _wizard_back(sheet_id, draft)
                if go_next:
                    current["calendar_end_date"] = end_date_value.isoformat()
                    current["calendar_end_time"] = _time_to_text(end_text) if _is_valid_time_text(end_text) else str(end_text or "").strip()
                    current["ends_next_day"] = _date_to_text(current.get("calendar_end_date")) > _date_to_text(current.get("calendar_date"))
                    problems = _validate_project_step(current)
                    _set_wizard_state(draft)
                    if problems:
                        for p in problems:
                            st.warning(p)
                    else:
                        _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
        elif step == "project_helper_task_choice":
            st.subheader("Would any extra Google Tasks checklist items help you begin or prepare?")
            _wizard_info_button("What is a helper checklist item?", "Pathmark will already add the project step itself to Google Tasks as a checklist item. Helper checklist items are extra small actions, such as ‘put sketchbook on desk’ or ‘open the course page’.")
            choice = st.radio("Add helper checklist items?", ["No", "Yes"], horizontal=True, index=1 if current.get("has_helper_tasks") else 0)
            current["has_helper_tasks"] = choice == "Yes"
            _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True, next_step=("project_helper_task_item" if current["has_helper_tasks"] else "project_add_step"))
        elif step == "project_helper_task_item":
            if not current.get("helper_tasks") or not draft.get("current_task_id"):
                task = _append_helper_task(current); draft["current_task_id"] = task["task_id"]
            task = _find_step_by_id(current.get("helper_tasks", []), "task_id", draft.get("current_task_id")) or current["helper_tasks"][-1]
            st.subheader("What extra checklist item would help you begin or prepare?")
            text, go_back, go_next = _wizard_required_text_form(
                draft=draft,
                step_key=f"project_helper_{task.get('task_id','')}",
                label="Helper checklist item",
                value=str(task.get("title", "")),
                placeholder="Put sketchbook on the desk",
            )
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                task["title"] = text.strip()
                _set_wizard_state(draft)
                if task["title"]:
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
                else:
                    st.warning("Add a helper checklist item before continuing.")
        elif step == "project_helper_task_due":
            task = _find_step_by_id(current.get("helper_tasks", []), "task_id", draft.get("current_task_id")) or current.get("helper_tasks", [{}])[-1]
            st.subheader("What date should this checklist item appear?")
            _wizard_info_button("Why only a date?", "Google Tasks items are date-based in Pathmark. If something needs a specific time, it belongs in your calendar.")
            task["due"] = date_input_nz("Date", value=_text_to_date(task.get("due"), _text_to_date(current.get("calendar_date")))).isoformat()
            _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
        elif step == "project_add_helper_task_item":
            st.subheader("Would you like to add another helper checklist item for this step?")
            choice = st.radio("Add another helper item?", ["No", "Yes"], horizontal=True)
            if choice == "Yes" and st.button("Add another helper item", use_container_width=True):
                task = _append_helper_task(current); draft["current_task_id"] = task["task_id"]
                _wizard_go(sheet_id, draft, "project_helper_task_item")
            elif choice == "No":
                _render_wizard_nav(sheet_id, draft, True, next_step="project_add_step", next_answer=False)
        elif step == "project_add_step":
            planning_mode = str(project.get("planning_mode", "Task-based") or "Task-based")
            label = "focus block" if planning_mode == "Focus-based" else "project step"
            st.subheader(f"Would you like to add another {label}?")
            choice = st.radio(f"Add another {label}?", ["No", "Yes"], horizontal=True)
            if choice == "Yes" and st.button(f"Add another {label}", use_container_width=True):
                _append_project_step(draft); _wizard_go(sheet_id, draft, "project_step_title")
            elif choice == "No":
                _render_wizard_nav(sheet_id, draft, True, next_step="project_review", next_answer=False)
    elif step == "project_review":
        render_wizard_review(sheet_id, draft)


def render_routine_wizard_step(sheet_id: str, draft: dict[str, Any], step: str) -> None:
    routine = draft.setdefault("routine", {})
    if step == "routine_title":
        st.subheader("What routine do you want to protect?")
        text, go_back, go_next = _wizard_required_text_form(
            draft=draft,
            step_key="routine_title",
            label="Routine",
            value=str(routine.get("title", "")),
            placeholder="Sleep 8 hours a night",
            helper_text="This is the routine container. It sets the repeating pattern, but it does not become the calendar block or reminder. The activities inside the routine are what appear on your calendar and task list.",
        )
        if go_back:
            _wizard_back(sheet_id, draft)
        if go_next:
            routine["title"] = text.strip()
            _set_wizard_state(draft)
            if routine["title"]:
                _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
            else:
                st.warning("Add a routine title before continuing.")
    elif step == "routine_purpose":
        st.subheader("What is this routine meant to support?")
        routine["purpose"] = st.text_area("Purpose", value=str(routine.get("purpose", "")), placeholder="Better energy, mood and concentration.")
        _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
    elif step == "routine_frequency":
        st.subheader("How often should this routine repeat?")
        current = str(routine.get("frequency", "Daily") or "Daily")
        idx = WIZARD_FREQ_OPTIONS.index(current) if current in WIZARD_FREQ_OPTIONS else 0
        routine["frequency"] = st.selectbox("Repeat", WIZARD_FREQ_OPTIONS, index=idx)
        _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
    elif step == "routine_days":
        st.subheader("Which days should it repeat?")
        st.caption("Choose all relevant days, then continue. The page will save them together rather than refreshing after each selection.")
        back_disabled = not bool(st.session_state.get(_wizard_back_stack_key(str(draft.get('draft_id',''))), []))
        with st.form(key=f"wiz_form_routine_days_{draft.get('draft_id','')}"):
            selected_days = st.multiselect("Days", VALID_DAYS, default=[d for d in routine.get("preferred_days", []) if d in VALID_DAYS])
            c1, c2, c3 = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
            with c1:
                go_back = st.form_submit_button("‹ Back", use_container_width=True, disabled=back_disabled, type="primary")
            with c2:
                st.markdown("<div class='wizard-nav-note'>Required for selected-day routines.</div>", unsafe_allow_html=True)
            with c3:
                go_next = st.form_submit_button("Next ›", use_container_width=True, type="primary")
        if go_back:
            _wizard_back(sheet_id, draft)
        if go_next:
            routine["preferred_days"] = selected_days
            _set_wizard_state(draft)
            if selected_days:
                _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
            else:
                st.warning("Choose at least one day before continuing.")
    elif step == "routine_start_date":
        st.subheader("When should this routine start?")
        routine["start_date"] = date_input_nz("Start date", value=_text_to_date(routine.get("start_date"))).isoformat()
        _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
    elif step in {"routine_activity_title", "routine_calendar_start_time", "routine_calendar_end_time", "routine_calendar_location", "routine_helper_task_choice", "routine_helper_task_item", "routine_helper_task_due", "routine_add_helper_task_item", "routine_add_activity"}:
        if not draft.get("current_activity_id") or _find_step_by_id(draft.get("routine_activities", []), "activity_id", draft.get("current_activity_id")) is None:
            _append_routine_activity(draft)
        current = _find_step_by_id(draft.get("routine_activities", []), "activity_id", draft.get("current_activity_id")) or draft["routine_activities"][-1]
        if step == "routine_activity_title":
            st.subheader("What activity belongs inside this routine?")
            st.caption("Routine activities are the scheduled blocks inside the routine. These are what become calendar/task items; the routine name itself stays as the parent container.")
            text, go_back, go_next = _wizard_required_text_form(
                draft=draft,
                step_key=f"routine_activity_title_{current.get('activity_id','')}",
                label="Routine activity",
                value=str(current.get("title", "")),
                placeholder="Sleep",
            )
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                current["title"] = text.strip()
                _set_wizard_state(draft)
                if current["title"]:
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
                else:
                    st.warning("Add a routine activity before continuing.")
        elif step == "routine_calendar_start_time":
            st.subheader("What time will this activity start?")
            st.caption("Enter the start time once, then continue. Use 24-hour time, for example 22:30.")
            back_disabled = not bool(st.session_state.get(_wizard_back_stack_key(str(draft.get('draft_id',''))), []))
            with st.form(key=f"wiz_form_routine_start_{current.get('activity_id','')}"):
                start_text = st.text_input("Start time", value=str(current.get("calendar_start_time", "") or ""), placeholder="22:30", key=f"routine_start_text_{current.get('activity_id','')}")
                c1, c2, c3 = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
                with c1:
                    go_back = st.form_submit_button("‹ Back", use_container_width=True, disabled=back_disabled, type="primary")
                with c2:
                    st.markdown("<div class='wizard-nav-note'>Required because this activity will become calendar time.</div>", unsafe_allow_html=True)
                with c3:
                    go_next = st.form_submit_button("Next ›", use_container_width=True, type="primary")
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                current["calendar_start_time"] = _time_to_text(start_text) if _is_valid_time_text(start_text) else str(start_text or "").strip()
                _set_wizard_state(draft)
                if _is_valid_time_text(current.get("calendar_start_time")):
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
                else:
                    st.warning("Enter a valid start time, such as 22:30.")
        elif step == "routine_calendar_end_time":
            st.subheader("When will this activity finish?")
            routine_start = _text_to_date(routine.get("start_date"))
            st.caption("Set the finish date and time for the first occurrence. Use the next day for overnight activities such as sleep.")
            back_disabled = not bool(st.session_state.get(_wizard_back_stack_key(str(draft.get('draft_id',''))), []))
            with st.form(key=f"wiz_form_routine_finish_{current.get('activity_id','')}"):
                end_date_value = date_input_nz("Finish date for the first occurrence", value=_calendar_end_date_default(current, routine_start))
                end_text = st.text_input("Finish time", value=str(current.get("calendar_end_time", "") or ""), placeholder="06:30", key=f"routine_finish_text_{current.get('activity_id','')}")
                c1, c2, c3 = st.columns([0.18, 0.64, 0.18], vertical_alignment="center")
                with c1:
                    go_back = st.form_submit_button("‹ Back", use_container_width=True, disabled=back_disabled, type="primary")
                with c2:
                    st.markdown("<div class='wizard-nav-note'>Required because this activity will become calendar time.</div>", unsafe_allow_html=True)
                with c3:
                    go_next = st.form_submit_button("Next ›", use_container_width=True, type="primary")
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                current["calendar_end_date"] = end_date_value.isoformat()
                current["calendar_end_time"] = _time_to_text(end_text) if _is_valid_time_text(end_text) else str(end_text or "").strip()
                current["ends_next_day"] = _date_to_text(current.get("calendar_end_date")) > _date_to_text(routine.get("start_date"))
                problems = _validate_routine_activity(current, routine.get("start_date"))
                _set_wizard_state(draft)
                if problems:
                    for p in problems:
                        st.warning(p)
                else:
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
        elif step == "routine_calendar_location":
            st.subheader("Where does this happen?")
            current["location"] = st.text_input("Location", value=str(current.get("location", "")), placeholder="Bedroom")
            _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
        elif step == "routine_helper_task_choice":
            st.subheader("Would any extra Google Tasks checklist items help you begin or prepare?")
            _wizard_info_button("What is a helper checklist item?", "Pathmark will already add the routine activity itself to Google Tasks as a checklist item. For sleep, a helper checklist item might be ‘no screen time three hours before bed’, ‘dim the lights’, or ‘put phone outside the bedroom’.")
            choice = st.radio("Add helper checklist items?", ["No", "Yes"], horizontal=True, index=1 if current.get("has_helper_tasks") else 0)
            current["has_helper_tasks"] = choice == "Yes"
            _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True, next_step=("routine_helper_task_item" if current["has_helper_tasks"] else "routine_add_activity"))
        elif step == "routine_helper_task_item":
            if not current.get("helper_tasks") or not draft.get("current_task_id"):
                task = _append_helper_task(current); draft["current_task_id"] = task["task_id"]
            task = _find_step_by_id(current.get("helper_tasks", []), "task_id", draft.get("current_task_id")) or current["helper_tasks"][-1]
            st.subheader("What extra checklist item would help you begin or prepare?")
            text, go_back, go_next = _wizard_required_text_form(
                draft=draft,
                step_key=f"routine_helper_{task.get('task_id','')}",
                label="Helper checklist item",
                value=str(task.get("title", "")),
                placeholder="No screen time three hours before bed",
            )
            if go_back:
                _wizard_back(sheet_id, draft)
            if go_next:
                task["title"] = text.strip()
                _set_wizard_state(draft)
                if task["title"]:
                    _wizard_go(sheet_id, draft, _wizard_next_step(draft, step), push_current=True)
                else:
                    st.warning("Add a helper checklist item before continuing.")
        elif step == "routine_helper_task_due":
            task = _find_step_by_id(current.get("helper_tasks", []), "task_id", draft.get("current_task_id")) or current.get("helper_tasks", [{}])[-1]
            st.subheader("When should this checklist item appear?")
            _wizard_info_button("Why only a date?", "Google Tasks items are date-based in Pathmark. If something needs a specific time, it belongs in your calendar.")
            task["due"] = date_input_nz("Date", value=_text_to_date(task.get("due"), _text_to_date(routine.get("start_date")))).isoformat()
            _set_wizard_state(draft); _render_wizard_nav(sheet_id, draft, True)
        elif step == "routine_add_helper_task_item":
            st.subheader("Would you like to add another helper checklist item for this activity?")
            choice = st.radio("Add another helper item?", ["No", "Yes"], horizontal=True)
            if choice == "Yes" and st.button("Add another helper item", use_container_width=True):
                task = _append_helper_task(current); draft["current_task_id"] = task["task_id"]
                _wizard_go(sheet_id, draft, "routine_helper_task_item")
            elif choice == "No":
                _render_wizard_nav(sheet_id, draft, True, next_step="routine_add_activity", next_answer=False)
        elif step == "routine_add_activity":
            st.subheader("Would you like to add another activity to this routine?")
            choice = st.radio("Add another routine activity?", ["No", "Yes"], horizontal=True)
            if choice == "Yes" and st.button("Add another routine activity", use_container_width=True):
                _append_routine_activity(draft); _wizard_go(sheet_id, draft, "routine_activity_title")
            elif choice == "No":
                _render_wizard_nav(sheet_id, draft, True, next_step="routine_review", next_answer=False)
    elif step == "routine_review":
        render_wizard_review(sheet_id, draft)


def render_wizard_review(sheet_id: str, draft: dict[str, Any]) -> None:
    wt = draft.get("wizard_type")
    st.subheader("Review before saving")
    area = draft.get("area", {})
    st.write(f"Area: **{area.get('area_name','')}**")
    if wt == "project":
        project = draft.get("project", {})
        st.markdown(f"### Project\n**{html.escape(str(project.get('title','')))}**")
        st.write(f"Definition of done: {project.get('definition_of_done','')}")
        st.markdown("#### Project steps")
        for i, step in enumerate(draft.get("project_steps", []), start=1):
            due = _date_to_text(step.get("calendar_date"))
            st.write(f"{i}. **{step.get('title','')}** — {display_date(due) if 'display_date' in globals() else due}, {_format_time_range_with_dates(step.get('calendar_date'), step.get('calendar_start_time'), step.get('calendar_end_date'), step.get('calendar_end_time'))}")
            st.caption("Google Tasks checklist item: " + str(step.get("title", "")))
            helpers = [t.get("title", "") for t in step.get("helper_tasks", []) if t.get("title")]
            if helpers:
                st.caption("Helper checklist items: " + "; ".join(helpers))
        if st.button("Save project", use_container_width=True):
            ok, msg = _final_save_wizard(sheet_id, draft)
            if ok:
                st.success(msg); _clear_wizard_state(); _return_to_pathmark_dashboard(); st.rerun()
            else:
                st.warning(safe_user_message(msg))
        _render_wizard_nav(sheet_id, draft, False)
    else:
        routine = draft.get("routine", {})
        st.markdown(f"### Routine\n**{html.escape(str(routine.get('title','')))}**")
        st.write(f"Repeats: {_routine_days_text(routine)}")
        st.markdown("#### Routine activities")
        for i, activity in enumerate(draft.get("routine_activities", []), start=1):
            st.write(f"{i}. **{activity.get('title','')}** — {_format_time_range_with_dates(routine.get('start_date'), activity.get('calendar_start_time'), activity.get('calendar_end_date'), activity.get('calendar_end_time'))}")
            st.caption("Google Tasks checklist item: " + str(activity.get("title", "")))
            helpers = [t.get("title", "") for t in activity.get("helper_tasks", []) if t.get("title")]
            if helpers:
                st.caption("Helper checklist items: " + "; ".join(helpers))
        if st.button("Save routine", use_container_width=True):
            ok, msg = _final_save_wizard(sheet_id, draft)
            if ok:
                st.success(msg); _clear_wizard_state(); _return_to_pathmark_dashboard(); st.rerun()
            else:
                st.warning(safe_user_message(msg))
        _render_wizard_nav(sheet_id, draft, False)


def render_online_overview(sheet_id: str) -> None:
    st.markdown("""
    <div class="dashboard-hero">
      <h2>Dashboard</h2>
      <p><strong>Protect your stability. Make progress. Direct your resources.</strong><br>
      Pathmark shows whether the life you are trying to build is supported this week.</p>
    </div>
    """, unsafe_allow_html=True)

    data = read_online_tables(sheet_id)
    areas = active_online_df(data.get("areas", pd.DataFrame()))
    goals = active_online_df(data.get("goals", pd.DataFrame()))
    routines = active_online_df(data.get("routines", pd.DataFrame()))
    actions = active_online_df(data.get("actions", pd.DataFrame()))

    calendar_rows = staged_calendar_blocks(sheet_id)
    task_rows = staged_tasklist(sheet_id)
    task_prompts = active_online_df(read_online_table(sheet_id, "task_prompts"))
    money = spending_summary(sheet_id)

    project_actions = pd.DataFrame()
    routine_actions = pd.DataFrame()
    if not actions.empty:
        if "goal_id" in actions.columns:
            project_actions = actions[actions["goal_id"].fillna("").astype(str).str.strip().ne("")].copy()
            if not project_actions.empty:
                project_actions = project_actions[project_actions.apply(project_action_counts_toward_progress, axis=1)].copy()
        if "routine_id" in actions.columns:
            routine_actions = actions[actions["routine_id"].fillna("").astype(str).str.strip().ne("")].copy()

    routine_count = len(routine_actions) if not routine_actions.empty else 0
    routine_done_week, routine_total_week, week_start_pref = routine_weekly_completion_summary(sheet_id)
    if routine_total_week:
        routine_progress_label = f"{routine_done_week} of {routine_total_week} routine activities complete this week"
    else:
        routine_progress_label = "No routine activities planned this week" if routine_count else "routine activities set up"
    project_action_count = len(project_actions) if not project_actions.empty else 0
    project_completed, project_count = project_overall_completion_summary(sheet_id)
    project_progress_label = f"{project_completed} of {project_count} project progress items complete" if project_count else "No project progress items linked to Google Tasks yet" if project_action_count else "project progress items set up"
    routine_progress_html = progress_bar_html(routine_done_week, routine_total_week, routine_progress_label, show_label=False) if routine_total_week else ""
    project_progress_html = progress_bar_html(project_completed, project_count, project_progress_label, show_label=False) if project_count else ""
    surplus = float(money.get("surplus_weekly", 0.0) or 0.0)
    money_overcommitted = surplus < -0.005
    money_balanced = abs(surplus) <= 0.005
    if money_overcommitted:
        money_flow_title = "Shortfall"
        money_flow_value = money_text(abs(surplus))
        money_flow_foot = "planned outflows exceed income"
        money_flow_body = "Planned outflows are higher than income. Treat safe-to-spend as $0.00 until adjusted."
    elif money_balanced:
        money_flow_title = "Money flow balanced"
        money_flow_value = money_text(0.0)
        money_flow_foot = "nothing left to allocate this week"
        money_flow_body = "Income is fully allocated across spending, bills, irregular costs, debt and savings."
    else:
        money_flow_title = "Money available to allocate"
        money_flow_value = money_text(surplus)
        money_flow_foot = "to emergency, savings, debt, or planned costs"
        money_flow_body = "Move unallocated money into emergency, savings, debt, or planned irregular costs."
    if not money_overcommitted and surplus > 0.005:
        try:
            proj = _projection_summary(sheet_id)
            if proj.get("debt_weeks") is not None and float(proj.get("debt_balance", 0.0) or 0.0) > 0.005 and float(proj.get("debt_weekly", 0.0) or 0.0) > 0.005:
                weeks = int(proj.get("debt_weeks") or 0)
                money_flow_title = "Debt pathway"
                money_flow_value = f"{weeks} week{'s' if weeks != 1 else ''}"
                money_flow_foot = f"projected payoff around {_payday_date_from_settings(sheet_id, weeks).strftime('%d/%m/%Y')}"
                money_flow_body = "Based on the debt balance and weekly allocation entered in Spending Plan projections."
            elif proj.get("emergency_weeks") is not None and float(proj.get("emergency_target", 0.0) or 0.0) > float(proj.get("emergency_current", 0.0) or 0.0) and float(proj.get("emergency_weekly", 0.0) or 0.0) > 0.005:
                weeks = int(proj.get("emergency_weeks") or 0)
                money_flow_title = "Emergency target"
                money_flow_value = f"{weeks} week{'s' if weeks != 1 else ''}"
                money_flow_foot = f"target date around {_payday_date_from_settings(sheet_id, weeks).strftime('%d/%m/%Y')}"
                money_flow_body = "Based on the emergency target and weekly allocation entered in Spending Plan projections."
            elif proj.get("savings_weeks") is not None and float(proj.get("savings_target", 0.0) or 0.0) > float(proj.get("savings_current", 0.0) or 0.0) and float(proj.get("savings_weekly", 0.0) or 0.0) > 0.005:
                weeks = int(proj.get("savings_weeks") or 0)
                money_flow_title = "Savings target"
                money_flow_value = f"{weeks} week{'s' if weeks != 1 else ''}"
                money_flow_foot = f"target date around {_payday_date_from_settings(sheet_id, weeks).strftime('%d/%m/%Y')}"
                money_flow_body = "Based on the savings target and weekly allocation entered in Spending Plan projections."
        except Exception:
            pass
    money_flow_class = "pillar-card warning" if money_overcommitted else "pillar-card"

    st.markdown(f"""
    <div class="pillar-grid">
      <div class="pillar-card">
        <div class="kicker">Stability</div>
        <h3>Wellbeing routines</h3>
        <p>Protect the repeating supports that keep you steady before life gets busy.</p>
        <div class="pillar-stat">{routine_done_week if routine_total_week else routine_count}</div>
        <div class="pillar-foot">{html.escape(routine_progress_label)}</div>
        {routine_progress_html}
      </div>
      <div class="pillar-card">
        <div class="kicker">Progress</div>
        <h3>Meaningful projects</h3>
        <p>Turn projects with a definition of done into scheduled project steps.</p>
        <div class="pillar-stat">{project_completed if project_count else project_action_count}</div>
        <div class="pillar-foot">{html.escape(project_progress_label)}</div>
        {project_progress_html}
      </div>
      <div class="{money_flow_class}">
        <div class="kicker">Resources</div>
        <h3>{html.escape(money_flow_title)}</h3>
        <p>{html.escape(money_flow_body)}</p>
        <div class="pillar-stat">{html.escape(money_flow_value)}</div>
        <div class="pillar-foot">{html.escape(money_flow_foot)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='dashboard-section'><h3>Your week at a glance</h3></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-tile"><div class="metric-label">Calendar time</div><div class="metric-value">{len(calendar_rows) if not calendar_rows.empty else 0}</div></div>
      <div class="metric-tile"><div class="metric-label">Google Tasks items</div><div class="metric-value">{len(task_prompts) if not task_prompts.empty else 0}</div></div>
      <div class="metric-tile"><div class="metric-label">Printable tasklist rows</div><div class="metric-value">{len(task_rows) if not task_rows.empty else 0}</div></div>
      <div class="metric-tile"><div class="metric-label">Unallocated / week</div><div class="metric-value">{html.escape(money_text(surplus))}</div></div>
    </div>
    """, unsafe_allow_html=True)

    attention_high: list[str] = []
    attention_medium: list[str] = []
    if money.get("income_weekly", 0.0) <= 0:
        attention_high.append("Spending Plan has no active income source yet.")
    if money.get("surplus_weekly", 0.0) < 0:
        attention_high.append(f"Spending Plan shows a weekly shortfall of {money_text(abs(money.get('surplus_weekly', 0.0)))}.")
    if areas.empty:
        attention_medium.append("Create at least one Area so routines, projects, calendar time and money decisions have a home.")
    if routines.empty:
        attention_medium.append("No wellbeing routines are active yet.")
    if goals.empty:
        attention_medium.append("No progress projects are active yet.")
    if not goals.empty:
        goal_ids_with_steps = set(project_actions.get("goal_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().tolist()) if not project_actions.empty else set()
        for _, row in goals.iterrows():
            gid = str(row.get("goal_id", "") or "").strip()
            title = str(row.get("title", "Project") or "Project").strip()
            if gid and gid not in goal_ids_with_steps:
                attention_medium.append(f"Project needs a next step: {title}.")
                break
    if not routines.empty:
        routine_ids_with_activities = set(routine_actions.get("routine_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip().tolist()) if not routine_actions.empty else set()
        for _, row in routines.iterrows():
            rid = str(row.get("routine_id", "") or "").strip()
            title = str(row.get("title", "Routine") or "Routine").strip()
            if rid and rid not in routine_ids_with_activities:
                attention_medium.append(f"Routine needs at least one protected activity: {title}.")
                break
    if calendar_rows.empty and (not goals.empty or not routines.empty):
        attention_medium.append("No active project steps or routine activities are currently staged as calendar time.")
    if money.get("income_weekly", 0.0) > 0 and money.get("sinking_weekly", 0.0) <= 0:
        attention_medium.append("Planned irregular costs have not been funded yet.")

    st.markdown("<div class='dashboard-section'><h3>Needs attention</h3></div>", unsafe_allow_html=True)
    if attention_high or attention_medium:
        for item in attention_high[:3]:
            st.markdown(f"<div class='attention-card high'><div class='attention-label'>High priority</div><div class='attention-text'>{html.escape(item)}</div></div>", unsafe_allow_html=True)
        remaining_slots = max(0, 5 - len(attention_high[:3]))
        for item in attention_medium[:remaining_slots]:
            st.markdown(f"<div class='attention-card medium'><div class='attention-label'>Medium priority</div><div class='attention-text'>{html.escape(item)}</div></div>", unsafe_allow_html=True)
    else:
        st.success("Nothing urgent needs attention. Your routines, projects and spending plan have no obvious setup gaps.")

    next_action = "Open the Creation Wizard to create a routine or project."
    if attention_high:
        next_action = "Open Spending Plan and resolve the high-priority money-flow issue first."
    elif attention_medium:
        first = attention_medium[0].lower()
        if "routine" in first:
            next_action = "Review Routines or use the Creation Wizard to protect a repeating wellbeing support."
        elif "project" in first:
            next_action = "Review Projects or use the Creation Wizard to add a scheduled next step."
        elif "area" in first:
            next_action = "Open Areas or the Creation Wizard and create your first life area."
        elif "calendar" in first:
            next_action = "Open Projects or Routines and add calendar time to the next step or activity."
        elif "irregular" in first:
            next_action = "Open Spending Plan and add planned irregular costs."
    elif not task_rows.empty:
        next_action = "Open Google Sync to send this week to Google Calendar and Google Tasks. Use Tasklist only if you want a printable paper copy."

    st.markdown(f"""
    <div class="next-action-card">
      <strong>Next useful action</strong><br>{html.escape(next_action)}
    </div>
    """, unsafe_allow_html=True)

    focus = online_setting(sheet_id, "weekly_focus", "")
    with st.expander("Weekly review focus", expanded=not bool(focus)):
        with st.form("weekly_focus_home_form"):
            new_focus = st.text_area("What should Pathmark protect, move forward, or check financially this week?", value=focus, placeholder="For example: protect sleep, schedule one pottery design step, and check planned irregular costs.", height=90)
            save_focus = st.form_submit_button("Save weekly focus", use_container_width=True)
        if save_focus:
            ok, message = save_online_setting(sheet_id, "weekly_focus", new_focus.strip())
            if ok:
                st.success("Weekly focus saved.")
            else:
                st.warning(safe_user_message(message))

    if areas.empty and goals.empty and routines.empty:
        st.info("Use the Creation Wizard tab to create your first Area, then build either a Project or a Routine from start to finish.")

def download_tab() -> None:
    version = load_version()
    windows_package = find_windows_package(version.get("windows_package", ""))
    # The large Pathmark wordmark now carries the Home page brand.
    # Keep the icon for browser/app identity rather than repeating it above the hero.
    render_seasonal_banner(compact=True, force=True, season=current_southern_hemisphere_season())
    st.markdown("""
    <div class="hero">
      <div class="eyebrow">Stability. Progress. Resources.</div>
      <h1>Pathmark</h1>
      <p class="lead">Protect your wellbeing, move meaningful projects forward, and keep money aligned with the life you are building.</p>
      <p class="sublead">Pathmark helps you decide what matters, then make time for it. Routines protect stability, projects create forward motion, and the Spending Plan directs income before it disappears.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="grid-3">
      <div class="card"><h3>Protect stability</h3><p>Routine activities become protected time, so wellbeing supports are not left until life is already overloaded.</p></div>
      <div class="card"><h3>Make progress</h3><p>Projects hold outcomes with a definition of done, then turn them into one-off steps with calendar time and checklist items.</p></div>
      <div class="card"><h3>Direct resources</h3><p>The Spending Plan helps you set up income, outflows, APs and safe-to-spend guidance so money supports the plan.</p></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="policy-link-row" aria-label="Pathmark public policy links">
      <a href="?page=privacy">Privacy Policy</a>
      <a href="?page=terms">Terms of Service</a>
      <a href="?page=oauth">Google access explanation</a>
    </div>
    """, unsafe_allow_html=True)
    st.header("Two ways to use Pathmark")
    st.markdown("""
    <div class="grid-2">
      <div class="card"><h3>Pathmark Planner</h3><p>Sign in to manage routines, projects, tasklists, calendar sync and task sync from a browser. Your planning records are saved in a Google Sheet that belongs to you.</p></div>
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
    st.caption("This release is Windows-only for desktop. Pathmark Online remains a browser app; phone-app/PWA shortcut support has been removed until it can be implemented cleanly.")
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
    notes_value = version.get("notes", version.get("release_notes", []))
    if isinstance(notes_value, str):
        note_lines = [line.strip(" -•") for line in notes_value.splitlines() if line.strip(" -•")]
        if not note_lines and notes_value.strip():
            note_lines = [notes_value.strip()]
    elif isinstance(notes_value, list):
        note_lines = [str(note).strip() for note in notes_value if str(note).strip()]
    else:
        note_lines = []
    if not note_lines and str(version.get("release_notes", "")).strip():
        note_lines = [str(version.get("release_notes", "")).strip()]
    for note in note_lines:
        st.markdown(f"- {html.escape(note)}")




def theme_tab() -> None:
    st.header("Theme")
    st.caption("Use Streamlit’s top-right menu for Light, Dark or System. Pathmark only changes the accent colour.")
    st.caption("Seasonal, Spring, Summer, Autumn and Winter can also show a soft New Zealand landscape banner. Non-seasonal accent themes keep the cleaner card-only treatment.")

    user = current_user()
    sheet_id = st.session_state.get("sync_sheet_id", "")
    if user.get("email"):
        current_theme = normalise_online_theme(st.session_state.get("hosted_theme_preference") or theme_for_user(user.get("email", "")))
    else:
        current_theme = normalise_online_theme(st.session_state.get("hosted_theme_preference") or "Seasonal")

    if sheet_id:
        st.session_state["hosted_custom_accent"] = online_setting(sheet_id, "custom_accent", st.session_state.get("hosted_custom_accent", "#334E9E"))
    custom_accent = str(st.session_state.get("hosted_custom_accent", "#334E9E") or "#334E9E")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", custom_accent):
        custom_accent = "#334E9E"

    c1, c2 = st.columns([1.1, .9])
    with c1:
        theme_name = st.selectbox("Accent theme", ONLINE_THEME_OPTIONS, index=ONLINE_THEME_OPTIONS.index(current_theme), key="top_level_seasonal_theme")
    with c2:
        picked_custom = st.color_picker("Custom accent", custom_accent, key="top_level_custom_accent")

    if theme_name == "Custom":
        st.session_state["hosted_custom_accent"] = picked_custom
    inject_theme_css(theme_name)

    preview_season = seasonal_banner_season(theme_name)
    render_seasonal_banner(
        title=f"{preview_season} banner preview",
        subtitle="Seasonal, or an explicit Spring / Summer / Autumn / Winter theme, now uses a soft AI-generated New Zealand landscape banner as a subtle backdrop.",
        season=preview_season,
        force=True,
        theme_name=theme_name,
        show_label=True,
    )

    current_display, _theme_tokens = resolved_accent_theme(theme_name)
    current_season = current_southern_hemisphere_season()
    st.markdown(f'''
    <div class="seasonal-preview-card">Accent preview: <span class="seasonal-theme-name"></span></div>
    <div class="grid-3">
      <div class="card"><h3>Selected accent</h3><p><strong>{html.escape(current_display)}</strong></p></div>
      <div class="card"><h3>Seasonal default</h3><p>Seasonal currently resolves to <strong>{html.escape(current_season)}</strong> and updates automatically.</p></div>
      <div class="card"><h3>Contrast</h3><p>Card text and card surfaces are paired from the active background so the accent does not create white-on-white or charcoal-on-black text.</p></div>
    </div>
    ''', unsafe_allow_html=True)

    b1, b2 = st.columns([1, 1])
    with b1:
        save_clicked = st.button("Save theme", use_container_width=True)
    with b2:
        reset_clicked = st.button("Reset to Seasonal", use_container_width=True)

    if reset_clicked:
        theme_name = "Seasonal"
        st.session_state["hosted_theme_preference"] = "Seasonal"
        persisted = False
        if sheet_id:
            ok_sheet, _message_sheet = save_online_setting(sheet_id, "theme", "Seasonal")
            persisted = persisted or ok_sheet
        if user.get("email") and supabase_available():
            ok_profile, _message_profile = update_supabase_user_theme(user.get("email", ""), "Seasonal", actor_email=user.get("email", ""))
            persisted = persisted or ok_profile
        st.success("Theme reset to Seasonal." if persisted or not sheet_id else "Theme reset for this session.")
        st.rerun()

    if save_clicked:
        theme_name = normalise_online_theme(theme_name)
        st.session_state["hosted_theme_preference"] = theme_name
        if theme_name == "Custom":
            st.session_state["hosted_custom_accent"] = picked_custom
        persisted = False
        failures = []
        if sheet_id:
            ok_sheet, message_sheet = save_online_setting(sheet_id, "theme", theme_name)
            persisted = persisted or ok_sheet
            if not ok_sheet:
                failures.append(message_sheet)
            if theme_name == "Custom":
                ok_custom, message_custom = save_online_setting(sheet_id, "custom_accent", picked_custom)
                persisted = persisted or ok_custom
                if not ok_custom:
                    failures.append(message_custom)
        if user.get("email") and supabase_available():
            ok_profile, message_profile = update_supabase_user_theme(user.get("email", ""), theme_name, actor_email=user.get("email", ""))
            persisted = persisted or ok_profile
            if not ok_profile:
                failures.append(message_profile)
        if persisted or not sheet_id:
            st.success("Theme saved." if persisted else "Theme saved for this session.")
            st.rerun()
        else:
            st.warning(safe_user_message(" ".join([m for m in failures if m]) or "The theme was saved for this session, but could not be persisted."))

def about_privacy_tab() -> None:
    st.header("About & Privacy")
    st.markdown("""
    <div class="policy-link-row">
      <a href="?page=privacy">Public Privacy Policy</a>
      <a href="?page=terms">Public Terms of Service</a>
      <a href="?page=oauth">Google access explanation</a>
    </div>
    """, unsafe_allow_html=True)
    st.write(
        "Pathmark uses a small number of services so the online app can run in a browser while keeping your planning records in a file you own. "
        "This page explains what Pathmark accesses and where each kind of information is stored."
    )

    st.subheader("The short version")
    st.markdown("""
    <div class="grid-2">
      <div class="card"><h3>Your planning records</h3><p>Planner saves your Areas, routines, goals, actions, spending plan records, setup progress, tasklists, export records and archive status in your <strong>Pathmark Sync</strong> Google Sheet.</p></div>
      <div class="card"><h3>Your Google Drive</h3><p>Pathmark uses Google's limited <strong>drive.file</strong> permission. It can create and update Pathmark files you use with the app, including Pathmark Sync, Pathmark Finance Template, and Pathmark backup sheets.</p></div>
      <div class="card"><h3>Optional Google sync</h3><p>Google Tasks and Google Calendar sync are optional. If enabled, Pathmark can create Pathmark checklist items and create/update events in calendars named after your Areas, then read linked completion or event status back into Pathmark.</p></div>
      <div class="card"><h3>Your access profile</h3><p>Supabase stores only small access/profile details: email, role, account status, feature flags, theme preference and audit records.</p></div>
      <div class="card"><h3>The app code</h3><p>GitHub stores the Pathmark code, release packages, documentation and database migrations. The current release package has been checked for obvious secrets and private planning records.</p></div>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("What Google access lets Pathmark do")
    st.markdown("""
    When you sign in, Pathmark uses Google for these jobs:

    1. **Sign-in** — Google confirms your email address so Pathmark can apply the correct access level.
    2. **Your Pathmark Sync sheet** — Pathmark creates or updates the Google Sheet that stores your online planning records.
    3. **Finance template and backups** — Pathmark can create a separate Pathmark Finance Template and timestamped Pathmark Backup sheets when you choose those actions.
    4. **Google Tasks permission** — Pathmark can create or update Pathmark checklist items and read linked completion status when you choose Tasks Sync.
    5. **Google Calendar permission** — Pathmark can create or reuse calendars named after your Areas, create or update Pathmark events in those calendars, and check linked event status when you choose Calendar Sync.

    Pathmark now explains these permissions before sending you to Google for the first time. The Google connection may grant Sheets/Drive, Tasks, and Calendar together, but Tasks and Calendar actions remain optional and user-controlled: Pathmark does not create tasks or events unless you press a sync button. Pathmark uses the limited `drive.file` permission for Drive files. In practical terms, Pathmark works with Pathmark files it creates or files you explicitly use with Pathmark. It does **not** request the broader Google Drive permission that would allow general access to all Drive files.
    """)
    st.markdown("""
    <div class="safe-rule"><strong>Pathmark does not collect your Google password.</strong><br>You sign in on Google's page. Pathmark receives confirmation from Google after you approve access.</div>
    """, unsafe_allow_html=True)

    st.subheader("Security model")
    st.markdown("""
    Pathmark is designed so your private planning and Spending Plan content stays in Google files owned by you. Supabase stores access/profile metadata only, not your projects, routines, finance records, tasklist rows, Google Tasks content, or Google Calendar content.

    Pathmark follows these security guardrails:

    - Use the least privileged Google scopes practical for the feature.
    - Keep Google Tasks and Google Calendar Sync optional in behaviour, even where permission is granted at sign-in.
    - Create or reuse a dedicated Pathmark task list and calendars named after your Areas rather than treating your whole Google account as Pathmark content.
    - Store Google task/event IDs so linked items can be updated without relying on broad title searches.
    - Never store OAuth tokens in Supabase, GitHub, logs, or user-visible error messages.
    - Create safety backups before import, restore, reset, and bulk sync actions.
    - Confirm destructive actions before running them.
    - Make clear that resetting Pathmark Sync does not automatically delete Google Tasks or Google Calendar items.
    """)


    st.subheader("Branding during Google sign-in")
    st.markdown("""
    Pathmark now focuses on the hosted browser app and the Windows desktop app. Browser-tab branding is handled through Streamlit page configuration, while phone-app/PWA shortcut support has been removed until it can be implemented cleanly.

    Google's own account chooser and consent screens are controlled by the Google Cloud OAuth configuration rather than by Streamlit code. To show the Pathmark logo there, the deployed Google Cloud project needs **Google Auth Platform → Branding** set to Pathmark with the Pathmark logo uploaded.
    """)

    st.subheader("Where information is stored")
    st.markdown("""
    | Information | Where it is stored | What that means |
    |---|---|---|
    | Areas, routines, projects, project steps, setup progress, tasklists, sync metadata, export records and archive status | Your Pathmark Sync Google Sheet | This is your online Pathmark workspace. It sits in your Google Drive and is visible to you. |
    | Spending Plan income, outflows, account roles and template-import records | Your Pathmark Sync Google Sheet and optional Pathmark Finance Template | Pathmark Finance Template is created only when you choose to export a template. |
    | Pathmark Sync backups | Separate Google Sheets named Pathmark Backup - timestamp | Created only when you choose backup, restore, template import, or reset actions that create a safety backup. |
    | Google Tasks checklist items and completion status | Google Tasks | Permission may be granted during Google connection, but tasks are created/read only when you use Google Tasks Sync. Pathmark stores linked task IDs/status in Pathmark Sync so it can avoid duplicates and reflect completion. |
    | Google Calendar events and moved/missing status | Google Calendar | Permission may be granted during Google connection. Pathmark uses it to create or reuse calendars named after your Areas, then create/read linked Pathmark events only when you use Google Calendar Sync. Pathmark stores linked event IDs/status in Pathmark Sync so it can avoid duplicates and flag changes for review. |
    | Local Workspace folders, Markdown files, local exports, backups and desktop tasklists | Your chosen Workspace folder on your computer | These are created by Pathmark Desktop, not by Pathmark Online. |
    | Email, access role, account status, feature flags, theme preference and audit records | Supabase | This controls beta/developer access and basic profile behaviour. It does not contain your planning records. |
    | Optional starter-pack libraries | Supabase | Curated read-only library rows, such as NZ Seasonal Produce, can be copied into your Pathmark Sync sheet after access is granted. |
    | App code, release files, public documentation and Supabase migration files | GitHub | This is the public/deployment codebase. The current package does not contain Google OAuth tokens, Supabase secret keys, client secrets or private planning records. |
    | Google OAuth client secrets, Supabase secret keys and deployment secrets | Streamlit secrets | These are deployment credentials held outside the GitHub repository. |
    """)

    st.subheader("What Pathmark stores in each service")
    st.markdown("""
    **Google Sheets** store your online Pathmark records, optional finance template, and optional backup sheets.  
    **Google Tasks** stores synced checklist items only after you choose Google Tasks Sync.  
    **Google Calendar** stores synced Pathmark events in calendars named after your Areas only after you choose Google Calendar Sync.  
    **Supabase** stores access/profile metadata and optional read-only starter-pack library rows.  
    **GitHub** stores code and release files only.  
    **Streamlit** hosts the app and stores deployment secrets outside the repository.

    The current release package has been checked for obvious secret patterns and private planning records before packaging. No real Supabase secret key, Google client secret, OAuth token, private key or private planning sheet was found in the release package.
    """)

    st.subheader("Spending Plan and financial advice")
    render_spending_plan_disclaimer(compact=False)
    st.markdown("""
    Spending Plan calculations and AP suggestions are generated from the figures and categories you enter. They are intended to help you see weekly equivalents, planned outflows, safe-to-spend amounts and possible account transfers. They should be checked against your own bank accounts, bills, contracts and obligations before you act on them.

    If you are struggling with debt, repayments, bills or urgent money pressure, consider contacting a free financial mentor or another appropriate support service in your area. Pathmark should not be used as a substitute for tailored financial, legal, tax or debt advice.
    """)

    st.subheader("Disconnecting or deleting")
    st.markdown("""
    - You can create backups, restore from backup, or restore Pathmark Sync to default from **Planner → Settings → Backup & restore**.
    - You can disconnect Google access from **Planner → Settings**. This revokes the current Google token and stops Pathmark from writing to your Pathmark Sync sheet, Google Tasks, or Google Calendar until you sign in again.
    - You can also remove Pathmark from your Google Account permissions.
    - Pathmark Online includes a deletion option in **Settings** for users who want to remove their online Pathmark data from Google Drive and disconnect access.
    - That deletion workflow only lists files Pathmark can identify as Pathmark files available to this app, such as the connected **Pathmark Sync** sheet or app-tagged Pathmark files. Pathmark does not delete Drive folders simply because they are named Pathmark.
    - You can also open, copy, export or delete your Pathmark Sync sheet directly from Google Drive.
    - Deleting online Pathmark data does not delete local Workspace files on your computer.
    """)

    with st.expander("Service-by-service summary", expanded=False):
        st.markdown("""
        **Google**  
        Used for sign-in, your own Pathmark Sync sheet, optional finance templates, optional backup sheets, Google Tasks Sync, and Google Calendar Sync. Pathmark requests `drive.file`, which limits Drive access to files Pathmark creates or files you explicitly authorise for Pathmark. Google Tasks and Calendar permissions may be granted during the Google connection, but Pathmark only creates or updates Pathmark tasks/events when you press sync actions. Pathmark does not have general access to your whole Google Drive.

        **Streamlit**  
        Hosts the Pathmark web app. Deployment credentials are kept in Streamlit secrets, outside the GitHub repository.

        **Supabase**  
        Stores access/profile metadata only: email, role, account status, feature flags, audit logs and theme preference. Supabase does not store your projects, routines, tasklists, calendar rows, private planning content, or your edited grocery inventory.

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

def render_missing_sync_sheet_recovery(context: str = "online") -> bool:
    """Render a recovery path when Pathmark Sync is missing.

    Returns True when the caller should stop normal rendering for this run.
    """
    recovery_message = st.session_state.get("sync_sheet_recovery_message", "Pathmark could not find a Pathmark Sync sheet in Google Drive.")

    st.markdown("## Welcome to Planning")
    st.markdown("Planning saves your routines, projects, tasklist, sync links and Finance records in a Google Sheet called **Pathmark Sync**.")
    st.info("No Pathmark Sync sheet was found for this Google account. You can start fresh with default Areas, load starter examples, restore from a backup, or check Google Drive Trash if you deleted the sheet recently.")

    with st.expander("Why am I seeing this?", expanded=False):
        st.write(safe_user_message(recovery_message))
        st.caption("Pathmark uses limited Google Drive access. It can only find files it created or files you have authorised for Pathmark. Recreating Pathmark Sync does not delete Google Tasks or Google Calendar events, but existing sync links may need review unless restored from backup.")

    st.markdown("### Start or restore")
    c1, c2, c3 = st.columns(3)
    if c1.button("Create fresh Pathmark Sync with default Areas", key=f"recreate_sync_{context}", use_container_width=True):
        ok, new_sheet_id, url_or_msg = create_user_sync_sheet()
        if ok:
            st.session_state.pop("sync_sheet_recovery_message", None)
            st.success("Created a fresh Pathmark Sync sheet with default Areas.")
            if url_or_msg:
                st.link_button("Open Pathmark Sync", url_or_msg, use_container_width=True)
            st.rerun()
        else:
            st.error(safe_user_message(url_or_msg))

    if c2.button("Create with starter examples", key=f"recreate_sync_examples_{context}", use_container_width=True):
        ok, new_sheet_id, url_or_msg = create_user_sync_sheet(include_default_areas=False)
        if ok:
            ok_examples, msg_examples = append_many_online_records(new_sheet_id, build_starter_example_records())
            st.session_state.pop("sync_sheet_recovery_message", None)
            if ok_examples:
                st.success("Created a new Pathmark Sync sheet with starter examples.")
            else:
                st.warning(safe_user_message(msg_examples))
            if url_or_msg:
                st.link_button("Open Pathmark Sync", url_or_msg, use_container_width=True)
            st.rerun()
        else:
            st.error(safe_user_message(url_or_msg))

    c3.link_button("Check Google Drive Trash", "https://drive.google.com/drive/trash", use_container_width=True)

    with st.expander("Restore from Pathmark Backup", expanded=False):
        ok_backups, backups, backup_msg = list_pathmark_backup_sheets("")
        if ok_backups and backups:
            labels = [f"{b.get('name','Untitled backup')} — {b.get('modifiedTime','')}" for b in backups]
            selected_label = st.selectbox("Choose a backup sheet", labels, key=f"missing_sync_backup_choice_{context}")
            selected = backups[labels.index(selected_label)] if selected_label in labels else backups[0]
            st.link_button("Open selected backup", selected.get("webViewLink", ""), use_container_width=True)
            confirm = st.checkbox("I understand Pathmark will create a new Pathmark Sync sheet from this backup.", key=f"missing_sync_backup_confirm_{context}")
            if st.button("Restore backup into new Pathmark Sync", key=f"missing_sync_restore_backup_{context}", use_container_width=True, disabled=not confirm):
                ok_restore, new_sheet_id, msg_restore = restore_missing_pathmark_sync_from_backup(selected.get("id", ""))
                if ok_restore:
                    st.success(safe_user_message(msg_restore))
                    st.rerun()
                else:
                    st.error(safe_user_message(msg_restore))
        elif ok_backups:
            st.info("No Pathmark Backup sheets were found. Create a fresh Pathmark Sync sheet to start using Pathmark, or check Google Drive Trash if you deleted the sheet recently.")
        else:
            st.warning(safe_user_message(backup_msg))

    return True


def render_connection_summary(credentials: Any, sheet_id: str, auth_ready: bool) -> None:
    """Show a compact connection state without exposing OAuth plumbing."""
    if credentials and sheet_id:
        st.markdown("<div class='connection-strip'><strong>Ready</strong> Records are saved to Pathmark Sync for this session.</div>", unsafe_allow_html=True)
    elif credentials:
        st.markdown("<div class='connection-strip'><strong>Google connected</strong> Preparing Pathmark Sync.</div>", unsafe_allow_html=True)
    elif auth_ready:
        st.info("Sign in with Google to use Planning, Finance and Nutrition.")
    else:
        st.warning("Google access is not configured for this deployment.")

def on_the_go_tab() -> None:
    handle_google_oauth_redirect()
    auth_ready = web_oauth_available()
    credentials = google_credentials_from_session()
    should_prepare_sheet = bool(credentials and not st.session_state.get("sync_sheet_id"))
    if should_prepare_sheet and (st.session_state.pop("auto_create_sync_sheet_after_connect", False) or not st.session_state.get("sync_sheet_ready_attempted")):
        st.session_state["sync_sheet_ready_attempted"] = True
        ok, sheet_id_found, message = ensure_pathmark_sync_sheet_ready()
        if not ok:
            st.warning(safe_user_message(message))

    sheet_id = st.session_state.get("sync_sheet_id", "")
    if credentials and sheet_id:
        apply_online_theme(sheet_id)
        render_seasonal_banner(compact=True)
    st.header("Planning")
    render_connection_summary(credentials, sheet_id, auth_ready)

    if not credentials and auth_ready:
        render_google_permissions_onboarding(compact=True)
        return

    if credentials and not sheet_id:
        render_missing_sync_sheet_recovery("online")
        return

    if not (credentials and sheet_id):
        st.info("Pathmark is still preparing your online workspace. Refresh online data or reconnect from Settings if this does not resolve.")
        return

    service = sheets_service()
    if service is not None:
        try:
            with st.spinner("Loading your Pathmark Planner workspace from Google Sheets..."):
                ensure_pathmark_online_schema(service, sheet_id)
                load_online_tables(sheet_id)
        except Exception:
            st.warning("Pathmark could not prepare your online workspace. Please refresh online data or reconnect Google access, then try again.")

    # The Creation Wizard now has its own Planner tab beside Home.
    sections = st.tabs([
        "Dashboard",
        "Creation Wizard",
        "Review Queue",
        "Areas",
        "Routines",
        "Projects",
        "Google Sync",
        "Tasklist",
        "Archive",
        "Settings",
    ])
    with sections[0]:
        render_safe_section("Dashboard", render_online_overview, sheet_id)
    with sections[1]:
        render_safe_section("Creation Wizard", render_pathmark_creation_wizard, sheet_id)
    with sections[2]:
        render_safe_section("Review Queue", render_review_queue_manager, sheet_id)
    with sections[3]:
        render_safe_section("Areas", render_area_manager, sheet_id)
    with sections[4]:
        render_safe_section("Routines", render_routine_manager, sheet_id)
    with sections[5]:
        render_safe_section("Projects", render_goal_manager, sheet_id)
    with sections[6]:
        render_safe_section("Google Sync", render_google_sync_manager, sheet_id)
    with sections[7]:
        render_safe_section("Tasklist", render_tasklist_manager, sheet_id)
    with sections[8]:
        render_safe_section("Archive", render_archive_manager, sheet_id)
    with sections[9]:
        render_safe_section("Settings", render_online_settings, sheet_id)


GROCERY_CATEGORIES = [
    "Baby Care",
    "Bakery",
    "Baking Supplies & Sugar",
    "Beauty & Grooming",
    "Beer, Cider & Wine",
    "Biscuits & Crackers",
    "Breakfast Cereals",
    "Bulk & Loose Foods",
    "Butchery",
    "Canned & Prepared Foods",
    "Cheese",
    "Cleaning Products",
    "Cold Drinks",
    "Condiments & Dressings",
    "Confectionery",
    "Dairy & Eggs",
    "Deli, Salads & Cooked Meats",
    "Desserts",
    "Fruits & Vegetables",
    "Garage & Outdoor",
    "Health & Wellness",
    "Hot Drinks",
    "Household",
    "Jams, Honey & Spreads",
    "Laundry",
    "Pasta, Rice & Noodles",
    "Pet Supplies",
    "Prep",
    "Produce",
    "Salad & Cooking Oils",
    "Sauces, Stock & Marinades",
    "Seafood",
    "Snack Foods",
    "Spices & Seasonings",
    "Stationary & Entertainments",
    "World Foods",
    "Frozen Foods"
]

GROCERY_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

RECIPE_COURSES = ["Breakfast", "Lunch", "Dinner", "Main", "Side", "Starter", "Dessert", "Snack", "Salad", "Soup", "Sharing", "Drink", "Other"]
RECIPE_MEAL_CATEGORIES = ["Breakfast", "Lunch", "Dinner", "Main", "Side", "Starter", "Dessert", "Snack", "Salad", "Soup", "Sharing", "Mezze", "Small Plate", "Preserve", "Drink", "Sauce / Condiment", "Baking"]
RECIPE_CUISINE_TAGS = ["New Zealand", "Japanese", "Korean", "Chinese", "Danish", "Scottish", "English", "French", "Italian", "Mexican", "Middle Eastern", "Indian", "Thai", "Vietnamese", "Mediterranean", "Fusion"]
RECIPE_DISH_STYLE_TAGS = ["Agemono", "Zenzai", "Donburi", "Nabe", "Mezze Plate", "Gratin", "Bake", "Curry", "Taco", "Risotto", "Pasta", "Pie", "Salad Bowl", "Fritter", "Croquette", "Soup", "Stew", "Cake", "Biscuit", "Sauce"]
RECIPE_DIETARY_TAGS = ["Vegetarian", "Vegan", "Gluten free", "Dairy free", "Nut free", "Contains egg", "Contains dairy", "Contains nuts", "Contains sesame", "Contains soy"]


GROCERY_NUTRITION_SOURCE_ROWS: list[dict[str, Any]] = [
    # Public sample rows only. The full curated starter library should be stored
    # outside the public GitHub repository, for example in Supabase starter-pack
    # tables, then copied into a user-owned Pathmark Sync sheet after access is
    # granted.
    {
        "food": "sample.ingredient",
        "portion": "100 g",
        "kcal per portion": "0 kcal",
        "total carbohydrate": "",
        "total fat": "",
        "protein": "",
    }
]

def _display_food_name(name: str) -> str:
    text = str(name or "").replace(".", " ").replace("_", " ").strip()
    parts = [p for p in re.split(r"\s+", text) if p]
    return " ".join(part.capitalize() if part.islower() else part for part in parts)


def _normalise_food_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name or "").lower())


def _parse_amount_and_unit(value: Any) -> tuple[float | None, str]:
    text = str(value or "").strip()
    if not text:
        return None, ""
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None, text.lower()
    amount = float(match.group(0))
    unit = text[match.end():].strip().lower()
    unit = unit.replace("grams", "g").replace("gram", "g").replace("millilitres", "ml").replace("milliliters", "ml")
    unit = unit.replace("millilitre", "ml").replace("milliliter", "ml")
    return amount, unit


def _amount_from_text(value: Any) -> float:
    amount, _unit = _parse_amount_and_unit(value)
    return float(amount or 0.0)


def _grocery_category_for_item(item: str) -> str:
    key = str(item or "").lower().replace(".", " ")
    spices = ["chilli", "pepper", "cumin", "allspice", "thyme", "basil", "coriander", "parsley", "salt"]
    oils = ["oil"]
    baking = ["flour", "sugar", "baking", "cornstarch", "vanilla"]
    dairy = ["milk", "yoghurt", "yogurt", "egg", "butter", "cream", "fraiche"]
    cheese = ["cheese", "parmesan"]
    sauces = ["sauce", "paste", "stock", "sriracha", "kewpie", "molasses", "vinegar"]
    spreads = ["jam", "syrup", "honey", "spread", "peanut butter", "tahini"]
    grains = ["rice", "noodle", "pasta", "tortilla", "pita", "masa", "chickpea"]
    produce = ["onion", "ginger", "garlic", "mushroom", "avocado", "kohlrabi", "lime", "orange", "lemon", "lettuce", "cucumber", "carrot", "capsicum", "leek", "tomato", "cabbage", "sprout", "bok choy", "asparagus", "tofu", "radish", "eggplant"]
    snacks = ["biscuit", "cracker", "peanut", "pine nut", "sesame seed"]
    if any(word in key for word in oils):
        return "Salad & Cooking Oils"
    if any(word in key for word in spices):
        return "Spices & Seasonings"
    if any(word in key for word in sauces):
        return "Sauces, Stock & Marinades"
    if any(word in key for word in baking):
        return "Baking Supplies & Sugar"
    if any(word in key for word in cheese):
        return "Cheese"
    if any(word in key for word in dairy):
        return "Dairy & Eggs"
    if any(word in key for word in spreads):
        return "Jams, Honey & Spreads"
    if any(word in key for word in grains):
        return "Pasta, Rice & Noodles"
    if any(word in key for word in produce):
        return "Fruits & Vegetables"
    if any(word in key for word in snacks):
        return "Snack Foods"
    if "weet" in key or "cereal" in key:
        return "Breakfast Cereals"
    if "hibiscus" in key:
        return "Hot Drinks"
    return "World Foods"


def grocery_nutrition_starter_records() -> list[dict[str, Any]]:
    records = []
    seen = set()
    for row in GROCERY_NUTRITION_SOURCE_ROWS:
        raw = str(row.get("food", "") or "").strip()
        if not raw:
            continue
        key = _normalise_food_key(raw)
        if key in seen:
            continue
        seen.add(key)
        portion_qty, portion_unit = _parse_amount_and_unit(row.get("portion", ""))
        record = {
            "nutrition_id": f"nutrition-{uuid.uuid4().hex[:12]}",
            "item": _display_food_name(raw),
            "category_name": _grocery_category_for_item(raw),
            "portion_quantity": str(portion_qty or ""),
            "portion_unit": portion_unit,
            "kcal_per_portion": str(_amount_from_text(row.get("kcal per portion", ""))),
            "notes": "Imported from previous nutrition examples.",
            "status": "active",
            "source": "Uploaded nutrition examples",
        }
        for source_key, dest_key in NUTRITION_FIELD_MAP.items():
            record[dest_key] = str(row.get(source_key, "") or "")
        records.append(record)
    return records


def grocery_nutrition_inventory_records() -> list[dict[str, Any]]:
    records = []
    for row in GROCERY_NUTRITION_SOURCE_ROWS:
        item = _display_food_name(row.get("food", ""))
        if not item:
            continue
        portion_qty, portion_unit = _parse_amount_and_unit(row.get("portion", ""))
        records.append({
            "inventory_id": f"inventory-{uuid.uuid4().hex[:12]}",
            "category_name": _grocery_category_for_item(item),
            "item": item,
            "quantity": "",
            "unit": portion_unit,
            "expiry_date": "",
            "storage": "",
            "is_frozen": "",
            "requires_substitute": "",
            "suggested_substitute": "",
            "must_be_homegrown": "",
            "unavailable": "",
            "imported": "",
            "canned": "",
            "in_season": "",
            "limited_in_season": "",
            "months": "",
            "notes": f"Nutrition example portion: {portion_qty or ''} {portion_unit}".strip(),
            "status": "active",
            "source": "Uploaded nutrition examples",
        })
    return records

GROCERY_PRODUCE_STARTERS: list[dict[str, Any]] = [
    # Public sample row only. The full NZ Seasonal Produce starter pack is
    # designed to be imported from Supabase after the user receives access.
    {"item": "Sample Produce", "raw": "sample.produce", "months": [], "tag": "", "substitute": ""}
]

def _grocery_bool_text(value: bool) -> str:
    return "TRUE" if bool(value) else ""


def _produce_starter_to_inventory_record(item: dict[str, Any]) -> dict[str, Any]:
    tag = str(item.get("tag", "") or "").strip().lower()
    months = [str(m).strip() for m in item.get("months", []) if str(m).strip()]
    raw_name = str(item.get("raw", "") or "").strip()
    substitute = str(item.get("substitute", "") or "").replace(".", " ").strip().title()
    requires_substitute = tag in {"substitute", "requires substitute"} or bool(substitute)
    limited = tag in {"limited", "limited in season"}
    in_season = bool(months) and not tag in {"unavailable"}
    notes = "Imported from Produce.xlsx."
    if raw_name:
        notes += f" Original produce key: {raw_name}."
    if tag:
        notes += f" Produce status: {item.get('tag')}."
    return {
        "inventory_id": f"inventory-{uuid.uuid4().hex[:12]}",
        "category_name": "Produce",
        "item": str(item.get("item", "") or "").strip(),
        "quantity": "0",
        "unit": "",
        "expiry_date": "",
        "storage": "Fresh",
        "is_frozen": _grocery_bool_text(tag == "frozen"),
        "requires_substitute": _grocery_bool_text(requires_substitute),
        "suggested_substitute": substitute,
        "must_be_homegrown": _grocery_bool_text(tag == "homegrown"),
        "unavailable": _grocery_bool_text(tag == "unavailable"),
        "imported": _grocery_bool_text(tag == "imported"),
        "canned": _grocery_bool_text(tag == "canned"),
        "in_season": _grocery_bool_text(in_season),
        "limited_in_season": _grocery_bool_text(limited),
        "months": ", ".join(months),
        "notes": notes,
        "status": "active",
        "source": "Produce.xlsx import",
    }


def grocery_category_starter_records() -> list[dict[str, Any]]:
    colours = ["#334E9E", "#1B8EA8", "#5D7F61", "#8A5A44", "#B66A00", "#8B4E9F", "#475569"]
    records: list[dict[str, Any]] = []
    for idx, category in enumerate(GROCERY_CATEGORIES, start=1):
        records.append({
            "category_id": f"grocery-category-{uuid.uuid4().hex[:12]}",
            "category_name": category,
            "description": "Grocery shopping-list category.",
            "colour": colours[(idx - 1) % len(colours)],
            "sort_order": str(idx),
            "status": "active",
            "source": "Pathmark grocery category defaults",
        })
    return records


def grocery_produce_inventory_records() -> list[dict[str, Any]]:
    return [_produce_starter_to_inventory_record(item) for item in GROCERY_PRODUCE_STARTERS if str(item.get("item", "")).strip()]




def _simple_starter_rows(values: list[str], id_prefix: str, name_col: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, value in enumerate(values, start=1):
        rows.append({
            f"{id_prefix}_id": f"{id_prefix}-{uuid.uuid4().hex[:12]}",
            name_col: value,
            "description": "Meal Plan recipe classification default.",
            "sort_order": str(idx),
            "status": "active",
            "source": "Pathmark recipe classification defaults",
        })
    return rows


def recipe_classification_starter_records() -> dict[str, list[dict[str, Any]]]:
    return {
        "recipe_courses": _simple_starter_rows(RECIPE_COURSES, "course", "course_name"),
        "recipe_meal_categories": _simple_starter_rows(RECIPE_MEAL_CATEGORIES, "meal_category", "meal_category_name"),
        "recipe_cuisine_tags": _simple_starter_rows(RECIPE_CUISINE_TAGS, "cuisine_tag", "cuisine_tag_name"),
        "recipe_dish_style_tags": _simple_starter_rows(RECIPE_DISH_STYLE_TAGS, "dish_style_tag", "dish_style_tag_name"),
        "recipe_dietary_tags": _simple_starter_rows(RECIPE_DIETARY_TAGS, "dietary_tag", "dietary_tag_name"),
    }

def ensure_grocery_default_rows(sheet_id: str) -> None:
    """Create only the public grocery category structure where missing.

    Curated nutrition, produce, and recipe data is deliberately not bundled into
    the public app repository. It can be imported separately through Starter
    Packs once access is granted.
    """
    if not sheet_id:
        return
    cache_key = f"grocery_defaults_checked::{sheet_id}"
    if st.session_state.get(cache_key):
        return
    st.session_state[cache_key] = True
    try:
        records: dict[str, list[dict[str, Any]]] = {}
        if active_online_df(read_online_table(sheet_id, "grocery_categories")).empty:
            records["grocery_categories"] = grocery_category_starter_records()
        for table, rows in recipe_classification_starter_records().items():
            if active_online_df(read_online_table(sheet_id, table)).empty:
                records[table] = rows
        if records:
            ok, _msg = append_many_online_records(sheet_id, records)
            if ok:
                clear_online_cache(sheet_id)
    except Exception:
        pass


def _grocery_table_options(sheet_id: str, table: str, label_col: str, fallback: list[str] | None = None) -> list[str]:
    df = active_online_df(read_online_table(sheet_id, table))
    if df.empty or label_col not in df.columns:
        return list(fallback or [])
    values = sorted({str(v).strip() for v in df[label_col].tolist() if str(v).strip()})
    return values or list(fallback or [])


def grocery_category_options(sheet_id: str) -> list[str]:
    values = _grocery_table_options(sheet_id, "grocery_categories", "category_name", GROCERY_CATEGORIES)
    return values or GROCERY_CATEGORIES


def grocery_inventory_options(sheet_id: str) -> list[str]:
    return _grocery_table_options(sheet_id, "grocery_inventory", "item", [])


def recipe_course_options(sheet_id: str) -> list[str]:
    return _grocery_table_options(sheet_id, "recipe_courses", "course_name", RECIPE_COURSES)


def recipe_meal_category_options(sheet_id: str) -> list[str]:
    return _grocery_table_options(sheet_id, "recipe_meal_categories", "meal_category_name", RECIPE_MEAL_CATEGORIES)


def recipe_cuisine_tag_options(sheet_id: str) -> list[str]:
    return _grocery_table_options(sheet_id, "recipe_cuisine_tags", "cuisine_tag_name", RECIPE_CUISINE_TAGS)


def recipe_dish_style_options(sheet_id: str) -> list[str]:
    return _grocery_table_options(sheet_id, "recipe_dish_style_tags", "dish_style_tag_name", RECIPE_DISH_STYLE_TAGS)


def recipe_dietary_tag_options(sheet_id: str) -> list[str]:
    return _grocery_table_options(sheet_id, "recipe_dietary_tags", "dietary_tag_name", RECIPE_DIETARY_TAGS)


def _split_tag_text(value: Any) -> set[str]:
    return {part.strip().lower() for part in re.split(r"[,;/|]", str(value or "")) if part.strip()}


def _join_tags(values: list[str] | tuple[str, ...] | set[str]) -> str:
    return ", ".join([str(v).strip() for v in values if str(v).strip()])


def _find_grocery_inventory_record(sheet_id: str, item_name: str) -> dict[str, Any] | None:
    inventory = active_online_df(read_online_table(sheet_id, "grocery_inventory"))
    target = str(item_name or "").strip().lower()
    if inventory.empty or not target:
        return None
    for _, row in inventory.iterrows():
        if str(row.get("item", "") or "").strip().lower() == target:
            return row.to_dict()
    return None


def _add_inventory_item_if_needed(sheet_id: str, ingredient: str, category: str, *, unit: str = "", notes: str = "") -> str:
    existing = _find_grocery_inventory_record(sheet_id, ingredient)
    if existing:
        return str(existing.get("inventory_id", "") or "")
    record = {
        "inventory_id": f"inventory-{uuid.uuid4().hex[:12]}",
        "category_name": category or "Produce",
        "item": ingredient,
        "quantity": "0",
        "unit": unit,
        "expiry_date": "",
        "storage": "",
        "is_frozen": "",
        "requires_substitute": "",
        "suggested_substitute": "",
        "must_be_homegrown": "",
        "unavailable": "",
        "imported": "",
        "canned": "",
        "in_season": "",
        "limited_in_season": "",
        "months": "",
        "notes": notes or "Added while creating a recipe or shopping-list item.",
        "status": "active",
        "source": "Meal Plan",
    }
    ok, _msg = append_online_record(sheet_id, "grocery_inventory", record)
    return record["inventory_id"] if ok else ""


def _shopping_items_for_list(sheet_id: str, list_id: str) -> pd.DataFrame:
    items = active_online_df(read_online_table(sheet_id, "shopping_items"))
    if items.empty:
        return items
    return items[items["shopping_list_id"].fillna("").astype(str).eq(str(list_id))].reset_index(drop=True)



def grocery_nutrition_options(sheet_id: str) -> list[str]:
    return _grocery_table_options(sheet_id, "grocery_nutrition", "item", [])


def _find_nutrition_record(sheet_id: str, item_name: str) -> dict[str, Any] | None:
    nutrition = active_online_df(read_online_table(sheet_id, "grocery_nutrition"))
    if nutrition.empty:
        return None
    key = _normalise_food_key(item_name)
    for _, row in nutrition.iterrows():
        if _normalise_food_key(row.get("item", "")) == key:
            return row.to_dict()
    return None


def _unit_to_base(amount: float, unit: str) -> tuple[float, str]:
    unit = str(unit or "").strip().lower()
    unit = unit.replace("grams", "g").replace("gram", "g").replace("kgs", "kg")
    unit = unit.replace("millilitres", "ml").replace("milliliters", "ml").replace("litres", "l").replace("liters", "l")
    conversions = {
        "kg": (1000.0, "g"),
        "g": (1.0, "g"),
        "mg": (0.001, "g"),
        "l": (1000.0, "ml"),
        "ml": (1.0, "ml"),
        "tbsp": (15.0, "ml"),
        "tablespoon": (15.0, "ml"),
        "tablespoons": (15.0, "ml"),
        "tsp": (5.0, "ml"),
        "teaspoon": (5.0, "ml"),
        "teaspoons": (5.0, "ml"),
        "cup": (250.0, "ml"),
        "cups": (250.0, "ml"),
    }
    factor, base_unit = conversions.get(unit, (1.0, unit))
    return amount * factor, base_unit


def _base_quantity_for_cost(amount: float, unit: str) -> tuple[float, str]:
    qty, base = _unit_to_base(amount, unit)
    # For simple meal-planning estimates, treat 1 g as equivalent to 1 ml.
    if base == "ml":
        return qty, "g"
    return qty, base


def _estimate_ingredient_cost(row: dict[str, Any]) -> tuple[float | None, str]:
    recipe_qty = _amount_from_text(row.get("quantity", ""))
    recipe_unit = str(row.get("unit", "") or "").strip()
    purchased_qty = _amount_from_text(row.get("purchased_quantity", ""))
    purchased_unit = str(row.get("purchased_unit", "") or "").strip()
    purchased_price = _amount_from_text(row.get("purchased_price", ""))
    if recipe_qty <= 0:
        return None, "Missing recipe quantity"
    if purchased_qty <= 0 or purchased_price <= 0:
        return None, "Missing price data"
    recipe_amount, recipe_base = _base_quantity_for_cost(recipe_qty, recipe_unit)
    purchase_amount, purchase_base = _base_quantity_for_cost(purchased_qty, purchased_unit)
    if recipe_base and purchase_base and recipe_base == purchase_base and purchase_amount > 0:
        return purchased_price * (recipe_amount / purchase_amount), "Calculated"
    if recipe_unit and purchased_unit and recipe_unit.lower() == purchased_unit.lower() and purchased_qty > 0:
        return purchased_price * (recipe_qty / purchased_qty), "Calculated"
    return None, f"Cannot convert {recipe_unit or 'blank unit'} to {purchased_unit or 'blank purchased unit'}"


def _ingredient_seasonality_status(sheet_id: str, ingredient: str) -> tuple[str, str, str]:
    inv = _find_grocery_inventory_record(sheet_id, ingredient)
    if not inv:
        return "Not found in inventory", "", ""
    months = str(inv.get("months", "") or "").strip()
    substitute = str(inv.get("suggested_substitute", "") or "").strip()
    flags = []
    for col, label in [
        ("requires_substitute", "Requires substitute"),
        ("must_be_homegrown", "Homegrown only"),
        ("unavailable", "Unavailable"),
        ("imported", "Imported"),
        ("canned", "Canned"),
        ("is_frozen", "Frozen"),
        ("limited_in_season", "Limited in season"),
    ]:
        if str(inv.get(col, "") or "").strip().lower() in {"yes", "true", "1"}:
            flags.append(label)
    status = "; ".join(flags) if flags else (f"Seasonal months: {months}" if months else "No seasonality flags")
    return status, months, substitute


def _estimate_ingredient_kcal(row: dict[str, Any], nutrition_row: dict[str, Any] | None = None) -> tuple[float | None, str]:
    if nutrition_row is None:
        return None, "Missing nutrition data"
    qty = _amount_from_text(row.get("quantity", ""))
    if qty <= 0:
        return None, "Missing quantity"
    recipe_unit = str(row.get("unit", "") or "").strip().lower()
    portion_qty = _amount_from_text(nutrition_row.get("portion_quantity", ""))
    portion_unit = str(nutrition_row.get("portion_unit", "") or "").strip().lower()
    kcal = _amount_from_text(nutrition_row.get("kcal_per_portion", ""))
    if portion_qty <= 0 or kcal <= 0:
        return None, "Missing kcal or portion data"
    recipe_amount, recipe_base = _unit_to_base(qty, recipe_unit)
    portion_amount, portion_base = _unit_to_base(portion_qty, portion_unit)
    if recipe_base and portion_base and recipe_base == portion_base and portion_amount > 0:
        return kcal * (recipe_amount / portion_amount), "Calculated"
    if recipe_unit and portion_unit and recipe_unit == portion_unit and portion_qty > 0:
        return kcal * (qty / portion_qty), "Calculated"
    return None, f"Cannot convert {recipe_unit or 'blank unit'} to {portion_unit or 'blank portion unit'}"


def recipe_nutrition_summary(sheet_id: str, recipe_id: str, servings: Any) -> tuple[pd.DataFrame, float, float, list[str]]:
    ingredients = active_online_df(read_online_table(sheet_id, "recipe_ingredients"))
    nutrition = active_online_df(read_online_table(sheet_id, "grocery_nutrition"))
    rows = ingredients[ingredients["recipe_id"].fillna("").eq(recipe_id)].copy() if not ingredients.empty else pd.DataFrame()
    details = []
    total_kcal = 0.0
    total_cost = 0.0
    missing = []
    for _, ing in rows.iterrows():
        ing_dict = ing.to_dict()
        item = str(ing_dict.get("ingredient", "") or "")
        nrow = None
        if not nutrition.empty:
            match = nutrition[nutrition["item"].fillna("").apply(_normalise_food_key).eq(_normalise_food_key(item))]
            if not match.empty:
                nrow = match.iloc[0].to_dict()
        kcal, kcal_status = _estimate_ingredient_kcal(ing_dict, nrow)
        cost, cost_status = _estimate_ingredient_cost(ing_dict)
        season_status, season_months, suggested_sub = _ingredient_seasonality_status(sheet_id, item) if str(ing_dict.get("lookup_seasonality", "") or "").strip().lower() in {"yes", "true", "1"} else ("", "", "")
        if kcal is not None:
            total_kcal += kcal
        else:
            missing.append(f"{item}: {kcal_status}")
        if cost is not None:
            total_cost += cost
        elif str(ing_dict.get("purchased_quantity", "") or "").strip() or str(ing_dict.get("purchased_price", "") or "").strip():
            missing.append(f"{item}: {cost_status}")
        details.append({
            "Ingredient": item,
            "Quantity": str(ing_dict.get("quantity", "") or ""),
            "Unit": str(ing_dict.get("unit", "") or ""),
            "Category": str(ing_dict.get("category_name", "") or ""),
            "Fresh produce": str(ing_dict.get("is_fresh_produce", "") or ""),
            "Seasonality": str(ing_dict.get("seasonality_status", "") or season_status),
            "Suggested substitute": str(ing_dict.get("suggested_substitute", "") or suggested_sub),
            "kcal estimate": round(kcal, 1) if kcal is not None else "",
            "Nutrition status": kcal_status,
            "Cost estimate": round(cost, 2) if cost is not None else "",
            "Cost status": cost_status,
        })
    return pd.DataFrame(details), total_kcal, total_cost, missing

def render_grocery_nutrition_tab(sheet_id: str) -> None:
    st.subheader("Nutrition information")
    st.caption("Store kcal and nutrition values by ingredient and portion. Recipe calories use these rows when units can be matched or converted.")
    categories = grocery_category_options(sheet_id)
    nutrition = active_online_df(read_online_table(sheet_id, "grocery_nutrition"))
    search = st.text_input("Search nutrition", placeholder="e.g., sesame, rice, soy sauce")
    view = nutrition.copy()
    if not view.empty and search.strip():
        mask = view.apply(lambda row: search.strip().lower() in " ".join(str(v).lower() for v in row.values), axis=1)
        view = view[mask]
    display_cols = [c for c in ["item", "category_name", "portion_quantity", "portion_unit", "kcal_per_portion", "total_carbohydrate", "total_fat", "protein", "sodium", "dietary_fibre", "notes"] if c in view.columns]
    st.dataframe(view[display_cols] if not view.empty else pd.DataFrame(columns=display_cols), use_container_width=True, hide_index=True, height=360)
    with st.form("add_grocery_nutrition_form"):
        st.markdown("#### Add or update nutrition item")
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        with c1:
            item = st.text_input("Ingredient / food")
            category = st.selectbox("Category", categories, key="nutrition_category")
        with c2:
            portion_quantity = st.text_input("Portion quantity", placeholder="100")
            portion_unit = st.text_input("Portion unit", placeholder="g")
        with c3:
            kcal = st.text_input("kcal per portion", placeholder="120")
        with c4:
            protein = st.text_input("Protein", placeholder="3 g")
        total_carbs = st.text_input("Total carbohydrate", placeholder="20 g")
        total_fat = st.text_input("Total fat", placeholder="5 g")
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save nutrition item", use_container_width=True)
    if submitted:
        if not item.strip():
            st.warning("Enter an ingredient or food name.")
        else:
            existing = _find_nutrition_record(sheet_id, item)
            record = {
                "item": item.strip(),
                "category_name": category,
                "portion_quantity": str(_amount_from_text(portion_quantity) or portion_quantity).strip(),
                "portion_unit": str(portion_unit or "").strip().lower(),
                "kcal_per_portion": str(_amount_from_text(kcal) or kcal).strip(),
                "total_carbohydrate": total_carbs.strip(),
                "total_fat": total_fat.strip(),
                "protein": protein.strip(),
                "notes": notes.strip(),
                "status": "active",
                "source": "Meal Plan nutrition entry",
            }
            if existing:
                ok, msg = update_online_record(sheet_id, "grocery_nutrition", str(existing.get("nutrition_id", "")), record)
            else:
                record["nutrition_id"] = f"nutrition-{uuid.uuid4().hex[:12]}"
                ok, msg = append_online_record(sheet_id, "grocery_nutrition", record)
            if ok:
                _add_inventory_item_if_needed(sheet_id, item.strip(), category, unit=str(portion_unit or "").strip(), notes="Added from nutrition information.")
                st.success("Nutrition item saved.")
                st.rerun()
            else:
                st.warning(msg)


def _find_existing_grocery_template() -> tuple[bool, str, str]:
    drive = drive_service()
    if drive is None:
        return False, "", ""
    try:
        result = drive.files().list(
            q="appProperties has { key='pathmark_grocery_template' and value='true' } and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            spaces="drive",
            fields="files(id,name,webViewLink,modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=1,
        ).execute()
        files = result.get("files", [])
        if files:
            fid = files[0].get("id", "")
            return True, fid, files[0].get("webViewLink", f"https://docs.google.com/spreadsheets/d/{fid}")
    except Exception:
        pass
    return False, "", ""


def _ensure_grocery_template_file() -> tuple[bool, str, str, str]:
    found, template_id, template_url = _find_existing_grocery_template()
    if found:
        return True, template_id, template_url, "Using your existing Pathmark Grocery Template."
    service = sheets_service()
    drive = drive_service()
    if service is None:
        return False, "", "", "Google Sheets access is not available for this session."
    try:
        spreadsheet = service.spreadsheets().create(
            body={"properties": {"title": GROCERY_TEMPLATE_TITLE}, "sheets": [{"properties": {"title": "README"}}]},
            fields="spreadsheetId,spreadsheetUrl",
        ).execute()
        template_id = spreadsheet.get("spreadsheetId", "")
        template_url = spreadsheet.get("spreadsheetUrl", f"https://docs.google.com/spreadsheets/d/{template_id}")
        if drive is not None and template_id:
            try:
                drive.files().update(fileId=template_id, body={"appProperties": {"pathmark_grocery_template": "true"}}, fields="id").execute()
            except Exception:
                pass
        return True, template_id, template_url, "Created a separate Pathmark Grocery Template sheet."
    except Exception as exc:
        return False, "", "", f"Could not create the Pathmark Grocery Template: {exc}"


def _values_from_records(df: pd.DataFrame, headers: list[str]) -> list[list[str]]:
    values = [headers]
    if not df.empty:
        for _, row in df.iterrows():
            values.append([str(row.get(col, "") or "") for col in headers])
    return values


def create_grocery_template(sheet_id: str) -> tuple[bool, str, str]:
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session.", ""
    ok_file, template_id, template_url, file_msg = _ensure_grocery_template_file()
    if not ok_file:
        return False, file_msg, ""
    try:
        ensure_grocery_default_rows(sheet_id)
        readme = [["Pathmark Grocery Template"], ["Purpose", "Edit nutrition, inventory and recipes here, then import back into Pathmark."], ["Import modes", "Clean import replaces existing grocery rows. Merge import updates by item/recipe where possible and adds new rows."]]
        service.spreadsheets().values().update(spreadsheetId=template_id, range="README!A1:B3", valueInputOption="RAW", body={"values": readme}).execute()
        table_specs = {
            "Nutrition": ["item", "category_name", "portion_quantity", "portion_unit", "kcal_per_portion", "total_carbohydrate", "total_fat", "protein", "saturated_fat", "sodium", "dietary_fibre", "sugars", "notes", "status"],
            "Inventory": ["item", "category_name", "quantity", "unit", "expiry_date", "storage", "is_frozen", "requires_substitute", "suggested_substitute", "must_be_homegrown", "unavailable", "imported", "canned", "in_season", "limited_in_season", "months", "notes", "status"],
            "Recipes": ["recipe_name", "category_name", "course", "meal_categories", "cuisine_tags", "dish_style_tags", "dietary_tags", "servings", "time_mins", "source_title", "source_url", "page", "author", "protein", "vegetarian_vegan", "vegetarian", "vegan", "gluten_free", "allergens", "months", "seasonality_summary", "imported_notes", "frozen_or_canned_notes", "substitute_notes", "homegrown_notes", "unavailable_notes", "notes", "status"],
            "Recipe Ingredients": ["recipe_name", "quantity", "unit", "ingredient", "category_name", "is_fresh_produce", "lookup_seasonality", "substitute_required", "suggested_substitute", "purchased_quantity", "purchased_unit", "purchased_price", "notes", "status"],
        }
        source_map = {"Nutrition": "grocery_nutrition", "Inventory": "grocery_inventory", "Recipes": "recipes", "Recipe Ingredients": "recipe_ingredients"}
        for title, headers in table_specs.items():
            _ensure_template_sheet(service, template_id, title, headers)
            df = active_online_df(read_online_table(sheet_id, source_map[title]))
            values = _values_from_records(df, headers)
            end_col = sheet_col_letter(len(headers))
            service.spreadsheets().values().update(spreadsheetId=template_id, range=f"'{title}'!A1:{end_col}{len(values)}", valueInputOption="RAW", body={"values": values}).execute()
        st.session_state["grocery_template_id"] = template_id
        st.session_state["grocery_template_url"] = template_url
        return True, file_msg + " Populated it with your current grocery data.", template_url
    except Exception as exc:
        return False, f"Could not populate the Pathmark Grocery Template: {exc}", ""


def _read_template_tab(template_id: str, title: str, columns: list[str]) -> list[dict[str, Any]]:
    service = sheets_service()
    if service is None:
        return []
    values = service.spreadsheets().values().get(spreadsheetId=template_id, range=f"'{title}'!A1:{sheet_col_letter(len(columns))}").execute().get("values", [])
    if not values:
        return []
    headers = [str(h or "").strip() for h in values[0]]
    records = []
    for row in values[1:]:
        padded = list(row) + [""] * (len(headers) - len(row))
        record = {headers[i]: str(padded[i] or "").strip() for i in range(len(headers)) if headers[i]}
        if any(record.values()):
            records.append(record)
    return records


def import_grocery_template(sheet_id: str, mode: str = "merge") -> tuple[bool, str]:
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session."
    template_id = extract_google_sheet_id(str(st.session_state.get("grocery_template_id", "") or ""))
    if not template_id:
        found, found_id, _url = _find_existing_grocery_template()
        template_id = found_id if found else ""
    if not template_id:
        return False, "Create the Pathmark Grocery Template first, then edit it and import it back."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        backup_ok, backup_url, backup_msg = create_pathmark_sync_backup(sheet_id)
        if not backup_ok:
            return False, backup_msg
        nutrition_rows = _read_template_tab(template_id, "Nutrition", ONLINE_TABLES["grocery_nutrition"])
        inventory_rows = _read_template_tab(template_id, "Inventory", ONLINE_TABLES["grocery_inventory"])
        recipe_rows = _read_template_tab(template_id, "Recipes", ONLINE_TABLES["recipes"])
        ingredient_rows = _read_template_tab(template_id, "Recipe Ingredients", ONLINE_TABLES["recipe_ingredients"])
        if mode == "clean":
            for table in ["grocery_nutrition", "grocery_inventory", "recipes", "recipe_ingredients"]:
                columns = ONLINE_TABLES.get(table, [])
                service.spreadsheets().values().clear(spreadsheetId=sheet_id, range=f"{table}!A2:{sheet_col_letter(len(columns))}").execute()
            clear_online_cache(sheet_id)
        existing_n = active_online_df(read_online_table(sheet_id, "grocery_nutrition"))
        existing_i = active_online_df(read_online_table(sheet_id, "grocery_inventory"))
        existing_r = active_online_df(read_online_table(sheet_id, "recipes"))
        append = {"grocery_nutrition": [], "grocery_inventory": [], "recipes": [], "recipe_ingredients": []}
        updated = 0
        def upsert(table: str, id_col: str, key_col: str, record: dict[str, Any], existing: pd.DataFrame) -> None:
            nonlocal updated
            key = _normalise_food_key(record.get(key_col, "")) if key_col in {"item", "ingredient"} else str(record.get(key_col, "") or "").strip().lower()
            if not key:
                return
            match = pd.DataFrame()
            if not existing.empty and key_col in existing.columns:
                if key_col == "item":
                    match = existing[existing[key_col].fillna("").apply(_normalise_food_key).eq(key)]
                else:
                    match = existing[existing[key_col].fillna("").astype(str).str.strip().str.lower().eq(key)]
            if mode != "clean" and not match.empty:
                rid = str(match.iloc[0].get(id_col, "") or "")
                ok, _ = update_online_record(sheet_id, table, rid, {k: v for k, v in record.items() if k != id_col})
                updated += 1 if ok else 0
            else:
                append[table].append(record)
        for row in nutrition_rows:
            row = {**row, "nutrition_id": f"nutrition-{uuid.uuid4().hex[:12]}", "status": row.get("status") or "active", "source": "Pathmark Grocery Template import"}
            upsert("grocery_nutrition", "nutrition_id", "item", row, existing_n)
        for row in inventory_rows:
            row = {**row, "inventory_id": f"inventory-{uuid.uuid4().hex[:12]}", "status": row.get("status") or "active", "source": "Pathmark Grocery Template import"}
            upsert("grocery_inventory", "inventory_id", "item", row, existing_i)
        recipe_name_to_id = {}
        for row in recipe_rows:
            recipe_key = str(row.get("recipe_name", "") or "").strip().lower()
            if not recipe_key:
                continue
            if mode != "clean" and not existing_r.empty:
                match = existing_r[existing_r.get("recipe_name", pd.Series(dtype=str)).fillna("").astype(str).str.strip().str.lower().eq(recipe_key)]
            else:
                match = pd.DataFrame()
            if not match.empty:
                rid = str(match.iloc[0].get("recipe_id", "") or "")
                recipe_name_to_id[recipe_key] = rid
                ok, _ = update_online_record(sheet_id, "recipes", rid, {**row, "status": row.get("status") or "active", "source": "Pathmark Grocery Template import"})
                updated += 1 if ok else 0
            else:
                rid = f"recipe-{uuid.uuid4().hex[:12]}"
                recipe_name_to_id[recipe_key] = rid
                append["recipes"].append({**row, "recipe_id": rid, "status": row.get("status") or "active", "source": "Pathmark Grocery Template import"})
        current_recipes = active_online_df(read_online_table(sheet_id, "recipes"))
        for row in ingredient_rows:
            recipe_name = str(row.get("recipe_name", "") or "").strip()
            rid = recipe_name_to_id.get(recipe_name.lower(), "")
            if not rid and not current_recipes.empty:
                match = current_recipes[current_recipes["recipe_name"].fillna("").astype(str).str.strip().str.lower().eq(recipe_name.lower())]
                if not match.empty:
                    rid = str(match.iloc[0].get("recipe_id", "") or "")
            ingredient = str(row.get("ingredient", "") or "").strip()
            inv_id = _add_inventory_item_if_needed(sheet_id, ingredient, row.get("category_name", "Produce"), unit=row.get("unit", ""), notes="Added from recipe import.") if ingredient else ""
            season_status, _season_months, inv_sub = _ingredient_seasonality_status(sheet_id, ingredient) if str(row.get("lookup_seasonality", "") or "").strip().lower() in {"yes", "true", "1"} else ("", "", "")
            nrow = _find_nutrition_record(sheet_id, ingredient)
            kcal_estimate, nutrition_status = _estimate_ingredient_kcal(row, nrow)
            cost_estimate, cost_status = _estimate_ingredient_cost(row)
            append["recipe_ingredients"].append({
                "recipe_ingredient_id": f"recipe-ingredient-{uuid.uuid4().hex[:12]}",
                "recipe_id": rid,
                "recipe_name": recipe_name,
                "inventory_id": inv_id,
                "ingredient": ingredient,
                "quantity": str(row.get("quantity", "") or ""),
                "unit": str(row.get("unit", "") or ""),
                "category_name": str(row.get("category_name", "") or ""),
                "is_fresh_produce": str(row.get("is_fresh_produce", "") or ""),
                "lookup_seasonality": str(row.get("lookup_seasonality", "") or ""),
                "seasonality_status": season_status,
                "substitute_required": str(row.get("substitute_required", "") or ""),
                "suggested_substitute": str(row.get("suggested_substitute", "") or inv_sub),
                "purchased_quantity": str(row.get("purchased_quantity", "") or ""),
                "purchased_unit": str(row.get("purchased_unit", "") or ""),
                "purchased_price": str(row.get("purchased_price", "") or ""),
                "cost_estimate": f"{cost_estimate:.2f}" if cost_estimate is not None else "",
                "missing_price_data": "" if cost_estimate is not None else cost_status,
                "kcal_estimate": f"{kcal_estimate:.1f}" if kcal_estimate is not None else "",
                "nutrition_status": nutrition_status,
                "missing_nutrition_data": "" if kcal_estimate is not None else nutrition_status,
                "notes": str(row.get("notes", "") or ""),
                "status": str(row.get("status", "") or "active"),
                "source": "Pathmark Grocery Template import",
            })
        ok, msg = append_many_online_records(sheet_id, append)
        clear_online_cache(sheet_id)
        total_new = sum(len(v) for v in append.values())
        return ok, f"{backup_msg}\nImported grocery template: updated {updated} row(s) and added {total_new} row(s)."
    except Exception as exc:
        return False, f"Could not import the Pathmark Grocery Template: {exc}"



STARTER_PACK_TABLES = {
    "nutrition": "grocery_nutrition",
    "inventory": "grocery_inventory",
    "ingredients": "grocery_inventory",
    "ingredient": "grocery_inventory",
    "produce": "grocery_inventory",
    "pantry": "grocery_inventory",
    "recipes": "recipes",
    "recipe": "recipes",
    "recipe ingredients": "recipe_ingredients",
    "recipe_ingredients": "recipe_ingredients",
}
STARTER_PACK_SECTION_LABELS = {
    "nutrition": "Nutrition",
    "inventory": "Ingredients / pantry",
    "ingredients": "Ingredients / pantry",
    "recipes": "Recipes",
    "recipe ingredients": "Recipe ingredients",
}

STARTER_PACK_SECTION_PRESETS = {
    "recipes": ["recipes"],
    "seasonal-recipe-library": ["recipes"],
    "ingredients": ["inventory"],
    "pantry-starter-pack": ["inventory"],
    "nutrition": ["nutrition"],
    "nz-seasonal-produce": ["inventory"],
}

def starter_pack_section_choices(slug: str) -> list[str]:
    clean_slug = str(slug or "").strip().lower()
    preset = STARTER_PACK_SECTION_PRESETS.get(clean_slug)
    if preset:
        return list(preset)
    return ["inventory", "nutrition", "recipes", "recipe ingredients"]

def starter_pack_default_sections(slug: str, choices: list[str]) -> list[str]:
    clean_slug = str(slug or "").strip().lower()
    preset = STARTER_PACK_SECTION_PRESETS.get(clean_slug)
    if preset:
        return [section for section in preset if section in choices]
    defaults = [section for section in ["inventory", "nutrition"] if section in choices]
    return defaults or list(choices[:1])


def starter_pack_secret_config() -> dict[str, Any]:
    return _secret_section("starter_packs") or _secret_section("pathmark_starter_packs") or {}


def starter_pack_code_is_valid(slug: str, code: str) -> bool:
    """Validate a lightweight starter-pack access code.

    This is controlled distribution, not DRM. Imported starter-pack data becomes
    an editable copy in the user's own Pathmark Sync sheet.
    """
    text = str(code or "").strip()
    if not text:
        return False
    cfg = starter_pack_secret_config()
    slug_key = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")
    plain_values = [
        str(cfg.get(f"{slug_key}_code", "") or ""),
        str(cfg.get(f"{slug_key}_password", "") or ""),
        str(cfg.get("starter_library_code", "") or ""),
        str(cfg.get("access_code", "") or ""),
    ]
    for plain in plain_values:
        if plain and secrets.compare_digest(text, plain):
            return True
    supplied_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    hash_values = [
        str(cfg.get(f"{slug_key}_code_hash", "") or ""),
        str(cfg.get(f"{slug_key}_password_hash", "") or ""),
        str(cfg.get("starter_library_code_hash", "") or ""),
        str(cfg.get("access_code_hash", "") or ""),
    ]
    for hashed in hash_values:
        if hashed and secrets.compare_digest(supplied_hash, hashed.strip().lower()):
            return True
    return False


def _supabase_quote(value: str) -> str:
    return urllib.parse.quote(str(value or ""), safe="")


def list_starter_packs_from_supabase() -> list[dict[str, Any]]:
    if not supabase_available():
        return []
    query = "?select=slug,name,description,status,price_note,updated_at&status=eq.active&order=name.asc"
    ok, payload = supabase_request("GET", "pathmark_starter_packs", query=query)
    if ok and isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def read_starter_pack_rows_from_supabase(slug: str, sections: list[str] | None = None) -> tuple[bool, list[dict[str, Any]], str]:
    if not supabase_available():
        return False, [], "Supabase is not configured for starter packs yet."
    params = [
        "select=id,pack_slug,section,target_table,row_data,status,sort_order",
        f"pack_slug=eq.{_supabase_quote(slug)}",
        "status=eq.active",
        "order=sort_order.asc",
    ]
    if sections:
        clean = sorted({_normalise_food_key(section).replace(".", "_") for section in sections if str(section).strip()})
        if clean:
            params.append("section=in.(" + ",".join(_supabase_quote(x) for x in clean) + ")")
    ok, payload = supabase_request("GET", "pathmark_starter_pack_rows", query="?" + "&".join(params))
    if not ok:
        return False, [], safe_user_message(payload)
    if not isinstance(payload, list):
        return False, [], "Starter pack rows were not returned in the expected format."
    return True, [row for row in payload if isinstance(row, dict)], ""


def clear_online_tables(sheet_id: str, tables: list[str]) -> tuple[bool, str]:
    service = sheets_service()
    if service is None:
        return False, "Google Sheets access is not available for this session."
    try:
        ensure_pathmark_online_schema(service, sheet_id)
        for table in tables:
            columns = ONLINE_TABLES.get(table)
            if not columns:
                continue
            service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range=f"{table}!A2:{sheet_col_letter(len(columns))}10000",
                body={},
            ).execute()
        clear_online_cache(sheet_id)
        return True, "Cleared selected grocery tables."
    except Exception as exc:
        return False, f"Could not clear selected grocery tables: {exc}"


def _coerce_supabase_row_data(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _starter_pack_row_to_record(row: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    target = str(row.get("target_table", "") or "").strip()
    section = str(row.get("section", "") or "").strip().lower().replace("_", " ")
    table = target if target in ONLINE_TABLES else STARTER_PACK_TABLES.get(section, "")
    if table not in {"grocery_nutrition", "grocery_inventory", "recipes", "recipe_ingredients"}:
        return None
    data = _coerce_supabase_row_data(row.get("row_data"))
    if not data:
        return None
    columns = ONLINE_TABLES.get(table, [])
    record = {col: str(data.get(col, "") or "") for col in columns}
    id_col = ONLINE_ID_COLUMNS.get(table)
    if id_col and not record.get(id_col):
        prefix = {
            "grocery_nutrition": "nutrition",
            "grocery_inventory": "inventory",
            "recipes": "recipe",
            "recipe_ingredients": "recipe-ingredient",
        }.get(table, "starter")
        record[id_col] = f"{prefix}-{uuid.uuid4().hex[:12]}"
    if not record.get("status"):
        record["status"] = "active"
    record["source"] = f"Starter pack: {row.get('pack_slug', 'starter library')}"
    return table, record


def import_starter_pack_to_sync(sheet_id: str, slug: str, sections: list[str], mode: str) -> tuple[bool, str]:
    ok_rows, rows, msg = read_starter_pack_rows_from_supabase(slug, sections)
    if not ok_rows:
        return False, msg
    records_by_table: dict[str, list[dict[str, Any]]] = {"grocery_nutrition": [], "grocery_inventory": [], "recipes": [], "recipe_ingredients": []}
    for row in rows:
        converted = _starter_pack_row_to_record(row)
        if not converted:
            continue
        table, record = converted
        records_by_table.setdefault(table, []).append(record)
    records_by_table = {table: records for table, records in records_by_table.items() if records}
    if not records_by_table:
        return False, "No starter-pack rows matched the selected sections."
    backup_msg = ""
    ok_backup, backup_msg, _backup_url = create_pathmark_sync_backup(sheet_id)
    if mode == "clean":
        ok_clear, clear_msg = clear_online_tables(sheet_id, list(records_by_table.keys()))
        if not ok_clear:
            return False, clear_msg
    ok_append, append_msg = append_many_online_records(sheet_id, records_by_table)
    if not ok_append:
        return False, append_msg
    total = sum(len(v) for v in records_by_table.values())
    bits = [f"Imported {total} starter-pack row(s) into your Pathmark Sync sheet."]
    if ok_backup:
        bits.append("A backup was created first.")
    elif backup_msg:
        bits.append("Backup could not be created first: " + safe_user_message(backup_msg))
    return True, " ".join(bits)


def render_grocery_starter_packs_tab(sheet_id: str) -> None:
    st.subheader("Starter Packs")
    st.write("Import optional grocery libraries into your own Pathmark Sync sheet. Purchased or supporter packs are copied into your sheet and can then be edited or deleted.")
    st.info("The full curated starter libraries are not bundled in the public GitHub repository. Supported Supabase starter packs include Recipes, Ingredients and Nutrition; each can be imported separately with an access code from the creator.")
    packs = list_starter_packs_from_supabase()
    fallback_pack = {
        "slug": "nz-seasonal-produce",
        "name": "NZ Seasonal Produce",
        "description": "Curated New Zealand produce seasonality, availability and substitution data.",
        "price_note": "Access code required",
    }
    if not packs:
        packs = [fallback_pack]
    pack_labels = [str(p.get("name") or p.get("slug") or "Starter pack") for p in packs]
    selected_label = st.selectbox("Starter pack", pack_labels, key="starter_pack_select")
    pack = packs[pack_labels.index(selected_label)] if selected_label in pack_labels else packs[0]
    slug = str(pack.get("slug") or "nz-seasonal-produce")
    st.markdown(f"**{pack.get('name', slug)}**")
    st.caption(str(pack.get("description", "") or ""))
    if pack.get("price_note"):
        st.caption(str(pack.get("price_note")))
    c1, c2 = st.columns([2, 1])
    with c1:
        access_code = st.text_input("Access code", type="password", key="starter_pack_access_code")
    with c2:
        import_mode = st.radio("Import mode", ["Merge/update", "Clean import"], index=0, horizontal=False, key="starter_pack_mode")
    section_choices = starter_pack_section_choices(slug)
    selected_sections = st.multiselect(
        "Sections to import",
        section_choices,
        default=starter_pack_default_sections(slug, section_choices),
        format_func=lambda x: STARTER_PACK_SECTION_LABELS.get(x, x.title()),
        key=f"starter_pack_sections_{slug}",
    )
    with st.expander("What happens when I import a pack?", expanded=False):
        st.markdown("""
        - Pathmark checks the access code before importing.
        - Starter-pack rows are copied from Supabase into your own Pathmark Sync sheet.
        - Merge/update adds the pack alongside existing data.
        - Clean import clears the selected grocery tables first.
        - Pathmark attempts to create a backup before importing.
        - Imported data is no longer locked; it becomes your editable copy.
        """)
    can_import = bool(access_code and selected_sections)
    if st.button("Import starter pack", use_container_width=True, disabled=not can_import):
        if not starter_pack_code_is_valid(slug, access_code):
            st.warning("That access code was not recognised. Check the code or contact the creator for access.")
        else:
            ok, msg = import_starter_pack_to_sync(sheet_id, slug, selected_sections, "clean" if import_mode.startswith("Clean") else "merge")
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.warning(safe_user_message(msg))

def render_grocery_template_tab(sheet_id: str) -> None:
    st.subheader("Templates and bulk import")
    st.write("Create a separate Google Sheet for editing nutrition, inventory and recipes in bulk, then import it back into Pathmark.")
    st.caption("Clean import replaces existing grocery nutrition, inventory and recipe rows. Merge import updates matching nutrition/inventory/recipes and adds new rows. Pathmark creates a backup before importing.")
    if st.button("Create / refresh Pathmark Grocery Template", use_container_width=True):
        ok, msg, url = create_grocery_template(sheet_id)
        if ok:
            st.success(msg)
            st.session_state["grocery_template_url"] = url
        else:
            st.warning(safe_user_message(msg))
    template_id = str(st.session_state.get("grocery_template_id", "") or "")
    template_url = str(st.session_state.get("grocery_template_url", "") or "")
    if not template_id:
        found, found_id, found_url = _find_existing_grocery_template()
        if found:
            template_id = found_id
            template_url = found_url
            st.session_state["grocery_template_id"] = found_id
            st.session_state["grocery_template_url"] = found_url
    if template_id:
        st.link_button("Open Pathmark Grocery Template in Google Sheets", template_url or f"https://docs.google.com/spreadsheets/d/{template_id}/edit", use_container_width=True)
    mode = st.radio("Import mode", ["Merge/update existing grocery data", "Clean import: replace current grocery data"], horizontal=False)
    confirm = st.checkbox("I understand Pathmark will create a backup before importing.")
    if st.button("Import from Pathmark Grocery Template", use_container_width=True, disabled=not confirm):
        ok, msg = import_grocery_template(sheet_id, "clean" if mode.startswith("Clean") else "merge")
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.warning(safe_user_message(msg))


def export_recipe_to_project(sheet_id: str, recipe_row: dict[str, Any]) -> tuple[bool, str]:
    areas = active_online_df(read_online_table(sheet_id, "areas"))
    area_options = [str(x).strip() for x in areas.get("area_name", pd.Series(dtype=str)).tolist() if str(x).strip()] or ["Body And Stability", "Home, Relationships, and Admin", "Making And Craft", "Expression And Culture", "Skills And Tools", "Rest And Play"]
    with st.form(f"export_recipe_project_{recipe_row.get('recipe_id', '')}"):
        area = st.selectbox("Area", area_options, key=f"recipe_export_area_{recipe_row.get('recipe_id', '')}")
        c1, c2, c3 = st.columns(3)
        with c1:
            cook_date = st.date_input("Cooking date", value=date.today(), key=f"recipe_export_date_{recipe_row.get('recipe_id', '')}")
        with c2:
            start_t = st.time_input("Start time", value=time(17, 30), key=f"recipe_export_start_{recipe_row.get('recipe_id', '')}")
        with c3:
            minutes = st.number_input("Duration minutes", min_value=15, max_value=480, value=60, step=15, key=f"recipe_export_duration_{recipe_row.get('recipe_id', '')}")
        submitted = st.form_submit_button("Create project activity for this recipe", use_container_width=True)
    if not submitted:
        return False, ""
    area_row = areas[areas.get("area_name", pd.Series(dtype=str)).fillna("").eq(area)] if not areas.empty else pd.DataFrame()
    area_id = str(area_row.iloc[0].get("area_id", "") or "") if not area_row.empty else ""
    title = f"Cook {recipe_row.get('recipe_name', 'recipe')}"
    goal_id = f"goal-{uuid.uuid4().hex[:12]}"
    action_id = f"action-{uuid.uuid4().hex[:12]}"
    start_dt = datetime.combine(cook_date, start_t)
    end_dt = start_dt + timedelta(minutes=int(minutes or 60))
    records = {
        "goals": [{
            "goal_id": goal_id,
            "area_id": area_id,
            "area_name": area,
            "title": title,
            "description": "Recipe exported from Meal Plan.",
            "specific_area": area,
            "status": "active",
            "target_date": str(cook_date),
            "purpose": "Cook a planned recipe.",
            "desired_outcome": title,
            "closure_criteria": "Recipe cooked.",
            "notes": str(recipe_row.get("notes", "") or ""),
            "source": "Meal Plan recipe export",
        }],
        "actions": [{
            "action_id": action_id,
            "goal_id": goal_id,
            "routine_id": "",
            "area_id": area_id,
            "area_name": area,
            "title": title,
            "description": "Cooking activity created from recipe.",
            "status": "active",
            "priority": "Normal",
            "specific_area": area,
            "due_date": str(cook_date),
            "scheduled_date": str(cook_date),
            "estimated_minutes": str(int(minutes or 60)),
            "calendar_block": "Yes",
            "include_tasklist": "Yes",
            "calendar_start_time": start_dt.strftime("%H:%M"),
            "calendar_end_time": end_dt.strftime("%H:%M"),
            "calendar_end_date": str(end_dt.date()),
            "notes": f"Recipe: {recipe_row.get('recipe_name', '')}",
            "source": "Meal Plan recipe export",
        }],
    }
    ok, msg = append_many_online_records(sheet_id, records)
    if ok:
        update_online_record(sheet_id, "recipes", str(recipe_row.get("recipe_id", "")), {"exported_goal_id": goal_id, "exported_action_id": action_id})
    return ok, msg

def render_grocery_categories_tab(sheet_id: str) -> None:
    st.subheader("Grocery categories")
    st.caption("These work like Areas for shopping lists. Items can be grouped under supermarket-style sections.")
    categories = active_online_df(read_online_table(sheet_id, "grocery_categories"))
    if not categories.empty:
        display_cols = [c for c in ["sort_order", "category_name", "description", "colour", "status"] if c in categories.columns]
        st.dataframe(categories[display_cols], use_container_width=True, hide_index=True)
    with st.form("add_grocery_category_form"):
        st.markdown("#### Add category")
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            name = st.text_input("Category name")
        with c2:
            description = st.text_input("Description", value="Grocery shopping-list category.")
        with c3:
            colour = st.color_picker("Colour", "#334E9E")
        submitted = st.form_submit_button("Add grocery category", use_container_width=True)
    if submitted:
        if not name.strip():
            st.warning("Enter a category name.")
        else:
            record = {
                "category_id": f"grocery-category-{uuid.uuid4().hex[:12]}",
                "category_name": name.strip(),
                "description": description.strip(),
                "colour": colour,
                "sort_order": str(len(categories) + 1 if not categories.empty else 1),
                "status": "active",
                "source": "Meal Plan",
            }
            ok, msg = append_online_record(sheet_id, "grocery_categories", record)
            if ok:
                st.success("Category added.")
                st.rerun()
            else:
                st.warning(msg)

    st.markdown("#### Recipe classifications")
    st.caption("Recipe categories are tag-style helpers for searching meal plans, recipes and future starter packs.")
    recipe_tables = [
        ("Courses", "recipe_courses", "course_id", "course_name", "course"),
        ("Meal categories", "recipe_meal_categories", "meal_category_id", "meal_category_name", "meal_category"),
        ("Cuisine / tradition tags", "recipe_cuisine_tags", "cuisine_tag_id", "cuisine_tag_name", "cuisine_tag"),
        ("Technique / dish-style tags", "recipe_dish_style_tags", "dish_style_tag_id", "dish_style_tag_name", "dish_style_tag"),
        ("Dietary tags", "recipe_dietary_tags", "dietary_tag_id", "dietary_tag_name", "dietary_tag"),
    ]
    for label, table, id_col, name_col, prefix in recipe_tables:
        with st.expander(label, expanded=False):
            df = active_online_df(read_online_table(sheet_id, table))
            show_cols = [c for c in ["sort_order", name_col, "description", "status"] if c in df.columns]
            st.dataframe(df[show_cols] if not df.empty else pd.DataFrame(columns=show_cols), use_container_width=True, hide_index=True, height=180)
            with st.form(f"add_{table}_form"):
                c1, c2 = st.columns([2, 3])
                with c1:
                    new_name = st.text_input(f"Add {label[:-1].lower() if label.endswith('s') else label.lower()}", key=f"{table}_name")
                with c2:
                    new_desc = st.text_input("Description", value="Meal Plan recipe classification.", key=f"{table}_desc")
                add_tag = st.form_submit_button(f"Add {label[:-1] if label.endswith('s') else label}", use_container_width=True)
            if add_tag:
                if not new_name.strip():
                    st.warning("Enter a name.")
                else:
                    record = {
                        id_col: f"{prefix}-{uuid.uuid4().hex[:12]}",
                        name_col: new_name.strip(),
                        "description": new_desc.strip(),
                        "sort_order": str(len(df) + 1 if not df.empty else 1),
                        "status": "active",
                        "source": "Meal Plan",
                    }
                    ok, msg = append_online_record(sheet_id, table, record)
                    if ok:
                        st.success("Recipe classification added.")
                        st.rerun()
                    else:
                        st.warning(msg)


def render_grocery_inventory_tab(sheet_id: str) -> None:
    st.subheader("Grocery inventory")
    st.caption("Track what you have, expiry dates, storage, substitutions, seasonality and availability.")
    categories = grocery_category_options(sheet_id)
    inventory = active_online_df(read_online_table(sheet_id, "grocery_inventory"))
    search = st.text_input("Search inventory", placeholder="e.g., mustard, tomato, rice")
    category_filter = st.selectbox("Category filter", ["All categories"] + categories, key="grocery_inventory_category_filter")
    view = inventory.copy()
    if not view.empty and search.strip():
        mask = view.apply(lambda row: search.strip().lower() in " ".join(str(v).lower() for v in row.values), axis=1)
        view = view[mask]
    if not view.empty and category_filter != "All categories":
        view = view[view["category_name"].fillna("").eq(category_filter)]
    display_cols = [c for c in ["category_name", "item", "quantity", "unit", "expiry_date", "storage", "is_frozen", "requires_substitute", "suggested_substitute", "must_be_homegrown", "unavailable", "imported", "canned", "in_season", "limited_in_season", "months", "notes"] if c in view.columns]
    st.dataframe(view[display_cols] if not view.empty else pd.DataFrame(columns=display_cols), use_container_width=True, hide_index=True, height=360)
    with st.form("add_grocery_inventory_form"):
        st.markdown("#### Add or update inventory item")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            item = st.text_input("Ingredient / item")
            category = st.selectbox("Category", categories, key="add_inventory_category")
            storage = st.selectbox("Storage", ["", "Pantry", "Fridge", "Freezer", "Fresh", "Other"])
        with c2:
            quantity = st.text_input("Quantity", placeholder="e.g., 1")
            unit = st.text_input("Unit", placeholder="e.g., kg, tin, bunch")
            expiry_date = st.date_input("Expiry date", value=None)
        with c3:
            is_frozen = st.checkbox("Frozen")
            requires_substitute = st.checkbox("Requires substitute")
            substitute = st.text_input("Suggested substitute")
        c4, c5, c6, c7, c8 = st.columns(5)
        with c4:
            homegrown = st.checkbox("Must be homegrown")
        with c5:
            unavailable = st.checkbox("Unavailable")
        with c6:
            imported = st.checkbox("Imported")
        with c7:
            canned = st.checkbox("Canned")
        with c8:
            limited = st.checkbox("Limited in season")
        months = st.multiselect("Months in season", GROCERY_MONTHS, default=[])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save inventory item", use_container_width=True)
    if submitted:
        if not item.strip():
            st.warning("Enter an item name.")
        else:
            existing = _find_grocery_inventory_record(sheet_id, item)
            record = {
                "category_name": category,
                "item": item.strip(),
                "quantity": quantity.strip(),
                "unit": unit.strip(),
                "expiry_date": str(expiry_date or ""),
                "storage": storage,
                "is_frozen": _grocery_bool_text(is_frozen),
                "requires_substitute": _grocery_bool_text(requires_substitute),
                "suggested_substitute": substitute.strip(),
                "must_be_homegrown": _grocery_bool_text(homegrown),
                "unavailable": _grocery_bool_text(unavailable),
                "imported": _grocery_bool_text(imported),
                "canned": _grocery_bool_text(canned),
                "in_season": _grocery_bool_text(bool(months) and not unavailable),
                "limited_in_season": _grocery_bool_text(limited),
                "months": ", ".join(months),
                "notes": notes.strip(),
                "status": "active",
                "source": "Meal Plan",
            }
            if existing:
                ok, msg = update_online_record(sheet_id, "grocery_inventory", str(existing.get("inventory_id", "")), record)
            else:
                record["inventory_id"] = f"inventory-{uuid.uuid4().hex[:12]}"
                ok, msg = append_online_record(sheet_id, "grocery_inventory", record)
            if ok:
                st.success("Inventory item saved.")
                st.rerun()
            else:
                st.warning(msg)


def _recipe_filter_mask(recipes: pd.DataFrame, *, month: str, course: str, meal_category: str, cuisine: str, dish_style: str, dietary: str, produce: str, vegetarian_only: bool, vegan_only: bool, gluten_free_only: bool, in_season_only: bool, avoid_unavailable: bool) -> pd.Series:
    if recipes.empty:
        return pd.Series(dtype=bool)
    mask = pd.Series([True] * len(recipes), index=recipes.index)
    if month and month != "Any month":
        mask &= recipes.apply(lambda r: month.lower() in _split_tag_text(r.get("months", "")) or month.lower() in _split_tag_text(r.get("seasonality_summary", "")), axis=1)
    if course and course != "Any course":
        mask &= recipes["course"].fillna("").astype(str).str.lower().str.contains(re.escape(course.lower()), na=False)
    if meal_category and meal_category != "Any meal category":
        mask &= recipes["meal_categories"].fillna("").astype(str).str.lower().str.contains(re.escape(meal_category.lower()), na=False)
    if cuisine and cuisine != "Any cuisine / style":
        mask &= recipes["cuisine_tags"].fillna("").astype(str).str.lower().str.contains(re.escape(cuisine.lower()), na=False)
    if dish_style and dish_style != "Any dish style":
        mask &= recipes["dish_style_tags"].fillna("").astype(str).str.lower().str.contains(re.escape(dish_style.lower()), na=False)
    if dietary and dietary != "Any dietary tag":
        mask &= recipes["dietary_tags"].fillna("").astype(str).str.lower().str.contains(re.escape(dietary.lower()), na=False)
    if vegetarian_only:
        mask &= recipes.apply(lambda r: "vegetarian" in str(r.get("vegetarian_vegan", "") or "").lower() or str(r.get("vegetarian", "") or "").strip().lower() in {"yes", "true", "1"}, axis=1)
    if vegan_only:
        mask &= recipes.apply(lambda r: "vegan" in str(r.get("vegetarian_vegan", "") or "").lower() or str(r.get("vegan", "") or "").strip().lower() in {"yes", "true", "1"}, axis=1)
    if gluten_free_only:
        mask &= recipes.apply(lambda r: "gluten" in str(r.get("gluten_free", "") or "").lower() or "gluten free" in str(r.get("dietary_tags", "") or "").lower(), axis=1)
    if avoid_unavailable:
        mask &= ~recipes.apply(lambda r: "unavailable" in (str(r.get("unavailable_notes", "") or "") + " " + str(r.get("seasonality_summary", "") or "")).lower(), axis=1)
    if in_season_only and month and month != "Any month":
        mask &= recipes.apply(lambda r: month.lower() in str(r.get("months", "") or "").lower(), axis=1)
    if produce.strip():
        ptxt = produce.strip().lower()
        mask &= recipes.apply(lambda r: ptxt in " ".join(str(r.get(c, "") or "") for c in ["recipe_name", "notes", "seasonality_summary", "substitute_notes", "imported_notes", "unavailable_notes"]).lower(), axis=1)
    return mask


def render_recipes_tab(sheet_id: str) -> None:
    st.subheader("Recipe Library")
    st.caption("Search, classify and build recipes with seasonality, nutrition and approximate cost estimates. Recipe starter packs can be imported from Supabase without storing curated recipe data in GitHub.")
    categories = grocery_category_options(sheet_id)
    course_options = recipe_course_options(sheet_id)
    meal_category_options = recipe_meal_category_options(sheet_id)
    cuisine_options = recipe_cuisine_tag_options(sheet_id)
    dish_style_options = recipe_dish_style_options(sheet_id)
    dietary_options = recipe_dietary_tag_options(sheet_id)
    recipes = active_online_df(read_online_table(sheet_id, "recipes"))
    ingredients = active_online_df(read_online_table(sheet_id, "recipe_ingredients"))

    with st.expander("Find recipes", expanded=not recipes.empty):
        c1, c2, c3 = st.columns(3)
        with c1:
            filter_month = st.selectbox("Month", ["Any month"] + GROCERY_MONTHS, key="recipe_filter_month")
            filter_course = st.selectbox("Course", ["Any course"] + course_options, key="recipe_filter_course")
            filter_meal_category = st.selectbox("Meal category", ["Any meal category"] + meal_category_options, key="recipe_filter_meal_category")
        with c2:
            filter_cuisine = st.selectbox("Cuisine / style", ["Any cuisine / style"] + cuisine_options, key="recipe_filter_cuisine")
            filter_dish_style = st.selectbox("Dish style", ["Any dish style"] + dish_style_options, key="recipe_filter_dish_style")
            filter_dietary = st.selectbox("Dietary tag", ["Any dietary tag"] + dietary_options, key="recipe_filter_dietary")
        with c3:
            filter_produce = st.text_input("Ingredient or produce", placeholder="e.g., Eggplant, Lime, Coriander")
            vegetarian_only = st.checkbox("Vegetarian", value=False, key="recipe_filter_vegetarian")
            vegan_only = st.checkbox("Vegan", value=False, key="recipe_filter_vegan")
            gluten_free_only = st.checkbox("Gluten free", value=False, key="recipe_filter_gf")
            in_season_only = st.checkbox("Only recipes tagged for selected month", value=False, key="recipe_filter_season")
            avoid_unavailable = st.checkbox("Avoid unavailable produce", value=False, key="recipe_filter_unavailable")
    filtered = recipes.copy()
    if not recipes.empty:
        mask = _recipe_filter_mask(recipes, month=filter_month, course=filter_course, meal_category=filter_meal_category, cuisine=filter_cuisine, dish_style=filter_dish_style, dietary=filter_dietary, produce=filter_produce, vegetarian_only=vegetarian_only, vegan_only=vegan_only, gluten_free_only=gluten_free_only, in_season_only=in_season_only, avoid_unavailable=avoid_unavailable)
        filtered = recipes[mask].copy()
    if filtered.empty:
        st.info("No recipes match those filters yet. Add a recipe below or import a recipe starter pack.")
    else:
        show_cols = [c for c in ["recipe_name", "course", "meal_categories", "cuisine_tags", "dish_style_tags", "dietary_tags", "servings", "time_mins", "months", "source_title", "page"] if c in filtered.columns]
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True, height=320)

    with st.form("add_recipe_form"):
        st.markdown("#### Add or update recipe")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            recipe_name = st.text_input("Recipe name")
            recipe_category = st.selectbox("Primary grocery/category", categories, key="recipe_category")
            course = st.selectbox("Course", course_options, key="recipe_course")
        with c2:
            servings = st.text_input("Servings", placeholder="4-6")
            time_mins = st.number_input("Time (mins)", min_value=0, max_value=1440, value=0, step=5)
            page = st.text_input("Page")
        with c3:
            source_title = st.text_input("Source / book")
            source_url = st.text_input("Source URL")
            author = st.text_input("Author")
        meal_tags = st.multiselect("Meal categories", meal_category_options, key="recipe_meal_tags")
        cuisine_tags = st.multiselect("Cuisine / tradition tags", cuisine_options, key="recipe_cuisine_tags")
        dish_tags = st.multiselect("Technique / dish-style tags", dish_style_options, key="recipe_dish_tags")
        dietary_tags = st.multiselect("Dietary tags", dietary_options, key="recipe_dietary_tags")
        months = st.multiselect("Best months", GROCERY_MONTHS, key="recipe_months")
        c4, c5, c6 = st.columns(3)
        with c4:
            vegetarian_vegan = st.text_input("Vegetarian / vegan wording", placeholder="Vegetarian, Vegan")
            gluten_free = st.selectbox("Gluten free?", ["", "Yes", "No"], key="recipe_gluten_free")
        with c5:
            protein = st.text_input("Protein / notable allergens", placeholder="egg, tofu, sesame")
            allergens = st.text_input("Allergens")
        with c6:
            imported_notes = st.text_input("Imported notes")
            frozen_notes = st.text_input("Frozen or canned notes")
        substitute_notes = st.text_input("Substitute notes")
        homegrown_notes = st.text_input("Homegrown notes")
        unavailable_notes = st.text_input("Unavailable notes")
        recipe_notes = st.text_area("Recipe notes")
        submitted = st.form_submit_button("Save recipe", use_container_width=True)
    if submitted:
        if not recipe_name.strip():
            st.warning("Enter a recipe name.")
        else:
            existing = pd.DataFrame()
            if not recipes.empty:
                existing = recipes[recipes["recipe_name"].fillna("").astype(str).str.strip().str.lower().eq(recipe_name.strip().lower())]
            record = {
                "recipe_name": recipe_name.strip(),
                "category_name": recipe_category,
                "course": course,
                "meal_categories": _join_tags(meal_tags),
                "cuisine_tags": _join_tags(cuisine_tags),
                "dish_style_tags": _join_tags(dish_tags),
                "dietary_tags": _join_tags(dietary_tags),
                "servings": servings.strip(),
                "time_mins": str(time_mins or ""),
                "source_url": source_url.strip(),
                "source_title": source_title.strip(),
                "page": page.strip(),
                "author": author.strip(),
                "protein": protein.strip(),
                "vegetarian_vegan": vegetarian_vegan.strip(),
                "vegetarian": "Yes" if "vegetarian" in (vegetarian_vegan + " " + _join_tags(dietary_tags)).lower() else "",
                "vegan": "Yes" if "vegan" in (vegetarian_vegan + " " + _join_tags(dietary_tags)).lower() else "",
                "gluten_free": gluten_free,
                "allergens": allergens.strip(),
                "months": _join_tags(months),
                "seasonality_summary": _join_tags(months),
                "imported_notes": imported_notes.strip(),
                "frozen_or_canned_notes": frozen_notes.strip(),
                "substitute_notes": substitute_notes.strip(),
                "homegrown_notes": homegrown_notes.strip(),
                "unavailable_notes": unavailable_notes.strip(),
                "notes": recipe_notes.strip(),
                "status": "active",
                "source": "Meal Plan",
            }
            if not existing.empty:
                rid = str(existing.iloc[0].get("recipe_id", "") or "")
                ok, msg = update_online_record(sheet_id, "recipes", rid, record)
            else:
                record["recipe_id"] = f"recipe-{uuid.uuid4().hex[:12]}"
                ok, msg = append_online_record(sheet_id, "recipes", record)
            if ok:
                st.success("Recipe saved.")
                st.rerun()
            else:
                st.warning(msg)

    recipes = active_online_df(read_online_table(sheet_id, "recipes"))
    ingredients = active_online_df(read_online_table(sheet_id, "recipe_ingredients"))
    if recipes.empty:
        return
    recipe_names = [str(x).strip() for x in recipes["recipe_name"].tolist() if str(x).strip()]
    selected_recipe = st.selectbox("Selected recipe", recipe_names, key="selected_recipe_for_ingredients")
    recipe_row = recipes[recipes["recipe_name"].fillna("").eq(selected_recipe)].iloc[0].to_dict()
    recipe_id = str(recipe_row.get("recipe_id", "") or "")
    servings_val = _amount_from_text(recipe_row.get("servings", "")) or 1.0
    st.markdown("#### Recipe ingredients, nutrition and cost")
    detail_df, total_kcal, total_cost, missing = recipe_nutrition_summary(sheet_id, recipe_id, servings_val)
    if detail_df.empty:
        st.info("This recipe has no ingredients yet.")
    else:
        st.dataframe(detail_df, use_container_width=True, hide_index=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Estimated kcal / recipe", f"{total_kcal:.0f}")
        c2.metric("Estimated kcal / serving", f"{(total_kcal / max(servings_val, 1)):.0f}")
        c3.metric("Estimated cost / recipe", f"${total_cost:.2f}")
        c4.metric("Estimated cost / serving", f"${(total_cost / max(servings_val, 1)):.2f}")
        if missing:
            with st.expander("Missing nutrition, price or conversion data", expanded=True):
                for item in missing:
                    st.write(f"- {item}")
    inv_options = grocery_inventory_options(sheet_id)
    with st.form("add_recipe_ingredient_form"):
        st.markdown("#### Add ingredient")
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            quantity = st.text_input("Quantity", placeholder="125")
        with c2:
            unit = st.text_input("Unit", placeholder="g")
        with c3:
            selection_options = ["+ Add new ingredient"] + inv_options
            selected_ingredient = st.selectbox("Ingredient", selection_options, key="recipe_ingredient_choice")
            new_ingredient = ""
            if selected_ingredient == "+ Add new ingredient":
                new_ingredient = st.text_input("New ingredient")
        ing_category = st.selectbox("Ingredient category", categories, key="recipe_ingredient_category")
        c4, c5, c6 = st.columns(3)
        with c4:
            is_fresh = st.checkbox("Fresh produce", value=ing_category in {"Produce", "Fruits & Vegetables"})
            lookup_season = st.checkbox("Look up seasonality", value=True)
        with c5:
            substitute_required = st.checkbox("Substitute required", value=False)
            suggested_substitute = st.text_input("Suggested substitute")
        with c6:
            purchased_quantity = st.text_input("Purchased quantity", placeholder="500")
            purchased_unit = st.text_input("Purchased unit", placeholder="g")
            purchased_price = st.text_input("Purchased price", placeholder="4.00")
        ing_notes = st.text_input("Notes")
        save_ing = st.form_submit_button("Add ingredient to recipe", use_container_width=True)
    if save_ing:
        ingredient_name = new_ingredient.strip() if selected_ingredient == "+ Add new ingredient" else selected_ingredient
        if not ingredient_name:
            st.warning("Choose or enter an ingredient.")
        else:
            inv_id = _add_inventory_item_if_needed(sheet_id, ingredient_name, ing_category, unit=unit, notes="Added from recipe.")
            nrow = _find_nutrition_record(sheet_id, ingredient_name)
            kcal_estimate, nutrition_status = _estimate_ingredient_kcal({"quantity": quantity, "unit": unit}, nrow)
            season_status, season_months, inv_sub = _ingredient_seasonality_status(sheet_id, ingredient_name) if lookup_season else ("", "", "")
            cost_estimate, cost_status = _estimate_ingredient_cost({"quantity": quantity, "unit": unit, "purchased_quantity": purchased_quantity, "purchased_unit": purchased_unit, "purchased_price": purchased_price})
            record = {
                "recipe_ingredient_id": f"recipe-ingredient-{uuid.uuid4().hex[:12]}",
                "recipe_id": recipe_id,
                "recipe_name": selected_recipe,
                "inventory_id": inv_id,
                "ingredient": ingredient_name,
                "quantity": quantity.strip(),
                "unit": unit.strip(),
                "category_name": ing_category,
                "is_fresh_produce": _grocery_bool_text(is_fresh),
                "lookup_seasonality": _grocery_bool_text(lookup_season),
                "seasonality_status": season_status,
                "substitute_required": _grocery_bool_text(substitute_required or "Requires substitute" in season_status),
                "suggested_substitute": suggested_substitute.strip() or inv_sub,
                "purchased_quantity": purchased_quantity.strip(),
                "purchased_unit": purchased_unit.strip(),
                "purchased_price": purchased_price.strip(),
                "cost_estimate": f"{cost_estimate:.2f}" if cost_estimate is not None else "",
                "missing_price_data": "" if cost_estimate is not None else cost_status,
                "kcal_estimate": f"{kcal_estimate:.1f}" if kcal_estimate is not None else "",
                "nutrition_status": nutrition_status,
                "missing_nutrition_data": "" if kcal_estimate is not None else nutrition_status,
                "notes": ing_notes.strip(),
                "status": "active",
                "source": "Meal Plan",
            }
            ok, msg = append_online_record(sheet_id, "recipe_ingredients", record)
            if ok:
                st.success("Ingredient added.")
                st.rerun()
            else:
                st.warning(msg)
    with st.expander("Export this recipe to Planner", expanded=False):
        st.write("Create a one-off project activity for cooking this recipe. The activity can then sync to Google Tasks and Calendar like other project steps.")
        ok, msg = export_recipe_to_project(sheet_id, recipe_row)
        if msg:
            if ok:
                st.success("Recipe exported to Planner.")
            else:
                st.warning(safe_user_message(msg))


def render_shopping_lists_tab(sheet_id: str) -> None:
    st.subheader("Shopping lists")
    st.caption("Create shopping lists using quantity, unit and ingredient, grouped by grocery category.")
    categories = grocery_category_options(sheet_id)
    lists = active_online_df(read_online_table(sheet_id, "shopping_lists"))
    items = active_online_df(read_online_table(sheet_id, "shopping_items"))
    with st.form("create_shopping_list_form"):
        c1, c2 = st.columns([2, 1])
        with c1:
            list_name = st.text_input("List name", value=f"Shopping list — {date.today().strftime('%d/%m/%Y')}")
        with c2:
            planned_date = st.date_input("Planned date", value=date.today())
        notes = st.text_input("Notes")
        create_list = st.form_submit_button("Create shopping list", use_container_width=True)
    if create_list:
        if not list_name.strip():
            st.warning("Enter a list name.")
        else:
            record = {
                "shopping_list_id": f"shopping-list-{uuid.uuid4().hex[:12]}",
                "list_name": list_name.strip(),
                "planned_date": str(planned_date),
                "status": "active",
                "notes": notes.strip(),
                "source": "Meal Plan",
            }
            ok, msg = append_online_record(sheet_id, "shopping_lists", record)
            if ok:
                st.success("Shopping list created.")
                st.rerun()
            else:
                st.warning(msg)
    if lists.empty:
        st.info("Create a shopping list to begin adding items.")
        return
    list_names = [str(x).strip() for x in lists["list_name"].tolist() if str(x).strip()]
    selected_list = st.selectbox("Active shopping list", list_names, key="active_shopping_list")
    list_row = lists[lists["list_name"].fillna("").eq(selected_list)].iloc[0].to_dict()
    list_id = str(list_row.get("shopping_list_id", ""))
    this_items = _shopping_items_for_list(sheet_id, list_id)
    if not this_items.empty:
        grouped_cols = [c for c in ["checked", "category_name", "quantity", "unit", "ingredient", "recipe_name", "notes"] if c in this_items.columns]
        st.dataframe(this_items.sort_values(["category_name", "ingredient"])[grouped_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No items in this list yet.")
    inv_options = grocery_inventory_options(sheet_id)
    with st.form("add_shopping_item_form"):
        st.markdown("#### Add item")
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            quantity = st.text_input("Quantity", placeholder="1")
        with c2:
            unit = st.text_input("Unit", placeholder="Tbsp")
        with c3:
            selection_options = ["+ Add new ingredient"] + inv_options
            ingredient_choice = st.selectbox("Ingredient", selection_options, key="shopping_item_ingredient_choice")
            new_item = ""
            if ingredient_choice == "+ Add new ingredient":
                new_item = st.text_input("New ingredient")
        category = st.selectbox("Category", categories, key="shopping_item_category")
        notes = st.text_input("Notes")
        add_to_inventory = st.checkbox("Add new ingredient to inventory", value=True)
        save_item = st.form_submit_button("Add item to shopping list", use_container_width=True)
    if save_item:
        ingredient = new_item.strip() if ingredient_choice == "+ Add new ingredient" else ingredient_choice
        if not ingredient:
            st.warning("Choose or enter an ingredient.")
        else:
            inv_id = ""
            if add_to_inventory or ingredient_choice != "+ Add new ingredient":
                inv_id = _add_inventory_item_if_needed(sheet_id, ingredient, category, unit=unit, notes="Added from shopping list.")
            record = {
                "shopping_item_id": f"shopping-item-{uuid.uuid4().hex[:12]}",
                "shopping_list_id": list_id,
                "shopping_list_name": selected_list,
                "category_name": category,
                "quantity": quantity.strip(),
                "unit": unit.strip(),
                "ingredient": ingredient,
                "inventory_id": inv_id,
                "recipe_id": "",
                "recipe_name": "",
                "checked": "",
                "notes": notes.strip(),
                "status": "active",
                "source": "Meal Plan",
            }
            ok, msg = append_online_record(sheet_id, "shopping_items", record)
            if ok:
                st.success("Item added.")
                st.rerun()
            else:
                st.warning(msg)
    recipes = active_online_df(read_online_table(sheet_id, "recipes"))
    recipe_ingredients = active_online_df(read_online_table(sheet_id, "recipe_ingredients"))
    if not recipes.empty:
        with st.expander("Add recipe ingredients to this shopping list", expanded=False):
            recipe_names = [str(x).strip() for x in recipes["recipe_name"].tolist() if str(x).strip()]
            recipe_name = st.selectbox("Recipe", recipe_names, key="shopping_recipe_add_select")
            if st.button("Add recipe to shopping list", use_container_width=True):
                recipe_row = recipes[recipes["recipe_name"].fillna("").eq(recipe_name)].iloc[0].to_dict()
                recipe_id = str(recipe_row.get("recipe_id", ""))
                rows = recipe_ingredients[recipe_ingredients["recipe_id"].fillna("").eq(recipe_id)] if not recipe_ingredients.empty else pd.DataFrame()
                records = []
                for _, row in rows.iterrows():
                    records.append({
                        "shopping_item_id": f"shopping-item-{uuid.uuid4().hex[:12]}",
                        "shopping_list_id": list_id,
                        "shopping_list_name": selected_list,
                        "category_name": str(row.get("category_name", "") or "Produce"),
                        "quantity": str(row.get("quantity", "") or ""),
                        "unit": str(row.get("unit", "") or ""),
                        "ingredient": str(row.get("ingredient", "") or ""),
                        "inventory_id": str(row.get("inventory_id", "") or ""),
                        "recipe_id": recipe_id,
                        "recipe_name": recipe_name,
                        "checked": "",
                        "notes": str(row.get("notes", "") or ""),
                        "status": "active",
                        "source": "Meal Plan recipe add",
                    })
                if not records:
                    st.warning("This recipe has no ingredients yet.")
                else:
                    ok, msg = append_many_online_records(sheet_id, {"shopping_items": records})
                    if ok:
                        st.success(f"Added {len(records)} recipe item(s) to the shopping list.")
                        st.rerun()
                    else:
                        st.warning(msg)


def render_shopping_list_manager(sheet_id: str) -> None:
    ensure_grocery_default_rows(sheet_id)
    st.header("Nutrition")
    st.write("Plan groceries by category, keep an inventory with expiry and seasonality, and build recipes from ingredients.")
    tabs = st.tabs(["Shopping Lists", "Inventory", "Nutrition", "Recipes", "Starter Packs", "Templates", "Categories"])
    with tabs[0]:
        render_shopping_lists_tab(sheet_id)
    with tabs[1]:
        render_grocery_inventory_tab(sheet_id)
    with tabs[2]:
        render_grocery_nutrition_tab(sheet_id)
    with tabs[3]:
        render_recipes_tab(sheet_id)
    with tabs[4]:
        render_grocery_starter_packs_tab(sheet_id)
    with tabs[5]:
        render_grocery_template_tab(sheet_id)
    with tabs[6]:
        render_grocery_categories_tab(sheet_id)


def shopping_list_beta_tab() -> None:
    handle_google_oauth_redirect()
    auth_ready = web_oauth_available()
    credentials = google_credentials_from_session()
    should_prepare_sheet = bool(credentials and not st.session_state.get("sync_sheet_id"))
    if should_prepare_sheet and (st.session_state.pop("auto_create_sync_sheet_after_connect", False) or not st.session_state.get("sync_sheet_ready_attempted")):
        st.session_state["sync_sheet_ready_attempted"] = True
        ok, sheet_id_found, message = ensure_pathmark_sync_sheet_ready()
        if not ok:
            st.warning(safe_user_message(message))

    sheet_id = st.session_state.get("sync_sheet_id", "")
    if credentials and sheet_id:
        apply_online_theme(sheet_id)
        render_seasonal_banner(compact=True)
    st.header("Nutrition")
    render_connection_summary(credentials, sheet_id, auth_ready)

    if not credentials and auth_ready:
        render_google_permissions_onboarding(compact=True)
        return
    if credentials and not sheet_id:
        render_missing_sync_sheet_recovery("shopping")
        return
    if not (credentials and sheet_id):
        st.info("Pathmark is still preparing your sync sheet. Refresh online data or reconnect from Settings if this does not resolve.")
        return

    service = sheets_service()
    if service is not None:
        try:
            with st.spinner("Loading your Meal Plan from Google Sheets..."):
                ensure_pathmark_online_schema(service, sheet_id)
                load_online_tables(sheet_id)
        except Exception:
            st.warning("Pathmark could not prepare your Meal Plan just now. Please refresh online data or reconnect Google access, then try again.")
    render_safe_section("Meal Plan", render_shopping_list_manager, sheet_id)


def spending_plan_beta_tab() -> None:
    handle_google_oauth_redirect()
    auth_ready = web_oauth_available()
    credentials = google_credentials_from_session()
    should_prepare_sheet = bool(credentials and not st.session_state.get("sync_sheet_id"))
    if should_prepare_sheet and (st.session_state.pop("auto_create_sync_sheet_after_connect", False) or not st.session_state.get("sync_sheet_ready_attempted")):
        st.session_state["sync_sheet_ready_attempted"] = True
        ok, sheet_id_found, message = ensure_pathmark_sync_sheet_ready()
        if not ok:
            st.warning(safe_user_message(message))

    sheet_id = st.session_state.get("sync_sheet_id", "")
    if credentials and sheet_id:
        apply_online_theme(sheet_id)
        render_seasonal_banner(compact=True)
    st.header("Finance")
    st.write("Use this space to plan what comes in, what goes out, and how money should move between accounts. Spending Plan records are saved in the Spending Plan tabs of your Pathmark Sync sheet.")
    render_connection_summary(credentials, sheet_id, auth_ready)

    if not credentials and auth_ready:
        render_google_permissions_onboarding(compact=True)
        return

    if credentials and not sheet_id:
        render_missing_sync_sheet_recovery("spending")
        return

    if not (credentials and sheet_id):
        st.info("Pathmark is still preparing your sync sheet. Refresh online data or reconnect from Settings if this does not resolve.")
        return

    service = sheets_service()
    if service is not None:
        try:
            with st.spinner("Loading your Spending Plan from Google Sheets..."):
                ensure_pathmark_online_schema(service, sheet_id)
                load_online_tables(sheet_id)
        except Exception:
            st.warning("Pathmark could not prepare your Spending Plan just now. Please refresh online data or reconnect Google access, then try again.")

    render_safe_section("Spending Plan", render_spending_plan_manager, sheet_id)


def _hex_to_rgb(hex_colour: str) -> tuple[int, int, int] | None:
    text = str(hex_colour or "").strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", text):
        return None
    return int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    vals = []
    for channel in rgb:
        c = channel / 255.0
        vals.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def contrast_ratio_hex(foreground: str, background: str) -> float | None:
    fg = _hex_to_rgb(foreground)
    bg = _hex_to_rgb(background)
    if fg is None or bg is None:
        return None
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def current_theme_config_dict() -> dict[str, Any]:
    aliases = {name: info.get("alias_for") for name, info in ONLINE_THEMES.items() if isinstance(info, dict) and info.get("alias_for")}
    themes = {name: {k: v for k, v in info.items() if k not in {"alias_for", "seasonal_icon"} or v} for name, info in ONLINE_THEMES.items() if name in ONLINE_THEME_OPTIONS and isinstance(info, dict) and not info.get("alias_for")}
    return {"options": list(ONLINE_THEME_OPTIONS), "seasonal_accents": SEASONAL_ACCENTS, "themes": themes, "aliases": aliases}


def theme_config_to_yaml(config: dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    return json.dumps(config, indent=2)


def render_developer_theme_editor() -> None:
    st.subheader("Theme editor")
    st.caption("Edit Pathmark accent presets, preview contrast, then download an updated app/config/themes.yaml to commit to GitHub.")
    config = current_theme_config_dict()
    theme_rows = []
    for name in ONLINE_THEME_OPTIONS:
        info = ONLINE_THEMES.get(name, {})
        if not isinstance(info, dict) or info.get("alias_for"):
            continue
        theme_rows.append({"name": name, "accent": str(info.get("accent", "#334E9E")), "accent_2": str(info.get("accent_2", info.get("accent", "#334E9E"))), "auto": bool(info.get("auto", False)), "custom": bool(info.get("custom", False))})
    edited_themes = st.data_editor(pd.DataFrame(theme_rows), hide_index=True, use_container_width=True, num_rows="dynamic", column_config={"name": st.column_config.TextColumn("Theme name", required=True), "accent": st.column_config.TextColumn("Accent hex", required=True), "accent_2": st.column_config.TextColumn("Second accent hex", required=True), "auto": st.column_config.CheckboxColumn("Seasonal/auto"), "custom": st.column_config.CheckboxColumn("Custom option")}, key="developer_theme_editor_table")
    season_rows = []
    for season in ["Spring", "Summer", "Autumn", "Winter"]:
        info = SEASONAL_ACCENTS.get(season, {})
        season_rows.append({"season": season, "accent": str(info.get("accent", "#334E9E")), "accent_2": str(info.get("accent_2", "#6BA2B8"))})
    edited_seasons = st.data_editor(pd.DataFrame(season_rows), hide_index=True, use_container_width=True, column_config={"season": st.column_config.TextColumn("Season", disabled=True), "accent": st.column_config.TextColumn("Accent hex", required=True), "accent_2": st.column_config.TextColumn("Second accent hex", required=True)}, key="developer_seasonal_theme_editor_table")
    preview_options = [str(row.get("name", "")).strip() for row in edited_themes.to_dict("records") if str(row.get("name", "")).strip()]
    preview_name = st.selectbox("Preview theme", preview_options or ONLINE_THEME_OPTIONS, key="developer_theme_preview_choice")
    preview_row = next((row for row in edited_themes.to_dict("records") if str(row.get("name", "")).strip() == preview_name), None)
    if preview_row:
        accent = str(preview_row.get("accent", "#334E9E"))
        accent_2 = str(preview_row.get("accent_2", accent))
        light_ratio = contrast_ratio_hex(accent, "#FFFFFF") or 0
        dark_ratio = contrast_ratio_hex(accent, "#111827") or 0
        preview_html = '<div class="grid-3"><div class="card"><h3>Accent</h3><p><strong>{}</strong><br>{} / {}</p></div><div class="card"><h3>On light surface</h3><p>Contrast vs white: <strong>{:.2f}:1</strong></p></div><div class="card"><h3>On dark surface</h3><p>Contrast vs dark: <strong>{:.2f}:1</strong></p></div></div>'.format(html.escape(preview_name), html.escape(accent), html.escape(accent_2), light_ratio, dark_ratio)
        st.markdown(preview_html, unsafe_allow_html=True)
        if light_ratio < 3:
            st.warning("This accent is low contrast on a white surface. It may need a darker light-mode variant.")
        if dark_ratio < 3:
            st.warning("This accent is low contrast on a dark surface. It may need a lighter dark-mode variant.")
    new_options = preview_options
    new_themes: dict[str, dict[str, Any]] = {}
    for row in edited_themes.to_dict("records"):
        name = str(row.get("name", "")).strip(); accent = str(row.get("accent", "")).strip(); accent_2 = str(row.get("accent_2", "")).strip() or accent
        if not name or not re.fullmatch(r"#[0-9A-Fa-f]{6}", accent) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", accent_2):
            continue
        info: dict[str, Any] = {"accent": accent, "accent_2": accent_2}
        if bool(row.get("auto", False)): info["auto"] = True
        if bool(row.get("custom", False)): info["custom"] = True
        new_themes[name] = info
    new_seasons: dict[str, dict[str, str]] = {}
    for row in edited_seasons.to_dict("records"):
        season = str(row.get("season", "")).strip(); accent = str(row.get("accent", "")).strip(); accent_2 = str(row.get("accent_2", "")).strip() or accent
        if season and re.fullmatch(r"#[0-9A-Fa-f]{6}", accent) and re.fullmatch(r"#[0-9A-Fa-f]{6}", accent_2):
            new_seasons[season] = {"accent": accent, "accent_2": accent_2}
    new_config = {"options": new_options, "seasonal_accents": new_seasons, "themes": new_themes, "aliases": config.get("aliases", {})}
    yaml_text = theme_config_to_yaml(new_config)
    st.download_button("Download updated themes.yaml", data=yaml_text.encode("utf-8"), file_name="themes.yaml", mime="text/yaml", use_container_width=True)
    with st.expander("Preview generated theme config", expanded=False):
        st.markdown(f'<div class="theme-config-preview">{html.escape(yaml_text)}</div>', unsafe_allow_html=True)
    st.info("To apply changes to the deployed app, replace app/config/themes.yaml in the GitHub repository with the downloaded file and redeploy. Direct GitHub write-back can be added later with a secure GitHub token.")

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
    with st.expander("Theme editor", expanded=False):
        render_developer_theme_editor()

    if supabase_available():
        st.success("Supabase access management is connected. Supabase is used only for roles, feature flags, and audit logs. It does not store Pathmark projects, routines, checklist items, Workspace files, or on-the-go planning entries.")
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

        Supabase should not store projects, routines, Google Tasks checklist items, calendar blocks, Workspace files, or other private planning content at this stage.
        """)



def _query_param_value(name: str) -> str:
    try:
        value = st.query_params.get(name, "")
        if isinstance(value, list):
            value = value[0] if value else ""
        return str(value or "").strip().lower()
    except Exception:
        return ""


def public_page_from_query() -> str:
    """Return the requested public OAuth/branding page, if any.

    Google Auth Platform can use URLs such as:
    - https://pathmark.streamlit.app/?page=privacy
    - https://pathmark.streamlit.app/?page=terms
    These pages must remain reachable without login.
    """
    page = _query_param_value("page") or _query_param_value("policy")
    aliases = {
        "privacy": "privacy",
        "privacy-policy": "privacy",
        "privacy_policy": "privacy",
        "terms": "terms",
        "terms-of-service": "terms",
        "terms_of_service": "terms",
        "tos": "terms",
        "oauth": "oauth",
        "google": "oauth",
        "google-access": "oauth",
    }
    return aliases.get(page, "")


def render_public_page_nav() -> None:
    render_seasonal_banner(compact=True, force=True, season=current_southern_hemisphere_season())
    st.markdown("""
    <div class="policy-link-row" aria-label="Pathmark public navigation">
      <a href="/">Home</a>
      <a href="?page=privacy">Privacy Policy</a>
      <a href="?page=terms">Terms of Service</a>
      <a href="?page=oauth">Google access</a>
    </div>
    """, unsafe_allow_html=True)


def render_public_privacy_policy() -> None:
    inject_theme_css(normalise_online_theme(st.session_state.get("hosted_theme_preference") or "Seasonal"))
    render_public_page_nav()
    st.title("Pathmark Privacy Policy")
    st.caption("Last updated: June 2026")
    st.markdown("""
    This page is public so it can be used on the Google OAuth consent screen.

    ## Summary
    Pathmark is designed so your private planning, Finance and Nutrition records stay in files owned by you, primarily a Google Sheet called **Pathmark Sync**. Pathmark uses Google sign-in and Google APIs only after you grant permission. This public Privacy Policy is the concise policy page used for Google OAuth and public review; the in-app **About & Privacy** page gives additional plain-English context for signed-in users.

    ## Information Pathmark uses
    Pathmark may use:

    - your Google account email address, to identify your Pathmark access level;
    - Google Sheets and Drive access, to create and update Pathmark Sync, Pathmark backups and optional templates;
    - Google Tasks access, when you choose to sync checklist items;
    - Google Calendar access, when you choose to sync Pathmark calendar events;
    - Supabase access/profile records, such as email, role, status, feature flags, theme preference and audit records;
    - optional starter-pack library rows copied into your own Pathmark Sync sheet when you import them.

    ## Where information is stored
    Your active Pathmark records are stored in your own Google files, including Pathmark Sync, backup sheets and optional templates. Google Tasks and Google Calendar store synced items only when you run sync actions. Supabase stores access/profile metadata and optional starter-pack library data. GitHub stores the public app code and release files.

    ## Google Drive scope
    Pathmark is intended to use Google's limited Drive file access, so it works with Pathmark-created files or files you explicitly use with Pathmark. It is not intended to browse unrelated Drive content.

    ## Google Tasks and Calendar
    Google Tasks and Calendar permissions allow Pathmark to create, update and read linked Pathmark items. Pathmark stores task and event IDs in Pathmark Sync so future syncs can update matching items rather than creating duplicates.

    ## What Pathmark does not do
    Pathmark does not sell user data, does not use your planning or Finance content for advertising, does not store your Google password, and does not intentionally store OAuth tokens in Supabase, GitHub, logs or public files.

    ## Revoking access
    You can revoke Pathmark's Google access from your Google Account. You can also delete Pathmark Sync, backups or templates directly from Google Drive. Deleting online Pathmark data does not delete any local desktop Workspace files.

    ## Active development
    Pathmark is under active development. Features, wording and data structures may change. Backups are recommended before imports, reset actions or major sync changes.
    """)


def render_public_terms_of_service() -> None:
    inject_theme_css(normalise_online_theme(st.session_state.get("hosted_theme_preference") or "Seasonal"))
    render_public_page_nav()
    st.title("Pathmark Terms of Service")
    st.caption("Last updated: June 2026")
    st.markdown("""
    This page is public so it can be used on the Google OAuth consent screen.

    ## What Pathmark is
    Pathmark is a planning, wellbeing, project, calendar/task sync, Finance, Nutrition and starter-pack tool. It helps users organise routines, projects, tasks, calendar time, spending-plan records, recipes, ingredients and related information.

    ## Beta status
    Pathmark is in active development. Features may change, break, be renamed or be removed. You should keep backups before using import, sync, reset, restore or delete workflows. This public Terms page is intended to be stable and accessible for Google OAuth review; the in-app **About & Privacy** page can provide fuller operational explanations without replacing these terms.

    ## Your responsibility
    You are responsible for the accuracy of information you enter, the files you authorise Pathmark to use, the sync actions you run, and the decisions you make from Pathmark outputs.

    ## Google services
    Pathmark uses Google sign-in and Google APIs after you grant permission. Google may show a consent screen explaining the access requested. Pathmark cannot update your Google files, Tasks or Calendar unless the relevant access is available.

    ## Finance disclaimer
    Pathmark Finance is a budgeting and planning tool only. It does not provide financial, legal, tax, mortgage, insurance, KiwiSaver, investment or debt advice. If you are in financial hardship, consider seeking help from an appropriate support or budgeting service.

    ## No warranty
    Pathmark is provided as-is during development. It may contain bugs or incomplete features. You should review exports, sync results and generated records before relying on them.

    ## Revoking access and deletion
    You may revoke Google access from your Google Account. You may also delete Pathmark-created Google files directly from Google Drive. Some Pathmark deletion or reset workflows may create a backup first.

    ## Changes
    These terms may be updated as Pathmark develops. Continued use after updates means you accept the updated terms.
    """)


def render_google_oauth_public_explanation() -> None:
    inject_theme_css(normalise_online_theme(st.session_state.get("hosted_theme_preference") or "Seasonal"))
    render_public_page_nav()
    st.title("Google access in Pathmark")
    st.markdown("""
    Pathmark uses Google access so your online records can live in your own Google files and services.

    <div class="grid-2">
      <div class="card"><h3>Home page</h3><p><code>https://pathmark.streamlit.app</code></p></div>
      <div class="card"><h3>Privacy Policy</h3><p><code>https://pathmark.streamlit.app/?page=privacy</code></p></div>
      <div class="card"><h3>Terms of Service</h3><p><code>https://pathmark.streamlit.app/?page=terms</code></p></div>
      <div class="card"><h3>Google consent screen</h3><p>The logo and these public links should match the Google Auth Platform branding settings.</p></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
    ## Permission behaviour
    Google may request access for Drive/Sheets, Tasks and Calendar during connection. In Pathmark, sync actions remain user-triggered:

    - Pathmark Sync is created or updated in Google Sheets.
    - Google Tasks items are created or updated when you run Google Sync.
    - Google Calendar events are created or updated when you run Google Sync.
    - Supabase stores access/profile metadata and optional starter-pack library rows, not your private planning records.

    ## Google Auth Platform checklist
    In Google Auth Platform, the Pathmark branding should use:

    - Application home page: `https://pathmark.streamlit.app`
    - Application privacy policy link: `https://pathmark.streamlit.app/?page=privacy`
    - Application terms of service link: `https://pathmark.streamlit.app/?page=terms`
    - App logo: the Pathmark logo you uploaded

    If Google later requires verification, any domains used in these links and OAuth client settings need to satisfy Google's authorised-domain requirements.
    """)


def render_public_oauth_branding_page_if_requested() -> bool:
    page = public_page_from_query()
    if not page:
        return False
    if page == "privacy":
        render_public_privacy_policy()
    elif page == "terms":
        render_public_terms_of_service()
    elif page == "oauth":
        render_google_oauth_public_explanation()
    return True


def render_app() -> None:
    if render_public_oauth_branding_page_if_requested():
        return
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
        st.session_state.pop("show_login_terms", None)
        st.session_state.pop("google_permissions_ack", None)
        inject_theme_css(theme_for_user(user.get("email", "")))
    else:
        inject_theme_css(normalise_online_theme(st.session_state.get("hosted_theme_preference") or "Seasonal"))
    maybe_record_login(user.get("email", ""), role, status)
    render_account_bar(role, user)
    if status == "disabled":
        st.error("This account has been disabled for the hosted Pathmark page.")
        return

    if not user.get("email") and st.session_state.get("show_login_terms") and login_configured():
        render_google_permissions_onboarding(compact=False)
        return

    # After login, land the user in Planner by making it the first tab,
    # but keep the rest of the top-level navigation available. This avoids the
    # earlier hard redirect that hid About & Privacy, Theme and Spending Plan.
    post_login_landing = bool(user.get("email") and role_can_use_on_the_go(role, status))
    if post_login_landing:
        tabs = ["Planning", "Finance", "Nutrition", "Home", "Theme", "About & Privacy"]
    else:
        tabs = ["Home", "Theme", "About & Privacy"]
    if role_can_develop(role, status):
        tabs.append("Developer")

    created_tabs = st.tabs(tabs)
    for tab_obj, tab_name in zip(created_tabs, tabs):
        with tab_obj:
            if tab_name == "Home":
                download_tab()
            elif tab_name == "Theme":
                theme_tab()
            elif tab_name == "About & Privacy":
                about_privacy_tab()
            elif tab_name == "Planning":
                on_the_go_tab()
            elif tab_name == "Finance":
                spending_plan_beta_tab()
            elif tab_name == "Nutrition":
                shopping_list_beta_tab()
            elif tab_name == "Developer":
                developer_tab()


render_app()

st.caption("Pathmark release hub. Sign in to use Planning, Finance and Nutrition when enabled for your account.")
