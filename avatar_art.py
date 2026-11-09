from __future__ import annotations

from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets" / "avatars"

# Every combination of these choices has its own portrait.
PORTRAIT_SKINS = ("light", "dark")
PORTRAIT_HAIR_STYLES = ("short", "curly", "ponytail")
PORTRAIT_HAIR_COLORS = ("black", "brown", "blonde")
PORTRAIT_BOOTS = ("black", "orange")

HAIR_GROUP = {
    "short": "short",
    "fade": "short",
    "straight": "short",
    "spikes": "short",
    "curly": "curly",
    "afro": "curly",
    "headband": "curly",
    "ponytail": "ponytail",
}


def _file(name: str) -> Path | None:
    path = ASSETS / name
    return path if path.is_file() else None


def portrait_skin(skin: str) -> str:
    return "light" if skin == "light" else "dark"


def portrait_hair_style(hair: str) -> str:
    style = HAIR_GROUP.get(hair, "curly")
    return style if style in PORTRAIT_HAIR_STYLES else "curly"


def portrait_hair_color(hair_color: str) -> str:
    if hair_color in PORTRAIT_HAIR_COLORS:
        return hair_color
    return "black"


def portrait_boots(boots: str) -> str:
    return "orange" if boots == "orange" else "black"


def portrait_path(
    gender: str,
    skin: str,
    hair: str,
    hair_color: str = "black",
    boots: str = "black",
) -> Path:
    side = "f" if gender == "F" else "m"
    name = (
        f"{side}_{portrait_skin(skin)}_{portrait_hair_style(hair)}_"
        f"{portrait_hair_color(hair_color)}_{portrait_boots(boots)}.jpg"
    )
    for candidate in (name, "m_brown_curly.jpg", "m_light_curly.jpg"):
        found = _file(candidate)
        if found is not None:
            return found
    raise FileNotFoundError("Volt Pitch character art is missing.")


def celebration_path(gender: str) -> Path:
    name = "celebrate_f.jpg" if gender == "F" else "celebrate_m.jpg"
    found = _file(name)
    if found is not None:
        return found
    return portrait_path(gender, "dark", "curly", "black", "black")
