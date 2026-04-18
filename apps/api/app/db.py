from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import Base

settings = get_settings()
REPO_ROOT = Path(__file__).resolve().parents[3]
SQLITE_FALLBACK_URL = f"sqlite:///{(REPO_ROOT / 'esg_chatbot.db').as_posix()}"


def _build_engine(database_url: str):
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


active_database_url = settings.database_url
engine = _build_engine(active_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False)
SessionLocal.configure(bind=engine)


def _fallback_to_sqlite(reason: Exception) -> None:
    global engine, active_database_url
    if active_database_url.startswith("sqlite"):
        raise reason

    print(
        "[db] Warning: failed to initialize configured database "
        f"({active_database_url}). Falling back to SQLite ({SQLITE_FALLBACK_URL}).\n"
        f"[db] Original error: {reason}"
    )

    active_database_url = SQLITE_FALLBACK_URL
    engine = _build_engine(active_database_url)
    SessionLocal.configure(bind=engine)


def init_db() -> None:
    global active_database_url

    try:
        if active_database_url.startswith("postgresql"):
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as exc:
        if active_database_url.startswith("postgresql"):
            _fallback_to_sqlite(exc)
            Base.metadata.create_all(bind=engine)
        else:
            raise


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
