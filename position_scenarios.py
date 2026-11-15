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
        "places": {"lb": (14, 26), "rb": (86, 26), "cdm": (50, 36), "lw": (12, 48), "rw": (88, 48), "st": (50, 56)},
        "desc": "Your keeper has the ball. Drag the other six into two diamonds across the width of the pitch.",
        "why": "The full-backs stay wide, and the midfielder is free in front of the keeper. The wingers stay wide, and the striker is the next pass through the middle.",
        "mistake": "A flat line leaves the keeper with no easy pass at an angle.",
        "tip": "A diamond has a player behind the ball, one on each side, and one ahead.",
    },
    {
        "section": "diamond",
        "title": "Midfielder's diamond",
        "difficulty": "easy",
        "ball": ("cdm", (50, 46)),
        "places": {"gk": (50, 14), "lb": (16, 30), "rb": (84, 30), "lw": (12, 54), "rw": (90, 50), "st": (72, 72)},
        "desc": "Your midfielder has the ball in the middle. Build a wide diamond, and send the striker into the gap.",
        "why": "Full-backs stay wide behind the ball and wingers stay wide ahead of it. The striker finds the space between their midfielder and their left winger, instead of standing on the ball.",
        "mistake": "Standing next to the midfielder blocks the forward pass.",
        "tip": "The striker looks for the gap between their midfielder and their left winger.",
    },
    {
        "section": "diamond",
        "title": "Diamond on the wing",
        "difficulty": "medium",
        "ball": ("rw", (90, 54)),
        "places": {"gk": (50, 14), "lb": (14, 26), "rb": (72, 30), "cdm": (46, 40), "lw": (12, 48), "st": (72, 72)},
        "desc": "Your right winger has the ball on the touchline. Give them three passing options, and keep the left side wide.",
        "why": "The right back is the pass behind the ball. The midfielder stays in the middle. The striker attacks the gap between their midfielder and their left winger. The left back and left winger keep the far side wide.",
        "mistake": "The right back, midfielder, and striker all standing next to the winger leaves no pass and no space.",
        "tip": "One player helps from behind. Everyone else keeps a gap and finds space.",
    },
    {
        "section": "diamond",
        "title": "Striker's diamond",
        "difficulty": "medium",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (16, 28), "rb": (84, 28), "cdm": (50, 42), "lw": (14, 50), "rw": (86, 48)},
        "desc": "Your striker has the ball in the gap. Put a wide diamond behind them.",
        "why": "The striker is between their midfielder and their left winger. Both of your wingers stay wide behind the ball, and the midfielder is the pass through the middle. The full-backs stay wide too.",
        "mistake": "Joining the striker in a bunch leaves no pass back.",
        "tip": "When the striker is in space, the next diamond stays wide behind them.",
    },
    {
        "section": "compact",
        "title": "Stay close to the keeper",
        "difficulty": "easy",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (14, 24), "rb": (86, 24), "cdm": (50, 34), "lw": (12, 44), "rw": (88, 44), "st": (50, 52)},
        "desc": "Your keeper has the ball. Bring the lines a little closer, and keep the team wide.",
        "why": "Full-backs and wingers stay on the sides. The midfielder and striker are free in the middle, close enough for a short pass.",
        "mistake": "A big gap between the lines makes the pass too long. Bunching in the middle wastes the width.",
        "tip": "Short passes, wide players.",
    },
    {
        "section": "compact",
        "title": "Slide together",
        "difficulty": "medium",
        "ball": ("lw", (12, 52)),
        "places": {"gk": (46, 14), "lb": (24, 30), "rb": (84, 28), "cdm": (42, 40), "rw": (90, 50), "st": (28, 72)},
        "desc": "Your left winger has the ball on the touchline. Slide across, and keep a player on the far side.",
        "why": "The left back and midfielder shift toward the ball and still leave a gap. The striker attacks the space between their right winger and their midfielder. The right back and right winger hold the far side.",
        "mistake": "Everyone crowding the ball leaves the far side empty.",
        "tip": "Move with the ball, keep a gap, and leave someone on the other wing.",
    },
    {
        "section": "compact",
        "title": "No big gaps",
        "difficulty": "medium",
        "ball": ("cdm", (50, 44)),
        "places": {"gk": (50, 16), "lb": (14, 30), "rb": (86, 30), "lw": (12, 52), "rw": (88, 50), "st": (72, 72)},
        "desc": "Your midfielder has the ball. Keep the lines connected, and send the striker into space.",
        "why": "Full-backs stay wide behind the ball and wingers stay wide just ahead of it. The striker is in the gap between their midfielder and their left winger, not stood on your midfielder.",
        "mistake": "The striker standing on the midfielder, or a big empty patch between the lines, makes the pass easy to win.",
        "tip": "Each line is a short step away. The striker still looks for the gap.",
    },
    {
        "section": "compact",
        "title": "Compact near the goal",
        "difficulty": "hard",
        "ball": ("rw", (88, 58)),
        "places": {"gk": (50, 14), "lb": (16, 28), "rb": (76, 36), "cdm": (48, 42), "lw": (14, 50), "st": (72, 72)},
        "desc": "Your right winger has the ball high and wide. One teammate is the close pass. The rest keep the shape.",
        "why": "The right back is the pass behind the ball. The midfielder stays in the middle. The striker attacks the gap, and the left side stays wide.",
        "mistake": "Pulling the midfielder and the striker onto the winger makes a bunch and leaves the middle empty.",
        "tip": "Help from one player behind the ball. Do not send the whole team there.",
    },
    {
        "section": "cover",
        "title": "Tuck the far back",
        "difficulty": "easy",
        "ball": ("lw", (12, 52)),
        "places": {"gk": (50, 14), "lb": (24, 30), "rb": (66, 28), "cdm": (42, 42), "rw": (88, 50), "st": (28, 72)},
        "desc": "The ball is with your left winger. The far full-back is still stuck on the touchline.",
        "why": "The right back slides inside to cover the middle. The right winger stays wide. The left back is the pass behind the ball, and the striker attacks the gap between their right winger and their midfielder.",
        "mistake": "A right back who stays on the touchline leaves the middle open. A bunch around the ball does not fix that.",
        "tip": "The defender farthest from the ball tucks in. The far winger stays wide.",
    },
    {
        "section": "cover",
        "title": "Cover from the left",
        "difficulty": "medium",
        "ball": ("rw", (88, 54)),
        "places": {"gk": (50, 14), "lb": (34, 28), "rb": (76, 32), "cdm": (54, 44), "lw": (14, 50), "st": (72, 72)},
        "desc": "Your right winger has the ball. Cover the middle from the left, and keep a player wide.",
        "why": "The left back tucks inside, between the ball and your goal. The left winger stays wide. The right back is the pass behind the ball, and the striker attacks the gap.",
        "mistake": "If the far full-back stays on the touchline, the path to your goal is open.",
        "tip": "Cover means being between the ball and your own goal, with a gap from your teammates.",
    },
    {
        "section": "cover",
        "title": "Protect the middle",
        "difficulty": "medium",
        "ball": ("lb", (16, 32)),
        "places": {"gk": (50, 14), "rb": (86, 28), "cdm": (50, 44), "lw": (12, 54), "rw": (88, 50), "st": (28, 72)},
        "desc": "Your left back has the ball, wide on the left. The middle must not be empty, and the right side stays wide.",
        "why": "The midfielder covers the centre, away from the ball. The striker attacks the gap on the left. The right back and right winger hold the far side.",
        "mistake": "If the middle is empty, one pass can split the team. The striker standing on the midfielder does not help.",
        "tip": "When a defender has the ball, a midfielder covers the middle and the striker finds space.",
    },
    {
        "section": "cover",
        "title": "Numbers behind the ball",
        "difficulty": "hard",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (16, 26), "rb": (84, 26), "cdm": (50, 38), "lw": (14, 44), "rw": (86, 44)},
        "desc": "Your striker has the ball in the gap. Keep every other player behind the ball, and keep them wide.",
        "why": "The striker is between their midfielder and their left winger. Your wingers, midfielder, full-backs, and keeper all stay closer to your goal, spread across the pitch.",
        "mistake": "Everyone rushing up to the striker leaves nothing behind the ball.",
        "tip": "Keep more players behind the ball than ahead of it, and do not leave the sides empty.",
    },
    {
        "section": "balance",
        "title": "The full shape",
        "difficulty": "medium",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (14, 28), "rb": (86, 28), "cdm": (50, 40), "lw": (12, 50), "rw": (88, 48), "st": (72, 72)},
        "desc": "Your keeper has the ball. Make a wide shape, keep the passes short, and send the striker into the gap.",
        "why": "Full-backs and wingers use the width. The midfielder is free in front of the keeper. The striker attacks the space between their midfielder and their left winger.",
        "mistake": "A narrow shape wastes the sides. A striker stood on the midfielder wastes the forward pass.",
        "tip": "Width, a free midfielder, and a striker in the gap.",
    },
    {
        "section": "balance",
        "title": "Wide, but compact",
        "difficulty": "medium",
        "ball": ("rw", (90, 54)),
        "places": {"gk": (50, 14), "lb": (18, 28), "rb": (72, 34), "cdm": (48, 42), "lw": (14, 50), "st": (72, 72)},
        "desc": "The ball is on the right touchline. Stay close enough to pass, and keep the left side wide.",
        "why": "The right back is behind the ball, the midfielder holds the middle, and the striker attacks the gap. None of them stand on the winger. The left winger keeps the far side wide.",
        "mistake": "Everyone rushing to the ball leaves the left side empty and makes a bunch.",
        "tip": "A short pass needs a gap you can see. Keep a player on the far wing.",
    },
    {
        "section": "balance",
        "title": "Wide left, cover in",
        "difficulty": "hard",
        "ball": ("lw", (12, 52)),
        "places": {"gk": (50, 14), "lb": (26, 30), "rb": (66, 28), "cdm": (46, 42), "rw": (88, 50), "st": (28, 72)},
        "desc": "The ball is on the left touchline. Help from behind, cover the middle, and keep the right winger wide.",
        "why": "The left back is the pass behind the ball. The midfielder is inside, with a gap. The striker attacks the space on the left. The right back tucks in to cover, and the right winger stays wide.",
        "mistake": "The far full-back staying on the touchline leaves the middle open. Crowding the winger does too.",
        "tip": "Tuck the far full-back in. Leave the far winger wide. Give the ball one pass, not three.",
    },
    {
        "section": "balance",
        "title": "Attack and leave cover",
        "difficulty": "hard",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (16, 24), "rb": (84, 24), "cdm": (50, 38), "lw": (14, 50), "rw": (82, 48)},
        "desc": "Your striker has the ball in the gap. The wingers join from wide, and the full-backs stay behind.",
        "why": "The wingers are wide and still behind the ball. The midfielder and both full-backs stay deeper, so the keeper is not left alone.",
        "mistake": "Six players around the striker leaves the keeper alone.",
        "tip": "Attack with width, and always leave players behind the ball.",
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
