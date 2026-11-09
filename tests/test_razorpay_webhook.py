import copy
import hashlib
import hmac
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

pytestmark = pytest.mark.integration

from skelion_agent.control_plane import app
import skelion_agent.billing_routes as billing_routes
from skelion_agent.database import get_engine, init_db
from skelion_agent.models import (
    Alert,
    CreditLedger,
    Invoice,
    Organization,
    Payment,
    PaymentOrder,
    Refund,
    WebhookEvent,
)
from skelion_agent.config import settings


SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "rzp_webhook_secret_placeholder")

BASE_PAYLOAD = {
    "event_id": "evt_base_template",
    "event": "payment.captured",
    "event_type": "payment.captured",
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_base_123",
                "order_id": "order_base_123",
                "amount": 100000,
                "currency": "INR",
                "status": "captured",
            }
        }
    },
    "created_at": 1700000000,
}


def generate_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def make_payload(event_id=None, order_id=None, amount=100000, event_type="payment.captured"):
    """Create a fully deep-copied test payload with a fresh UUID event_id unless specified."""
    p = copy.deepcopy(BASE_PAYLOAD)
    p["event_id"] = event_id if event_id is not None else f"evt_{uuid.uuid4().hex}"
    p["event"] = event_type
    p["event_type"] = event_type
    p["created_at"] = int(datetime.now(timezone.utc).timestamp())
    ent = p["payload"]["payment"]["entity"]
    ent["id"] = f"pay_{uuid.uuid4().hex[:10]}"
    if order_id is not None:
        ent["order_id"] = order_id
    ent["amount"] = amount
    return p


def post_webhook(client: TestClient, payload: dict, secret: str = SECRET, signature: str = None):
    body = json.dumps(payload).encode("utf-8")
    sig = signature if signature is not None else generate_signature(body, secret)
    headers = {
        "content-type": "application/json",
        "X-Razorpay-Event-Id": payload.get("event_id", f"evt_{uuid.uuid4().hex[:12]}"),
        "X-Razorpay-Signature": sig,
    }
    return client.post("/v1/billing/webhook", data=body, headers=headers)


@pytest.fixture(scope="module")
def test_client():
    client = TestClient(app, raise_server_exceptions=False)
    yield client


@pytest.fixture(autouse=True)
def clean_db():
    engine = get_engine()
    init_db(engine)
    with Session(engine) as session:
        if engine.dialect.name == "postgresql":
            session.exec(
                "TRUNCATE TABLE payments, invoices, credit_ledger, webhook_events, payment_orders, refunds, alerts, audit_log, organizations RESTART IDENTITY CASCADE"
            )
        else:
            session.exec("TRUNCATE TABLE payments")
            session.exec("TRUNCATE TABLE invoices")
            session.exec("TRUNCATE TABLE credit_ledger")
            session.exec("TRUNCATE TABLE webhook_events")
            session.exec("TRUNCATE TABLE payment_orders")
            session.exec("TRUNCATE TABLE refunds")
            session.exec("TRUNCATE TABLE alerts")
            session.exec("TRUNCATE TABLE audit_log")
            session.exec("TRUNCATE TABLE organizations")
        session.commit()
    yield
    engine.dispose()


def setup_org_and_order(session: Session, amount_paise: int = 100000, kind: str = "plan"):
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    org = Organization(
        id=org_id,
        name="Test Org",
        token=f"skl_live_{uuid.uuid4().hex}",
        plan="pilot",
        credits_total=100,
        credits_used=0,
    )
    session.add(org)
    session.commit()

    provider_order_id = f"order_{uuid.uuid4().hex[:10]}"
    order_id = f"po_{uuid.uuid4().hex[:10]}"
    order = PaymentOrder(
        id=order_id,
        org_id=org_id,
        plan_id="pro",
        kind=kind,
        amount_paise=amount_paise,
        currency="INR",
        provider="razorpay",
        provider_order_id=provider_order_id,
        status="created",
    )
    session.add(order)
    session.commit()
    return org_id, order_id, provider_order_id


