from __future__ import annotations

from auth_service import AuthError
from constants import (
    AVATAR_BODIES,
    AVATAR_BOOTS,
    AVATAR_GENDERS,
    AVATAR_HAIR,
    AVATAR_HAIR_STYLES,
    AVATAR_KIT,
    AVATAR_KIT_STYLES,
    AVATAR_SKIN,
    GENERIC_AVATAR,
)
from db import PlayerAvatar, User, utcnow


def _swatch(catalog: dict, key: str) -> dict:
    item = catalog.get(key)
    if item is None:
        key, item = next(iter(catalog.items()))
    return {"id": key, "label": item["label"], "hex": item["hex"]}


def _named(catalog: dict, key: str, fallback: str) -> dict:
    chosen = key if key in catalog else fallback
    return {"id": chosen, "label": catalog[chosen]}


def public_avatar(avatar: PlayerAvatar | None) -> dict | None:
    if avatar is None:
        return None
    gender = avatar.gender if avatar.gender in AVATAR_GENDERS else "M"
    body = avatar.body_type if avatar.body_type in AVATAR_BODIES else "balanced"
    return {
        "gender": {"id": gender, "label": AVATAR_GENDERS[gender]},
        "skin_color": _swatch(AVATAR_SKIN, avatar.skin_color),
        "hair_style": _named(AVATAR_HAIR_STYLES, avatar.hair_style, "curly"),
        "hair_color": _swatch(AVATAR_HAIR, avatar.hair_color),
        "kit_style": _named(AVATAR_KIT_STYLES, avatar.kit_style, "volt"),
        "kit_primary": _swatch(AVATAR_KIT, avatar.kit_primary),
        "kit_accent": _swatch(AVATAR_KIT, avatar.kit_accent),
        "boots_color": _swatch(AVATAR_BOOTS, avatar.boots_color),
        "body_type": {"id": body, "label": AVATAR_BODIES[body]},
        "nickname": avatar.nickname,
        "is_custom": bool(avatar.is_custom),
    }


def _players_only(user: User) -> None:
    if user.account_type != "player":
        raise AuthError(403, "Only player accounts have an avatar.")


def _choice(catalog: dict, key: str, label: str) -> str:
    if key not in catalog:
        raise AuthError(400, f"Choose a {label}.")
    return key


def clean_nickname(value: str) -> str:
    cleaned = " ".join((value or "").split())
    if len(cleaned) < 2 or len(cleaned) > 20:
        raise AuthError(400, "Nickname needs 2 to 20 characters.")
    if any(ord(char) < 32 for char in cleaned):
        raise AuthError(400, "Nickname contains invalid characters.")
    return cleaned


def _write(db, user: User, fields: dict, is_custom: bool) -> None:
    avatar = user.avatar
    if avatar is None:
        avatar = PlayerAvatar(user=user, created_at=utcnow())
        db.add(avatar)
    avatar.gender = fields["gender"]
    avatar.skin_color = fields["skin_color"]
    avatar.hair_style = fields["hair_style"]
    avatar.hair_color = fields["hair_color"]
    avatar.kit_style = fields["kit_style"]
    avatar.kit_primary = fields["kit_primary"]
    avatar.kit_accent = fields["kit_accent"]
    avatar.boots_color = fields["boots_color"]
    avatar.body_type = fields["body_type"]
    avatar.nickname = fields["nickname"]
    avatar.is_custom = is_custom
    avatar.updated_at = utcnow()


def save_avatar(db, user: User, payload: dict) -> User:
    _players_only(user)
    gender = payload.get("gender")
    if gender not in AVATAR_GENDERS:
        raise AuthError(400, "Choose M or F.")
    fields = {
        "gender": gender,
        "skin_color": _choice(AVATAR_SKIN, payload.get("skin_color"), "skin colour"),
        "hair_style": _choice(AVATAR_HAIR_STYLES, payload.get("hair_style"), "hair style"),
        "hair_color": _choice(AVATAR_HAIR, payload.get("hair_color"), "hair colour"),
        "kit_style": _choice(AVATAR_KIT_STYLES, payload.get("kit_style"), "kit style"),
        "kit_primary": _choice(AVATAR_KIT, payload.get("kit_primary"), "kit primary colour"),
        "kit_accent": _choice(AVATAR_KIT, payload.get("kit_accent"), "kit accent colour"),
        "boots_color": _choice(AVATAR_BOOTS, payload.get("boots_color"), "boots colour"),
        "body_type": _choice(AVATAR_BODIES, payload.get("body_type"), "body type"),
        "nickname": clean_nickname(str(payload.get("nickname") or "")),
    }
    _write(db, user, fields, True)
    db.commit()
    db.refresh(user)
    return user


def skip_avatar(db, user: User) -> User:
    _players_only(user)
    if user.avatar is not None:
        return user
    nickname = " ".join(user.first_name.split())[:20].strip()
    if len(nickname) < 2:
        nickname = "Player"
    fields = dict(GENERIC_AVATAR)
    fields["nickname"] = nickname
    _write(db, user, fields, False)
    db.commit()
    db.refresh(user)
    return user
