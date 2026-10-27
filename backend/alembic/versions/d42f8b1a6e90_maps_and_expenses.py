"""Add map references, itinerary ordering and the trip ledger.

Revision ID: d42f8b1a6e90
Revises: c91e2a704f36
"""
from alembic import op
import sqlalchemy as sa

revision = "d42f8b1a6e90"
down_revision = "c91e2a704f36"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("trips", sa.Column("timezone", sa.String(64), server_default="Asia/Taipei", nullable=False))
    op.add_column("trips", sa.Column("currency", sa.String(3), server_default="TWD", nullable=False))
    op.add_column("activities", sa.Column("place_id", sa.String(255)))
    op.add_column("activities", sa.Column("category", sa.String(16), server_default="sight", nullable=False))
    op.add_column("activities", sa.Column("position", sa.Integer()))
    op.add_column("activities", sa.Column("stay_until", sa.Date()))
    op.create_check_constraint("ck_activity_position", "activities", "position IS NULL OR position >= 0")
    op.create_check_constraint("ck_activity_stay_range", "activities",
                               "stay_until IS NULL OR (category = 'lodging' AND stay_until >= activity_date)")
    op.create_table("expenses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payer_name", sa.String(50), nullable=False),
        sa.Column("split_mode", sa.String(10), nullable=False),
        sa.Column("activity_id", sa.Integer(), sa.ForeignKey("activities.id", ondelete="SET NULL")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_expense_positive"))
    op.create_index("ix_expenses_trip_date", "expenses", ["trip_id", "expense_date"])
    op.create_table("expense_shares",
        sa.Column("expense_id", sa.Integer(), sa.ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("amount_minor >= 0", name="ck_share_nonnegative"))
    op.create_table("settlements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trip_id", sa.Integer(), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sender_name", sa.String(50), nullable=False),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recipient_name", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("settled_on", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_settlement_positive"),
        sa.CheckConstraint("sender_id <> recipient_id", name="ck_settlement_distinct"))
    op.create_index("ix_settlements_trip", "settlements", ["trip_id"])


def downgrade():
    op.drop_table("settlements")
    op.drop_table("expense_shares")
    op.drop_table("expenses")
    op.drop_constraint("ck_activity_stay_range", "activities", type_="check")
    op.drop_constraint("ck_activity_position", "activities", type_="check")
    for name in ("stay_until", "position", "category", "place_id"):
        op.drop_column("activities", name)
    op.drop_column("trips", "currency")
    op.drop_column("trips", "timezone")
