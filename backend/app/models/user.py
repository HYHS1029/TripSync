'''
Author: Jacky Hsieh
Date: 2026-10-04 22:01:56
LastEditTime: 2026-10-04 22:20:54
'''
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # Only verified addresses are bound here; pending addresses never reserve an email.
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pending_email: Mapped[str | None] = mapped_column(String(255))
    email_verification_token_hash: Mapped[str | None] = mapped_column(String(64))
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
