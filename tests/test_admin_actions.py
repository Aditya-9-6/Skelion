# tests/test_admin_actions.py
"""
Unit and integration tests for real FastAPI admin action endpoints:
- credit grant/adjust
- tier change
- order reconciliation
- payment refund
- kill-switch toggle

Verifies:
- Idempotency via Idempotency-Key header (returning already_done or idempotent response without re-executing)
- Immutable AuditLog entry creation in the same transaction
- Step-up verification enforcement (403 when not stepped up)
- Clear JSON responses
"""

import os
import hashlib
import uuid
import pyotp
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, SQLModel

from admin_api.main import app, SESSION_COOKIE, sign_session_token
from admin_api.models import AdminSession, AdminFactor, AuditLog, get_engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "admin_actions_test.db"
    os.environ["ADMIN_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    yield

def create_authenticated_session(github_user_id: int = 123456, stepped_up: bool = True):
    engine = get_engine()
    raw_token = f"test_raw_session_token_{github_user_id}"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now_utc = datetime.now(timezone.utc)
    
    step_up = now_utc + timedelta(minutes=15) if stepped_up else None
    
    with Session(engine) as db:
        sess = AdminSession(
            github_user_id=github_user_id,
            session_token_hash=token_hash,
            created_at=now_utc,
            last_seen_at=now_utc,
            expires_at=now_utc + timedelta(hours=1),
            step_up_until=step_up
        )
        db.add(sess)
        db.commit()
    
    signed_cookie = sign_session_token(raw_token)
    client.cookies.set(SESSION_COOKIE, signed_cookie)
    return github_user_id

def test_credit_grant_action():
    github_user_id = create_authenticated_session(123456, stepped_up=True)
    target_user_id = str(uuid.uuid4())
    idem_key = str(uuid.uuid4())
    
    # 1. Successful grant
    resp = client.post(
        "/credits/grant",
        json={"user_id": target_user_id, "amount": 100, "reason": "Bonus credits"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    assert "audit_id" in data
    audit_id = data["audit_id"]
    
    # Check audit log in DB
    engine = get_engine()
    with Session(engine) as db:
        audit = db.exec(select(AuditLog).where(AuditLog.id == audit_id)).first()
        assert audit is not None
        assert audit.action == "grant_credit"
        assert audit.actor_github_id == github_user_id
        assert audit.request_id == idem_key
        assert audit.after["balance"] == 100
        assert audit.target_id == target_user_id

    # 2. Idempotency test (duplicate key)
    resp_idem = client.post(
        "/credits/grant",
        json={"user_id": target_user_id, "amount": 100, "reason": "Bonus credits"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp_idem.status_code == 200, resp_idem.text
    idem_data = resp_idem.json()
    assert idem_data["status"] == "already_done"
    assert idem_data["audit_id"] == audit_id

def test_credit_adjust_action():
    github_user_id = create_authenticated_session(123456, stepped_up=True)
    target_user_id = str(uuid.uuid4())
    idem_key = str(uuid.uuid4())
    
    resp = client.post(
        "/credits/adjust",
        json={"user_id": target_user_id, "delta": -25, "reason": "Correction"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    
    engine = get_engine()
    with Session(engine) as db:
        audit = db.exec(select(AuditLog).where(AuditLog.request_id == idem_key)).first()
        assert audit is not None
        assert audit.action == "adjust_credit"
        assert audit.after["balance"] == -25

def test_tier_change_action():
    github_user_id = create_authenticated_session(123456, stepped_up=True)
    target_user_id = str(uuid.uuid4())
    idem_key = str(uuid.uuid4())
    
    resp = client.post(
        "/tier/change",
        json={"user_id": target_user_id, "new_tier": "enterprise", "reason": "VIP upgrade"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    
    engine = get_engine()
    with Session(engine) as db:
        audit = db.exec(select(AuditLog).where(AuditLog.request_id == idem_key)).first()
        assert audit is not None
        assert audit.action == "change_tier"
        assert audit.after["tier"] == "enterprise"

def test_order_reconcile_action():
    github_user_id = create_authenticated_session(123456, stepped_up=True)
    order_id = str(uuid.uuid4())
    idem_key = str(uuid.uuid4())
    
    resp = client.post(
        "/order/reconcile",
        json={"order_id": order_id, "reason": "Stripe webhook missed"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    
    engine = get_engine()
    with Session(engine) as db:
        audit = db.exec(select(AuditLog).where(AuditLog.request_id == idem_key)).first()
        assert audit is not None
        assert audit.action == "reconcile_order"
        assert audit.target_id == order_id
        assert audit.after["status"] == "reconciled"

def test_payment_refund_action():
    github_user_id = create_authenticated_session(123456, stepped_up=True)
    order_id = str(uuid.uuid4())
    idem_key = str(uuid.uuid4())
    
    resp = client.post(
        "/payment/refund",
        json={"order_id": order_id, "amount": 5000, "reason": "Customer request"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    
    engine = get_engine()
    with Session(engine) as db:
        audit = db.exec(select(AuditLog).where(AuditLog.request_id == idem_key)).first()
        assert audit is not None
        assert audit.action == "refund_payment"
        assert audit.after["status"] == "refunded"
        assert audit.after["amount"] == 5000

def test_kill_switch_toggle_action():
    github_user_id = create_authenticated_session(123456, stepped_up=True)
    idem_key = str(uuid.uuid4())
    
    resp = client.post(
        "/kill-switch/toggle",
        json={"name": "ai_codegen", "enable": True, "reason": "Emergency maintenance completed"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    
    engine = get_engine()
    with Session(engine) as db:
        audit = db.exec(select(AuditLog).where(AuditLog.request_id == idem_key)).first()
        assert audit is not None
        assert audit.action == "toggle_kill_switch"
        assert audit.target_type == "kill_switch"
        assert audit.after["enabled"] is True

def test_missing_step_up_rejected():
    # Session without step-up
    create_authenticated_session(123456, stepped_up=False)
    target_user_id = str(uuid.uuid4())
    idem_key = str(uuid.uuid4())
    
    resp = client.post(
        "/credits/grant",
        json={"user_id": target_user_id, "amount": 100, "reason": "Unauthorized"},
        headers={"Idempotency-Key": idem_key, "CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 403
    assert "Step-up" in resp.json()["detail"]

def test_missing_idempotency_key_rejected():
    create_authenticated_session(123456, stepped_up=True)
    target_user_id = str(uuid.uuid4())
    
    resp = client.post(
        "/credits/grant",
        json={"user_id": target_user_id, "amount": 100, "reason": "No key"},
        headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 400
    assert "Idempotency-Key" in resp.json()["detail"]
