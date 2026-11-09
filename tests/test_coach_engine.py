import unittest

from coach_engine import build_path, decision_score, position_score, score_answer, scenarios, validate_library


class CoachLibraryTest(unittest.TestCase):
    def test_library_is_complete(self):
        self.assertEqual(validate_library(), [])

    def test_counts_and_modes(self):
        library = scenarios()
        self.assertEqual(len(library), 100)
        self.assertEqual(sum(item["mode"] == "positioning" for item in library), 60)
        self.assertEqual(sum(item["mode"] == "decision" for item in library), 40)
        self.assertEqual({item["difficulty"] for item in library}, {"easy", "medium", "hard"})

    def test_position_bands_and_zones(self):
        scenario = next(item for item in scenarios() if item["id"] == 4)
        correct = scenario["correctPosition"]
        self.assertEqual(position_score(correct, scenario), 100)
        far = {"x": correct["x"], "y": max(0, correct["y"] - 40)}
        if abs(far["y"] - correct["y"]) < 30:
            far = {"x": max(0, correct["x"] - 40), "y": correct["y"]}
        self.assertEqual(position_score(far, scenario), 0)
        for zone in scenario["acceptablePositionZones"]:
            self.assertGreaterEqual(position_score(zone, scenario), zone["score"])

    def test_decision_levels(self):
        scenario = next(item for item in scenarios() if item["id"] == 14)
        self.assertEqual(decision_score(scenario["correctAction"], scenario), 100)
        for alternative in scenario["alternativeActions"]:
            self.assertEqual(decision_score(alternative, scenario), alternative["score"])
        self.assertEqual(decision_score({"action": "pass", "targetPlayerId": "st"}, scenario), 0)

    def test_path_unlocks_in_order(self):
        path = build_path({})
        self.assertEqual(path["sections"][0]["status"], "current")
        self.assertTrue(all(section["status"] == "locked" for section in path["sections"][1:]))
        first = path["sections"][0]
        attempts = {scenario["id"]: [100] for scenario in first["scenarios"]}
        opened = build_path(attempts)
        self.assertEqual(opened["sections"][0]["status"], "complete")
        self.assertEqual(opened["sections"][1]["status"], "current")
        self.assertEqual(opened["progress"]["attempted"], first["total"])
        self.assertEqual(opened["progress"]["accuracy"], 100)
        self.assertEqual(opened["progress"]["totalScore"], first["total"] * 100 + 500)
        self.assertEqual(opened["progress"]["maxScore"], 10000 + 500 * len(opened["sections"]))
        replay = dict(attempts)
        replay[first["scenarios"][0]["id"]] = [100, 25]
        self.assertEqual(build_path(replay)["progress"]["totalScore"], opened["progress"]["totalScore"])

    def test_total_score_keeps_the_best_attempt(self):
        from coach_engine import total_score

        self.assertEqual(total_score({1: [25, 100], 2: [75, 50]}), 175)
        self.assertEqual(total_score({}), 0)

    def test_public_score_hides_the_answer_until_submit(self):
        from coach_engine import public_scenario

        scenario = scenarios()[0]
        public = public_scenario(scenario)
        self.assertNotIn("correctPosition", public)
        self.assertNotIn("explanation", public)
        scored = score_answer(scenario, scenario["correctPosition"])
        self.assertEqual(scored["result"], "correct")
        self.assertEqual(scored["points"], 100)


if __name__ == "__main__":
    unittest.main()
