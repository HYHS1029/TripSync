"""Portable connection settings shared by the API and migration commands."""

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def normalize_database_url(value: str) -> str:
    url = make_url(value)
    # Neon supplies postgresql://, which SQLAlchemy otherwise resolves to psycopg2.
    # This project uses psycopg 3. Parsing preserves escaped passwords and TLS options.
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    return url.render_as_string(hide_password=False)


def database_engine_options(serverless: bool) -> dict:
    if serverless:
        # Neon provides the shared connection pool. Do not retain connections in
        # idle function instances, which can keep a free database from sleeping.
        return {"poolclass": NullPool}
    return {"pool_pre_ping": True}
