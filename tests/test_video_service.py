import unittest
import uuid

from club_service import create_club, join_club, leaderboard
from db import CoachAttempt, PlayerAvatar, SessionLocal, User, init_db
from video_service import VIDEO_POINTS, VideoError, record_watch


class VideoWatchTest(unittest.TestCase):
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
            email=f"volt-video-{uuid.uuid4().hex}@example.com",
            account_type=account_type,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.user_ids.append(user.id)
        return user

    def test_a_clip_charges_once_and_ranks_on_the_squad(self):
        coach = self._user("coach_admin", "Coach")
        ava = self._user("player", "Ava")
        self.db.add(
            PlayerAvatar(
                user_id=ava.id,
                gender="F",
                skin_color="light",
                kit_primary="black",
                kit_accent="lime",
                kit_style="volt",
                boots_color="orange",
                hair_style="ponytail",
                hair_color="blonde",
                body_type="lean",
                nickname="Ava",
                is_custom=True,
            )
        )
        self.db.commit()
        club = create_club(self.db, coach, "Volt United", "black", "lime")
        join_club(self.db, ava, uuid.UUID(club["id"]))

        first = record_watch(self.db, ava, "form_231")
        self.assertTrue(first["awarded"])
        self.assertEqual(first["points"], VIDEO_POINTS)
        again = record_watch(self.db, ava, "form_231")
        self.assertFalse(again["awarded"])
        self.assertEqual(again["points"], 0)
        self.assertEqual(leaderboard(self.db, ava)["ranks"][0]["score"], VIDEO_POINTS)

        self.db.add(CoachAttempt(user_id=ava.id, scenario_id=1, score=100, result="correct"))
        self.db.commit()
        self.assertEqual(leaderboard(self.db, ava)["ranks"][0]["score"], 100 + VIDEO_POINTS)

        with self.assertRaises(VideoError) as missing:
            record_watch(self.db, ava, "../secret")
        self.assertEqual(missing.exception.status_code, 404)
        with self.assertRaises(VideoError) as coach_clip:
            record_watch(self.db, coach, "form_231")
        self.assertEqual(coach_clip.exception.status_code, 403)
