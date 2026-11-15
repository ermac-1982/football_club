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
        "blurb": "Stay close enough for a short pass.",
    },
    {
        "id": "cover",
        "title": "Cover the space",
        "kicker": "COVER",
        "mode": "positions",
        "blurb": "The far players tuck in and protect the middle.",
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

_DRILLS = [
    {
        "section": "diamond",
        "title": "Keeper's diamond",
        "difficulty": "easy",
        "ball": ("gk", (50, 14)),
        "places": {"lb": (32, 32), "rb": (68, 32), "cdm": (50, 48), "lw": (28, 64), "rw": (72, 64), "st": (50, 78)},
        "desc": "Your keeper has the ball. Drag the other six into two diamonds.",
        "why": "The left back, right back, and midfielder make a diamond with the keeper. The wingers and the striker make a second diamond in front of the midfielder.",
        "mistake": "A flat line leaves the keeper with no easy pass at an angle.",
        "tip": "A diamond has a player behind the ball, one on each side, and one ahead.",
    },
    {
        "section": "diamond",
        "title": "Midfielder's diamond",
        "difficulty": "easy",
        "ball": ("cdm", (50, 48)),
        "places": {"gk": (50, 16), "lb": (34, 34), "rb": (66, 34), "lw": (32, 64), "rw": (68, 64), "st": (50, 76)},
        "desc": "Your midfielder has the ball in the middle. Build a diamond around them.",
        "why": "A defender sits each side behind the ball, a winger each side ahead of it, and the striker is the point. The keeper is the player behind the diamond.",
        "mistake": "Standing in a row beside the ball blocks the pass.",
        "tip": "Around the ball: one behind, one each side, and one ahead.",
    },
    {
        "section": "diamond",
        "title": "Diamond on the wing",
        "difficulty": "medium",
        "ball": ("rw", (78, 62)),
        "places": {"gk": (50, 16), "lb": (28, 34), "rb": (70, 44), "cdm": (58, 54), "lw": (30, 58), "st": (62, 76)},
        "desc": "Your right winger has the ball near the side. Make a diamond on that side.",
        "why": "The right back is behind the ball, the midfielder is inside, and the striker is ahead. That is the diamond. The left side stays in its own lane.",
        "mistake": "Everyone rushing to the ball crowds the winger.",
        "tip": "On the wing, the diamond is behind, inside, and ahead of the ball.",
    },
    {
        "section": "diamond",
        "title": "Striker's diamond",
        "difficulty": "medium",
        "ball": ("st", (50, 76)),
        "places": {"gk": (50, 16), "lb": (34, 36), "rb": (66, 36), "cdm": (50, 52), "lw": (32, 64), "rw": (68, 64)},
        "desc": "Your striker has the ball near the other goal. Put a diamond behind them.",
        "why": "Both wingers sit just behind the striker, with the midfielder behind them. The defenders and the keeper hold the rest of the shape.",
        "mistake": "Joining the striker in a bunch leaves no pass back.",
        "tip": "When the striker has the ball, the next diamond is just behind them.",
    },
    {
        "section": "compact",
        "title": "Stay close to the keeper",
        "difficulty": "easy",
        "ball": ("gk", (50, 14)),
        "places": {"lb": (38, 28), "rb": (62, 28), "cdm": (50, 40), "lw": (36, 50), "rw": (64, 50), "st": (50, 60)},
        "desc": "Your keeper has the ball. The team is too spread out. Pull the other six in.",
        "why": "Everyone stays in your own half, close enough for a short pass. The striker does not wait on the halfway line.",
        "mistake": "A teammate on the halfway line is too far for a short pass from the keeper.",
        "tip": "Compact means a teammate can receive a short pass.",
    },
    {
        "section": "compact",
        "title": "Slide together",
        "difficulty": "medium",
        "ball": ("lw", (24, 58)),
        "places": {"gk": (40, 16), "lb": (26, 40), "rb": (48, 38), "cdm": (38, 50), "rw": (46, 66), "st": (36, 72)},
        "desc": "Your left winger has the ball. Slide the team across and stay close.",
        "why": "The right winger and the right back come across. Nobody is left on the far side, too far to help.",
        "mistake": "Leaving a player on the far touchline makes the team too wide.",
        "tip": "When the ball moves, the whole team moves with it.",
    },
    {
        "section": "compact",
        "title": "No big gaps",
        "difficulty": "medium",
        "ball": ("cdm", (50, 48)),
        "places": {"gk": (50, 16), "lb": (36, 34), "rb": (64, 34), "lw": (36, 62), "rw": (64, 62), "st": (50, 72)},
        "desc": "Your midfielder has the ball. Close the gaps between the lines.",
        "why": "Defenders, midfielder, wingers, and striker sit in even steps. A big hole between them is where the other team steps in.",
        "mistake": "A gap between the defenders and the striker is an easy place to lose the ball.",
        "tip": "If you can see a big empty patch between your players, move someone into it.",
    },
    {
        "section": "compact",
        "title": "Compact near the goal",
        "difficulty": "hard",
        "ball": ("rw", (76, 70)),
        "places": {"gk": (50, 18), "lb": (46, 42), "rb": (68, 52), "cdm": (60, 58), "lw": (52, 68), "st": (64, 80)},
        "desc": "Your right winger has the ball by the box. Bring the attack in tight.",
        "why": "The striker, the left winger, and the midfielder stay close to the ball. The defenders step up, and the keeper stays back.",
        "mistake": "Spreading across the box makes the pass too far.",
        "tip": "Near the goal, short passes need a tight shape.",
    },
    {
        "section": "cover",
        "title": "Tuck the far back",
        "difficulty": "easy",
        "ball": ("lw", (18, 60)),
        "places": {"gk": (46, 16), "lb": (26, 42), "rb": (54, 40), "cdm": (40, 50), "rw": (56, 64), "st": (42, 74)},
        "desc": "The ball is with your left winger. Your right side is too wide.",
        "why": "The right back slides into the middle to cover the goal. The right winger tucks in too. The near players stay close to the ball.",
        "mistake": "A right back who stays wide leaves the middle open.",
        "tip": "The defender farthest from the ball tucks in and protects the middle.",
    },
    {
        "section": "cover",
        "title": "Cover from the left",
        "difficulty": "medium",
        "ball": ("rw", (82, 60)),
        "places": {"gk": (54, 16), "lb": (46, 40), "rb": (74, 42), "cdm": (60, 50), "lw": (44, 64), "st": (58, 74)},
        "desc": "Your right winger has the ball. Cover the middle from the left.",
        "why": "The left back and the left winger come inside, between the ball and your goal. They can stop a break if the ball is lost.",
        "mistake": "Staying wide on the far side leaves the path to your goal empty.",
        "tip": "Cover means being between the ball and your own goal.",
    },
    {
        "section": "cover",
        "title": "Protect the middle",
        "difficulty": "medium",
        "ball": ("lb", (30, 36)),
        "places": {"gk": (50, 14), "rb": (62, 32), "cdm": (48, 48), "lw": (28, 56), "rw": (66, 58), "st": (50, 72)},
        "desc": "Your left back has the ball. The middle of the pitch must not be empty.",
        "why": "The midfielder moves into the centre, in front of your goal. The right back holds the other side of that space.",
        "mistake": "If the middle is empty, one pass can split the team.",
        "tip": "When a defender has the ball, a midfielder covers the middle.",
    },
    {
        "section": "cover",
        "title": "Numbers behind the ball",
        "difficulty": "hard",
        "ball": ("st", (58, 76)),
        "places": {"gk": (50, 16), "lb": (34, 40), "rb": (66, 40), "cdm": (52, 56), "lw": (40, 64), "rw": (74, 66)},
        "desc": "Your striker has the ball near goal. Keep players behind the ball.",
        "why": "The midfielder, both defenders, and the keeper stay closer to your goal than the ball. If the move breaks down, they are already covering.",
        "mistake": "Everyone rushing past the ball leaves nothing behind it.",
        "tip": "Keep more players behind the ball than ahead of it.",
    },
    {
        "section": "balance",
        "title": "The full shape",
        "difficulty": "medium",
        "ball": ("gk", (50, 14)),
        "places": {"lb": (34, 32), "rb": (66, 32), "cdm": (50, 46), "lw": (32, 60), "rw": (68, 60), "st": (50, 74)},
        "desc": "Your keeper has the ball. Make the diamonds, keep them close, and cover the middle.",
        "why": "Two diamonds, short gaps, and the defenders narrow enough to protect the goal.",
        "mistake": "A stretched team loses the diamond and the cover at the same time.",
        "tip": "Diamond, compact, cover. Check all three.",
    },
    {
        "section": "balance",
        "title": "Wide, but compact",
        "difficulty": "medium",
        "ball": ("rw", (80, 62)),
        "places": {"gk": (52, 16), "lb": (44, 36), "rb": (70, 44), "cdm": (60, 52), "lw": (48, 62), "st": (64, 76)},
        "desc": "The ball is wide on the right. Make a diamond there, and keep the rest of the team close.",
        "why": "The right back is behind, the midfielder is inside, and the striker is ahead. The left players slide across so the team stays compact and the middle is covered.",
        "mistake": "A diamond on the wing, with the other players stuck wide, is still a broken shape.",
        "tip": "Build the diamond beside the ball, then check the far side has come across.",
    },
    {
        "section": "balance",
        "title": "Wide left, cover in",
        "difficulty": "hard",
        "ball": ("lw", (20, 62)),
        "places": {"gk": (48, 16), "lb": (28, 44), "rb": (56, 38), "cdm": (40, 52), "rw": (54, 64), "st": (36, 76)},
        "desc": "The ball is wide on the left. Diamond on that side, and cover in the middle.",
        "why": "The left back is behind the ball, the midfielder is inside, and the striker is ahead. The right back tucks into the middle to cover.",
        "mistake": "The far defender staying wide leaves the goal unprotected.",
        "tip": "Far from the ball means tuck in, not stay wide.",
    },
    {
        "section": "balance",
        "title": "Attack and leave cover",
        "difficulty": "hard",
        "ball": ("st", (54, 76)),
        "places": {"gk": (50, 16), "lb": (32, 38), "rb": (64, 36), "cdm": (50, 54), "lw": (36, 64), "rw": (68, 66)},
        "desc": "Your striker has the ball in the box. Join in, but leave a cover behind.",
        "why": "The wingers make the diamond just behind the striker. The midfielder and the defenders stay behind the ball, so a lost ball is not a free run at goal.",
        "mistake": "Six players in the box leaves the keeper alone.",
        "tip": "Attack with a diamond, and always leave players behind the ball.",
    },
]


def _clamp(value: float, low: float = 8, high: float = 94) -> float:
    return max(low, min(high, value))


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


_DEFEND_SLOTS = ((50, 94), (16, 86), (84, 86), (34, 90), (66, 90), (8, 94), (92, 94))


def _free_spot(x: float, y: float, blocked: list[tuple[float, float]]) -> tuple[float, float]:
    for radius in (0, 12, 18, 24):
        for angle in range(0, 360, 20):
            rad = math.radians(angle)
            spot = (_clamp(x + radius * math.cos(rad), 8, 94), _clamp(y + radius * math.sin(rad) * 0.35, 82, 94))
            if all(_dist(spot, other) >= 11 for other in blocked):
                return spot
    return (_clamp(x), _clamp(y, 82, 94))


def _opponents(blocked: list[tuple[float, float]]) -> dict[str, tuple[float, float]]:
    chosen = []
    keys = ("dgk", "dl", "dr", "dcm", "dlw", "drw", "dst")
    for key, (x, y) in zip(keys, _DEFEND_SLOTS):
        spot = _free_spot(x, y, blocked + chosen)
        chosen.append(spot)
    return dict(zip(keys, chosen))


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
    defend = _opponents([attack[carrier], *correct.values()])
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
