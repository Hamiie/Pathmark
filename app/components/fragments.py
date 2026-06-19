from __future__ import annotations

from typing import Callable, TypeVar

import streamlit as st

F = TypeVar("F", bound=Callable)


def pathmark_fragment(func: F) -> F:
    fragment = getattr(st, "fragment", None)
    if callable(fragment):
        return fragment(func)  # type: ignore[return-value]
    return func