def test_duplicate_x5(test_client):
    """Assert duplicate x5 results in exactly 200 OKs, but only 1 payment, 1 invoice, 1 credit grant."""
    engine = get_engine()
    with Session(engine) as session:
        org_id, order_id, provider_order_id = setup_org_and_order(session, amount_paise=100000, kind="plan")

    shared_event_id = f"evt_dup_{uuid.uuid4().hex}"
    payload = make_payload(
        event_id=shared_event_id,
        order_id=provider_order_id,
        amount=100000,
        event_type="payment.captured",
    )

    # 1st call: processed
    resp1 = post_webhook(test_client, copy.deepcopy(payload))
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "processed"

    # 4 duplicate calls: duplicate status, HTTP 200
    for _ in range(4):
        resp_dup = post_webhook(test_client, copy.deepcopy(payload))
        assert resp_dup.status_code == 200
        assert resp_dup.json()["status"] == "duplicate"

    # Assert exact DB state
    with Session(engine) as session:
        payments = session.exec(
            select(Payment).where(Payment.payment_order_id == order_id)
        ).all()
        assert len(payments) == 1

        invoices = session.exec(
            select(Invoice).where(Invoice.org_id == org_id)
        ).all()
        assert len(invoices) == 1

        ledger_grants = session.exec(
            select(CreditLedger).where(
                CreditLedger.org_id == org_id,
                CreditLedger.reason == "plan_period",
            )
        ).all()
        assert len(ledger_grants) == 1

        webhook_events = session.exec(
            select(WebhookEvent).where(WebhookEvent.event_id == shared_event_id)
        ).all()
        assert len(webhook_events) == 1
        assert webhook_events[0].status == "processed"


def test_concurrency_two_deliveries(test_client):
    """Add concurrency test using threading to deliver same event twice, ensuring both return 200 and only 1 effect."""
    engine = get_engine()
    with Session(engine) as session:
        org_id, order_id, provider_order_id = setup_org_and_order(session, amount_paise=100000, kind="plan")

    shared_event_id = f"evt_conc_{uuid.uuid4().hex}"
    payload = make_payload(
        event_id=shared_event_id,
        order_id=provider_order_id,
        amount=100000,
        event_type="payment.captured",
    )

    def send_one():
        return post_webhook(test_client, copy.deepcopy(payload))

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(send_one)
        f2 = executor.submit(send_one)
        resp1 = f1.result()
        resp2 = f2.result()

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    statuses = {resp1.json()["status"], resp2.json()["status"]}
    assert "processed" in statuses
    assert "duplicate" in statuses

    with Session(engine) as session:
        payments = session.exec(
            select(Payment).where(Payment.payment_order_id == order_id)
        ).all()
        assert len(payments) == 1

        invoices = session.exec(
            select(Invoice).where(Invoice.org_id == org_id)
        ).all()
        assert len(invoices) == 1

        ledger_grants = session.exec(
            select(CreditLedger).where(
                CreditLedger.org_id == org_id,
                CreditLedger.reason == "plan_period",
            )
        ).all()
        assert len(ledger_grants) == 1


def test_failure_then_retry(test_client, monkeypatch):
    """Monkey-patch effect to raise once: 1st returns 5xx without recording event; retry returns 200 and applies effect."""
    engine = get_engine()
    with Session(engine) as session:
        org_id, order_id, provider_order_id = setup_org_and_order(session, amount_paise=100000, kind="plan")

    target_event_id = f"evt_retry_{uuid.uuid4().hex}"
    payload = make_payload(
        event_id=target_event_id,
        order_id=provider_order_id,
        amount=100000,
        event_type="payment.captured",
    )

    failed_once = False
    orig_activate = billing_routes.activate_plan_period

    def mock_activate(*args, **kwargs):
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise RuntimeError("Simulated transient failure in entitlement effect")
        return orig_activate(*args, **kwargs)

    monkeypatch.setattr(billing_routes, "activate_plan_period", mock_activate)

    # 1st call fails
    resp1 = post_webhook(test_client, copy.deepcopy(payload))
    assert resp1.status_code >= 500

    # Ensure nothing recorded in DB on failure
    with Session(engine) as session:
        whe_first = session.exec(
            select(WebhookEvent).where(WebhookEvent.event_id == target_event_id)
        ).all()
        assert len(whe_first) == 0

        payments_first = session.exec(
            select(Payment).where(Payment.payment_order_id == order_id)
        ).all()
        assert len(payments_first) == 0

        invoices_first = session.exec(
            select(Invoice).where(Invoice.org_id == org_id)
        ).all()
        assert len(invoices_first) == 0

    # Retry call succeeds
    resp2 = post_webhook(test_client, copy.deepcopy(payload))
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "processed"

    # DB now has exactly one recorded event and one applied effect
    with Session(engine) as session:
        whe_retry = session.exec(
            select(WebhookEvent).where(WebhookEvent.event_id == target_event_id)
        ).all()
        assert len(whe_retry) == 1
        assert whe_retry[0].status == "processed"

        payments_retry = session.exec(
            select(Payment).where(Payment.payment_order_id == order_id)
        ).all()
        assert len(payments_retry) == 1

        invoices_retry = session.exec(
            select(Invoice).where(Invoice.org_id == org_id)
        ).all()
        assert len(invoices_retry) == 1

        ledger_retry = session.exec(
            select(CreditLedger).where(
                CreditLedger.org_id == org_id,
                CreditLedger.reason == "plan_period",
            )
        ).all()
        assert len(ledger_retry) == 1


