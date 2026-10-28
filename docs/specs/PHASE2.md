# Skelion — Phase 2 Implementation Prompt & Spec

> **For:** your coding agent (Antigravity). **Use:** paste Section 0 first, then keep this whole file in context (save it as `/docs/specs/PHASE2.md` in the repo).
> **Status assumed:** the first extension + billing plan is already implemented. This file covers the **delta**: fix billing correctness, add local/BYO-LLM deployment, the Audit CLI "magnet", license system, integrations, an incident-first extension, pilot tooling, and launch evidence.
> **Companion specs (put in `/docs/specs/` if available):** `SKELION_BILLING_PLANS_V2.md` (detailed billing data model, pseudocode, tests), `VSCODE_EXTENSION_MASTER_PLAN.md` (extension/infra/scale baseline). **Precedence on conflict: this file > BILLING_PLANS_V2 > MASTER_PLAN > the original implementation plan.**
> **Deadline pressure:** revenue is needed within ~5 weeks. Section 17 orders work so the revenue-critical slices ship first and lists what to cut if time slips.

---

## 0. MASTER PROMPT (paste this first)

```
You are a senior staff engineer implementing Phase 2 of Skelion (reverse proxy + AI coding agent + VS Code extension). The first plan is already implemented; do NOT rebuild it. Change it safely.

OUTCOMES
1. Billing is correct and safe for real money: prepaid passes, append-only credit ledger, verified webhooks, plan expiry (replace the old receipt-parsing / credit-reset logic).
2. Customers who refuse to share traffic or logs can run Skelion entirely on their own infrastructure ("Skelion Local") with their own LLM key or a local model. Nothing sensitive leaves their environment unless they explicitly opt in.
3. A free "Production Health Audit" CLI (the sales magnet) produces a one-page report from logs/traffic on the customer's machine, including one proposed fix verified by replay.
4. A signed offline license system sells Local plans; expiry never breaks customer traffic.
5. Integrations where teams already work: MCP server (Claude Code / Cursor / other agents can ask about production), GitHub App, Slack bot.
6. The VS Code extension becomes an incident inbox (Incidents, Fixes with evidence, Ask, Account), not a generic chat clone.
7. Pilot + founding-offer tooling, admin console additions, funnel metrics.
8. Launch evidence: tests, load/chaos, security checks, FINAL_REPORT.md.

RULES
- First read the repo and write AUDIT_P2.md (what exists, what is wrong vs this spec, migration risks). Reuse working code. Keep old API routes working through aliases until the extension is updated.
- Work in vertical slices (Section 17). After each slice: tests pass, evidence saved, commit, update PROGRESS.md. Do not start the next slice with failing tests.
- Every new capability behind a feature flag with a kill switch. Migrations must be reversible and backward compatible (expand → migrate → contract).
- NEVER put secrets, keys, customer data, or real traffic into the repo, logs, tests, prompts, or screenshots. Use env vars/secret manager; fixtures must be synthetic.
- Fail-open always: no billing, license, telemetry or LLM failure may ever block a customer's production traffic through the proxy.
- Verify third-party behavior (Razorpay, GitHub App, Slack, MCP client config formats, LLM provider APIs) against CURRENT official docs and test mode. If docs and this file disagree, docs win; record in DECISIONS.md.
- Ask me only when blocked on a missing secret or a product decision that has no default in Section 18. Otherwise choose the default and log it.
- Do not claim anything is done without evidence (Section 16).
```

---

## 1. Product Positioning (drives every UX and copy decision)

- **Line:** *"Your AI coding tools are blind to production. Skelion shows them, and you, what actually breaks."*
- **Not** a replacement for Cursor / Claude Code / Antigravity. It complements them: production visibility + fixes verified on real traffic.
- **Trust is the product:** open-source core, data stays local by default in Local mode, fail-open, transparent about what leaves the machine.
- Primary customer: small/mid software teams (founders/CEOs buy; the lead engineer approves). Avoid regulated verticals (fintech/health) for the first customers.

---

## 2. Current State → Target State (agent confirms in AUDIT_P2.md)

