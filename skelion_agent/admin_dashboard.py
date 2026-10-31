# skelion_agent/admin_dashboard.py – Special Master Control Dashboard & Admin APIs

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session, select, desc

from skelion_agent.database import get_db
from skelion_agent.models import (
    Organization,
    TransactionRecord,
    Incident,
    License,
    utc_now,
)
from skelion_agent.plan_config import PLAN_DEFINITIONS
from skelion_agent.limits_service import get_token_status
from license.issuer import issue_license

router = APIRouter(tags=["Admin Master Dashboard"])


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class CreateCustomerRequest(BaseModel):
    name: str
    email: Optional[str] = None
    plan: str = "pilot"
    credits_total: Optional[int] = None
    autofix_tokens_total: int = 50000


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    billing_email: Optional[str] = None
    plan: Optional[str] = None
    stripe_subscription_status: Optional[str] = None
    credits_total: Optional[int] = None
    autofix_tokens_total: Optional[int] = None
    limit_enforcement_enabled: Optional[bool] = None


class RefillTokensRequest(BaseModel):
    token_type: str  # "coding" or "autofix"
    amount_tokens: int
    reason: Optional[str] = "Admin manual grant"


# ---------------------------------------------------------------------------
# Admin API Endpoints
# ---------------------------------------------------------------------------


@router.get("/v1/admin/stats")
def get_admin_stats(db: Session = Depends(get_db)):
    """Return high-level KPIs across customers, token pools, orders and incidents."""
    total_customers = len(db.exec(select(Organization)).all())

    orgs = db.exec(select(Organization)).all()
    plans_count = {}
    total_coding_allocated = 0
    total_coding_used = 0
    total_autofix_allocated = 0
    total_autofix_used = 0

    for org in orgs:
        plans_count[org.plan] = plans_count.get(org.plan, 0) + 1
        total_coding_allocated += org.credits_total + org.purchased_tokens
        total_coding_used += org.credits_used + org.purchased_tokens_used
        total_autofix_allocated += org.autofix_tokens_total
        total_autofix_used += org.autofix_tokens_used

    total_incidents = len(db.exec(select(Incident)).all())

    # Revenue & Transactions
    txs = db.exec(select(TransactionRecord)).all()
    total_revenue_inr = sum(t.amount_inr for t in txs if t.status == "paid")
    total_orders = len(txs)

    return {
        "total_customers": total_customers,
        "plans_breakdown": plans_count,
        "tokens": {
            "coding_allocated": total_coding_allocated,
            "coding_used": total_coding_used,
            "coding_remaining": max(0, total_coding_allocated - total_coding_used),
            "autofix_allocated": total_autofix_allocated,
            "autofix_used": total_autofix_used,
            "autofix_remaining": max(0, total_autofix_allocated - total_autofix_used),
        },
        "incidents_resolved": total_incidents,
        "total_revenue_inr": round(total_revenue_inr, 2),
        "total_orders": total_orders,
    }


@router.get("/v1/admin/customers")
def list_admin_customers(db: Session = Depends(get_db)):
    """Return comprehensive customer roster with plan quotas, limits, and usage."""
    orgs = db.exec(select(Organization).order_by(Organization.created_at.desc())).all()
    results = []

    for org in orgs:
        limits = get_token_status(org)
        results.append(
            {
                "id": org.id,
                "name": org.name,
                "email": org.email or org.billing_email or "No email",
                "github_username": org.github_username,
                "avatar_url": org.avatar_url,
                "token": org.token,
                "plan": org.plan,
                "subscription_status": org.stripe_subscription_status,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "coding_tokens": {
                    "monthly_total": org.credits_total,
                    "monthly_used": org.credits_used,
                    "monthly_remaining": max(0, org.credits_total - org.credits_used),
                    "purchased_total": org.purchased_tokens,
                    "purchased_used": org.purchased_tokens_used,
                    "purchased_remaining": max(
                        0, org.purchased_tokens - org.purchased_tokens_used
                    ),
                    "total_available": (org.credits_total - org.credits_used)
                    + (org.purchased_tokens - org.purchased_tokens_used),
                },
                "autofix_tokens": {
                    "total": org.autofix_tokens_total,
                    "used": org.autofix_tokens_used,
                    "remaining": max(
                        0, org.autofix_tokens_total - org.autofix_tokens_used
                    ),
                },
                "limits": limits["windows"],
                "limit_enforcement_enabled": org.limit_enforcement_enabled,
            }
        )

    return {"customers": results}