def test_wrong_amount(test_client):
    """Wrong amount test returns 200 with JSON status 'flagged', no entitlement granted, and alert row written."""
    engine = get_engine()
    with Session(engine) as session:
        org_id, order_id, provider_order_id = setup_org_and_order(session, amount_paise=100000, kind="plan")

    event_id = f"evt_wrong_amt_{uuid.uuid4().hex}"
    payload = make_payload(
        event_id=event_id,
        order_id=provider_order_id,
        amount=9999,
        event_type="payment.captured",
    )

    resp = post_webhook(test_client, copy.deepcopy(payload))
    assert resp.status_code == 200
    assert resp.json()["status"] == "flagged"

    with Session(engine) as session:
        payments = session.exec(
            select(Payment).where(Payment.payment_order_id == order_id)
        ).all()
        assert len(payments) == 0

        ledger_entries = session.exec(
            select(CreditLedger).where(CreditLedger.org_id == org_id)
        ).all()
        assert len(ledger_entries) == 0

        order_db = session.get(PaymentOrder, order_id)
        assert order_db.status != "paid"

        alerts = session.exec(
            select(Alert).where(Alert.org_id == org_id)
        ).all()
        assert len(alerts) >= 1
        assert "mismatch" in alerts[0].alert_type or "mismatch" in alerts[0].message.lower()

        whe = session.exec(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        ).first()
        assert whe is not None
        assert whe.status == "flagged"


def test_out_of_order_events(test_client):
    """Out-of-order test ensures later events (e.g. payment.failed after payment.captured) do not downgrade, and refunds before capture are handled safely."""
    engine = get_engine()
    with Session(engine) as session:
        org_id, order_id, provider_order_id = setup_org_and_order(session, amount_paise=100000, kind="plan")

    # Capture payment first
    event_id_cap = f"evt_order_cap_{uuid.uuid4().hex}"
    payload_cap = make_payload(
        event_id=event_id_cap,
        order_id=provider_order_id,
        amount=100000,
        event_type="payment.captured",
    )

    resp_cap = post_webhook(test_client, copy.deepcopy(payload_cap))
    assert resp_cap.status_code == 200
    assert resp_cap.json()["status"] == "processed"

    with Session(engine) as session:
        order_db = session.get(PaymentOrder, order_id)
        assert order_db.status == "paid"

    # Now deliver out-of-order payment.failed for same order: must not downgrade
    event_id_fail = f"evt_order_fail_{uuid.uuid4().hex}"
    payload_fail = make_payload(
        event_id=event_id_fail,
        order_id=provider_order_id,
        amount=100000,
        event_type="payment.failed",
    )
    resp_fail = post_webhook(test_client, copy.deepcopy(payload_fail))
    assert resp_fail.status_code == 200

    with Session(engine) as session:
        order_db_after = session.get(PaymentOrder, order_id)
        assert order_db_after.status == "paid"

    # Now test refund before capture is handled safely
    event_id_refund = f"evt_order_refund_{uuid.uuid4().hex}"
    refund_payload = {
        "event_id": event_id_refund,
        "event": "payment.refunded",
        "event_type": "payment.refunded",
        "payload": {
            "refund": {
                "entity": {
                    "id": f"rfnd_{uuid.uuid4().hex[:10]}",
                    "payment_id": f"pay_unseen_{uuid.uuid4().hex[:10]}",
                    "amount": 50000,
                    "status": "processed",
                    "notes": {"reason": "pre_capture_refund"},
                }
            }
        },
        "created_at": int(datetime.now(timezone.utc).timestamp()),
    }
    resp_ref = post_webhook(test_client, copy.deepcopy(refund_payload))
    assert resp_ref.status_code == 200

    with Session(engine) as session:
        whe_ref = session.exec(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id_refund)
        ).first()
        assert whe_ref is not None
        refunds = session.exec(select(Refund)).all()
        assert len(refunds) >= 1