| Area | Likely current (from v1 docs) | Target |
|---|---|---|
| Billing model | Razorpay Order labelled "monthly"; no plan expiry | Prepaid 30-day/annual passes + scheduler (Subscriptions later) |
| Credits | `credits_total` / `credits_used` counters; reset on `payment.captured` | Append-only `credit_ledger` with buckets + idempotency |
| Webhook | Parses plan/org from `receipt`; handles only `payment.captured` | Looks up our `payment_orders`; verifies amount/currency; dedupes; handles failed/refund; reconciliation |
| Plans | Pilot ₹0 / Pro ₹3,999 / Enterprise ₹9,999 | Hosted + Local SKUs (Section 5) |
| Deployment | Hosted control plane | Hosted, Hybrid, **Local-only** (Section 6) |
| LLM | Platform's key pool | Platform keys (hosted) **or** customer keys / local models (Local) |
| Extension | Chat-centric | Incident inbox + fixes + ask + account (Section 12) |
| Integrations | Slack/email alerts (basic) | + MCP server, GitHub App, Slack approvals |
| Sales assets | None | Audit CLI + report, pilot flow, license issuance, funnel metrics |

---

## 3. Architecture Additions

```
CUSTOMER ENVIRONMENT (Local / Hybrid)                         SKELION CLOUD (hosted / hybrid control plane)
┌──────────────────────────────────────────┐                  ┌───────────────────────────────┐
│ skelion-proxy (open-source, fail-open)   │                  │ Accounts, billing, licenses   │
│   ├─ capture + redaction (allow-list)    │                  │ Dashboard, admin console      │
│ skelion-agent (daemon, pro modules)      │  metadata only   │ GitHub App / Slack backend    │
│   ├─ analyzers, incident store (SQLite)  │ ───────────────► │ (hybrid: fingerprints+counts) │
│   ├─ replay sandbox runner               │   (opt-in)       └───────────────────────────────┘
│   ├─ LLM adapter → customer's LLM        │
│   ├─ license verifier (offline)          │      ┌────────────────────────────────────────┐
│   └─ MCP server / local HTTP API         │◄─────│ VS Code extension, GitHub App, Slack   │
└──────────────────────────────────────────┘      │ (talk to local daemon or hosted API)    │
                                                  └────────────────────────────────────────┘
```
- **Data plane** (capture, redaction, analysis, replay, LLM calls) can run entirely in the customer environment.
- **Control plane** (accounts, billing, license issuance, dashboard) is the hosted service. In Local mode it receives **nothing** except optional license check-ins (license_id + version).
- Local incident store: SQLite file (or Postgres if configured) with retention (default 7 days), size cap, rotation, encryption-at-rest option.

### Repo layout (open-core split)
```
/core            # OPEN SOURCE (default Apache-2.0): proxy, capture, redaction, basic audit, LLM adapter interface, schemas
/pro             # PROPRIETARY: fix generation, replay verification, PR bot, integrations, team features (license-gated)
/license         # license format, verifier lib (shared), issuer (server-side only)
/server          # hosted control plane
/extension /webview
/docs/specs  /docs/launch-evidence  /docs/runbooks
```
Decision default: license of `/core` = Apache-2.0 (log in DECISIONS.md; revisit before publishing).

---

## 4. Workstream A — Billing Correctness Migration (REVENUE-CRITICAL, do first)

Implement `SKELION_BILLING_PLANS_V2.md` §6–§8 in full. Summary of required behavior:

1. **New tables:** `payment_orders`, `payments`, `refunds`, `credit_ledger`, `webhook_events`, `coupons`, `coupon_redemptions`, `invoices`, `licenses` (Section 7), `audit_log`; org fields: `plan_id, plan_version, billing_status, plan_period_start, plan_period_end, grace_until, cancel_at_period_end, pilot_until, gstin, billing_name, billing_state`. Money in integer paise. UTC timestamps.
2. **Migrate existing data:** map `credits_total - credits_used` per org into ledger rows (reason `migration`, bucket `allowance`, expiry = new period end or 30 days). Map old plan names: `pilot→community`, `pro→hosted_team`, `enterprise→hosted_business`. Keep a rollback script.
3. **Checkout** (`POST /v1/billing/checkout`): server computes price (plan + coupon + GST), creates `payment_orders` row, creates Razorpay order with short `receipt` = our row id and `notes`. Never trust client amounts. Order expires in 30 min.
4. **Verify** (`POST /v1/billing/verify`): signature = HMAC-SHA256(`order_id|payment_id`, key_secret), constant-time compare; then fetch payment from Razorpay and run the same idempotent activation as the webhook.
5. **Webhook** (`POST /v1/webhooks/razorpay`): verify `X-Razorpay-Signature` on the RAW body → dedupe on `X-Razorpay-Event-Id` → enqueue → 200. Worker (transaction + row lock): `payment.captured`/`order.paid` → verify amount, currency, order state, org/plan from OUR row → apply entitlement idempotently; `payment.failed`, `refund.processed` handled; unknown events stored.
6. **Entitlements:** plan period fields set; renewal extends from `max(now, period_end)`; credits via ledger with `idempotency_key` (`period:{payment_id}` / `pack:{payment_id}`); packs never touch plan or usage.
7. **Scheduler:** expire pending orders/reservations (5 min); `active→grace(3d)→expired→community` (hourly); renewal reminders T-7/T-3/T-1 (daily); reconciliation vs Razorpay (daily); weekly unit-economics report.
8. **Credit consumption:** reserve → settle (V2 §8.5); store `cost_inr_est` on every usage event.
9. **Emails:** receipt, renewal reminders, low credits, payment failed, plan changed, license delivered (new).
10. **Invoices:** sequential numbers, GST fields, PDF, emailed on payment.
11. **Backward compatibility:** keep old endpoints as thin aliases (`/v1/billing/webhook` → new handler) until the extension update ships.

