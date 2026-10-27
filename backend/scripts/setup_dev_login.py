"""Provision a regular local test user and server-only Next.js dev credentials.

From backend/: python scripts/setup_dev_login.py
No API authentication bypass, shared default password, or administrator role.
"""

import os
from pathlib import Path
import secrets
import sys

from dotenv import dotenv_values, load_dotenv, set_key
from sqlalchemy import or_, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
ENV_PATH = BACKEND.parent / "frontend" / ".env.development.local"
EMAIL = "developer@example.com"
USERNAME = "TripSync 開發者"


def require_local_database(database_url: str) -> None:
    url = make_url(database_url)
    if (
        url.get_backend_name() != "postgresql"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or any(key in url.query for key in ("host", "hostaddr", "service", "servicefile"))
    ):
        raise ValueError("Setup requires a PostgreSQL database on localhost/127.0.0.1/::1.")


def prepare_account(db: Session, config: dict) -> tuple[str, bool]:
    from app.core.security import hash_password, verify_password
    from app.models.user import User

    user = db.scalar(select(User).where(or_(User.email == EMAIL, User.username == USERNAME)))
    password = config.get("TRIPSYNC_DEV_LOGIN_PASSWORD")
    valid_config = (
        config.get("TRIPSYNC_DEV_LOGIN_EMAIL") == EMAIL
        and isinstance(password, str)
        and 32 <= len(password) <= 128
    )
    if user:
        if (
            user.email != EMAIL or user.username != USERNAME
            or not valid_config or not verify_password(password, user.password_hash)
        ):
            raise ValueError("An existing account conflicts with dev setup; no password was changed.")
        return password, False

    # Reuse a previously saved credential if a prior database commit failed.
    if not valid_config:
        password = secrets.token_urlsafe(48)
    db.add(User(email=EMAIL, username=USERNAME, password_hash=hash_password(password)))
    db.flush()
    return password, True


def main() -> None:
    load_dotenv(BACKEND / ".env")
    require_local_database(os.environ.get("DATABASE_URL", ""))
    from app.database import SessionLocal

    config = dict(dotenv_values(ENV_PATH, interpolate=False)) if ENV_PATH.exists() else {}
    with SessionLocal.begin() as db:
        password, created = prepare_account(db, config)
        # Only development loads this ignored file; other local environment
        # variables are preserved. Never print the generated password.
        for key, value in {
            "TRIPSYNC_DEV_LOGIN_ENABLED": "true",
            "TRIPSYNC_DEV_LOGIN_EMAIL": EMAIL,
            "TRIPSYNC_DEV_LOGIN_PASSWORD": password,
        }.items():
            set_key(ENV_PATH, key, value)

    print("Created local developer account." if created else "Reused local developer account; data preserved.")
    print("Restart frontend with: npm run dev -- --webpack")
    print("Open http://localhost:3000/login and choose the developer login button.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Database exceptions may contain a connection URL or bound credentials.
        print("Dev login setup failed. Check local database/migrations and existing account configuration; no existing password was reset.", file=sys.stderr)
        raise SystemExit(1)
