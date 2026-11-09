from __future__ import annotations

import logging
import warnings
from contextlib import asynccontextmanager
from html import escape
import uuid
from typing import Annotated, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

warnings.filterwarnings("ignore", category=FutureWarning, module=r"google\.(auth|oauth2)")

import settings
from auth_service import (
    AuthError,
    UnverifiedEmail,
    complete_google,
    exchange_handoff,
    finish_google,
    google_authorize_url,
    public_user,
    login_with_password,
    register_account,
    session_payload,
    user_from_session,
)
from avatar_service import save_avatar, skip_avatar
from club_service import (
    ClubError,
    club_for,
    create_club,
    join_club,
    leaderboard,
    leave_club,
    search_clubs,
    update_club,
)
from coach_service import CoachError, answer_scenario, path_for, scenario_for
from constants import ACCOUNT_TYPES
from db import engine, get_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("football_club")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Football Club", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    first_name: str
    account_type: Literal["coach_admin", "player"]
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.strip().lower()


class ExchangeRequest(BaseModel):
    code: str


class GoogleCompleteRequest(BaseModel):
    pending_token: str
    first_name: str
    account_type: Literal["coach_admin", "player"]


class AvatarRequest(BaseModel):
    gender: str
    skin_color: str
    hair_style: str
    hair_color: str
    kit_style: str
    kit_primary: str
    kit_accent: str
    boots_color: str
    body_type: str
    nickname: str


def _auth_http(exc: AuthError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Sign in required.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Sign in required.")
    try:
        return user_from_session(db, token.strip())
    except AuthError as exc:
        raise _auth_http(exc) from exc


def _app_redirect(**params: str) -> RedirectResponse:
    from urllib.parse import urlencode

    query = urlencode(params)
    target = settings.APP_URL + (f"?{query}" if query else "")
    return RedirectResponse(target, status_code=302)


@app.get("/")
def hello() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("database health check failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


@app.get("/auth/providers")
def providers() -> dict[str, bool]:
    return {
        "google": settings.google_enabled(),
        "email": True,
    }


@app.post("/auth/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user = register_account(db, body.email, body.first_name, body.account_type, body.password)
    except AuthError as exc:
        raise _auth_http(exc) from exc
    return session_payload(user)


@app.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user = login_with_password(db, body.email, body.password)
    except AuthError as exc:
        raise _auth_http(exc) from exc
    return session_payload(user)


@app.post("/auth/exchange")
def exchange(body: ExchangeRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return exchange_handoff(db, body.code.strip())
    except AuthError as exc:
        raise _auth_http(exc) from exc


@app.get("/auth/google/start")
def google_start():
    if not settings.google_enabled():
        back = escape(settings.APP_URL)
        return HTMLResponse(
            "<!doctype html><html><head><meta charset='utf-8'><title>Volt Pitch</title>"
            "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=Poppins:wght@700&family=Nunito:wght@600&display=swap'>"
            "<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0D1117;color:#fff;"
            "font-family:Nunito,Segoe UI,sans-serif}main{background:#161B22;border:1px solid #2A2F36;border-radius:24px;"
            "padding:2rem;box-shadow:0 0 24px rgba(57,255,20,.2)}h1{font-family:Poppins,Segoe UI,sans-serif;margin:0 0 .5rem}"
            "a{color:#FF6B00;font-weight:700}</style></head><body><main>"
            "<h1>Volt Pitch</h1><p>Google sign-in is not configured yet.</p>"
            f"<p><a href='{back}'>Back to Football Club</a></p></main></body></html>",
            status_code=503,
        )
    try:
        return RedirectResponse(google_authorize_url(), status_code=302)
    except AuthError as exc:
        raise _auth_http(exc) from exc


@app.get("/auth/google/callback")
def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if error:
        return _app_redirect(auth_error="google_denied")
    if not code or not state:
        return _app_redirect(auth_error="google_failed")
    try:
        handoff = finish_google(db, code, state)
    except UnverifiedEmail:
        return _app_redirect(auth_error="google_unverified")
    except AuthError as exc:
        logger.info("google callback rejected: %s", exc.detail)
        error_code = "google_state" if exc.status_code == 401 else "google_failed"
        return _app_redirect(auth_error=error_code)
    except Exception:
        logger.exception("google callback failed")
        return _app_redirect(auth_error="google_failed")
    return _app_redirect(auth_code=handoff)


@app.post("/auth/google/complete")
def google_complete(body: GoogleCompleteRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user = complete_google(db, body.pending_token, body.first_name, body.account_type)
    except AuthError as exc:
        raise _auth_http(exc) from exc
    return session_payload(user)


@app.get("/auth/me")
def me(user=Depends(get_current_user)) -> dict:
    return public_user(user)


@app.put("/me/avatar")
def put_avatar(
    body: AvatarRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        saved = save_avatar(db, user, body.model_dump())
    except AuthError as exc:
        raise _auth_http(exc) from exc
    return {"user": public_user(saved)}


@app.post("/me/avatar/skip")
def post_avatar_skip(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        saved = skip_avatar(db, user)
    except AuthError as exc:
        raise _auth_http(exc) from exc
    return {"user": public_user(saved)}


@app.get("/auth/account-types")
def account_types() -> dict[str, str]:
    return ACCOUNT_TYPES


class ClubBody(BaseModel):
    name: str
    primary_color: str
    accent_color: str


def _club_http(exc: ClubError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@app.post("/clubs")
def post_club(
    body: ClubBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        club = create_club(db, user, body.name, body.primary_color, body.accent_color)
    except ClubError as exc:
        raise _club_http(exc) from exc
    return {"club": club}


@app.patch("/clubs/mine")
def patch_club(
    body: ClubBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        club = update_club(db, user, body.name, body.primary_color, body.accent_color)
    except ClubError as exc:
        raise _club_http(exc) from exc
    return {"club": club}


@app.get("/clubs")
def get_clubs(
    q: str = "",
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"clubs": search_clubs(db, q)}


@app.post("/clubs/{club_id}/join")
def post_join_club(
    club_id: uuid.UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        club = join_club(db, user, club_id)
    except ClubError as exc:
        raise _club_http(exc) from exc
    return {"club": club}


@app.get("/me/club")
def get_my_club(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"club": club_for(db, user)}


@app.delete("/me/club")
def delete_my_club(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        leave_club(db, user)
    except ClubError as exc:
        raise _club_http(exc) from exc
    return {"club": None}


@app.get("/me/club/leaderboard")
def get_my_leaderboard(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        return leaderboard(db, user)
    except ClubError as exc:
        raise _club_http(exc) from exc


class CoachAnswerBody(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    action: Optional[Literal["pass", "dribble", "shoot"]] = None
    targetPlayerId: Optional[str] = None


def _coach_http(exc: CoachError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@app.get("/coach/path")
def coach_path(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return path_for(db, user)


@app.get("/coach/scenarios/{scenario_id}")
def coach_scenario(
    scenario_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return scenario_for(db, user, scenario_id)
    except CoachError as exc:
        raise _coach_http(exc) from exc


@app.post("/coach/scenarios/{scenario_id}/answer")
def coach_answer(
    scenario_id: int,
    body: CoachAnswerBody,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return answer_scenario(db, user, scenario_id, body.model_dump(exclude_none=True))
    except CoachError as exc:
        raise _coach_http(exc) from exc
