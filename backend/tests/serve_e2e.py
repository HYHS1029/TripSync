"""Run a disposable API on :8001 for browser checks, without PostgreSQL writes.

From backend/: python tests/serve_e2e.py
Account: traveler@example.com / correct-horse-battery-123
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "tripsync-browser-tests-only-secret-key-123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.user import User


engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


Base.metadata.create_all(engine)
with Session(engine) as db:
    password_hash = hash_password("correct-horse-battery-123")
    db.add_all([
        User(email="traveler@example.com", username="traveler", password_hash=password_hash),
    ])
    db.commit()


def get_test_db():
    with Session(engine) as db:
        yield db


app.dependency_overrides[get_db] = get_test_db


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
