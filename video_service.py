"""Charge for watching a clip through once."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import User, VideoWatch

VIDEO_POINTS = 200
VIDEO_DIR = Path(__file__).resolve().parent / "assets" / "videos"
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


class VideoError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _clip_file(video_id: str) -> None:
    if _VIDEO_ID.fullmatch(video_id or "") is None:
        raise VideoError(404, "That clip does not exist.")
    path = (VIDEO_DIR / f"{video_id}.mp4").resolve()
    if path.parent != VIDEO_DIR.resolve() or not path.is_file():
        raise VideoError(404, "That clip does not exist.")


def watched_ids(db: Session, user: User) -> list[str]:
    rows = db.query(VideoWatch.video_id).filter(VideoWatch.user_id == user.id).all()
    return [video_id for (video_id,) in rows]


def points_by_user(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not user_ids:
        return {}
    rows = (
        db.query(VideoWatch.user_id, func.sum(VideoWatch.points))
        .filter(VideoWatch.user_id.in_(user_ids))
        .group_by(VideoWatch.user_id)
        .all()
    )
    return {user_id: int(total or 0) for user_id, total in rows}


def record_watch(db: Session, user: User, video_id: str) -> dict:
    if user.account_type != "player":
        raise VideoError(403, "Only players earn charge from clips.")
    _clip_file(video_id)
    existing = (
        db.query(VideoWatch)
        .filter(VideoWatch.user_id == user.id, VideoWatch.video_id == video_id)
        .one_or_none()
    )
    if existing is not None:
        return {"videoId": video_id, "awarded": False, "points": 0}
    db.add(VideoWatch(user_id=user.id, video_id=video_id, points=VIDEO_POINTS))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"videoId": video_id, "awarded": False, "points": 0}
    return {"videoId": video_id, "awarded": True, "points": VIDEO_POINTS}