@router.post("/v1/admin/customers")
def create_customer(req: CreateCustomerRequest, db: Session = Depends(get_db)):
    """Provision a new customer organization manually."""
    plan = req.plan.lower()
    default_quota = PLAN_DEFINITIONS.get(plan, {}).get("quota", 100)
    credits_total = (
        req.credits_total if req.credits_total is not None else default_quota
    )

    new_org = Organization(
        id=f"org_{uuid.uuid4().hex[:12]}",
        name=req.name,
        token=f"skl_live_{uuid.uuid4().hex}",
        plan=plan,
        email=req.email,
        credits_total=credits_total,
        credits_used=0,
        autofix_tokens_total=req.autofix_tokens_total,
        autofix_tokens_used=0,
        limit_enforcement_enabled=True,
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    return {"status": "created", "customer": new_org}


@router.post("/v1/admin/customers/{org_id}/update")
def update_customer(
    org_id: str, req: UpdateCustomerRequest, db: Session = Depends(get_db)
):
    """Perform modifications to customer plan, name, email, or token limits."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer organization not found")

    if req.name is not None:
        org.name = req.name
    if req.email is not None:
        org.email = req.email
    if req.billing_email is not None:
        org.billing_email = req.billing_email
    if req.stripe_subscription_status is not None:
        org.stripe_subscription_status = req.stripe_subscription_status
    if req.limit_enforcement_enabled is not None:
        org.limit_enforcement_enabled = req.limit_enforcement_enabled

    # If plan is updated, adjust quota if not explicitly specified
    if req.plan is not None:
        new_plan = req.plan.lower()
        if new_plan in PLAN_DEFINITIONS:
            org.plan = new_plan
            if req.credits_total is None:
                org.credits_total = PLAN_DEFINITIONS[new_plan]["quota"]
                org.credits_used = 0

    if req.credits_total is not None:
        org.credits_total = req.credits_total
    if req.autofix_tokens_total is not None:
        org.autofix_tokens_total = req.autofix_tokens_total

    db.add(org)
    db.commit()
    db.refresh(org)

    return {"status": "updated", "customer": org}


@router.post("/v1/admin/customers/{org_id}/refill-tokens")
def refill_tokens(org_id: str, req: RefillTokensRequest, db: Session = Depends(get_db)):
    """Admin tool to credit additional Coding or Autofix tokens to a customer."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer organization not found")

    if req.amount_tokens <= 0:
        raise HTTPException(
            status_code=400, detail="Token amount must be greater than zero"
        )

    item_name = ""
    if req.token_type == "coding":
        org.purchased_tokens += req.amount_tokens
        item_name = f"Admin Grant: {req.amount_tokens:,} Universal Coding Tokens"
    elif req.token_type == "autofix":
        org.autofix_tokens_total += req.amount_tokens
        item_name = f"Admin Grant: {req.amount_tokens:,} Skelion Autofix Tokens"
    else:
        raise HTTPException(
            status_code=400, detail="Invalid token_type. Must be 'coding' or 'autofix'"
        )

    # Record administrative grant transaction
    tx = TransactionRecord(
        org_id=org.id,
        order_id=f"admin_grant_{uuid.uuid4().hex[:10]}",
        payment_id=f"admin_manual_{req.reason.replace(' ', '_')[:20]}",
        category="admin_credit",
        item_name=item_name,
        amount_inr=0.0,
        tokens_granted=req.amount_tokens,
        status="paid",
    )
    db.add(tx)
    db.add(org)
    db.commit()
    db.refresh(org)

    return {
        "status": "refilled",
        "org_id": org.id,
        "token_type": req.token_type,
        "tokens_added": req.amount_tokens,
        "coding_available": (org.credits_total - org.credits_used)
        + (org.purchased_tokens - org.purchased_tokens_used),
        "autofix_remaining": org.autofix_tokens_total - org.autofix_tokens_used,
    }


@router.post("/v1/admin/customers/{org_id}/reset-limits")
def reset_limits(org_id: str, db: Session = Depends(get_db)):
    """Instantly reset 5-hour and weekly usage counters for a customer."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer organization not found")

    org.window_5h_tokens_used = 0
    org.window_5h_reset_at = utc_now()
    org.window_weekly_tokens_used = 0
    org.window_weekly_reset_at = utc_now()

    db.add(org)
    db.commit()

    return {
        "status": "limits_reset",
        "org_id": org.id,
        "message": "5h and weekly limit counters reset to 0",
    }


@router.post("/v1/admin/customers/{org_id}/toggle-enforcement")
def toggle_customer_enforcement(org_id: str, db: Session = Depends(get_db)):
    """Toggle rate limit throttling on/off for a customer."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer organization not found")

    org.limit_enforcement_enabled = not org.limit_enforcement_enabled
    db.add(org)
    db.commit()

    return {
        "status": "toggled",
        "org_id": org.id,
        "limit_enforcement_enabled": org.limit_enforcement_enabled,
    }


