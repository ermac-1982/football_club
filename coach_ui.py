"""Situational Coach path, drills, and feedback."""

from __future__ import annotations

import base64
import io
import math
import struct
import wave
from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from coach_engine import get_scenario as coach_scenario
from position_engine import get_scenario as quiz_scenario
from coach_pitch import coach_pitch


class _Track:
    def __init__(self, prefix: str, api: str, lookup):
        self.prefix = prefix
        self.api = api
        self.lookup = lookup
        self.screen = f"{prefix}_screen"
        self.section = f"{prefix}_section_id"
        self.scenario = f"{prefix}_scenario_id"
        self.nonce = f"{prefix}_nonce"
        self.handled = f"{prefix}_handled"
        self.feedback = f"{prefix}_feedback"
        self.feedback_n = f"{prefix}_feedback_n"

    def button(self, name: str) -> str:
        return f"{self.prefix}_{name}"


_COACH = _Track("coach", "/coach", coach_scenario)
_QUIZ = _Track("pos", "/position", quiz_scenario)
_track = _COACH


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    import app as hub

    return hub.api_request(method, path, payload, st.session_state.token)


def _screen(name: str) -> None:
    st.session_state[_track.screen] = name


def render_situational_coach(user: dict) -> None:
    global _track
    _track = _COACH
    _render_track(user)


def render_positional_quiz(user: dict) -> None:
    global _track
    _track = _QUIZ
    _render_track(user)


def _render_track(user: dict) -> None:
    st.markdown('<div class="volt-coach"></div>', unsafe_allow_html=True)
    screen = st.session_state.get(_track.screen) or "path"
    if screen == "surge":
        st.session_state.coach_surge_open = True
        screen = "feedback"
        st.session_state[_track.screen] = "feedback"
    path = None
    try:
        path = _api("GET", f"{_track.api}/path")
    except Exception as exc:
        _show_error(exc)
    if path is not None:
        if screen == "section":
            _render_section(path)
        elif screen == "play":
            _render_play()
        elif screen == "feedback":
            _render_feedback()
        else:
            _render_path(path)
    render_power_surge(user)


def _show_error(exc: Exception) -> None:
    message = getattr(exc, "message", None) or "The coach could not load. Check that the API is running."
    st.error(message)


