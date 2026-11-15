"""Positional Quiz library. One teammate has the ball. Place the other six."""

from __future__ import annotations

import math

from coach_scenarios import ROLES

SECTIONS = [
    {
        "id": "diamond",
        "title": "Diamond shapes",
        "kicker": "DIAMOND",
        "mode": "positions",
        "blurb": "Put a player behind the ball, one each side, and one ahead.",
    },
    {
        "id": "compact",
        "title": "Stay compact",
        "kicker": "COMPACT",
        "mode": "positions",
        "blurb": "Keep the passes short, and still use the width.",
    },
    {
        "id": "cover",
        "title": "Cover the space",
        "kicker": "COVER",
        "mode": "positions",
        "blurb": "The far full-back tucks in. Everyone else keeps the width.",
    },
    {
        "id": "balance",
        "title": "Shape, compact, cover",
        "kicker": "BALANCE",
        "mode": "positions",
        "blurb": "Keep the diamond, stay close, and cover the goal.",
    },
]

SECTION_CATEGORY = {section["id"]: section["id"] for section in SECTIONS}

_ORDER = ("gk", "lb", "rb", "cdm", "lw", "rw", "st")
_DEFEND_ORDER = ("dgk", "dr", "dl", "dcm", "drw", "dlw", "dst")

# Their 2-3-1, seen from our goal. Their right side is on the left of the screen.
STANDARD_231 = {
    "dgk": (50, 96),
    "dr": (20, 90),
    "dl": (80, 90),
    "drw": (10, 82),
    "dcm": (50, 82),
    "dlw": (90, 82),
    "dst": (50, 70),
}

