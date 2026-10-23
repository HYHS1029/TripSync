'''
Author: Jacky Hsieh
Date: 2026-09-29 17:30:29
FilePath: \TripSync\backend\app\database.py
'''
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from collections.abc import Generator
from sqlalchemy.orm import Session


# Load environment variables from .env
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")


# Base class for all SQLAlchemy ORM models
class Base(DeclarativeBase):
    pass


# Create the SQLAlchemy database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# Create database session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

def get_db() -> Generator[Session, None, None]:
    """Provide a database session for each request."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def commit_transaction(db: Session) -> None:
    """Commit a completed operation, restoring the session on database failure."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
