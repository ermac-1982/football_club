import unittest
import uuid
from unittest.mock import patch

import settings
from auth_service import _send_code, request_email_code, verify_email_code
from db import EmailCode, SessionLocal, User, init_db


class EmailCodeTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.email = f"volt-code-{uuid.uuid4().hex}@example.com"
        self.user_ids = []
        self.resend_key = settings.RESEND_API_KEY

    def tearDown(self):
        settings.RESEND_API_KEY = self.resend_key
        self.db.rollback()
        self.db.query(EmailCode).filter(EmailCode.email == self.email).delete()
        for user_id in self.user_ids:
            row = self.db.get(User, user_id)
            if row is not None:
                self.db.delete(row)
        self.db.commit()
        self.db.close()

    def test_a_code_creates_the_player_only_after_it_matches(self):
        sent = []

        def remember(email, code):
            sent.append((email, code))
            return True

        with patch("auth_service._send_code", side_effect=remember):
            shown = request_email_code(
                self.db,
                self.email,
                "register",
                "Ava",
                "player",
                "VoltTest1!",
            )
        self.assertIsNone(shown)
        self.assertEqual(sent[0][0], self.email)
        with self.assertRaises(Exception):
            verify_email_code(self.db, self.email, "000000")
        user = verify_email_code(self.db, self.email, sent[0][1])
        self.user_ids.append(user.id)
        self.assertEqual(user.account_type, "player")
        self.assertTrue(user.password_hash)

    def test_resend_posts_the_code(self):
        settings.RESEND_API_KEY = "test-key"
        with patch("auth_service.httpx.post") as post:
            post.return_value.status_code = 200
            self.assertTrue(_send_code(self.email, "123456"))
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["to"], [self.email])
        self.assertIn("123456", body["text"])
        self.assertTrue(post.call_args.kwargs["headers"]["Authorization"].startswith("Bearer "))
