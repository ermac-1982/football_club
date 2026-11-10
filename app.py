from __future__ import annotations

import os
import re
from html import escape
from pathlib import Path
from typing import Optional

from streamlit.elements.lib.image_utils import image_to_url
from streamlit.elements.lib.layout_utils import LayoutConfig

import requests
import streamlit as st
from dotenv import load_dotenv

from clubs_ui import render_club_badge, render_coach_club, render_join_club, render_leaderboard
from coach_ui import render_situational_coach
from videos import render_videos
from avatar_art import (
    PORTRAIT_BOOTS,
    PORTRAIT_HAIR_COLORS,
    PORTRAIT_HAIR_STYLES,
    PORTRAIT_SKINS,
    celebration_path,
    portrait_boots,
    portrait_hair_color,
    portrait_hair_style,
    portrait_path,
    portrait_skin,
)
from constants import (
    ACCOUNT_TYPES,
    AVATAR_BOOTS,
    AVATAR_GENDERS,
    AVATAR_HAIR,
    AVATAR_HAIR_STYLES,
    AVATAR_SKIN,
    GENERIC_AVATAR,
)

PLAYER_MENU = (
    "Situational Coach",
    "Videos",
    "Join club",
    "Daily Challenge",
    "Leaderboard",
)

PLAYER_MENU_ICONS = {
    "Situational Coach": ":material/sports_soccer:",
    "Videos": ":material/smart_display:",
    "Join club": ":material/groups:",
    "Daily Challenge": ":material/electric_bolt:",
    "Leaderboard": ":material/leaderboard:",
}

_PHONE_UA = re.compile(
    r"Android|iPhone|iPad|iPod|Mobile|IEMobile|Opera Mini|BlackBerry|webOS",
    re.IGNORECASE,
)


def _is_phone_client(user_agent: str, mobile_hint: str = "") -> bool:
    if (mobile_hint or "").strip() == "?1":
        return True
    return _PHONE_UA.search(user_agent or "") is not None


def viewing_on_phone() -> bool:
    """True when the browser identifies itself as a phone or tablet."""
    try:
        headers = st.context.headers
    except Exception:
        return False
    return _is_phone_client(
        headers.get("user-agent") or "",
        headers.get("sec-ch-ua-mobile") or "",
    )


def mark_phone() -> None:
    if viewing_on_phone():
        st.markdown('<div class="volt-phone"></div>', unsafe_allow_html=True)


PLAYER_SECTIONS = {
    "Situational Coach": (
        "THE MOMENT",
        "Coach the situation.",
        "Read what is happening, then pick the move that fits.",
    ),
    "Videos": (
        "WATCH",
        "See it, then try it.",
        "Skill clips and match moments sit in this lane.",
    ),
    "Join club": (
        "SQUAD",
        "Find your club.",
        "Search the clubs a coach has created, then join.",
    ),
    "Daily Challenge": (
        "TODAY",
        "One charge for today.",
        "A single task to power up your streak.",
    ),
    "Leaderboard": (
        "SQUAD",
        "Who is powered up.",
        "Charge ranks for players on your pitch.",
    ),
}

load_dotenv(Path(__file__).resolve().parent / ".env")


def api_base_url() -> str:
    explicit = os.environ.get("API_URL")
    if explicit:
        return explicit.rstrip("/")
    hostport = os.environ.get("API_HOSTPORT")
    if hostport:
        return f"http://{hostport}"
    return "http://127.0.0.1:8000"


API_URL = api_base_url()

AUTH_ERRORS = {
    "google_denied": "Google sign-in was cancelled.",
    "google_unverified": "That Google account does not have a verified email.",
    "google_failed": "Google sign-in failed. Try again.",
    "google_state": "Google sign-in expired. Try again.",
}


class ApiError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "Something went wrong. Try again."
    detail = body.get("detail", "Something went wrong. Try again.")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        messages = []
        for item in detail:
            if isinstance(item, dict) and item.get("msg"):
                messages.append(str(item["msg"]).removeprefix("Value error, "))
            else:
                messages.append("Check the form and try again.")
        return " ".join(messages) or "Check the form and try again."
    return "Something went wrong. Try again."


