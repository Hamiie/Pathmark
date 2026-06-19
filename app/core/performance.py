from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

import streamlit as st

PERF_RUN_KEY = "pm_perf_current_run"
PERF_HISTORY_KEY = "pm_perf_history"
DIRTY_KEY = "pm_dirty_state"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def begin_perf_run(context: str = "") -> None:
    """Start lightweight per-rerun diagnostics for developer mode.

    This is intentionally session-local. It does not write to Google Sheets,
    Supabase or logs. It helps identify accidental full-page reruns and repeated
    Google reads/writes while Pathmark is growing.
    """
    previous = st.session_state.get(PERF_RUN_KEY)
    if isinstance(previous, dict) and previous.get("events"):
        history = st.session_state.setdefault(PERF_HISTORY_KEY, [])
        if isinstance(history, list):
            history.insert(0, previous)
            del history[25:]
    st.session_state[PERF_RUN_KEY] = {
        "started_at": _now_iso(),
        "start_perf": time.perf_counter(),
        "context": context,
        "events": [],
        "counts": {},
    }


def record_perf_event(kind: str, label: str, *, detail: str = "", count: int = 1) -> None:
    run = st.session_state.setdefault(PERF_RUN_KEY, {"started_at": _now_iso(), "start_perf": time.perf_counter(), "context": "", "events": [], "counts": {}})
    if not isinstance(run, dict):
        return
    events = run.setdefault("events", [])
    counts = run.setdefault("counts", {})
    if isinstance(counts, dict):
        counts[kind] = int(counts.get(kind, 0) or 0) + int(count or 1)
    if isinstance(events, list):
        events.append({
            "at_ms": round((time.perf_counter() - float(run.get("start_perf", time.perf_counter()))) * 1000, 1),
            "kind": str(kind),
            "label": str(label),
            "detail": str(detail or ""),
            "count": int(count or 1),
        })
        del events[80:]


def mark_dirty(scope: str, key: str, count: int = 1, label: str = "") -> None:
    dirty = st.session_state.setdefault(DIRTY_KEY, {})
    if not isinstance(dirty, dict):
        dirty = {}
        st.session_state[DIRTY_KEY] = dirty
    dirty[f"{scope}:{key}"] = {"scope": scope, "key": key, "count": int(count or 0), "label": label, "updated_at": _now_iso()}


def clear_dirty(scope: str | None = None, key: str | None = None) -> None:
    dirty = st.session_state.get(DIRTY_KEY)
    if not isinstance(dirty, dict):
        return
    if scope is None and key is None:
        dirty.clear()
        return
    prefix = f"{scope}:" if scope else ""
    for dirty_key in list(dirty.keys()):
        value = dirty.get(dirty_key, {})
        if scope and not dirty_key.startswith(prefix):
            continue
        if key and str(value.get("key", "")) != key:
            continue
        dirty.pop(dirty_key, None)


def dirty_summary() -> list[dict[str, Any]]:
    dirty = st.session_state.get(DIRTY_KEY)
    if not isinstance(dirty, dict):
        return []
    return [dict(v) for v in dirty.values() if isinstance(v, dict)]


def render_perf_diagnostics() -> None:
    """Render a compact developer performance panel."""
    run = st.session_state.get(PERF_RUN_KEY, {}) if isinstance(st.session_state.get(PERF_RUN_KEY), dict) else {}
    counts = run.get("counts", {}) if isinstance(run.get("counts"), dict) else {}
    elapsed_ms = 0.0
    try:
        elapsed_ms = (time.perf_counter() - float(run.get("start_perf", time.perf_counter()))) * 1000
    except Exception:
        elapsed_ms = 0.0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("This rerun", f"{elapsed_ms:.0f} ms")
    c2.metric("Sheets reads", str(int(counts.get("sheets_read", 0) or 0)))
    c3.metric("Sheets writes", str(int(counts.get("sheets_write", 0) or 0)))
    c4.metric("Cache hits", str(int(counts.get("cache_hit", 0) or 0)))

    dirty = dirty_summary()
    if dirty:
        st.caption("Unsaved local changes")
        if pd is not None:
            st.dataframe(pd.DataFrame(dirty), use_container_width=True, hide_index=True)
        else:
            st.write(dirty)
    else:
        st.caption("No unsaved local changes recorded in this session.")

    events = run.get("events", []) if isinstance(run.get("events"), list) else []
    if events:
        with st.expander("Current rerun events", expanded=False):
            if pd is not None:
                st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True, height=260)
            else:
                st.write(events)
    history = st.session_state.get(PERF_HISTORY_KEY, [])
    if isinstance(history, list) and history:
        with st.expander("Recent reruns", expanded=False):
            rows = []
            for h in history[:10]:
                if not isinstance(h, dict):
                    continue
                rows.append({"started_at": h.get("started_at", ""), "context": h.get("context", ""), **(h.get("counts", {}) if isinstance(h.get("counts"), dict) else {})})
            if pd is not None and rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            elif rows:
                st.write(rows)
