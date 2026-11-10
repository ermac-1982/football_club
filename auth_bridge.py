"""Browser bridge that keeps the refresh cookie on the API host."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_BRIDGE = components.declare_component(
    "auth_bridge",
    path=str(Path(__file__).resolve().parent / "auth_bridge"),
)


def auth_bridge(api: str, mode: str, grant: str = "", key: str = "auth_bridge"):
    return _BRIDGE(api=api, mode=mode, grant=grant, key=key, default=None)
