import os
import uuid

try:
    import razorpay
except ImportError:  # pragma: no cover
    razorpay = None
from typing import Dict
from fastapi import HTTPException
from skelion_agent.config import settings

# Load credentials from environment. Payment simulation must be explicit.
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"
ALLOW_PAYMENT_SIMULATION = (
    os.getenv(
        "ALLOW_PAYMENT_SIMULATION",
        "true" if not IS_PRODUCTION else "false",
    ).lower()
    == "true"
    and not IS_PRODUCTION
)
PAYMENTS_CONFIGURED = all(
    value and "placeholder" not in value.lower()
    for value in (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET)
)


def _payment_secret() -> str:
    return os.getenv("RAZORPAY_KEY_SECRET") or settings.RAZORPAY_KEY_SECRET

if razorpay and PAYMENTS_CONFIGURED:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    client = None


def create_order(
    amount: int, currency: str = "INR", receipt: str = "order_rcptid_11"
) -> Dict:
    """Create a Razorpay order.
    amount: amount in paise (e.g., ₹3999 => 399900)
    In development, a mock order is available only when explicitly enabled.
    """
    if client:
        try:
            order = client.order.create(
                {
                    "amount": amount,
                    "currency": currency,
                    "receipt": receipt,
                    "payment_capture": 1,
                }
            )
            return order
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail="Failed to create Razorpay order"
            ) from exc
    elif ALLOW_PAYMENT_SIMULATION:
        return {
            "id": f"order_{uuid.uuid4().hex[:14]}",
            "entity": "order",
            "amount": amount,
            "amount_paid": 0,
            "amount_due": amount,
            "currency": currency,
            "receipt": receipt,
            "status": "created",
            "attempts": 0,
            "key_id": RAZORPAY_KEY_ID,
        }
    raise HTTPException(
        status_code=503,
        detail="Razorpay payments are not configured for this environment",
    )


def verify_signature(payload_body: bytes, razorpay_signature: str) -> bool:
    """Verify webhook signature using HMAC SHA256.
    Returns True if valid, False otherwise.
    """
    import hmac
    import hashlib

    if not RAZORPAY_WEBHOOK_SECRET:
        return False
    if "placeholder" in RAZORPAY_WEBHOOK_SECRET.lower() and IS_PRODUCTION:
        return False

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, razorpay_signature)


def verify_payment_signature(
    order_id: str, payment_id: str, razorpay_signature: str
) -> bool:
    """Verify the client payment signature for a Razorpay order."""
    import hmac
    import hashlib

    secret = _payment_secret()
    if not secret:
        return False
    if "placeholder" in secret.lower() and IS_PRODUCTION:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, razorpay_signature)
