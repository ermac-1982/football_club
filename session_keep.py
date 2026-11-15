"""Keeps the signed-in session in the browser so a refresh can restore it."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_KEEP = components.declare_component(
    "session_keep",
    path=str(Path(__file__).resolve().parent / "session_keep"),
)


def session_keep(token: str, clear: bool, key: str = "volt_session_keep"):
    return _KEEP(token=token, clear=clear, key=key, default=None)
