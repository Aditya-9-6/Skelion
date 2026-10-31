# migrate_v2.py — Expand schema for Phase 2 / V2 Billing
import sqlite3
from sqlmodel import SQLModel
from skelion_agent.database import get_engine

# 1. Create all newly defined tables
SQLModel.metadata.create_all(get_engine())
print("All tables created / verified.")

# 2. Add columns to organizations
conn = sqlite3.connect("helios.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(organizations)")
existing_cols = [r[1] for r in cursor.fetchall()]

new_cols = [
    ("is_personal", "BOOLEAN DEFAULT 0"),
    ("owner_user_id", "TEXT"),
    ("plan_id", "TEXT DEFAULT 'hosted_community'"),
    ("plan_version", "INTEGER DEFAULT 1"),
    ("billing_status", "TEXT DEFAULT 'active'"),
    ("plan_period_start", "TIMESTAMP"),
    ("plan_period_end", "TIMESTAMP"),
    ("grace_until", "TIMESTAMP"),
    ("cancel_at_period_end", "BOOLEAN DEFAULT 0"),
    ("pilot_until", "TIMESTAMP"),
    ("gstin", "TEXT"),
    ("billing_name", "TEXT"),
    ("billing_address", "TEXT"),
    ("billing_state", "TEXT"),
]

for col_name, col_type in new_cols:
    if col_name not in existing_cols:
        cursor.execute(f"ALTER TABLE organizations ADD COLUMN {col_name} {col_type}")
        print(f"Added column {col_name} to organizations.")

conn.commit()
conn.close()
print("V2 Migration successful!")
