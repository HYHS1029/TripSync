from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_expense_positive"),
        Index("ix_expenses_trip_date", "trip_id", "expense_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    expense_date: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    payer_name: Mapped[str] = mapped_column(String(50))
    split_mode: Mapped[str] = mapped_column(String(10))
    activity_id: Mapped[int | None] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    shares: Mapped[list["ExpenseShare"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="ck_share_nonnegative"),)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    amount_minor: Mapped[int] = mapped_column(BigInteger)


class Settlement(Base):
    __tablename__ = "settlements"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="ck_settlement_positive"),
        CheckConstraint("sender_id <> recipient_id", name="ck_settlement_distinct"),
        Index("ix_settlements_trip", "trip_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    sender_name: Mapped[str] = mapped_column(String(50))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    recipient_name: Mapped[str] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(3))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    settled_on: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
