"""Situational Coach path, drills, and feedback."""

from __future__ import annotations

import base64
import io
import math
import struct
import wave
from functools import lru_cache
from html import escape

import streamlit as st

from coach_engine import get_scenario
from coach_pitch import coach_pitch


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    import app as hub

    return hub.api_request(method, path, payload, st.session_state.token)


def _screen(name: str) -> None:
    st.session_state.coach_screen = name


def render_situational_coach(user: dict) -> None:
    st.markdown('<div class="volt-coach"></div>', unsafe_allow_html=True)
    screen = st.session_state.get("coach_screen") or "path"
    if screen == "surge":
        st.session_state.coach_surge_open = True
        screen = "feedback"
        st.session_state.coach_screen = "feedback"
    path = None
    try:
        path = _api("GET", "/coach/path")
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
    if st.button(label, type="primary", width="stretch", key="coach_start"):
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
        )
        if st.button("Open section", width="stretch", key="coach_open_section"):
            st.session_state.coach_section_id = picked
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
    section = _section(path, st.session_state.get("coach_section_id"))
    if section is None:
        _screen("path")
        st.rerun()
    if st.button("Back to path", key="coach_section_back"):
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
    )
    if st.button("Start Drill", type="primary", width="stretch", key="coach_section_start"):
        _open_scenario(path, picked)


def _render_play() -> None:
    scenario_id = st.session_state.get("coach_scenario_id")
    if st.button("Back", key="coach_play_back"):
        _screen("section")
        st.rerun()
    try:
        scenario = _api("GET", f"/coach/scenarios/{scenario_id}")
    except Exception as exc:
        _show_error(exc)
        return
    st.markdown(
        f"""
        <p class="volt-kicker">{escape(scenario["difficulty"].upper())} · {escape(scenario["mode"].upper())}</p>
        <h2>{escape(scenario["title"])}</h2>
        <p>{escape(scenario["description"])}</p>
        """,
        unsafe_allow_html=True,
    )
    nonce = st.session_state.get("coach_nonce", 0)
    value = coach_pitch(scenario, key=f"pitch-{scenario_id}-{nonce}")
    if not isinstance(value, dict):
        return
    token = value.get("token")
    if not token or token == st.session_state.get("coach_handled") or value.get("scenarioId") != scenario_id:
        return
    body = {key: value[key] for key in ("x", "y", "action", "targetPlayerId") if key in value}
    try:
        result = _api("POST", f"/coach/scenarios/{scenario_id}/answer", body)
    except Exception as exc:
        st.session_state.coach_handled = token
        _show_error(exc)
        return
    st.session_state.coach_handled = token
    st.session_state.coach_feedback = result
    st.session_state.coach_feedback_n = st.session_state.get("coach_feedback_n", 0) + 1
    st.session_state.coach_nonce = nonce + 1
    if result.get("sectionJustCompleted"):
        st.session_state.surge_bonus = None
        st.session_state.coach_surge_open = True
        st.session_state.coach_surge_sound_played = False
    _screen("feedback")
    st.rerun()


def _render_feedback() -> None:
    result = st.session_state.get("coach_feedback") or {}
    scenario_id = result.get("scenarioId") or st.session_state.get("coach_scenario_id")
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
        scenario = _api("GET", f"/coach/scenarios/{scenario_id}")
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
            "correctAction": result.get("correctAction"),
            "score": result.get("score", 0),
        }
        coach_pitch(review, key=f"review-{scenario_id}-{st.session_state.get('coach_feedback_n', 0)}")
    columns = st.columns(2)
    with columns[0]:
        if st.button("Try again", width="stretch", key="coach_retry"):
            st.session_state.coach_nonce = st.session_state.get("coach_nonce", 0) + 1
            _screen("play")
            st.rerun()
    with columns[1]:
        nxt = result.get("nextScenarioId")
        label = "Next drill" if nxt else "Back to path"
        if st.button(label, type="primary", width="stretch", key="coach_next"):
            if nxt:
                st.session_state.coach_scenario_id = nxt
                st.session_state.coach_section_id = get_scenario(nxt)["section"]
                st.session_state.coach_nonce = st.session_state.get("coach_nonce", 0) + 1
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


def render_power_surge(user: dict) -> None:
    if st.session_state.get("coach_surge_open"):
        _surge_dialog(user)


@st.dialog("Power surge", width="small", dismissible=False)
def _surge_dialog(user: dict) -> None:
    result = st.session_state.get("coach_feedback") or {}
    bonus = st.session_state.get("surge_bonus")
    if not bonus:
        bonus = int(result.get("sectionBonus") or 500)
    bonus = int(bonus)
    import app as hub

    portrait = hub._portrait_url(user.get("avatar"))
    if not st.session_state.get("coach_surge_sound_played"):
        _play_surge()
        st.session_state.coach_surge_sound_played = True
    st.markdown(
        f"""
        <div class="volt-charge-card">
          <div class="volt-bolt-bg"></div>
          <p class="volt-charge-logo"><span>⚡</span> VOLT PITCH</p>
          <p class="volt-charge-kicker">POWER SURGE!</p>
          <h1 class="volt-charge-title">CHARGE<br>UP</h1>
          <div class="volt-charge-hero">
            <div class="volt-orb"></div>
            <img class="volt-charge-avatar" src="{escape(portrait)}" alt="Your player">
          </div>
          <div class="volt-xp">
            <p>⚡ XP BOOST</p>
            <strong>+{bonus:,} XP</strong>
          </div>
          <p class="volt-cheer">YOU'RE UNSTOPPABLE!</p>
          <p class="volt-cheer-sub">Keep pitching. Keep winning.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("BACK TO THE PITCH →", type="primary", width="stretch", key="coach_surge_continue"):
        st.session_state.coach_surge_open = False
        st.session_state.coach_surge_sound_played = False
        st.session_state.surge_bonus = None
        st.rerun()


def _open_scenario(path: dict, scenario_id: int) -> None:
    scenario = _find_scenario(path, scenario_id)
    st.session_state.coach_scenario_id = scenario_id
    st.session_state.coach_section_id = _section_for(path, scenario_id)
    st.session_state.coach_nonce = st.session_state.get("coach_nonce", 0) + 1
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
