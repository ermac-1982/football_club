"""Scoring and path rules for Situational Coach. Scenario text lives in coach_scenarios."""

from __future__ import annotations

import math
from typing import Optional

from coach_scenarios import SECTIONS, load_scenarios

BANDS = ((7, 100), (12, 75), (17, 50), (22, 25))
SECTION_BONUS = 500
SCORE_LABELS = {100: "Excellent", 75: "Good", 50: "Almost", 25: "Poor", 0: "Try again"}
PRIVATE_FIELDS = {
    "correctPosition",
    "acceptablePositionZones",
    "correctAction",
    "targetPlayerId",
    "alternativeActions",
    "explanation",
    "incorrectExplanation",
    "coachingTip",
}


def scenarios() -> list[dict]:
    return load_scenarios()


def scenario_map() -> dict[int, dict]:
    return {item["id"]: item for item in scenarios()}


def get_scenario(scenario_id: int) -> dict:
    found = scenario_map().get(scenario_id)
    if found is None:
        raise KeyError(scenario_id)
    return found


def public_scenario(scenario: dict) -> dict:
    return {key: value for key, value in scenario.items() if key not in PRIVATE_FIELDS}


def result_for(score: int) -> str:
    if score >= 100:
        return "correct"
    if score >= 50:
        return "partial"
    return "incorrect"


def label_for(score: int) -> str:
    return SCORE_LABELS.get(score, "Score")


def _distance(a: dict, b: dict) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def _band_score(distance: float) -> int:
    for limit, score in BANDS:
        if distance <= limit:
            return score
    return 0


def position_score(chosen: dict, scenario: dict) -> int:
    correct = scenario["correctPosition"]
    best = _band_score(_distance(chosen, correct))
    for zone in scenario.get("acceptablePositionZones") or []:
        if _distance(chosen, zone) <= float(zone["radius"]):
            best = max(best, int(zone["score"]))
    return best


def _action_matches(answer: dict, action: dict) -> bool:
    if answer.get("action") != action.get("action"):
        return False
    if action.get("action") == "pass":
        return answer.get("targetPlayerId") == action.get("targetPlayerId")
    return True


def decision_score(answer: dict, scenario: dict) -> int:
    if _action_matches(answer, scenario["correctAction"]):
        return 100
    for alternative in scenario.get("alternativeActions") or []:
        if _action_matches(answer, alternative):
            return int(alternative["score"])
    return 0


def _players(scenario: dict, team: str) -> list[dict]:
    key = "attackingPlayers" if team == "attack" else "defendingPlayers"
    return list(scenario[key])


def _player(scenario: dict, player_id: str) -> Optional[dict]:
    for player in _players(scenario, "attack") + _players(scenario, "defend"):
        if player["id"] == player_id:
            return player
    return None


