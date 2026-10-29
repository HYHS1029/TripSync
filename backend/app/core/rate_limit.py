"""Atomic, shared fixed-window limits for PostgreSQL and isolated SQLite tests."""
import hashlib
import hmac
import time

from fastapi import HTTPException
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import commit_transaction
from app.models.auth_rate_limit import AuthRateLimit


def limit_requests(db: Session, *rules: tuple[str, str, int, int]) -> None:
    """Rules are (scope, identifier, limit, seconds). Call before business writes."""
    now = int(time.time())
    table = AuthRateLimit.__table__
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    retry_after = 0
    # Bounded indexed cleanup avoids accumulating historical identifiers forever.
    expired = select(table.c.key).where(table.c.expires_at <= now).limit(100)
    db.execute(delete(table).where(table.c.key.in_(expired)))
    for scope, identifier, limit, seconds in rules:
        digest = hmac.new(
            get_settings().jwt_secret_key.get_secret_value().encode(),
            f"{scope}:{identifier}".encode(), hashlib.sha256,
        ).hexdigest()
        expires_at = (now // seconds + 1) * seconds
        stale = table.c.expires_at <= now
        statement = insert(table).values(key=f"{scope}:{digest}", count=1, expires_at=expires_at)
        accepted = db.execute(statement.on_conflict_do_update(
            index_elements=[table.c.key],
            set_={"count": case((stale, 1), else_=table.c.count + 1),
                  "expires_at": case((stale, expires_at), else_=table.c.expires_at)},
            where=stale | (table.c.count < limit),
        ).returning(table.c.key)).scalar_one_or_none()
        if accepted is None:
            retry_after = max(retry_after, expires_at - now)
            break
    commit_transaction(db)
    if retry_after:
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(retry_after)})
