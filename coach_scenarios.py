"""Situational Coach scenario library. Edit this file to add a drill."""

from __future__ import annotations

import math

SECTIONS = [
    {
        "id": "support",
        "title": "Building and supporting",
        "kicker": "SUPPORT",
        "mode": "positioning",
        "blurb": "Move so a teammate has someone to pass to.",
    },
    {
        "id": "build-decide",
        "title": "Building from the back",
        "kicker": "BUILD",
        "mode": "decision",
        "blurb": "Choose the pass that starts the attack.",
    },
    {
        "id": "space",
        "title": "Creating space",
        "kicker": "SPACE",
        "mode": "positioning",
        "blurb": "Move to open a gap or stretch the other team.",
    },
    {
        "id": "passing",
        "title": "Passing combinations",
        "kicker": "PASS",
        "mode": "decision",
        "blurb": "Find the free player and keep the move going.",
    },
    {
        "id": "attack-move",
        "title": "Attacking movement",
        "kicker": "ATTACK",
        "mode": "positioning",
        "blurb": "Run into the box at the right moment.",
    },
    {
        "id": "final-third",
        "title": "Final third",
        "kicker": "FINISH",
        "mode": "decision",
        "blurb": "Pick the best action near the goal.",
    },
    {
        "id": "defend",
        "title": "Defensive organisation",
        "kicker": "DEFEND",
        "mode": "positioning",
        "blurb": "Get goal-side and protect the middle.",
    },
    {
        "id": "press",
        "title": "Pressing",
        "kicker": "PRESS",
        "mode": "positioning",
        "blurb": "Close the ball and block the easy pass.",
    },
    {
        "id": "gk-pos",
        "title": "Goalkeeper build-up",
        "kicker": "KEEPER",
        "mode": "positioning",
        "blurb": "Help your keeper start the attack.",
    },
    {
        "id": "gk-decide",
        "title": "Keeper distribution",
        "kicker": "KEEPER",
        "mode": "decision",
        "blurb": "Help the keeper find a free player.",
    },
    {
        "id": "trans-pos",
        "title": "Transition runs",
        "kicker": "SWITCH",
        "mode": "positioning",
        "blurb": "React fast when the ball changes team.",
    },
    {
        "id": "trans-decide",
        "title": "Transition choices",
        "kicker": "SWITCH",
        "mode": "decision",
        "blurb": "Attack quickly, or slow the other team down.",
    },
    {
        "id": "adv-move",
        "title": "Advanced movement",
        "kicker": "ADVANCED",
        "mode": "positioning",
        "blurb": "Rotate, then play into the space you made.",
    },
    {
        "id": "adv-decide",
        "title": "Advanced decisions",
        "kicker": "ADVANCED",
        "mode": "decision",
        "blurb": "Read the numbers, then pick the smart action.",
    },
]

SECTION_CATEGORY = {
    "support": "building",
    "build-decide": "building",
    "space": "supporting",
    "passing": "supporting",
    "attack-move": "attacking",
    "final-third": "attacking",
    "defend": "defending",
    "press": "pressing",
    "gk-pos": "goalkeeper",
    "gk-decide": "goalkeeper",
    "trans-pos": "transition",
    "trans-decide": "transition",
    "adv-move": "advanced",
    "adv-decide": "advanced",
}

ROLES = {
    "gk": ("GK", "Goalkeeper", True),
    "lb": ("LB", "Left back", False),
    "rb": ("RB", "Right back", False),
    "cdm": ("CM", "Midfielder", False),
    "lw": ("LW", "Left winger", False),
    "rw": ("RW", "Right winger", False),
    "st": ("ST", "Striker", False),
    "dgk": ("GK", "Keeper", True),
    "dr": ("RB", "Right back", False),
    "dl": ("LB", "Left back", False),
    "dcm": ("CM", "Midfielder", False),
    "drw": ("RW", "Right winger", False),
    "dlw": ("LW", "Left winger", False),
    "dst": ("ST", "Striker", False),
}

ATTACK = {
    "gk": (50, 8),
    "lb": (18, 24),
    "rb": (82, 24),
    "cdm": (50, 42),
    "lw": (12, 58),
    "rw": (88, 58),
    "st": (50, 74),
}
DEFEND = {
    "dgk": (50, 94),
    "dr": (24, 84),
    "dl": (76, 84),
    "dcm": (62, 68),
    "drw": (14, 70),
    "dlw": (88, 74),
    "dst": (36, 56),
}

_SECTION = "support"
_ROWS: list[dict] = []


def _use(section: str) -> None:
    global _SECTION
    _SECTION = section


def _clamp(value: float, low: float = 8, high: float = 92) -> float:
    return max(low, min(high, value))


def _push(x: float, y: float, ax: float, ay: float, minimum: float) -> tuple[float, float]:
    dx, dy = x - ax, y - ay
    dist = math.hypot(dx, dy) or 0.01
    if dist >= minimum:
        return x, y
    scale = minimum / dist
    return ax + dx * scale, ay + dy * scale


def _spread(groups: list[dict[str, tuple[float, float]]], anchors: list[tuple[float, float]], pinned: set[str]) -> None:
    for _ in range(24):
        moved = False
        for players in groups:
            for pid in list(players):
                if pid in pinned:
                    continue
                x, y = players[pid]
                for ax, ay in anchors:
                    x, y = _push(x, y, ax, ay, 8)
                players[pid] = (_clamp(x), _clamp(y))
        members: list[tuple[dict, str]] = []
        for players in groups:
            members.extend((players, pid) for pid in players)
        for index, (players, pid) in enumerate(members):
            x, y = players[pid]
            for other_players, other in members[index + 1 :]:
                ox, oy = other_players[other]
                dist = math.hypot(x - ox, y - oy)
                if dist >= 7.5:
                    continue
                if pid not in pinned:
                    x, y = _push(x, y, ox, oy, 7.5)
                    moved = True
                if other not in pinned:
                    ox, oy = _push(ox, oy, x, y, 7.5)
                    other_players[other] = (_clamp(ox), _clamp(oy))
                    moved = True
            players[pid] = (_clamp(x), _clamp(y))
        if not moved:
            break
    _park(groups, pinned, anchors)


def _too_close(x: float, y: float, others: list[tuple[float, float]], minimum: float = 7.5) -> bool:
    return any(math.hypot(x - ox, y - oy) < minimum for ox, oy in others)


def _park(groups: list[dict[str, tuple[float, float]]], pinned: set[str], anchors: list[tuple[float, float]]) -> None:
    for players in groups:
        for pid in list(players):
            if pid in pinned:
                continue
            others = [
                pos
                for group in groups
                for other, pos in group.items()
                if not (group is players and other == pid)
            ] + list(anchors)
            x, y = players[pid]
            if not _too_close(x, y, others):
                continue
            found = None
            for radius in range(4, 48, 2):
                for angle in range(0, 360, 15):
                    rad = math.radians(angle)
                    nx = _clamp(x + radius * math.cos(rad))
                    ny = _clamp(y + radius * math.sin(rad))
                    if not _too_close(nx, ny, others):
                        found = (nx, ny)
                        break
                if found:
                    break
            if found:
                players[pid] = found


def _pack(players: dict[str, tuple[float, float]], team: str) -> list[dict]:
    rows = []
    for pid, (x, y) in players.items():
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


