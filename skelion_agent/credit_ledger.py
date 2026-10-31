# skelion_agent/credit_ledger.py — Append-Only Ledger & Entitlement Engine (Billing v2)

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlmodel import Session, select

from skelion_agent.models import Organization, CreditLedger, utc_now
from skelion_agent.plan_config import PLAN_DEFINITIONS


def get_ledger_balances(session: Session, org_id: str) -> Dict[str, int]:
    """Calculate live token balances by summing non-expired delta rows in credit_ledger.
    Buckets:
    - 'allowance': monthly plan grant (expires at period_end)
    - 'pack': purchased top-up tokens (valid for 12 months, burned after allowance)
    - 'grant': pilot/promotional credits
    - 'autofix': dedicated Skelion Autofix token pool
    """
    now = utc_now()
    entries = session.exec(
        select(CreditLedger).where(CreditLedger.org_id == org_id)
    ).all()

    balances = {
        "allowance": 0,
        "pack": 0,
        "grant": 0,
        "autofix": 0,
    }

    for e in entries:
        if e.expires_at is not None and e.expires_at < now:
            continue
        if e.bucket in balances:
            balances[e.bucket] += e.delta

    for k in balances:
        balances[k] = max(0, balances[k])

    balances["total_coding"] = (
        balances["allowance"] + balances["pack"] + balances["grant"]
    )
    return balances


def record_ledger_entry(
    session: Session,
    org_id: str,
    bucket: str,
    delta: int,
    reason: str,
    idempotency_key: str,
    ref_type: Optional[str] = None,
    ref_id: Optional[str] = None,
    cost_inr_est: float = 0.0,
    expires_at: Optional[datetime] = None,
) -> Tuple[CreditLedger, bool]:
    """Insert an immutable ledger entry.
    Returns (entry, is_new). If idempotency_key already exists, returns existing entry without double-spending.
    """
    existing = session.exec(
        select(CreditLedger).where(CreditLedger.idempotency_key == idempotency_key)
    ).first()

    if existing:
        return existing, False

    entry = CreditLedger(
        org_id=org_id,
        bucket=bucket,
        delta=delta,
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id,
        idempotency_key=idempotency_key,
        cost_inr_est=cost_inr_est,
        expires_at=expires_at,
    )
    session.add(entry)

    # Sync organization cached summary for backward compatibility
    org = session.get(Organization, org_id)
    if org:
        if bucket == "autofix":
            if delta > 0:
                org.autofix_tokens_total += delta
            else:
                org.autofix_tokens_used += abs(delta)
        elif bucket == "pack":
            if delta > 0:
                org.purchased_tokens += delta
            else:
                org.purchased_tokens_used += abs(delta)
        elif bucket in ("allowance", "grant"):
            if delta > 0:
                org.credits_total += delta
            else:
                org.credits_used += abs(delta)
        session.add(org)

    session.commit()
    session.refresh(entry)
    return entry, True


def activate_plan_period(
    session: Session,
    org_id: str,
    plan_id: str,
    period: str = "monthly",
    payment_id: Optional[str] = None,
) -> Organization:
    """Activate or renew a plan prepaid pass.
    Renewal extends from max(now, current_period_end).
    Credits are granted via the ledger with idempotency_key='period:{payment_id}'.
    """
    org = session.get(Organization, org_id)
    if not org:
        raise ValueError(f"Organization {org_id} not found")

    plan_info = PLAN_DEFINITIONS.get(plan_id, PLAN_DEFINITIONS.get("pilot"))
    quota = plan_info["quota"]
    days = 365 if period == "annual" else 30

    now = utc_now()
    if org.plan_period_end and org.plan_period_end > now:
        start_date = org.plan_period_start or now
        end_date = org.plan_period_end + timedelta(days=days)
    else:
        start_date = now
        end_date = now + timedelta(days=days)

    org.plan = plan_id
    org.plan_id = plan_id
    org.billing_status = "active"
    org.plan_period_start = start_date
    org.plan_period_end = end_date
    org.grace_until = end_date + timedelta(days=3)
    org.credits_total = quota
    org.credits_used = 0
    session.add(org)

    # Record ledger grant
    idemp_key = (
        f"period:{payment_id}"
        if payment_id
        else f"period:{org.id}:{end_date.isoformat()}"
    )
    record_ledger_entry(
        session=session,
        org_id=org.id,
        bucket="allowance",
        delta=quota,
        reason="plan_period",
        ref_type="payment" if payment_id else "admin",
        ref_id=payment_id,
        idempotency_key=idemp_key,
        expires_at=end_date,
    )

    session.commit()
    session.refresh(org)
    return org


def activate_token_pack(
    session: Session,
    org_id: str,
    token_type: str,
    tokens: int,
    payment_id: Optional[str] = None,
) -> int:
    """Credit purchased top-up tokens.
    Does NOT touch plan or monthly usage!
    """
    now = utc_now()
    expires_at = now + timedelta(days=365)
    bucket = "autofix" if token_type == "topup_autofix" else "pack"
    idemp_key = (
        f"pack:{payment_id}" if payment_id else f"pack:{org_id}:{uuid.uuid4().hex[:10]}"
    )

    record_ledger_entry(
        session=session,
        org_id=org_id,
        bucket=bucket,
        delta=tokens,
        reason="pack",
        ref_type="payment" if payment_id else "admin",
        ref_id=payment_id,
        idempotency_key=idemp_key,
        expires_at=expires_at,
    )

    balances = get_ledger_balances(session, org_id)
    return balances["autofix"] if bucket == "autofix" else balances["pack"]
