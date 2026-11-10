from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
PRODUCTION = APP_ENV == "production"
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
APP_URL = os.getenv("APP_URL", "http://localhost:8501").rstrip("/")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "Football Club <noreply@localhost>").strip()

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres").strip() or "postgres"
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost").strip() or "localhost"
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432").strip() or "5432"
POSTGRES_DB = os.getenv("POSTGRES_DB", "football_club").strip() or "football_club"
EXPLICIT_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def _smtp_use_tls() -> bool:
    raw = os.getenv("SMTP_USE_TLS")
    if raw is None or raw.strip() == "":
        return SMTP_PORT != 465
    return raw.strip().lower() in {"1", "true", "yes", "on"}


SMTP_USE_TLS = _smtp_use_tls()


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def database_url() -> str:
    if EXPLICIT_DATABASE_URL:
        return normalize_database_url(EXPLICIT_DATABASE_URL)
    user = quote_plus(POSTGRES_USER)
    host = f"{POSTGRES_HOST}:{POSTGRES_PORT}"
    if POSTGRES_PASSWORD:
        auth = f"{user}:{quote_plus(POSTGRES_PASSWORD)}"
    else:
        auth = user
    return f"postgresql+psycopg://{auth}@{host}/{POSTGRES_DB}"


def database_name() -> str:
    url = database_url().split("?", 1)[0]
    name = url.rsplit("/", 1)[-1]
    return name or POSTGRES_DB


def allowed_origins() -> list[str]:
    origins = {APP_URL}
    if not PRODUCTION:
        origins.update({"http://localhost:8501", "http://127.0.0.1:8501"})
    return sorted(origins)


def google_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def google_redirect_uri() -> str:
    explicit = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if explicit:
        return explicit
    external = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if external:
        return f"{external}/auth/google/callback"
    return "http://127.0.0.1:8000/auth/google/callback"


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM)


def validate() -> None:
    if len(SECRET_KEY) < 32:
        raise RuntimeError(
            "Set SECRET_KEY in .env to a random string of at least 32 characters."
        )
    if not APP_URL.startswith(("http://", "https://")):
        raise RuntimeError("APP_URL must start with http:// or https://")
    if not EXPLICIT_DATABASE_URL and not POSTGRES_PASSWORD:
        raise RuntimeError(
            "Local Postgres requires a password. Set POSTGRES_PASSWORD in .env "
            f"for user '{POSTGRES_USER}' and database '{POSTGRES_DB}'."
        )