@router.post("/v1/admin/customers/{org_id}/regenerate-token")
def regenerate_api_token(org_id: str, db: Session = Depends(get_db)):
    """Regenerate API key for an organization."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer organization not found")

    org.token = f"skl_live_{uuid.uuid4().hex}"
    db.add(org)
    db.commit()

    return {"status": "regenerated", "org_id": org.id, "token": org.token}


@router.delete("/v1/admin/customers/{org_id}")
def delete_customer(org_id: str, db: Session = Depends(get_db)):
    """Delete a customer organization."""
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Customer organization not found")

    db.delete(org)
    db.commit()
    return {"status": "deleted", "org_id": org_id}


@router.get("/v1/admin/transactions")
def list_transactions(limit: int = 50, db: Session = Depends(get_db)):
    """Return checkout orders and payment transactions feed."""
    txs = db.exec(
        select(TransactionRecord)
        .order_by(desc(TransactionRecord.created_at))
        .limit(limit)
    ).all()

    # Join org names
    org_map = {o.id: o.name for o in db.exec(select(Organization)).all()}

    results = []
    for t in txs:
        results.append(
            {
                "id": t.id,
                "org_id": t.org_id,
                "org_name": org_map.get(t.org_id, "Unknown Customer"),
                "order_id": t.order_id,
                "payment_id": t.payment_id,
                "category": t.category,
                "item_name": t.item_name,
                "amount_inr": t.amount_inr,
                "tokens_granted": t.tokens_granted,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        )

    return {"transactions": results}


class IssueAdminLicenseRequest(BaseModel):
    org_id: str
    plan_id: str = "local_team"
    duration_days: int = 365
    grace_days: int = 7


@router.get("/v1/admin/licenses")
def list_admin_licenses(db: Session = Depends(get_db)):
    """List all issued offline licenses across all customers."""
    licenses = db.exec(select(License).order_by(desc(License.issued_at))).all()
    org_map = {o.id: o.name for o in db.exec(select(Organization)).all()}

    results = []
    for lic in licenses:
        results.append(
            {
                "id": lic.id,
                "org_id": lic.org_id,
                "org_name": org_map.get(lic.org_id, "Unknown Org"),
                "sku": lic.sku,
                "plan_id": lic.plan_id,
                "customer_name": lic.customer_name,
                "customer_email": lic.customer_email,
                "issued_at": lic.issued_at.isoformat() if lic.issued_at else None,
                "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                "grace_days": lic.grace_days,
                "active": lic.active,
            }
        )
    return {"licenses": results}


@router.post("/v1/admin/licenses/issue")
def issue_admin_license(req: IssueAdminLicenseRequest, db: Session = Depends(get_db)):
    """Issue and cryptographically sign an offline Ed25519 license for any org."""
    org = db.get(Organization, req.org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    signed_lic = issue_license(
        org_id=org.id,
        customer_name=org.name,
        customer_email=org.email
        or f"admin@{org.name.lower().replace(' ', '')}.internal",
        plan_id=req.plan_id,
        duration_days=req.duration_days,
        grace_days=req.grace_days,
    )

    lic_payload = signed_lic["payload"]
    lic_record = License(
        id=lic_payload["license_id"],
        org_id=org.id,
        sku="local",
        plan_id=req.plan_id,
        limits_json=json.dumps(lic_payload.get("limits", {})),
        features_json=json.dumps(lic_payload.get("features", [])),
        signature=signed_lic["signature"],
        customer_name=org.name,
        customer_email=org.email
        or f"admin@{org.name.lower().replace(' ', '')}.internal",
        issued_at=datetime.fromisoformat(lic_payload["issued_at"]),
        expires_at=datetime.fromisoformat(lic_payload["expires_at"]),
        grace_days=req.grace_days,
        active=True,
    )
    db.add(lic_record)
    db.commit()

    return {
        "status": "issued",
        "license_id": lic_record.id,
        "plan": req.plan_id,
        "signed_license": signed_lic,
    }


@router.get("/v1/admin/licenses/{license_id}/download")
def download_admin_license(license_id: str, db: Session = Depends(get_db)):
    """Download signed license file for offline airgap installation."""
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")

    signed_format = {
        "license_format": "skelion-ed25519-v1",
        "kid": "skelion_root_2026_v1",
        "payload": {
            "v": 1,
            "license_id": lic.id,
            "org_id": lic.org_id,
            "sku": lic.sku,
            "plan": lic.plan_id,
            "limits": json.loads(lic.limits_json) if lic.limits_json else {},
            "features": json.loads(lic.features_json) if lic.features_json else [],
            "issued_at": lic.issued_at.isoformat() if lic.issued_at else None,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
            "grace_days": lic.grace_days,
            "customer": {
                "name": lic.customer_name,
                "email": lic.customer_email,
            },
        },
        "signature": lic.signature,
    }

    content = json.dumps(signed_format, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=skelion-{lic.id}.license"
        },
    )


@router.post("/v1/admin/licenses/{license_id}/revoke")
def revoke_admin_license(license_id: str, db: Session = Depends(get_db)):
    """Revoke an offline license."""
    lic = db.get(License, license_id)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    lic.active = False
    db.add(lic)
    db.commit()
    return {"status": "revoked", "license_id": license_id}


# ---------------------------------------------------------------------------
# Master Dashboard UI (Single-Page App)
# ---------------------------------------------------------------------------


@router.get("/admin", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def serve_master_dashboard():
    """Serves the special Master Control Dashboard with real-time management."""
    return HTMLResponse(content=DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Skelion Master Control Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090c13;
      --card-bg: #111624;
      --card-border: #1c2438;
      --card-hover: #161e31;
      --text-main: #f0f3fa;
      --text-muted: #8b9bb4;
      --accent: #7c5cff;
      --accent-hover: #6a49f5;
      --accent-glow: rgba(124, 92, 255, 0.25);
      --mint: #10b981;
      --mint-glow: rgba(16, 185, 129, 0.2);
      --amber: #f59e0b;
      --red: #ef4444;
      --blue: #3b82f6;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    /* Top Navbar */
    header {
      background: rgba(17, 22, 36, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 50;
      padding: 0.85rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }

    .brand-logo {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, var(--accent), #ff5caa);
      border-radius: 10px;
      display: grid;
      place-items: center;
      box-shadow: 0 0 16px var(--accent-glow);
    }

    .brand-title {
      font-size: 1.15rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(90deg, #fff, #b9c7df);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-badge {
      font-size: 0.65rem;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 7px;
      background: rgba(124, 92, 255, 0.18);
      color: var(--accent);
      border: 1px solid rgba(124, 92, 255, 0.35);
      border-radius: 6px;
      margin-left: 0.4rem;
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
      font-weight: 600;
      padding: 0.55rem 1rem;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
    }

    .btn-primary {
      background: var(--accent);
      color: #fff;
      box-shadow: 0 0 14px var(--accent-glow);
    }
    .btn-primary:hover {
      background: var(--accent-hover);
      transform: translateY(-1px);
    }

    .btn-outline {
      background: transparent;
      border-color: var(--card-border);
      color: var(--text-main);
    }
    .btn-outline:hover {
      background: var(--card-bg);
      border-color: #2b354e;
    }

    /* Main Container */
    main {
      flex: 1;
      max-width: 1400px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.25rem;
    }

    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 1.25rem 1.5rem;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s, border-color 0.2s;
    }
    .stat-card:hover {
      transform: translateY(-2px);
      border-color: #2a3550;
    }

    .stat-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--accent);
    }
    .stat-card.mint::before { background: var(--mint); }
    .stat-card.amber::before { background: var(--amber); }
    .stat-card.blue::before { background: var(--blue); }

    .stat-label {
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 0.4rem;
    }

    .stat-value {
      font-size: 1.85rem;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: baseline;
      gap: 0.4rem;
    }

    .stat-sub {
      font-size: 0.78rem;
      color: var(--text-muted);
      margin-top: 0.35rem;
    }

    /* Tab Controls */
    .tab-bar {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 0.5rem;
    }

    .tab-item {
      padding: 0.55rem 1.15rem;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      transition: all 0.2s ease;
      background: transparent;
      border: none;
    }
    .tab-item.active {
      color: #fff;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
    }

    /* Search & Filter Toolbar */
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .search-box {
      display: flex;
      align-items: center;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 0.5rem 0.9rem;
      width: 320px;
      max-width: 100%;
    }
    .search-box input {
      background: transparent;
      border: none;
      outline: none;
      color: #fff;
      font-size: 0.88rem;
      width: 100%;
      margin-left: 0.5rem;
      font-family: inherit;
    }

    .filter-select {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      border-radius: 8px;
      padding: 0.55rem 0.9rem;
      font-size: 0.85rem;
      outline: none;
      cursor: pointer;
      font-family: inherit;
    }

    /* Content Cards / Tables */
    .panel-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      overflow: hidden;
    }

    .table-container {
      width: 100%;
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.86rem;
    }

    th {
      background: rgba(22, 29, 47, 0.6);
      color: var(--text-muted);
      font-weight: 700;
      text-transform: uppercase;
      font-size: 0.72rem;
      letter-spacing: 0.05em;
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--card-border);
    }

    td {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--card-border);
      vertical-align: middle;
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255, 255, 255, 0.015); }

    /* Customer Name Info */
    .customer-cell {
      display: flex;
      align-items: center;
      gap: 0.85rem;
    }
    .customer-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #1c2438;
      display: grid;
      place-items: center;
      font-weight: 700;
      color: var(--accent);
      font-size: 0.85rem;
      border: 1px solid rgba(255,255,255,0.08);
      flex-shrink: 0;
    }
    .customer-info-title {
      font-weight: 700;
      color: #fff;
    }
    .customer-info-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }

    /* Badges */
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }
    .badge-pilot { background: rgba(139, 155, 180, 0.15); color: #b9c7df; border: 1px solid rgba(139, 155, 180, 0.3); }
    .badge-pro { background: rgba(124, 92, 255, 0.18); color: #a289ff; border: 1px solid rgba(124, 92, 255, 0.4); }
    .badge-enterprise { background: rgba(16, 185, 129, 0.18); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-team { background: rgba(59, 130, 246, 0.18); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    
    .badge-paid { background: rgba(16, 185, 129, 0.15); color: var(--mint); border: 1px solid var(--mint-glow); }
    .badge-created { background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }

    /* Mini Progress Bar */
    .mini-progress {
      width: 110px;
      height: 6px;
      background: #1c2438;
      border-radius: 3px;
      overflow: hidden;
      margin-top: 4px;
    }
    .mini-progress-fill {
      height: 100%;
      background: var(--accent);
      border-radius: 3px;
    }
    .mini-progress-fill.mint { background: var(--mint); }
    .mini-progress-fill.amber { background: var(--amber); }

    /* Action Icon Buttons */
    .action-group {
      display: flex;
      gap: 0.4rem;
      align-items: center;
    }
    .btn-icon {
      background: #182033;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      border-radius: 6px;
      padding: 5px 9px;
      font-size: 0.78rem;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.15s ease;
      font-family: inherit;
    }
    .btn-icon:hover {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
      transform: scale(1.04);
    }
    .btn-icon.danger:hover {
      background: var(--red);
      border-color: var(--red);
    }

    /* Modal Overlay */
    .modal-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.75);
      backdrop-filter: blur(6px);
      display: none;
      place-items: center;
      z-index: 100;
      padding: 1.5rem;
    }
    .modal-overlay.open { display: grid; }

    .modal-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      width: 100%;
      max-width: 520px;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      animation: modalIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes modalIn {
      from { opacity: 0; transform: scale(0.96) translateY(8px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }

    .modal-header {
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .modal-title {
      font-size: 1.1rem;
      font-weight: 700;
      color: #fff;
    }
    .modal-close {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 1.2rem;
      cursor: pointer;
    }

    .modal-body {
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.1rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }
    .form-group label {
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .form-control {
      background: #0b0f19;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 0.65rem 0.9rem;
      color: #fff;
      font-size: 0.88rem;
      outline: none;
      font-family: inherit;
    }
    .form-control:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-glow);
    }

    .modal-footer {
      padding: 1rem 1.5rem;
      background: rgba(14, 19, 32, 0.7);
      border-top: 1px solid var(--card-border);
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
    }

    /* Toast Notification */
    #toast {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: var(--card-bg);
      border: 1px solid var(--mint);
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
      border-radius: 10px;
      padding: 0.9rem 1.4rem;
      color: #fff;
      font-weight: 600;
      font-size: 0.88rem;
      display: none;
      align-items: center;
      gap: 0.7rem;
      z-index: 200;
      animation: toastIn 0.3s ease;
    }
    @keyframes toastIn {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  </style>
</head>
<body>

  <!-- Top Navigation -->
  <header>
    <div class="brand">
      <div class="brand-logo">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div>
        <span class="brand-title">SKELION CONTROL PLANE</span>
        <span class="brand-badge">Master Admin</span>
      </div>
    </div>
    <div class="nav-actions">
      <button class="btn btn-outline" onclick="loadAllData()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        Refresh
      </button>
      <button class="btn btn-primary" onclick="openCreateModal()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        + New Customer Org
      </button>
    </div>
  </header>

  <!-- Main Content -->
  <main>
    <!-- KPIs Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Customers</div>
        <div class="stat-value" id="kpi-customers">-</div>
        <div class="stat-sub" id="kpi-plans-sub">Loading plans...</div>
      </div>
      <div class="stat-card mint">
        <div class="stat-label">Total Revenue</div>
        <div class="stat-value" id="kpi-revenue">₹0</div>
        <div class="stat-sub" id="kpi-orders-sub">0 Completed Checkouts</div>
      </div>
      <div class="stat-card blue">
        <div class="stat-label">Autofix Token Pool</div>
        <div class="stat-value" id="kpi-autofix">-</div>
        <div class="stat-sub" id="kpi-autofix-sub">Dedicated unthrottled pool</div>
      </div>
      <div class="stat-card amber">
        <div class="stat-label">Universal Coding Tokens</div>
        <div class="stat-value" id="kpi-coding">-</div>
        <div class="stat-sub" id="kpi-coding-sub">Active in circulation</div>
      </div>
    </div>

    <!-- Tab Bar -->
    <div class="tab-bar">
      <button class="tab-item active" onclick="switchTab('customers')">👥 Customers & Quota Management</button>
      <button class="tab-item" onclick="switchTab('transactions')">💳 Checkout & Orders Feed</button>
      <button class="tab-item" onclick="switchTab('licenses')">📜 Offline Licenses (Airgap)</button>
    </div>

    <!-- Section: Customers & Quotas -->
    <div id="section-customers" style="display: flex; flex-direction: column; gap: 1rem;">
      <div class="toolbar">
        <div class="search-box">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-muted);"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <input type="text" id="customer-search" placeholder="Search customer, email or org id..." oninput="filterCustomers()">
        </div>
        <div style="display: flex; gap: 0.6rem;">
          <select class="filter-select" id="plan-filter" onchange="filterCustomers()">
            <option value="all">All Plans</option>
            <option value="pilot">Pilot</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
      </div>

      <div class="panel-card">
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Customer / Organization</th>
                <th>Plan & Status</th>
                <th>Universal Coding Tokens</th>
                <th>Autofix Tokens</th>
                <th>Rate Limits (5h & Wk)</th>
                <th>Throttling</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="customers-table-body">
              <tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:3rem;">Loading customers...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Section: Checkouts & Transactions Feed -->
    <div id="section-transactions" style="display: none; flex-direction: column; gap: 1rem;">
      <div class="panel-card">
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Order / Transaction ID</th>
                <th>Customer Org</th>
                <th>Category</th>
                <th>Description</th>
                <th>Amount (INR)</th>
                <th>Tokens Credited</th>
                <th>Status</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody id="transactions-table-body">
              <tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:3rem;">Loading checkouts...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Section: Offline Licenses & Airgap -->
    <div id="section-licenses" style="display: none; flex-direction: column; gap: 1rem;">
      <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 0.88rem; color: var(--text-muted);">
          Cryptographically signed Ed25519 offline licenses for customer airgapped on-prem deployments.
        </div>
        <button class="btn btn-primary" onclick="openIssueLicenseModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          + Issue Offline License
        </button>
      </div>

      <div class="panel-card">
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>License ID</th>
                <th>Customer Org</th>
                <th>Plan SKU</th>
                <th>Issued At</th>
                <th>Expires At</th>
                <th>Grace</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="licenses-table-body">
              <tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:3rem;">Loading licenses...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </main>

  <!-- Issue License Modal -->
  <div class="modal-overlay" id="issue-license-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">📜 Issue Ed25519 Offline License</div>
        <button class="modal-close" onclick="closeModal('issue-license-modal')">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Target Customer Organization</label>
          <select class="form-control" id="license-org-select">
            <option value="">Select customer org...</option>
          </select>
        </div>
        <div class="form-group">
          <label>License Plan Tier</label>
          <select class="form-control" id="license-plan-select">
            <option value="local_community">Local Community (Free / BYO-LLM)</option>
            <option value="local_pro">Local Pro (Single Node / Full Autonomous Fixes)</option>
            <option value="local_team" selected>Local Team (Up to 10 Nodes / Sandboxed Replay)</option>
            <option value="local_enterprise">Local Enterprise (Unlimited Nodes / Airgapped)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Validity Duration (Days)</label>
          <select class="form-control" id="license-duration-select">
            <option value="30">30 Days (Pilot / POC)</option>
            <option value="90">90 Days (Quarterly)</option>
            <option value="365" selected>365 Days (Annual)</option>
            <option value="730">730 Days (2-Year Enterprise)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Expiry Grace Period (Days)</label>
          <input type="number" class="form-control" id="license-grace-days" value="7">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeModal('issue-license-modal')">Cancel</button>
        <button class="btn btn-primary" onclick="submitIssueLicense()">Sign & Issue License</button>
      </div>
    </div>
  </div>

  <!-- Edit Customer Modal -->
  <div class="modal-overlay" id="edit-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">✏️ Modify Customer Details & Plan</div>
        <button class="modal-close" onclick="closeModal('edit-modal')">&times;</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="edit-org-id">
        <div class="form-group">
          <label>Customer Organization Name</label>
          <input type="text" class="form-control" id="edit-name">
        </div>
        <div class="form-group">
          <label>Email Address</label>
          <input type="email" class="form-control" id="edit-email">
        </div>
        <div class="form-group">
          <label>Subscription Plan</label>
          <select class="form-control" id="edit-plan" onchange="onEditPlanChanged(this.value)">
            <option value="hosted_community">Hosted Community (Free / 50 Credits)</option>
            <option value="hosted_lite">Skelion AI Lite (Pilot 30% Off / ₹559 / 500 Credits)</option>
            <option value="hosted_developer">Hosted Developer (₹799/mo / 800 Credits)</option>
            <option value="hosted_team">Hosted Team (₹3,999/mo / 4,500 Credits)</option>
            <option value="hosted_business">Hosted Business (₹9,999/mo / 12,500 Credits)</option>
            <option value="local_solo">Local Solo (₹999/mo / BYO-LLM / 1 Project)</option>
            <option value="local_team">Local Team (₹4,999/mo / 5 Projects / Unlimited Seats)</option>
            <option value="local_business">Local Business (₹14,999/mo / 20 Projects)</option>
            <option value="hosted_enterprise">Enterprise Tier (Custom / SLA)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Monthly Coding Tokens Quota</label>
          <input type="number" class="form-control" id="edit-monthly-quota">
        </div>
        <div class="form-group">
          <label>Autofix Tokens Pool</label>
          <input type="number" class="form-control" id="edit-autofix-total">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeModal('edit-modal')">Cancel</button>
        <button class="btn btn-primary" onclick="submitEditCustomer()">Save Modifications</button>
      </div>
    </div>
  </div>

  <!-- Refill Tokens Modal -->
  <div class="modal-overlay" id="refill-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">➕ Credit / Refill Tokens</div>
        <button class="modal-close" onclick="closeModal('refill-modal')">&times;</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="refill-org-id">
        <div style="font-size:0.9rem; color:#fff;" id="refill-target-name">Customer: <b>-</b></div>
        <div class="form-group">
          <label>Token Pool Type</label>
          <select class="form-control" id="refill-type">
            <option value="coding">Universal Coding Tokens (Top-Up Pool)</option>
            <option value="autofix">Skelion Autofix Tokens (Dedicated Pool)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Tokens to Grant</label>
          <input type="number" class="form-control" id="refill-amount" placeholder="e.g. 5000" value="1000">
        </div>
        <div class="form-group">
          <label>Admin Note / Reason</label>
          <input type="text" class="form-control" id="refill-reason" value="Customer loyalty bonus">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeModal('refill-modal')">Cancel</button>
        <button class="btn btn-primary" onclick="submitRefillTokens()">Grant Tokens</button>
      </div>
    </div>
  </div>

  <!-- Create Customer Modal -->
  <div class="modal-overlay" id="create-modal">
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">✨ Provision New Customer Org</div>
        <button class="modal-close" onclick="closeModal('create-modal')">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>Customer Name</label>
          <input type="text" class="form-control" id="new-name" placeholder="Acme Dev Labs">
        </div>
        <div class="form-group">
          <label>Customer Email</label>
          <input type="email" class="form-control" id="new-email" placeholder="founder@acme.io">
        </div>
        <div class="form-group">
          <label>Select Plan</label>
          <select class="form-control" id="new-plan">
            <option value="hosted_community">Hosted Community (Free)</option>
            <option value="hosted_developer">Hosted Developer (₹799/mo)</option>
            <option value="hosted_team" selected>Hosted Team (₹3,999/mo)</option>
            <option value="hosted_business">Hosted Business (₹9,999/mo)</option>
            <option value="local_solo">Local Solo (₹999/mo)</option>
            <option value="local_team">Local Team (₹4,999/mo)</option>
            <option value="local_business">Local Business (₹14,999/mo)</option>
            <option value="hosted_enterprise">Enterprise Tier</option>
          </select>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" onclick="closeModal('create-modal')">Cancel</button>
        <button class="btn btn-primary" onclick="submitCreateCustomer()">Create Customer Org</button>
      </div>
    </div>
  </div>

  <!-- Toast -->
  <div id="toast">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--mint)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
    <span id="toast-msg">Action completed!</span>
  </div>

  <script>
    let rawCustomers = [];
    let rawTransactions = [];

    async function loadAllData() {
      try {
        const [statsRes, custRes, txRes] = await Promise.all([
          fetch('/v1/admin/stats'),
          fetch('/v1/admin/customers'),
          fetch('/v1/admin/transactions')
        ]);
        
        const stats = await statsRes.json();
        const custData = await custRes.json();
        const txData = await txRes.json();

        // Update KPIs
        document.getElementById('kpi-customers').textContent = stats.total_customers;
        const plansStr = Object.entries(stats.plans_breakdown).map(([k, v]) => k.toUpperCase() + ': ' + v).join(' | ');
        document.getElementById('kpi-plans-sub').textContent = plansStr || 'No active plans';

        document.getElementById('kpi-revenue').textContent = '₹' + stats.total_revenue_inr.toLocaleString();
        document.getElementById('kpi-orders-sub').textContent = stats.total_orders + ' Checkouts Processed';

        document.getElementById('kpi-autofix').textContent = stats.tokens.autofix_remaining.toLocaleString();
        document.getElementById('kpi-autofix-sub').textContent = stats.tokens.autofix_used.toLocaleString() + ' Used / ' + stats.tokens.autofix_allocated.toLocaleString() + ' Total';

        document.getElementById('kpi-coding').textContent = stats.tokens.coding_remaining.toLocaleString();
        document.getElementById('kpi-coding-sub').textContent = stats.tokens.coding_used.toLocaleString() + ' Used / ' + stats.tokens.coding_allocated.toLocaleString() + ' Total';

        rawCustomers = custData.customers || [];
        rawTransactions = txData.transactions || [];

        renderCustomersTable(rawCustomers);
        renderTransactionsTable(rawTransactions);
      } catch (err) {
        showToast('Error loading admin data: ' + err.message);
      }
    }

    function renderCustomersTable(list) {
      const tbody = document.getElementById('customers-table-body');
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:2rem;">No matching customers found.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(c => {
        const initials = (c.name || 'C').substring(0, 2).toUpperCase();
        const badgeClass = 'badge-' + (c.plan || 'pilot');
        
        const codingTotal = c.coding_tokens.total_available;
        const codingMonthlyUsedPct = Math.min(100, (c.coding_tokens.monthly_used / (c.coding_tokens.monthly_total || 1)) * 100);
        
        const autofixUsedPct = Math.min(100, (c.autofix_tokens.used / (c.autofix_tokens.total || 1)) * 100);
        
        const fiveHour = c.limits.five_hour;
        const weekly = c.limits.weekly;
        const throttlingActive = c.limit_enforcement_enabled ? 
          '<span style="color:var(--mint); font-weight:700; font-size:11px;">ACTIVE (Throttled)</span>' : 
          '<span style="color:var(--amber); font-weight:700; font-size:11px;">BYPASS (Full Speed)</span>';

        return `
          <tr>
            <td>
              <div class="customer-cell">
                <div class="customer-avatar">${initials}</div>
                <div>
                  <div class="customer-info-title">${escapeHtml(c.name)}</div>
                  <div class="customer-info-sub">${escapeHtml(c.email)}</div>
                  <div style="font-size:10px; color:#556688; font-family:monospace;">${c.id}</div>
                </div>
              </div>
            </td>
            <td>
              <span class="badge ${badgeClass}">${(c.plan || 'pilot').toUpperCase()}</span>
              <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">Status: ${c.subscription_status || 'active'}</div>
            </td>
            <td>
              <div style="font-weight:700; color:#fff;">${c.coding_tokens.total_available.toLocaleString()} Rem.</div>
              <div style="font-size:11px; color:var(--text-muted);">
                Monthly: ${c.coding_tokens.monthly_remaining}/${c.coding_tokens.monthly_total} | Top-Up: ${c.coding_tokens.purchased_remaining}
              </div>
              <div class="mini-progress">
                <div class="mini-progress-fill" style="width:${100 - codingMonthlyUsedPct}%"></div>
              </div>
            </td>
            <td>
              <div style="font-weight:700; color:#fff;">${c.autofix_tokens.remaining.toLocaleString()} Rem.</div>
              <div style="font-size:11px; color:var(--text-muted);">
                Used: ${c.autofix_tokens.used.toLocaleString()} / ${c.autofix_tokens.total.toLocaleString()}
              </div>
              <div class="mini-progress">
                <div class="mini-progress-fill mint" style="width:${100 - autofixUsedPct}%"></div>
              </div>
            </td>
            <td>
              <div style="font-size:11.5px;"><b>5h:</b> ${fiveHour.remaining}/${fiveHour.limit} (${fiveHour.resets_in_human})</div>
              <div style="font-size:11.5px; color:var(--text-muted);"><b>Wk:</b> ${weekly.remaining}/${weekly.limit}</div>
            </td>
            <td>
              ${throttlingActive}
              <div style="margin-top:4px;">
                <button class="btn-icon" style="font-size:10px; padding:2px 6px;" onclick="toggleEnforcement('${c.id}')">Toggle</button>
              </div>
            </td>
            <td>
              <div class="action-group">
                <button class="btn-icon" title="Edit Customer & Plan" onclick="openEditModal('${c.id}')">✏️ Edit</button>
                <button class="btn-icon" title="Credit / Refill Tokens" onclick="openRefillModal('${c.id}', '${escapeHtml(c.name)}')">➕ Refill</button>
                <button class="btn-icon" title="Reset 5h & Weekly Windows" onclick="resetCustomerLimits('${c.id}')">🔄 Reset Limits</button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    function renderTransactionsTable(list) {
      const tbody = document.getElementById('transactions-table-body');
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:2rem;">No checkout transactions recorded yet.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(t => {
        const statusBadge = t.status === 'paid' ? 
          '<span class="badge badge-paid">PAID</span>' : 
          '<span class="badge badge-created">CREATED</span>';

        return `
          <tr>
            <td>
              <div style="font-family:'JetBrains Mono', monospace; font-weight:600; color:#fff;">${escapeHtml(t.order_id)}</div>
              <div style="font-size:10.5px; color:var(--text-muted); font-family:monospace;">${t.id}</div>
            </td>
            <td>
              <b>${escapeHtml(t.org_name)}</b>
              <div style="font-size:10.5px; color:#556688; font-family:monospace;">${t.org_id}</div>
            </td>
            <td><span class="badge badge-pilot">${escapeHtml(t.category)}</span></td>
            <td><b>${escapeHtml(t.item_name || '-')}</b></td>
            <td style="font-weight:700; color:var(--mint);">₹${t.amount_inr.toLocaleString()}</td>
            <td><b>${t.tokens_granted > 0 ? t.tokens_granted.toLocaleString() + ' Tokens' : '-'}</b></td>
            <td>${statusBadge}</td>
            <td style="font-size:11px; color:var(--text-muted);">${t.created_at ? new Date(t.created_at).toLocaleString() : '-'}</td>
          </tr>
        `;
      }).join('');
    }

    const PLAN_DEFAULT_QUOTAS = {
      hosted_community: 50,
      hosted_lite: 500,
      hosted_developer: 800,
      hosted_team: 4500,
      hosted_business: 12500,
      hosted_enterprise: 50000,
      local_community: 100,
      local_solo: 1000,
      local_team: 5000,
      local_business: 15000,
      local_enterprise: 50000,
      pilot: 100,
      starter: 500,
      pro: 1200,
      team: 4500,
      enterprise: 15000
    };

    function onEditPlanChanged(val) {
      const q = PLAN_DEFAULT_QUOTAS[val] || 100;
      const inp = document.getElementById('edit-monthly-quota');
      if (inp) inp.value = q;
    }

    function switchTab(tab) {
      document.querySelectorAll('.tab-item').forEach(b => b.classList.remove('active'));
      const activeBtn = document.querySelector('.tab-item[onclick*="' + tab + '"]');
      if (activeBtn) activeBtn.classList.add('active');
      if (tab === 'customers') {
        document.getElementById('section-customers').style.display = 'flex';
        document.getElementById('section-transactions').style.display = 'none';
        document.getElementById('section-licenses').style.display = 'none';
      } else if (tab === 'transactions') {
        document.getElementById('section-customers').style.display = 'none';
        document.getElementById('section-transactions').style.display = 'flex';
        document.getElementById('section-licenses').style.display = 'none';
      } else if (tab === 'licenses') {
        document.getElementById('section-customers').style.display = 'none';
        document.getElementById('section-transactions').style.display = 'none';
        document.getElementById('section-licenses').style.display = 'flex';
        loadLicenses();
      }
    }

    let rawLicenses = [];

    async function loadLicenses() {
      try {
        const res = await fetch('/v1/admin/licenses');
        if (res.ok) {
          const data = await res.json();
          rawLicenses = data.licenses || [];
          renderLicensesTable(rawLicenses);
        }
      } catch (e) {
        console.error('Failed to load licenses', e);
      }
    }

    function renderLicensesTable(list) {
      const tbody = document.getElementById('licenses-table-body');
      if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:2rem;">No offline licenses issued yet. Click "+ Issue Offline License" above to generate one.</td></tr>';
        return;
      }

      tbody.innerHTML = list.map(lic => {
        const statusBadge = lic.active ? 
          '<span class="badge badge-paid">ACTIVE</span>' : 
          '<span class="badge badge-danger">REVOKED</span>';

        return `
          <tr>
            <td>
              <div style="font-family:\'JetBrains Mono\', monospace; font-weight:600; color:#fff;">${escapeHtml(lic.id)}</div>
            </td>
            <td>
              <b>${escapeHtml(lic.org_name)}</b>
              <div style="font-size:10.5px; color:#556688; font-family:monospace;">${escapeHtml(lic.org_id)}</div>
            </td>
            <td><span class="badge badge-enterprise">${escapeHtml(lic.plan_id)}</span></td>
            <td style="font-size:11px; color:var(--text-muted);">${lic.issued_at ? new Date(lic.issued_at).toLocaleDateString() : '-'}</td>
            <td style="font-size:11px; color:var(--mint); font-weight:600;">${lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : '-'}</td>
            <td><b>${lic.grace_days}d</b></td>
            <td>${statusBadge}</td>
            <td>
              <div class="action-group">
                <a class="btn-icon" href="/v1/admin/licenses/${lic.id}/download" title="Download .skelion.license file" download style="text-decoration:none;">⬇️ Download</a>
                ${lic.active ? `<button class="btn-icon danger" onclick="revokeLicense(\'${lic.id}\')" title="Revoke License">🚫 Revoke</button>` : ''}
              </div>
            </td>
          </tr>
        `;
      }).join('');
    }

    function openIssueLicenseModal() {
      const select = document.getElementById('license-org-select');
      select.innerHTML = '<option value="">Select customer org...</option>' + 
        rawCustomers.map(c => `<option value="${c.id}">${escapeHtml(c.name)} (${c.id})</option>`).join('');
      openModal('issue-license-modal');
    }

    async function submitIssueLicense() {
      const orgId = document.getElementById('license-org-select').value;
      if (!orgId) { alert('Please select a customer organization'); return; }
      const payload = {
        org_id: orgId,
        plan_id: document.getElementById('license-plan-select').value,
        duration_days: parseInt(document.getElementById('license-duration-select').value) || 365,
        grace_days: parseInt(document.getElementById('license-grace-days').value) || 7
      };

      try {
        const res = await fetch('/v1/admin/licenses/issue', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal('issue-license-modal');
          showToast('Offline license generated and cryptographically signed!');
          loadLicenses();
        } else {
          const err = await res.json();
          alert('Failed to issue license: ' + (err.detail || 'Unknown error'));
        }
      } catch (e) {
        alert('Error issuing license: ' + e.message);
      }
    }

    async function revokeLicense(licId) {
      if (!confirm('Are you sure you want to revoke license ' + licId + '?')) return;
      try {
        const res = await fetch('/v1/admin/licenses/' + licId + '/revoke', { method: 'POST' });
        if (res.ok) {
          showToast('License ' + licId + ' revoked.');
          loadLicenses();
        }
      } catch (e) {
        alert('Revoke failed: ' + e.message);
      }
    }

    function filterCustomers() {
      const q = document.getElementById('customer-search').value.toLowerCase().trim();
      const plan = document.getElementById('plan-filter').value;
      const filtered = rawCustomers.filter(c => {
        const matchesQuery = !q || 
          c.name.toLowerCase().includes(q) || 
          c.email.toLowerCase().includes(q) || 
          c.id.toLowerCase().includes(q);
        const matchesPlan = plan === 'all' || (c.plan || 'pilot') === plan;
        return matchesQuery && matchesPlan;
      });
      renderCustomersTable(filtered);
    }

    // Modal helpers
    function openModal(id) { document.getElementById(id).classList.add('open'); }
    function closeModal(id) { document.getElementById(id).classList.remove('open'); }

    function openEditModal(orgId) {
      const cust = rawCustomers.find(c => c.id === orgId);
      if (!cust) return;
      document.getElementById('edit-org-id').value = cust.id;
      document.getElementById('edit-name').value = cust.name;
      document.getElementById('edit-email').value = cust.email;
      document.getElementById('edit-plan').value = cust.plan || 'pilot';
      document.getElementById('edit-monthly-quota').value = cust.coding_tokens.monthly_total;
      document.getElementById('edit-autofix-total').value = cust.autofix_tokens.total;
      openModal('edit-modal');
    }

    async function submitEditCustomer() {
      const orgId = document.getElementById('edit-org-id').value;
      const payload = {
        name: document.getElementById('edit-name').value,
        email: document.getElementById('edit-email').value,
        plan: document.getElementById('edit-plan').value,
        credits_total: parseInt(document.getElementById('edit-monthly-quota').value) || 100,
        autofix_tokens_total: parseInt(document.getElementById('edit-autofix-total').value) || 50000
      };

      try {
        const res = await fetch('/v1/admin/customers/' + orgId + '/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal('edit-modal');
          showToast('Customer modifications saved!');
          loadAllData();
        } else {
          const err = await res.json();
          alert('Failed to update: ' + (err.detail || 'Server error'));
        }
      } catch (e) {
        alert('Exception: ' + e.message);
      }
    }

    function openRefillModal(orgId, name) {
      document.getElementById('refill-org-id').value = orgId;
      document.getElementById('refill-target-name').innerHTML = 'Customer: <b>' + escapeHtml(name) + '</b> (' + orgId + ')';
      openModal('refill-modal');
    }

    async function submitRefillTokens() {
      const orgId = document.getElementById('refill-org-id').value;
      const payload = {
        token_type: document.getElementById('refill-type').value,
        amount_tokens: parseInt(document.getElementById('refill-amount').value) || 0,
        reason: document.getElementById('refill-reason').value
      };

      try {
        const res = await fetch('/v1/admin/customers/' + orgId + '/refill-tokens', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal('refill-modal');
          showToast('Tokens successfully credited!');
          loadAllData();
        } else {
          const err = await res.json();
          alert('Failed: ' + (err.detail || 'Server error'));
        }
      } catch (e) {
        alert('Exception: ' + e.message);
      }
    }

    async function resetCustomerLimits(orgId) {
      if (!confirm('Instantly reset 5-hour and weekly usage counters to 0 for this customer?')) return;
      try {
        const res = await fetch('/v1/admin/customers/' + orgId + '/reset-limits', { method: 'POST' });
        if (res.ok) {
          showToast('Customer rate limits successfully reset to 0!');
          loadAllData();
        }
      } catch (e) {
        alert('Reset failed: ' + e.message);
      }
    }

    async function toggleEnforcement(orgId) {
      try {
        const res = await fetch('/v1/admin/customers/' + orgId + '/toggle-enforcement', { method: 'POST' });
        if (res.ok) {
          showToast('Rate limit throttling state updated!');
          loadAllData();
        }
      } catch (e) {
        alert('Toggle failed: ' + e.message);
      }
    }

    function openCreateModal() {
      document.getElementById('new-name').value = '';
      document.getElementById('new-email').value = '';
      openModal('create-modal');
    }

    async function submitCreateCustomer() {
      const name = document.getElementById('new-name').value.trim();
      if (!name) { alert('Please enter a name'); return; }
      const payload = {
        name: name,
        email: document.getElementById('new-email').value.trim(),
        plan: document.getElementById('new-plan').value
      };

      try {
        const res = await fetch('/v1/admin/customers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal('create-modal');
          showToast('New customer organization created!');
          loadAllData();
        }
      } catch (e) {
        alert('Create failed: ' + e.message);
      }
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      document.getElementById('toast-msg').textContent = msg;
      t.style.display = 'flex';
      setTimeout(() => { t.style.display = 'none'; }, 3500);
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Initial load
    loadAllData();
  </script>
</body>
</html>
"""
