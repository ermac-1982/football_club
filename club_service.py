"""Clubs created by coaches, joined by players, ranked by Situational Coach score."""

from __future__ import annotations

import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from avatar_service import public_avatar
from coach_engine import total_score
from constants import CLUB_COLOURS
from db import Club, ClubMember, CoachAttempt, User, utcnow

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 '\-]*$")


class ClubError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def clean_club_name(value: str) -> str:
    cleaned = " ".join((value or "").split())
    if len(cleaned) < 2 or len(cleaned) > 40:
        raise ClubError(400, "Club name needs 2 to 40 characters.")
    if _NAME.fullmatch(cleaned) is None:
        raise ClubError(400, "Use letters, numbers, spaces, apostrophes, or hyphens.")
    return cleaned


def ordered_ranks(entries: list[dict]) -> list[dict]:
    """Highest score first. Equal scores share a rank, then names break the tie."""
    ordered = sorted(entries, key=lambda row: (-int(row["score"]), row["name"].casefold(), row["user_id"]))
    ranked = []
    last_score = None
    last_rank = 0
    for index, row in enumerate(ordered, start=1):
        rank = last_rank if row["score"] == last_score else index
        last_score = row["score"]
        last_rank = rank
        ranked.append({**row, "rank": rank})
    return ranked


def _colour(key: str, label: str) -> str:
    if key not in CLUB_COLOURS:
        raise ClubError(400, f"Choose a {label}.")
    return key


def _swatch(key: str) -> dict:
    chosen = key if key in CLUB_COLOURS else next(iter(CLUB_COLOURS))
    item = CLUB_COLOURS[chosen]
    return {"id": chosen, "label": item["label"], "hex": item["hex"]}


def _counts(db: Session, club_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not club_ids:
        return {}
    rows = (
        db.query(ClubMember.club_id, ClubMember.user_id)
        .filter(ClubMember.club_id.in_(club_ids))
        .all()
    )
    counts: dict[uuid.UUID, int] = {}
    for club_id, _user_id in rows:
        counts[club_id] = counts.get(club_id, 0) + 1
    return counts


def public_club(club: Club, player_count: int) -> dict:
    coach_name = club.coach.first_name if club.coach is not None else ""
    return {
        "id": str(club.id),
        "name": club.name,
        "primary_color": _swatch(club.primary_color),
        "accent_color": _swatch(club.accent_color),
        "coach_name": coach_name,
        "player_count": player_count,
    }


def _as_public(db: Session, club: Club) -> dict:
    count = _counts(db, [club.id]).get(club.id, 0)
    return public_club(club, count)


def _coaches_only(user: User) -> None:
    if user.account_type != "coach_admin":
        raise ClubError(403, "Only a coach can create a club.")


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def create_club(db: Session, user: User, name: str, primary_color: str, accent_color: str) -> dict:
    _coaches_only(user)
    if user.owned_club is not None:
        raise ClubError(409, "You already created a club.")
    cleaned = clean_club_name(name)
    club = Club(
        name=cleaned,
        name_key=cleaned.casefold(),
        primary_color=_colour(primary_color, "primary colour"),
        accent_color=_colour(accent_color, "accent colour"),
        coach_id=user.id,
    )
    db.add(club)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        detail = str(getattr(exc, "orig", exc)).lower()
        if "coach" in detail:
            raise ClubError(409, "You already created a club.") from exc
        raise ClubError(409, "A club already has that name.") from exc
    db.refresh(club)
    db.expire(user, ["owned_club"])
    return _as_public(db, club)


def update_club(db: Session, user: User, name: str, primary_color: str, accent_color: str) -> dict:
    _coaches_only(user)
    club = user.owned_club
    if club is None:
        raise ClubError(404, "Create a club first.")
    club.name = clean_club_name(name)
    club.name_key = club.name.casefold()
    club.primary_color = _colour(primary_color, "primary colour")
    club.accent_color = _colour(accent_color, "accent colour")
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ClubError(409, "A club already has that name.") from exc
    db.refresh(club)
    return _as_public(db, club)


def club_for(db: Session, user: User) -> dict | None:
    if user.account_type == "coach_admin":
        club = user.owned_club
    elif user.account_type == "player" and user.membership is not None:
        club = user.membership.club
    else:
        club = None
    if club is None:
        return None
    return _as_public(db, club)


def search_clubs(db: Session, query: str) -> list[dict]:
    words = " ".join((query or "").split())
    stmt = db.query(Club)
    if words:
        stmt = stmt.filter(Club.name.ilike(_like(words), escape="\\"))
    clubs = stmt.order_by(Club.name).limit(50).all()
    counts = _counts(db, [club.id for club in clubs])
    return [public_club(club, counts.get(club.id, 0)) for club in clubs]


def join_club(db: Session, user: User, club_id: uuid.UUID) -> dict:
    if user.account_type != "player":
        raise ClubError(403, "Only a player can join a club.")
    club = db.get(Club, club_id)
    if club is None:
        raise ClubError(404, "That club does not exist.")
    member = user.membership
    if member is None:
        db.add(ClubMember(user_id=user.id, club_id=club.id, joined_at=utcnow()))
    else:
        member.club_id = club.id
        member.joined_at = utcnow()
    db.commit()
    db.expire(user, ["membership"])
    db.refresh(club)
    return _as_public(db, club)


def leave_club(db: Session, user: User) -> None:
    if user.account_type != "player":
        raise ClubError(403, "Only a player can leave a club.")
    member = user.membership
    if member is None:
        raise ClubError(404, "You are not in a club.")
    db.delete(member)
    db.commit()
    db.expire(user, ["membership"])


def _squad(db: Session, club: Club, viewer_id: uuid.UUID) -> dict:
    members = (
        db.query(User)
        .options(joinedload(User.avatar))
        .join(ClubMember, ClubMember.user_id == User.id)
        .filter(ClubMember.club_id == club.id, User.account_type == "player")
        .all()
    )
    by_user: dict[uuid.UUID, dict[int, list[int]]] = {member.id: {} for member in members}
    if by_user:
        attempts = db.query(CoachAttempt).filter(CoachAttempt.user_id.in_(list(by_user))).all()
        for attempt in attempts:
            by_user.setdefault(attempt.user_id, {}).setdefault(attempt.scenario_id, []).append(attempt.score)
    entries = []
    for member in members:
        avatar = public_avatar(member.avatar)
        entries.append(
            {
                "user_id": str(member.id),
                "name": (avatar or {}).get("nickname") or member.first_name,
                "score": total_score(by_user.get(member.id) or {}),
                "avatar": avatar,
                "you": member.id == viewer_id,
            }
        )
    return {"club": _as_public(db, club), "ranks": ordered_ranks(entries)}


def leaderboard(db: Session, user: User) -> dict:
    if user.account_type == "coach_admin" and user.owned_club is not None:
        return _squad(db, user.owned_club, user.id)
    if user.account_type == "player" and user.membership is not None:
        return _squad(db, user.membership.club, user.id)
    if user.account_type == "coach_admin":
        raise ClubError(404, "Create a club to see the squad ranks.")
    raise ClubError(404, "Join a club to see the squad ranks.")
