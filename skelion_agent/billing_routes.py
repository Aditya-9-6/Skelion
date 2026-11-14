# skelion_agent/billing_routes.py – Razorpay Billing, Quota Refills & Custom Token Purchase

"""Provides billing endpoints:
* ``GET /v1/billing/plan`` – retrieve current plan, prices, and limits status.
* ``POST /v1/billing/checkout`` – create subscription or custom token top-up order.
* ``POST /v1/billing/webhook`` – handle verified Razorpay webhook events to safely credit tokens.
"""

import json
import os
import uuid
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from skelion_agent.auth_routes import get_org_from_jwt, require_member_org
from skelion_agent.database import get_db, get_engine
from skelion_agent.models import (
    Organization,
    TransactionRecord,
    PaymentOrder,
    Payment,
    Refund,
    WebhookEvent,
    Invoice,
    Alert,
    utc_now,
    Membership,
)
from skelion_agent.plan_config import PLAN_DEFINITIONS, ADDONS
from skelion_agent.razorpay_service import (
    create_order,
    verify_payment_signature,
    verify_signature,
)
from skelion_agent.limits_service import get_token_status
from skelion_agent.credit_ledger import (
    activate_plan_period,
    activate_token_pack,
)
from skelion_agent.billing_reconciliation import reconcile_billing
from skelion_agent.config import settings

router = APIRouter(prefix="/v1/billing", tags=["Billing & Subscriptions"])


def _require_writable_region() -> None:
    if os.getenv("SKELION_READ_ONLY", "false").lower() == "true":
        raise HTTPException(status_code=503, detail="This deployment region is read-only")

# Pocket-Friendly Competitive Pricing Model:
# 1 Universal Coding Token = ₹0.25 (Super accessible for students & indie devs, 60%-92% gross margin)
# 1,000 Skelion Autofix Tokens = ₹10.00 (₹0.010 per token, 96% gross margin)
INR_PER_CODING_TOKEN = 0.25
INR_PER_AUTOFIX_TOKEN = 0.010  # ₹10.00 per 1,000 tokens


@router.get("/reconciliation")
def billing_reconciliation(
    org: Organization = Depends(require_member_org("owner", "admin", "billing")),
    db: Session = Depends(get_db),
):
    """Return local billing invariant findings for operator/customer support use."""
    return reconcile_billing(db, org.id)


@router.get("/invoices")
def list_invoices(
    org: Organization = Depends(require_member_org("owner", "admin", "billing")),
    db: Session = Depends(get_db),
):
    invoices = db.exec(
        select(Invoice)
        .where(Invoice.org_id == org.id)
        .order_by(Invoice.issued_at.desc())
    ).all()
    return {
        "invoices": [
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "payment_id": invoice.payment_id,
                "amount_paise": invoice.amount_paise,
                "gst_paise": invoice.gst_paise,
                "issued_at": invoice.issued_at.isoformat(),
            }
            for invoice in invoices
        ]
    }


@router.get("/seats")
def billing_seats(
    org: Organization = Depends(require_member_org("owner", "admin", "billing")),
    db: Session = Depends(get_db),
):
    members = db.exec(select(Membership).where(Membership.org_id == org.id)).all()
    return {
        "organization_id": org.id,
        "seat_count": len(members),
        "billable_roles": ["owner", "admin", "developer", "viewer", "billing"],
        "members_by_role": {
            role: sum(1 for member in members if member.role == role)
            for role in ["owner", "admin", "developer", "viewer", "billing"]
        },
    }


class TopUpCalculateRequest(BaseModel):
    token_type: str  # "coding" or "autofix"
    amount_inr: float


@router.get("/plan")
async def get_plan(org: Organization = Depends(require_member_org("owner", "admin", "developer", "viewer", "billing"))):
    """Return plan, Antigravity-style token status, and available 24/7 loop add-ons."""
    limits = get_token_status(org)
    return {
        "plan": org.plan,
        "limits": limits,
        "token_rates": {
            "coding_token_inr": INR_PER_CODING_TOKEN,
            "autofix_token_inr": INR_PER_AUTOFIX_TOKEN,
        },
        "available_plans": [
            {
                "id": k,
                "name": k.capitalize(),
                "price": v["price"],
                "quota": v["quota"],
                "active": org.plan == k,
            }
            for k, v in PLAN_DEFINITIONS.items()
        ],
        "addons": {
            k: {
                **v,
                "active": getattr(org, f"addon_{k}", False),
            }
            for k, v in ADDONS.items()
        },
    }


