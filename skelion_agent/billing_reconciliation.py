"""Deterministic billing math and local ledger reconciliation checks."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlmodel import Session, select

from skelion_agent.models import (
    CreditLedger,
    Invoice,
    Payment,
    PaymentOrder,
    Refund,
)


def calculate_proration(
    current_amount_paise: int,
    replacement_amount_paise: int,
    period_start: date,
    period_end: date,
    change_date: date,
) -> int:
    """Return the signed credit/debit for a mid-period plan change."""
    total_days = (period_end - period_start).days
    remaining_days = max(0, (period_end - change_date).days)
    if total_days <= 0:
        raise ValueError("billing period must contain at least one day")
    delta = Decimal(replacement_amount_paise - current_amount_paise)
    return int(
        (delta * Decimal(remaining_days) / Decimal(total_days)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def reconcile_billing(session: Session, org_id: str) -> dict:
    """Check payment/order/invoice/ledger invariants without mutating customer data."""
    orders = session.exec(
        select(PaymentOrder).where(PaymentOrder.org_id == org_id)
    ).all()
    paid_orders = [order for order in orders if order.status == "paid"]
    payments = session.exec(
        select(Payment).where(Payment.payment_order_id.in_([o.id for o in paid_orders]))
    ).all() if paid_orders else []
    invoices = session.exec(select(Invoice).where(Invoice.org_id == org_id)).all()
    ledger = session.exec(
        select(CreditLedger).where(CreditLedger.org_id == org_id)
    ).all()

    payment_order_ids = {payment.payment_order_id for payment in payments}
    invoice_payment_ids = {invoice.payment_id for invoice in invoices if invoice.payment_id}
    findings = []
    for order in paid_orders:
        if order.id not in payment_order_ids:
            findings.append({"type": "paid_order_without_payment", "order_id": order.id})
    for payment in payments:
        if payment.id not in invoice_payment_ids:
            findings.append({"type": "payment_without_invoice", "payment_id": payment.id})
        refunds = session.exec(
            select(Refund).where(Refund.payment_id == payment.id)
        ).all()
        refunded = sum(refund.amount_paise for refund in refunds)
        if refunded > payment.amount_paise:
            findings.append(
                {
                    "type": "refund_exceeds_payment",
                    "payment_id": payment.id,
                    "refunded_paise": refunded,
                    "payment_paise": payment.amount_paise,
                }
            )
    for invoice in invoices:
        if invoice.amount_paise < 0:
            findings.append({"type": "negative_invoice", "invoice_id": invoice.id})

    return {
        "organization_id": org_id,
        "status": "ok" if not findings else "attention_required",
        "paid_orders": len(paid_orders),
        "payments": len(payments),
        "invoices": len(invoices),
        "ledger_entries": len(ledger),
        "findings": findings,
    }
