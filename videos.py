"""Clips shown on the Videos page. Drop new mp4 files in assets/videos."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from video_service import VIDEO_POINTS

VIDEO_DIR = Path(__file__).resolve().parent / "assets" / "videos"

CATALOG = (
    ("form_231.mp4", "FORM", "2-3-1 Formation"),
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


_WATCH_BRIDGE = """
<script>
const videoId = __VIDEO_ID__;
const parentDoc = window.parent.document;
const timer = window.setInterval(() => {
  const video = parentDoc.querySelector('video[data-testid="stVideo"]');
  const button = parentDoc.querySelector('[class*="st-key-video_watch_' + videoId + '"] button');
  if (!video || !button) return;
  if (video.dataset.voltWatch === videoId) return;
  video.dataset.voltWatch = videoId;
  const claim = () => {
    if (video.dataset.voltClaimed === videoId) return;
    const finished = video.ended || (video.duration && video.currentTime >= video.duration - 0.35);
    if (!finished) return;
    video.dataset.voltClaimed = videoId;
    button.click();
  };
  video.addEventListener("ended", claim);
  video.addEventListener("timeupdate", claim);
  claim();
  window.clearInterval(timer);
}, 400);
window.setTimeout(() => window.clearInterval(timer), 20000);
</script>
"""


def _watched_ids() -> set[str]:
    import app as hub

    try:
        data = hub.api_request("GET", "/me/videos/watched", token=st.session_state.token)
    except hub.ApiError:
        return set()
    return {str(video_id) for video_id in data.get("videoIds") or []}


def _claim_watch(video_id: str) -> bool:
    import app as hub

    try:
        result = hub.api_request("POST", f"/me/videos/{video_id}/watch", token=st.session_state.token)
    except hub.ApiError as exc:
        st.error(exc.message)
        return False
    if not result.get("awarded"):
        return False
    st.session_state.surge_bonus = int(result.get("points") or VIDEO_POINTS)
    st.session_state.coach_surge_open = True
    st.session_state.coach_surge_sound_played = False
    return True


def _watch_bridge(video_id: str) -> None:
    if st.button("Watched", key=f"video_watch_{video_id}"):
        if _claim_watch(video_id):
            st.rerun()
    with st.container(key="volt_watch_bridge"):
        components.html(_WATCH_BRIDGE.replace("__VIDEO_ID__", json.dumps(video_id)), height=0)


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
    watched = _watched_ids()
    st.markdown(
        f'<p class="volt-kicker volt-video-kicker">{escape(current["kicker"])}</p>',
        unsafe_allow_html=True,
    )
    if current["id"] not in watched:
        st.markdown(
            f'<p class="volt-sub">Watch it to the end. Charge +{VIDEO_POINTS} XP.</p>',
            unsafe_allow_html=True,
        )
    st.video(str(current["file"]), format="video/mp4", autoplay=False)
    if current["id"] not in watched:
        _watch_bridge(current["id"])
    from coach_ui import render_power_surge

    render_power_surge(st.session_state.user or {})