**Acceptance (must pass before enabling live payments):** V2 §15 tests, especially: duplicate webhook ×5 → one grant; wrong amount rejected; pack purchase leaves usage intact; 50 parallel runs at balance=estimate → exactly one reserves; reconciliation fixes a dropped webhook; no secrets in repo/logs (gitleaks).

---

## 5. Workstream B — Plans & Pricing (config-driven, versioned)

Plans live in DB/YAML (`plans` table, versioned). **Prices are proposals; keep editable. INR, excl. GST unless DECISIONS.md says otherwise.**

### 5.1 Hosted SKU (platform LLM, credits)
| Plan id | Price/mo | Credits | Requests | Seats | Projects |
|---|---|---|---|---|---|
| `hosted_community` | ₹0 | 100 | 1,000 | 1 | 1 |
| `hosted_developer` | ₹799 | 1,000 | 10,000 | 1 | 3 |
| `hosted_team` | ₹3,999 | 5,000 | 50,000 | 5 | 10 |
| `hosted_business` | ₹9,999 | 25,000 | 250,000 | 20 | 50 |
| `hosted_enterprise` | custom | custom | custom | custom | custom |

### 5.2 Local SKU (customer's LLM key or local model; **no credits**; priced per account/org)
| Plan id | Price/mo | Projects | Seats | Includes |
|---|---|---|---|---|
| `local_community` | Free | 1 | 1 | Open-source proxy + local `audit` command |
| `local_solo` | ₹999 (~$12; set USD separately, e.g. $19) | 1 | 1 | Fix proposals, replay verification |
| `local_team` | ₹4,999 (USD e.g. $79) | 5 | unlimited | + PR bot, Slack, MCP, team dashboard |
| `local_business` | ₹14,999 (USD e.g. $199) | 20 | unlimited | + SSO/MFA, audit log, auto-merge guardrails, priority support |
| `local_enterprise` | custom (from ~₹40k) | custom | unlimited | + SLA, SCIM, custom contract, dedicated help |

- Annual = 10× monthly (2 months free). Offer annual first for Local plans.
- Packs/credits apply to **Hosted** only.
- **Founding offer:** coupon `FOUNDING50`-style (30% off for 12 months, price-locked via `price_lock_until`, max redemptions 50, expiry date) valid for both SKUs.
- **Optional outcome pricing (pilot customers only, flagged):** ₹499 per merged verified fix, capped at plan price; metered from GitHub App `pull_request.closed(merged)` events with label `skelion-fix`; billed manually via Razorpay Payment Link/invoice at first (admin console action).
- Paid setup service: product `setup_fee` (₹5,000–15,000 one-time) purchasable via checkout `kind=service`.

### 5.3 Entitlements library (shared by server, daemon, extension)
Single package `entitlements` mapping `plan_id → {features, limits}` with functions `can(feature)`, `limit(name)`, `explain_denial()`. Features examples: `fix_generation, replay_verify, pr_bot, slack, mcp, team_dashboard, sso, audit_log, auto_merge, scim, priority_support`. Used identically by hosted API and local license verifier.

---

## 6. Workstream C — Deployment Modes & BYO LLM

