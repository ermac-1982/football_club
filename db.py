import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

import settings

settings.validate()

engine = create_engine(
    settings.database_url(),
    pool_pre_ping=True,
    connect_args={"application_name": "football_club"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('coach_admin', 'player')",
            name="ck_users_account_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    identities: Mapped[list["Identity"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    avatar: Mapped[Optional["PlayerAvatar"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    owned_club: Mapped[Optional["Club"]] = relationship(
        back_populates="coach",
        cascade="all, delete-orphan",
        uselist=False,
    )
    membership: Mapped[Optional["ClubMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Identity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_identity_provider"),
        CheckConstraint("provider IN ('email', 'google')", name="ck_identity_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="identities")


class EmailCode(Base):
    __tablename__ = "email_login_codes"
    __table_args__ = (
        CheckConstraint("purpose IN ('register', 'login')", name="ck_email_code_purpose"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(80))
    account_type: Mapped[Optional[str]] = mapped_column(String(32))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class PlayerAvatar(Base):
    __tablename__ = "player_avatars"
    __table_args__ = (
        CheckConstraint("gender IN ('M', 'F')", name="ck_avatar_gender"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    gender: Mapped[str] = mapped_column(String(1), nullable=False)
    skin_color: Mapped[str] = mapped_column(String(32), nullable=False)
    kit_primary: Mapped[str] = mapped_column("kit_color", String(32), nullable=False)
    kit_accent: Mapped[str] = mapped_column(String(32), nullable=False, default="lime")
    kit_style: Mapped[str] = mapped_column(String(32), nullable=False, default="volt")
    boots_color: Mapped[str] = mapped_column(String(32), nullable=False)
    hair_style: Mapped[str] = mapped_column(String(32), nullable=False, default="curly")
    hair_color: Mapped[str] = mapped_column(String(32), nullable=False)
    body_type: Mapped[str] = mapped_column(String(32), nullable=False)
    nickname: Mapped[str] = mapped_column(String(20), nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="avatar")


class CoachAttempt(Base):
    __tablename__ = "coach_attempts"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_coach_attempt_score"),
        CheckConstraint(
            "result IN ('correct', 'partial', 'incorrect')",
            name="ck_coach_attempt_result",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class Club(Base):
    """A coach's squad. Players join one club at a time."""

    __tablename__ = "clubs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    name_key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    primary_color: Mapped[str] = mapped_column(String(32), nullable=False)
    accent_color: Mapped[str] = mapped_column(String(32), nullable=False)
    coach_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    coach: Mapped["User"] = relationship(back_populates="owned_club")
    members: Mapped[list["ClubMember"]] = relationship(back_populates="club", cascade="all, delete-orphan")


class ClubMember(Base):
    __tablename__ = "club_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    club_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="membership")
    club: Mapped["Club"] = relationship(back_populates="members")


class Handoff(Base):
    """One-time code that moves a finished API login back into the Streamlit app."""

    __tablename__ = "auth_handoffs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


REQUIRED_COLUMNS = {
    "users": {"id", "first_name", "email", "password_hash", "account_type", "created_at"},
    "auth_identities": {"id", "user_id", "provider", "provider_user_id", "created_at"},
    "email_login_codes": {
        "id",
        "email",
        "code_hash",
        "purpose",
        "expires_at",
        "attempts",
        "password_hash",
    },
    "auth_handoffs": {"id", "code_hash", "kind", "payload", "expires_at"},
    "player_avatars": {
        "user_id",
        "gender",
        "skin_color",
        "kit_color",
        "kit_accent",
        "kit_style",
        "boots_color",
        "hair_style",
        "hair_color",
        "body_type",
        "nickname",
        "is_custom",
        "created_at",
        "updated_at",
    },
    "coach_attempts": {"id", "user_id", "scenario_id", "score", "result", "created_at"},
    "clubs": {"id", "name", "name_key", "primary_color", "accent_color", "coach_id", "created_at"},
    "club_members": {"user_id", "club_id", "joined_at"},
}

COLUMN_ADDITIONS = {
    "users": {"password_hash": "VARCHAR(255)"},
    "email_login_codes": {"password_hash": "VARCHAR(255)"},
    "player_avatars": {
        "hair_style": "VARCHAR(32) NOT NULL DEFAULT 'curly'",
        "kit_style": "VARCHAR(32) NOT NULL DEFAULT 'volt'",
        "kit_accent": "VARCHAR(32) NOT NULL DEFAULT 'lime'",
    },
}


def init_db() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        inspector = inspect(engine)
        with engine.begin() as connection:
            for table, columns in COLUMN_ADDITIONS.items():
                if not inspector.has_table(table):
                    continue
                present = {column["name"] for column in inspector.get_columns(table)}
                for name, column_type in columns.items():
                    if name not in present:
                        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}"))
        inspector = inspect(engine)
        for table, columns in REQUIRED_COLUMNS.items():
            if not inspector.has_table(table):
                continue
            present = {column["name"] for column in inspector.get_columns(table)}
            missing = columns - present
            if missing:
                raise RuntimeError(
                    f"Table '{table}' already exists in database '{settings.database_name()}' "
                    f"but is missing columns: {', '.join(sorted(missing))}. "
                    "Rename that table so the app can create its own."
                )
        Base.metadata.create_all(engine)
    except OperationalError as exc:
        raise RuntimeError(
            "Could not connect to PostgreSQL. Check POSTGRES_PASSWORD in .env "
            f"for user '{settings.POSTGRES_USER}' and database '{settings.database_name()}' "
            f"on {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}."
        ) from exc


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
