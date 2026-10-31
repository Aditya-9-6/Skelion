# skelion_agent/database.py – Database engine and session helpers

import os
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.engine import Engine

from skelion_agent.config import settings

# Resolve database URL – fallback to Settings or default SQLite for dev
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("DATABASE_URI", settings.DATABASE_URL),
)

# Create the SQLAlchemy engine
engine: Engine = create_engine(DATABASE_URL, echo=False)


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


def init_db() -> None:
    """Create all tables defined in the models module."""

    SQLModel.metadata.create_all(engine)
