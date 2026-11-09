import os
import pytest
from sqlmodel import Session as _SQLModelSession, SQLModel, create_engine
from sqlalchemy import text
from sqlalchemy.engine import Engine

# Use SQLite for testing to avoid external Postgres dependency
TEST_DB_URL = "sqlite:///test_db.sqlite"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["DATABASE_URI"] = TEST_DB_URL
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_webhook_secret_placeholder"

# SQLite TRUNCATE / Session.exec shim moved out of skelion_agent/db.py into tests/conftest.py
_original_exec = _SQLModelSession.exec

def _patched_exec(self, statement, *args, **kwargs):
    if isinstance(statement, str):
        stmt_str = statement.strip()
        # Special handling for TRUNCATE when running on SQLite dialects
        if stmt_str.upper().startswith("TRUNCATE"):
            dialect_name = ""
            bind = getattr(self, "bind", None)
            if bind and hasattr(bind, "dialect"):
                dialect_name = bind.dialect.name
            else:
                try:
                    dialect_name = self.get_bind().dialect.name
                except Exception:
                    pass
            if dialect_name == "sqlite":
                parts = stmt_str.split()
                try:
                    tbl_index = parts.index("TABLE") + 1
                    table_name = parts[tbl_index]
                except Exception:
                    raise ValueError(f"Unable to parse TRUNCATE statement: {statement}")
                self.execute(text(f"DELETE FROM {table_name}"))
                if "RESTART" in stmt_str.upper():
                    try:
                        self.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'"))
                    except Exception:
                        pass
                return self
        # Generic raw SQL string wrapped in text()
        statement = text(statement)
    return _original_exec(self, statement, *args, **kwargs)

_SQLModelSession.exec = _patched_exec

# Ensure skelion_agent.database and skelion_agent.config use the test engine
import skelion_agent.database as db_module
import skelion_agent.config as config_module
import skelion_agent.models  # ensure models are registered
import skelion_agent.razorpay_service as rzp_svc

connect_args = {"check_same_thread": False} if "sqlite" in TEST_DB_URL else {}
pg_engine = create_engine(TEST_DB_URL, echo=False, pool_pre_ping=True, connect_args=connect_args)
db_module.engine = pg_engine
db_module.DATABASE_URL = TEST_DB_URL
config_module.engine = pg_engine
config_module.settings.DATABASE_URL = TEST_DB_URL
config_module.settings.DATABASE_URI = TEST_DB_URL
config_module.settings.RAZORPAY_KEY_SECRET = "rzp_webhook_secret_placeholder"
rzp_svc.RAZORPAY_WEBHOOK_SECRET = "rzp_webhook_secret_placeholder"

@pytest.fixture(scope="session", autouse=True)
def setup_postgres_schema():
    """Ensure all SQLModel tables are initialized for testing."""
    import skelion_agent.models  # ensure models are registered
    from pathlib import Path
    from skelion_agent.migrate_billing import ensure_columns
    SQLModel.metadata.create_all(pg_engine)
    ensure_columns(Path("test_db.sqlite"))
    yield