def _finish(row: dict, attack: dict, defend: dict, pinned: set[str], anchors: list[tuple[float, float]], ball_on: str) -> dict:
    _spread([attack, defend], anchors, pinned)
    bx, by = attack[ball_on] if ball_on in attack else defend[ball_on]
    row["attackingPlayers"] = _pack(attack, "attack")
    row["defendingPlayers"] = _pack(defend, "defend")
    row["ballPosition"] = {"x": round(_clamp(bx + 3, 4, 96), 1), "y": round(_clamp(by + 2, 4, 96), 1)}
    row["formation"] = "2-1-2-1"
    return row


def move(
    title: str,
    who: str,
    start: tuple[float, float],
    correct: tuple[float, float],
    ball: str,
    desc: str,
    why: str,
    mistake: str,
    tip: str,
    difficulty: str = "easy",
    topics: tuple[str, ...] = (),
    attack: dict | None = None,
    defend: dict | None = None,
    zones: tuple[tuple[float, float, float, int], ...] = (),
) -> None:
    attack_pos = dict(ATTACK)
    defend_pos = dict(DEFEND)
    attack_pos.update(attack or {})
    defend_pos.update(defend or {})
    attack_pos[who] = start
    pinned = set(attack or {}) | set(defend or {}) | {who, "gk", "dgk"}
    category = SECTION_CATEGORY[_SECTION]
    section = next(item for item in SECTIONS if item["id"] == _SECTION)
    row = {
        "id": len(_ROWS) + 1,
        "title": title,
        "description": desc,
        "mode": "positioning",
        "category": category,
        "topics": list(topics or (category,)),
        "difficulty": difficulty,
        "section": _SECTION,
        "highlightedPlayerId": who,
        "correctPosition": {"x": correct[0], "y": correct[1]},
        "acceptablePositionZones": [
            {"x": zone[0], "y": zone[1], "radius": zone[2], "score": zone[3]} for zone in zones
        ],
        "availableActions": [],
        "correctAction": None,
        "targetPlayerId": None,
        "alternativeActions": [],
        "explanation": why,
        "incorrectExplanation": mistake,
        "coachingTip": tip,
    }
    _ROWS.append(
        _finish(
            row,
            attack_pos,
            defend_pos,
            pinned,
            [correct, start],
            ball,
        )
    )
    row["mode"] = section["mode"]


def decide(
    title: str,
    who: str,
    where: tuple[float, float],
    correct: tuple[str, str | None],
    alts: list[tuple[str, str | None, int]],
    desc: str,
    why: str,
    mistake: str,
    tip: str,
    difficulty: str = "easy",
    topics: tuple[str, ...] = (),
    attack: dict | None = None,
    defend: dict | None = None,
    shoot: bool = False,
) -> None:
    attack_pos = dict(ATTACK)
    defend_pos = dict(DEFEND)
    attack_pos.update(attack or {})
    defend_pos.update(defend or {})
    attack_pos[who] = where
    pinned = set(attack or {}) | set(defend or {}) | {who, "gk", "dgk"}
    category = SECTION_CATEGORY[_SECTION]
    actions = ["pass", "dribble"] + (["shoot"] if shoot or correct[0] == "shoot" or any(item[0] == "shoot" for item in alts) else [])
    row = {
        "id": len(_ROWS) + 1,
        "title": title,
        "description": desc,
        "mode": "decision",
        "category": category,
        "topics": list(topics or (category,)),
        "difficulty": difficulty,
        "section": _SECTION,
        "highlightedPlayerId": who,
        "correctPosition": None,
        "acceptablePositionZones": [],
        "availableActions": actions,
        "correctAction": {"action": correct[0], "targetPlayerId": correct[1]},
        "targetPlayerId": correct[1],
        "alternativeActions": [
            {"action": action, "targetPlayerId": target, "score": score} for action, target, score in alts
        ],
        "explanation": why,
        "incorrectExplanation": mistake,
        "coachingTip": tip,
    }
    _ROWS.append(_finish(row, attack_pos, defend_pos, pinned, [where], who))


