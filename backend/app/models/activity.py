from datetime import date, datetime, time

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(
            "end_time IS NULL OR (start_time IS NOT NULL AND end_time >= start_time)",
            name="ck_activity_time_range",
        ),
        Index("ix_activities_trip_date", "trip_id", "activity_date", "start_time"),
        CheckConstraint("position IS NULL OR position >= 0", name="ck_activity_position"),
        CheckConstraint("stay_until IS NULL OR (category = 'lodging' AND stay_until >= activity_date)",
                        name="ck_activity_stay_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    activity_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    location: Mapped[str | None] = mapped_column(String(200))
    place_id: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(16), default="sight", server_default="sight")
    position: Mapped[int | None] = mapped_column(Integer)
    stay_until: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
