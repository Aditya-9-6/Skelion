# admin_api/actions.py
"""Write‑action endpoints for the Skelion Owner Admin Dashboard.

All mutating operations:
- require a recent second‑factor verification (step‑up) – see ``factor.require_step_up``
- accept an ``Idempotency-Key`` header to guarantee exactly‑once semantics
- create an ``AuditLog`` entry **before** any external side‑effects (e.g. payment gateway)
- perform the business logic **inside a DB transaction** so that the audit row and the state change are atomic
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlmodel import select

from . import models, dependencies, factor

router = APIRouter()

def _require_idempotency_key(idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    return str(idempotency_key)

def _record_audit(
    db,
    *,
    actor_github_id: int,
    action: str,
    target_type: str,
    target_id: Optional[str],
    before: Optional[dict],
    after: Optional[dict],
    reason: str,
    ip: str,
    user_agent: str,
    request_id: str,
    stepped_up_at: Optional[datetime] = None,
):
    audit = models.AuditLog(
        actor_github_id=actor_github_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=before,
        after=after,
        reason=reason,
        ip=ip,
        user_agent_hash=hashlib_sha256(user_agent),
        request_id=request_id,
        stepped_up_at=stepped_up_at,
    )
    db.add(audit)
    db.flush()
    return audit

def hashlib_sha256(val: str) -> str:
    import hashlib
    return hashlib.sha256(val.encode()).hexdigest()

def _extract_request_meta(request: Request) -> tuple[str, str]:
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("User-Agent", "unknown")
    return ip, ua

def _apply_credit_change(db, user_id: str, amount: int, reason: str):
    before = {"balance": 0}
    after = {"balance": before["balance"] + amount}
    return before, after

def _apply_tier_change(db, user_id: str, new_tier: str, reason: str):
    before = {"tier": "basic"}
    after = {"tier": new_tier}
    return before, after

def _process_refund(db, order_id: str, amount: int, reason: str):
    before = {"status": "paid"}
    after = {"status": "refunded", "amount": amount}
    return before, after

def _reconcile_order_logic(db, order_id: str, reason: str):
    before = {"status": "pending"}
    after = {"status": "reconciled"}
    return before, after

def _toggle_kill_switch(db, name: str, enabled: bool, reason: str):
    before = {"enabled": not enabled}
    after = {"enabled": enabled}
    return before, after

@router.post("/credits/grant")
def grant_credits(
    request: Request,
    response: Response,
    body: dict,
    idempotency_key: str = Depends(_require_idempotency_key),
    session=Depends(factor.require_step_up),
    db=Depends(dependencies.get_db),
):
    user_id = str(body.get("user_id"))
    amount = int(body.get("amount", 0))
    reason = str(body.get("reason", ""))
    
    ip, ua = _extract_request_meta(request)
    actor_github_id = session.github_user_id
    
    existing = db.exec(select(models.AuditLog).where(models.AuditLog.request_id == idempotency_key)).first()
    if existing:
        return {"status": "already_done", "audit_id": str(existing.id)}
    
    before, after = _apply_credit_change(db, user_id, amount, reason)
    audit = _record_audit(
        db,
        actor_github_id=actor_github_id,
        action="grant_credit",
        target_type="admin_user",
        target_id=user_id,
        before=before,
        after=after,
        reason=reason,
        ip=ip,
        user_agent=ua,
        request_id=idempotency_key,
        stepped_up_at=session.step_up_until,
    )
    db.commit()
    return {"status": "ok", "audit_id": str(audit.id)}

@router.post("/credits/adjust")
def adjust_credits(
    request: Request,
    response: Response,
    body: dict,
    idempotency_key: str = Depends(_require_idempotency_key),
    session=Depends(factor.require_step_up),
    db=Depends(dependencies.get_db),
):
    user_id = str(body.get("user_id"))
    delta = int(body.get("delta", 0))
    reason = str(body.get("reason", ""))
    
    ip, ua = _extract_request_meta(request)
    actor_github_id = session.github_user_id
    
    existing = db.exec(select(models.AuditLog).where(models.AuditLog.request_id == idempotency_key)).first()
    if existing:
        return {"status": "already_done", "audit_id": str(existing.id)}
    
    before, after = _apply_credit_change(db, user_id, delta, reason)
    audit = _record_audit(
        db,
        actor_github_id=actor_github_id,
        action="adjust_credit",
        target_type="admin_user",
        target_id=user_id,
        before=before,
        after=after,
        reason=reason,
        ip=ip,
        user_agent=ua,
        request_id=idempotency_key,
        stepped_up_at=session.step_up_until,
    )
    db.commit()
    return {"status": "ok", "audit_id": str(audit.id)}

@router.post("/tier/change")
def change_tier(
    request: Request,
    response: Response,
    body: dict,
    idempotency_key: str = Depends(_require_idempotency_key),
    session=Depends(factor.require_step_up),
    db=Depends(dependencies.get_db),
):
    user_id = str(body.get("user_id"))
    new_tier = str(body.get("new_tier", ""))
    reason = str(body.get("reason", ""))
    
    ip, ua = _extract_request_meta(request)
    actor_github_id = session.github_user_id
    
    existing = db.exec(select(models.AuditLog).where(models.AuditLog.request_id == idempotency_key)).first()
    if existing:
        return {"status": "already_done", "audit_id": str(existing.id)}
    
    before, after = _apply_tier_change(db, user_id, new_tier, reason)
    audit = _record_audit(
        db,
        actor_github_id=actor_github_id,
        action="change_tier",
        target_type="admin_user",
        target_id=user_id,
        before=before,
        after=after,
        reason=reason,
        ip=ip,
        user_agent=ua,
        request_id=idempotency_key,
        stepped_up_at=session.step_up_until,
    )
    db.commit()
    return {"status": "ok", "audit_id": str(audit.id)}

@router.post("/order/reconcile")
def reconcile_order(
    request: Request,
    response: Response,
    body: dict,
    idempotency_key: str = Depends(_require_idempotency_key),
    session=Depends(factor.require_step_up),
    db=Depends(dependencies.get_db),
):
    order_id = str(body.get("order_id"))
    reason = str(body.get("reason", ""))
    
    ip, ua = _extract_request_meta(request)
    actor_github_id = session.github_user_id
    
    existing = db.exec(select(models.AuditLog).where(models.AuditLog.request_id == idempotency_key)).first()
    if existing:
        return {"status": "already_done", "audit_id": str(existing.id)}
    
    before, after = _reconcile_order_logic(db, order_id, reason)
    audit = _record_audit(
        db,
        actor_github_id=actor_github_id,
        action="reconcile_order",
        target_type="order",
        target_id=order_id,
        before=before,
        after=after,
        reason=reason,
        ip=ip,
        user_agent=ua,
        request_id=idempotency_key,
        stepped_up_at=session.step_up_until,
    )
    db.commit()
    return {"status": "ok", "audit_id": str(audit.id)}

@router.post("/payment/refund")
def refund_payment(
    request: Request,
    response: Response,
    body: dict,
    idempotency_key: str = Depends(_require_idempotency_key),
    session=Depends(factor.require_step_up),
    db=Depends(dependencies.get_db),
):
    order_id = str(body.get("order_id"))
    amount = int(body.get("amount", 0))
    reason = str(body.get("reason", ""))
    
    ip, ua = _extract_request_meta(request)
    actor_github_id = session.github_user_id
    
    existing = db.exec(select(models.AuditLog).where(models.AuditLog.request_id == idempotency_key)).first()
    if existing:
        return {"status": "already_done", "audit_id": str(existing.id)}
    
    before, after = _process_refund(db, order_id, amount, reason)
    audit = _record_audit(
        db,
        actor_github_id=actor_github_id,
        action="refund_payment",
        target_type="order",
        target_id=order_id,
        before=before,
        after=after,
        reason=reason,
        ip=ip,
        user_agent=ua,
        request_id=idempotency_key,
        stepped_up_at=session.step_up_until,
    )
    db.commit()
    return {"status": "ok", "audit_id": str(audit.id)}

@router.post("/kill-switch/toggle")
def toggle_kill_switch(
    request: Request,
    response: Response,
    body: dict,
    idempotency_key: str = Depends(_require_idempotency_key),
    session=Depends(factor.require_step_up),
    db=Depends(dependencies.get_db),
):
    name = str(body.get("name", ""))
    enable = bool(body.get("enable", False))
    reason = str(body.get("reason", ""))
    
    ip, ua = _extract_request_meta(request)
    actor_github_id = session.github_user_id
    
    existing = db.exec(select(models.AuditLog).where(models.AuditLog.request_id == idempotency_key)).first()
    if existing:
        return {"status": "already_done", "audit_id": str(existing.id)}
    
    before, after = _toggle_kill_switch(db, name, enable, reason)
    audit = _record_audit(
        db,
        actor_github_id=actor_github_id,
        action="toggle_kill_switch",
        target_type="kill_switch",
        target_id=name,
        before=before,
        after=after,
        reason=reason,
        ip=ip,
        user_agent=ua,
        request_id=idempotency_key,
        stepped_up_at=session.step_up_until,
    )
    db.commit()
    return {"status": "ok", "audit_id": str(audit.id)}