_DRILLS = [
    {
        "section": "diamond",
        "title": "Keeper's diamond",
        "difficulty": "easy",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (14, 28), "rb": (86, 28), "cdm": (50, 42), "lw": (12, 52), "rw": (88, 52), "st": (50, 60)},
        "desc": "Your keeper has the ball. Drag the other six into two diamonds across the width of the pitch.",
        "why": "The full-backs stay wide and the midfielder is the point of the first diamond. The wingers stay wide and the striker is the point of the second.",
        "mistake": "A flat line leaves the keeper with no easy pass at an angle.",
        "tip": "A diamond has a player behind the ball, one on each side, and one ahead.",
    },
    {
        "section": "diamond",
        "title": "Midfielder's diamond",
        "difficulty": "easy",
        "ball": ("cdm", (50, 46)),
        "places": {"gk": (50, 14), "lb": (16, 32), "rb": (84, 32), "lw": (12, 56), "rw": (88, 56), "st": (50, 60)},
        "desc": "Your midfielder has the ball in the middle. Build a wide diamond around them.",
        "why": "Full-backs stay wide behind the ball, wingers stay wide ahead of it, and the striker is the point. The keeper is the player behind the diamond.",
        "mistake": "Standing in a row beside the ball blocks the pass.",
        "tip": "Around the ball: one behind, one each side, and one ahead.",
    },
    {
        "section": "diamond",
        "title": "Diamond on the wing",
        "difficulty": "medium",
        "ball": ("rw", (90, 54)),
        "places": {"gk": (50, 14), "lb": (16, 30), "rb": (76, 40), "cdm": (64, 46), "lw": (14, 50), "st": (72, 60)},
        "desc": "Your right winger has the ball on the touchline. Make a diamond there, and keep the left side wide.",
        "why": "The right back is behind the ball, the midfielder is inside, and the striker is ahead. The left back and left winger stay in the wide left lane.",
        "mistake": "Everyone rushing to the ball crowds the winger.",
        "tip": "On the wing, the diamond is behind, inside, and ahead of the ball.",
    },
    {
        "section": "diamond",
        "title": "Striker's diamond",
        "difficulty": "medium",
        "ball": ("st", (50, 60)),
        "places": {"gk": (50, 14), "lb": (16, 30), "rb": (84, 30), "cdm": (50, 42), "lw": (14, 50), "rw": (86, 50)},
        "desc": "Your striker has the ball. Put a wide diamond behind them.",
        "why": "Both wingers stay wide just behind the striker, with the midfielder behind them. The full-backs stay wide too.",
        "mistake": "Joining the striker in a bunch leaves no pass back.",
        "tip": "When the striker has the ball, the next diamond is just behind them.",
    },
    {
        "section": "compact",
        "title": "Stay close to the keeper",
        "difficulty": "easy",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (16, 24), "rb": (84, 24), "cdm": (50, 34), "lw": (14, 42), "rw": (86, 42), "st": (50, 50)},
        "desc": "Your keeper has the ball. Bring the lines closer, and keep the team wide.",
        "why": "Full-backs and wingers stay near the sides. The lines are close enough for the keeper to play a short pass.",
        "mistake": "A big gap between the lines makes the pass too long. Bunching in the middle wastes the width.",
        "tip": "Short passes, wide players.",
    },
    {
        "section": "compact",
        "title": "Slide together",
        "difficulty": "medium",
        "ball": ("lw", (12, 52)),
        "places": {"gk": (42, 14), "lb": (18, 32), "rb": (74, 30), "cdm": (40, 42), "rw": (82, 50), "st": (36, 58)},
        "desc": "Your left winger has the ball on the touchline. Slide across, and keep a player on the far side.",
        "why": "The team slides toward the ball. The right back and right winger still hold the right side, so the team uses the width.",
        "mistake": "Everyone crowding the ball leaves the far side empty.",
        "tip": "Move with the ball, and keep the team wide.",
    },
    {
        "section": "compact",
        "title": "No big gaps",
        "difficulty": "medium",
        "ball": ("cdm", (50, 44)),
        "places": {"gk": (50, 14), "lb": (16, 28), "rb": (84, 28), "lw": (14, 50), "rw": (86, 50), "st": (50, 58)},
        "desc": "Your midfielder has the ball. Close the gaps between the lines, and keep the width.",
        "why": "Full-backs and wingers stay wide. The lines sit in even steps, with no big hole between them.",
        "mistake": "A gap between the defenders and the striker is an easy place to lose the ball.",
        "tip": "If you can see a big empty patch between your players, move someone into it.",
    },
    {
        "section": "compact",
        "title": "Compact near the goal",
        "difficulty": "hard",
        "ball": ("rw", (88, 56)),
        "places": {"gk": (50, 16), "lb": (20, 32), "rb": (74, 42), "cdm": (60, 46), "lw": (16, 48), "st": (68, 58)},
        "desc": "Your right winger has the ball high and wide. The near players stay close enough to pass, and the left side holds the width.",
        "why": "The right back, midfielder, and striker are close to the ball. The left back and left winger stay wide on the far side.",
        "mistake": "Bunching the whole team around the ball leaves the far side empty.",
        "tip": "Help the ball from nearby, and keep a player on the other wing.",
    },
    {
        "section": "cover",
        "title": "Tuck the far back",
        "difficulty": "easy",
        "ball": ("lw", (12, 52)),
        "places": {"gk": (46, 14), "lb": (18, 34), "rb": (58, 32), "cdm": (40, 44), "rw": (82, 50), "st": (34, 58)},
        "desc": "The ball is with your left winger. The far full-back is still stuck on the touchline.",
        "why": "The right back slides inside to cover the middle. The right winger stays wide. The near players stay close to the ball.",
        "mistake": "A right back who stays on the touchline leaves the middle open.",
        "tip": "The defender farthest from the ball tucks in and protects the middle.",
    },
    {
        "section": "cover",
        "title": "Cover from the left",
        "difficulty": "medium",
        "ball": ("rw", (88, 54)),
        "places": {"gk": (54, 14), "lb": (42, 32), "rb": (76, 40), "cdm": (62, 46), "lw": (18, 48), "st": (68, 58)},
        "desc": "Your right winger has the ball. Cover the middle from the left, and keep a player wide.",
        "why": "The left back tucks inside to cover the goal. The left winger stays wide. The right back and striker support the ball.",
        "mistake": "If the far full-back stays on the touchline, the path to your goal is open.",
        "tip": "Cover means being between the ball and your own goal.",
    },
    {
        "section": "cover",
        "title": "Protect the middle",
        "difficulty": "medium",
        "ball": ("lb", (16, 32)),
        "places": {"gk": (50, 14), "rb": (84, 30), "cdm": (50, 44), "lw": (14, 50), "rw": (86, 50), "st": (50, 58)},
        "desc": "Your left back has the ball, wide on the left. The middle must not be empty, and the right side stays wide.",
        "why": "The midfielder covers the centre. The right back and right winger hold the far side so the team still uses the width.",
        "mistake": "If the middle is empty, one pass can split the team.",
        "tip": "When a defender has the ball, a midfielder covers the middle.",
    },
    {
        "section": "cover",
        "title": "Numbers behind the ball",
        "difficulty": "hard",
        "ball": ("st", (50, 60)),
        "places": {"gk": (50, 14), "lb": (16, 30), "rb": (84, 30), "cdm": (50, 42), "lw": (14, 50), "rw": (86, 50)},
        "desc": "Your striker has the ball. Keep players behind the ball, and keep them wide.",
        "why": "The wingers, midfielder, full-backs, and keeper all stay closer to your goal than the ball. The wingers and full-backs still use the sides.",
        "mistake": "Everyone rushing past the ball leaves nothing behind it.",
        "tip": "Keep more players behind the ball than ahead of it.",
    },
    {
        "section": "balance",
        "title": "The full shape",
        "difficulty": "medium",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (14, 28), "rb": (86, 28), "cdm": (50, 42), "lw": (12, 52), "rw": (88, 52), "st": (50, 60)},
        "desc": "Your keeper has the ball. Make two wide diamonds, with short gaps between the lines.",
        "why": "Full-backs and wingers use the width. The midfielder and striker are the points of the two diamonds, close enough to pass to.",
        "mistake": "A narrow shape wastes the sides. A huge gap between the lines makes the pass too long.",
        "tip": "Diamond, compact, cover. Check all three.",
    },
    {
        "section": "balance",
        "title": "Wide, but compact",
        "difficulty": "medium",
        "ball": ("rw", (90, 54)),
        "places": {"gk": (52, 14), "lb": (22, 30), "rb": (76, 40), "cdm": (64, 46), "lw": (16, 48), "st": (70, 58)},
        "desc": "The ball is on the right touchline. Make a diamond there, and keep the left side wide.",
        "why": "The right back is behind, the midfielder is inside, and the striker is ahead. The left back and left winger hold the far side.",
        "mistake": "Everyone rushing to the ball leaves the left side empty.",
        "tip": "Build the diamond beside the ball, and keep a player on the far wing.",
    },
    {
        "section": "balance",
        "title": "Wide left, cover in",
        "difficulty": "hard",
        "ball": ("lw", (12, 52)),
        "places": {"gk": (48, 14), "lb": (20, 36), "rb": (60, 32), "cdm": (42, 44), "rw": (82, 50), "st": (36, 58)},
        "desc": "The ball is on the left touchline. Diamond on that side, cover in the middle, and keep the right winger wide.",
        "why": "The left back is behind the ball, the midfielder is inside, and the striker is ahead. The right back tucks in to cover. The right winger stays wide.",
        "mistake": "The far full-back staying on the touchline leaves the middle open.",
        "tip": "Tuck the far full-back in. Leave the far winger wide.",
    },
    {
        "section": "balance",
        "title": "Attack and leave cover",
        "difficulty": "hard",
        "ball": ("st", (50, 60)),
        "places": {"gk": (50, 14), "lb": (16, 28), "rb": (84, 28), "cdm": (50, 42), "lw": (14, 50), "rw": (86, 50)},
        "desc": "Your striker has the ball. Join with a wide diamond, and leave the full-backs behind.",
        "why": "The wingers stay wide just behind the striker. The midfielder and both full-backs stay behind the ball, still using the width.",
        "mistake": "Six players in the box leaves the keeper alone.",
        "tip": "Attack with a diamond, and always leave players behind the ball.",
    },
]


