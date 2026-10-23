"""Add private invitations and daily activities.

Revision ID: c91e2a704f36
Revises: b83f7c2d9e10
"""

from alembic import op
import sqlalchemy as sa


revision = "c91e2a704f36"
down_revision = "b83f7c2d9e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trip_invitations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.CheckConstraint("(accepted_at IS NULL AND accepted_by IS NULL) OR "
                           "(accepted_at IS NOT NULL AND accepted_by IS NOT NULL)", name="ck_invitation_acceptance"),
    )
    op.create_index("ix_trip_invitations_trip_created", "trip_invitations", ["trip_id", "created_at"])
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time()),
        sa.Column("end_time", sa.Time()),
        sa.Column("location", sa.String(200)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("end_time IS NULL OR (start_time IS NOT NULL AND end_time >= start_time)", name="ck_activity_time_range"),
    )
    op.create_index("ix_activities_trip_date", "activities", ["trip_id", "activity_date", "start_time"])


def downgrade() -> None:
    op.drop_index("ix_activities_trip_date", table_name="activities")
    op.drop_table("activities")
    op.drop_index("ix_trip_invitations_trip_created", table_name="trip_invitations")
    op.drop_table("trip_invitations")
