"""Email lifecycle and abuse controls; isolated SQLite, mocked delivery only."""
import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "tripsync-test-only-key-not-for-real-use-123456789"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import verification_digest
from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models.auth_rate_limit import AuthRateLimit
from app.models.user import User
from app.services.email import EmailDeliveryError, send_email, send_verification_email

REQUEST = "/auth/email-verification/request"
CONFIRM = "/auth/email-verification/confirm"


class EmailVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "correct-horse-battery-123"
        cls.password_hash = hash_password(cls.password)

    def setUp(self):
        self.now = int(time.time()) // 60 * 60 + 10
        self.clock_patch = patch("app.core.rate_limit.time")
        self.clock_patch.start().time.return_value = self.now
        self.environment = patch.dict(os.environ, {
            "EMAIL_VERIFICATION_ENABLED": "true",
            "SMTP_HOST": "127.0.0.1", "SMTP_PORT": "1025", "SMTP_SECURITY": "none",
            "SMTP_USERNAME": "", "SMTP_PASSWORD": "", "FRONTEND_URL": "http://localhost:3000",
        })
        self.environment.start()
        get_settings.cache_clear()
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            user = User(username="traveler", password_hash=self.password_hash)
            other = User(username="other", password_hash=self.password_hash)
            db.add_all([user, other])
            db.commit()
            self.user_id, self.other_id = user.id, other.id
        def database():
            with Session(self.engine) as db:
                yield db
        app.dependency_overrides[get_db] = database
        self.client = TestClient(app)
        self.delivery_patch = patch("app.api.auth.send_verification_email")
        self.delivery = self.delivery_patch.start()
        self.notice_patch = patch("app.api.auth.send_email")
        self.notice = self.notice_patch.start()

    def tearDown(self):
        self.clock_patch.stop()
        self.client.close()
        app.dependency_overrides.clear()
        self.delivery_patch.stop()
        self.notice_patch.stop()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.environment.stop()
        get_settings.cache_clear()

    def headers(self, user_id=None):
        return {"Authorization": f"Bearer {create_access_token(user_id or self.user_id)}"}

    def request_email(self, email="traveler@example.com", user_id=None, password=None):
        return self.client.post(REQUEST, headers=self.headers(user_id), json={"email": email, "password": password or self.password})

    def issue(self, **kwargs):
        response = self.request_email(**kwargs)
        self.assertEqual(response.status_code, 202, response.text)
        return self.delivery.call_args.args[2]

    def confirm(self, token, user_id=None):
        return self.client.post(CONFIRM, headers=self.headers(user_id), json={"token": token})

    def login(self, identifier, password=None):
        return self.client.post("/auth/login", json={"identifier": identifier, "password": password or self.password})

    def test_username_only_registration_and_pending_email_do_not_reserve_address(self):
        for username, extra in [("no_email", {}), ("pending_one", {"email": "shared@example.com"}), ("pending_two", {"email": "shared@example.com"})]:
            response = self.client.post("/users", json={"username": username, "password": self.password, **extra})
            self.assertEqual(response.status_code, 201)
            self.assertIsNone(response.json()["email"])
            self.assertIsNone(response.json()["email_verified_at"])
            self.assertNotIn("token", response.text)
            self.assertEqual(self.login(username).status_code, 200)
        self.assertEqual(self.login("shared@example.com").status_code, 401)

    def test_disabled_feature_blocks_both_endpoints_without_consuming_pending_token(self):
        token = self.issue()
        self.delivery.reset_mock()
        with patch.dict(os.environ, {"EMAIL_VERIFICATION_ENABLED": "false"}):
            get_settings.cache_clear()
            self.assertEqual(self.request_email().status_code, 404)
            self.assertEqual(self.confirm(token).status_code, 404)
            self.assertEqual(self.client.post(REQUEST, json={"email": "a@example.com", "password": self.password}).status_code, 404)
            self.assertEqual(self.login("traveler").status_code, 200)
            with Session(self.engine) as db:
                user = db.get(User, self.user_id)
                self.assertIsNone(user.email)
                self.assertEqual(user.email_verification_token_hash, verification_digest(token))
            self.delivery.assert_not_called()
            self.notice.assert_not_called()
        get_settings.cache_clear()
        self.assertEqual(self.confirm(token).status_code, 200)

    def test_round_trip_stores_only_digest_and_enables_email_login(self):
        self.assertEqual(self.login("traveler@example.com").status_code, 401)
        token = self.issue()
        with Session(self.engine) as db:
            user = db.get(User, self.user_id)
            self.assertEqual(user.email_verification_token_hash, verification_digest(token))
            self.assertNotEqual(user.email_verification_token_hash, token)
            self.assertIsNone(user.email)
        confirmed = self.confirm(token)
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["email"], "traveler@example.com")
        self.assertIsNotNone(confirmed.json()["email_verified_at"])
        self.assertIsNone(confirmed.json()["pending_email"])
        self.assertNotIn(token, confirmed.text)
        self.assertNotIn("token_hash", confirmed.text)
        self.assertEqual(self.login("traveler@example.com").status_code, 200)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(User, self.user_id).email_verification_token_hash)

    def test_single_use_wrong_account_and_purpose_are_rejected(self):
        token = self.issue()
        self.assertEqual(self.confirm(token, self.other_id).status_code, 400)
        self.assertEqual(self.confirm("x" * 43).status_code, 400)
        self.assertEqual(self.confirm(create_access_token(self.user_id)).status_code, 422)
        self.assertEqual(self.confirm(token).status_code, 200)
        self.assertEqual(self.confirm(token).status_code, 400)

    def test_expired_and_malformed_tokens_do_not_bind_email(self):
        token = self.issue()
        with Session(self.engine) as db:
            db.get(User, self.user_id).email_verification_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.confirm(token).status_code, 400)
        for invalid in ["", token + "\n", "x" * 44, "../" + "x" * 40, None]:
            response = self.confirm(invalid)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn('"input"', response.text)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(User, self.user_id).email)

    def test_resend_invalidates_previous_link(self):
        old = self.issue()
        with patch("app.core.rate_limit.time.time", return_value=self.now + 61):
            new = self.issue()
        self.assertNotEqual(old, new)
        self.assertEqual(self.confirm(old).status_code, 400)
        self.assertEqual(self.confirm(new).status_code, 200)

    def test_delivery_failure_preserves_previous_pending_token(self):
        old = self.issue()
        self.delivery.side_effect = EmailDeliveryError("provider-private-error")
        with patch("app.core.rate_limit.time.time", return_value=self.now + 61):
            response = self.request_email("new@example.com")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("provider-private-error", response.text)
        self.assertEqual(self.confirm(old).status_code, 200)
        self.assertEqual(self.login("traveler@example.com").status_code, 200)

    def test_reauthentication_and_login_are_required(self):
        self.assertEqual(self.client.post(REQUEST, json={"email": "a@example.com", "password": self.password}).status_code, 401)
        self.assertEqual(self.client.post(CONFIRM, json={"token": "x" * 43}).status_code, 401)
        self.assertEqual(self.request_email(password="wrong-password").status_code, 401)
        self.delivery.assert_not_called()

    def test_unconfigured_delivery_does_not_create_token(self):
        with patch.dict(os.environ, {"SMTP_HOST": ""}):
            get_settings.cache_clear()
            self.assertEqual(self.request_email().status_code, 503)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(User, self.user_id).email_verification_token_hash)
        self.delivery.assert_not_called()

    def test_account_cooldown_and_recipient_hourly_limits(self):
        self.issue()
        cooldown = self.request_email()
        self.assertEqual(cooldown.status_code, 429)
        self.assertGreater(int(cooldown.headers["retry-after"]), 0)
        self.assertEqual(self.delivery.call_count, 1)
        self.issue(user_id=self.other_id)
        for index in range(2):
            with Session(self.engine) as db:
                user = User(username=f"extra{index}", password_hash=self.password_hash)
                db.add(user)
                db.commit()
                user_id = user.id
            self.assertEqual(self.request_email(user_id=user_id).status_code, 202 if index == 0 else 429)
        self.assertEqual(self.delivery.call_count, 3)

    def test_unique_verified_binding_prevents_second_claim(self):
        first = self.issue()
        second = self.issue(user_id=self.other_id)
        self.assertEqual(self.confirm(first).status_code, 200)
        self.assertEqual(self.confirm(second, self.other_id).status_code, 409)
        with Session(self.engine) as db:
            self.assertIsNone(db.get(User, self.other_id).email)
            self.assertEqual(db.get(User, self.user_id).email, "traveler@example.com")

    def test_email_change_preserves_old_binding_until_confirmation(self):
        with Session(self.engine) as db:
            user = db.get(User, self.user_id)
            user.email = "old@example.com"
            user.email_verified_at = datetime.now(timezone.utc)
            db.commit()
        token = self.issue(email="new@example.com")
        self.notice.assert_called_once()
        self.assertEqual(self.notice.call_args.args[0], "old@example.com")
        self.assertEqual(self.login("old@example.com").status_code, 200)
        self.assertEqual(self.login("new@example.com").status_code, 401)
        self.assertEqual(self.confirm(token).status_code, 200)
        self.assertEqual(self.login("old@example.com").status_code, 401)
        self.assertEqual(self.login("new@example.com").status_code, 200)

    def test_login_aliases_share_one_account_limit(self):
        self.assertEqual(self.confirm(self.issue()).status_code, 200)
        with patch("app.api.auth.verify_password", return_value=False):
            for index in range(20):
                self.assertEqual(self.login("traveler" if index % 2 else "traveler@example.com").status_code, 401)
            self.assertEqual(self.login("traveler").status_code, 429)
            self.assertEqual(self.login("traveler@example.com").status_code, 429)
        with Session(self.engine) as db:
            rows = db.scalars(select(AuthRateLimit)).all()
            self.assertTrue(all("@" not in row.key and "traveler" not in row.key for row in rows))


