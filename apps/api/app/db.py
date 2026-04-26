from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, inspect, text
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
        connect_args = {"check_same_thread": False, "timeout": 30}
    db_engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)

    if database_url.startswith("sqlite"):
        @event.listens_for(db_engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return db_engine


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
        _ensure_prediction_columns()
    except SQLAlchemyError as exc:
        if active_database_url.startswith("postgresql"):
            _fallback_to_sqlite(exc)
            Base.metadata.create_all(bind=engine)
            _ensure_prediction_columns()
        else:
            raise


def _ensure_prediction_columns() -> None:
    inspector = inspect(engine)
    if "predictions" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("predictions")}
    additions = {
        "predicted_score": "FLOAT",
        "num_chunks": "INTEGER",
        "doc_count": "INTEGER",
    }

    missing = [(name, sql_type) for name, sql_type in additions.items() if name not in existing]
    if not missing:
        return

    with engine.begin() as conn:
        for name, sql_type in missing:
            conn.execute(text(f"ALTER TABLE predictions ADD COLUMN {name} {sql_type}"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
