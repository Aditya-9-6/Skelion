# admin_api/factor.py
"""
Passkey and TOTP registration, verification, and step-up enforcement.
Implements append-only behavior for factors in admin_factors table and
integrates with get_current_session dependency.
"""

import hmac
import hashlib
import pyotp
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from .models import AdminSession, AdminFactor, AuditLog, get_engine
from .dependencies import get_current_session, get_db

router = APIRouter(prefix="/factor", tags=["factor"])

class TOTPRegisterRequest(BaseModel):
    secret: Optional[str] = None  # if not provided, generated automatically

class TOTPVerifyRequest(BaseModel):
    code: str

class PasskeyRegisterRequest(BaseModel):
    credential_id: str
    public_key: Optional[str] = None
    name: Optional[str] = "Passkey"

class PasskeyVerifyRequest(BaseModel):
    credential_id: str
    signature: Optional[str] = None

class StepUpVerifyRequest(BaseModel):
    factor_type: str  # "totp" | "passkey"
    code: Optional[str] = None
    credential_id: Optional[str] = None

@router.post("/totp/register")
def register_totp(
    payload: Optional[TOTPRegisterRequest] = None,
    session: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Register a new TOTP factor for the current admin user (append-only)."""
    secret = payload.secret if payload and payload.secret else pyotp.random_base32()
    last4 = secret[-4:]
    
    factor = AdminFactor(
        github_user_id=session.github_user_id,
        type="totp",
        secret_ref=secret,
        last4=last4,
        created_at=datetime.now(timezone.utc),
        revoked_at=None
    )
    db.add(factor)
    
    # Audit log entry
    audit = AuditLog(
        actor_github_id=session.github_user_id,
        action="FACTOR_REGISTER",
        target_type="admin_factor",
        target_id=factor.id,
        after={"type": "totp", "last4": last4},
        reason="TOTP factor registered"
    )
    db.add(audit)
    db.commit()
    db.refresh(factor)
    
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=f"Admin {session.github_user_id}", issuer_name="Skelion Admin")
    
    return {
        "status": "registered",
        "factor_id": factor.id,
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "last4": last4
    }

@router.post("/totp/verify")
def verify_totp(
    payload: TOTPVerifyRequest,
    session: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Verify a TOTP code against registered TOTP factors and grant step-up."""
    stmt = select(AdminFactor).where(
        AdminFactor.github_user_id == session.github_user_id,
        AdminFactor.type == "totp",
        AdminFactor.revoked_at.is_(None)
    )
    factors = db.exec(stmt).all()
    if not factors:
        raise HTTPException(status_code=400, detail="No active TOTP factor registered")
    
    verified = False
    for f in factors:
        if f.secret_ref:
            totp = pyotp.TOTP(f.secret_ref)
            if totp.verify(payload.code, valid_window=1):
                verified = True
                break
    
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    
    # Extend step_up_until by 15 minutes
    step_duration = timedelta(minutes=15)
    now_utc = datetime.now(timezone.utc)
    session.step_up_until = now_utc + step_duration
    db.add(session)
    
    audit = AuditLog(
        actor_github_id=session.github_user_id,
        action="FACTOR_VERIFY",
        target_type="admin_session",
        target_id=session.id,
        reason="TOTP verification successful, step-up granted"
    )
    db.add(audit)
    db.commit()
    
    return {"status": "verified", "step_up_until": session.step_up_until.isoformat()}

@router.post("/passkey/register")
def register_passkey(
    payload: PasskeyRegisterRequest,
    session: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Register a new passkey credential (append-only)."""
    existing = db.exec(select(AdminFactor).where(AdminFactor.credential_id == payload.credential_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Credential ID already registered")
    
    factor = AdminFactor(
        github_user_id=session.github_user_id,
        type="passkey",
        credential_id=payload.credential_id,
        secret_ref=payload.public_key,
        created_at=datetime.now(timezone.utc),
        revoked_at=None
    )
    db.add(factor)
    
    audit = AuditLog(
        actor_github_id=session.github_user_id,
        action="FACTOR_REGISTER",
        target_type="admin_factor",
        target_id=factor.id,
        after={"type": "passkey", "credential_id": payload.credential_id},
        reason="Passkey registered"
    )
    db.add(audit)
    db.commit()
    db.refresh(factor)
    
    return {"status": "registered", "factor_id": factor.id, "credential_id": payload.credential_id}

@router.post("/passkey/verify")
def verify_passkey(
    payload: PasskeyVerifyRequest,
    session: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Verify passkey credential and grant step-up."""
    stmt = select(AdminFactor).where(
        AdminFactor.github_user_id == session.github_user_id,
        AdminFactor.credential_id == payload.credential_id,
        AdminFactor.type == "passkey",
        AdminFactor.revoked_at.is_(None)
    )
    factor = db.exec(stmt).first()
    if not factor:
        raise HTTPException(status_code=400, detail="Passkey credential not found or revoked")
    
    step_duration = timedelta(minutes=15)
    now_utc = datetime.now(timezone.utc)
    session.step_up_until = now_utc + step_duration
    db.add(session)
    
    audit = AuditLog(
        actor_github_id=session.github_user_id,
        action="FACTOR_VERIFY",
        target_type="admin_session",
        target_id=session.id,
        reason="Passkey verification successful, step-up granted"
    )
    db.add(audit)
    db.commit()
    
    return {"status": "verified", "step_up_until": session.step_up_until.isoformat()}

@router.post("/verify")
def verify_factor_generic(
    payload: StepUpVerifyRequest,
    session: AdminSession = Depends(get_current_session),
    db: Session = Depends(get_db)
):
    """Generic factor verification endpoint for step-up."""
    if payload.factor_type == "totp":
        if not payload.code:
            raise HTTPException(status_code=400, detail="Missing TOTP code")
        return verify_totp(TOTPVerifyRequest(code=payload.code), session, db)
    elif payload.factor_type == "passkey":
        if not payload.credential_id:
            raise HTTPException(status_code=400, detail="Missing passkey credential ID")
        return verify_passkey(PasskeyVerifyRequest(credential_id=payload.credential_id, signature=payload.signature), session, db)
    else:
        raise HTTPException(status_code=400, detail="Unsupported factor type")

def require_step_up(session: AdminSession = Depends(get_current_session)) -> AdminSession:
    """Dependency that enforces step-up authentication within the last 15 minutes."""
    if not session.step_up_until:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Step-up authentication required")
    
    now_utc = datetime.now(timezone.utc)
    step_up = session.step_up_until
    if step_up.tzinfo is None:
        step_up = step_up.replace(tzinfo=timezone.utc)
        
    if now_utc > step_up:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Step-up session expired. Re-verification required.")
        
    return session
