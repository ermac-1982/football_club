"""Scoring and path rules for Positional Quiz."""

from __future__ import annotations

import math
from typing import Optional

from coach_engine import SECTION_BONUS, label_for, result_for
from position_scenarios import SECTIONS, load_scenarios

BANDS = ((7, 100), (12, 75), (17, 50), (22, 25))
PRIVATE_FIELDS = {
    "correctPositions",
    "explanation",
    "incorrectExplanation",
    "coachingTip",
}
_SNAP = (0, 25, 50, 75, 100)


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


def _distance(a: dict, b: dict) -> float:
    return math.hypot(float(a["x"]) - float(b["x"]), float(a["y"]) - float(b["y"]))


def _band_score(distance: float) -> int:
    for limit, score in BANDS:
        if distance <= limit:
            return score
    return 0


def _snap(average: float) -> int:
    return min(_SNAP, key=lambda band: (abs(band - average), -band))


def _player(scenario: dict, player_id: str) -> Optional[dict]:
    for player in list(scenario["attackingPlayers"]) + list(scenario["defendingPlayers"]):
        if player["id"] == player_id:
            return player
    return None


def positions_score(submitted: dict[str, dict], scenario: dict) -> tuple[int, dict[str, int]]:
    marks = {}
    for pid, correct in scenario["correctPositions"].items():
        marks[pid] = _band_score(_distance(submitted[pid], correct))
    average = sum(marks.values()) / len(marks)
    return _snap(average), marks