def _build() -> list[dict]:
    if _ROWS:
        return _ROWS
    _use("support")
    move("CDM drops deep", "cdm", (50, 70), (50, 46), "gk",
         "Your keeper has the ball. Your midfielder is standing too far up the pitch.",
         "Come back to just your side of the halfway line. The keeper can pass to you, and you stay out of the defenders' space.",
         "Dropping all the way between the defenders crowds the keeper. Staying too high makes the pass too long.",
         "When the keeper has the ball, show for it just below the halfway line.",
         difficulty="easy", attack={"lb": (28, 28), "rb": (72, 28)})
    move("Wide defender advances", "lb", (14, 22), (46, 36), "rw",
         "The ball is on the right. Your left back is stuck wide, away from the danger.",
         "Slide your left back across the pitch so they can cover the middle if the ball is lost.",
         "Staying wide leaves a big hole in front of your goal.",
         "The defender farthest from the ball tucks in and protects the middle.",
         difficulty="easy", attack={"rw": (86, 62), "rb": (74, 48)}, defend={"dlw": (80, 58)})
    move("Striker drops short", "st", (80, 90), (38, 69), "cdm",
         "Your midfielder has the ball and needs a friend. Your striker is waiting by the other goal.",
         "Move your striker into the gap between their right winger and their midfielder. Your midfielder can pass into that space.",
         "Dropping all the way back beside the ball, or staying by the goal, misses that gap.",
         "Come toward the ball, but stop between two opponents.",
         difficulty="easy", attack={"cdm": (50, 42)},
         defend={"drw": (14, 70), "dcm": (62, 68), "dst": (72, 86)})
    move("CM supports winger", "cdm", (36, 36), (70, 62), "rw",
         "Your right winger has the ball and a defender is closing in. Your midfielder is in the centre.",
         "Move the midfielder toward the winger. Now the winger can pass instead of trying to beat the defender alone.",
         "Staying in the centre leaves the winger with nobody close.",
         "When a winger is in trouble, a nearby midfielder gives them a way out.",
         difficulty="easy", topics=("building", "supporting"),
         attack={"rw": (86, 66)}, defend={"dlw": (78, 60)},
         zones=((62, 50, 8, 75),))
    move("CM overlaps winger", "cdm", (48, 40), (92, 72), "rw",
         "Your right winger has the ball near the side. There is space on the outside.",
         "Run your midfielder around the outside of the winger. They can receive the ball in space and go forward.",
         "Running inside crowds the winger and blocks the wide space.",
         "An overlap means running past your teammate on the outside.",
         difficulty="medium", attack={"rw": (74, 64)}, defend={"dl": (70, 78)})
    move("CM underlaps winger", "cdm", (40, 40), (64, 74), "rw",
         "Your right winger has the ball wide. There is a gap inside them, toward the goal.",
         "Send the midfielder on a run inside the winger. That run can get them in behind the defender.",
         "Staying behind the ball wastes the gap in front.",
         "An underlap is a forward run on the inside of the winger.",
         difficulty="medium", attack={"rw": (86, 62)}, defend={"dl": (78, 70), "dcm": (60, 80)})
    move("Striker supports winger", "st", (40, 86), (69, 76), "rw",
         "Your right winger is stopped near the side. Your striker is too far ahead.",
         "Move your striker into the gap between their left back and their midfielder. Your winger can then pass inside.",
         "Dropping beside the winger, or staying by the goal, misses the space between those two opponents.",
         "Look for the gap between two opponents. That is a good place to ask for the ball.",
         difficulty="medium", attack={"rw": (88, 60)},
         defend={"dl": (76, 84), "dcm": (62, 68), "dlw": (80, 56)})
    move("Defender supports winger", "rb", (70, 24), (80, 52), "rw",
         "Your right winger has the ball higher up. Your right back is still deep.",
         "Move the right back up behind the winger. If the winger passes back, the attack can continue.",
         "Leaving the right back on the edge of your own box gives the winger no backward pass.",
         "A defender can join the attack by moving up behind the winger.",
         difficulty="medium", attack={"rw": (86, 64)}, defend={"dlw": (74, 70)})
    move("Opposite winger moves central", "lw", (12, 58), (42, 78), "rw",
         "The ball is with your right winger, close to the other team's box. Your left winger is still wide.",
         "Bring the far winger into the box. They can attack the space near the goal.",
         "Staying wide on the far side leaves the box empty.",
         "When the ball is near one corner of the box, the far winger should arrive in the middle.",
         difficulty="medium", attack={"rw": (84, 74)}, defend={"dgk": (50, 94), "dl": (64, 80)})
    move("Diagonal support", "cdm", (30, 30), (62, 58), "lb",
         "Your left back has the ball and is looking forward. Your midfielder is behind them.",
         "Move the midfielder diagonally ahead of the ball so the left back can pass forward.",
         "A midfielder hiding behind the ball only offers a backward pass.",
         "A diagonal run opens a passing lane that a defender cannot easily block.",
         difficulty="hard", attack={"lb": (24, 40)}, zones=((70, 50, 7, 75),))
    move("Support from behind", "rb", (78, 58), (70, 36), "cdm",
         "Your midfielder is being closed down and needs a safe pass. Your right back has pushed on.",
         "Drop the right back behind the ball. A backward pass keeps the ball and lets you start again.",
         "Running further forward removes the safe pass.",
         "A teammate behind the ball is a reset button when you are in trouble.",
         difficulty="medium", attack={"cdm": (56, 48)}, defend={"dcm": (60, 58)})
    move("Two passing options", "cdm", (28, 36), (46, 58), "lb",
         "Your left back has the ball. Your striker is already ahead. Your midfielder is too far to the side.",
         "Move the midfielder so the left back can choose between the midfielder and the striker.",
         "If the midfielder stands next to the striker, the left back has only one pass.",
         "Two friends at different angles make a passing triangle.",
         difficulty="hard", attack={"lb": (22, 36), "st": (62, 70)},
         zones=((58, 48, 7, 75),))
    move("Support and rotate", "rw", (62, 40), (90, 78), "cdm",
         "You just passed inside. The midfielder has the ball, and the winger has stopped.",
         "The winger runs forward after the pass so the midfielder has a new player to find.",
         "Standing still after a pass lets the other team get organised.",
         "Pass, then move. The next pass is often for the player who just gave the ball.",
         difficulty="hard", attack={"cdm": (58, 56), "rw": (62, 40)}, defend={"dlw": (70, 86)})

    _use("build-decide")
    decide("Defender to CDM pivot", "rb", (76, 30), ("pass", "cdm"),
           [("pass", "rw", 75), ("pass", "gk", 75), ("dribble", None, 25)],
           "Your right back has the ball. A defender is coming. Your midfielder is free in the middle, and your right winger has space.",
           "Pass to your midfielder. They can turn and switch the ball to the other side. Passing to your right winger is also a very good choice.",
           "Dribbling into the closing defender gives the ball away.",
           "A free midfielder can change the direction of the attack. A free winger is another good pass.",
           difficulty="easy", attack={"cdm": (48, 42), "lw": (14, 62)}, defend={"dlw": (70, 40)})
    decide("CDM bounce pass", "lb", (24, 34), ("pass", "cdm"),
           [("pass", "gk", 50), ("dribble", None, 25)],
           "Your left back has the ball and an opponent is close. Your midfielder is facing you, ready to play it back.",
           "Pass to the midfielder and get it back. That one-touch pass moves the opponent and frees you.",
           "Dribbling past a close opponent is risky when a simple bounce pass is on.",
           "A bounce pass means giving it and getting it straight back.",
           difficulty="easy", attack={"cdm": (40, 42)}, defend={"drw": (30, 46)})
    decide("Striker as a pivot", "cdm", (52, 48), ("pass", "st"),
           [("pass", "rw", 50), ("dribble", None, 25)],
           "Your midfielder has the ball. Your striker can hold it up, and a winger is ready to spin out wide.",
           "Pass into the striker. They can protect the ball and lay it off to the winger.",
           "Ignoring the striker and dribbling into a crowd makes the attack slow.",
           "A striker with their back to goal can be the wall that sets up a winger.",
           difficulty="medium", attack={"st": (58, 66), "rw": (82, 60)}, defend={"dst": (60, 74)})
    decide("Defender carries forward", "rb", (74, 36), ("dribble", None),
           [("pass", "cdm", 75), ("pass", "rw", 50)],
           "Your right back has the ball and the space in front of them is empty.",
           "Dribble forward into the space. You do not have to pass when nobody is in front of you.",
           "Passing backwards when you have space wastes the chance to go forward.",
           "If the path ahead is empty, carry the ball.",
           difficulty="easy", attack={"rw": (88, 70)}, defend={"dlw": (40, 70), "dl": (48, 82)})
    decide("Switch through goalkeeper", "lb", (22, 32), ("pass", "gk"),
           [("pass", "cdm", 75), ("dribble", None, 0)],
           "Your left back is trapped near the side. The other team has crowded that side. Your keeper is free.",
           "Pass back to the keeper. They can send the ball to the other side, where you have space.",
           "Trying to dribble out of a crowded side often loses the ball.",
           "The keeper can be the player who switches the ball from one side to the other.",
           difficulty="medium", attack={"gk": (50, 10), "rw": (86, 58)}, defend={"drw": (28, 42), "dr": (30, 48)})
    decide("Third-man combination", "rb", (74, 32), ("pass", "cdm"),
           [("pass", "lb", 50), ("dribble", None, 25)],
           "Your right back has the ball. A straight pass to the far side may be blocked. Your midfielder is free.",
           "Pass to the midfielder first. They can play the ball on to the other defender.",
           "Forcing a long pass across the pitch is easy for the other team to cut out.",
           "Sometimes the best path to a teammate is through a third player.",
           difficulty="hard", attack={"cdm": (50, 40), "lb": (22, 30)}, defend={"dcm": (62, 50)})
    decide("Attract pressure", "cdm", (50, 46), ("dribble", None),
           [("pass", "lb", 75), ("pass", "st", 25)],
           "Your midfielder has time on the ball. An opponent is about to step toward them, which will free a defender.",
           "Hold the ball for a moment so the opponent comes closer, then you can pass to the free defender.",
           "Rushing a forward pass before the opponent moves keeps their defenders in good spots.",
           "Waiting for a second can pull an opponent out of position.",
           difficulty="hard", attack={"lb": (24, 30)}, defend={"dcm": (58, 58)})

    _use("space")
    move("Striker drags defender away", "st", (50, 74), (78, 70), "cdm",
         "Your midfielder wants to run into the middle. A defender is standing on your striker in the centre.",
         "The striker moves wide and takes that defender with them. The middle is now empty for the midfielder.",
         "Standing still in the centre keeps the defender in the important space.",
         "A striker can be a decoy. Moving away can be as helpful as moving toward the ball.",
         difficulty="easy", attack={"cdm": (46, 52)}, defend={"dst": (58, 82)})
    move("Winger holds width", "rw", (60, 64), (90, 62), "cdm",
         "The attack is getting narrow. Your right winger has come inside, and the side is empty.",
         "Stay wide. A winger on the touchline stretches the other team and opens gaps in the middle.",
         "Coming inside next to the striker makes the attack easy to defend.",
         "Width means staying near the side so the pitch feels big.",
         difficulty="easy", attack={"st": (52, 72), "cdm": (48, 50)})
    move("Winger moves inside", "rw", (90, 60), (64, 70), "lb",
         "Your left back is ready to run into the wide space. Your right winger is still glued to the touchline.",
         "The winger moves inside. That leaves the wide space free for the defender to run into.",
         "Two players stuck on the same touchline get in each other's way.",
         "If a teammate is overlapping, the winger can move inside to make room.",
         difficulty="medium", attack={"lb": (78, 48)})
    move("Decoy run", "lw", (18, 62), (40, 80), "rw",
         "Your right winger has the ball. A defender is watching your left winger.",
         "The left winger runs toward the box and pulls that defender away, so the ball carrier has more space.",
         "Standing still lets the defender watch both the ball and the space.",
         "A decoy run is a run that moves a defender, even if you never get the ball.",
         difficulty="medium", attack={"rw": (82, 64)}, defend={"drw": (24, 68)})
    move("Striker runs across defenders", "st", (30, 78), (68, 78), "lw",
         "Your left winger has the ball near the box. Two defenders are close together in the middle.",
         "The striker runs across the defenders. That move can confuse them and open one side of the box.",
         "Running straight at a defender makes the block easy.",
         "A sideways run across defenders is hard for them to follow.",
         difficulty="medium", attack={"lw": (16, 70)}, defend={"dr": (40, 80), "dl": (56, 80)})
    move("Opposite winger attacks back post", "lw", (16, 64), (38, 86), "rw",
         "A cross is coming from the right. Your left winger is still out wide, away from the far post.",
         "Run the far winger toward the far post so they can meet the cross.",
         "Staying wide means the cross arrives with nobody there.",
         "The far post is the back post. Attack it when the ball is coming from the other side.",
         difficulty="medium", attack={"rw": (86, 74)}, defend={"dgk": (54, 92)})
    move("CM arrives late", "cdm", (48, 40), (58, 78), "rw",
         "The ball is wide and the box is crowded. Your midfielder is still far from the goal.",
         "Time the midfielder's run so they arrive in the box as the cross comes in, not too early.",
         "Standing outside the box leaves a free shot unused.",
         "A late run into the box is hard for defenders to pick up.",
         difficulty="hard", attack={"rw": (84, 70), "st": (46, 82)}, defend={"dl": (68, 88)})
    move("Diagonal striker run", "st", (48, 64), (70, 86), "lw",
         "Your left winger has the ball. A defender is goalside of your striker.",
         "The striker runs diagonally behind that defender, into the space toward the goal.",
         "Running toward the ball keeps the striker in front of the defender.",
         "Attack the space behind a defender, not the defender's feet.",
         difficulty="hard", attack={"lw": (20, 66)}, defend={"dr": (52, 74)})
    move("Wingers exchange positions", "rw", (84, 58), (18, 64), "cdm",
         "The other team is set. Your wingers can swap sides while your midfielder has the ball.",
         "The right winger runs across to the left side. Swapping sides makes defenders unsure who to follow.",
         "Both wingers staying still makes the attack easy to mark.",
         "Switching places with a teammate can shake off a marker.",
         difficulty="hard", attack={"lw": (42, 82), "cdm": (50, 52)})
    move("Clear central space", "st", (50, 74), (80, 68), "cdm",
         "Your midfielder is about to drive forward. Your striker is standing in the space they want to run into.",
         "The striker moves out of the centre so the midfielder has room to carry the ball.",
         "Staying in the centre blocks your own teammate.",
         "If you are in a teammate's way, move and leave them the space.",
         difficulty="medium", attack={"cdm": (46, 56)}, defend={"dst": (52, 86)})

    _use("passing")
    decide("One-two", "cdm", (48, 50), ("pass", "st"),
           [("dribble", None, 50), ("pass", "lw", 25)],
           "Your midfielder is facing a defender. Your striker is close and can give the ball straight back.",
           "Pass to the striker, then run forward for the return. That is a one-two.",
           "Dribbling straight at the defender is harder than a quick pass and move.",
           "A one-two is a pass, a run, and a pass back.",
           difficulty="easy", attack={"st": (58, 60)}, defend={"dst": (52, 64)})
    decide("Wall pass with striker", "rw", (78, 64), ("pass", "st"),
           [("dribble", None, 50), ("pass", "cdm", 75)],
           "Your winger is stopped by a defender. The striker is close, side-on, ready to bounce the ball.",
           "Use the striker as a wall. Pass, run past the defender, and collect the return.",
           "Trying to dribble past a set defender loses the easy bounce pass.",
           "A wall pass uses a teammate's first touch to get you past a defender.",
           difficulty="easy", attack={"st": (66, 70)}, defend={"dlw": (82, 70)})
    decide("Third-man run", "cdm", (46, 52), ("pass", "st"),
           [("pass", "rw", 75), ("dribble", None, 25)],
           "Your winger is running forward. A pass straight to them may be cut off, but your striker can help.",
           "Pass to the striker. They can set the ball for the winger's run.",
           "Forcing the ball into a marked runner lets the defender step in.",
           "Look for the player who can help the runner, not only the runner.",
           difficulty="medium", attack={"st": (58, 64), "rw": (84, 74)}, defend={"dl": (74, 70)})
    decide("Switch of play", "lb", (22, 36), ("pass", "cdm"),
           [("pass", "lw", 25), ("dribble", None, 25)],
           "Your team is crowded on the left. Your right winger is free on the other side.",
           "Pass to the midfielder so they can switch the ball to the free winger.",
           "Playing again into the crowded side makes the other team's job easy.",
           "If one side is full, move the ball to the open side.",
           difficulty="medium", attack={"lw": (12, 50), "rw": (88, 62), "cdm": (50, 44)}, defend={"drw": (20, 48), "dr": (28, 42)})
    decide("Give and go", "rb", (72, 40), ("pass", "cdm"),
           [("dribble", None, 50), ("pass", "gk", 25)],
           "Your right back can pass to the midfielder and keep running forward into space.",
           "Give the ball to the midfielder and go. Ask for the return in front of you.",
           "Stopping after the pass wastes the space you were running into.",
           "Give and go means pass and move for the ball back.",
           difficulty="medium", attack={"cdm": (56, 48)}, defend={"dlw": (78, 56)})
    decide("Diagonal ball", "cdm", (42, 48), ("pass", "rw"),
           [("pass", "st", 75), ("dribble", None, 25)],
           "Your right winger is running in behind. A straight pass may be blocked, but a diagonal pass can find them.",
           "Play the diagonal pass into the winger's run.",
           "Dribbling slowly lets the defender get back and cover the run.",
           "A diagonal pass travels into the space a runner is attacking.",
           difficulty="hard", attack={"rw": (86, 72)}, defend={"dl": (70, 64)})
    decide("Striker lays off first time", "lw", (24, 66), ("pass", "st"),
           [("dribble", None, 25), ("pass", "cdm", 75)],
           "Your striker is facing you and your midfielder is free behind them.",
           "Pass into the striker. They can lay it off first time to the midfielder, who is facing the goal.",
           "Dribbling alone ignores two teammates who are ready.",
           "A first-time lay-off is a one-touch pass back to a friend.",
           difficulty="medium", attack={"st": (42, 70), "cdm": (48, 58)})
    decide("Overlap and cross", "rw", (80, 68), ("pass", "rb"),
           [("dribble", None, 50), ("pass", "st", 75)],
           "Your right back has run past you on the outside. There is space for a cross.",
           "Pass to the overlapping right back so they can cross.",
           "Holding the ball lets the other team get across and block the overlap.",
           "If a teammate overlaps, give them the ball in space.",
           difficulty="medium", attack={"rb": (90, 74), "st": (52, 80)}, defend={"dlw": (70, 66)})
    decide("Inside combination", "rw", (76, 66), ("pass", "st"),
           [("dribble", None, 75), ("pass", "cdm", 50)],
           "You have cut inside with the ball. Your striker is free for a quick pass in the box.",
           "Combine with the striker. A short pass can open a shot.",
           "Taking an extra dribble in a crowded box can waste the striker's run.",
           "After you cut inside, look for the striker.",
           difficulty="hard", attack={"st": (60, 76)}, defend={"dl": (68, 74), "dcm": (58, 68)})
    decide("Switch through striker", "lw", (20, 64), ("pass", "st"),
           [("pass", "rw", 50), ("dribble", None, 25)],
           "The left side is crowded. Your striker can see the free right winger.",
           "Pass to the striker and let them redirect the ball to the far winger.",
           "A long pass from the crowded side is easy to intercept.",
           "Use the striker as a stepping stone to the other side.",
           difficulty="hard", attack={"st": (52, 70), "rw": (88, 66)}, defend={"drw": (28, 58)})

    _use("attack-move")
    move("Near-post run", "st", (46, 64), (62, 88), "rw",
         "A cross is coming from the right. The near post is empty.",
         "Attack the near post. Getting there early lets you meet the cross first.",
         "Waiting in the middle lets the keeper take the ball.",
         "The near post is the post closest to the ball.",
         difficulty="easy", attack={"rw": (88, 76)}, defend={"dgk": (48, 92)})
    move("Far-post run", "lw", (16, 62), (36, 88), "rw",
         "The cross from the right is going over the near post. Your far winger has not moved.",
         "Run to the far post so you can score if the ball goes across the goal.",
         "Staying wide leaves the far post empty.",
         "One player attacks the near post. Another attacks the far post.",
         difficulty="medium", attack={"rw": (86, 74), "st": (64, 84)}, defend={"dgk": (56, 92)})
    move("Striker pulls wide", "st", (50, 80), (76, 74), "cdm",
         "Your midfielder is arriving in the middle for a shot. The centre is blocked by your striker.",
         "The striker pulls wide into the channel. The midfielder can now shoot through the gap.",
         "Standing in front of the shooter blocks your own team.",
         "Leave the shooting space free for the player who is arriving.",
         difficulty="medium", attack={"cdm": (46, 66)}, defend={"dst": (48, 86)})

    _use("final-third")
    decide("Cutback", "rw", (86, 80), ("pass", "cdm"),
           [("pass", "st", 75), ("shoot", None, 25)],
           "You have reached the goal line. Defenders are on the goal. Your midfielder is waiting just outside the box.",
           "Pass the ball back to the midfielder. A cutback can give them an open shot.",
           "Shooting from a tight angle on the goal line is harder than the cutback.",
           "A cutback is a pass backwards from the goal line to a teammate.",
           difficulty="medium", shoot=True, attack={"cdm": (58, 68), "st": (48, 84)}, defend={"dl": (60, 86), "dgk": (46, 92)})
    decide("Cross and rebound", "rw", (84, 74), ("pass", "st"),
           [("pass", "cdm", 75), ("dribble", None, 25)],
           "You can cross to the striker, or cut the ball back to the midfielder. The striker is free at the near post.",
           "Cross to the striker. They are the free player at the near post.",
           "Dribbling along the line lets the defender get back.",
           "Pick the teammate who is free, then pass.",
           difficulty="medium", attack={"st": (60, 86), "cdm": (52, 66)}, defend={"dl": (40, 82)})
    decide("Winger shoots across goal", "rw", (72, 82), ("shoot", None),
           [("pass", "st", 75), ("dribble", None, 25)],
           "You have cut inside onto your stronger foot. The keeper is off the near post and the goal is open.",
           "Shoot across the goal. This is a chance to score.",
           "Taking an extra touch lets the keeper get set.",
           "If the goal is open and you are close, shoot.",
           difficulty="easy", shoot=True, attack={"st": (40, 84)}, defend={"dgk": (42, 92), "dl": (58, 70)})
    decide("CM shoots from distance", "cdm", (54, 68), ("shoot", None),
           [("pass", "st", 75), ("dribble", None, 25)],
           "Your midfielder has the ball outside the box. Defenders have backed off and the path to goal is open.",
           "Shoot. Space in front of goal is a chance to strike.",
           "Dribbling closer lets the defenders step out and block.",
           "If nobody closes you down outside the box, you can shoot.",
           difficulty="medium", shoot=True, attack={"st": (48, 84)}, defend={"dr": (30, 78), "dl": (74, 78), "dcm": (40, 80)})
    decide("Overload one side", "rw", (82, 66), ("pass", "st"),
           [("pass", "rb", 75), ("dribble", None, 25)],
           "You have more attackers than defenders on the right. Your striker is free beside you.",
           "Pass to the striker and keep the overload working. Do not try to beat everyone alone.",
           "Dribbling into two defenders wastes the extra player.",
           "When your team has more players on one side, use them.",
           difficulty="medium", attack={"st": (68, 72), "rb": (88, 58)}, defend={"dlw": (76, 74)})
    decide("Switch to isolated winger", "cdm", (48, 50), ("pass", "lw"),
           [("pass", "rw", 25), ("dribble", None, 25)],
           "The right side has three defenders. Your left winger is alone, with space.",
           "Switch the ball to the left winger. One against one is a good attack.",
           "Playing into the crowded side helps the other team.",
           "Find the teammate who is one against one, not the one who is surrounded.",
           difficulty="hard", attack={"lw": (14, 66), "rw": (84, 62)}, defend={"dl": (78, 68), "dlw": (92, 46), "dcm": (70, 64)})
    decide("Pass rather than dribble", "st", (58, 72), ("pass", "lw"),
           [("dribble", None, 25), ("pass", "cdm", 75)],
           "A defender has stepped toward you. Your left winger is now free behind that defender.",
           "Pass to the winger. The defender's step has left them free.",
           "Dribbling at a defender who has already committed is how balls are lost.",
           "When a defender comes to you, look for the friend they left.",
           difficulty="hard", attack={"lw": (24, 74)}, defend={"dr": (64, 70)})

    _use("defend")
    move("Defender steps out", "rb", (76, 36), (80, 58), "rw",
         "An opponent has the ball wide and is running at your defence. Your right back is too deep.",
         "Step toward the ball carrier so they cannot walk forward for free.",
         "Dropping deeper gives the opponent time and space to pick a pass.",
         "The closest defender should meet the player with the ball.",
         difficulty="easy", attack={"rw": (86, 48)}, defend={"dlw": (82, 66), "dl": (74, 74)})
    move("Second defender covers", "lb", (20, 40), (48, 32), "rw",
         "Your right back is stepping out to the ball. The middle in front of goal is open.",
         "The other defender drops into the middle to cover. If the first defender is beaten, you are still safe.",
         "Both defenders going to the ball leaves the goal empty.",
         "One defender presses. The other covers behind them.",
         difficulty="easy", attack={"rb": (78, 56)}, defend={"dlw": (84, 62)})
    move("CDM protects the middle", "cdm", (24, 58), (50, 40), "lw",
         "The ball is wide. Your midfielder has wandered to the side, and the middle is open.",
         "Get the midfielder between the ball and your goal. The middle is the danger.",
         "Chasing the ball out wide leaves a pass into the centre.",
         "Midfielders protect the centre first.",
         difficulty="easy", attack={"lw": (16, 62)}, defend={"drw": (20, 68)})
    move("Winger tracks back", "rw", (86, 74), (78, 40), "lb",
         "The other team has the ball on your right and is attacking. Your winger is still up the pitch.",
         "Run back and help your defender. A winger's job includes defending.",
         "Staying high leaves your defender one against two.",
         "When you lose the ball, the nearest attackers must run back.",
         difficulty="medium", attack={"rb": (74, 28)}, defend={"dlw": (84, 50), "dst": (60, 46)})
    move("Striker screens the pivot", "st", (70, 80), (52, 62), "gk",
         "The other team's keeper has the ball and wants to pass to their midfielder.",
         "Stand in the passing lane between the keeper and the midfielder so the easy pass is blocked.",
         "Chasing the keeper lets the midfielder receive and turn.",
         "Screening means standing in a passing lane so the ball cannot go through.",
         difficulty="medium", defend={"dgk": (50, 92), "dcm": (50, 74)})
    move("Shift across together", "lb", (16, 34), (40, 36), "rw",
         "The ball has moved to the right, but your left back is still on the far touchline.",
         "Slide across with the ball. The whole team should shift, and this player starts the slide.",
         "Staying on the far side opens a huge gap through the middle.",
         "When the ball goes to one side, the team slides that way together.",
         difficulty="medium", attack={"rb": (72, 40), "cdm": (48, 48), "rw": (84, 62)}, defend={"dlw": (92, 80)})
    move("Protect the centre", "rb", (90, 68), (64, 36), "lw",
         "An opponent on the left wants to come inside. Your right back is too wide.",
         "Move inside and show them the touchline. Make them play away from the goal.",
         "Leaving the centre open invites a shot or a through pass.",
         "Force attackers toward the side, not toward your goal.",
         difficulty="hard", defend={"drw": (18, 58)})
    move("CDM covers advancing defender", "cdm", (62, 58), (74, 32), "lb",
         "Your left back has gone forward and left a space behind them.",
         "Drop the midfielder into that empty space so a counterattack has nobody to run at.",
         "Staying high leaves a hole where the defender used to be.",
         "If a defender attacks, a midfielder should cover the space they left.",
         difficulty="hard", attack={"lb": (30, 62)})
    move("Far-side winger tucks in", "lw", (12, 66), (40, 58), "rw",
         "The ball is on the right and you are defending. Your left winger is still on the far touchline.",
         "Tuck the far winger into the middle so a switch of play does not find an empty centre.",
         "Staying wide leaves the middle short of players.",
         "The winger farthest from the ball should come inside and protect the middle.",
         difficulty="medium", defend={"dlw": (82, 62)})
    move("Defensive line drops", "rb", (76, 52), (74, 20), "cdm",
         "An opponent is ready to play a through ball behind your defenders.",
         "This defender drops toward goal so they stay between the runner and the goal.",
         "Stepping up lets the pass go behind you.",
         "If a through ball is coming, the defensive line drops together.",
         difficulty="hard", attack={"lb": (28, 24)}, defend={"dst": (60, 46)})

    _use("press")
    move("Striker initiates the press", "st", (22, 52), (54, 84), "gk",
         "The other keeper has the ball and a defender is close. Your striker is too far away to matter.",
         "Start the press by moving toward the ball at an angle that also blocks the middle pass.",
         "Jogging straight at the keeper lets them pass around you.",
         "The striker starts the press. Everyone else follows.",
         difficulty="easy", defend={"dgk": (50, 92), "dl": (68, 80)},
         zones=((64, 80, 7, 75),))
    move("Curved pressing run", "st", (40, 70), (66, 82), "gk",
         "The keeper wants to pass into the middle. A straight run leaves that pass open.",
         "Curve your run so your body blocks the pass into the middle and the keeper has to go wide.",
         "Running straight makes it easy to pass around you.",
         "A curved press takes away the middle and sends the ball to the side.",
         difficulty="medium", defend={"dgk": (50, 92), "dcm": (52, 76)})
    move("Winger traps defender", "rw", (46, 48), (78, 78), "gk",
         "A defender on the right has the ball near the touchline. There is no space behind them.",
         "Approach from the inside so the defender is trapped by the touchline.",
         "Pressing from the outside lets them pass or dribble into the middle.",
         "Use the touchline as an extra defender.",
         difficulty="medium", defend={"dl": (92, 88)})
    move("CM jumps forward", "cdm", (48, 40), (56, 66), "gk",
         "The other team is about to pass to their midfielder. Your midfielder is too deep to arrive in time.",
         "Jump forward so you reach their midfielder as the ball does.",
         "Waiting deep lets them turn and face your goal.",
         "Press the player who is about to receive, not only the player who has the ball.",
         difficulty="medium", defend={"dcm": (72, 80), "dgk": (50, 92)})
    move("Double-team", "lw", (12, 36), (30, 74), "gk",
         "Your striker is already pressing the ball. A defender nearby is the easy pass.",
         "The second player closes that nearest passing option so the ball carrier has nowhere to go.",
         "Watching the pass instead of closing it makes the press easy to escape.",
         "A double team means two players working on the ball and the next pass.",
         difficulty="hard", attack={"st": (48, 84)}, defend={"dgk": (50, 92), "dr": (16, 88)})
    move("Press on a poor touch", "cdm", (40, 48), (58, 64), "gk",
         "An opponent has taken a heavy touch and the ball is loose in front of them.",
         "Attack the loose ball. A bad touch is the moment to win it.",
         "Standing off lets them recover the ball and look up.",
         "If the ball is loose, the closest player goes.",
         difficulty="easy", defend={"dcm": (76, 76)})
    move("Press on a backwards pass", "st", (24, 48), (50, 82), "gk",
         "The other team has passed backwards. Their players are facing their own goal.",
         "Move up with the ball. A backward pass is a signal for the whole team to step forward.",
         "Staying deep gives them time to turn and play forward again.",
         "When the ball goes backwards, your team steps up.",
         difficulty="medium", defend={"dgk": (50, 92), "dcm": (48, 74)})
    move("Force goalkeeper long", "rw", (92, 40), (74, 80), "gk",
         "The keeper wants a short pass to a defender. Your winger is too far away to stop it.",
         "Move to block the short pass. If both short options are covered, the keeper has to kick long.",
         "Leaving the short pass open lets them play out easily.",
         "Take away the short pass and the keeper must kick it long.",
         difficulty="hard", attack={"st": (50, 84), "lw": (28, 78)}, defend={"dgk": (50, 92), "dl": (90, 88)})
    move("Intercept rather than chase", "cdm", (36, 40), (58, 62), "gk",
         "You can see the pass they want to play. Chasing the ball carrier will be too late.",
         "Move into the passing lane and intercept the ball.",
         "Chasing the player leaves the pass free.",
         "Sometimes the smart press is to wait in the passing lane.",
         difficulty="hard", defend={"dgk": (48, 90), "dcm": (64, 70)})

    _use("gk-pos")
    move("Keeper rolls to winger", "rw", (60, 40), (90, 28), "gk",
         "Your keeper wants to roll the ball out. Your winger is too narrow to receive it safely.",
         "Move wide, toward the touchline, so the keeper can roll the ball into space.",
         "Standing in the middle makes the short roll easy to intercept.",
         "Show wide for a keeper who wants to roll the ball.",
         difficulty="easy", attack={"gk": (50, 8)}, defend={"dlw": (70, 50)})
    move("Defender splits wide", "lb", (40, 24), (16, 26), "gk",
         "Both defenders are close together, so the keeper has no wide pass.",
         "Split wide. A big gap between the defenders gives the keeper two clear passes.",
         "Standing next to the other defender blocks the keeper's angles.",
         "Defenders should spread when the keeper has the ball.",
         difficulty="easy", attack={"rb": (60, 24), "gk": (50, 8)})
    move("CDM creates an angle", "cdm", (50, 48), (36, 30), "gk",
         "Your keeper's pass to the defenders is blocked. Your midfielder is hiding behind a defender.",
         "Move diagonally into an open passing lane so the keeper can see you.",
         "Standing directly behind an opponent means the pass cannot reach you.",
         "If the keeper cannot see you, move until they can.",
         difficulty="medium", attack={"gk": (50, 10)}, defend={"dst": (50, 28)})
    move("Striker offers a long option", "st", (50, 60), (62, 82), "gk",
         "The short passes are marked. Your keeper may need to kick longer.",
         "The striker moves into a spot where they can receive a longer pass and hold it up.",
         "Dropping next to marked defenders gives the keeper nothing new.",
         "Always give the keeper a long option as well as a short one.",
         difficulty="medium", attack={"gk": (50, 8)}, defend={"dr": (30, 40), "dl": (70, 40)})
    move("Keeper communicates", "rb", (62, 36), (82, 24), "gk",
         "The keeper is asking the defenders to spread. Your right back is still narrow.",
         "Follow the keeper and move wide so the build-up has a shape.",
         "Ignoring the keeper leaves the team bunched.",
         "Listen to the keeper. They can see the whole pitch.",
         difficulty="easy", attack={"lb": (22, 24), "gk": (50, 8)})

    _use("gk-decide")
    decide("Keeper finds wide defender", "gk", (50, 10), ("pass", "lb"),
           [("pass", "cdm", 75), ("dribble", None, 0)],
           "Your keeper has the ball. The left back is free and wide. The right side is marked.",
           "Roll or pass to the free left back.",
           "Dribbling out of goal, or passing into a marked side, gives the other team a chance.",
           "The first job for a keeper is to find the free defender.",
           difficulty="easy", attack={"lb": (18, 26), "rb": (78, 28)}, defend={"dlw": (74, 40), "dst": (52, 24)})
    decide("Keeper finds CDM", "gk", (50, 10), ("pass", "cdm"),
           [("pass", "lb", 75), ("dribble", None, 0)],
           "Both defenders are marked. Your midfielder has dropped into an open pocket.",
           "Pass to the midfielder. They are the free player.",
           "Forcing the ball to a marked defender is how presses win the ball.",
           "If the defenders are marked, use the midfielder.",
           difficulty="easy", attack={"cdm": (46, 28), "lb": (22, 30), "rb": (78, 30)}, defend={"drw": (28, 40), "dlw": (74, 40)})
    decide("Keeper switches play", "gk", (50, 12), ("pass", "rw"),
           [("pass", "lb", 50), ("dribble", None, 0)],
           "The left side is crowded. Your right winger is free and wide.",
           "Switch the ball to the right winger.",
           "Playing back into the crowded side keeps you under pressure.",
           "A keeper can change the side of the attack with one pass.",
           difficulty="medium", attack={"rw": (88, 36), "lb": (20, 28)}, defend={"drw": (24, 36), "dr": (30, 30)})
    decide("Defender plays around pressure", "rb", (74, 28), ("pass", "gk"),
           [("dribble", None, 25), ("pass", "rw", 50)],
           "An opponent is pressing your right back. Your keeper is free behind you.",
           "Pass back to the keeper and go around the press.",
           "Dribbling into the press is how the other team wins the ball high up.",
           "Use the keeper to escape a press.",
           difficulty="medium", attack={"gk": (50, 10)}, defend={"dlw": (78, 40)})
    decide("Defender and keeper combination", "lb", (24, 30), ("pass", "gk"),
           [("pass", "cdm", 75), ("dribble", None, 25)],
           "You are closed down near the corner. The keeper is open and can restart the attack.",
           "Pass to the keeper. Together you can escape the corner.",
           "Shielding the ball in the corner until you lose it is not a plan.",
           "The keeper is a teammate. Use them when you are stuck.",
           difficulty="hard", attack={"gk": (48, 12)}, defend={"drw": (28, 42), "dr": (32, 36)})

    _use("trans-pos")
    move("Winger runs beyond", "rw", (70, 48), (88, 76), "cdm",
         "You have just won the ball in the middle. Your winger is level with the ball, and there is space in front.",
         "Sprint beyond the ball straight away. A fast run gives the passer a target.",
         "Jogging, or coming back toward the ball, wastes the open space.",
         "The first second after you win the ball is the best time to run forward.",
         difficulty="easy", attack={"cdm": (50, 50)}, defend={"dl": (64, 78), "dcm": (40, 70)})
    move("Counterpress", "cdm", (40, 40), (58, 56), "lw",
         "You just lost the ball. The opponent who won it is still close.",
         "Go straight at them. The counterpress tries to win the ball back before they can pass.",
         "Dropping off lets them turn and start an attack.",
         "Lose it, and the nearest player tries to win it back at once.",
         difficulty="easy", defend={"drw": (76, 66)})
    move("Nearest player delays", "rb", (90, 72), (70, 40), "lw",
         "The other team has won the ball and is running at you. Help is on the way, but not here yet.",
         "Get in their path and slow them down. Do not dive in.",
         "Diving in lets them go past you and leaves the goal open.",
         "Delay means slowing the attack until your teammates get back.",
         difficulty="medium", attack={"lb": (30, 20), "cdm": (40, 24)}, defend={"drw": (72, 56)})
    move("Recover centrally", "cdm", (78, 62), (50, 36), "rw",
         "The ball has been lost and the other team is breaking through the middle. You are stuck out wide.",
         "Sprint back into the centre. That is the space in front of your goal.",
         "Chasing the wide player leaves the middle empty.",
         "Recover to the middle first.",
         difficulty="medium", defend={"dst": (52, 58), "dcm": (48, 66)})
    move("Defenders recover goal-side", "lb", (30, 62), (32, 24), "cdm",
         "A counterattack is running at your goal. Your left back is still up the pitch.",
         "Sprint back toward your own goal until you are closer to the goal than the ball is.",
         "Staying high means the counter has a free run.",
         "Goal-side means you are between the ball and your goal.",
         difficulty="hard", attack={"rb": (74, 26)}, defend={"dst": (50, 50)})
    move("Keeper sweeps", "gk", (50, 8), (50, 38), "cdm",
         "A through ball is coming and your defenders cannot reach it. There is space behind them.",
         "The keeper comes off the line and collects the ball, or forces the attacker wide.",
         "Staying on the line lets the attacker run through and shoot.",
         "A sweeper keeper protects the space behind the defenders.",
         difficulty="hard", attack={"lb": (28, 40), "rb": (72, 40)}, defend={"dst": (50, 48)})

    _use("trans-decide")
    decide("Win it and attack", "cdm", (50, 52), ("pass", "st"),
           [("dribble", None, 75), ("pass", "lb", 25)],
           "You have just won the ball. Your striker is free and facing the goal. The other team is out of shape.",
           "Play forward to the striker straight away.",
           "Passing backwards gives the other team time to get back.",
           "Win the ball and look forward first.",
           difficulty="easy", attack={"st": (56, 74)}, defend={"dr": (30, 80), "dl": (72, 78), "dcm": (40, 70)})
    decide("Immediate counterattack", "lb", (28, 40), ("pass", "st"),
           [("pass", "cdm", 75), ("dribble", None, 50)],
           "You have intercepted a pass. Your striker is already running in behind.",
           "Pass forward into the striker. This is a counterattack.",
           "Slowing down to dribble lets defenders recover.",
           "A counterattack should be played forward quickly.",
           difficulty="easy", attack={"st": (60, 76)}, defend={"dl": (48, 84)})
    decide("Striker holds up counterattack", "cdm", (48, 50), ("pass", "st"),
           [("dribble", None, 50), ("pass", "rw", 75)],
           "You are on the break, but your wingers are still catching up. The striker can hold the ball.",
           "Pass to the striker so they can protect it until help arrives.",
           "Forcing a shot or a rushed dribble wastes the break.",
           "If help is coming, the striker can hold the ball up.",
           difficulty="medium", attack={"st": (58, 68), "rw": (70, 48)}, defend={"dl": (64, 78)})
    decide("Counter through the middle", "cdm", (50, 48), ("dribble", None),
           [("pass", "rw", 75), ("pass", "lb", 25)],
           "The middle of the pitch is empty in front of you. Wide players are marked.",
           "Carry the ball through the middle.",
           "Passing wide into a marked player slows the counter.",
           "If the centre is open, drive into it.",
           difficulty="medium", attack={"rw": (86, 58), "lw": (16, 58)}, defend={"drw": (78, 62), "dlw": (24, 62), "dcm": (70, 70)})
    decide("Quick switch after winning possession", "rb", (74, 36), ("pass", "lw"),
           [("pass", "rw", 25), ("dribble", None, 50)],
           "You won the ball on the right, and that side is crowded. Your left winger is completely free.",
           "Switch the ball quickly to the left winger.",
           "Staying on the side where you won it runs into the players who just lost it.",
           "After you win the ball, look for the open side.",
           difficulty="hard", attack={"lw": (14, 64), "rw": (84, 40)}, defend={"dlw": (78, 48), "dl": (70, 44)})

    _use("adv-move")
    move("Rotate positions", "cdm", (48, 46), (82, 64), "lb",
         "Your winger is coming inside. Someone needs to fill the wide space they left.",
         "The midfielder rotates out wide. The team keeps its shape even though two players swapped jobs.",
         "Everyone following the ball leaves the wide space empty.",
         "When one player leaves a position, another player fills it.",
         difficulty="hard", attack={"rw": (64, 70), "lb": (28, 36)})
    move("Create a passing triangle", "lw", (10, 84), (34, 56), "lb",
         "Your left back has the ball. The striker and midfielder are almost in a line, so the pass is easy to block.",
         "The winger drops to a new angle. Three players at different angles make a triangle.",
         "Standing in a straight line with the ball makes every pass simple to intercept.",
         "Triangles give the player on the ball two safe passes.",
         difficulty="medium", attack={"lb": (22, 36), "cdm": (42, 48)},
         zones=((28, 64, 7, 75),))
    move("Move after passing", "cdm", (40, 44), (58, 64), "lb",
         "You pictured the pass already going to the left back. The midfielder has stopped and is no longer useful.",
         "Move straight after the pass so you can receive it again in a better spot.",
         "Watching your own pass standing still helps the other team.",
         "The pass is only the first part. The next move matters too.",
         difficulty="medium", attack={"lb": (24, 34), "cdm": (40, 44)})
    move("Attack the space, not the ball", "st", (54, 66), (72, 84), "rw",
         "Three teammates are already near the ball. The space near the goal is empty.",
         "Run into the empty space. Do not join the crowd around the ball.",
         "Running toward the ball puts too many players in one place.",
         "Go where the defenders are not.",
         difficulty="hard", attack={"rw": (84, 62), "cdm": (70, 58), "lw": (60, 60)})

    _use("adv-decide")
    decide("Recognise the overload", "rw", (80, 66), ("pass", "st"),
           [("pass", "rb", 75), ("dribble", None, 25)],
           "There are three of you against one defender on this side. Your striker is free next to you.",
           "Pass and combine. An overload works when you use the extra player.",
           "Trying to dribble the last defender alone ignores the extra attacker.",
           "Count the players. If you have more, pass.",
           difficulty="medium", attack={"st": (66, 72), "rb": (88, 56)}, defend={"dlw": (78, 74)})
    decide("Recognise the 1v1", "rw", (82, 68), ("dribble", None),
           [("pass", "st", 50), ("pass", "cdm", 25)],
           "You are isolated against one defender, with space to attack them.",
           "Take them on. A one against one in space is a chance to dribble.",
           "Passing away from a good one-against-one gives the ball back to a crowded area.",
           "If you are one against one and you have space, dribble.",
           difficulty="easy", attack={"st": (40, 78)}, defend={"dlw": (70, 58), "dl": (24, 88)})
    decide("Recognise the 2v1", "cdm", (48, 58), ("pass", "st"),
           [("dribble", None, 75), ("pass", "lb", 25)],
           "You and the striker are against one defender. The striker is free to the side.",
           "Pass to the striker. Two against one should end with the free player on the ball.",
           "Ignoring the striker makes it one against one again.",
           "In a two against one, pass to the free teammate.",
           difficulty="medium", attack={"st": (64, 68)}, defend={"dst": (56, 74)})
    decide("Recognise when to switch", "lb", (22, 40), ("pass", "cdm"),
           [("pass", "lw", 25), ("dribble", None, 25)],
           "Your left side is full of opponents. The right winger is free.",
           "Play to the midfielder so the ball can go to the open side.",
           "Keeping the ball in the crowd makes you lose it.",
           "Leave the crowded side. Switch.",
           difficulty="medium", attack={"cdm": (50, 46), "rw": (88, 62), "lw": (14, 48)}, defend={"dr": (26, 48), "drw": (18, 56), "dcm": (34, 52)})
    decide("Recognise when to recycle", "st", (58, 74), ("pass", "cdm"),
           [("pass", "rw", 50), ("shoot", None, 25)],
           "The forward pass is blocked and the shot is covered. Your midfielder is free behind you.",
           "Pass backwards and keep the ball. You can attack again in a better moment.",
           "Forcing a shot or a blocked pass gives the other team the ball.",
           "Keeping the ball is better than a hopeful kick.",
           difficulty="hard", shoot=True, attack={"cdm": (46, 56)}, defend={"dst": (78, 88), "dl": (70, 76)})
    decide("Recognise when to slow down", "cdm", (52, 50), ("pass", "lb"),
           [("dribble", None, 25), ("pass", "st", 50)],
           "You have the ball, but your striker and wingers are still running back into the attack.",
           "Play a safe pass and wait. Rushing forward alone makes the attack one against many.",
           "Dribbling at a set defence before your teammates arrive usually loses the ball.",
           "If your team is not ready, slow the game down.",
           difficulty="hard", attack={"lb": (24, 36), "st": (60, 64)}, defend={"dr": (34, 70), "dl": (66, 70), "dcm": (50, 66)})
    return _ROWS


def load_scenarios() -> list[dict]:
    return _build()
