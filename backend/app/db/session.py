"""
SQLAlchemy engine and session management.

Provides:
- engine:          the SQLAlchemy Engine bound to the configured DATABASE_URL
- SessionLocal:    a session factory for request-scoped database sessions
- get_db():        FastAPI dependency that yields a session per request
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a database session, closes after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