def normalise_answer(scenario: dict, answer: dict) -> dict:
    expected = set(scenario["correctPositions"])
    raw = answer.get("placements")
    if not isinstance(raw, list):
        raise ValueError("Drag all six players, then submit.")
    found: dict[str, dict] = {}
    for item in raw:
        if not isinstance(item, dict) or "id" not in item:
            raise ValueError("Drag all six players, then submit.")
        pid = str(item["id"])
        if pid == scenario["highlightedPlayerId"]:
            raise ValueError("Leave the player on the ball where they are.")
        if pid not in expected or pid in found:
            raise ValueError("Drag all six players, then submit.")
        try:
            x = float(item["x"])
            y = float(item["y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Drag all six players, then submit.") from exc
        if not (0 <= x <= 100 and 0 <= y <= 100):
            raise ValueError("Keep every player on the pitch.")
        found[pid] = {"x": round(x, 1), "y": round(y, 1)}
    if set(found) != expected:
        raise ValueError("Drag all six players, then submit.")
    return {"placements": [{"id": pid, "x": found[pid]["x"], "y": found[pid]["y"]} for pid in scenario["movablePlayerIds"]]}


def score_answer(scenario: dict, answer: dict) -> dict:
    submitted = normalise_answer(scenario, answer)
    placed = {item["id"]: item for item in submitted["placements"]}
    score, marks = positions_score(placed, scenario)
    if score >= 50:
        explanation = scenario["explanation"]
    else:
        explanation = f"{scenario['incorrectExplanation']} {scenario['explanation']}"
    names = {player["id"]: player["name"] for player in scenario["attackingPlayers"]}
    weak = [names[pid] for pid, mark in marks.items() if mark < 75]
    if weak and score < 100:
        joined = ", ".join(weak)
        explanation = f"{explanation} Move {joined} closer to the shape."
    return {
        "scenarioId": scenario["id"],
        "mode": scenario["mode"],
        "score": score,
        "points": score,
        "result": result_for(score),
        "label": label_for(score),
        "explanation": explanation,
        "coachingTip": scenario["coachingTip"],
        "correctPositions": scenario["correctPositions"],
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
                "modeLabel": "Shape",
                "status": status,
                "completed": done,
                "total": len(rows),
                "scenarios": scenario_rows,
            }
        )
    library_best = {scenario["id"]: best[scenario["id"]] for scenario in library if scenario["id"] in best}
    attempted_ids = [scenario["id"] for scenario in library if attempts.get(scenario["id"])]
    correct = sum(1 for scenario_id in attempted_ids if library_best.get(scenario_id, 0) >= 75)
    average = round(sum(library_best[scenario_id] for scenario_id in attempted_ids) / len(attempted_ids)) if attempted_ids else 0
    progress = {
        "attempted": len(attempted_ids),
        "total": len(library),
        "totalAttempts": sum(len(attempts.get(scenario["id"]) or []) for scenario in library),
        "correct": correct,
        "accuracy": round(100 * correct / len(attempted_ids)) if attempted_ids else 0,
        "averageScore": average,
        "bestScore": max(library_best.values()) if library_best else 0,
        "totalScore": total_score(attempts),
        "maxScore": 100 * len(library) + SECTION_BONUS * len(SECTIONS),
        "byCategory": _grouped(library, attempts, library_best, "category"),
        "byDifficulty": _grouped(library, attempts, library_best, "difficulty"),
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
    labels = {"diamond": "Diamond", "compact": "Compact", "cover": "Cover", "balance": "Balance"}
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
                "label": labels.get(key, key[:1].upper() + key[1:]),
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
    if ids != list(range(1, len(_expected_count()) + 1)):
        problems.append(f"ids are {ids}")
    section_ids = [section["id"] for section in SECTIONS]
    if len(section_ids) != len(set(section_ids)):
        problems.append("duplicate section id")
    by_section = {section["id"]: [] for section in SECTIONS}
    for scenario in library:
        if scenario["section"] not in by_section:
            problems.append(f"{scenario['id']} unknown section")
            continue
        by_section[scenario["section"]].append(scenario["id"])
        if scenario["mode"] != "positions":
            problems.append(f"{scenario['id']} mode")
        if len(scenario["attackingPlayers"]) != 7 or len(scenario["defendingPlayers"]) != 7:
            problems.append(f"{scenario['id']} needs 7v7")
        attack_ids = [player["id"] for player in scenario["attackingPlayers"]]
        carrier = scenario["highlightedPlayerId"]
        if carrier not in attack_ids or set(scenario["movablePlayerIds"]) != set(attack_ids) - {carrier}:
            problems.append(f"{scenario['id']} movers")
        if set(scenario["correctPositions"]) != set(scenario["movablePlayerIds"]):
            problems.append(f"{scenario['id']} answers")
        everyone = scenario["attackingPlayers"] + scenario["defendingPlayers"]
        for player in everyone:
            if not (0 <= player["x"] <= 100 and 0 <= player["y"] <= 100):
                problems.append(f"{scenario['id']} {player['id']} off the pitch")
        ball = scenario["ballPosition"]
        if not (0 <= ball["x"] <= 100 and 0 <= ball["y"] <= 100):
            problems.append(f"{scenario['id']} ball off the pitch")
        carrier_player = _player(scenario, carrier)
        if _distance(carrier_player, ball) > 8:
            problems.append(f"{scenario['id']} ball is not with the carrier")
        for index, player in enumerate(everyone):
            for other in everyone[index + 1 :]:
                if _distance(player, other) < 8:
                    problems.append(f"{scenario['id']} {player['id']} overlaps {other['id']}")
        starts = {item["id"]: item for item in scenario["attackingPlayers"]}
        for pid, correct in scenario["correctPositions"].items():
            if _band_score(_distance(starts[pid], correct)) != 0:
                problems.append(f"{scenario['id']} {pid} already scores")
            if _band_score(0) != 100:
                problems.append("bands")
            placed = dict(starts)
            placed[pid] = correct
            # correct spot itself must be a perfect mark for that player
            if _band_score(_distance(correct, correct)) != 100:
                problems.append(f"{scenario['id']} {pid} correct is not 100")
            for other in everyone:
                if other["id"] != pid and _distance(other, correct) < 8 and other["id"] not in scenario["correctPositions"]:
                    problems.append(f"{scenario['id']} {other['id']} covers {pid}")
        perfect = {pid: dict(spot) for pid, spot in scenario["correctPositions"].items()}
        score, marks = positions_score(perfect, scenario)
        if score != 100 or any(mark != 100 for mark in marks.values()):
            problems.append(f"{scenario['id']} perfect score {score}")
    if any(len(rows) != 4 for rows in by_section.values()):
        problems.append(f"section sizes {[len(rows) for rows in by_section.values()]}")
    return problems


def _expected_count() -> list[dict]:
    return scenarios()
