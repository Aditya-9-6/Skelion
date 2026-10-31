import os
import uuid

try:
    import razorpay
except ImportError:  # pragma: no cover
    razorpay = None
from typing import Dict
from fastapi import HTTPException

# Load credentials from environment
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if not all([RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET]):
    RAZORPAY_KEY_ID = RAZORPAY_KEY_ID or "rzp_test_placeholder_key"
    RAZORPAY_KEY_SECRET = RAZORPAY_KEY_SECRET or "rzp_secret_placeholder"
    RAZORPAY_WEBHOOK_SECRET = (
        RAZORPAY_WEBHOOK_SECRET or "rzp_webhook_secret_placeholder"
    )

if razorpay and not RAZORPAY_KEY_ID.startswith("rzp_test_placeholder"):
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    client = None


def create_order(
    amount: int, currency: str = "INR", receipt: str = "order_rcptid_11"
) -> Dict:
    """Create a Razorpay order.
    amount: amount in paise (e.g., ₹3999 => 399900)
    If live/test keys are not connected or in sandbox test mode, provides a standard mock order.
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
    else:
        # Development / Sandbox Mode Order Generation
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


def verify_signature(payload_body: bytes, razorpay_signature: str) -> bool:
    """Verify webhook signature using HMAC SHA256.
    Returns True if valid, False otherwise.
    """
    import hmac
    import hashlib

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, razorpay_signature)
