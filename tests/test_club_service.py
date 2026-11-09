import unittest
import uuid

from club_service import (
    ClubError,
    clean_club_name,
    club_for,
    create_club,
    join_club,
    leaderboard,
    leave_club,
    ordered_ranks,
    search_clubs,
    update_club,
)
from db import CoachAttempt, PlayerAvatar, SessionLocal, User, init_db


class ClubRankTest(unittest.TestCase):
    def test_name_rules(self):
        self.assertEqual(clean_club_name("  Volt   United "), "Volt United")
        self.assertEqual(clean_club_name("St Mary's U10"), "St Mary's U10")
        with self.assertRaises(ClubError):
            clean_club_name("A")
        with self.assertRaises(ClubError):
            clean_club_name("Volt!!!")

    def test_ties_share_a_rank(self):
        ranks = ordered_ranks(
            [
                {"user_id": "b", "name": "Bea", "score": 100},
                {"user_id": "a", "name": "Ava", "score": 100},
                {"user_id": "c", "name": "Cal", "score": 40},
            ]
        )
        self.assertEqual([row["name"] for row in ranks], ["Ava", "Bea", "Cal"])
        self.assertEqual([row["rank"] for row in ranks], [1, 1, 3])


class ClubFlowTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.user_ids = []

    def tearDown(self):
        self.db.rollback()
        for user_id in self.user_ids:
            row = self.db.get(User, user_id)
            if row is not None:
                self.db.delete(row)
        self.db.commit()
        self.db.close()

    def _user(self, account_type: str, first_name: str) -> User:
        user = User(
            first_name=first_name,
            email=f"volt-club-{uuid.uuid4().hex}@example.com",
            account_type=account_type,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.user_ids.append(user.id)
        return user

    def _nickname(self, user: User, nickname: str) -> None:
        self.db.add(
            PlayerAvatar(
                user_id=user.id,
                gender="M",
                skin_color="dark",
                kit_primary="black",
                kit_accent="lime",
                kit_style="volt",
                boots_color="black",
                hair_style="curly",
                hair_color="black",
                body_type="lean",
                nickname=nickname,
                is_custom=True,
            )
        )
        self.db.commit()
        self.db.expire(user, ["avatar"])

    def test_create_join_switch_and_rank(self):
        coach = self._user("coach_admin", "Alex")
        other = self._user("coach_admin", "Sam")
        ava = self._user("player", "Ava")
        ben = self._user("player", "Ben")
        self._nickname(ava, "Ava")
        self._nickname(ben, "Ben")

        with self.assertRaises(ClubError):
            create_club(self.db, ava, "Player FC", "black", "lime")
        created = create_club(self.db, coach, "Volt United", "black", "lime")
        self.assertEqual(created["name"], "Volt United")
        self.assertEqual(created["primary_color"]["id"], "black")
        self.assertEqual(created["accent_color"]["id"], "lime")
        with self.assertRaises(ClubError):
            create_club(self.db, other, "volt united", "orange", "cyan")
        second = create_club(self.db, other, "River City", "navy", "cyan")

        with self.assertRaises(ClubError):
            join_club(self.db, coach, uuid.UUID(created["id"]))
        join_club(self.db, ava, uuid.UUID(created["id"]))
        join_club(self.db, ben, uuid.UUID(created["id"]))
        self.db.add(CoachAttempt(user_id=ava.id, scenario_id=1, score=80, result="partial"))
        self.db.add(CoachAttempt(user_id=ava.id, scenario_id=1, score=100, result="correct"))
        self.db.commit()

        board = leaderboard(self.db, ava)
        self.assertEqual(board["club"]["name"], "Volt United")
        self.assertEqual([row["name"] for row in board["ranks"]], ["Ava", "Ben"])
        self.assertEqual(board["ranks"][0]["score"], 100)
        self.assertEqual(board["ranks"][1]["score"], 0)
        self.assertTrue(board["ranks"][0]["you"])
        self.assertFalse(board["ranks"][1]["you"])
        self.assertEqual(leaderboard(self.db, coach)["ranks"][0]["name"], "Ava")

        join_club(self.db, ava, uuid.UUID(second["id"]))
        self.assertEqual(club_for(self.db, ava)["name"], "River City")
        self.assertEqual([row["name"] for row in leaderboard(self.db, coach)["ranks"]], ["Ben"])
        self.assertEqual(leaderboard(self.db, ava)["ranks"][0]["name"], "Ava")

        found = search_clubs(self.db, "volt")
        self.assertEqual([club["name"] for club in found], ["Volt United"])
        self.assertEqual(search_clubs(self.db, "no-such-club"), [])

        saved = update_club(self.db, coach, "Volt City", "yellow", "purple")
        self.assertEqual(saved["name"], "Volt City")
        self.assertEqual(saved["primary_color"]["label"], "Yellow")
        self.assertEqual(saved["accent_color"]["id"], "purple")

        leave_club(self.db, ben)
        with self.assertRaises(ClubError):
            leaderboard(self.db, ben)
        self.assertIsNone(club_for(self.db, ben))