def test_bad_signature(test_client):
    """Bad signature test returns 400 and writes nothing to DB."""
    engine = get_engine()
    event_id = f"evt_badsig_{uuid.uuid4().hex}"
    payload = make_payload(event_id=event_id, amount=100000)

    resp = post_webhook(
        test_client,
        copy.deepcopy(payload),
        secret="wrong_secret",
        signature="invalid_signature_hex_12345",
    )
    assert resp.status_code == 400

    with Session(engine) as session:
        whe = session.exec(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        ).all()
        assert len(whe) == 0

        payments = session.exec(select(Payment)).all()
        assert len(payments) == 0

        invoices = session.exec(select(Invoice)).all()
        assert len(invoices) == 0

        ledger = session.exec(select(CreditLedger)).all()
        assert len(ledger) == 0

        alerts = session.exec(select(Alert)).all()
        assert len(alerts) == 0


def create_test_org(org_id: str, name: str = "Test Org", plan: str = "pilot") -> Organization:
    engine = get_engine()
    with Session(engine, expire_on_commit=False) as session:
        existing = session.get(Organization, org_id)
        if existing:
            return existing
        org = Organization(
            id=org_id,
            name=name,
            token=f"tok_{org_id}",
            plan=plan,
            credits_total=1000,
            credits_used=0,
            autofix_tokens_total=50000,
            autofix_tokens_used=0,
        )
        session.add(org)
        session.commit()
        return org


