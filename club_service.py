"""Clubs created by coaches, joined by players, ranked by coaching and clip scores."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from avatar_service import public_avatar
from coach_engine import total_score
from constants import CLUB_COLOURS
from db import Club, ClubMember, CoachAttempt, PositionAttempt, RefreshToken, User, VideoWatch, utcnow
from position_engine import total_score as quiz_score
from video_service import points_by_user

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


def _members(db: Session, club: Club) -> list[User]:
    return (
        db.query(User)
        .options(joinedload(User.avatar))
        .join(ClubMember, ClubMember.user_id == User.id)
        .filter(ClubMember.club_id == club.id, User.account_type == "player")
        .all()
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _attempt_maps(
    db: Session, user_ids: list[uuid.UUID]
) -> tuple[dict[uuid.UUID, dict[int, list[int]]], dict[uuid.UUID, dict[int, list[int]]], dict[uuid.UUID, int], dict[uuid.UUID, int]]:
    coach: dict[uuid.UUID, dict[int, list[int]]] = {user_id: {} for user_id in user_ids}
    quiz: dict[uuid.UUID, dict[int, list[int]]] = {user_id: {} for user_id in user_ids}
    drills = {user_id: 0 for user_id in user_ids}
    if not user_ids:
        return coach, quiz, {}, drills
    for attempt in db.query(CoachAttempt).filter(CoachAttempt.user_id.in_(user_ids)).all():
        coach.setdefault(attempt.user_id, {}).setdefault(attempt.scenario_id, []).append(attempt.score)
        drills[attempt.user_id] = drills.get(attempt.user_id, 0) + 1
    for attempt in db.query(PositionAttempt).filter(PositionAttempt.user_id.in_(user_ids)).all():
        quiz.setdefault(attempt.user_id, {}).setdefault(attempt.scenario_id, []).append(attempt.score)
        drills[attempt.user_id] = drills.get(attempt.user_id, 0) + 1
    return coach, quiz, points_by_user(db, user_ids), drills


def _clip_counts(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not user_ids:
        return {}
    rows = (
        db.query(VideoWatch.user_id, func.count(VideoWatch.id))
        .filter(VideoWatch.user_id.in_(user_ids))
        .group_by(VideoWatch.user_id)
        .all()
    )
    return {user_id: int(total or 0) for user_id, total in rows}


def _last_logins(db: Session, members: list[User]) -> dict[uuid.UUID, datetime | None]:
    if not members:
        return {}
    user_ids = [member.id for member in members]
    rows = (
        db.query(RefreshToken.user_id, func.max(RefreshToken.created_at))
        .filter(RefreshToken.user_id.in_(user_ids))
        .group_by(RefreshToken.user_id)
        .all()
    )
    remembered = {user_id: _as_utc(when) for user_id, when in rows}
    found: dict[uuid.UUID, datetime | None] = {}
    for member in members:
        times = [item for item in (_as_utc(member.last_login_at), remembered.get(member.id)) if item is not None]
        found[member.id] = max(times) if times else None
    return found


def _points(
    coach: dict[int, list[int]],
    quiz: dict[int, list[int]],
    clips: dict[uuid.UUID, int],
    user_id: uuid.UUID,
) -> int:
    return total_score(coach) + quiz_score(quiz) + clips.get(user_id, 0)


def _squad(db: Session, club: Club, viewer_id: uuid.UUID) -> dict:
    members = _members(db, club)
    user_ids = [member.id for member in members]
    coach, quiz, clip_points, _drills = _attempt_maps(db, user_ids)
    entries = []
    for member in members:
        avatar = public_avatar(member.avatar)
        entries.append(
            {
                "user_id": str(member.id),
                "name": (avatar or {}).get("nickname") or member.first_name,
                "score": _points(coach.get(member.id) or {}, quiz.get(member.id) or {}, clip_points, member.id),
                "avatar": avatar,
                "you": member.id == viewer_id,
            }
        )
    return {"club": _as_public(db, club), "ranks": ordered_ranks(entries)}


def squad_stats(db: Session, user: User) -> dict:
    if user.account_type != "coach_admin":
        raise ClubError(403, "Only a coach can see squad stats.")
    club = user.owned_club
    if club is None:
        return {
            "club": None,
            "players": 0,
            "points": 0,
            "drills": 0,
            "clips": 0,
            "active_week": 0,
            "roster": [],
        }
    members = _members(db, club)
    user_ids = [member.id for member in members]
    coach, quiz, clip_points, drills = _attempt_maps(db, user_ids)
    clips = _clip_counts(db, user_ids)
    logins = _last_logins(db, members)
    week_ago = utcnow() - timedelta(days=7)
    roster = []
    active_week = 0
    for member in members:
        avatar = public_avatar(member.avatar)
        when = logins.get(member.id)
        if when is not None and when >= week_ago:
            active_week += 1
        roster.append(
            {
                "user_id": str(member.id),
                "name": (avatar or {}).get("nickname") or member.first_name,
                "points": _points(coach.get(member.id) or {}, quiz.get(member.id) or {}, clip_points, member.id),
                "last_login": when.isoformat() if when else None,
                "drills": drills.get(member.id, 0),
                "clips": clips.get(member.id, 0),
            }
        )
    roster.sort(key=lambda row: (-int(row["points"]), row["name"].casefold()))
    return {
        "club": _as_public(db, club),
        "players": len(roster),
        "points": sum(int(row["points"]) for row in roster),
        "drills": sum(int(row["drills"]) for row in roster),
        "clips": sum(int(row["clips"]) for row in roster),
        "active_week": active_week,
        "roster": roster,
    }


def remove_player(db: Session, user: User, player_id: uuid.UUID) -> None:
    if user.account_type != "coach_admin":
        raise ClubError(403, "Only a coach can remove a player.")
    club = user.owned_club
    if club is None:
        raise ClubError(404, "Create a club first.")
    member = db.get(ClubMember, player_id)
    if member is None or member.club_id != club.id:
        raise ClubError(404, "That player is not on your team.")
    db.delete(member)
    db.commit()


def leaderboard(db: Session, user: User) -> dict:
    if user.account_type == "coach_admin" and user.owned_club is not None:
        return _squad(db, user.owned_club, user.id)
    if user.account_type == "player" and user.membership is not None:
        return _squad(db, user.membership.club, user.id)
    if user.account_type == "coach_admin":
        raise ClubError(404, "Create a club to see the squad ranks.")
    raise ClubError(404, "Join a club to see the squad ranks.")