def _render_path(path: dict) -> None:
    progress = path["progress"]
    width = 0 if not progress["total"] else round(100 * progress["attempted"] / progress["total"])
    st.markdown(
        f"""
        <div class="volt-card volt-coach-progress">
          <p class="volt-kicker">CHARGE</p>
          <h2>{progress["attempted"]} of {progress["total"]} drills</h2>
          <div class="volt-coach-bar" aria-hidden="true"><span style="width:{width}%"></span></div>
          <p>Total score {progress["totalScore"]:,} of {progress["maxScore"]:,}</p>
          <p>Accuracy {progress["accuracy"]}% · Average {progress["averageScore"]} · Best {progress["bestScore"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(_path_html(path["sections"]), unsafe_allow_html=True)
    notes = [row for row in progress["byCategory"] if row["attempted"]]
    if notes:
        bits = "".join(
            f"<li><strong>{escape(row['label'])}</strong> · {escape(row['note'])}</li>" for row in notes
        )
        st.markdown(f'<div class="volt-card"><p class="volt-kicker">PRACTICE</p><ul class="volt-coach-notes">{bits}</ul></div>', unsafe_allow_html=True)
    if path["allComplete"]:
        st.markdown(
            '<div class="volt-card volt-next"><p class="volt-kicker">PATH COMPLETE</p><h2>You charged the whole path.</h2><p>Replay any section to raise your score.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        nxt = _find_scenario(path, path["nextScenarioId"])
        st.markdown(
            f"""
            <div class="volt-card volt-next">
              <p class="volt-kicker">NEXT DRILL</p>
              <h2>{escape(nxt["title"])}</h2>
              <p>{escape(nxt["difficulty"].title())} · {escape(_section(path, path["nextSectionId"])["title"])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    label = "Replay the path" if path["allComplete"] else "Start Drill"
    if st.button(label, type="primary", width="stretch", key=_track.button("start")):
        scenario_id = 1 if path["allComplete"] else path["nextScenarioId"]
        _open_scenario(path, scenario_id)
    open_sections = [section for section in path["sections"] if section["status"] != "locked"]
    if open_sections:
        section_ids = [section["id"] for section in open_sections]
        current_id = next(
            (section["id"] for section in open_sections if section["status"] == "current"),
            section_ids[-1],
        )
        picked = st.selectbox(
            "Section",
            section_ids,
            index=section_ids.index(current_id),
            format_func=lambda section_id: _section(path, section_id)["title"],
            key=_track.button("section_pick"),
        )
        if st.button("Open section", width="stretch", key=_track.button("open_section")):
            st.session_state[_track.section] = picked
            _screen("section")
            st.rerun()


def _path_html(sections: list[dict]) -> str:
    parts = ['<div class="volt-path">']
    for index, section in enumerate(sections):
        mark = "✓" if section["status"] == "complete" else str(index + 1)
        parts.append(
            f"""
            <div class="volt-path-stop is-{escape(section["status"])}">
              <span class="volt-path-dot">{mark}</span>
              <div>
                <p class="volt-kicker">{escape(section["kicker"])}</p>
                <strong>{escape(section["title"])}</strong>
                <p>{section["completed"]} / {section["total"]} · {escape(section["modeLabel"])}</p>
              </div>
            </div>
            """
        )
        if index < len(sections) - 1:
            parts.append(f'<div class="volt-path-wire is-{escape(section["status"])}"></div>')
    parts.append("</div>")
    return "".join(parts)


def _render_section(path: dict) -> None:
    section = _section(path, st.session_state.get(_track.section))
    if section is None:
        _screen("path")
        st.rerun()
    if st.button("Back to path", key=_track.button("section_back")):
        _screen("path")
        st.rerun()
    st.markdown(
        f"""
        <p class="volt-kicker">{escape(section["kicker"])}</p>
        <h2>{escape(section["title"])}</h2>
        <p class="volt-sub">{escape(section["blurb"])}</p>
        """,
        unsafe_allow_html=True,
    )
    rows = []
    for scenario in section["scenarios"]:
        score = "Not tried" if not scenario["done"] else f"Best {scenario['bestScore']}"
        rows.append(
            f"<li><strong>{escape(scenario['title'])}</strong> · {escape(scenario['difficulty'].title())} · {score}</li>"
        )
    st.markdown(f'<ul class="volt-coach-notes">{"".join(rows)}</ul>', unsafe_allow_html=True)
    options = [scenario["id"] for scenario in section["scenarios"]]
    labels = {scenario["id"]: scenario["title"] for scenario in section["scenarios"]}
    pending = next((scenario["id"] for scenario in section["scenarios"] if not scenario["done"]), options[0])
    picked = st.selectbox(
        "Drill",
        options,
        index=options.index(pending),
        format_func=lambda scenario_id: labels[scenario_id],
        key=_track.button("drill_pick"),
    )
    if st.button("Start Drill", type="primary", width="stretch", key=_track.button("section_start")):
        _open_scenario(path, picked)


def _render_play() -> None:
    scenario_id = st.session_state.get(_track.scenario)
    if not scenario_id:
        _screen("path")
        st.rerun()
    if st.button("Back", key=_track.button("play_back")):
        _screen("section")
        st.rerun()
    try:
        scenario = _api("GET", f"{_track.api}/scenarios/{scenario_id}")
    except Exception as exc:
        _show_error(exc)
        return
    st.markdown(
        f"""
        <p class="volt-kicker">{escape(scenario["difficulty"].upper())} · {escape("SHAPE" if scenario["mode"] == "positions" else scenario["mode"].upper())}</p>
        <h2>{escape(scenario["title"])}</h2>
        <p>{escape(scenario["description"])}</p>
        """,
        unsafe_allow_html=True,
    )
    nonce = st.session_state.get(_track.nonce, 0)
    value = coach_pitch(scenario, key=f"{_track.prefix}-pitch-{scenario_id}-{nonce}")
    if not isinstance(value, dict):
        return
    token = value.get("token")
    if not token or token == st.session_state.get(_track.handled) or value.get("scenarioId") != scenario_id:
        return
    if value.get("placements"):
        body = {"placements": value["placements"]}
    else:
        body = {key: value[key] for key in ("x", "y", "action", "targetPlayerId") if key in value}
    try:
        result = _api("POST", f"{_track.api}/scenarios/{scenario_id}/answer", body)
    except Exception as exc:
        st.session_state[_track.handled] = token
        _show_error(exc)
        return
    st.session_state[_track.handled] = token
    st.session_state[_track.feedback] = result
    st.session_state[_track.feedback_n] = st.session_state.get(_track.feedback_n, 0) + 1
    st.session_state[_track.nonce] = nonce + 1
    if result.get("sectionJustCompleted"):
        st.session_state.surge_bonus = int(result.get("sectionBonus") or 500)
        st.session_state.surge_reason = "Section clear"
        st.session_state.coach_surge_open = True
        st.session_state.coach_surge_sound_played = False
    _screen("feedback")
    st.rerun()


def _render_feedback() -> None:
    result = st.session_state.get(_track.feedback) or {}
    scenario_id = result.get("scenarioId") or st.session_state.get(_track.scenario)
    headline = {"correct": "Correct", "partial": "Partially correct", "incorrect": "Incorrect"}.get(
        result.get("result"), "Result"
    )
    st.markdown(
        f"""
        <div class="volt-card volt-coach-result is-{escape(str(result.get("result")))}">
          <p class="volt-kicker">{escape(headline.upper())}</p>
          <h2>{result.get("points", 0)} points</h2>
          <p>{escape(result.get("label", ""))}. {escape(result.get("explanation", ""))}</p>
          <p>Total score {int(result.get("totalScore") or 0):,}</p>
          <p><strong>Remember:</strong> {escape(result.get("coachingTip", ""))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if result.get("sectionComplete") and not result.get("sectionJustCompleted"):
        st.success("Section complete. The next part of the path is open.")
    try:
        scenario = _api("GET", f"{_track.api}/scenarios/{scenario_id}")
    except Exception as exc:
        _show_error(exc)
        scenario = None
    if scenario:
        review = dict(scenario)
        review["playMode"] = scenario["mode"]
        review["mode"] = "review"
        review["review"] = {
            "submitted": result.get("submitted"),
            "correctPosition": result.get("correctPosition"),
            "correctPositions": result.get("correctPositions"),
            "correctAction": result.get("correctAction"),
            "score": result.get("score", 0),
        }
        coach_pitch(review, key=f"{_track.prefix}-review-{scenario_id}-{st.session_state.get(_track.feedback_n, 0)}")
    columns = st.columns(2)
    with columns[0]:
        if st.button("Try again", width="stretch", key=_track.button("retry")):
            st.session_state[_track.nonce] = st.session_state.get(_track.nonce, 0) + 1
            _screen("play")
            st.rerun()
    with columns[1]:
        nxt = result.get("nextScenarioId")
        label = "Next drill" if nxt else "Back to path"
        if st.button(label, type="primary", width="stretch", key=_track.button("next")):
            st.session_state.coach_surge_open = False
            st.session_state.coach_surge_sound_played = False
            if nxt:
                st.session_state[_track.scenario] = nxt
                st.session_state[_track.section] = _track.lookup(nxt)["section"]
                st.session_state[_track.nonce] = st.session_state.get(_track.nonce, 0) + 1
                _screen("play")
            else:
                _screen("path")
            st.rerun()


@lru_cache(maxsize=1)
def _surge_wav() -> str:
    rate = 22050
    seconds = 1.15
    frames = int(rate * seconds)
    samples = bytearray()
    for index in range(frames):
        t = index / rate
        rise = (t / seconds) ** 1.35
        env = math.sin(math.pi * min(t / seconds, 1.0)) ** 0.55
        tone = math.sin(2 * math.pi * (160 + 980 * rise) * t)
        spark = math.sin(2 * math.pi * (1600 + 500 * math.sin(36 * t)) * t)
        spark *= 0.35 if int(t * 24) % 3 == 0 else 0.08
        ping = math.sin(2 * math.pi * 1320 * t) * math.exp(-7 * (t % 0.16))
        value = max(-1.0, min(1.0, (0.62 * tone + spark + 0.28 * ping) * env))
        samples += struct.pack("<h", int(value * 28000))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _play_surge() -> None:
    st.audio(base64.b64decode(_surge_wav()), format="audio/wav", autoplay=True)


def _charge_art_url() -> str:
    from streamlit.elements.lib.image_utils import image_to_url
    from streamlit.elements.lib.layout_utils import LayoutConfig

    path = Path(__file__).resolve().parent / "assets" / "surge" / "charge_up.png"
    return image_to_url(
        str(path),
        layout_config=LayoutConfig(width="content"),
        clamp=False,
        channels="RGB",
        output_format="auto",
        image_id="volt-charge-up",
    )


def _surge_copy() -> tuple[int, str, str]:
    result = st.session_state.get("coach_feedback") or {}
    bonus = st.session_state.get("surge_bonus")
    if not bonus:
        bonus = int(result.get("sectionBonus") or 500)
    bonus = int(bonus)
    reason = st.session_state.get("surge_reason")
    if not reason:
        reason = "Section clear" if bonus >= 500 else "Clip watched"
    label, _, value = str(reason).partition(" ")
    return bonus, label.upper(), (value or label).upper()


def render_power_surge(user: dict) -> None:
    if st.session_state.get("coach_surge_open"):
        _surge_dialog(user)


@st.dialog("Power surge", width="small", dismissible=False)
def _surge_dialog(_user: dict) -> None:
    bonus, label, value = _surge_copy()
    art = _charge_art_url()
    if not st.session_state.get("coach_surge_sound_played"):
        _play_surge()
        st.session_state.coach_surge_sound_played = True
    st.markdown(
        f"""
        <div class="volt-charge-card">
          <div class="volt-charge-frame">
            <img class="volt-charge-art" src="{escape(art)}" alt="">
            <p class="volt-charge-amount">+{bonus:,} XP</p>
            <p class="volt-charge-reason"><span>{escape(label)}</span><strong>{escape(value)}</strong></p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("BACK TO THE PITCH →", type="primary", width="stretch", key="coach_surge_continue"):
        st.session_state.coach_surge_open = False
        st.session_state.coach_surge_sound_played = False
        st.session_state.surge_bonus = None
        st.session_state.surge_reason = None
        st.rerun()
    st.markdown(
        '<p class="volt-charge-foot">VOLT PITCH KIDS FOOTBALL APP</p>',
        unsafe_allow_html=True,
    )


def _open_scenario(path: dict, scenario_id: int) -> None:
    scenario = _find_scenario(path, scenario_id)
    st.session_state[_track.scenario] = scenario_id
    st.session_state[_track.section] = _section_for(path, scenario_id)
    st.session_state[_track.nonce] = st.session_state.get(_track.nonce, 0) + 1
    _screen("play")
    st.rerun()


def _find_scenario(path: dict, scenario_id: int) -> dict:
    for section in path["sections"]:
        for scenario in section["scenarios"]:
            if scenario["id"] == scenario_id:
                return scenario
    return path["sections"][0]["scenarios"][0]


def _section(path: dict, section_id: str) -> dict | None:
    for section in path["sections"]:
        if section["id"] == section_id:
            return section
    return None


def _section_for(path: dict, scenario_id: int) -> str | None:
    for section in path["sections"]:
        if any(scenario["id"] == scenario_id for scenario in section["scenarios"]):
            return section["id"]
    return None
