"""Optional verified email bindings and shared authentication limits.

Revision ID: e53a9c2d7f01
Revises: d42f8b1a6e90
"""
from alembic import op
import sqlalchemy as sa

revision = "e53a9c2d7f01"
down_revision = "d42f8b1a6e90"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("pending_email", sa.String(255)))
    op.add_column("users", sa.Column("email_verification_token_hash", sa.String(64)))
    op.add_column("users", sa.Column("email_verification_expires_at", sa.DateTime(timezone=True)))
    # Existing emails were never verified. Preserve them as suggestions, not identities.
    op.execute("UPDATE users SET pending_email = email, email = NULL")
    op.create_table("auth_rate_limits",
        sa.Column("key", sa.String(96), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_auth_rate_limits_expires_at", "auth_rate_limits", ["expires_at"])


def downgrade():
    connection = op.get_bind()
    invalid = connection.execute(sa.text(
        "SELECT COALESCE(email, pending_email) FROM users "
        "GROUP BY COALESCE(email, pending_email) "
        "HAVING COALESCE(email, pending_email) IS NULL OR COUNT(*) > 1 LIMIT 1"
    )).first()
    if invalid:
        raise RuntimeError("Downgrade requires a unique email for every account; no accounts were removed")
    op.execute("UPDATE users SET email = COALESCE(email, pending_email)")
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
    for column in ("email_verification_expires_at", "email_verification_token_hash", "pending_email", "email_verified_at"):
        op.drop_column("users", column)
    op.drop_table("auth_rate_limits")
