"""Coach club setup, player join, and the squad leaderboard."""

from __future__ import annotations

from html import escape
from urllib.parse import quote

import streamlit as st

from constants import CLUB_COLOURS

COLOURS = list(CLUB_COLOURS)


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    import app as hub

    return hub.api_request(method, path, payload, st.session_state.token)


def _api_error():
    import app as hub

    return hub.ApiError


def _colour_label(key: str) -> str:
    return CLUB_COLOURS[key]["label"]


def _strip(primary: dict, accent: dict) -> str:
    return (
        '<div class="volt-club-strip" aria-hidden="true">'
        f'<span style="background:{escape(primary["hex"])}"></span>'
        f'<span style="background:{escape(accent["hex"])}"></span>'
        "</div>"
    )


def _players_label(count: int) -> str:
    return "1 player" if count == 1 else f"{count} players"


def _club_card(club: dict, yours: bool = False) -> str:
    classes = "volt-card volt-club-card"
    if yours:
        classes += " volt-club-yours"
    return (
        f'<div class="{classes}">'
        f'{_strip(club["primary_color"], club["accent_color"])}'
        '<p class="volt-kicker">CLUB</p>'
        f'<h2>{escape(club["name"])}</h2>'
        f'<p>Coach {escape(club["coach_name"])} · {_players_label(int(club["player_count"]))}</p>'
        "</div>"
    )


def _portrait(avatar: dict | None) -> str:
    import app as hub

    try:
        url = hub._portrait_url(avatar)
    except Exception:
        return ""
    if not url:
        return ""
    return f'<img src="{escape(url)}" alt="">'


def _ranks_html(ranks: list[dict]) -> str:
    parts = []
    for row in ranks:
        rank = int(row["rank"])
        classes = "volt-rank"
        if rank <= 3:
            classes += f" volt-rank-{rank}"
        if row.get("you"):
            classes += " volt-rank-you"
        you = '<span class="volt-badge">You</span>' if row.get("you") else ""
        parts.append(
            f'<div class="{classes}">'
            f'<span class="volt-rank-num">{rank}</span>'
            f'{_portrait(row.get("avatar"))}'
            f'<div class="volt-rank-name"><strong>{escape(str(row["name"]))}</strong>{you}</div>'
            f'<span class="volt-rank-score">{int(row["score"]):,}</span>'
            "</div>"
        )
    return "".join(parts)


def _colour_picker(prefix: str, field: str, label: str, default: str) -> str:
    key = f"club_{prefix}_{field}"
    index = COLOURS.index(default) if default in COLOURS else 0
    return st.selectbox(label, COLOURS, index=index, format_func=_colour_label, key=key)


def _save_club(prefix: str, method: str, path: str, success: str) -> None:
    name = (st.session_state.get(f"club_{prefix}_name") or "").strip()
    if len(name) < 2:
        st.warning("Enter a club name.")
        return
    try:
        _api(
            method,
            path,
            {
                "name": name,
                "primary_color": st.session_state.get(f"club_{prefix}_primary"),
                "accent_color": st.session_state.get(f"club_{prefix}_accent"),
            },
        )
    except _api_error() as exc:
        st.error(exc.message)
        return
    st.session_state.club_notice = success
    st.rerun()


def _club_editor(prefix: str, button: str, method: str, path: str, club: dict | None, success: str) -> None:
    name_key = f"club_{prefix}_name"
    if club is not None and name_key not in st.session_state:
        st.session_state[name_key] = club["name"]
    primary_default = "black"
    accent_default = "lime"
    if club is not None:
        primary_default = (club.get("primary_color") or {}).get("id", primary_default)
        accent_default = (club.get("accent_color") or {}).get("id", accent_default)
    st.text_input("Club name", key=name_key, placeholder="Volt United")
    primary = _colour_picker(prefix, "primary", "Primary colour", primary_default)
    accent = _colour_picker(prefix, "accent", "Accent colour", accent_default)
    st.markdown(
        _strip(CLUB_COLOURS[primary], CLUB_COLOURS[accent]),
        unsafe_allow_html=True,
    )
    if st.button(button, type="primary", key=f"club_{prefix}_save"):
        _save_club(prefix, method, path, success)


