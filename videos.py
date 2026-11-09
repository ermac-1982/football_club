"""Clips shown on the Videos page. Drop new mp4 files in assets/videos."""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

VIDEO_DIR = Path(__file__).resolve().parent / "assets" / "videos"

CATALOG = (
    ("form_231.mp4", "FORM", "Form"),
    ("position_gk_231.mp4", "KEEPER", "Goalkeeper"),
    ("position_df_231.mp4", "DEFEND", "Defender"),
    ("position_cm_231.mp4", "MIDFIELD", "Midfielder"),
    ("position_wing_231.mp4", "WING", "Winger"),
    ("position_st_231.mp4", "STRIKE", "Striker"),
)


def _title_from_name(filename: str) -> tuple[str, str]:
    stem = Path(filename).stem.replace("_", " ")
    return "CLIP", stem.title()


def list_videos() -> list[dict]:
    known = {name: (kicker, title) for name, kicker, title in CATALOG}
    found: list[dict] = []
    for name, kicker, title in CATALOG:
        path = VIDEO_DIR / name
        if path.is_file():
            found.append({"id": path.stem, "file": path, "kicker": kicker, "title": title})
    if VIDEO_DIR.is_dir():
        for path in sorted(VIDEO_DIR.glob("*.mp4")):
            if path.name in known:
                continue
            kicker, title = _title_from_name(path.name)
            found.append({"id": path.stem, "file": path, "kicker": kicker, "title": title})
    return found


def render_videos() -> None:
    st.markdown(
        """
        <div class="volt-card volt-lane">
          <span class="volt-node" aria-hidden="true"></span>
          <div>
            <p class="volt-kicker">WATCH</p>
            <h2>See it, then try it.</h2>
            <p>Skill clips and match moments. Use the fullscreen control on the player.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    clips = list_videos()
    if not clips:
        st.info("No clips yet. Add mp4 files to assets/videos.")
        return
    selected = st.session_state.get("video_id")
    if selected not in {clip["id"] for clip in clips}:
        selected = clips[0]["id"]
        st.session_state.video_id = selected
    columns = st.columns(3)
    for index, clip in enumerate(clips):
        with columns[index % 3]:
            if st.button(
                clip["title"],
                key=f"video_{clip['id']}",
                type="primary" if clip["id"] == selected else "secondary",
                width="stretch",
            ):
                st.session_state.video_id = clip["id"]
                st.rerun()
    current = next(clip for clip in clips if clip["id"] == st.session_state.video_id)
    st.markdown(
        f'<p class="volt-kicker volt-video-kicker">{escape(current["kicker"])}</p>',
        unsafe_allow_html=True,
    )
    st.video(str(current["file"]), format="video/mp4", autoplay=False)