@router.get("/addons")
async def get_addons(org: Organization = Depends(require_member_org("owner", "admin", "developer", "viewer", "billing"))):
    """Return available 24/7 autonomous loop add-ons and activation status."""
    return {
        "addons": [
            {
                **addon,
                "active": getattr(org, f"addon_{addon['id']}", False),
            }
            for addon in ADDONS.values()
        ]
    }


@router.api_route("/calculate-tokens", methods=["GET", "POST"])
def calculate_tokens_for_price(
    token_type: str = "coding",
    amount_inr: float = 0.0,
    req: Optional[TopUpCalculateRequest] = None,
):
    """When user enters an amount in INR, return the exact equivalent tokens with 25% margin."""
    t_type = req.token_type if (req and req.amount_inr > 0) else token_type
    amt = req.amount_inr if (req and req.amount_inr > 0) else amount_inr

    if amt <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    if t_type == "autofix":
        tokens = int(amt / INR_PER_AUTOFIX_TOKEN)
        return {
            "token_type": "autofix",
            "amount_inr": amt,
            "tokens_granted": tokens,
            "description": f"{tokens:,} Skelion Autofix Tokens (Zero time limits, never expires)",
        }
    elif t_type == "coding":
        tokens = int(amt / INR_PER_CODING_TOKEN)
        return {
            "token_type": "coding",
            "amount_inr": amt,
            "tokens_granted": tokens,
            "description": f"{tokens:,} Universal Coding Tokens (Unthrottled top-up pool)",
        }
    else:
        raise HTTPException(
            status_code=400, detail="Invalid token_type. Must be 'coding' or 'autofix'"
        )


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/checkout")
async def checkout(
    plan: str = "pro",
    token_type: str = "plan",  # "plan", "topup_coding", or "topup_autofix"
    period: str = "monthly",  # "monthly" or "annual"
    custom_amount_inr: float = 0.0,
    org: Organization = Depends(require_member_org("owner", "admin", "billing")),
    db: Session = Depends(get_db),
):
    """Create server-validated PaymentOrder and Razorpay order (Billing v2)."""
    _require_writable_region()
    tokens_granted = 0
    item_name = ""
    amount_paise = 0

    if token_type == "plan":
        if plan not in PLAN_DEFINITIONS:
            raise HTTPException(status_code=400, detail="Invalid plan name")
        base_price = PLAN_DEFINITIONS[plan]["price"]
        if period == "annual":
            base_price = base_price * 10  # 2 months free
        amount_paise = int(base_price * 100)
        item_name = f"Plan Pass ({period.capitalize()}): {plan.upper()}"
        tokens_granted = PLAN_DEFINITIONS[plan]["quota"]
    elif token_type == "topup_autofix":
        if custom_amount_inr < 50:
            raise HTTPException(status_code=400, detail="Minimum top-up is ₹50")
        amount_paise = int(custom_amount_inr * 100)
        tokens_granted = int(custom_amount_inr / INR_PER_AUTOFIX_TOKEN)
        item_name = f"Skelion Autofix Pack: {tokens_granted:,} Tokens"
    elif token_type == "topup_coding":
        if custom_amount_inr < 50:
            raise HTTPException(status_code=400, detail="Minimum top-up is ₹50")
        amount_paise = int(custom_amount_inr * 100)
        tokens_granted = int(custom_amount_inr / INR_PER_CODING_TOKEN)
        item_name = f"Universal Coding Pack: {tokens_granted:,} Tokens"
    elif token_type in ["pack", "credit_pack"]:
        from skelion_agent.plan_config import CREDIT_PACKS

        pack_key = plan.lower() if plan in CREDIT_PACKS else "medium"
        pack_info = CREDIT_PACKS[pack_key]
        amount_paise = int(pack_info["price_inr"] * 100)
        tokens_granted = pack_info["credits"]
        item_name = f"Credit Pack: {pack_info['name']} ({tokens_granted:,} Credits)"
    elif token_type in ["addon", "addon_autonomous_dev_loop", "addon_reverse_proxy_loop"] or plan in ADDONS:
        if plan in ADDONS:
            addon_key = plan
        elif "autonomous" in token_type:
            addon_key = "autonomous_dev_loop"
        elif "reverse_proxy" in token_type:
            addon_key = "reverse_proxy_loop"
        else:
            raise HTTPException(status_code=400, detail="Invalid addon name")
        addon_info = ADDONS[addon_key]
        base_price = addon_info["annual_price_inr"] if period == "annual" else addon_info["price_inr"]
        amount_paise = int(base_price * 100)
        tokens_granted = addon_info["credits"]
        item_name = f"Add-on ({period.capitalize()}): {addon_info['name']}"
    else:
        raise HTTPException(status_code=400, detail="Invalid token_type")

    # 1. Create internal PaymentOrder row first (expires in 30 minutes)
    expires_at = utc_now() + timedelta(minutes=30)
    order_row = PaymentOrder(
        org_id=org.id,
        user_id=org.owner_user_id or org.id,
        plan_id=plan if (token_type == "plan" or plan in ADDONS or token_type.startswith("addon")) else None,
        kind=token_type,
        amount_paise=amount_paise,
        currency="INR",
        status="created",
        expires_at=expires_at,
    )
    db.add(order_row)
    db.commit()
    db.refresh(order_row)

    # 2. Call Razorpay with receipt = our order_row.id
    short_receipt = order_row.id[:36]
    order_row.receipt = short_receipt
    rzp_order = create_order(amount=amount_paise, currency="INR", receipt=short_receipt)
    provider_order_id = rzp_order.get("id")
    if not provider_order_id:
        raise HTTPException(
            status_code=502, detail="Payment provider returned no order identifier"
        )
    order_row.provider_order_id = provider_order_id
    db.add(order_row)

    # 3. Mirror in TransactionRecord for existing Admin UI
    tx = TransactionRecord(
        org_id=org.id,
        order_id=provider_order_id,
        category=token_type,
        item_name=item_name,
        amount_inr=amount_paise / 100.0,
        tokens_granted=tokens_granted,
        status="created",
    )
    db.add(tx)
    db.commit()

    return {
        "order_id": provider_order_id,
        "payment_order_id": order_row.id,
        "amount": amount_paise,
        "currency": "INR",
        "key_id": rzp_order.get("key_id") or settings.RAZORPAY_KEY_ID,
        "receipt": short_receipt,
    }


