"""Streamlit bridge for the 7v7 pitch component."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_PITCH = components.declare_component(
    "coach_pitch",
    path=str(Path(__file__).resolve().parent / "coach_pitch"),
)


def coach_pitch(spec: dict, key: str):
    return _PITCH(spec=spec, key=key, default=None)
