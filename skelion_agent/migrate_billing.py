# migrations/migrate_billing.py – Ensure new auth & billing columns exist in SQLite

"""A lightweight migration script executed manually (or on startup) to add the
required columns for authentication and billing to the ``organizations`` table.
It uses raw SQL ``ALTER TABLE`` statements which are safe on SQLite – they only
add columns with a default value and do not touch existing data.
"""

import os
import sqlite3
from pathlib import Path

from skelion_agent.config import settings

# Path to the SQLite DB – resolve from env or settings (defaults to helios.db)
DB_URL = os.getenv("DATABASE_URL", os.getenv("DATABASE_URI", settings.DATABASE_URL))
DB_PATH = Path(DB_URL.replace("sqlite:///", ""))

def ensure_columns(db_path: Path):
    if not db_path.is_file():
        return
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        def column_exists(table: str, column: str) -> bool:
            cur.execute(f"PRAGMA table_info({table})")
            return any(row[1] == column for row in cur.fetchall())

        columns = [
            ("plan", "TEXT", "'pilot'"),
            ("credits_total", "INTEGER", "0"),
            ("credits_used", "INTEGER", "0"),
            ("monthly_quota", "INTEGER", "1000"),
            ("quota_remaining", "INTEGER", "1000"),
            ("requests_total", "INTEGER", "0"),
            ("requests_today", "INTEGER", "0"),
            ("last_request_at", "TEXT", "NULL"),
            ("razorpay_customer_id", "TEXT", "NULL"),
            ("email", "TEXT", "NULL"),
            ("password_hash", "TEXT", "NULL"),
            ("github_id", "INTEGER", "NULL"),
            ("github_username", "TEXT", "NULL"),
            ("avatar_url", "TEXT", "NULL"),
            ("addon_autonomous_dev_loop", "INTEGER", "0"),
            ("addon_reverse_proxy_loop", "INTEGER", "0"),
        ]

        for name, col_type, default in columns:
            if not column_exists("organizations", name):
                cur.execute(
                    f"ALTER TABLE organizations ADD COLUMN {name} {col_type} DEFAULT {default}"
                )
                print(f"Added column {name} to organizations in {db_path}")

        if not column_exists("api_keys", "expires_at"):
            cur.execute("ALTER TABLE api_keys ADD COLUMN expires_at TEXT DEFAULT NULL")
            print(f"Added column expires_at to api_keys in {db_path}")

        if column_exists("sso_connections", "client_id") and not column_exists(
            "sso_connections", "client_secret_ref"
        ):
            cur.execute(
                "ALTER TABLE sso_connections ADD COLUMN client_secret_ref TEXT DEFAULT NULL"
            )
            print(f"Added column client_secret_ref to sso_connections in {db_path}")

        if column_exists("audit_log", "created_at") and not column_exists(
            "audit_log", "ts"
        ):
            cur.execute(
                "ALTER TABLE audit_log ADD COLUMN ts TEXT DEFAULT CURRENT_TIMESTAMP"
            )
            print(f"Added column ts to audit_log in {db_path}")

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Migration error for {db_path}: {e}")


ensure_columns(DB_PATH)