### 6.1 Modes (config `deployment.mode`)
| Mode | Data leaves customer env? | LLM | Billing |
|---|---|---|---|
| `local` | **No** (except optional license check-in: license_id + version) | Customer's key or local model | License (Local SKU) |
| `hybrid` | Only whitelisted metadata (6.3) | Customer's | License + optional hosted dashboard |
| `cloud` | Yes (redacted) | Platform keys | Credits (Hosted SKU) |

Default for new self-installs: `local`. Telemetry/check-in **off by default** in `local`; clear opt-in prompt.

### 6.2 LLM adapter (BYO)
```yaml
llm:
  provider: openai_compatible   # openai_compatible | anthropic | google | azure_openai
  base_url: http://localhost:11434/v1     # Ollama, vLLM, LM Studio, or any OpenAI-compatible endpoint
  api_key_env: SKELION_LLM_KEY            # read from env or secret file; never persisted in DB, never sent to Skelion
  models:
    analysis: <model-id>
    fix: <model-id>
    cheap: <model-id>
  timeout_s: 60
  max_input_tokens: 24000
  max_output_tokens: 4000
```
Requirements:
- Provider interface with: streaming, tool/function calling when supported, JSON mode fallback, retries with jitter, circuit breaker, per-run token/step caps.
- **Startup self-test** (`skelion doctor`): checks connectivity, model availability, context size, tool-calling support; prints which features will be available (e.g., small local model → analysis only, fix generation disabled with a clear explanation).
- **LLM egress preview:** `skelion egress --dry-run` and a UI view show the exact redacted text that would be sent to the configured LLM for a given incident. Customers must be able to verify this.
- Reuse the existing key-pool/backoff code for multi-key customer setups.
- Prompt data minimization: send only redacted snippets and normalized route templates, never raw bodies/headers.

### 6.3 Hybrid metadata contract (strict allow-list)
Allowed fields only: `project_id, service_name, release/version, error_fingerprint (hash), error_class, http_status, route_template (ids normalized), latency_bucket, count, first_seen, last_seen, severity, fix_status`.
**Never sent:** request/response bodies, headers, query strings, IPs, user identifiers, source code, stack-trace text (only a hash), LLM prompts/outputs.
- Define the schema once (`egress_schema.json`); generate `EGRESS.md` for customers from it.
- **CI test** fails if any code sends a field not in the schema.
- `skelion egress --show-last` prints the last N payloads actually sent.

### 6.4 Resource & safety limits (local daemon)
CPU/memory caps and backpressure (drop capture before slowing traffic), disk cap with rotation (default 7-day retention), capture sampling rates, per-route exclusions (login/payment paths excluded by default), encryption-at-rest option for the incident store, bounded queue sizes. **Published overhead budget:** measure and document p50/p95 added proxy latency; set a target (default p95 < 5 ms added at 500 rps on reference hardware) and report actual numbers.

---

## 7. Workstream D — License System (offline-verifiable)

**License file** (JSON + detached Ed25519 signature, `kid` for key rotation):
```json
{
  "v": 1, "license_id": "lic_xxx", "org_id": "org_xxx", "sku": "local",
  "plan": "local_team", "limits": {"projects": 5}, "features": ["fix_generation","replay_verify","pr_bot","slack","mcp","team_dashboard"],
  "issued_at": "…", "expires_at": "…", "grace_days": 7,
  "customer": {"name": "…", "email": "…"}
}
```
- Private signing key lives in KMS/secret manager (never in repo); public keys embedded in `/license` verifier; support multiple `kid`s for rotation.
- **Issuance:** on verified payment (or admin action) create `licenses` row → sign file → email + download in dashboard (`GET /v1/licenses`, `GET /v1/licenses/{id}/download`). Renewal issues a new file with extended expiry.
- **Verification:** daemon verifies locally at startup and daily; no network required. Optional (opt-in) online refresh: sends only `license_id` + version; may fetch a small revocation list.
- **Expiry behavior (critical):** after `expires_at + grace_days`, **degrade features to `local_community`**, show a clear banner, **never stop proxying or break traffic**.
- **Project limit:** daemon keeps a registry of `project_id`s; when over the limit, extra projects get community features only, with a clear message. Never block traffic.
- Tamper handling: invalid signature → community features + warning. Do not over-invest in anti-piracy; honest customers are the goal.
- `licenses`, `license_events` tables: issued/renewed/revoked/downloaded.
- Admin console: issue/revoke/extend, view license history.

