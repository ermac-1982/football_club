import unittest

from app import COACH_MENU, _place_for


class PlaceTest(unittest.TestCase):
    def test_an_open_drill_is_not_kept_in_the_address_bar(self):
        page, view, drill = _place_for("Situational Coach", "home")
        self.assertEqual(page, "Situational Coach")
        self.assertEqual(view, "")
        self.assertEqual(drill, "")

        page, view, drill = _place_for("Positional Quiz", "home")
        self.assertEqual((page, view, drill), ("Positional Quiz", "", ""))

    def test_coach_pages_are_remembered_without_a_drill(self):
        self.assertEqual(_place_for("Home", "home", COACH_MENU), ("Home", "", ""))
        self.assertEqual(_place_for("Leaderboard", "home", COACH_MENU), ("Leaderboard", "", ""))
        self.assertEqual(_place_for("Situational Coach", "home", COACH_MENU), ("Home", "", ""))

    def test_avatar_is_still_remembered(self):
        self.assertEqual(_place_for("Situational Coach", "avatar"), ("Situational Coach", "avatar", ""))
        self.assertEqual(_place_for("Edit avatar", "home"), ("Edit avatar", "avatar", ""))
