"""SQLModel definitions for the admin‑only API (Phase A0).
Only a minimal subset is required for the foundation – session handling,
second‑factor records, and the audit log (append‑only).
"""

import os
from datetime import datetime, timezone
from typing import Optional, List

from sqlmodel import SQLModel, Field, create_engine, Session, Column, JSON
from sqlalchemy.engine import Engine

# Re‑use the same database URL as the main app but with a dedicated role.
# The environment variable ADMIN_DATABASE_URL should point to the admin DB.
DATABASE_URL = os.getenv("ADMIN_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///admin.db"))

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

def get_engine() -> Engine:
    """Return the SQLAlchemy engine used by the admin services."""
    db_url = os.getenv("ADMIN_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///admin.db"))
    c_args = {"check_same_thread": False, "timeout": 30} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, echo=False, connect_args=c_args)

engine: Engine = get_engine()


class AdminSession(SQLModel, table=True):
    __tablename__ = "admin_sessions"
    __table_args__ = {"extend_existing": True}
    id: str = Field(default_factory=lambda: str(os.urandom(16).hex()), primary_key=True)
    github_user_id: int = Field(index=True)
    session_token_hash: str = Field(index=True)  # hashed token stored in cookie
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: Optional[datetime] = Field(default=None)
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip: Optional[str] = Field(default=None)
    user_agent_hash: Optional[str] = Field(default=None)
    revoked_at: Optional[datetime] = Field(default=None)
    step_up_until: Optional[datetime] = Field(default=None)


class AdminFactor(SQLModel, table=True):
    __tablename__ = "admin_factors"
    __table_args__ = {"extend_existing": True}
    id: str = Field(default_factory=lambda: str(os.urandom(16).hex()), primary_key=True)
    github_user_id: int = Field(foreign_key="admin_sessions.github_user_id", index=True)
    type: str = Field(index=True)  # "passkey" | "totp" | "recovery"
    credential_id: Optional[str] = Field(default=None, index=True)
    secret_ref: Optional[str] = Field(default=None)
    last4: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: Optional[datetime] = Field(default=None)


class AdminUser(SQLModel, table=True):
    __tablename__ = "admin_users"
    __table_args__ = {"extend_existing": True}
    id: str = Field(default_factory=lambda: str(os.urandom(16).hex()), primary_key=True)
    github_user_id: int = Field(index=True, unique=True)
    login_snapshot: str = Field(nullable=False)
    role: str = Field(index=True)  # e.g., "admin", "superadmin"
    status: str = Field(index=True)  # e.g., "active", "disabled"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = {"extend_existing": True}
    id: str = Field(default_factory=lambda: str(os.urandom(16).hex()), primary_key=True)
    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_github_id: int = Field(index=True)
    action: str = Field(nullable=False)
    target_type: str = Field(index=True)
    target_id: Optional[str] = Field(default=None)
    before: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    after: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    reason: Optional[str] = Field(default=None)
    ip: Optional[str] = Field(default=None)
    user_agent_hash: Optional[str] = Field(default=None)
    request_id: Optional[str] = Field(default=None)
    stepped_up_at: Optional[datetime] = Field(default=None)
    prev_hash: Optional[str] = Field(default=None)
    row_hash: Optional[str] = Field(default=None)
