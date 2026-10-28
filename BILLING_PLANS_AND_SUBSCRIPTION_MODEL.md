# Skelion & GossipMesh — Billing Plans, Subscription Model & Usage Limits

This document provides a complete overview of the billing architecture, subscription tiers, pricing models, payment gateways, credit mechanics, and system limits across the platform.

---

## 1. Executive Summary & Architecture Overview

The platform uses a hybrid multi-tenant billing and commercialization model:
1. **Skelion SaaS Tiering & Credit Quota System**: Manages developer/team subscriptions, autonomous incident response quotas, AI PR reviews, and edge proxy telemetry. Primary gateway: **Razorpay** (with INR pricing) and dual-support **Stripe** integration.
2. **GossipMesh Enterprise Commercialization Engine**: Handles multi-tenant seat allocations, metered resource telemetry, token/request rate limiting, and custom enterprise contracts.

---

## 2. Subscription Plans & Tiers

The core tiers are defined in [`skelion_agent/plan_config.py`](file:///g:/My%20Drive/helios/skelion_agent/plan_config.py) and enforced via [`skelion_agent/billing_routes.py`](file:///g:/My%20Drive/helios/skelion_agent/billing_routes.py).

| Plan Tier | Price (INR / Month) | Credit Quota | Default Monthly Quota | Target Audience | Key Capabilities & Features |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pilot (Free / Community)** | **₹0** | **100 Credits** | 1,000 requests | Solo developers & evaluation | • Fail-open edge proxy telemetry<br>• Basic incident fingerprinting<br>• Automated synthetic replay test generation<br>• Community support |
| **Pro** | **₹3,999** | **5,000 Credits** | 50,000 requests | Fast-growing teams & startups | • Autonomous LLM incident fix generation<br>• PR review bot diagnostic cards<br>• Shared multi-provider LLM key-pooling with backoff<br>• PII redaction on all payloads<br>• Dedicated Slack/Email alerts |
| **Enterprise** | **₹9,999** *(Custom)* | **25,000 Credits** *(Expandable)* | Custom / Unlimited | Large engineering orgs & enterprises | • Custom enterprise contract terms & SLA<br>• Auto-merge for verified non-breaking patches<br>• SCIM directory sync & SSO (MFA TOTP via pyotp)<br>• Multi-seat allocation management<br>• Dedicated canary deployments & custom LLM bridges |

---

## 3. Credit Quota & Usage Mechanics

### How Credits Are Consumed
Credits represent atomic units of compute and autonomous agent workflows executed by the control plane and edge nodes:
- **PR Diagnostic Review**: Each PR security & diagnostic card run consumes **1 Credit** (tracked in `PRReview.credits_deducted`).
- **Autonomous Incident Resolution**: Incident root-cause analysis, sandboxed reproduction, and diff synthesis consume credits based on LLM token budgets and execution cycles.
- **Credit Enforcement**: Tracked per organization (`credits_total` vs `credits_used`).
  - Active remaining credits: `credits_remaining = max(0, org.credits_total - org.credits_used)`
  - Out of credits: The system refuses autonomous patch execution or falls back to passive monitoring / proxy-only mode.

### Quota Reset & Top-Ups
- When a subscription payment succeeds or webhook captures a captured payment event, `credits_total` is credited with the plan's quota, and `credits_used` is reset to `0`.
- Top-ups and plan upgrades adjust the organization's quota dynamically in the database (`organizations` table).

---

## 4. Payment Integrations & Workflows

### A. Razorpay Integration (Primary INR Gateway)
- **Service implementation**: [`skelion_agent/billing_routes.py`](file:///g:/My%20Drive/helios/skelion_agent/billing_routes.py) & `skelion_agent/razorpay_service.py`
- **Checkout Flow**:
  1. Client calls `POST /v1/billing/checkout?plan={pilot|pro|enterprise}` with Bearer auth token.
  2. Control plane validates plan name against `PLAN_DEFINITIONS`.
  3. Creates a Razorpay order in paise (`amount_paise = price * 100`).
  4. Encodes receipt metadata as `{org_id}:{plan}`.
  5. Returns `order_id`, `amount`, `currency`, and `key_id` to client.
- **Webhook Handling**:
  - Endpoint: `POST /v1/billing/webhook`
  - Verifies signature using `X-Razorpay-Signature` and HMAC-SHA256.
  - On `payment.captured`, parses receipt `{org_id}:{plan}`, loads organization, updates `plan`, refills `credits_total`, and resets `credits_used = 0`.

### B. Stripe Integration (Global USD Gateway & Enterprise Subscriptions)
- **Service implementation**: [`skelion_agent/payment.py`](file:///g:/My%20Drive/helios/skelion_agent/payment.py) and [`gossipmesh_engine/billing/commercialization.py`](file:///g:/My%20Drive/helios/gossipmesh_engine/billing/commercialization.py)
- **Checkout Flow**:
  - Endpoint: `POST /checkout`
  - Generates hosted Stripe Checkout Session for recurring SaaS subscriptions (`Devproxy SaaS Subscription`).
- **Webhooks**:
  - Endpoint: `POST /webhooks/stripe`
  - Listens for `charge.succeeded` and subscription life-cycle events.
- **Subscription States Tracked**:
  - `trialing`, `active`, `past_due`, `canceled`, `unpaid`.

---

## 5. GossipMesh Enterprise Commercialization Model

Located in [`gossipmesh_engine/billing/commercialization.py`](file:///g:/My%20Drive/helios/gossipmesh_engine/billing/commercialization.py), providing modular enterprise billing engines:

1. **`SeatManager`**:
   - Manages per-seat licenses for enterprise organizations (`allocate_seat`, `remove_seat`).
   - Enables seat-based billing for multi-user developer teams.
2. **`MeteredUsageTracker`**:
   - Tracks granular resource consumption across tenants (`record_usage(tenant_id, resource, amount)`).
   - Resources metered: API calls, LLM prompt/completion tokens, synthetic sandbox execution minutes.
3. **`EnterpriseContractManager`**:
   - Custom contract provisioning (`create_contract(org_id, terms)`).
   - Allows bespoke pricing, custom billing cycles (annual/quarterly invoicing), and custom credit allowances.
4. **`StripeBillingEngine`**:
   - Manages prepaid account balances, customer wallet funds, and usage-based debiting.

---

## 6. Rate Limits & Technical Constraints

### A. API & HTTP Rate Limits
- **P2P & Transport Rate Limiting**: Token-bucket and sliding-window rate limiters ([`gossipmesh_engine/api/rate_limit.py`](file:///g:/My%20Drive/helios/gossipmesh_engine/api/rate_limit.py), [`gossipmesh_engine/p2p/rate_limiter.py`](file:///g:/My%20Drive/helios/gossipmesh_engine/p2p/rate_limiter.py)).
- **Standard Headers**:
  - `X-RateLimit-Limit`: Maximum allowable requests in the active window.
  - `X-RateLimit-Remaining`: Count of remaining requests before rate limiting kicks in.
  - `X-RateLimit-Reset`: Unix epoch timestamp when quota window resets.
- **Graceful Backoff**: Shared multi-key pool (`key_pool.py`) captures HTTP 429 errors from upstream LLM providers, automatically rotating keys and applying exponential backoff without dropping customer traffic. Metric tracked: `rate_limits_saved_total`.

### B. Payload & Security Constraints
- **Fail-Open Guarantee**: If edge proxy encounters unhandled exceptions, it fails open to prevent breaking production traffic.
- **PII Scrubbing**: Automatic masking of sensitive headers (`Authorization`, `Cookie`, `X-Api-Key`) and JSON request/response bodies prior to telemetry ingestion.
- **Token Format**: Standard live API tokens use the `skl_live_<32_hex>` prefix, with SHA-256 hashed storage in the database.

---

## 7. Relevant Source Files & Configuration

- **Plans Definition**: [`skelion_agent/plan_config.py`](file:///g:/My%20Drive/helios/skelion_agent/plan_config.py)
- **Billing API Routes**: [`skelion_agent/billing_routes.py`](file:///g:/My%20Drive/helios/skelion_agent/billing_routes.py)
- **Organization & Billing Data Models**: [`skelion_agent/models.py`](file:///g:/My%20Drive/helios/skelion_agent/models.py)
- **Stripe & Payment Endpoints**: [`skelion_agent/payment.py`](file:///g:/My%20Drive/helios/skelion_agent/payment.py)
- **Enterprise Commercialization Engines**: [`gossipmesh_engine/billing/commercialization.py`](file:///g:/My%20Drive/helios/gossipmesh_engine/billing/commercialization.py)
- **Environment & Secret Config**: [`.env.skelion.example`](file:///g:/My%20Drive/helios/.env.skelion.example)
