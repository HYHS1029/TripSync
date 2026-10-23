"""Run a disposable API on :8001 for browser checks, without PostgreSQL writes.

From backend/: python tests/serve_e2e.py
Accounts: traveler@example.com, other@example.com / correct-horse-battery-123
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "tripsync-browser-tests-only-secret-key-123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

import uvicorn
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.trip import Trip, TripMember
from app.models.activity import Activity
from app.models.invitation import TripInvitation


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, _record):
    connection.execute("PRAGMA foreign_keys=ON")


Base.metadata.create_all(engine)
with Session(engine) as db:
    password_hash = hash_password("correct-horse-battery-123")
    db.add_all([
        User(email="traveler@example.com", username="traveler", password_hash=password_hash),
        User(email="other@example.com", username="other", password_hash=password_hash),
    ])
    db.commit()


def get_test_db():
    with Session(engine) as db:
        yield db


app.dependency_overrides[get_db] = get_test_db


@app.get("/__test__/status", include_in_schema=False)
def test_status():
    with Session(engine) as db:
        return {
            "fixture": "tripsync-memory-only",
            "trips": db.scalar(select(func.count()).select_from(Trip)),
            "memberships": db.scalar(select(func.count()).select_from(TripMember)),
            "activities": db.scalar(select(func.count()).select_from(Activity)),
            "invitations": db.scalar(select(func.count()).select_from(TripInvitation)),
        }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