def _clamp(value: float, low: float = 8, high: float = 94) -> float:
    return max(low, min(high, value))


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _opponents() -> dict[str, tuple[float, float]]:
    return {pid: (float(x), float(y)) for pid, (x, y) in STANDARD_231.items()}


def _starts(
    correct: dict[str, tuple[float, float]],
    blocked: list[tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    starts: dict[str, tuple[float, float]] = {}
    taken = list(blocked)
    xs = (10, 24, 38, 50, 64, 78, 90)
    ys = (18, 32, 46, 60, 74)
    for pid, spot in correct.items():
        options = []
        for x in xs:
            for y in ys:
                if _dist((x, y), spot) < 28:
                    continue
                if any(_dist((x, y), other) < 10 for other in taken):
                    continue
                options.append((_dist((x, y), spot), x, y))
        if not options:
            raise RuntimeError(f"No start spot for {pid}")
        options.sort(reverse=True)
        _, x, y = options[0]
        starts[pid] = (float(x), float(y))
        taken.append((float(x), float(y)))
    return starts


def _pack(players: dict[str, tuple[float, float]], team: str) -> list[dict]:
    order = _ORDER if team == "attack" else _DEFEND_ORDER
    rows = []
    for pid in order:
        x, y = players[pid]
        role, name, keeper = ROLES[pid]
        rows.append(
            {
                "id": pid,
                "role": role,
                "name": name,
                "team": team,
                "x": round(x, 1),
                "y": round(y, 1),
                "goalkeeper": keeper,
            }
        )
    return rows


def _build_one(drill: dict, scenario_id: int) -> dict:
    carrier, ball_at = drill["ball"]
    correct = {pid: (float(x), float(y)) for pid, (x, y) in drill["places"].items()}
    if carrier in correct or len(correct) != 6:
        raise RuntimeError(f"{drill['title']} needs the other six players")
    attack = dict(correct)
    attack[carrier] = (float(ball_at[0]), float(ball_at[1]))
    defend = _opponents()
    starts = _starts(correct, [attack[carrier], *defend.values()])
    shown = dict(starts)
    shown[carrier] = attack[carrier]
    bx, by = attack[carrier]
    return {
        "id": scenario_id,
        "title": drill["title"],
        "description": drill["desc"],
        "mode": "positions",
        "category": SECTION_CATEGORY[drill["section"]],
        "topics": [drill["section"]],
        "difficulty": drill["difficulty"],
        "section": drill["section"],
        "highlightedPlayerId": carrier,
        "movablePlayerIds": [pid for pid in _ORDER if pid != carrier],
        "correctPositions": {pid: {"x": round(x, 1), "y": round(y, 1)} for pid, (x, y) in correct.items()},
        "availableActions": [],
        "explanation": drill["why"],
        "incorrectExplanation": drill["mistake"],
        "coachingTip": drill["tip"],
        "attackingPlayers": _pack(shown, "attack"),
        "defendingPlayers": _pack(defend, "defend"),
        "ballPosition": {"x": round(_clamp(bx + 3, 6, 96), 1), "y": round(_clamp(by + 2, 6, 96), 1)},
        "formation": "2-3-1",
    }


_ROWS: list[dict] = []


def load_scenarios() -> list[dict]:
    if not _ROWS:
        for index, drill in enumerate(_DRILLS, start=1):
            _ROWS.append(_build_one(drill, index))
    return _ROWS
