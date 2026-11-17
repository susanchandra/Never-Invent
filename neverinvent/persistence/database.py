"""
persistence/database.py — SQLite database setup with SQLAlchemy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DB_DIR = Path("data")
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "neverinvent.db"


class Base(DeclarativeBase):
    pass


_engine = None
_SessionFactory = None


def get_engine(db_url: str = ""):
    global _engine, _SessionFactory
    if not db_url:
        DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{DEFAULT_DB_PATH}"

    if _engine is None or str(_engine.url) != db_url:
        _engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        )
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def init_db(db_url: str = "") -> None:
    """Initialize database tables."""
    engine = get_engine(db_url)
    Base.metadata.create_all(bind=engine)


def get_db_session(db_url: str = "") -> Generator[Session, None, None]:
    """Yield a database session."""
    get_engine(db_url)
    assert _SessionFactory is not None
    session = _SessionFactory()
    try:
        yield session
    finally:
        session.close()
