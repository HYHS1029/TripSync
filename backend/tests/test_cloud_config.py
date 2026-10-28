"""Cloud configuration checks without a network connection or cloud credentials."""

import os
import unittest

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "tripsync-test-only-key-not-for-real-use-123456789"

from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.database_config import database_engine_options, normalize_database_url
from scripts.migrate_neon import require_neon_direct_url


class CloudConfigurationTests(unittest.TestCase):
    def test_neon_url_uses_psycopg3_without_losing_tls_or_escaped_password(self):
        for scheme in ("postgresql", "postgres", "postgresql+psycopg"):
            original = f"{scheme}://test:a%40b%25c@ep-test.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
            normalized = make_url(normalize_database_url(original))
            self.assertEqual(normalized.drivername, "postgresql+psycopg")
            self.assertEqual(normalized.password, "a@b%c")
            self.assertEqual(normalized.query["sslmode"], "require")
            self.assertEqual(normalized.query["channel_binding"], "require")

    def test_sqlite_test_urls_are_preserved(self):
        self.assertEqual(normalize_database_url("sqlite+pysqlite:///:memory:"), "sqlite+pysqlite:///:memory:")

    def test_serverless_functions_do_not_hold_idle_database_connections(self):
        self.assertIs(database_engine_options(True)["poolclass"], NullPool)
        self.assertEqual(database_engine_options(False), {"pool_pre_ping": True})

    def test_percent_encoded_url_can_round_trip_through_alembic_config(self):
        url = normalize_database_url("postgresql://test:a%25b%40c@localhost/db")
        config = Config()
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        self.assertEqual(config.get_main_option("sqlalchemy.url"), url)
        self.assertEqual(make_url(config.get_main_option("sqlalchemy.url")).password, "a%b@c")

    def test_migration_helper_requires_direct_neon_tls_and_refuses_local_database(self):
        valid = "postgresql://user:pass@ep-test.us-east-1.aws.neon.tech/neondb?sslmode=require"
        self.assertTrue(require_neon_direct_url(valid).startswith("postgresql+psycopg://"))
        for url in [
            valid.replace("ep-test.", "ep-test-pooler."),
            valid.replace("?sslmode=require", ""),
            valid.replace("sslmode=require", "sslmode=disable"),
            valid.replace("ep-test.us-east-1.aws.neon.tech", "localhost"),
            valid.replace(".neon.tech", ".neon.tech.example.com"),
            valid + "&host=localhost",
            "sqlite+pysqlite:///:memory:",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                require_neon_direct_url(url)

    def test_cors_allows_explicit_origins_and_rejects_wildcards_or_paths(self):
        settings = Settings(cors_allow_origins=["https://tripsync-test.vercel.app/"])
        self.assertEqual(settings.cors_allow_origins, ["https://tripsync-test.vercel.app"])
        for origin in ["*", "https://*.vercel.app", "https://example.com/path", "https://user:pass@example.com"]:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                Settings(cors_allow_origins=[origin])
