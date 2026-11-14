# migrate_v2.py — Expand schema for Phase 2 / V2 Billing
from sqlalchemy import inspect, text
from sqlmodel import SQLModel
from skelion_agent.database import get_engine
from skelion_agent import models  # noqa: F401 - register application tables

engine = get_engine()

# 1. Create all newly defined tables using the configured database backend.
SQLModel.metadata.create_all(engine)
print("All tables created / verified.")

# 2. Add compatibility columns to organizations on SQLite and PostgreSQL.
inspector = inspect(engine)
existing_cols = {
    column["name"] for column in inspector.get_columns("organizations")
}

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
        with engine.begin() as connection:
            connection.execute(
                text(f"ALTER TABLE organizations ADD COLUMN {col_name} {col_type}")
            )
        print(f"Added column {col_name} to organizations.")

print("V2 Migration successful!")
