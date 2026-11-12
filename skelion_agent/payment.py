from fastapi import APIRouter, Request, HTTPException
import stripe
import os

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


@router.post("/checkout")
async def create_checkout_session(request: Request):
    data = await request.json()
    amount = data.get("amount")
    currency = data.get("currency")
    success_url = os.getenv("STRIPE_SUCCESS_URL")
    cancel_url = os.getenv("STRIPE_CANCEL_URL")
    if not stripe.api_key or not success_url or not cancel_url:
        raise HTTPException(status_code=503, detail="Stripe checkout is not configured")
    if not isinstance(amount, int) or amount <= 0 or not isinstance(currency, str):
        raise HTTPException(status_code=422, detail="A positive amount and currency are required")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": "Devproxy SaaS Subscription"},
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url,
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not endpoint_secret:
        raise HTTPException(status_code=503, detail="Stripe webhooks are not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "received", "type": event["type"]}