def api_request(method: str, path: str, payload: Optional[dict] = None, token: Optional[str] = None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method,
            f"{API_URL}{path}",
            json=payload,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise ApiError(
            "Could not reach the API. Start it with `uvicorn api:app --reload`."
        ) from exc
    if response.status_code >= 400:
        raise ApiError(error_message(response))
    if not response.content:
        return {}
    return response.json()


def init_state() -> None:
    defaults = {
        "token": None,
        "user": None,
        "auth_error": None,
        "auth_error_ready": False,
        "pending_email": None,
        "google_pending": None,
        "just_signed_in": False,
        "providers": None,
        "screen": "home",
        "avatar_notice": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_providers() -> dict:
    try:
        response = requests.get(f"{API_URL}/auth/providers", timeout=3)
        response.raise_for_status()
        data = response.json()
        data["api_down"] = False
        return data
    except requests.RequestException:
        return {"google": False, "email": True, "api_down": True}


def apply_session(data: dict) -> None:
    st.session_state.token = data["token"]
    st.session_state.user = data["user"]
    st.session_state.pending_email = None
    st.session_state.google_pending = None
    st.session_state.just_signed_in = True
    for key in ("finish_first_name", "finish_account_type"):
        st.session_state.pop(key, None)


def consume_handoff() -> None:
    code = st.query_params.get("auth_code")
    error = st.query_params.get("auth_error")
    if code is None and error is None:
        return
    if code:
        try:
            data = api_request("POST", "/auth/exchange", {"code": code})
        except ApiError as exc:
            st.session_state.auth_error = exc.message
        else:
            if data.get("kind") == "session":
                apply_session(data)
            elif data.get("kind") == "google_pending":
                st.session_state.token = None
                st.session_state.user = None
                st.session_state.google_pending = data
                st.session_state.pending_email = None
                st.session_state.finish_first_name = data.get("suggested_first_name") or ""
            else:
                st.session_state.auth_error = "Sign-in did not complete. Try again."
    if error:
        st.session_state.auth_error = AUTH_ERRORS.get(
            error, "Sign-in did not complete. Try again."
        )
    st.query_params.clear()


def inject_theme() -> None:
    css_path = Path(__file__).resolve().parent / "volt.css"
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def volt_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="volt-hero">
          <div class="volt-bolt" aria-hidden="true">⚡</div>
          <div>
            <p class="volt-kicker">VOLT PITCH</p>
            <h1>{escape(title)}</h1>
          </div>
        </div>
        <p class="volt-sub">{escape(subtitle)}</p>
        """,
        unsafe_allow_html=True,
    )


def _portrait(avatar: Optional[dict]) -> str:
    avatar = avatar or {}
    gender = (avatar.get("gender") or {}).get("id", "M")
    skin = (avatar.get("skin_color") or {}).get("id", "deep")
    hair = (avatar.get("hair_style") or {}).get("id", "curly")
    color = (avatar.get("hair_color") or {}).get("id", "black")
    boots = (avatar.get("boots_color") or {}).get("id", "black")
    return str(portrait_path(str(gender), str(skin), str(hair), str(color), str(boots)))


def player_card(user: dict) -> None:
    avatar = user.get("avatar") or {}
    nickname = avatar.get("nickname") or user["first_name"]
    name = escape(nickname)
    role = escape(user["account_type_label"])
    email = escape(user["email"])
    picture, details = st.columns([1, 1.35])
    with picture:
        if avatar:
            st.image(_portrait(avatar), use_container_width=True)
    with details:
        st.markdown(
            f"""
            <div class="volt-card volt-player">
              <div>
                <p class="volt-kicker">ON THE PITCH</p>
                <h2>Welcome, {name}</h2>
                <span class="volt-badge">{role}</span>
                <p class="volt-mail">{email}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _choice_id(avatar: Optional[dict], name: str, fallback: str) -> str:
    part = (avatar or {}).get(name) or {}
    if isinstance(part, dict) and part.get("id"):
        return str(part["id"])
    return fallback


def _sign_out() -> None:
    for key in ("token", "user", "pending_email", "google_pending", "just_signed_in", "avatar_notice"):
        st.session_state[key] = None if key != "just_signed_in" else False
    st.session_state.screen = "home"
    for key in (
        "nav_menu",
        "player_nav",
        "player_nav_seen",
        "avatar_menu_open",
        "coach_screen",
        "coach_section_id",
        "coach_scenario_id",
        "coach_feedback",
        "coach_nonce",
        "coach_handled",
        "player_nav_pending",
        "club_search",
        "club_create_name",
        "club_create_primary",
        "club_create_accent",
        "club_edit_name",
        "club_edit_primary",
        "club_edit_accent",
        "club_notice",
    ):
        st.session_state.pop(key, None)
    st.rerun()


def _player_nickname(user: dict) -> str:
    avatar = user.get("avatar") or {}
    return avatar.get("nickname") or user["first_name"]


def _portrait_url(avatar: Optional[dict]) -> str:
    path = Path(_portrait(avatar))
    return image_to_url(
        str(path),
        layout_config=LayoutConfig(width="content"),
        clamp=False,
        channels="RGB",
        output_format="auto",
        image_id=f"player-menu-{path.stem}",
    )


def _sync_player_menu(choice: str) -> None:
    previous = st.session_state.get("player_nav_seen")
    if previous is not None and choice != previous:
        st.session_state.avatar_menu_open = False
        if st.session_state.screen == "avatar":
            st.session_state.screen = "home"
            st.session_state.player_nav_seen = choice
            st.rerun()
    st.session_state.player_nav_seen = choice


def _avatar_actions() -> None:
    if not st.session_state.get("avatar_menu_open"):
        return
    if st.button("Modify avatar", type="primary", width="stretch", key="player_modify_avatar"):
        st.session_state.avatar_menu_open = False
        st.session_state.screen = "avatar"
        st.rerun()
    if st.button("Log out", width="stretch", key="player_log_out"):
        st.session_state.avatar_menu_open = False
        _sign_out()


def render_avatar_menu(user: dict, *, actions: bool = True) -> None:
    st.markdown('<div class="volt-account-slot"></div>', unsafe_allow_html=True)
    portrait = _portrait_url(user.get("avatar"))
    if st.button(f"![Your player]({portrait})", key="avatar_toggle"):
        st.session_state.avatar_menu_open = not st.session_state.get("avatar_menu_open", False)
        st.rerun()
    if actions:
        _avatar_actions()


def render_player_section(name: str) -> None:
    kicker, title, body = PLAYER_SECTIONS[name]
    st.markdown(
        f"""
        <div class="volt-card volt-lane">
          <span class="volt-node" aria-hidden="true"></span>
          <div>
            <p class="volt-kicker">{escape(kicker)}</p>
            <h2>{escape(title)}</h2>
            <p>{escape(body)}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _prepare_player_nav() -> None:
    pending = st.session_state.pop("player_nav_pending", None)
    if pending in PLAYER_MENU:
        st.session_state.player_nav = pending
        st.session_state.player_nav_seen = pending
    if st.session_state.get("player_nav") not in PLAYER_MENU:
        st.session_state.player_nav = PLAYER_MENU[0]
        st.session_state.player_nav_seen = PLAYER_MENU[0]


def _player_menu_radio() -> str:
    choice = st.radio(
        "Menu",
        PLAYER_MENU,
        format_func=lambda name: f"{PLAYER_MENU_ICONS[name]} {name}",
        label_visibility="collapsed",
        key="player_nav",
        width="stretch",
    )
    _sync_player_menu(choice)
    return choice


def _render_player_content(user: dict, choice: str) -> None:
    if st.session_state.avatar_notice:
        st.success(st.session_state.avatar_notice)
        st.session_state.avatar_notice = None
    if st.session_state.just_signed_in:
        st.success("You are on the pitch.")
        st.session_state.just_signed_in = False
    if st.session_state.screen == "avatar":
        render_avatar(user, first_time=False)
    elif choice == "Situational Coach":
        render_situational_coach(user)
    elif choice == "Videos":
        render_videos()
    elif choice == "Join club":
        render_join_club(user)
    elif choice == "Leaderboard":
        render_leaderboard(user)
    else:
        render_player_section(choice)


def _phone_bar(user: dict, play_menu: bool) -> str:
    if play_menu:
        _prepare_player_nav()
    brand, trigger = st.columns([1.45, 1], vertical_alignment="center")
    with brand:
        st.markdown(
            '<div class="volt-phone-bar"></div><p class="volt-kicker volt-phone-brand">VOLT PITCH</p>',
            unsafe_allow_html=True,
        )
    choice = st.session_state.get("player_nav", PLAYER_MENU[0]) if play_menu else ""
    with trigger:
        with st.popover("Menu", icon=":material/menu:", width="stretch"):
            st.markdown('<div class="volt-phone-sheet"></div>', unsafe_allow_html=True)
            nick = escape(_player_nickname(user))
            if play_menu:
                name_col, avatar_col = st.columns([1.7, 0.72], vertical_alignment="top")
                with name_col:
                    st.markdown(
                        f'<div class="volt-phone-head"></div><h2 class="volt-player-name">{nick}</h2>',
                        unsafe_allow_html=True,
                    )
                    render_club_badge()
                with avatar_col:
                    render_avatar_menu(user, actions=False)
                _avatar_actions()
                choice = _player_menu_radio()
            else:
                st.markdown(f'<h2 class="volt-player-name">{nick}</h2>', unsafe_allow_html=True)
                render_club_badge()
                if st.button("Log out", width="stretch", key="phone_log_out"):
                    _sign_out()
    return choice


def render_player(user: dict) -> None:
    st.markdown('<div class="volt-hub"></div>', unsafe_allow_html=True)
    if viewing_on_phone():
        choice = _phone_bar(user, play_menu=True)
        heading = "Modify avatar" if st.session_state.screen == "avatar" else choice
        st.markdown(
            f'<p class="volt-sub volt-phone-section">{escape(heading)}</p>',
            unsafe_allow_html=True,
        )
        _render_player_content(user, choice)
        return
    nav, stage = st.columns([1.2, 3.05], gap="medium")
    with nav:
        st.markdown('<div class="volt-nav"></div>', unsafe_allow_html=True)
        st.markdown('<p class="volt-kicker">VOLT PITCH</p>', unsafe_allow_html=True)
        st.markdown('<p class="volt-nav-label">Play</p>', unsafe_allow_html=True)
        _prepare_player_nav()
        choice = _player_menu_radio()
    with stage:
        nick = escape(_player_nickname(user))
        heading = "Modify avatar" if st.session_state.screen == "avatar" else choice
        copy, avatar_slot = st.columns([2.15, 1], vertical_alignment="top")
        with copy:
            st.markdown(
                f"""
                <p class="volt-kicker">ON THE PITCH</p>
                <h1 class="volt-player-name">{nick}</h1>
                <p class="volt-sub">{escape(heading)}</p>
                """,
                unsafe_allow_html=True,
            )
        with avatar_slot:
            render_avatar_menu(user)
        render_club_badge()
        _render_player_content(user, choice)


def render_sidebar(user: dict) -> None:
    avatar = user.get("avatar")
    labels = ["Home"]
    if user.get("account_type") == "player" and avatar:
        labels.append("My avatar")
    current = "My avatar" if st.session_state.screen == "avatar" and "My avatar" in labels else "Home"
    with st.sidebar:
        st.markdown('<p class="volt-kicker">VOLT PITCH</p>', unsafe_allow_html=True)
        picked = st.radio("Menu", labels, index=labels.index(current), key="nav_menu")
        if picked != current:
            st.session_state.screen = "avatar" if picked == "My avatar" else "home"
            st.rerun()
        st.caption(avatar.get("nickname") if avatar and avatar.get("nickname") else user["first_name"])
        if st.button("Log out", use_container_width=True):
            _sign_out()


def _clear_avatar_fields(user_id: str) -> None:
    for name in (
        "gender",
        "skin",
        "body",
        "hair_style",
        "hair",
        "kit_style",
        "kit_primary",
        "kit_accent",
        "boots",
        "nickname",
    ):
        st.session_state.pop(f"avatar_{name}_{user_id}", None)


def _option(catalog: dict, key: str, fallback: str) -> str:
    return key if key in catalog else fallback


def render_avatar(user: dict, first_time: bool) -> None:
    saved = user.get("avatar") or {}
    user_id = user["id"]
    if first_time:
        volt_header(
            "Build your player",
            "Pick a look. You can change it later from your player icon.",
        )
    else:
        st.caption("Pick a look. Save it when you are charged up.")
    skins = {key: AVATAR_SKIN[key] for key in PORTRAIT_SKINS}
    hair_styles = {key: AVATAR_HAIR_STYLES[key] for key in PORTRAIT_HAIR_STYLES}
    hair_colors = {key: AVATAR_HAIR[key] for key in PORTRAIT_HAIR_COLORS}
    boots_colors = {key: AVATAR_BOOTS[key] for key in PORTRAIT_BOOTS}
    defaults = {
        "gender": _choice_id(saved, "gender", GENERIC_AVATAR["gender"]),
        "skin": portrait_skin(_choice_id(saved, "skin_color", GENERIC_AVATAR["skin_color"])),
        "hair_style": portrait_hair_style(_choice_id(saved, "hair_style", GENERIC_AVATAR["hair_style"])),
        "hair": portrait_hair_color(_choice_id(saved, "hair_color", GENERIC_AVATAR["hair_color"])),
        "kit_style": _choice_id(saved, "kit_style", GENERIC_AVATAR["kit_style"]),
        "kit_primary": _choice_id(saved, "kit_primary", GENERIC_AVATAR["kit_primary"]),
        "kit_accent": _choice_id(saved, "kit_accent", GENERIC_AVATAR["kit_accent"]),
        "boots": portrait_boots(_choice_id(saved, "boots_color", GENERIC_AVATAR["boots_color"])),
        "nickname": saved.get("nickname") or user["first_name"][:20],
    }
    for name, catalog in (
        ("gender", AVATAR_GENDERS),
        ("skin", skins),
        ("hair_style", hair_styles),
        ("hair", hair_colors),
        ("boots", boots_colors),
    ):
        key = f"avatar_{name}_{user_id}"
        if st.session_state.get(key) not in catalog:
            st.session_state.pop(key, None)
    picked = {
        "gender": _option(AVATAR_GENDERS, st.session_state.get(f"avatar_gender_{user_id}", defaults["gender"]), defaults["gender"]),
        "skin": _option(skins, st.session_state.get(f"avatar_skin_{user_id}", defaults["skin"]), defaults["skin"]),
        "hair_style": _option(hair_styles, st.session_state.get(f"avatar_hair_style_{user_id}", defaults["hair_style"]), defaults["hair_style"]),
        "hair": _option(hair_colors, st.session_state.get(f"avatar_hair_{user_id}", defaults["hair"]), defaults["hair"]),
        "boots": _option(boots_colors, st.session_state.get(f"avatar_boots_{user_id}", defaults["boots"]), defaults["boots"]),
    }
    preview_col, _spacer = st.columns([1.1, 1])
    with preview_col:
        st.image(
            str(
                portrait_path(
                    picked["gender"],
                    picked["skin"],
                    picked["hair_style"],
                    picked["hair"],
                    picked["boots"],
                )
            ),
            use_container_width=True,
        )
    st.caption("Volt kit: black shirt and shorts, lime trim, cyan details. Every mix of these choices has its own player.")
    left, right = st.columns(2)
    with left:
        gender = st.selectbox(
            "Gender",
            list(AVATAR_GENDERS),
            index=list(AVATAR_GENDERS).index(defaults["gender"]),
            format_func=lambda key: AVATAR_GENDERS[key],
            key=f"avatar_gender_{user_id}",
        )
        skin = st.selectbox(
            "Skin colour",
            list(skins),
            index=list(skins).index(defaults["skin"]),
            format_func=lambda key: skins[key]["label"],
            key=f"avatar_skin_{user_id}",
        )
        hair_style = st.selectbox(
            "Hair style",
            list(hair_styles),
            index=list(hair_styles).index(defaults["hair_style"]),
            format_func=lambda key: hair_styles[key],
            key=f"avatar_hair_style_{user_id}",
        )
        hair = st.selectbox(
            "Hair colour",
            list(hair_colors),
            index=list(hair_colors).index(defaults["hair"]),
            format_func=lambda key: hair_colors[key]["label"],
            key=f"avatar_hair_{user_id}",
        )
    with right:
        boots = st.selectbox(
            "Boots colour",
            list(boots_colors),
            index=list(boots_colors).index(defaults["boots"]),
            format_func=lambda key: boots_colors[key]["label"],
            key=f"avatar_boots_{user_id}",
        )
    nick_key = f"avatar_nickname_{user_id}"
    if nick_key not in st.session_state:
        st.session_state[nick_key] = defaults["nickname"]
    nickname = st.text_input("Nickname", key=nick_key)
    if first_time:
        save_clicked = st.button("Save my look", type="primary")
        back_clicked = False
    else:
        save_col, back_col = st.columns(2)
        save_clicked = save_col.button("Save my look", type="primary", width="stretch")
        back_clicked = back_col.button("Back", width="stretch")
    if save_clicked:
        try:
            data = api_request(
                "PUT",
                "/me/avatar",
                {
                    "gender": gender,
                    "skin_color": skin,
                    "hair_style": hair_style,
                    "hair_color": hair,
                    "kit_style": "volt",
                    "kit_primary": "black",
                    "kit_accent": "lime",
                    "boots_color": boots,
                    "body_type": "lean",
                    "nickname": nickname,
                },
                token=st.session_state.token,
            )
        except ApiError as exc:
            st.error(exc.message)
            return
        st.session_state.user = data["user"]
        st.session_state.screen = "home"
        st.session_state.avatar_notice = "Your player is charged up."
        _clear_avatar_fields(user_id)
        st.rerun()
    if back_clicked:
        st.session_state.screen = "home"
        st.rerun()
    if first_time and st.button("Skip for now"):
        try:
            data = api_request("POST", "/me/avatar/skip", token=st.session_state.token)
        except ApiError as exc:
            st.error(exc.message)
            return
        st.session_state.user = data["user"]
        st.session_state.screen = "home"
        st.session_state.avatar_notice = "A starter player is ready. Change it any time from your player icon."
        _clear_avatar_fields(user_id)
        st.rerun()


def show_auth_error() -> None:
    message = st.session_state.auth_error
    if not message:
        return
    st.error(message)
    if st.session_state.auth_error_ready:
        st.session_state.auth_error = None
        st.session_state.auth_error_ready = False
    else:
        st.session_state.auth_error_ready = True


def google_section() -> None:
    providers = st.session_state.providers or {}
    if providers.get("api_down"):
        return
    st.divider()
    if providers.get("google"):
        st.link_button("Continue with Google", f"{API_URL}/auth/google/start")
    else:
        st.button("Continue with Google", disabled=True)
        st.caption(
            "Google sign-in needs GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env, "
            "then a restart of the API."
        )


def render_register() -> None:
    st.subheader("Create an account")
    st.caption("We store your first name, email, account type, and a user ID.")
    first_name = st.text_input("First name", key="register_first_name")
    email = st.text_input("Email", key="register_email")
    account_type = st.selectbox(
        "Account type",
        options=list(ACCOUNT_TYPES),
        format_func=lambda key: ACCOUNT_TYPES[key],
        index=None,
        placeholder="Choose Coach / Admin or Player",
        key="register_account_type",
    )
    password = st.text_input("Password", type="password", key="register_password")
    confirm_password = st.text_input(
        "Confirm password", type="password", key="register_password_confirm"
    )
    if st.button("Create account", type="primary"):
        if not first_name.strip():
            st.warning("Enter your first name.")
            return
        if not email.strip():
            st.warning("Enter your email.")
            return
        if not account_type:
            st.warning("Choose an account type.")
            return
        if len(password) < 8:
            st.warning("Use a password of at least 8 characters.")
            return
        if password != confirm_password:
            st.warning("Those passwords do not match.")
            return
        try:
            with st.spinner("Creating your account"):
                data = api_request(
                    "POST",
                    "/auth/register",
                    {
                        "email": email.strip(),
                        "first_name": first_name.strip(),
                        "account_type": account_type,
                        "password": password,
                    },
                )
        except ApiError as exc:
            st.error(exc.message)
            return
        apply_session(data)
        st.rerun()
    google_section()


def render_login() -> None:
    st.subheader("Log in")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Log in", type="primary"):
        if not email.strip():
            st.warning("Enter your email.")
            return
        if not password:
            st.warning("Enter your password.")
            return
        try:
            with st.spinner("Signing in"):
                data = api_request(
                    "POST",
                    "/auth/login",
                    {"email": email.strip(), "password": password},
                )
        except ApiError as exc:
            st.error(exc.message)
            return
        apply_session(data)
        st.rerun()
    google_section()


def render_google_finish() -> None:
    pending = st.session_state.google_pending
    st.subheader("Finish creating your account")
    st.write(f"Google account **{pending['email']}**")
    st.caption("This email comes from your Google account.")
    if "finish_first_name" not in st.session_state:
        st.session_state.finish_first_name = pending.get("suggested_first_name") or ""
    st.text_input("First name", key="finish_first_name")
    st.selectbox(
        "Account type",
        options=list(ACCOUNT_TYPES),
        format_func=lambda key: ACCOUNT_TYPES[key],
        index=None,
        placeholder="Choose Coach / Admin or Player",
        key="finish_account_type",
    )
    if st.button("Create account", type="primary"):
        first_name = (st.session_state.get("finish_first_name") or "").strip()
        account_type = st.session_state.get("finish_account_type")
        if not first_name:
            st.warning("Enter your first name.")
            return
        if not account_type:
            st.warning("Choose an account type.")
            return
        try:
            with st.spinner("Creating your account"):
                data = api_request(
                    "POST",
                    "/auth/google/complete",
                    {
                        "pending_token": pending["pending_token"],
                        "first_name": first_name,
                        "account_type": account_type,
                    },
                )
        except ApiError as exc:
            st.error(exc.message)
            return
        apply_session(data)
        st.rerun()
    if st.button("Cancel"):
        st.session_state.google_pending = None
        st.session_state.pop("finish_first_name", None)
        st.session_state.pop("finish_account_type", None)
        st.rerun()


def render_auth() -> None:
    volt_header("Football Club", "Register or log in with your email, or with Google.")
    if (st.session_state.providers or {}).get("api_down"):
        st.error("Could not reach the API. Start it with `uvicorn api:app --reload`.")
    show_auth_error()
    if st.session_state.google_pending:
        render_google_finish()
        return
    mode = st.radio("Account", ["Register", "Log in"], horizontal=True)
    if mode == "Register":
        render_register()
    else:
        render_login()


def render_home(user: dict) -> None:
    if viewing_on_phone():
        _phone_bar(user, play_menu=False)
        render_coach_club(user)
        return
    st.markdown('<div class="volt-with-nav"></div>', unsafe_allow_html=True)
    render_sidebar(user)
    volt_header("Football Club", "Build your club, then send players to the pitch.")
    player_card(user)
    render_coach_club(user)
    if st.session_state.avatar_notice:
        gender = ((user.get("avatar") or {}).get("gender") or {}).get("id", "M")
        celebrate, _rest = st.columns([1, 1.4])
        with celebrate:
            st.image(str(celebration_path(str(gender))), use_container_width=True)
        st.success(st.session_state.avatar_notice)
        st.session_state.avatar_notice = None
    if st.session_state.just_signed_in:
        st.success(f"You are signed in. Your user ID is {user['id']}.")
        st.session_state.just_signed_in = False
    st.subheader(f"Welcome, {user['first_name']}")
    st.write(f"**{user['account_type_label']}**")
    st.write(user["email"])
    st.caption("User ID")
    st.code(user["id"], language=None)

    if st.button("Say hello"):
        try:
            response = requests.get(f"{API_URL}/", timeout=30)
            response.raise_for_status()
            st.success(response.json().get("message", "Hello World"))
        except requests.RequestException as exc:
            st.error(
                "Could not reach the FastAPI server. "
                "Locally: `uvicorn api:app --reload`. On Render: wait for the API service to come up."
            )
            st.caption(str(exc))

    if st.button("Log out"):
        _sign_out()


def main() -> None:
    st.set_page_config(
        page_title="Volt Pitch",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()
    init_state()
    mark_phone()
    providers = st.session_state.providers
    if providers is None or providers.get("api_down"):
        st.session_state.providers = load_providers()
    consume_handoff()
    user = st.session_state.user if st.session_state.token else None
    if user and "needs_avatar" not in user:
        try:
            st.session_state.user = api_request("GET", "/auth/me", token=st.session_state.token)
            user = st.session_state.user
        except ApiError as exc:
            if exc.message == "Sign in required.":
                st.session_state.auth_error = exc.message
                _sign_out()
            st.error(exc.message)
    if user and user.get("needs_avatar"):
        render_avatar(user, first_time=True)
    elif user and user.get("account_type") == "player":
        render_player(user)
    elif user:
        render_home(user)
    else:
        render_auth()


if __name__ == "__main__":
    main()
