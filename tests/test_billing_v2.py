# tests/test_billing_v2.py — Acceptance Tests for Billing v2 & Append-Only Credit Ledger

import pytest
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, SQLModel, create_engine

from skelion_agent.models import Organization
from skelion_agent.credit_ledger import (
    record_ledger_entry,
    get_ledger_balances,
    activate_plan_period,
    activate_token_pack,
)


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        org = Organization(
            id="org_test_1",
            name="Test Company",
            token="skl_live_test123456789",
            plan="pilot",
            credits_total=100,
            credits_used=0,
            autofix_tokens_total=50000,
        )
        session.add(org)
        session.commit()
        yield session


def test_append_only_ledger_and_idempotency(test_db):
    org_id = "org_test_1"

    # 1. First grant: 500 credits
    entry1, is_new1 = record_ledger_entry(
        session=test_db,
        org_id=org_id,
        bucket="allowance",
        delta=500,
        reason="plan_period",
        idempotency_key="idemp_evt_001",
    )
    assert is_new1 is True
    assert entry1.delta == 500

    bal = get_ledger_balances(test_db, org_id)
    assert bal["allowance"] == 500

    # 2. Duplicate webhook event with SAME idempotency key
    entry2, is_new2 = record_ledger_entry(
        session=test_db,
        org_id=org_id,
        bucket="allowance",
        delta=500,
        reason="plan_period",
        idempotency_key="idemp_evt_001",
    )
    assert is_new2 is False
    assert entry2.id == entry1.id

    # Balance MUST NOT be duplicated
    bal_after = get_ledger_balances(test_db, org_id)
    assert bal_after["allowance"] == 500


def test_pack_purchase_leaves_monthly_allowance_intact(test_db):
    org_id = "org_test_1"

    # Grant 1,000 monthly allowance
    activate_plan_period(test_db, org_id=org_id, plan_id="starter", period="monthly")

    # Customer uses 200 monthly tokens
    record_ledger_entry(
        session=test_db,
        org_id=org_id,
        bucket="allowance",
        delta=-200,
        reason="usage",
        idempotency_key="usage_001",
    )

    bal1 = get_ledger_balances(test_db, org_id)
    assert bal1["allowance"] == 600  # 800 - 200 (Developer / Starter tier)

    # Customer buys a pack of 500 top-up tokens
    activate_token_pack(
        test_db,
        org_id=org_id,
        token_type="topup_coding",
        tokens=500,
        payment_id="pay_test_pack",
    )

    bal2 = get_ledger_balances(test_db, org_id)
    assert bal2["allowance"] == 600  # Monthly allowance usage untouched!
    assert bal2["pack"] == 500  # Dedicated unthrottled pack pool
    assert bal2["total_coding"] == 1100


def test_plan_renewal_extends_period(test_db):
    org_id = "org_test_1"
    now = datetime.now(timezone.utc)

    # Initial monthly activation
    org = activate_plan_period(test_db, org_id=org_id, plan_id="pro", period="monthly")
    first_end = org.plan_period_end

    # Renew plan before expiry
    org_renewed = activate_plan_period(
        test_db,
        org_id=org_id,
        plan_id="pro",
        period="monthly",
        payment_id="pay_renew_01",
    )

    # Expiry must extend by 30 days from the previous period end
    expected_end = first_end + timedelta(days=30)
    assert abs((org_renewed.plan_period_end - expected_end).total_seconds()) < 5