class InstantTopUpRequest(BaseModel):
    token_type: str = "autofix"  # "autofix" or "coding"
    amount_inr: float = 100.0


@router.post("/topup-instant")
async def instant_topup(
    req: InstantTopUpRequest,
    org: Organization = Depends(require_member_org("owner", "admin", "billing")),
    db: Session = Depends(get_db),
):
    """Credit top-up tokens instantly for local development and live demonstrations.
    ₹100 gives exactly 10,000 Autofix Tokens (40 complete replay-verified bug fixes).
    """
    _require_writable_region()
    if req.amount_inr <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    if req.token_type == "autofix":
        tokens = int(req.amount_inr / INR_PER_AUTOFIX_TOKEN)
        activate_token_pack(
            session=db,
            org_id=org.id,
            token_type="topup_autofix",
            tokens=tokens,
            payment_id=f"pay_instant_{uuid.uuid4().hex[:8]}",
        )
        remaining = max(0, org.autofix_tokens_total - org.autofix_tokens_used)
        return {
            "status": "credited",
            "token_type": "autofix",
            "amount_inr": req.amount_inr,
            "tokens_added": tokens,
            "autofix_tokens_remaining": remaining,
            "fixes_equivalent": tokens // 250,
            "description": f"Credited {tokens:,} Autofix Tokens! Equivalent to {tokens // 250} production bug fixes.",
        }
    elif req.token_type == "coding":
        tokens = int(req.amount_inr / INR_PER_CODING_TOKEN)
        activate_token_pack(
            session=db,
            org_id=org.id,
            token_type="topup_coding",
            tokens=tokens,
            payment_id=f"pay_instant_{uuid.uuid4().hex[:8]}",
        )
        return {
            "status": "credited",
            "token_type": "coding",
            "amount_inr": req.amount_inr,
            "tokens_added": tokens,
            "description": f"Credited {tokens:,} Universal Coding Tokens!",
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid token_type")


class InstantAddonRequest(BaseModel):
    addon_id: str = "autonomous_dev_loop"  # "autonomous_dev_loop" or "reverse_proxy_loop"
    active: bool = True


@router.post("/addon-instant")
async def instant_addon(
    req: InstantAddonRequest,
    org: Organization = Depends(require_member_org("owner", "admin", "billing")),
    db: Session = Depends(get_db),
):
    """Enable or disable 24/7 loop add-on instantly and credit tokens."""
    _require_writable_region()
    if req.addon_id not in ADDONS:
        raise HTTPException(status_code=400, detail="Invalid addon_id. Choose 'autonomous_dev_loop' or 'reverse_proxy_loop'")

    if req.addon_id == "autonomous_dev_loop":
        org.addon_autonomous_dev_loop = req.active
    elif req.addon_id == "reverse_proxy_loop":
        org.addon_reverse_proxy_loop = req.active

    db.add(org)
    tokens_credited = 0
    if req.active:
        tokens_credited = ADDONS[req.addon_id]["credits"]
        activate_token_pack(
            session=db,
            org_id=org.id,
            token_type="topup_autofix",
            tokens=tokens_credited,
            payment_id=f"addon_instant_{uuid.uuid4().hex[:8]}",
        )

    db.commit()
    db.refresh(org)
    return {
        "status": "activated" if req.active else "deactivated",
        "addon_id": req.addon_id,
        "name": ADDONS[req.addon_id]["name"],
        "active": req.active,
        "tokens_credited": tokens_credited,
        "description": f"{ADDONS[req.addon_id]['name']} {'enabled with ' + str(tokens_credited) + ' tokens' if req.active else 'disabled'}.",
    }


@router.post("/verify")
def verify_payment(req: VerifyPaymentRequest, db: Session = Depends(get_db)):
    """Fast-path client signature verification with idempotent activation."""
    if not verify_payment_signature(
        req.razorpay_order_id,
        req.razorpay_payment_id,
        req.razorpay_signature,
    ):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    order = db.exec(
        select(PaymentOrder).where(
            PaymentOrder.provider_order_id == req.razorpay_order_id
        )
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Payment order not found")

    if order.status == "paid":
        return {"status": "already_activated", "order_id": order.provider_order_id}

    # Activate
    order.status = "paid"
    db.add(order)

    # Insert Payment record
    payment = Payment(
        payment_order_id=order.id,
        provider_payment_id=req.razorpay_payment_id,
        amount_paise=order.amount_paise,
        currency="INR",
        status="captured",
    )
    db.add(payment)

    # Insert Invoice
    inv_num = f"INV-{utc_now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    invoice = Invoice(
        invoice_number=inv_num,
        org_id=order.org_id,
        payment_id=payment.id,
        amount_paise=order.amount_paise,
    )
    db.add(invoice)

    # Activate entitlements via append-only ledger
    if order.kind == "plan":
        activate_plan_period(
            session=db,
            org_id=order.org_id,
            plan_id=order.plan_id or "pro",
            payment_id=req.razorpay_payment_id,
        )
    elif order.kind in ("topup_coding", "topup_autofix"):
        tokens = int(
            order.amount_paise
            / 100
            / (
                INR_PER_AUTOFIX_TOKEN
                if order.kind == "topup_autofix"
                else INR_PER_CODING_TOKEN
            )
        )
        activate_token_pack(
            session=db,
            org_id=order.org_id,
            token_type=order.kind,
            tokens=tokens,
            payment_id=req.razorpay_payment_id,
        )
    elif order.kind.startswith("addon") or (order.plan_id and order.plan_id in ADDONS):
        addon_key = order.plan_id if (order.plan_id and order.plan_id in ADDONS) else ("autonomous_dev_loop" if "autonomous" in order.kind else "reverse_proxy_loop")
        org = db.get(Organization, order.org_id)
        if org:
            if addon_key == "autonomous_dev_loop":
                org.addon_autonomous_dev_loop = True
            elif addon_key == "reverse_proxy_loop":
                org.addon_reverse_proxy_loop = True
            db.add(org)
        addon_info = ADDONS.get(addon_key, {})
        tokens = addon_info.get("credits", 5000 if "autonomous" in addon_key else 2500)
        activate_token_pack(
            session=db,
            org_id=order.org_id,
            token_type="topup_autofix",
            tokens=tokens,
            payment_id=req.razorpay_payment_id,
        )

    db.commit()
    return {
        "status": "activated",
        "order_id": order.provider_order_id,
        "invoice_number": inv_num,
    }


@router.post("/webhook")
async def webhook(request: Request):
    """Handle verified Razorpay webhook events to safely credit purchased tokens and plans (v2)."""
    raw_payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    event_id = request.headers.get(
        "X-Razorpay-Event-Id", f"evt_{uuid.uuid4().hex[:12]}"
    )

    if not signature:
        raise HTTPException(
            status_code=400, detail="Missing X-Razorpay-Signature header"
        )

    # Constant-time signature verification
    if not verify_signature(raw_payload, signature):
        raise HTTPException(status_code=400, detail="Invalid HMAC webhook signature")

    engine = get_engine()
    with Session(engine) as db:
        # Deduplication check on X-Razorpay-Event-Id
        existing_event = db.exec(
            select(WebhookEvent).where(
                WebhookEvent.provider == "razorpay",
                WebhookEvent.event_id == event_id,
            )
        ).first()

        if existing_event and existing_event.status in ("processed", "duplicate"):
            return {"status": "duplicate", "reason": "duplicate_event_already_processed"}

        # Parse JSON payload
        data = json.loads(raw_payload.decode("utf-8"))
        event_type = data.get("event", "unknown")

        whe = existing_event or WebhookEvent(
            provider="razorpay",
            event_id=event_id,
            event_type=event_type,
            payload_json=raw_payload.decode("utf-8"),
            status="received",
        )
        db.add(whe)

        if event_type in ("payment.refunded", "refund.processed"):
            ref_ent = data.get("payload", {}).get("refund", {}).get("entity", {})
            if not ref_ent:
                ref_ent = data.get("payload", {}).get("payment", {}).get("entity", {})
            provider_refund_id = ref_ent.get("id")
            pay_id = ref_ent.get("payment_id")
            rfnd_amt = ref_ent.get("amount", 0)
            rfnd_status = ref_ent.get("status", "processed")
            rfnd_reason = ref_ent.get("notes", {}).get("reason", "refund")
            if not provider_refund_id or not pay_id:
                whe.status = "failed"
                whe.error = "Refund event omitted provider refund/payment identifiers"
                db.add(whe)
                db.commit()
                raise HTTPException(status_code=422, detail=whe.error)

            existing_refund = db.exec(
                select(Refund).where(
                    Refund.provider_refund_id == provider_refund_id
                )
            ).first()
            if existing_refund:
                whe.status = "duplicate"
                db.add(whe)
                db.commit()
                return {"status": "duplicate", "refund_id": existing_refund.id}

            pay_record = db.exec(
                select(Payment).where(
                    (Payment.id == pay_id) | (Payment.provider_payment_id == pay_id)
                )
            ).first()
            if not pay_record:
                whe.status = "failed"
                whe.error = "Refund references an unknown payment"
                db.add(whe)
                db.commit()
                raise HTTPException(status_code=422, detail=whe.error)

            refund = Refund(
                id=f"ref_{uuid.uuid4().hex[:10]}",
                payment_id=pay_record.id,
                provider_refund_id=provider_refund_id,
                amount_paise=rfnd_amt,
                status=rfnd_status,
                reason=rfnd_reason,
            )
            db.add(refund)
            pay_record.status = "refunded"
            order = db.get(PaymentOrder, pay_record.payment_order_id)
            if order:
                order.status = "refunded"
                db.add(order)
            whe.status = "processed"
            whe.processed_at = utc_now()
            db.add(whe)
            db.commit()
            return {"status": "processed", "event_id": event_id, "refund_id": refund.id}

        if event_type not in ("payment.captured", "order.paid", "subscription.charged"):
            whe.status = "ignored"
            db.add(whe)
            db.commit()
            return {"status": "ignored", "event": event_type}

        payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})
        order_entity = data.get("payload", {}).get("order", {}).get("entity", {})
        entity = payment_entity or order_entity
        provider_order_id = entity.get("order_id") or order_entity.get("id")
        provider_payment_id = payment_entity.get("id")
        amount_paid = entity.get("amount", 0)
        if not provider_payment_id or not amount_paid:
            whe.status = "failed"
            whe.error = "Payment event omitted provider payment or amount"
            db.add(whe)
            db.commit()
            raise HTTPException(status_code=422, detail=whe.error)

        # Look up authoritative PaymentOrder
        order = (
            db.exec(
                select(PaymentOrder).where(
                    PaymentOrder.provider_order_id == provider_order_id
                )
            ).first()
            if provider_order_id
            else None
        )

        if order and order.status == "paid":
            return {"status": "duplicate", "reason": "order_already_paid"}

        if order:
            if order.amount_paise != amount_paid:
                whe.status = "flagged"
                whe.error = f"Payment amount mismatch: expected {order.amount_paise}, got {amount_paid}"
                alert = Alert(
                    org_id=order.org_id,
                    alert_type="amount_mismatch",
                    message=f"Payment amount mismatch for order {order.id}: expected {order.amount_paise}, got {amount_paid}",
                )
                db.add(alert)
                db.add(whe)
                db.commit()
                return {"status": "flagged", "reason": "amount_mismatch"}

        if order and order.status != "paid":
            order.status = "paid"
            db.add(order)

            # Record Payment
            payment = Payment(
                payment_order_id=order.id,
                provider_payment_id=provider_payment_id,
                amount_paise=amount_paid,
                currency="INR",
                status="captured",
            )
            db.add(payment)

            # Record Invoice
            inv_num = f"INV-{utc_now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
            invoice = Invoice(
                invoice_number=inv_num,
                org_id=order.org_id,
                payment_id=payment.id,
                amount_paise=amount_paid,
            )
            db.add(invoice)

            # Apply Entitlements
            if order.kind == "plan":
                activate_plan_period(
                    session=db,
                    org_id=order.org_id,
                    plan_id=order.plan_id or "pro",
                    payment_id=provider_payment_id,
                )
            elif order.kind in ("topup_coding", "topup_autofix"):
                tokens = int(
                    order.amount_paise
                    / 100
                    / (
                        INR_PER_AUTOFIX_TOKEN
                        if order.kind == "topup_autofix"
                        else INR_PER_CODING_TOKEN
                    )
                )
                activate_token_pack(
                    session=db,
                    org_id=order.org_id,
                    token_type=order.kind,
                    tokens=tokens,
                    payment_id=provider_payment_id,
                )
            elif order.kind.startswith("addon") or (order.plan_id and order.plan_id in ADDONS):
                addon_key = order.plan_id if (order.plan_id and order.plan_id in ADDONS) else ("autonomous_dev_loop" if "autonomous" in order.kind else "reverse_proxy_loop")
                org = db.get(Organization, order.org_id)
                if org:
                    if addon_key == "autonomous_dev_loop":
                        org.addon_autonomous_dev_loop = True
                    elif addon_key == "reverse_proxy_loop":
                        org.addon_reverse_proxy_loop = True
                    db.add(org)
                addon_info = ADDONS.get(addon_key, {})
                tokens = addon_info.get("credits", 5000 if "autonomous" in addon_key else 2500)
                activate_token_pack(
                    session=db,
                    org_id=order.org_id,
                    token_type="topup_autofix",
                    tokens=tokens,
                    payment_id=provider_payment_id,
                )
        else:
            # Fallback for legacy receipt format {org_id}:{kind}:{value}
            receipt = entity.get("receipt", "")
            parts = receipt.split(":")
            if len(parts) >= 3:
                org_id = parts[0]
                category = parts[1]
                value = parts[2]
                org = db.get(Organization, org_id)
                if org:
                    if category == "plan":
                        activate_plan_period(
                            db,
                            org_id=org.id,
                            plan_id=value,
                            payment_id=provider_payment_id,
                        )
                    elif category in ("topup_coding", "topup_autofix"):
                        tokens = int(value) if value.isdigit() else 1000
                        activate_token_pack(
                            db,
                            org_id=org.id,
                            token_type=category,
                            tokens=tokens,
                            payment_id=provider_payment_id,
                        )

        whe.status = "processed"
        whe.processed_at = utc_now()
        db.add(whe)
        db.commit()

    return {"status": "processed", "event_id": event_id}
