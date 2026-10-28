# Architectural Decisions Log (DECISIONS.md)

### D1: Plan Tiers, Currency, and Credits
- **Decision**: Primary recurring subscription tiers are set in INR via Razorpay:
  - **Pilot**: ₹0 / month, 100 Credits, 1,000 requests monthly quota.
  - **Pro**: ₹3,999 / month, 5,000 Credits, 50,000 requests monthly quota.
  - **Enterprise**: ₹9,999 / month (base), 25,000 Credits, customizable SLA and seat management.
- **Rationale**: Aligns with existing `skelion_agent/plan_config.py` and complies with Indian e-mandate and Razorpay domestic billing guidelines. International USD payments can be processed through Stripe or one-time Razorpay passes.

### D2: Authentication Model & First-Time Flow
- **Decision**: GitHub OAuth (`read:user`, `user:email`) initiated from VS Code's `vscode.authentication` API. The token is sent to `POST /v1/auth/github` where the backend validates against GitHub, creates or updates the Organization/User, and automatically assigns the **Pilot** (Free) tier with 100 credits for new sign-ups.
- **Rationale**: Zero manual password entry in extension, instant onboarding, server-controlled identity issuance.

### D3: Tool Execution & Sandbox Boundaries
- **Decision**: The LLM agent loop runs on the backend server (`POST /v1/chat`), but file/terminal operations execute on the user's local machine via the extension's `AgentBridge`.
- **Rationale**: The backend never requires raw filesystem access to client machines. File edits generate side-by-side diff previews with explicit user acceptance/rejection. Command runs in integrated terminal require user approval.

### D4: Webhook as Source of Truth & Outbox Pattern
- **Decision**: Payment activation occurs strictly upon verified HMAC-SHA256 signature on the raw payload in `POST /v1/billing/webhook`. The client-side return or checkout redirect only acts as an optimistic trigger to fetch `/v1/me`.
- **Rationale**: Prevents client tampering and guarantees consistent state across distributed instances.

### D5: Open-Core Licensing Split
- **Decision**: Core proxy, capture, redaction engine, and basic audit CLI are licensed under Apache-2.0 (`/core`). Advanced fix generation, replay verification sandbox, PR bot, and Slack integrations are proprietary (`/pro`).
- **Rationale**: Maximizes developer trust and adoption while protecting monetization.

### D6: Default Deployment Mode: Local-First & Zero Egress
- **Decision**: Default deployment mode is `local`. Zero telemetry or network egress is enabled unless explicitly opted-in by the user. `skelion egress` command provides full cryptographic visibility into outbound metadata.
- **Rationale**: Enables adoption by enterprises, fintechs, and security-conscious engineering teams who refuse cloud log ingestion.

### D7: Final Proposal v3 Pricing & 30-Day Prepaid Passes
- **Decision**: Adopt the v3 two-stream pricing model (`SKELION_PRICING_AND_BILLING_FINAL.md`):
  - **Hosted (credits-metered)**: Community (₹0 / 50 credits), Developer (₹799 / 800 credits), Team (₹3,999 / 4,500 credits), Business (₹9,999 / 12,500 credits).
  - **Local (on-prem / BYO-LLM)**: Community (₹0), Solo (₹999 / $19), Team (₹4,999 / $79 / unlimited seats), Business (₹14,999 / $199).
  - **Credit Value & Cost Rule**: 1 Credit = ₹1 usage value; debited at `actual_cost × 3` to ensure a guaranteed 60%–67% gross margin.
  - Subscriptions structured as 30-day (or 365-day annual = 10 months paid, 12 months granted) prepaid passes via Razorpay Orders.
- **Rationale**: Eliminates e-mandate card failures, shields against LLM token inflation, and undercuts Sentry Seer ($40/contributor/mo ≈ ₹17,000 for 5 devs) and Cursor Teams ($40/user/mo) by 75%.

### D8: Append-Only Credit Ledger & Idempotency
- **Decision**: Replace mutable `credits_total` and `credits_used` counters with an immutable `credit_ledger` table. All credit grants, reservations, settlements, and expirations are recorded as distinct ledger entries with unique idempotency keys.
- **Rationale**: Prevents double-spend, race conditions, and duplicate webhook activations.

### D9: Offline Cryptographic Licensing via Ed25519
- **Decision**: Offline airgapped deployments use Ed25519 digitally signed `.skelion.license` files with a 7-day grace period. On expiry past grace, the system degrades gracefully to `local_community` free mode; proxy traffic is NEVER halted or broken.
- **Rationale**: Strict fail-open guarantee ensures zero disruption to production systems while giving customers ample renewal time.

### D10: Sandboxed Replay Verification Safety Policy
- **Decision**: Automated replay testing strictly permits only idempotent HTTP methods (GET, HEAD, OPTIONS) by default. Non-idempotent methods require explicit per-route allow-listing. All outbound external egress in the replay sandbox is mocked.
- **Rationale**: Eliminates the risk of replay tests triggering unintended third-party mutations, charges, or database side effects.

### D11: The Model Context Protocol (MCP) Integration Vector
- **Decision**: Rather than competing against Cursor or Claude Code as a raw chat tool, Skelion acts as a specialized production intelligence server via MCP, providing real error traces, service health, and verified diffs to existing AI coding assistants.
- **Rationale**: Avoids commodity chat competition; turns competitors into distribution partners.

### D12: Incident-First VS Code Extension Re-Scope
- **Decision**: Reorganize extension sidebar into 5 focused workflows: Incidents, Replay-Verified Fixes, Ask, Limits, and Pricing.
- **Rationale**: Centers developer experience around actionable production problems rather than generic conversational prompts.

