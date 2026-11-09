"""Save Situational Coach attempts against the signed-in player."""

from __future__ import annotations

from sqlalchemy.orm import Session

from coach_engine import (
    SECTION_BONUS,
    build_path,
    get_scenario,
    next_incomplete,
    public_scenario,
    scenarios,
    score_answer,
    section_status,
    total_score,
)
from coach_scenarios import SECTIONS
from db import CoachAttempt, User


class CoachError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _attempts(db: Session, user_id) -> dict[int, list[int]]:
    rows = db.query(CoachAttempt).filter(CoachAttempt.user_id == user_id).all()
    grouped: dict[int, list[int]] = {}
    for row in rows:
        grouped.setdefault(row.scenario_id, []).append(row.score)
    return grouped


def _scenario_or_404(scenario_id: int) -> dict:
    try:
        return get_scenario(scenario_id)
    except KeyError as exc:
        raise CoachError(404, "That drill does not exist.") from exc


def path_for(db: Session, user: User) -> dict:
    return build_path(_attempts(db, user.id))


def scenario_for(db: Session, user: User, scenario_id: int) -> dict:
    scenario = _scenario_or_404(scenario_id)
    status = section_status(_attempts(db, user.id), scenario["section"])
    if status == "locked":
        raise CoachError(403, "Finish the earlier section first.")
    return public_scenario(scenario)


def answer_scenario(db: Session, user: User, scenario_id: int, answer: dict) -> dict:
    scenario = _scenario_or_404(scenario_id)
    attempts = _attempts(db, user.id)
    if section_status(attempts, scenario["section"]) == "locked":
        raise CoachError(403, "Finish the earlier section first.")
    try:
        scored = score_answer(scenario, answer)
    except ValueError as exc:
        raise CoachError(400, str(exc)) from exc
    db.add(
        CoachAttempt(
            user_id=user.id,
            scenario_id=scenario_id,
            score=scored["score"],
            result=scored["result"],
        )
    )
    before = section_status(attempts, scenario["section"])
    db.commit()
    attempts.setdefault(scenario_id, []).append(scored["score"])
    finished = section_status(attempts, scenario["section"]) == "complete"
    just_finished = finished and before != "complete"
    section = next(item for item in SECTIONS if item["id"] == scenario["section"])
    scored["totalScore"] = total_score(attempts)
    scored["maxScore"] = 100 * len(scenarios()) + SECTION_BONUS * len(SECTIONS)
    scored["nextScenarioId"] = next_incomplete(attempts)
    scored["sectionComplete"] = finished
    scored["sectionJustCompleted"] = just_finished
    scored["sectionBonus"] = SECTION_BONUS if just_finished else 0
    scored["sectionTitle"] = section["title"]
    return scored
