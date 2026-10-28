# Skelion & GossipMesh — Billing, Plans & Credits (v2)

> **Purpose:** Replaces `BILLING_PLANS_AND_SUBSCRIPTION_MODEL.md` (v1). Written to be fed to your coding agent (Antigravity). It keeps everything that works in v1 and fixes the gaps that would hurt you with real paying customers.
>
> **Precedence:** Where this file conflicts with `VSCODE_EXTENSION_MASTER_PLAN.md` on **plans, pricing, credits, or billing model (its §6–§8)**, this file wins. Everything else in the master plan still applies.
>
> **Rule for the agent:** Inspect the existing code first (`plan_config.py`, `billing_routes.py`, `razorpay_service.py`, `payment.py`, `models.py`, `commercialization.py`). Reuse what works, migrate what doesn't, write `BILLING_AUDIT.md` before changing anything. Verify all Razorpay/Stripe behavior against current official docs and test mode; if docs and this file disagree, the docs win (log in `DECISIONS.md`). No secret values anywhere in code, logs or prompts.

---

## 0. What changed vs v1 (and why)

| # | v1 | Problem | v2 fix |
|---|---|---|---|
| 1 | Razorpay **Orders** labelled "monthly subscription" | An order is a one-time payment. Nothing renews, nothing expires | Explicit **30-day prepaid pass** model (`plan_period_end`, reminders, grace, auto-downgrade). Razorpay **Subscriptions** (auto-renew) added as Phase 2 |
| 2 | On `payment.captured`: `credits_total = plan quota; credits_used = 0` | A top-up or repeat webhook **wipes usage and overwrites balance**; double webhook = double credit | Append-only **credit ledger** with idempotency keys, buckets and expiry |
| 3 | Plan/org parsed from `receipt` (`{org_id}:{plan}`) | Razorpay limits `receipt` length (40 chars at last check; a UUID + `enterprise` exceeds it) and receipt is a weak source of truth | Server-side `payment_orders` table created at checkout; webhook looks up by `order_id` and verifies amount/currency/org/plan from **our** record |
| 4 | Only `payment.captured` handled | Failures, refunds, duplicates, out-of-order events ignored | Full event handling, dedupe on event id, DB transaction + row lock, reconciliation job |
| 5 | Free ₹0 → Pro ₹3,999 gap | No entry plan for solo developers (the VS Code extension's main audience) | New **Developer** tier at ₹799; your ₹3,999 → **Team**; ₹9,999 → **Business**; **Enterprise** becomes real custom contracts |
| 6 | "Pilot" is the free plan name | Collides with your 1-week pilot program | Free plan renamed **Community**; **Pilot** becomes a time-boxed program (§9) |
| 7 | Credits and "requests" both used, never defined together | Customers can't predict what they pay for | Clear split: **requests** = cheap proxy traffic, **credits** = agent compute. Published credit **rate card** (§4) |
| 8 | Enterprise "unlimited" | Unbounded cost risk | Custom quotas with fair-use and burst protection |
| 9 | No annual plans, credit packs, coupons, trials | Slower revenue, no upsell path when credits run out | Annual (2 months free), credit packs, coupons/founding offer, pilot grants |
| 10 | Org billing only | VS Code extension signs users in with GitHub | **User → personal org** auto-created on first sign-in (§7) |
| 11 | No GST/invoice handling | Required for selling in India | GST-aware pricing + invoice records (§11) |
| 12 | Two gateways, different webhook URLs and state names | Double the bug surface | One internal billing state machine, one webhook pattern (`/v1/webhooks/{provider}`), Stripe/MoR deferred to Phase 3 |
| 13 | No unit-economics tracking | Risk of selling credits below cost | Every credit event stores estimated INR cost; margin dashboard + alerts (§5) |

---

## 1. Plans & Pricing (proposed v2)

> Prices are **INR per month, excluding GST** (decide inclusive vs exclusive in `DECISIONS.md`; see §11). All values live in versioned config/DB (`plans` table), never hard-coded in UI or logic. **Validate prices with pilot customers before announcing them publicly.**

| | **Community** | **Developer** *(new)* | **Team** *(was Pro)* | **Business** *(was Enterprise ₹9,999)* | **Enterprise** |
|---|---|---|---|---|---|
| Price / month | ₹0 | ₹799 | ₹3,999 | ₹9,999 | Custom (annual contract) |
| Annual price | – | ₹7,990 (2 months free) | ₹39,990 | ₹99,990 | Custom |
| Credits / month | 100 | 1,000 | 5,000 | 25,000 | Custom |
| Proxy requests / month | 1,000 | 10,000 | 50,000 | 250,000 | Custom + fair use |
| Seats | 1 | 1 | up to 5 (extra seat ₹499) | up to 20 (extra seat ₹399) | Custom |
| Projects / proxies | 1 | 3 | 10 | 50 | Custom |
| Models | Standard | Standard + limited premium | All standard + premium | All + priority routing | All + custom LLM bridges |
| Fail-open edge proxy + telemetry | ✔ | ✔ | ✔ | ✔ | ✔ |
| Incident fingerprinting + synthetic replay tests | ✔ | ✔ | ✔ | ✔ | ✔ |
| Autonomous fix generation (human approves) | Preview only | ✔ | ✔ | ✔ | ✔ |
| PR review diagnostic cards | – | Limited | ✔ | ✔ | ✔ |
| Multi-provider key pooling + backoff | – | ✔ | ✔ | ✔ | ✔ |
| PII redaction on payloads | ✔ | ✔ | ✔ | ✔ | ✔ |
| Slack / email alerts | – | Email | Slack + email | Slack + email + webhooks | Custom |
| History retention | 7 days | 30 days | 90 days | 1 year | Custom |
| SSO + TOTP MFA, audit log | – | – | – | ✔ | ✔ |
| Auto-merge for verified non-breaking patches (with guardrails §8.4) | – | – | – | ✔ (opt-in) | ✔ |
| SCIM directory sync | – | – | – | – | ✔ |
| Dedicated canary deployments, SLA, custom contract | – | – | – | – | ✔ |
| Support | Community | Email | Priority email | Priority + onboarding call | Dedicated |

**Why these changes:** most extension users are individuals; a ₹799 tier captures them and gives your ₹3,999 plan a natural upgrade story ("add teammates"). Your ₹9,999 plan has SSO/MFA, auto-merge and multi-seat features, which is Business-level value; real Enterprise (SLA, SCIM, contracts, dedicated infra) deserves negotiated pricing rather than a ₹9,999 sticker.

### 1.1 Credit packs (top-ups, never reset usage)
| Pack | Price | Credits | Valid for |
|---|---|---|---|
| Small | ₹499 | 500 | 12 months |
| Medium | ₹1,399 | 1,500 | 12 months |
| Large | ₹4,499 | 5,000 | 12 months |

Packs cost more per credit than the plan allowance on purpose, so subscribing is always the better deal, but a customer who hits the limit mid-month can keep working instantly.

### 1.2 Offers (all configurable)
- **Founding 50:** first 50 paying customers get 30% off Developer/Team for 12 months, price-locked (coupon + `price_lock_until`).
- **Annual prepay:** 2 months free.
- **Pilot program:** see §9.
- Coupons: percent/fixed, max redemptions, expiry date, plan scope, one per org.

---

## 2. Billing Model: Two Phases (important for speed)

### Phase 1 — Prepaid 30-day passes via Razorpay Orders (ship first; simplest and fastest)
- Customer buys a plan period (monthly 30 days, or annual 365 days) with UPI/card/netbanking via a Razorpay **Order**.
- On verified payment: set `plan_id`, `plan_period_start`, `plan_period_end`, grant that period's credits via the ledger.
- **Renewal:** reminder emails at T-7, T-3, T-1 days, a one-click "Renew" link, and in-panel banner. **Grace period:** 3 days of access after expiry, then auto-downgrade to Community by the scheduler.
- Customers understand it ("pay for 30 days"), UPI works without mandate complexity, and there is no failed-auto-debit support burden.

### Phase 2 — Auto-renewing Razorpay Subscriptions (add after first customers)
- Use Razorpay Subscriptions API for cards/UPI AutoPay where supported (check current limits and plan-change rules; §10).
- Map Razorpay subscription events into the same internal state machine (§3). The ledger and entitlements code does not change.
- Keep prepaid passes available as a fallback for users whose bank/UPI app doesn't support mandates.

### Phase 3 — International / enterprise invoicing
- Stripe (or a merchant-of-record such as Paddle/Lemon Squeezy if you want global tax handling offloaded) for USD.
- Enterprise annual contracts via manual invoice + bank transfer/UPI, recorded as `payment_orders` with `provider='manual'` and granted through the same ledger by an admin action (audit-logged).

---

## 3. Internal Billing State Machine (provider-independent)

```
community (free)
   │ checkout created
   ▼
pending_payment ──fail/expire──► community
   │ payment verified
   ▼
active ──period ends (no renewal)──► grace (3 days) ──► expired ──► community
   │                                     ▲ renew
   │ payment failed on renewal (Phase 2)
   ▼
past_due ──retries exhausted──► expired
active ──user cancels──► active (cancel_at_period_end=true) ──period end──► community
active/any ──full refund──► community (credits from that payment reversed)
```
Every transition writes `audit_log` and emits an event for email + extension realtime update.

---

## 4. Credits: Definition, Rate Card & Rules

### 4.1 Requests vs credits
- **Requests** = proxy traffic and telemetry events (cheap, high volume). Metered per plan; at limit, the proxy **keeps passing traffic (fail-open)** and only pauses enrichment/analysis. Never block a customer's production traffic.
- **Credits** = agent compute (LLM tokens, sandbox time). At 0 credits, agent actions stop and the product falls back to passive monitoring + upgrade/pack prompt.

### 4.2 Starting rate card (tune using real cost data after the pilot, §5)
| Action | Credits |
|---|---|
| Proxy telemetry, fingerprinting, basic synthetic replay generation | 0 (uses request quota) |
| PR diagnostic card | 1 (up to 500 changed lines), +1 per extra 500 lines, max 5 |
| Incident root-cause analysis | 3 |
| Fix generation (diff synthesis) | 5 |
| Sandboxed reproduction + verification | 5 (+1 per 2 sandbox-minutes beyond the first 2) |
| VS Code chat turn, standard model | 1 |
| VS Code chat turn, premium model | 3 |
| Agent run (multi-step) | Sum of its steps, capped by a per-run limit shown **before** the user approves ("This run may use up to ~12 credits") |

Show the estimate before expensive actions and the actual cost after. Trust is a feature.

### 4.3 Credit buckets and expiry
| Bucket | Source | Expires | Consumed |
|---|---|---|---|
| `allowance` | Plan's monthly credits | End of plan period (no rollover) | First |
| `grant` | Pilot, promos, support goodwill | Per grant (e.g., end of pilot) | Second |
| `purchased` | Credit packs | 12 months after purchase | Last |

Consume the soonest-to-expire first. Show customers the breakdown ("820 plan + 300 pack").

### 4.4 Spend safety
- Per-run caps (steps, tokens, sandbox minutes) and per-day org caps.
- Soft alerts at 80% and 100% of credits (email + panel + Slack for paid plans). Optional "auto-buy pack" is **off by default**.
- Hard stop at 0: no negative balances.

---

## 5. Unit Economics (required before final prices)

1. For **every credit-consuming event**, store `cost_inr_est` = provider token cost + sandbox compute + overhead (field on `usage_events`).
2. Dashboard: average cost per credit, by action type, model, and plan; gross margin per org.
3. Rule of thumb: **price per credit ≥ 3× average cost per credit** (≈ 65–70% gross margin). Example with made-up numbers: if measured cost is ₹0.20/credit, Team's ₹0.80/credit gives ~75% margin; if it's ₹0.50, raise the credit cost of the expensive actions or the plan price.
4. Alerts: org or plan with negative margin; model whose cost per credit rises; daily provider spend above budget.
5. Re-run this analysis after the first pilot week and again after 30 days; update the rate card by creating a **new plan/rate-card version** (existing customers keep their version until renewal).

---

## 6. Data Model (adapt to your ORM; Postgres shown)

```sql
users(id, github_id unique, login, email, avatar_url, status, created_at)
organizations(id, name, owner_user_id, is_personal bool,
  plan_id, plan_version, billing_status,          -- see §3
  plan_period_start, plan_period_end, grace_until,
  cancel_at_period_end bool, pilot_until,
  gstin null, billing_name, billing_address, billing_state, created_at)
memberships(org_id, user_id, role)                 -- owner|admin|member

plans(id, version, name, price_inr_paise, billing_period, credits, requests_quota,
      seats, projects, limits jsonb, features jsonb, models jsonb, active)

payment_orders(id, org_id, user_id, plan_id, plan_version, kind,   -- plan|renewal|pack|manual
      amount_paise, currency, gst_paise, coupon_id null,
      provider, provider_order_id unique, status,                  -- created|paid|failed|expired|refunded
      expires_at, created_at)
payments(id, payment_order_id, provider_payment_id unique, amount_paise, currency,
      method, status, captured_at, raw jsonb)
refunds(id, payment_id, provider_refund_id unique, amount_paise, status, reason, created_at)

credit_ledger(id, org_id, bucket,                  -- allowance|grant|purchased
      delta int, reason,                           -- plan_period|pack|pilot_grant|usage|refund|expiry|admin_adjust
      ref_type, ref_id, idempotency_key unique,
      expires_at null, created_at)
-- balance per bucket = SUM(delta) WHERE not expired; expiry rows written by scheduler

usage_events(id, org_id, user_id, action, model, credits, tokens_in, tokens_out,
      sandbox_seconds, cost_inr_est, run_id, ts)   -- partition monthly
credit_reservations(id, org_id, run_id, credits_reserved, status, expires_at)

coupons(code, kind, value, plan_scope, max_redemptions, valid_until, price_lock_months)
coupon_redemptions(coupon_id, org_id, payment_order_id, created_at)

invoices(id, number unique, org_id, payment_id, amount_paise, gst_paise, gstin_buyer, pdf_url, issued_at)
webhook_events(provider, event_id, type, payload jsonb, received_at, processed_at, error, unique(provider,event_id))
audit_log(id, actor, org_id, action, meta jsonb, ts)
```
Money is **integer paise**, never floats. Timestamps UTC.

---

## 7. Identity Mapping for the VS Code Extension

- First GitHub sign-in → create `users` row **and** a personal `organization` (`is_personal=true`, Community plan, 100 allowance credits for the current period) + `memberships(owner)`.
- Extension JWT carries `user_id` and `org_id`; all billing/credit checks are per org.
- Teams: owner invites members (GitHub login); seats counted from `memberships`; credits are pooled per org.
- Extension shows: plan name, **credits remaining by bucket**, period end date, "Renew" / "Upgrade" / "Buy credits" buttons. Checkout opens in the external browser; the panel shows *Waiting → Confirming → Activated* via SSE/polling.
- Proxy/agent API keys (`skl_live_…`) belong to an org and project; add scopes, optional expiry, `last_used_at`, one-click rotation. Keep SHA-256 hashed storage and a visible prefix for lookup. Add `skl_test_…` for sandbox mode.

---

## 8. Core Flows (specification)

### 8.1 Checkout — `POST /v1/billing/checkout`
Body: `{ kind: "plan"|"renewal"|"pack", planId?, packId?, period: "monthly"|"annual", couponCode? }`
1. AuthN/AuthZ (org owner/admin only). Validate plan/pack exists and is active; compute price server-side (plan + coupon + GST). **Never trust client-sent amounts.**
2. Create `payment_orders` row (`status=created`, `expires_at = now+30 min`).
3. Create Razorpay order (`amount` in paise, `currency=INR`, short `receipt` = our order row id, `notes = {order_row_id, org_id, plan_id}`); store `provider_order_id`.
4. Return a one-time checkout URL for the hosted page (not the raw secret), or `{order_id, key_id, amount}` for the web checkout page. Extension opens it in the browser.

### 8.2 Client confirmation — `POST /v1/billing/verify` (fast path, hint only)
Verify the checkout handler signature: HMAC-SHA256 of `razorpay_order_id + "|" + razorpay_payment_id` with the key secret, constant-time compare. Then fetch the payment from Razorpay and run the same activation logic as the webhook (idempotent). The webhook remains the source of truth.

### 8.3 Webhook — `POST /v1/webhooks/razorpay`
```python
# Pseudocode — adapt to your framework
raw = await request.body()
sig = request.headers["X-Razorpay-Signature"]
expected = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, sig): return 400

event_id = request.headers["X-Razorpay-Event-Id"]
if not insert_webhook_event_once("razorpay", event_id, payload): return 200  # duplicate
enqueue(process_razorpay_event, event_id)    # worker does the real work
return 200                                    # respond fast
```
Worker, per event, inside one DB transaction with `SELECT … FOR UPDATE` on the org row:
- `payment.captured` / `order.paid`: load `payment_orders` by `provider_order_id`; **verify** status not already paid, `amount == order.amount_paise`, `currency == INR`, then mark paid → apply entitlement (below) → create invoice → emit events.
- `payment.failed`: mark order failed; notify user.
- `refund.processed`: record refund; if full refund within policy, reverse the credits granted by that payment (ledger `delta` negative with `idempotency_key=refund:{id}`, floor at what's unspent) and downgrade.
- Unknown events: store, ignore.

**Apply entitlement (idempotent):**
- kind `plan`/`renewal`: set plan, period start/end (renewal extends from `max(now, current_period_end)`), `billing_status=active`; ledger `+credits` bucket `allowance` with `idempotency_key = "period:{payment_id}"`, `expires_at = period_end`.
- kind `pack`: ledger `+credits` bucket `purchased`, `idempotency_key = "pack:{payment_id}"`, `expires_at = now + 12 months`. **Does not touch plan or usage.**
- Duplicate delivery → unique key violation → no-op.

### 8.4 Auto-merge guardrails (Business/Enterprise)
Opt-in per repo; require green CI, sandbox verification passed, diff size limit, protected paths excluded, no dependency/security-config changes, one-click revert PR generated, org admin can disable instantly.

### 8.5 Credit consumption (reserve → settle)
```python
def run_with_credits(org, action, estimate, execute):
    with tx():
        buckets = lock_buckets_by_soonest_expiry(org.id)       # FOR UPDATE
        if sum_available(buckets) < estimate: raise OutOfCredits(upgrade_url, pack_url)
        reservation = reserve(org.id, estimate, ttl=15min)
    try:
        result = execute()                                      # LLM / sandbox work
        actual = measure(result)                                # tokens, sandbox secs
    except Exception:
        release(reservation); raise
    with tx():
        settle(reservation, actual)                             # ledger usage rows, soonest-expiry first
        record_usage_event(org, action, actual, cost_inr_est=...)
    return result
```
Unused reservations expire automatically. Parallel requests cannot overshoot the balance.

### 8.6 Scheduler jobs
- Every 5 min: expire stale `pending_payment`/reservations.
- Hourly: move `active → grace → expired → community`; write ledger `expiry` rows for lapsed buckets.
- Daily: renewal reminders (T-7/T-3/T-1), low-credit alerts, reconciliation (fetch recent Razorpay payments/orders and compare with our DB; fix drift; alert on any mismatch).
- Weekly: unit-economics report to you.

### 8.7 Upgrades and downgrades (Phase 1)
- **Upgrade mid-period:** charge the difference prorated by remaining days (`(new − old) × remaining/total`), grant the extra credits proportionally, or simply start a fresh period at the new plan if proration feels too complex (log choice in DECISIONS.md).
- **Downgrade:** takes effect at period end; show a notice. Credits already granted stay until expiry.
- **Cancel:** sets `cancel_at_period_end`; access continues to period end.

---

## 9. One-Week Pilot Program (fits your launch window)

- Invite-only; set `organizations.pilot_until = now + 7 days`.
- Grant Team-level features and a **300-credit `grant` bucket** expiring at `pilot_until` (ledger reason `pilot_grant`). No card needed.
- Day 1 onboarding message; Day 3 check-in; Day 5 offer: Founding-50 coupon valid 72 hours; Day 7 summary email showing credits used and value delivered (PRs reviewed, incidents analyzed), with a one-click pay link.
- At `pilot_until`: automatic downgrade to Community unless paid. Do not extend silently.
- Ask pilot users to pay at least a small amount or commit in writing; paid intent is the strongest validation signal.
- Track per pilot org: activation (first agent action), credits used, time-to-value, NPS-style question, willingness to pay at your proposed prices.

---

## 10. Razorpay & Stripe Items the Agent Must Verify Live

1. `receipt` max length and allowed characters (use our short order-row id).
2. Orders vs Subscriptions: whether your account supports Subscriptions, UPI AutoPay limits, first-payment authentication, plan-change rules.
3. USD/international card acceptance and whether recurring USD is available for your account.
4. Webhook events and retry window; respond 200 quickly; separate webhook secret per environment.
5. Test vs live: keys, webhooks, plans are separate; add a CI guard that fails if live keys appear outside production.
6. Razorpay plans are immutable: version plans; existing customers keep their price until renewal.
7. Stripe (if used, Phase 3): prefer `checkout.session.completed` and `invoice.paid` for activation and `invoice.payment_failed` for dunning; `charge.succeeded` alone is not a reliable subscription signal. Use idempotency keys on all writes.

---

## 11. Tax, Invoices & Policies (confirm with a CA / Razorpay compliance)

- Decide GST-inclusive vs GST-exclusive display (GST on software services is commonly 18%; confirm current rate and whether/when you must register for GST at your turnover).
- Store buyer GSTIN/state optionally; generate sequential invoices with GST breakup; email on every successful payment.
- Required pages: Pricing (with tax note), Terms, Privacy, **Refund & Cancellation**, Contact. Suggested refund rule: full refund within 7 days if less than 10% of credits used; no refund otherwise (adjust to taste, publish clearly).
- Data rights: export and delete endpoints; retention per plan.

---

## 12. API Surface (billing & credits)

```
GET  /v1/plans                         GET  /v1/billing/status        (plan, period, buckets, grace)
POST /v1/billing/checkout              POST /v1/billing/verify
POST /v1/billing/coupon/validate       POST /v1/billing/cancel
GET  /v1/billing/invoices              GET  /v1/billing/invoices/{id}.pdf
GET  /v1/credits/balance               GET  /v1/credits/ledger        (paginated)
POST /v1/credits/estimate              GET  /v1/usage/summary
POST /v1/webhooks/razorpay             POST /v1/webhooks/stripe       (Phase 3)
Admin (internal only): POST /admin/orgs/{id}/grant-credits  /override-plan  /refund  /replay-webhook
```
Standard errors: `quota_exceeded` (429), `out_of_credits` (402, includes `upgradeUrl`, `packUrl`), `plan_required` (403), `payment_pending` (409), `validation_error` (422). Keep `X-RateLimit-*` headers on all limited endpoints.

---

## 13. Rate Limits (proposed per plan)

| | Community | Developer | Team | Business | Enterprise |
|---|---|---|---|---|---|
| API requests / min / org | 60 | 300 | 1,200 | 6,000 | Custom |
| Concurrent agent runs | 1 | 2 | 5 | 20 | Custom |
| Max agent steps / run | 10 | 25 | 25 | 40 | Custom |
| Max payload size | 256 KB | 1 MB | 2 MB | 5 MB | Custom |

Keep your token-bucket/sliding-window limiters and the key-pool 429 backoff (`rate_limits_saved_total`). Add per-plan limits from config, burst allowance, and a fair-use policy instead of "unlimited".

---

## 14. Implementation Order (compressed for a ~37-day window)

**Week 1 — fix money correctness (must-do before any live payment)**
1. `BILLING_AUDIT.md` of current code.
2. Add `payment_orders`, `payments`, `credit_ledger`, `webhook_events`; migrate existing org credits into ledger rows.
3. Rewrite checkout + webhook per §8.1–§8.3 (amount/currency verification, idempotency, dedupe, row lock).
4. Plan period fields + scheduler for grace/expiry; Community downgrade.
5. Tests: duplicate webhook, shuffled events, wrong amount, expired order, refund, concurrent credit use.

**Week 2 — product layer**
6. Developer tier, credit packs, coupons, annual, rate card + estimate endpoint, reserve/settle consumption.
7. Personal-org creation on GitHub sign-in; credits/plan endpoints for the extension.
8. Emails: receipt, renewal reminders, low credits, payment failed.
9. Invoices + GST fields.

**Week 3 — pilot**
10. Pilot flag/grants; admin console basics (grant credits, replay webhook, view ledger).
11. Unit-economics dashboard; run the 1-week pilot; adjust rate card and prices.

**Week 4+ — open paid plans, then Phase 2**
12. Go live with Razorpay live keys; one real small payment + refund test.
13. Add Razorpay Subscriptions (auto-renew) once first customers are paying.
14. Stripe or merchant-of-record for international; enterprise manual invoicing.

---

## 15. Acceptance Tests (all must pass)

| Test | Expected |
|---|---|
| Same webhook delivered 5× | Exactly one credit grant, one invoice, one state change |
| Webhook before client verify, and vice versa | Same final state |
| Payment amount ≠ order amount (tampered or partial) | Rejected, flagged, no entitlement |
| Pack purchase while plan active | Plan period and usage untouched; purchased credits added |
| Renewal 2 days before expiry | New period starts at old `period_end`, no lost days |
| Plan lapses | Grace 3 days → Community; plan allowance expires; purchased credits remain |
| 50 parallel agent runs at balance = estimate | Exactly one reserves; others get `out_of_credits` |
| Run fails midway | Reservation released; no credits charged |
| Full refund | Credits from that payment reversed (up to unspent), plan downgraded, refund recorded |
| Credit balance == `SUM(ledger)` | Always, verified by nightly job |
| Free user calls premium-only feature | `plan_required` with upgrade link |
| Extension after payment | Panel flips to new plan within seconds, no restart |
| Reconciliation with a deliberately dropped webhook | Drift detected and fixed, alert raised |
| Secrets scan | No keys in repo, logs, or client bundle |

---

## 16. Metrics to Watch

Activation (first agent action within 24 h) · Community → paid conversion · pilot → paid conversion · ARPU · gross margin per credit and per plan · % of allowance unused at period end (pricing signal) · renewal rate · failed/abandoned checkout rate · time from payment to activation (p95 < 5 s) · support tickets about billing.

---

## 17. Decisions for You (agent logs defaults in `DECISIONS.md`)

1. Final prices and credit amounts for Developer/Team/Business (defaults above) and annual discount.
2. GST-inclusive vs exclusive pricing.
3. Pilot length (default 7 days) and pilot grant (default 300 credits).
4. Refund policy (default: 7 days, under 10% credits used).
5. Mid-period upgrade: prorate vs restart period (default: prorate).
6. Grace period length (default: 3 days).
7. When to add Razorpay Subscriptions (default: after first 10 paying customers).
8. International: Stripe vs merchant-of-record (default: decide in Phase 3).

---
**End.** Start with `BILLING_AUDIT.md`, then Week 1 tasks. Do not enable live payments until every Week 1 acceptance test passes.
