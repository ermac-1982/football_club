import unittest

from position_engine import build_path, public_scenario, score_answer, scenarios, validate_library


class PositionLibraryTest(unittest.TestCase):
    def test_library_is_complete(self):
        self.assertEqual(validate_library(), [])

    def test_counts(self):
        library = scenarios()
        self.assertEqual(len(library), 16)
        self.assertTrue(all(item["mode"] == "positions" for item in library))
        self.assertEqual(len({item["section"] for item in library}), 4)

    def test_perfect_shape_scores_100_and_the_start_does_not(self):
        for scenario in scenarios():
            perfect = {
                "placements": [
                    {"id": pid, **spot} for pid, spot in scenario["correctPositions"].items()
                ]
            }
            scored = score_answer(scenario, perfect)
            self.assertEqual(scored["score"], 100, scenario["title"])
            self.assertEqual(scored["result"], "correct")
            starts = {
                "placements": [
                    {"id": player["id"], "x": player["x"], "y": player["y"]}
                    for player in scenario["attackingPlayers"]
                    if player["id"] != scenario["highlightedPlayerId"]
                ]
            }
            opened = score_answer(scenario, starts)
            self.assertEqual(opened["score"], 0, scenario["title"])
            self.assertNotIn("correctPositions", public_scenario(scenario))

    def test_path_unlocks_in_order(self):
        path = build_path({})
        self.assertEqual(path["sections"][0]["status"], "current")
        self.assertTrue(all(section["status"] == "locked" for section in path["sections"][1:]))
        self.assertEqual(path["progress"]["maxScore"], 1600 + 500 * 4)
        first = path["sections"][0]
        attempts = {scenario["id"]: [100] for scenario in first["scenarios"]}
        opened = build_path(attempts)
        self.assertEqual(opened["sections"][0]["status"], "complete")
        self.assertEqual(opened["sections"][1]["status"], "current")
        self.assertEqual(opened["progress"]["totalScore"], first["total"] * 100 + 500)


if __name__ == "__main__":
    unittest.main()
