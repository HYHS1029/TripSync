"""Test account provisioning in memory, never against the developer database."""

import os
import unittest

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "tripsync-test-only-key-not-for-real-use-123456789"

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.database import Base
from app.main import app  # noqa: F401 - register all models for foreign keys
from app.models.user import User
from scripts.setup_dev_login import EMAIL, USERNAME, prepare_account, require_local_database


class DevelopmentAccountTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_create_then_reuse_same_account_without_reset(self):
        with Session(self.engine) as db:
            password, created = prepare_account(db, {})
            db.commit()
            user = db.scalar(select(User).where(User.email == EMAIL))
            self.assertTrue(created)
            self.assertGreaterEqual(len(password), 32)
            self.assertNotEqual(password, user.password_hash)
            self.assertTrue(verify_password(password, user.password_hash))
            original = (user.id, user.password_hash, user.created_at)
            repeated, created = prepare_account(db, {
                "TRIPSYNC_DEV_LOGIN_EMAIL": EMAIL,
                "TRIPSYNC_DEV_LOGIN_PASSWORD": password,
            })
            db.commit()
            self.assertFalse(created)
            self.assertEqual(repeated, password)
            self.assertEqual((user.id, user.password_hash, user.created_at), original)

    def test_refuse_to_overwrite_existing_account(self):
        with Session(self.engine) as db:
            original_hash = hash_password("existing-user-password")
            user = User(email=EMAIL, username=USERNAME, password_hash=original_hash)
            db.add(user)
            db.commit()
            for config in [{}, {"TRIPSYNC_DEV_LOGIN_EMAIL": EMAIL, "TRIPSYNC_DEV_LOGIN_PASSWORD": "x" * 64}]:
                with self.assertRaises(ValueError):
                    prepare_account(db, config)
                self.assertEqual(user.password_hash, original_hash)

    def test_refuse_username_collision(self):
        with Session(self.engine) as db:
            db.add(User(email="someone@example.com", username=USERNAME, password_hash=hash_password("existing-password")))
            db.commit()
            with self.assertRaises(ValueError):
                prepare_account(db, {})
            self.assertEqual(len(db.scalars(select(User)).all()), 1)

    def test_setup_refuses_remote_database_and_connection_overrides(self):
        for url in [
            "postgresql+psycopg://user:pass@localhost/db",
            "postgresql+psycopg://user:pass@127.0.0.1/db",
            "postgresql+psycopg://user:pass@[::1]/db",
        ]:
            require_local_database(url)
        for url in [
            "postgresql+psycopg://user:pass@example.com/db",
            "postgresql+psycopg://user:pass@localhost.example.com/db",
            "postgresql+psycopg://user:pass@localhost/db?host=example.com",
            "postgresql+psycopg://user:pass@localhost/db?service=remote",
            "sqlite+pysqlite:///:memory:",
        ]:
            with self.assertRaises(ValueError):
                require_local_database(url)


if __name__ == "__main__":
    unittest.main()
