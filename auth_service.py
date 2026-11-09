from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import settings
from constants import ACCOUNT_TYPES
from db import EmailCode, Handoff, Identity, User, utcnow

logger = logging.getLogger("football_club.auth")

SESSION_DAYS = 14
PASSWORD_ITERATIONS = 310_000


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class UnverifiedEmail(AuthError):
    def __init__(self) -> None:
        super().__init__(400, "That Google account does not have a verified email.")


def clean_first_name(value: str | None) -> str:
    cleaned = " ".join((value or "").split())
    if not cleaned:
        raise AuthError(400, "Enter your first name.")
    if len(cleaned) > 80:
        raise AuthError(400, "First name must be 80 characters or fewer.")
    if any(ord(char) < 32 for char in cleaned):
        raise AuthError(400, "First name contains invalid characters.")
    return cleaned


def normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise AuthError(400, "Use a password of at least 8 characters.")
    if len(password) > 128:
        raise AuthError(400, "Password must be 128 characters or fewer.")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        got = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, expected)


_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


def _hash_secret(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def _hashes_match(stored: str, presented: str) -> bool:
    if len(stored) != len(presented):
        return False
    return hmac.compare_digest(stored, presented)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def public_user(user: User) -> dict:
    from avatar_service import public_avatar

    created_at = user.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    avatar = public_avatar(user.avatar)
    return {
        "id": str(user.id),
        "first_name": user.first_name,
        "email": user.email,
        "account_type": user.account_type,
        "account_type_label": ACCOUNT_TYPES.get(user.account_type, user.account_type),
        "created_at": created_at.isoformat(),
        "avatar": avatar,
        "needs_avatar": user.account_type == "player" and avatar is None,
    }


def issue_session(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "typ": "session",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=SESSION_DAYS)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def session_payload(user: User) -> dict:
    return {"token": issue_session(user), "user": public_user(user)}


def _decode(token: str, expected_typ: str) -> dict:
    try:
        data = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(401, "Sign in required.") from exc
    if data.get("typ") != expected_typ:
        raise AuthError(401, "Sign in required.")
    return data


def user_from_session(db: Session, token: str) -> User:
    data = _decode(token, "session")
    try:
        user_id = uuid.UUID(str(data.get("sub")))
    except (TypeError, ValueError) as exc:
        raise AuthError(401, "Sign in required.") from exc
    user = db.get(User, user_id)
    if user is None:
        raise AuthError(401, "Sign in required.")
    return user


def _sweep_expired(db: Session) -> None:
    now = utcnow()
    db.query(EmailCode).filter(EmailCode.expires_at < now).delete(synchronize_session=False)
    db.query(Handoff).filter(Handoff.expires_at < now).delete(synchronize_session=False)


def register_account(
    db: Session,
    email: str,
    first_name: str,
    account_type: str,
    password: str,
) -> User:
    email = normalize_email(email)
    _validate_password(password)
    if db.query(User).filter(User.email == email).one_or_none():
        raise AuthError(409, "An account with this email already exists. Log in instead.")
    user = _create_user(db, first_name, email, account_type, hash_password(password))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError(409, "An account with this email already exists. Log in instead.") from exc
    db.refresh(user)
    return user


def login_with_password(db: Session, email: str, password: str) -> User:
    email = normalize_email(email)
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise AuthError(404, "No account for this email yet. Register first.")
    if not user.password_hash:
        uses_google = (
            db.query(Identity)
            .filter(Identity.user_id == user.id, Identity.provider == "google")
            .first()
        )
        if uses_google:
            raise AuthError(400, "This account uses Google sign-in.")
        raise AuthError(400, "This account has no password yet.")
    if not verify_password(password, user.password_hash):
        raise AuthError(401, "That password is incorrect.")
    return user


def _create_user(
    db: Session,
    first_name: str,
    email: str,
    account_type: str,
    password_hash: str | None = None,
) -> User:
    first_name = clean_first_name(first_name)
    email = normalize_email(email)
    if account_type not in ACCOUNT_TYPES:
        raise AuthError(400, "Choose an account type.")
    user = User(
        id=uuid.uuid4(),
        first_name=first_name,
        email=email,
        account_type=account_type,
        password_hash=password_hash,
    )
    db.add(user)
    db.flush()
    db.add(Identity(user_id=user.id, provider="email", provider_user_id=email))
    logger.info("allocated user id %s", user.id)
    return user


def _ensure_identity(db: Session, user: User, provider: str, provider_user_id: str) -> None:
    existing = (
        db.query(Identity)
        .filter(Identity.provider == provider, Identity.provider_user_id == provider_user_id)
        .one_or_none()
    )
    if existing:
        if existing.user_id != user.id:
            raise AuthError(409, "This sign-in method is already linked to another account.")
        return
    db.add(Identity(user_id=user.id, provider=provider, provider_user_id=provider_user_id))


def _find_google_user(db: Session, google_sub: str, email: str) -> User | None:
    identity = (
        db.query(Identity)
        .filter(Identity.provider == "google", Identity.provider_user_id == google_sub)
        .one_or_none()
    )
    if identity is not None:
        return identity.user
    return db.query(User).filter(User.email == email).one_or_none()


def _create_handoff(db: Session, kind: str, payload: dict) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(
        Handoff(
            code_hash=_hash_secret(raw),
            kind=kind,
            payload=payload,
            expires_at=utcnow() + timedelta(minutes=5),
        )
    )
    db.commit()
    return raw


def exchange_handoff(db: Session, code: str) -> dict:
    row = db.query(Handoff).filter(Handoff.code_hash == _hash_secret(code)).one_or_none()
    now = utcnow()
    if row is None or row.used_at is not None:
        raise AuthError(400, "That sign-in link has expired. Try again.")
    if _aware(row.expires_at) < now:
        raise AuthError(400, "That sign-in link has expired. Try again.")

    kind = row.kind
    payload = dict(row.payload or {})
    row.used_at = now
    db.commit()

    if kind == "session":
        try:
            user = db.get(User, uuid.UUID(str(payload.get("user_id"))))
        except (TypeError, ValueError):
            user = None
        if user is None:
            raise AuthError(400, "That sign-in link has expired. Try again.")
        return {"kind": "session", **session_payload(user)}

    if kind == "google_pending":
        email = str(payload.get("email") or "")
        google_sub = str(payload.get("google_sub") or "")
        if not email or not google_sub:
            raise AuthError(400, "That sign-in link has expired. Try again.")
        pending = jwt.encode(
            {
                "typ": "google_pending",
                "email": email,
                "google_sub": google_sub,
                "exp": int((now + timedelta(minutes=15)).timestamp()),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        return {
            "kind": "google_pending",
            "pending_token": pending,
            "email": email,
            "suggested_first_name": str(payload.get("suggested_first_name") or ""),
        }

    raise AuthError(400, "That sign-in link has expired. Try again.")


def google_authorize_url() -> str:
    if not settings.google_enabled():
        raise AuthError(503, "Google sign-in is not configured.")
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    nonce = secrets.token_urlsafe(16)
    state = jwt.encode(
        {
            "typ": "google_state",
            "verifier": verifier,
            "nonce": nonce,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def _suggested_name(info: dict) -> str:
    raw = info.get("given_name") or ""
    if not raw and info.get("name"):
        raw = str(info["name"]).split(" ")[0]
    try:
        return clean_first_name(str(raw))
    except AuthError:
        return ""


def finish_google(db: Session, code: str, state: str) -> str:
    try:
        state_data = jwt.decode(
            state,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(401, "Google sign-in expired. Try again.") from exc
    if state_data.get("typ") != "google_state":
        raise AuthError(401, "Google sign-in expired. Try again.")

    try:
        token_response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.google_redirect_uri(),
                "grant_type": "authorization_code",
                "code_verifier": state_data.get("verifier"),
            },
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        raise AuthError(502, "Google sign-in failed. Try again.") from exc
    if token_response.status_code != 200:
        logger.info("google token exchange failed status=%s", token_response.status_code)
        raise AuthError(502, "Google sign-in failed. Try again.")

    raw_id_token = token_response.json().get("id_token")
    if not raw_id_token:
        raise AuthError(502, "Google sign-in failed. Try again.")
    try:
        info = id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise AuthError(502, "Google sign-in failed. Try again.") from exc

    if info.get("nonce") != state_data.get("nonce"):
        raise AuthError(401, "Google sign-in expired. Try again.")

    verified = info.get("email_verified")
    email = normalize_email(str(info.get("email") or ""))
    google_sub = str(info.get("sub") or "")
    if not email or not google_sub or verified not in (True, "true"):
        raise UnverifiedEmail()

    user = _find_google_user(db, google_sub, email)
    if user is not None:
        _ensure_identity(db, user, "google", google_sub)
        _ensure_identity(db, user, "email", user.email)
        db.commit()
        return _create_handoff(db, "session", {"user_id": str(user.id)})

    return _create_handoff(
        db,
        "google_pending",
        {
            "email": email,
            "google_sub": google_sub,
            "suggested_first_name": _suggested_name(info),
        },
    )


def complete_google(db: Session, pending_token: str, first_name: str, account_type: str) -> User:
    data = _decode(pending_token, "google_pending")
    email = normalize_email(str(data.get("email") or ""))
    google_sub = str(data.get("google_sub") or "")
    if not email or not google_sub:
        raise AuthError(401, "Sign in required.")

    user = _find_google_user(db, google_sub, email)
    if user is None:
        user = _create_user(db, first_name, email, account_type)
        db.add(Identity(user_id=user.id, provider="google", provider_user_id=google_sub))
    else:
        _ensure_identity(db, user, "google", google_sub)
        _ensure_identity(db, user, "email", user.email)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        user = _find_google_user(db, google_sub, email)
        if user is None:
            raise AuthError(409, "An account with this email already exists. Log in instead.") from exc
        _ensure_identity(db, user, "google", google_sub)
        _ensure_identity(db, user, "email", user.email)
        db.commit()
    db.refresh(user)
    return user
