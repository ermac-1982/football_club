import unittest
import uuid
from datetime import timedelta

import jwt
from fastapi.testclient import TestClient

import settings
from api import app
from auth_service import (
    ACCESS_MINUTES,
    REFRESH_DAYS,
    AuthError,
    issue_refresh_token,
    issue_session,
    rotate_refresh_token,
)
from db import RefreshToken, SessionLocal, User, init_db, utcnow


class AccessTokenTest(unittest.TestCase):
    def test_access_token_lasts_one_hour(self):
        class Person:
            id = uuid.uuid4()

        data = jwt.decode(issue_session(Person()), settings.SECRET_KEY, algorithms=["HS256"])
        self.assertEqual(data["exp"] - data["iat"], ACCESS_MINUTES * 60)


class RefreshTokenTest(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.user_ids = []
        self.client = TestClient(app)

    def tearDown(self):
        self.db.rollback()
        for user_id in self.user_ids:
            row = self.db.get(User, user_id)
            if row is not None:
                self.db.delete(row)
        self.db.commit()
        self.db.close()

    def _user(self) -> User:
        user = User(
            first_name="Ava",
            email=f"volt-refresh-{uuid.uuid4().hex}@example.com",
            account_type="player",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.user_ids.append(user.id)
        return user

    def test_rotation_lasts_30_days_and_reuse_revokes_the_family(self):
        user = self._user()
        first = issue_refresh_token(self.db, user)
        _user, second = rotate_refresh_token(self.db, first)
        live = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .all()
        )
        self.assertEqual(len(live), 1)
        remaining = live[0].expires_at - utcnow()
        self.assertGreater(remaining, timedelta(days=REFRESH_DAYS - 1))
        with self.assertRaises(AuthError):
            rotate_refresh_token(self.db, first)
        self.db.expire_all()
        still_live = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .count()
        )
        self.assertEqual(still_live, 0)
        with self.assertRaises(AuthError):
            rotate_refresh_token(self.db, second)

    def test_cookie_is_http_only_and_remembers_a_login(self):
        email = f"volt-refresh-{uuid.uuid4().hex}@example.com"
        registered = self.client.post(
            "/auth/register",
            json={
                "email": email,
                "first_name": "Ava",
                "account_type": "player",
                "password": "VoltTest1!",
            },
        )
        self.assertEqual(registered.status_code, 200, registered.text)
        body = registered.json()
        user_id = uuid.UUID(body["user"]["id"])
        self.user_ids.append(user_id)
        self.assertIn("cookie_grant", body)
        self.assertNotIn("refresh", body)
        planted = self.client.post("/auth/cookie", json={"grant": body["cookie_grant"]})
        self.assertEqual(planted.status_code, 200, planted.text)
        cookie = planted.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertIn("path=/auth", cookie)
        self.assertIn("max-age=2592000", cookie)
        self.assertNotIn(body["cookie_grant"], planted.headers["set-cookie"])
        refreshed = self.client.post("/auth/refresh")
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        code = refreshed.json()["code"]
        exchanged = self.client.post("/auth/exchange", json={"code": code})
        self.assertEqual(exchanged.status_code, 200, exchanged.text)
        self.assertEqual(exchanged.json()["kind"], "session")
        self.assertNotIn("cookie_grant", exchanged.json())
        logged_out = self.client.post("/auth/logout")
        self.assertEqual(logged_out.status_code, 200)
        self.assertIn("max-age=0", logged_out.headers["set-cookie"].lower())
        forgotten = self.client.post("/auth/refresh")
        self.assertEqual(forgotten.status_code, 401)
