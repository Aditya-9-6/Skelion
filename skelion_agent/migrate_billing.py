# migrations/migrate_billing.py – Ensure new auth & billing columns exist in SQLite

"""A lightweight migration script executed manually (or on startup) to add the
required columns for authentication and billing to the ``organizations`` table.
It uses raw SQL ``ALTER TABLE`` statements which are safe on SQLite – they only
add columns with a default value and do not touch existing data.
"""

import os
import sqlite3
from pathlib import Path

# Path to the SQLite DB – same as ``DATABASE_URI`` environment variable (sqlite:///./skelion.db)
DB_PATH = Path(os.getenv("DATABASE_URI", "sqlite:///./skelion.db").replace("sqlite:///", ""))

if not DB_PATH.is_file():
    # If the file doesn't exist yet, it will be initialized by SQLModel init_db
    pass
else:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    def column_exists(table: str, column: str) -> bool:
        cur.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cur.fetchall())

    # Define columns to add: (name, type, default)
    columns = [
        ("plan", "TEXT", "'pilot'"),
        ("credits_total", "INTEGER", "0"),
        ("credits_used", "INTEGER", "0"),
        ("razorpay_customer_id", "TEXT", "NULL"),
        ("email", "TEXT", "NULL"),
        ("password_hash", "TEXT", "NULL"),
        ("github_id", "INTEGER", "NULL"),
        ("github_username", "TEXT", "NULL"),
        ("avatar_url", "TEXT", "NULL"),
    ]

    for name, col_type, default in columns:
        if not column_exists("organizations", name):
            cur.execute(f"ALTER TABLE organizations ADD COLUMN {name} {col_type} DEFAULT {default}")
            print(f"Added column {name} to organizations")

    conn.commit()
    conn.close()