class EmailTransportTests(unittest.TestCase):
    def tearDown(self):
        get_settings.cache_clear()

    def test_email_verification_is_disabled_by_default(self):
        with patch.dict(os.environ):
            os.environ.pop("EMAIL_VERIFICATION_ENABLED", None)
            self.assertFalse(Settings(_env_file=None).email_verification_enabled)

    def test_smtp_starttls_and_credentials(self):
        settings = Settings(smtp_host="smtp.example.com", smtp_username="test-user", smtp_password="test-password", smtp_security="starttls")
        with patch("app.services.email.get_settings", return_value=settings), patch("app.services.email.smtplib.SMTP") as factory:
            send_email("recipient@example.com", "Test", "Body")
            smtp = factory.return_value.__enter__.return_value
            smtp.starttls.assert_called_once()
            smtp.login.assert_called_once_with("test-user", "test-password")
            smtp.send_message.assert_called_once()

    def test_smtp_ssl_and_safe_failure(self):
        settings = Settings(smtp_host="smtp.example.com", smtp_port=465, smtp_security="ssl")
        with patch("app.services.email.get_settings", return_value=settings), patch("app.services.email.smtplib.SMTP_SSL") as factory:
            send_email("recipient@example.com", "Test", "Body")
            factory.return_value.__enter__.return_value.starttls.assert_not_called()
            factory.side_effect = OSError("private-server-data")
            with self.assertRaisesRegex(EmailDeliveryError, "^Unable to send email$"):
                send_email("recipient@example.com", "Test", "Body")

    def test_verification_url_uses_trusted_origin_and_fragment(self):
        settings = Settings(frontend_url="https://tripsync.example.com")
        with patch("app.services.email.get_settings", return_value=settings), patch("app.services.email.send_email") as delivery:
            send_verification_email("recipient@example.com", "traveler", "x" * 43)
            text = delivery.call_args.args[2]
            self.assertIn("https://tripsync.example.com/verify-email#" + "x" * 43, text)
            self.assertNotIn("?token=", text)

    def test_rejects_insecure_transport_and_untrusted_link_configuration(self):
        with self.assertRaises(ValueError):
            Settings(smtp_host="smtp.example.com", smtp_security="none")
        for origin in ["http://public.example.com", "https://user:password@example.com", "https://example.com/path", "https://example.com?next=evil", "https://*.example.com"]:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                Settings(frontend_url=origin)


if __name__ == "__main__":
    unittest.main()
