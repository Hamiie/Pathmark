from __future__ import annotations

from typing import Any

import streamlit as st


def session_get(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def session_set(key: str, value: Any) -> Any:
    st.session_state[key] = value
    return value


def session_dict(key: str) -> dict[str, Any]:
    value = st.session_state.get(key)
    if not isinstance(value, dict):
        value = {}
        st.session_state[key] = value
    return value


def session_list(key: str) -> list[Any]:
    value = st.session_state.get(key)
    if not isinstance(value, list):
        value = []
        st.session_state[key] = value
    return value