---

## 8. Workstream E — Audit CLI (the sales magnet) — HIGH PRIORITY

Command: `skelion audit --since 48h --source <type> --out ./skelion-report [--format html,md,pdf] [--project <name>]`
Everything runs **locally**; **no network calls by default** (LLM step only if configured and approved).

### 8.1 Inputs ("sources")
- `nginx` (combined/JSON), generic `jsonl` application logs (configurable field map), HAR files, Skelion proxy capture (shadow mode), error-tracker export (e.g., JSON export from Sentry/others), plain access logs.
- **Shadow mode proxy:** read-only/mirrored capture, `--shadow` flag; never alters responses; fail-open; excluded routes by default; sampling.

### 8.2 Pipeline
1. **Ingest & normalize** (route templating, status, latency, timestamp, service, version).
2. **Redact first** (Section 8.4) before anything is stored or shown.
3. **Analyzers:** error clustering/fingerprints; 4xx/5xx spikes and new-error-after-deploy detection; latency regressions (p95 by route); **silent failures** (HTTP 200 with error-shaped bodies, schema/shape drift, empty responses); retry storms; upstream/LLM-provider failures (429/5xx/timeouts) and wasted retries; cost estimate when LLM usage is visible.
4. **Rank** issues by estimated user impact (affected requests, routes' traffic share, error rate, recency).
5. **Proposed fix (one):** if `--repo <path>` provided and an LLM is configured: generate a patch for the top issue; **verify by replay** (Section 9); attach evidence. If no LLM/repo: provide a precise diagnosis and a suggested investigation checklist instead.
6. **Render report.**

### 8.3 Report template (one page + appendix)
1. **Header:** project, period, data source, counts analyzed, "Generated locally; nothing uploaded."
2. **Executive summary (business language):** "3 issues are likely affecting customers right now", estimated % of requests affected, risk level.
3. **Top 5 issues** table: title, routes, first/last seen, affected requests, severity, confidence.
4. **Issue #1 detail:** evidence (redacted samples), likely cause, blast radius, **proposed fix with replay result** ("passed 482/482 replayed requests; 0 regressions") or investigation steps.
5. **Next steps** checklist + how to enable continuous monitoring (CTA with pilot license instructions).
6. **Appendix:** methodology, redaction summary (what was removed), limitations, environment.
HTML (self-contained, printable) is required; Markdown and PDF optional. Include a `findings.json` the customer may choose to share (contains no raw samples).

### 8.4 Redaction (must be best-in-class and tested)
- Allow-list approach for headers/body fields; drop everything else.
- Pattern scrubbers: emails, phone numbers, JWTs, API keys/tokens (provider prefixes, high-entropy strings), card numbers (Luhn), bearer/basic auth, cookies, IPs, UUID/ID normalization in paths, Indian ID formats (PAN, Aadhaar-like) and common national-ID patterns.
- Redaction runs **before** persistence, before LLM calls, before report rendering.
- Test suite with synthetic secret fixtures; CI fails if any fixture secret appears in outputs, logs, or LLM payload previews. Include fuzz/property tests.

### 8.5 Acceptance
- Run on 3 synthetic datasets with planted issues (silent 200-with-error, post-deploy regression, LLM 429 storm): top issue is found in ≥ 2 of 3 with correct ranking; zero planted secrets leak; report generated in < 2 minutes for 1M log lines on reference hardware (document actual).
- Works offline (verify with network disabled).
- Report reviewed by a human for clarity (non-engineer can understand the executive summary).

---

## 9. Workstream F — Replay Verification & Fix Proposals (reuse existing replay generation)

- **Record → replay:** from captured (redacted) requests, build replay sets keyed by route; for verification run the **patched build in an isolated sandbox** (container), never against production or customer databases.
- **Safety rules:** replay only idempotent methods by default (GET/HEAD/OPTIONS); non-idempotent allowed only via explicit allow-list with mocked dependencies; outbound network disabled/mocked; time/random seeded; secrets stubbed; resource and time limits.
- **Verification result object:** `{requests_replayed, passed, failed, regressions, latency_delta, flaky_count, coverage_of_routes, confidence}`; attach to the fix card and PR body.
- **Fix generation:** LLM produces a minimal diff; run project tests (if configured) + replay; reject fixes that fail; cap steps/tokens; always human approval before PR (auto-merge only for Business+/opt-in with guardrails: green CI, verification passed, diff size limit, protected paths excluded, one-click revert PR).
- **Confidence scoring:** explain factors (tests passed, replay coverage, diff size, touched paths).

---

## 10. Workstream G — Integrations

### 10.1 MCP server (`skelion-mcp`)
- Transports: stdio and local HTTP. Read-only by default. Works against the local daemon (Local) or hosted API (Cloud) with scoped tokens.
- Tools: `list_incidents(since, severity)`, `get_incident(id)`, `get_service_health(project, window)`, `get_fix_status(incident_id)`, `get_top_errors(route|service)`, `explain_incident(id)` (returns redacted summary), `propose_fix(incident_id)` (write action: requires explicit enablement + confirmation).
- Provide **verified setup docs** for Claude Code, Cursor, and other MCP-capable clients (agent must confirm each client's current config format from official docs; do not assume). Test with at least two real clients; for Antigravity, verify MCP/extension support and document the result honestly.

### 10.2 GitHub App
- Permissions minimal (read repo contents, PRs, checks; write PR comments/branches). Features: **PR diagnostic card** (Hosted/Local), **fix PRs** with replay evidence in body and `skelion-fix` label, **check run** showing verification result, merge events → `merged_fix_events` (idempotent).
- Webhook signature verification; installation tokens short-lived; per-repo opt-in; kill switch.

### 10.3 Slack bot
- Incident alert cards with severity, affected routes, link; buttons: Approve fix / Reject / Snooze; slash command `/skelion status`. Verify request signatures; respond within Slack time limits; retries idempotent.

---

## 11. Workstream H — Hosted Dashboard & Admin Console Additions

- **Customer dashboard (web):** account, plan/period, credits (Hosted) or license + projects (Local), invoices, license download, deployment-mode help, "doctor" results (optional upload of non-sensitive doctor output).
- **Admin console (internal, GitHub login + allowlist + 2FA):** issue/extend/revoke licenses; grant credits; extend/end pilots; view ledger; replay webhooks; coupon management; funnel metrics; merged-fix counts and outcome-billing queue; kill switches. All actions audit-logged.
- **Funnel metrics:** audits run (opt-in counter or self-reported), audit → pilot → paid conversion, activation (first incident viewed), time-to-first-value, fix acceptance (merge) rate, MRR, gross margin per credit (Hosted), support tickets per customer.

---

## 12. Workstream I — Extension Re-scope (incident-first)

Keep existing auth, secret storage, webview security, update gating. Re-scope UI:

| Tab | Purpose |
|---|---|
| **Incidents** | Ranked list (severity, routes, affected %, first/last seen), filters, status; click → detail |
| **Fixes** | Proposed diffs with **replay evidence** card, confidence, blast radius, Approve / Reject / Revert; opens VS Code diff view; creates PR via GitHub App |
| **Ask** | Chat scoped to an incident or service ("why did /checkout fail after 14:05?") using the configured LLM; shows credit cost estimate (Hosted) |
| **Account** | Plan, period end, credits by bucket (Hosted) or license status + project usage (Local), Renew/Upgrade/Buy credits/Download license, deployment mode |
| **Settings** | Deployment mode, daemon URL (localhost), LLM provider status (`doctor` results), approval mode, telemetry opt-in |

- Connection model: Local/Hybrid → talks to the local daemon on localhost (authenticated with a local token); Cloud → hosted API (existing GitHub sign-in). Show a clear connection status chip.
- States: no daemon found (guided install), license expired/degraded banner, LLM misconfigured (link to `doctor`), offline, over project limit.
- Keep the generic chat only as the **Ask** tab; remove marketing that implies it competes with Cursor/Copilot chat.
- Accessibility/theme requirements from the master plan still apply.

---

## 13. Workstream J — Pilot Program & Outreach Tooling

- `organizations.pilot_until`; pilot grants: Hosted = 300-credit `grant` bucket expiring at pilot end; Local = 14-day pilot license (`pilot=true` claim) with Team features. Auto-downgrade at end; no silent extension.
- **Pilot emails (templates in admin console, editable):** Day 0 welcome + setup, Day 3 check-in, Day 5 founding offer (72-hour coupon), Day 7/14 results summary (incidents found, fixes verified/merged) + one-click pay link.
- **Pilot health dashboard:** per pilot: setup completed, incidents seen, fixes proposed/approved, last active.
- Referral capture: field in pilot wrap-up ("who else should see this?").
- Collect willingness-to-pay answers (4 pricing questions) in a short form; store results for analysis.

---

## 14. Security, Privacy & Supply Chain

- **Threat model doc** (`SECURITY.md`): untrusted logs/prompts (prompt injection via log content must not trigger tool actions: treat all captured data as untrusted, never as instructions), license tampering, malicious replay data, SSRF via configurable URLs, secrets in logs, daemon local API exposure.
- Daemon local API binds to `127.0.0.1` by default with a random local token; CORS locked; CSRF protections.
- Prompt-injection defenses: captured content is quoted/fenced as data; tools exposed to the LLM are least-privilege; write actions need human approval; output validation.
- Supply chain: reproducible builds, signed container images (e.g., cosign) and checksums, SBOM, dependency pinning and scanning, release provenance.
- Documents to produce: **Privacy policy, security one-pager, EGRESS.md, DPA template, vulnerability disclosure policy, data retention table.** (Skip SOC 2 for now; be honest and specific instead.)
- Secrets: gitleaks in CI; CI guard that fails if live Razorpay keys appear outside prod config.

---

## 15. Reliability & Scale Deltas

- Keep all items from `VSCODE_EXTENSION_MASTER_PLAN.md` §22. Additional:
- Daemon: graceful shutdown, crash-safe incident store, bounded memory, health endpoint, self-diagnostics (`skelion doctor`), auto-update channel with signature check (opt-in).
- Hosted control plane: license issuance and billing remain available if analysis/LLM services are down (isolate failure domains).
- Load/chaos tests (store reports in `/docs/launch-evidence`):
  | Test | Pass criteria |
  |---|---|
  | Proxy under 500 rps for 30 min with capture on | No traffic errors added; p95 overhead within published budget; memory flat |
  | Daemon killed/restarted mid-traffic | Proxy keeps forwarding; capture resumes; no corruption |
  | Disk full | Capture stops gracefully, alerts; traffic unaffected |
  | License expired / invalid / missing | Features degrade to community; traffic unaffected |
  | LLM down/slow | Analysis degrades; no traffic impact; clear UI message |
  | Webhook storm (1,000 events, 30% dupes, shuffled) | Final state identical to ordered single delivery |
  | 50 parallel credit runs at limit | Exactly the allowed number succeed |

---

## 16. Testing, Evidence & Definition of Done

**Test layers:** unit (ledger math, entitlements, license verify, redaction), integration (Razorpay test mode end-to-end, GitHub App sandbox, Slack signature), e2e (install proxy → run audit → view incident in extension → approve fix → PR with evidence), security (secret-leak fixtures, injection fixtures), performance (Section 15), manual matrix (Windows/macOS/Linux, VS Code + at least one fork, Docker and bare-metal install, offline mode).

**Definition of Done (all required; evidence in `/docs/launch-evidence`):**
- [ ] AUDIT_P2.md, DECISIONS.md, PROGRESS.md, FINAL_REPORT.md exist and are accurate
- [ ] Billing V2 tests pass; one real small live payment + refund verified before public launch
- [ ] Ledger balance == SUM(entries) nightly check green; reconciliation job proven
- [ ] Local mode works with network disabled (audit + incidents + fix proposal using a local model or customer key)
- [ ] `skelion egress` shows exactly what leaves; hybrid schema CI test enforced
- [ ] License issued after payment, verified offline, expiry degrades gracefully without breaking traffic
- [ ] Audit CLI meets 8.5 acceptance on synthetic datasets; sample report included in docs
- [ ] MCP server tested with ≥2 real clients; GitHub App and Slack flows tested
- [ ] Extension incident-first UI verified at 280px/600px, light/dark/high-contrast, keyboard-only
- [ ] Load/chaos table (Section 15) passed with reports
- [ ] Security docs published; gitleaks/dependency/SAST scans clean; signed releases
- [ ] Runbooks: webhook backlog, license issuance failure, LLM outage, daemon crash, key rotation, bad release rollback, "paid but not upgraded"
- [ ] Pilot flow end-to-end tested (grant → emails → founding coupon → payment → license/credits → downgrade on expiry)
- [ ] Kill switches tested in staging

`FINAL_REPORT.md` must map every outcome in Section 0 to evidence links.

---

## 17. Execution Order (fits a ~5-week window; ship revenue-critical slices first)

**Slice 1 — Money safety + magnet (days 1–7)**
1. AUDIT_P2.md. 2. Billing correctness (Section 4) with migration + tests. 3. Redaction library + tests. 4. Audit CLI MVP: nginx/jsonl sources, analyzers, ranked issues, HTML report (no LLM fix yet).
*Gate:* billing acceptance tests pass; audit runs on synthetic datasets offline. → Outreach can start now using the audit.

**Slice 2 — Local mode + licenses (days 8–16)**
5. LLM adapter + `doctor` + egress preview. 6. Local daemon packaging (Docker + binary), incident store, shadow-mode proxy. 7. License format/issuer/verifier + issuance after payment + dashboard download. 8. Local plans/entitlements/pricing config, founding coupon, annual option.
*Gate:* local-only e2e works offline; license expiry degrades safely.

**Slice 3 — Fix verification + integrations (days 17–25)**
9. Replay sandbox + fix generation + evidence + confidence. 10. GitHub App (PR cards, fix PRs, merged-fix events). 11. MCP server + client docs. 12. Slack alerts + approvals.

**Slice 4 — Extension + pilot tooling (days 26–32)**
13. Incident-first extension. 14. Pilot flow, emails, admin console additions, funnel metrics. 15. Security docs, runbooks, load/chaos tests, release signing.

**Slice 5 — Launch hardening (days 33–37)**
16. Live-mode checklist, real payment + refund test, FINAL_REPORT.md, release to Marketplace + Open VSX (pre-release → stable).

**Cut list if time slips (in this order):** hybrid mode → Slack approvals → outcome-based billing automation → SCIM/SSO/Enterprise features → auto-merge → PDF output → Razorpay Subscriptions/Stripe. **Never cut:** billing correctness, redaction, fail-open guarantees, license graceful degradation, audit CLI.

---

## 18. Defaults the Agent Should Use (log in DECISIONS.md; I can override)

1. Core license Apache-2.0; pro modules proprietary.
2. Default mode for self-install: `local`; telemetry/check-in off.
3. Prices as in Section 5 (editable config); annual = 10× monthly; GST-exclusive display until decided.
4. Pilot: 7 days hosted / 14 days local; founding coupon 30% for 12 months, 72-hour window.
5. Retention (local): 7 days, 2 GB cap.
6. Grace after expiry/non-renewal: 3 days (hosted pass) / 7 days (local license).
7. Replay: idempotent methods only unless allow-listed.
8. Capture excludes login/payment/auth routes by default.
9. Auto-merge disabled by default everywhere.
10. Razorpay Orders-first; Subscriptions after first 10 paying customers.

---

## Appendix A — Outreach Kit (for the founder; admin console may seed email templates from these)

**DM 1 (cold-warm, personal):**
"Hey [Name], quick one. I'm building something that finds what's silently breaking in production and proposes a fix verified on real traffic. It runs on your side, nothing leaves your infrastructure, and it works alongside Cursor/Claude Code. Could I run a free 48-hour health audit for [Company]? Takes ~10 minutes to set up."

**DM 2 (after reply):**
"Great. Who on your team handles production issues? I'll send a one-command setup. The report is generated on your machine; you decide whether to share anything."

**DM 3 (follow-up after no reply, 4–5 days):**
"Not pushing. If production incidents aren't a pain right now, no worries. If they are, I'd love to show you what the audit finds. I'll share the sample report first."

**15-minute call script:** (1) How do you find out about production issues today? (2) Last incident: cost, time to fix, who was paged? (3) What stops you trusting a tool near production? (4) Show sample report. (5) Offer pilot + founding price + paid setup. (6) Ask for the engineer to join and for 2 intros.

**Objection answers:** "We use Cursor/Claude Code" → "Great, keep them. Skelion gives them production context via MCP." · "We can't share logs" → "Nothing leaves your machine; `skelion egress` proves it." · "Security review?" → send SECURITY.md, EGRESS.md, DPA. · "Price?" → founding price, annual discount, pay-per-merged-fix option for pilots.

**Pilot emails:** Day 0 (setup steps, what to expect), Day 3 (what we found so far, ask for feedback), Day 5 (founding offer, 72 hours), Day 7/14 (results summary, pay link).

---
**End.** Begin with `AUDIT_P2.md`. Do not enable live payments until Slice 1 acceptance tests pass. Report progress in `PROGRESS.md` after every slice.
