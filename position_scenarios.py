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
        "places": {"lb": (14, 34), "rb": (86, 34), "cdm": (50, 48), "lw": (12, 64), "rw": (88, 62), "st": (72, 72)},
        "desc": "Your keeper has the ball. Build two wide diamonds that finish with the striker in the gap.",
        "why": "The full-backs stay wide for the first pass. The wingers are high and wide, ready to attack. The striker is in the space between their midfielder and their left winger.",
        "mistake": "A flat line, or a striker left in your own half, gives the keeper no forward pass.",
        "tip": "Play forward. The wingers and the striker are there to attack the goal.",
    },
    {
        "section": "diamond",
        "title": "Midfielder's diamond",
        "difficulty": "easy",
        "ball": ("cdm", (62, 52)),
        "places": {"gk": (50, 14), "lb": (16, 42), "rb": (84, 42), "lw": (14, 68), "rw": (90, 64), "st": (72, 72)},
        "desc": "Your midfielder has the ball and can turn. The wingers and the striker attack the goal.",
        "why": "The striker is in the gap between their midfielder and their left winger. Both wingers are high and wide, so the pass forward can end in a shot. The full-backs have stepped up to join.",
        "mistake": "Wingers stuck beside the ball, or a striker stood on the midfielder, leaves no one to score.",
        "tip": "Pass forward into the gap. The wingers stay high so they can attack with the striker.",
    },
    {
        "section": "diamond",
        "title": "Diamond on the wing",
        "difficulty": "medium",
        "ball": ("rw", (88, 66)),
        "places": {"gk": (50, 14), "lb": (18, 44), "rb": (74, 52), "cdm": (38, 52), "lw": (16, 66), "st": (68, 74)},
        "desc": "Your right winger has the ball, ready to cross. Give them a striker to aim at and a player at the far side.",
        "why": "The striker attacks the gap in front of goal. The left winger is at the far side. The right back and the midfielder are close enough to help, with a gap so they are not in the way.",
        "mistake": "A striker left deep, or four players stood on the winger, means the cross has nowhere to go.",
        "tip": "Cross towards the striker. Keep one player at the far side of the goal.",
    },
    {
        "section": "diamond",
        "title": "Striker's diamond",
        "difficulty": "medium",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (18, 46), "rb": (82, 44), "cdm": (58, 50), "lw": (14, 68), "rw": (90, 64)},
        "desc": "Your striker has the ball and can score. Get the wingers and the midfielder up to help.",
        "why": "The right winger is the pass beside the striker. The left winger attacks the far side of the goal. The midfielder is underneath for a one-two. The full-backs step up so there is still a pass back.",
        "mistake": "Leaving the striker alone means there is no one to pass to and no one arriving at the goal.",
        "tip": "When the striker can shoot, the wingers attack with them.",
    },
    {
        "section": "compact",
        "title": "Stay close to the keeper",
        "difficulty": "easy",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (14, 32), "rb": (86, 32), "cdm": (50, 46), "lw": (12, 60), "rw": (88, 58), "st": (70, 68)},
        "desc": "Your keeper has the ball. Keep the lines close, and keep the attack high.",
        "why": "The full-backs and the midfielder are close enough for a short pass. The wingers stay high and wide, and the striker is already in the gap.",
        "mistake": "Dropping the striker and the wingers next to the keeper wastes the attack.",
        "tip": "Short passes through the team, with the attack already near their goal.",
    },
    {
        "section": "compact",
        "title": "Slide together",
        "difficulty": "medium",
        "ball": ("lw", (12, 66)),
        "places": {"gk": (46, 14), "lb": (24, 50), "rb": (80, 46), "cdm": (46, 56), "rw": (88, 64), "st": (32, 74)},
        "desc": "Your left winger has the ball, ready to cross. Slide the attack across with them.",
        "why": "The striker attacks the gap on the left. The right winger stays high on the far side of the goal. The left back and the midfielder are close enough to help.",
        "mistake": "Leaving the striker and the far winger deep means the cross has no one to find.",
        "tip": "Move up with the ball. Someone attacks the goal, and someone stays on the far side.",
    },
    {
        "section": "compact",
        "title": "No big gaps",
        "difficulty": "medium",
        "ball": ("cdm", (58, 50)),
        "places": {"gk": (50, 16), "lb": (14, 38), "rb": (86, 38), "lw": (14, 64), "rw": (88, 62), "st": (72, 72)},
        "desc": "Your midfielder has the ball. Keep every line close enough to pass, right up to the striker.",
        "why": "The full-backs, the wingers, and the striker are a short step apart. The striker is in the gap, so the last pass is a chance to score.",
        "mistake": "A big empty patch in front of the midfielder leaves the striker alone.",
        "tip": "Connect the lines. The striker is the last pass, in the gap.",
    },
    {
        "section": "compact",
        "title": "Compact near the goal",
        "difficulty": "hard",
        "ball": ("rw", (88, 66)),
        "places": {"gk": (50, 14), "lb": (18, 44), "rb": (74, 50), "cdm": (38, 52), "lw": (16, 64), "st": (68, 74)},
        "desc": "Your right winger has the ball near their goal. The striker and the far winger attack the goal with them.",
        "why": "The striker is in the gap to finish. The left winger attacks the far side. The right back is the pass behind the ball, close enough to help and far enough to stay out of the way.",
        "mistake": "Dropping the striker back, or standing the whole team on the winger, wastes the chance.",
        "tip": "Near their goal, the striker and both wingers stay high.",
    },
    {
        "section": "cover",
        "title": "Tuck the far back",
        "difficulty": "easy",
        "ball": ("lw", (12, 66)),
        "places": {"gk": (50, 14), "lb": (24, 48), "rb": (64, 42), "cdm": (44, 50), "rw": (88, 64), "st": (32, 74)},
        "desc": "Your left winger can cross. The far full-back tucks in, and the attack stays high.",
        "why": "The striker attacks the gap on the left. The right winger stays high and wide. The right back slides inside to cover, but the rest of the team is up to help the goal.",
        "mistake": "A far full-back stuck on the touchline leaves the middle open. Dropping the striker does not help the cross.",
        "tip": "Tuck the far full-back in. Keep the striker and the far winger attacking.",
    },
    {
        "section": "cover",
        "title": "Cover from the left",
        "difficulty": "medium",
        "ball": ("rw", (88, 66)),
        "places": {"gk": (50, 14), "lb": (32, 40), "rb": (74, 50), "cdm": (54, 44), "lw": (14, 64), "st": (68, 74)},
        "desc": "Your right winger can cross. Cover the middle from the left, and attack the goal.",
        "why": "The left back tucks inside, between the ball and your goal. The left winger still attacks the far side. The striker is in the gap to finish.",
        "mistake": "If the far full-back stays wide and the striker stays deep, the cross and the goal are both left open.",
        "tip": "One player covers. The striker and the far winger go to score.",
    },
    {
        "section": "cover",
        "title": "Protect the middle",
        "difficulty": "medium",
        "ball": ("lb", (16, 46)),
        "places": {"gk": (50, 14), "rb": (82, 44), "cdm": (42, 50), "lw": (12, 66), "rw": (88, 64), "st": (32, 74)},
        "desc": "Your left back has the ball and can play forward. Protect the middle, and send the attack at their goal.",
        "why": "The midfielder is free in the centre to receive and pass. The left winger and the striker attack the left gap. The right winger stays high on the far side.",
        "mistake": "An empty middle, or an attack left in your own half, wastes the pass forward.",
        "tip": "The midfielder shows for the ball. The striker and the wingers stay high.",
    },
    {
        "section": "cover",
        "title": "Numbers behind the ball",
        "difficulty": "hard",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (18, 42), "rb": (78, 44), "cdm": (54, 54), "lw": (16, 62), "rw": (88, 60)},
        "desc": "Your striker has the ball and can score. Stay behind the ball, but stay close enough to help.",
        "why": "Both wingers are just behind the striker, wide, so they can receive and shoot. The midfielder is the pass underneath. The full-backs are up, still behind the ball.",
        "mistake": "Dropping back to your own goal leaves the striker with no pass and no support.",
        "tip": "Behind the ball still means close enough to join the attack.",
    },
    {
        "section": "balance",
        "title": "The full shape",
        "difficulty": "medium",
        "ball": ("gk", (50, 12)),
        "places": {"lb": (14, 36), "rb": (86, 36), "cdm": (50, 50), "lw": (12, 66), "rw": (90, 60), "st": (72, 72)},
        "desc": "Your keeper has the ball. Build the attack all the way to the striker.",
        "why": "The full-backs and the midfielder give a short pass forward. The wingers are high and wide. The striker is in the gap, ready to score.",
        "mistake": "A striker or a winger left in your own half wastes the chance.",
        "tip": "Width at the back, and the attack already near their goal.",
    },
    {
        "section": "balance",
        "title": "Wide, but compact",
        "difficulty": "medium",
        "ball": ("rw", (90, 66)),
        "places": {"gk": (50, 14), "lb": (18, 44), "rb": (74, 50), "cdm": (38, 52), "lw": (14, 64), "st": (68, 74)},
        "desc": "The ball is high on the right. Stay close enough to pass, and attack their goal.",
        "why": "The striker is in the gap to finish. The left winger attacks the far side. The right back and the midfielder are a short pass away, not stood on the winger.",
        "mistake": "A deep striker, or a bunch on the ball, leaves no one to score.",
        "tip": "Help the cross from close by, and give the striker space in the gap.",
    },
    {
        "section": "balance",
        "title": "Wide left, cover in",
        "difficulty": "hard",
        "ball": ("lw", (12, 66)),
        "places": {"gk": (50, 14), "lb": (24, 48), "rb": (70, 38), "cdm": (50, 46), "rw": (88, 64), "st": (32, 74)},
        "desc": "The ball is high on the left. Help the cross, cover the middle, and attack the goal.",
        "why": "The striker attacks the left gap. The right winger stays high and wide. The right back tucks in to cover, while the left back and the midfielder support the ball.",
        "mistake": "A far full-back on the touchline, or a striker left behind, wastes the attack.",
        "tip": "Cover with the far full-back. Everyone else helps the striker score.",
    },
    {
        "section": "balance",
        "title": "Attack and leave cover",
        "difficulty": "hard",
        "ball": ("st", (72, 72)),
        "places": {"gk": (50, 14), "lb": (16, 40), "rb": (82, 42), "cdm": (56, 56), "lw": (14, 66), "rw": (90, 64)},
        "desc": "Your striker has the ball and can score. The wingers join the attack, and the full-backs stay behind them.",
        "why": "Both wingers are high and wide, ready to receive and shoot. The midfielder is the pass underneath. The full-backs step up, but they stay behind the ball so the keeper is not alone.",
        "mistake": "Leaving the wingers deep leaves the striker with no one to pass to.",
        "tip": "Attack with the wingers. Leave the full-backs behind the ball.",
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
