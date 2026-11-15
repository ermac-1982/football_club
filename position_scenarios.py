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
        "blurb": "The far full-back tucks in. Everyone else attacks and keeps the width.",
    },
    {
        "id": "balance",
        "title": "Shape, compact, cover",
        "kicker": "BALANCE",
        "mode": "positions",
        "blurb": "Attack together, stay close enough to pass, and leave someone behind the ball.",
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
        "places": {"lb": (13, 31), "rb": (90, 29), "cdm": (50, 50), "lw": (8, 63), "rw": (91, 60), "st": (63, 74)},
        "desc": "Your keeper has the ball. Spread the team wide and put the striker in the gap.",
        "why": "The full-backs stay wide for the first pass. The midfielder is free in the middle. The wingers stay wide and high. The striker attacks the space beside their striker, between their midfielder and their left winger.",
        "mistake": "A narrow shape, or a striker stood on your midfielder, wastes the pass forward.",
        "tip": "Wide full-backs, a free midfielder, and the striker in the gap.",
    },
    {
        "section": "diamond",
        "title": "Midfielder's diamond",
        "difficulty": "easy",
        "ball": ("cdm", (62, 52)),
        "places": {"gk": (50, 14), "lb": (47, 31), "rb": (82, 39), "lw": (25, 67), "rw": (90, 69), "st": (69, 82)},
        "desc": "Your midfielder has the ball and can turn. Play the striker in the gap.",
        "why": "The keeper stays home. The left back tucks in and the right back steps up. The left winger attacks the inside, the right winger stays wide, and the striker is between their midfielder and their left winger.",
        "mistake": "Leaving the striker deep wastes the chance to turn and score.",
        "tip": "Turn and pass. The striker attacks the gap, and one winger stays wide.",
    },
    {
        "section": "diamond",
        "title": "Diamond on the wing",
        "difficulty": "medium",
        "ball": ("rw", (88, 66)),
        "places": {"gk": (50, 14), "lb": (58, 44), "rb": (90, 49), "cdm": (62, 66), "lw": (22, 68), "st": (72, 91)},
        "desc": "Your right winger has the ball, ready to cross. Attack the space behind their defence.",
        "why": "The right back is the pass behind the ball. The midfielder is inside. The left winger attacks the far side. The striker runs in behind their left back, and the left back tucks in to cover.",
        "mistake": "A striker who stays deep has nothing to attack when the cross comes.",
        "tip": "Cross in behind their left back, and keep a player on the far side.",
    },
    {
        "section": "diamond",
        "title": "Striker's diamond",
        "difficulty": "medium",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (48, 38), "rb": (80, 45), "cdm": (59, 58), "lw": (28, 74), "rw": (96, 76)},
        "desc": "Your striker has the ball and can score. The wingers attack with them.",
        "why": "The left winger is inside and the right winger stays wide and high. The midfielder is the pass underneath. The right back steps up, and the left back tucks in.",
        "mistake": "Leaving the wingers deep gives the striker no one to pass to.",
        "tip": "One winger inside, one winger wide, and the midfielder underneath.",
    },
    {
        "section": "compact",
        "title": "Stay close to the keeper",
        "difficulty": "easy",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (17, 29), "rb": (85, 27), "cdm": (49, 45), "lw": (7, 59), "rw": (91, 55), "st": (61, 75)},
        "desc": "Your keeper has the ball. Keep the lines close, and send the striker into the gap.",
        "why": "The full-backs stay wide and close enough for a short pass. The midfielder is free in the middle. The wingers stay wide, and the striker attacks the space beside their striker.",
        "mistake": "A big gap in front of the keeper, or a striker stood on the midfielder, makes the pass too hard.",
        "tip": "Short passes, wide players, and the striker in the gap.",
    },
    {
        "section": "compact",
        "title": "Slide together",
        "difficulty": "medium",
        "ball": ("lw", (12, 66)),
        "places": {"gk": (50, 14), "lb": (18, 48), "rb": (53, 41), "cdm": (37, 58), "rw": (78, 72), "st": (41, 85)},
        "desc": "Your left winger has the ball, ready to cross. Slide across and attack the gap.",
        "why": "The left back and the midfielder slide toward the ball. The right back tucks into the middle. The striker attacks the space in front of their midfielder, and the right winger stays on the far side.",
        "mistake": "Leaving the far side empty, or the striker deep, wastes the cross.",
        "tip": "Slide toward the ball, tuck the far full-back in, and attack the gap.",
    },
    {
        "section": "compact",
        "title": "No big gaps",
        "difficulty": "medium",
        "ball": ("cdm", (58, 50)),
        "places": {"gk": (50, 14), "lb": (42, 39), "rb": (80, 36), "lw": (25, 70), "rw": (91, 63), "st": (70, 76)},
        "desc": "Your midfielder has the ball. Keep every line close enough to pass.",
        "why": "The left back tucks in and the right back stays on the right. The left winger attacks the inside, the right winger stays wide, and the striker is in the gap beside their striker.",
        "mistake": "A big empty patch between the midfielder and the striker makes the pass too easy to win.",
        "tip": "Each line is a short step away, and the striker is in the gap.",
    },
    {
        "section": "compact",
        "title": "Compact near the goal",
        "difficulty": "hard",
        "ball": ("rw", (88, 66)),
        "places": {"gk": (50, 14), "lb": (47, 36), "rb": (73, 49), "cdm": (59, 74), "lw": (28, 74), "st": (71, 90)},
        "desc": "Your right winger has the ball near their goal. Attack the space in behind.",
        "why": "The right back is the pass behind the ball. The midfielder and the left winger are high. The striker runs in beside their left back, and the left back tucks in to cover.",
        "mistake": "A striker who stays deep has nothing to finish when the ball is this high.",
        "tip": "Stay close enough to pass, and send the striker in behind.",
    },
    {
        "section": "cover",
        "title": "Tuck the far back",
        "difficulty": "easy",
        "ball": ("lw", (12, 66)),
        "places": {"gk": (50, 14), "lb": (22, 46), "rb": (56, 35), "cdm": (43, 56), "rw": (72, 86), "st": (56, 89)},
        "desc": "Your left winger can cross. Tuck the far full-back in, and attack the goal.",
        "why": "The right back slides into the middle. The left back and the midfielder support the ball. The striker and the right winger attack the space in the goal.",
        "mistake": "A far full-back stuck on the touchline leaves the middle open, and a deep striker wastes the cross.",
        "tip": "Tuck the far full-back in. Send the striker and the far winger into the goal.",
    },
    {
        "section": "cover",
        "title": "Cover from the left",
        "difficulty": "medium",
        "ball": ("rw", (88, 66)),
        "places": {"gk": (50, 14), "lb": (46, 45), "rb": (90, 47), "cdm": (59, 69), "lw": (31, 88), "st": (42, 89)},
        "desc": "Your right winger can cross. Cover the middle from the left, and attack the goal.",
        "why": "The left back tucks in to cover. The right back is the pass behind the ball. The midfielder supports underneath. The striker and the left winger attack the space in the goal.",
        "mistake": "A left back stuck on the touchline leaves the middle open, and a deep attack wastes the cross.",
        "tip": "Cover from the left. Send the striker and the left winger into the goal.",
    },
    {
        "section": "cover",
        "title": "Protect the middle",
        "difficulty": "medium",
        "ball": ("lb", (16, 46)),
        "places": {"gk": (50, 14), "rb": (60, 38), "cdm": (46, 61), "lw": (12, 73), "rw": (86, 64), "st": (41, 89)},
        "desc": "Your left back has the ball and can play forward. Protect the middle, and attack the goal.",
        "why": "The right back tucks in to protect the middle. The midfielder supports underneath the ball. The left winger stays wide on the ball side. The striker attacks the space in the goal, and the right winger stays wide.",
        "mistake": "A right back stuck on the touchline leaves the middle open, and a deep striker wastes the pass forward.",
        "tip": "Tuck the far full-back in. Keep the wingers wide and send the striker into the goal.",
    },
    {
        "section": "cover",
        "title": "Numbers behind the ball",
        "difficulty": "hard",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (51, 39), "rb": (88, 54), "cdm": (51, 58), "lw": (33, 88), "rw": (72, 91)},
        "desc": "Your striker has the ball and can score. Keep numbers behind the ball, and attack the goal.",
        "why": "The left back and the midfielder sit in the middle behind the ball. The right back stays wide. The left winger and the right winger attack the space in the goal.",
        "mistake": "Everyone rushing up leaves nothing behind the ball, and wingers stuck wide waste the chance to score.",
        "tip": "Leave the left back and the midfielder behind the ball. Send both wingers into the goal.",
    },
    {
        "section": "balance",
        "title": "The full shape",
        "difficulty": "medium",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (14, 38), "rb": (78, 37), "cdm": (51, 60), "lw": (16, 72), "rw": (89, 63), "st": (63, 74)},
        "desc": "Your keeper has the ball. Build the full shape and find the striker in space.",
        "why": "Both full-backs are wide for a short pass. The midfielder is free in the middle. The wingers stay wide. The striker finds the gap beside their striker.",
        "mistake": "A bunched team gives the keeper no pass, and a striker stuck to a defender cannot receive.",
        "tip": "Spread the full shape. Leave the striker in the gap.",
    },
    {
        "section": "balance",
        "title": "Wide, but compact",
        "difficulty": "medium",
        "ball": ("rw", (90, 66)),
        "places": {"gk": (50, 14), "lb": (49, 41), "rb": (72, 49), "cdm": (60, 73), "lw": (23, 67), "st": (71, 90)},
        "desc": "The ball is high on the right. Stay compact, and attack the goal.",
        "why": "The left back tucks in. The right back is the pass behind the ball. The left winger comes inside. The midfielder supports underneath, and the striker attacks the space beside their left back.",
        "mistake": "A team stretched to both touchlines leaves gaps, and a deep striker wastes the cross.",
        "tip": "Stay close enough to pass. Send the striker in beside their left back.",
    },
    {
        "section": "balance",
        "title": "Wide left, cover in",
        "difficulty": "hard",
        "ball": ("lw", (12, 66)),
        "places": {"gk": (50, 14), "lb": (36, 51), "rb": (74, 49), "cdm": (40, 75), "rw": (75, 75), "st": (41, 88)},
        "desc": "The ball is high on the left. Stay wide on the ball side, cover in, and attack the goal.",
        "why": "The left back supports the ball. The right back covers on the far side. The midfielder supports underneath their striker. The striker attacks the space in the goal, and the right winger comes inside.",
        "mistake": "A right back stuck on the touchline leaves the middle open, and a deep striker wastes the cross.",
        "tip": "Cover in from the right. Send the striker into the goal and bring the far winger inside.",
    },
    {
        "section": "balance",
        "title": "Attack and leave cover",
        "difficulty": "hard",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (36, 37), "rb": (84, 50), "cdm": (59, 76), "lw": (27, 83), "rw": (71, 90)},
        "desc": "Your striker has the ball and can score. Attack the goal, and leave cover behind.",
        "why": "The keeper and the left back stay behind to cover. The right back steps up on the right. The midfielder supports the ball. The left winger and the right winger attack the space in the goal.",
        "mistake": "Everyone rushing into the box leaves no cover, and wingers stuck wide give the striker no help.",
        "tip": "Leave the keeper and one full-back behind. Send both wingers into the goal.",
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
