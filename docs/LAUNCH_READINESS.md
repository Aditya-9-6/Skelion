# Skelion Control Plane Launch Readiness

This document records the launch hardening applied to payment handling and the required production configuration.

## What changed

- Removed committed Razorpay credentials from environment examples.
- Disabled implicit Razorpay placeholder credentials.
- Added explicit `ALLOW_PAYMENT_SIMULATION=true` gating for development-only mock orders.
- Production order creation now fails with HTTP 503 when Razorpay is not configured instead of creating a fake order.
- Client payment signatures and webhook signatures now fail closed when secrets are missing or placeholders.
- Removed the placeholder-secret bypass that previously accepted any client payment signature.
- Removed placeholder fallback values from the returned Razorpay key configuration.

## Required production variables

```text
ENVIRONMENT=production
SECRET_KEY=<random high-entropy value>
ENCRYPTION_KEY=<random high-entropy value>
DATABASE_URL=<managed production database URL>
REDIS_URL=<managed production Redis URL>
ALLOWED_ORIGINS=https://your-production-domain.example
RAZORPAY_KEY_ID=rzp_live_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

Do not copy values from `.env.helios.example` or `.env.skelion.example` into production without replacing every placeholder. Keep secrets in the hosting provider's secret manager.

## Operator launch steps

1. Rotate the Razorpay credentials previously committed to repository history.
2. Provision production database and Redis resources.
3. Set `ENVIRONMENT=production` and all required secrets.
4. Run `python -m skelion_agent.config` checks or the service startup path and confirm insecure defaults are rejected.
5. Configure `ALLOWED_ORIGINS` with the exact browser origins that may call the API. Production no longer permits wildcard credentialed CORS.
6. Configure the Razorpay webhook endpoint and use the exact same webhook secret.
7. Verify `/health` is liveness-only and `/readyz` returns 200 only after both the database and Redis are reachable.
8. Run the billing, webhook, quota, and configuration tests.
9. Confirm one invalid client signature and one invalid webhook signature return 400 and create no entitlement.
10. Confirm the application never authorizes quota from browser-provided balances.

## Launch boundary

Payment verification is now fail-closed, but payment entitlements still need to be persisted and enforced by the authenticated control-plane database/webhook path. The website's local ledger must remain presentation-only.
