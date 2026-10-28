"""Apply schema migrations to a Neon test database using a masked URL prompt.

From backend/: python scripts/migrate_neon.py
The connection URL stays in this process and is never saved or printed.
"""

from getpass import getpass
import os
from pathlib import Path
import sys

from sqlalchemy.engine import make_url

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def require_neon_direct_url(value: str) -> str:
    from app.core.database_config import normalize_database_url

    normalized = normalize_database_url(value.strip())
    url = make_url(normalized)
    if (
        url.drivername != "postgresql+psycopg"
        or not url.host or not url.host.endswith(".neon.tech")
        or "-pooler." in url.host or not url.database
        or url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}
        or any(key in url.query for key in ("host", "hostaddr", "service", "servicefile"))
    ):
        raise ValueError("Use a direct Neon PostgreSQL URL with TLS enabled.")
    return normalized


def main() -> None:
    direct_url = require_neon_direct_url(getpass("Paste Neon DIRECT connection URL (hidden): "))
    # Set both before loading application models. Never accidentally migrate the
    # existing local database or use a different URL inherited from the shell.
    os.environ["DATABASE_URL"] = direct_url
    os.environ["MIGRATION_DATABASE_URL"] = direct_url

    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("prepend_sys_path", str(BACKEND))
    command.upgrade(config, "head")
    print("Neon schema migration complete. No local accounts or trips were copied.")


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt):
        # Driver exceptions may echo a connection URL or SQL parameters.
        print("Migration did not complete. Check the direct Neon URL, TLS, network access and project status; keep the URL private.", file=sys.stderr)
        raise SystemExit(1)