def render_club_badge() -> None:
    try:
        club = _api("GET", "/me/club").get("club")
    except _api_error():
        return
    if not club:
        return
    st.markdown(
        '<div class="volt-club-badge">'
        f'{_strip(club["primary_color"], club["accent_color"])}'
        f'<span>{escape(club["name"])}</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def _show_notice() -> None:
    notice = st.session_state.get("club_notice")
    if notice:
        st.success(notice)
        st.session_state.club_notice = None


def render_coach_club(_user: dict) -> None:
    st.markdown(
        """
        <div class="volt-card volt-lane">
          <span class="volt-node" aria-hidden="true"></span>
          <div>
            <p class="volt-kicker">YOUR CLUB</p>
            <h2>Name it. Colour it.</h2>
            <p>Players search this list, join, and climb the squad ranks.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        club = _api("GET", "/me/club").get("club")
    except _api_error() as exc:
        st.error(exc.message)
        return
    _show_notice()
    if club is None:
        _club_editor("create", "Create club", "POST", "/clubs", None, "Your club is ready.")
        return
    st.markdown(_club_card(club, yours=True), unsafe_allow_html=True)
    st.markdown('<p class="volt-kicker">COLOURS</p>', unsafe_allow_html=True)
    _club_editor("edit", "Save club", "PATCH", "/clubs/mine", club, "Club saved.")
    st.markdown('<p class="volt-kicker">SQUAD</p>', unsafe_allow_html=True)
    render_leaderboard(_user)


def render_join_club(_user: dict) -> None:
    try:
        current = _api("GET", "/me/club").get("club")
    except _api_error() as exc:
        st.error(exc.message)
        return
    _show_notice()
    if current:
        st.markdown(_club_card(current, yours=True), unsafe_allow_html=True)
        if st.button("Leave club", key="club_leave"):
            try:
                _api("DELETE", "/me/club")
            except _api_error() as exc:
                st.error(exc.message)
            else:
                st.session_state.club_notice = "You left the club."
                st.rerun()
        st.caption("Joining another club moves you from this one.")
    query = st.text_input("Search clubs", key="club_search", placeholder="Type a club name")
    path = "/clubs" if not query.strip() else f"/clubs?q={quote(query.strip())}"
    try:
        clubs = _api("GET", path).get("clubs") or []
    except _api_error() as exc:
        st.error(exc.message)
        return
    if not clubs:
        message = "No clubs match that search." if query.strip() else "No clubs yet. A coach can create one."
        st.info(message)
        return
    if len(clubs) == 50:
        st.caption("Showing the first 50. Search to narrow the list.")
    current_id = current["id"] if current else None
    for club in clubs:
        info, action = st.columns([3.2, 1], vertical_alignment="center")
        with info:
            st.markdown(_club_card(club, yours=club["id"] == current_id), unsafe_allow_html=True)
        with action:
            if club["id"] == current_id:
                st.markdown('<p class="volt-club-yours-label">Your club</p>', unsafe_allow_html=True)
            elif st.button("Join", type="primary", key=f"join_{club['id']}"):
                try:
                    joined = _api("POST", f"/clubs/{club['id']}/join")
                except _api_error() as exc:
                    st.error(exc.message)
                else:
                    st.session_state.club_notice = f"You play for {joined['club']['name']}."
                    st.rerun()


def render_leaderboard(user: dict) -> None:
    try:
        data = _api("GET", "/me/club/leaderboard")
    except _api_error() as exc:
        if user.get("account_type") == "player" and exc.message == "Join a club to see the squad ranks.":
            st.markdown(
                """
                <div class="volt-card volt-lane">
                  <span class="volt-node" aria-hidden="true"></span>
                  <div>
                    <p class="volt-kicker">SQUAD</p>
                    <h2>Join a club first.</h2>
                    <p>The ranks are the players in your club, ordered by Situational Coach score.</p>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Join a club", type="primary", key="leaderboard_join"):
                st.session_state.player_nav_pending = "Join club"
                st.rerun()
            return
        if exc.message == "Create a club to see the squad ranks.":
            st.info("Create a club to see the squad ranks.")
            return
        st.error(exc.message)
        return
    ranks = data.get("ranks") or []
    if not ranks:
        st.info("No players have joined this club yet.")
        return
    st.caption("Ranked by Situational Coach score.")
    st.markdown(_ranks_html(ranks), unsafe_allow_html=True)
