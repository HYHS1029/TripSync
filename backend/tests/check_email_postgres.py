"""Migration and concurrency checks in a disposable local PostgreSQL schema."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import re
import sys
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Only this disposable test process enables the deferred feature.
os.environ["EMAIL_VERIFICATION_ENABLED"] = "true"

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.rate_limit import limit_requests
from app.core.security import create_access_token, hash_password
from app.database import DATABASE_URL, get_db
from app.main import app
from app.models.user import User
from scripts.setup_dev_login import require_local_database


def parallel(functions):
    gate = Barrier(len(functions))
    def run(function):
        gate.wait(timeout=15)
        return function()
    with ThreadPoolExecutor(max_workers=len(functions)) as pool:
        return list(pool.map(run, functions))


def main():
    require_local_database(DATABASE_URL)
    schema = "tripsync_email_check_" + uuid4().hex
    assert re.fullmatch(r"tripsync_email_check_[a-f0-9]{32}", schema)
    engine = create_engine(DATABASE_URL, hide_parameters=True,
        connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=15000"})
    isolated = engine.execution_options(schema_translate_map={None: schema})
    password_hash = hash_password("postgres-check-only-password")
    original_overrides = app.dependency_overrides.copy()
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            revisions = list(reversed(list(ScriptDirectory.from_config(Config("alembic.ini")).walk_revisions())))
            with Operations.context(MigrationContext.configure(connection)):
                for revision in revisions[:-1]:
                    revision.module.upgrade()
                connection.execute(text(
                    "INSERT INTO users (email, username, password_hash) VALUES (:email, :username, :password)"
                ), {"email": "legacy@example.com", "username": "legacy", "password": password_hash})
                revisions[-1].module.upgrade()
            row = connection.execute(text("SELECT email, pending_email, email_verified_at FROM users WHERE username = 'legacy'")).one()
            assert tuple(row) == (None, "legacy@example.com", None)
        print("PASS: full PostgreSQL migration preserves legacy accounts without trusting unverified email")

        with Session(isolated) as db:
            users = [User(username=f"emailcheck{i}", password_hash=password_hash) for i in range(3)]
            db.add_all(users)
            db.commit()
            ids = [user.id for user in users]
        def database():
            with Session(isolated) as db:
                yield db
        app.dependency_overrides[get_db] = database
        def confirm(user_id, token):
            with TestClient(app) as client:
                return client.post("/auth/email-verification/confirm",
                    headers={"Authorization": f"Bearer {create_access_token(user_id)}"}, json={"token": token})
        def pending(user_id, email, token):
            from app.api.auth import verification_digest
            with Session(isolated) as db:
                user = db.get(User, user_id)
                user.pending_email = email
                user.email_verification_token_hash = verification_digest(token)
                user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
                db.commit()

        token = "a" * 43
        pending(ids[0], "single@example.com", token)
        responses = parallel([lambda: confirm(ids[0], token) for _ in range(2)])
        assert sorted(response.status_code for response in responses) == [200, 400]
        print("PASS: concurrent clicks consume a verification token exactly once")

        for user_id, token in zip(ids[1:], ["b" * 43, "c" * 43]):
            pending(user_id, "shared@example.com", token)
        responses = parallel([lambda: confirm(ids[1], "b" * 43), lambda: confirm(ids[2], "c" * 43)])
        assert sorted(response.status_code for response in responses) == [200, 409]
        print("PASS: concurrent email claims bind the address to exactly one account")

        def limited():
            with Session(isolated) as db:
                try:
                    limit_requests(db, ("concurrency-check", "same-account", 5, 300))
                    return 200
                except HTTPException as error:
                    return error.status_code
        with patch("app.core.rate_limit.time") as clock:
            clock.time.return_value = 1_800_000_010
            responses = parallel([limited for _ in range(12)])
        assert responses.count(200) == 5 and responses.count(429) == 7
        print("PASS: database rate limits remain atomic across concurrent requests")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)
        # The validated, uniquely named test schema is the only deletion target.
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()


if __name__ == "__main__":
    main()
