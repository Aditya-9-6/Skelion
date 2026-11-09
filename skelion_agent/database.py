# skelion_agent/database.py – Database engine and session helpers

import os
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import event

from skelion_agent.config import settings
from skelion_agent.pr_review_models import (
    Installation,
    Repository,
    PullRequest,
    ReviewRun,
    Finding,
    Evidence,
    Fix,
    Feedback,
    Suppression,
    LLMCache,
    Command,
    WebhookDelivery,
    Installations,
    Repositories,
    PullRequests,
    ReviewRuns,
    Findings,
    Evidences,
    Fixes,
    Feedbacks,
    FeedbackRecords,
    Suppressions,
    LLMCaches,
    Commands,
    WebhookDeliveries,
)

# Resolve database URL – fallback to Settings or default SQLite for dev
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("DATABASE_URI", settings.DATABASE_URL),
)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

# Create the SQLAlchemy engine with concurrency safeguards
engine: Engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


def get_engine() -> Engine:
    """Return the SQLAlchemy engine instance."""
    return engine


# Compatibility helper used by existing code/tests – returns the engine (bind) directly
def get_session() -> Engine:
    """Return the engine to be used as the bind for SQLModel Session.

    The test suite expects ``Session(get_session())`` to work, where the
    argument is an engine, not a session instance.
    """
    return engine


# FastAPI dependency that yields a proper Session object
def get_db() -> Generator[Session, None, None]:
    """Yield a ``Session`` bound to the engine for request handling."""
    with Session(engine) as session:
        yield session


def init_db(target_engine: Engine | None = None) -> None:
    """Create all tables defined in the models module and ensure SQLite column consistency."""
    eng = target_engine or engine
    SQLModel.metadata.create_all(eng)
    if eng.dialect.name == "sqlite":
        try:
            from pathlib import Path
            from skelion_agent.migrate_billing import ensure_columns
            db_file = eng.url.database
            if db_file:
                ensure_columns(Path(db_file))
        except Exception:
            pass