def normalise_answer(scenario: dict, answer: dict) -> dict:
    if scenario["mode"] == "positioning":
        try:
            x = float(answer["x"])
            y = float(answer["y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Drag the player, then submit.") from exc
        if not (0 <= x <= 100 and 0 <= y <= 100):
            raise ValueError("Keep the player on the pitch.")
        return {"x": round(x, 1), "y": round(y, 1)}

    action = answer.get("action")
    allowed = set(scenario.get("availableActions") or [])
    if action not in allowed:
        raise ValueError("Pick a pass, a dribble, or a shot.")
    if action == "pass":
        target = answer.get("targetPlayerId")
        carrier = scenario["highlightedPlayerId"]
        player = _player(scenario, str(target)) if target else None
        if player is None or player["team"] != "attack" or player["id"] == carrier:
            raise ValueError("Pass to a teammate.")
        return {"action": "pass", "targetPlayerId": player["id"]}
    return {"action": action}


def score_answer(scenario: dict, answer: dict) -> dict:
    submitted = normalise_answer(scenario, answer)
    if scenario["mode"] == "positioning":
        score = position_score(submitted, scenario)
    else:
        score = decision_score(submitted, scenario)
    if score >= 50:
        explanation = scenario["explanation"]
    else:
        explanation = f"{scenario['incorrectExplanation']} {scenario['explanation']}"
    return {
        "scenarioId": scenario["id"],
        "mode": scenario["mode"],
        "score": score,
        "points": score,
        "result": result_for(score),
        "label": label_for(score),
        "explanation": explanation,
        "coachingTip": scenario["coachingTip"],
        "correctPosition": scenario.get("correctPosition"),
        "correctAction": scenario.get("correctAction"),
        "submitted": submitted,
    }


def _best_scores(attempts: dict[int, list[int]]) -> dict[int, int]:
    return {scenario_id: max(scores) for scenario_id, scores in attempts.items() if scores}


def completed_sections(attempts: dict[int, list[int]]) -> list[str]:
    by_section: dict[str, list[int]] = {section["id"]: [] for section in SECTIONS}
    for scenario in scenarios():
        by_section.setdefault(scenario["section"], []).append(scenario["id"])
    done = []
    for section in SECTIONS:
        ids = by_section.get(section["id"]) or []
        if ids and all(attempts.get(scenario_id) for scenario_id in ids):
            done.append(section["id"])
    return done


def total_score(attempts: dict[int, list[int]]) -> int:
    """Best drill scores, plus 500 for each finished section. Replays raise it only when a best score goes up."""
    library_ids = {scenario["id"] for scenario in scenarios()}
    drill_score = sum(score for scenario_id, score in _best_scores(attempts).items() if scenario_id in library_ids)
    return drill_score + SECTION_BONUS * len(completed_sections(attempts))


def build_path(attempts: dict[int, list[int]]) -> dict:
    library = scenarios()
    by_section: dict[str, list[dict]] = {section["id"]: [] for section in SECTIONS}
    for scenario in library:
        by_section[scenario["section"]].append(scenario)
    best = _best_scores(attempts)
    sections = []
    open_found = False
    for section in SECTIONS:
        rows = by_section[section["id"]]
        done = 0
        scenario_rows = []
        for scenario in rows:
            scores = attempts.get(scenario["id"]) or []
            finished = bool(scores)
            done += int(finished)
            scenario_rows.append(
                {
                    "id": scenario["id"],
                    "title": scenario["title"],
                    "difficulty": scenario["difficulty"],
                    "category": scenario["category"],
                    "bestScore": best.get(scenario["id"]),
                    "attempts": len(scores),
                    "done": finished,
                }
            )
        complete = done == len(rows) and bool(rows)
        if complete:
            status = "complete"
        elif not open_found:
            status = "current"
            open_found = True
        else:
            status = "locked"
        sections.append(
            {
                "id": section["id"],
                "title": section["title"],
                "kicker": section["kicker"],
                "blurb": section["blurb"],
                "mode": section["mode"],
                "modeLabel": "Positioning" if section["mode"] == "positioning" else "Decision",
                "status": status,
                "completed": done,
                "total": len(rows),
                "scenarios": scenario_rows,
            }
        )

    attempted_ids = [scenario["id"] for scenario in library if attempts.get(scenario["id"])]
    correct = sum(1 for scenario_id in attempted_ids if best.get(scenario_id, 0) >= 75)
    average = round(sum(best[scenario_id] for scenario_id in attempted_ids) / len(attempted_ids)) if attempted_ids else 0
    progress = {
        "attempted": len(attempted_ids),
        "total": len(library),
        "totalAttempts": sum(len(scores) for scores in attempts.values()),
        "correct": correct,
        "accuracy": round(100 * correct / len(attempted_ids)) if attempted_ids else 0,
        "averageScore": average,
        "bestScore": max(best.values()) if best else 0,
        "totalScore": total_score(attempts),
        "maxScore": 100 * len(library) + SECTION_BONUS * len(SECTIONS),
        "byCategory": _grouped(library, attempts, best, "category"),
        "byDifficulty": _grouped(library, attempts, best, "difficulty"),
    }
    nxt = next_incomplete(attempts)
    return {
        "sections": sections,
        "progress": progress,
        "nextScenarioId": nxt,
        "nextSectionId": get_scenario(nxt)["section"] if nxt else None,
        "allComplete": nxt is None,
    }


def _grouped(library: list[dict], attempts: dict[int, list[int]], best: dict[int, int], field: str) -> list[dict]:
    order = []
    buckets: dict[str, list[int]] = {}
    for scenario in library:
        key = scenario[field]
        if key not in buckets:
            order.append(key)
            buckets[key] = []
        if attempts.get(scenario["id"]):
            buckets[key].append(best[scenario["id"]])
    rows = []
    for key in order:
        scores = buckets[key]
        average = round(sum(scores) / len(scores)) if scores else None
        if not scores:
            note = "Not tried yet"
        elif average < 50:
            note = "Needs practice"
        elif average >= 75:
            note = "Coming on"
        else:
            note = "Keep going"
        rows.append(
            {
                "id": key,
                "label": key[:1].upper() + key[1:],
                "attempted": len(scores),
                "average": average,
                "note": note,
            }
        )
    return rows


def section_status(attempts: dict[int, list[int]], section_id: str) -> str:
    for section in build_path(attempts)["sections"]:
        if section["id"] == section_id:
            return section["status"]
    raise KeyError(section_id)


def next_incomplete(attempts: dict[int, list[int]]) -> Optional[int]:
    for scenario in scenarios():
        if not attempts.get(scenario["id"]):
            return scenario["id"]
    return None


def validate_library() -> list[str]:
    problems = []
    library = scenarios()
    ids = [item["id"] for item in library]
    if ids != list(range(1, 101)):
        problems.append(f"ids are {ids[:5]}... count {len(ids)}")
    modes = {"positioning": 0, "decision": 0}
    section_ids = [section["id"] for section in SECTIONS]
    if len(section_ids) != len(set(section_ids)):
        problems.append("duplicate section id")
    by_section = {section["id"]: [] for section in SECTIONS}
    for scenario in library:
        modes[scenario["mode"]] = modes.get(scenario["mode"], 0) + 1
        if scenario["section"] not in by_section:
            problems.append(f"{scenario['id']} unknown section")
            continue
        by_section[scenario["section"]].append(scenario["id"])
        section = next(item for item in SECTIONS if item["id"] == scenario["section"])
        if scenario["mode"] != section["mode"]:
            problems.append(f"{scenario['id']} mode does not match its section")
        if len(scenario["attackingPlayers"]) != 7 or len(scenario["defendingPlayers"]) != 7:
            problems.append(f"{scenario['id']} needs 7v7")
        attack_ids = [player["id"] for player in scenario["attackingPlayers"]]
        if len(set(attack_ids)) != 7 or scenario["highlightedPlayerId"] not in attack_ids:
            problems.append(f"{scenario['id']} highlight must be an attacker")
        everyone = scenario["attackingPlayers"] + scenario["defendingPlayers"]
        for player in everyone:
            if not (0 <= player["x"] <= 100 and 0 <= player["y"] <= 100):
                problems.append(f"{scenario['id']} {player['id']} off the pitch")
        ball = scenario["ballPosition"]
        if not (0 <= ball["x"] <= 100 and 0 <= ball["y"] <= 100):
            problems.append(f"{scenario['id']} ball off the pitch")
        for index, player in enumerate(everyone):
            for other in everyone[index + 1 :]:
                if _distance(player, other) < 6:
                    problems.append(f"{scenario['id']} {player['id']} overlaps {other['id']}")
        if scenario["mode"] == "positioning":
            correct = scenario["correctPosition"]
            start = _player(scenario, scenario["highlightedPlayerId"])
            if position_score(start, scenario) != 0:
                problems.append(f"{scenario['id']} starting spot already scores")
            if position_score(correct, scenario) != 100:
                problems.append(f"{scenario['id']} correct spot is not 100")
            for other in everyone:
                if other["id"] != scenario["highlightedPlayerId"] and _distance(other, correct) < 7:
                    problems.append(f"{scenario['id']} {other['id']} covers the answer")
            for zone in scenario.get("acceptablePositionZones") or []:
                awarded = position_score(zone, scenario)
                if awarded < int(zone["score"]):
                    problems.append(f"{scenario['id']} zone scores {awarded}")
        else:
            carrier = _player(scenario, scenario["highlightedPlayerId"])
            if _distance(carrier, ball) > 7:
                problems.append(f"{scenario['id']} ball is not with the carrier")
            correct = scenario["correctAction"]
            if decision_score(correct, scenario) != 100:
                problems.append(f"{scenario['id']} correct action is not 100")
            if correct["action"] not in scenario["availableActions"]:
                problems.append(f"{scenario['id']} correct action is not available")
            for alternative in scenario.get("alternativeActions") or []:
                if decision_score(alternative, scenario) != int(alternative["score"]):
                    problems.append(f"{scenario['id']} alternative {alternative} scored wrong")
                if alternative["action"] not in scenario["availableActions"]:
                    problems.append(f"{scenario['id']} alternative action is not available")
    if modes.get("positioning") != 60 or modes.get("decision") != 40:
        problems.append(f"mode counts {modes}")
    return problems
