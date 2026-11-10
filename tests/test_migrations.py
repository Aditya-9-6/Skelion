import os
import sqlite3
import subprocess
from pathlib import Path

import pytest
from sqlmodel import SQLModel, Session, select

# Ensure alembic is in PATH

@pytest.fixture(scope="function")
def admin_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("admin_db") / "admin_test.db"
    os.environ["ADMIN_DATABASE_URL"] = f"sqlite:///{db_path}"
    # Run alembic upgrade
    result = subprocess.run(["alembic", "upgrade", "head"], cwd=Path.cwd(), capture_output=True, text=True)
    assert result.returncode == 0, f"Alembic upgrade failed: {result.stderr}"
    yield db_path
    # Cleanup
    del os.environ["ADMIN_DATABASE_URL"]
    if db_path.is_file():
        db_path.unlink()

def test_tables_created(admin_db):
    # Connect to SQLite directly
    conn = sqlite3.connect(admin_db)
    cursor = conn.cursor()
    # Check admin_users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users';")
    assert cursor.fetchone() is not None
    # Check admin_sessions table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_sessions';")
    assert cursor.fetchone() is not None
    # Check admin_factors table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_factors';")
    assert cursor.fetchone() is not None
    # Check audit_log table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log';")
    assert cursor.fetchone() is not None
    conn.close()

def test_append_only_triggers(admin_db):
    # Attempt to update admin_sessions should fail due to trigger
    conn = sqlite3.connect(admin_db)
    try:
        cursor = conn.cursor()
        # Insert a row first
        cursor.execute("INSERT INTO admin_sessions (id, github_user_id, session_token_hash, created_at, expires_at) VALUES (?,?,?,datetime('now'),datetime('now'))", ("testid", 1, "hash"))
        conn.commit()
        # Try update
        with pytest.raises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            cursor.execute("UPDATE admin_sessions SET github_user_id=2 WHERE id='testid'")
            conn.commit()
        # Try delete
        with pytest.raises((sqlite3.OperationalError, sqlite3.IntegrityError)):
            cursor.execute("DELETE FROM admin_sessions WHERE id='testid'")
            conn.commit()
    finally:
        conn.close()