def test_plan_endpoint(test_client):
    from skelion_agent.auth_routes import get_org_from_jwt
    create_test_org("org_plan_test", name="Plan Test Org", plan="pro")

    app.dependency_overrides[get_org_from_jwt] = lambda: create_test_org("org_plan_test", plan="pro")
    try:
        resp = test_client.get("/v1/billing/plan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "pro"
        assert "token_rates" in data
        assert "available_plans" in data
    finally:
        app.dependency_overrides.pop(get_org_from_jwt, None)


def test_calculate_tokens_endpoint(test_client):
    # GET with 0 amount
    r = test_client.get("/v1/billing/calculate-tokens?amount_inr=0")
    assert r.status_code == 400

    # GET with autofix
    r = test_client.get("/v1/billing/calculate-tokens?token_type=autofix&amount_inr=100")
    assert r.status_code == 200
    assert r.json()["token_type"] == "autofix"
    assert r.json()["tokens_granted"] == 10000

    # GET with coding
    r = test_client.get("/v1/billing/calculate-tokens?token_type=coding&amount_inr=100")
    assert r.status_code == 200
    assert r.json()["token_type"] == "coding"
    assert r.json()["tokens_granted"] == 400

    # GET with invalid token_type
    r = test_client.get("/v1/billing/calculate-tokens?token_type=unknown&amount_inr=100")
    assert r.status_code == 400

    # POST with body
    r = test_client.post("/v1/billing/calculate-tokens", json={"token_type": "coding", "amount_inr": 50})
    assert r.status_code == 200
    assert r.json()["tokens_granted"] == 200


def test_checkout_endpoint(test_client):
    from skelion_agent.auth_routes import get_org_from_jwt
    create_test_org("org_checkout_test", name="Checkout Test Org", plan="pilot")

    app.dependency_overrides[get_org_from_jwt] = lambda: create_test_org("org_checkout_test", plan="pilot")
    try:
        # Invalid plan
        r = test_client.post("/v1/billing/checkout?token_type=plan&plan=invalid_plan")
        assert r.status_code == 400

        # Valid plan monthly
        r = test_client.post("/v1/billing/checkout?token_type=plan&plan=pro&period=monthly")
        assert r.status_code == 200
        assert "order_id" in r.json()

        # Valid plan annual
        r = test_client.post("/v1/billing/checkout?token_type=plan&plan=pro&period=annual")
        assert r.status_code == 200

        # Topup autofix under min
        r = test_client.post("/v1/billing/checkout?token_type=topup_autofix&custom_amount_inr=20")
        assert r.status_code == 400

        # Topup autofix valid
        r = test_client.post("/v1/billing/checkout?token_type=topup_autofix&custom_amount_inr=100")
        assert r.status_code == 200

        # Topup coding under min
        r = test_client.post("/v1/billing/checkout?token_type=topup_coding&custom_amount_inr=10")
        assert r.status_code == 400

        # Topup coding valid
        r = test_client.post("/v1/billing/checkout?token_type=topup_coding&custom_amount_inr=100")
        assert r.status_code == 200

        # Credit pack
        r = test_client.post("/v1/billing/checkout?token_type=pack&plan=small")
        assert r.status_code == 200

        # Invalid token_type
        r = test_client.post("/v1/billing/checkout?token_type=invalid_type")
        assert r.status_code == 400
    finally:
        app.dependency_overrides.pop(get_org_from_jwt, None)


def test_topup_instant_endpoint(test_client):
    from skelion_agent.auth_routes import get_org_from_jwt
    create_test_org("org_instant_test", name="Instant Test Org", plan="pilot")

    app.dependency_overrides[get_org_from_jwt] = lambda: create_test_org("org_instant_test", plan="pilot")
    try:
        # Amount <= 0
        r = test_client.post("/v1/billing/topup-instant", json={"token_type": "autofix", "amount_inr": -5})
        assert r.status_code == 400

        # Autofix
        r = test_client.post("/v1/billing/topup-instant", json={"token_type": "autofix", "amount_inr": 100})
        assert r.status_code == 200
        assert r.json()["status"] == "credited"

        # Coding
        r = test_client.post("/v1/billing/topup-instant", json={"token_type": "coding", "amount_inr": 100})
        assert r.status_code == 200
        assert r.json()["status"] == "credited"

        # Invalid token type
        r = test_client.post("/v1/billing/topup-instant", json={"token_type": "bad_token", "amount_inr": 100})
        assert r.status_code == 400
    finally:
        app.dependency_overrides.pop(get_org_from_jwt, None)



def test_verify_payment_endpoint(test_client):
    engine = get_engine()
    orig_secret = settings.RAZORPAY_KEY_SECRET

    # Test signature failure when secret is non-placeholder
    settings.RAZORPAY_KEY_SECRET = "production_secret_key_123"
    try:
        r_sig = test_client.post("/v1/billing/verify", json={
            "razorpay_order_id": "order_test_sig",
            "razorpay_payment_id": "pay_test_sig",
            "razorpay_signature": "invalid_sig_abc"
        })
        assert r_sig.status_code == 400
    finally:
        settings.RAZORPAY_KEY_SECRET = orig_secret

    # 1. Order not found
    r = test_client.post("/v1/billing/verify", json={
        "razorpay_order_id": "order_non_existent",
        "razorpay_payment_id": "pay_test_123",
        "razorpay_signature": "dummy_sig"
    })
    assert r.status_code == 404

    # 2. Plan order activation
    with Session(engine) as session:
        org = Organization(id="org_verify_plan", name="Verify Plan Org", token="tok_verify_test", plan="pilot")
        session.add(org)
        po = PaymentOrder(
            id="po_verify_plan",
            org_id="org_verify_plan",
            user_id="user_1",
            provider_order_id="order_verify_plan_prov",
            kind="plan",
            plan_id="pro",
            amount_paise=9900,
            status="created"
        )
        session.add(po)
        session.commit()

    r = test_client.post("/v1/billing/verify", json={
        "razorpay_order_id": "order_verify_plan_prov",
        "razorpay_payment_id": "pay_verify_001",
        "razorpay_signature": "dummy_sig"
    })
    assert r.status_code == 200
    assert r.json()["status"] == "activated"

    # 3. Already activated
    r_dup = test_client.post("/v1/billing/verify", json={
        "razorpay_order_id": "order_verify_plan_prov",
        "razorpay_payment_id": "pay_verify_001",
        "razorpay_signature": "dummy_sig"
    })
    assert r_dup.status_code == 200
    assert r_dup.json()["status"] == "already_activated"

    # 4. Topup order activation
    with Session(engine) as session:
        po_topup = PaymentOrder(
            id="po_verify_topup",
            org_id="org_verify_plan",
            user_id="user_1",
            provider_order_id="order_verify_topup_prov",
            kind="topup_coding",
            amount_paise=5000,
            status="created"
        )
        session.add(po_topup)
        session.commit()

    r_topup = test_client.post("/v1/billing/verify", json={
        "razorpay_order_id": "order_verify_topup_prov",
        "razorpay_payment_id": "pay_verify_002",
        "razorpay_signature": "dummy_sig"
    })
    assert r_topup.status_code == 200
    assert r_topup.json()["status"] == "activated"


def test_webhook_edge_cases(test_client):
    engine = get_engine()
    # 1. Missing signature header
    r = test_client.post("/v1/billing/webhook", data=b"{}")
    assert r.status_code == 400

    # 2. Ignored event type
    evt_ignore = f"evt_ignore_{uuid.uuid4().hex}"
    payload_ignore = {"event": "dummy.event", "event_id": evt_ignore}
    r = post_webhook(test_client, payload_ignore)
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"

    # 3. Topup order via webhook
    with Session(engine) as session:
        org = Organization(id="org_wb_topup", name="WB Topup Org", token="tok_wb_topup", plan="pilot")
        session.add(org)
        po_topup = PaymentOrder(
            id="po_wb_topup",
            org_id="org_wb_topup",
            user_id="user_wb",
            provider_order_id="order_wb_topup_prov",
            kind="topup_autofix",
            amount_paise=10000,
            status="created"
        )
        session.add(po_topup)
        session.commit()

    evt_wb_topup = f"evt_topup_{uuid.uuid4().hex}"
    payload_topup = make_payload(event_id=evt_wb_topup, order_id="order_wb_topup_prov", amount=10000)
    r = post_webhook(test_client, payload_topup)
    assert r.status_code == 200
    assert r.json()["status"] == "processed"

    # 4. Duplicate webhook when order is already paid
    evt_dup_order = f"evt_dup_order_{uuid.uuid4().hex}"
    payload_dup = make_payload(event_id=evt_dup_order, order_id="order_wb_topup_prov", amount=10000)
    r = post_webhook(test_client, payload_dup)
    assert r.status_code == 200
    assert r.json()["status"] == "duplicate"

    # 5. Legacy receipt fallback: category plan
    with Session(engine) as session:
        org_legacy = Organization(id="org_legacy_plan", name="Legacy Org", token="tok_legacy_plan", plan="starter")
        session.add(org_legacy)
        session.commit()

    evt_legacy_plan = f"evt_legacy_plan_{uuid.uuid4().hex}"
    payload_legacy = make_payload(event_id=evt_legacy_plan, order_id=None, amount=5000)
    payload_legacy["payload"]["payment"]["entity"]["order_id"] = None
    payload_legacy["payload"]["payment"]["entity"]["receipt"] = "org_legacy_plan:plan:pro"
    r = post_webhook(test_client, payload_legacy)
    assert r.status_code == 200
    assert r.json()["status"] == "processed"

    # 6. Legacy receipt fallback: category topup_coding
    evt_legacy_topup = f"evt_legacy_topup_{uuid.uuid4().hex}"
    payload_legacy2 = make_payload(event_id=evt_legacy_topup, order_id=None, amount=5000)
    payload_legacy2["payload"]["payment"]["entity"]["order_id"] = None
    payload_legacy2["payload"]["payment"]["entity"]["receipt"] = "org_legacy_plan:topup_coding:500"
    r = post_webhook(test_client, payload_legacy2)
    assert r.status_code == 200
    assert r.json()["status"] == "processed"

    # 6. Legacy receipt fallback: category topup_coding
    evt_legacy_topup = f"evt_legacy_topup_{uuid.uuid4().hex}"
    payload_legacy2 = make_payload(event_id=evt_legacy_topup, order_id=None, amount=5000)
    payload_legacy2["payload"]["payment"]["entity"]["order_id"] = None
    payload_legacy2["payload"]["payment"]["entity"]["receipt"] = "org_legacy_plan:topup_coding:500"
    r = post_webhook(test_client, payload_legacy2)
    assert r.status_code == 200
    assert r.json()["status"] == "processed"

