# tests/test_factor.py
"""
Unit tests for passkey and TOTP registration, verification, and step-up enforcement.
Verifies append-only behavior for admin_factors and integration with session handling.
"""

import os
import hashlib
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
    db_path = tmp_path / "admin_factor_test.db"
    os.environ["ADMIN_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    from admin_api.models import get_engine
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    yield

def create_authenticated_session(github_user_id: int = 123456, stepped_up: bool = False):
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

def test_totp_registration_and_verification():
    github_user_id = create_authenticated_session(123456)
    
    # 1. Register TOTP
    resp = client.post("/factor/totp/register", headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "registered"
    assert "secret" in data
    assert "factor_id" in data
    secret = data["secret"]
    
    # Verify factor stored in DB and append-only check
    engine = get_engine()
    with Session(engine) as db:
        factors = db.exec(select(AdminFactor).where(AdminFactor.github_user_id == github_user_id)).all()
        assert len(factors) == 1
        assert factors[0].type == "totp"
        assert factors[0].secret_ref == secret
    
    # Register second TOTP factor (append-only behavior)
    resp2 = client.post("/factor/totp/register", json={"secret": pyotp.random_base32()}, headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"})
    assert resp2.status_code == 200, resp2.text
    
    with Session(engine) as db:
        factors = db.exec(select(AdminFactor).where(AdminFactor.github_user_id == github_user_id)).all()
        assert len(factors) == 2  # Append-only: both records exist
    
    # 2. Verify TOTP with valid code
    totp = pyotp.TOTP(secret)
    code = totp.now()
    
    resp_verify = client.post("/factor/totp/verify", json={"code": code}, headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"})
    assert resp_verify.status_code == 200, resp_verify.text
    verify_data = resp_verify.json()
    assert verify_data["status"] == "verified"
    assert "step_up_until" in verify_data

def test_passkey_registration_and_verification():
    github_user_id = create_authenticated_session(789012)
    
    cred_id = "cred_abc123"
    pub_key = "pubkey_xyz789"
    
    # 1. Register Passkey
    resp = client.post(
        "/factor/passkey/register",
        json={"credential_id": cred_id, "public_key": pub_key, "name": "YubiKey"},
        headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "registered"
    assert data["credential_id"] == cred_id
    
    # Duplicate credential registration should fail
    resp_dup = client.post(
        "/factor/passkey/register",
        json={"credential_id": cred_id, "public_key": pub_key},
        headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp_dup.status_code == 400
    
    # 2. Verify Passkey
    resp_verify = client.post(
        "/factor/passkey/verify",
        json={"credential_id": cred_id},
        headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"}
    )
    assert resp_verify.status_code == 200, resp_verify.text
    assert resp_verify.json()["status"] == "verified"

def test_step_up_enforcement_dependency():
    from fastapi import Depends
    from admin_api.factor import require_step_up
    
    github_user_id = create_authenticated_session(555666, stepped_up=False)
    
    # Test protected endpoint requiring step-up
    @app.get("/test-step-up-protected")
    def protected_route(session: AdminSession = Depends(require_step_up)):
        return {"status": "success", "user": session.github_user_id}
    
    # Without step-up -> 403
    resp = client.get("/test-step-up-protected", headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"})
    assert resp.status_code == 403, resp.text
    assert "Step-up authentication required" in resp.json()["detail"]
    
    # Perform TOTP registration and verification to get step-up
    totp_reg = client.post("/factor/totp/register", headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"}).json()
    secret = totp_reg["secret"]
    code = pyotp.TOTP(secret).now()
    
    resp_verify = client.post("/factor/totp/verify", json={"code": code}, headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"})
    assert resp_verify.status_code == 200, resp_verify.text
    
    # Now with step-up -> 200
    resp_success = client.get("/test-step-up-protected", headers={"CF-Access-Authenticated-User-Email": "admin@skelion.dev"})
    assert resp_success.status_code == 200, resp_success.text
    assert resp_success.json()["status"] == "success"
