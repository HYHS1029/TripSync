"""Authentication regression tests; all account writes use isolated in-memory SQLite."""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Configure before importing the app. Never connect tests to the developer database.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "tripsync-test-only-key-not-for-real-use-123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    create_access_token,
    hash_password,
    verify_password,
)
from app.database import Base, get_db
from app.main import app
from app.models.user import User


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.password = "correct-horse-battery-123"
        cls.password_hash = hash_password(cls.password)
        get_settings.cache_clear()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        get_settings.cache_clear()

    def setUp(self):
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            user = User(
                email="traveler@example.com",
                email_verified_at=datetime.now(timezone.utc),
                username="traveler",
                password_hash=self.password_hash,
            )
            db.add(user)
            db.commit()
            self.user_id = user.id

        def override_get_db():
            with Session(self.engine) as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def login(self, **overrides):
        return self.client.post(
            "/auth/login",
            json={"email": "traveler@example.com", "password": self.password} | overrides,
        )

    def signed_token(self, changes=None, omit=()):
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(self.user_id),
            "iat": now,
            "exp": now + timedelta(minutes=30),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "type": "access",
        }
        claims.update(changes or {})
        for key in omit:
            claims.pop(key)
        return jwt.encode(
            claims, get_settings().jwt_secret_key.get_secret_value(), algorithm=JWT_ALGORITHM
        )

    def assert_unauthorized(self, token=None, scheme="Bearer"):
        headers = {"Authorization": f"{scheme} {token}"} if token else {}
        response = self.client.get("/users/me", headers=headers)
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.headers["www-authenticate"], "Bearer")
        return response

    def test_login_returns_signed_token_and_expiry(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["pragma"], "no-cache")
        data = response.json()
        self.assertEqual(set(data), {"access_token", "token_type", "expires_in"})
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["expires_in"], 1800)
        payload = jwt.decode(
            data["access_token"],
            get_settings().jwt_secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )
        self.assertEqual(payload["sub"], str(self.user_id))
        self.assertEqual(payload["exp"] - payload["iat"], 1800)
        self.assertEqual(payload["type"], "access")

    def test_current_user_returns_only_public_fields(self):
        token = self.login().json()["access_token"]
        response = self.client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(set(response.json()), {"id", "email", "email_verified_at", "pending_email", "username", "created_at"})
        self.assertEqual(response.json()["id"], self.user_id)

    def test_unknown_email_and_wrong_password_have_same_error(self):
        wrong_password = self.login(password="incorrect-password")
        unknown_email = self.login(email="unknown@example.com")
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_email.status_code, 401)
        self.assertEqual(wrong_password.json(), unknown_email.json())
        self.assertEqual(wrong_password.headers["www-authenticate"], "Bearer")
        self.assertNotIn("access_token", wrong_password.json())

    def test_unknown_email_still_verifies_password_hash(self):
        with patch("app.api.auth.verify_password", wraps=verify_password) as verify:
            self.assertEqual(self.login(email="unknown@example.com").status_code, 401)
            verify.assert_called_once()

    def test_invalid_login_payloads(self):
        for body in [
            {},
            {"email": "invalid@", "password": self.password},
            {"email": "traveler@example.com", "password": "short"},
            {"email": "traveler@example.com", "password": "x" * 129},
            {"email": "traveler@example.com", "password": None},
        ]:
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/auth/login", json=body).status_code, 422)

    def test_password_whitespace_matches_existing_registration_policy(self):
        self.assertEqual(self.login(password="  " + self.password + "  ").status_code, 200)

    def test_missing_malformed_and_wrong_scheme_tokens(self):
        self.assert_unauthorized()
        self.assert_unauthorized("not-a-token")
        self.assert_unauthorized(create_access_token(self.user_id), scheme="Basic")

    def test_invalid_claims_are_rejected(self):
        now = datetime.now(timezone.utc)
        cases = [
            {"exp": now - timedelta(seconds=1)},
            {"iat": now + timedelta(minutes=1)},
            {"iss": "another-app"},
            {"aud": "another-client"},
            {"type": "refresh"},
            {"sub": "not-a-number"},
            {"sub": "0"},
            {"sub": "-1"},
            {"sub": "2147483648"},
            {"sub": "9" * 5000},
            {"sub": "١"},
            {"sub": 1},
        ]
        for changes in cases:
            with self.subTest(claims=list(changes)):
                self.assert_unauthorized(self.signed_token(changes))

    def test_required_claims_cannot_be_omitted(self):
        for claim in ["sub", "exp", "iat", "iss", "aud", "type"]:
            with self.subTest(claim=claim):
                self.assert_unauthorized(self.signed_token(omit=[claim]))

    def test_wrong_signature_and_algorithm_are_rejected(self):
        valid = self.signed_token()
        self.assert_unauthorized(valid[:-8] + "tampered")
        claims = jwt.decode(valid, options={"verify_signature": False})
        wrong_key = jwt.encode(claims, "a-different-test-key-with-32-plus-characters", algorithm="HS256")
        self.assert_unauthorized(wrong_key)
        wrong_algorithm = jwt.encode(
            claims, get_settings().jwt_secret_key.get_secret_value(), algorithm="HS384"
        )
        self.assert_unauthorized(wrong_algorithm)
        self.assert_unauthorized(jwt.encode(claims, key="", algorithm="none"))

    def test_deleted_user_token_is_rejected(self):
        self.assert_unauthorized(create_access_token(self.user_id + 999))

    def test_valid_token_can_only_identify_its_owner(self):
        with Session(self.engine) as db:
            other = User(email="other@example.com", username="other", password_hash=self.password_hash)
            db.add(other)
            db.commit()
            other_id = other.id
        token = create_access_token(other_id)
        response = self.client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], other_id)
        self.assertNotEqual(response.json()["id"], self.user_id)

    def test_registration_still_hashes_password_and_can_login(self):
        response = self.client.post(
            "/users", json={"email": "new@example.com", "username": "new_user", "password": self.password}
        )
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password_hash", response.json())
        with Session(self.engine) as db:
            user = db.scalar(select(User).where(User.username == "new_user"))
            self.assertIsNone(user.email)
            self.assertEqual(user.pending_email, "new@example.com")
            self.assertNotEqual(user.password_hash, self.password)
            self.assertTrue(verify_password(self.password, user.password_hash))
        self.assertEqual(self.login(email="new@example.com").status_code, 401)
        token = self.login(email="new_user").json()["access_token"]
        me = self.client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me.json()["username"], "new_user")

    def test_duplicate_registration_remains_conflict(self):
        response = self.client.post(
            "/users", json={"email": "traveler@example.com", "username": "traveler", "password": self.password}
        )
        self.assertEqual(response.status_code, 409)

    def test_invalid_stored_password_hash_is_unauthorized(self):
        with Session(self.engine) as db:
            db.get(User, self.user_id).password_hash = "invalid-hash"
            db.commit()
        self.assertEqual(self.login().status_code, 401)

    def test_token_expiry_is_configurable(self):
        with patch.dict(os.environ, {"ACCESS_TOKEN_EXPIRE_MINUTES": "5"}):
            get_settings.cache_clear()
            response = self.login()
            self.assertEqual(response.json()["expires_in"], 300)
        get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
