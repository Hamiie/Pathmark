from __future__ import annotations

from typing import Any

import streamlit as st


def cache_get(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def cache_set(key: str, value: Any) -> Any:
    st.session_state[key] = value
    return value


def cache_delete_prefix(prefix: str) -> None:
    for key in list(st.session_state.keys()):
        if str(key).startswith(prefix):
            st.session_state.pop(key, None)
