# Skelion VS Code Extension & Billing Platform — Comprehensive Implementation Plan

> **Plan Status:** Ready for Phased Execution  
> **Source Documents Referenced:**
> 1. `VSCODE_EXTENSION_MASTER_PLAN.md` (Master Build, Security, Scalability, and Launch Specification)
> 2. `BILLING_PLANS_AND_SUBSCRIPTION_MODEL.md` (Skelion & GossipMesh Commercialization & Entitlements)
> 3. Active Codebase: `g:\My Drive\helios` (`skelion_agent`, `skelion_edge`, `gossipmesh_engine`, `vscode_extension`, `skelion_vscode_extension`)

---

## 1. Executive Summary & Architecture Synthesis

This implementation plan bridges the existing backend engine (`skelion_agent` FastAPI control plane, `skelion_edge` proxy, and `gossipmesh_engine` resilience key-pool) with a commercial-grade VS Code extension and an automated Razorpay subscription management system.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VS CODE EXTENSION CLIENT                           │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ Activity Bar: Skelion Agent Panel (Webview View Provider)              │  │
│  │ Screens:                                                               │  │
│  │  1. Sign In (GitHub Auth via vscode.authentication)                    │  │
│  │  2. Agent Chat (Streaming responses, @file context, Model Picker)     │  │
│  │  3. Agent Operations (Diff Cards, WorkspaceEdit, Terminal Run Approvals)│ │
│  │  4. Usage Meter (Realtime day/month quotas & token counters)           │  │
│  │  5. Subscription & Billing Tab (Pilot / Pro / Enterprise cards)        │  │
│  └───────────────────────────────────┬────────────────────────────────────┘  │
│                                      │ postMessage (Typed JSON-RPC Protocol)  │
│  ┌───────────────────────────────────▼────────────────────────────────────┐  │
│  │ Extension Host (TypeScript, Strict)                                    │  │
│  │  • AuthService (SecretStorage, JWT memory cache, Session Refresh)      │  │
│  │  • ApiClient (SSE stream handler, retry with jitter, auth interceptor) │  │
│  │  • AgentBridge (Local tool execution: read_file, diff edit, run_cmd)   │  │
│  │  • Razorpay UriHandler callback: vscode://skelion.agent/billing/return │  │
│  └───────────────────────────────────┬────────────────────────────────────┘  │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │ HTTPS (Bearer JWT / SSE)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    SKELION FASTAPI BACKEND CONTROL PLANE                    │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ Routers & Gateway:                                                     │  │
│  │  • /v1/auth/github & /v1/auth/refresh (Upsert user, assign Pilot free) │  │
│  │  • /v1/me, /v1/me/usage (Atomic quota verification)                    │  │
│  │  • /v1/chat (SSE streaming, agent loop orchestration, tool invocation) │  │
│  │  • /v1/billing (Checkout order generation, webhook signature check)    │  │
│  └───────────────────┬────────────────────────────────┬───────────────────┘  │
│                      │                                │                      │
│        ┌─────────────▼────────────┐      ┌────────────▼─────────────┐        │
│        │ SQLite / PostgreSQL DB   │      │ Redis State & Key-Pool   │        │
│        │  • organizations         │      │  • Atomic Quota Counters │        │
│        │  • users / sessions      │      │  • Active Chat Run State │        │
│        │  • subscriptions         │      │  • GossipMesh Key-Pool   │        │
│        │  • payments / webhooks   │      │    (429 exponential back)│        │
│        │  • incidents / agent_runs│      └──────────────────────────┘        │
│        └──────────────────────────┘                                          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
           ┌───────────────────────────┴───────────────────────────┐
           │                                                       │
┌──────────▼───────────────┐                             ┌─────────▼──────────────┐
│   Razorpay Gateway API   │                             │ LLM Upstream Providers │
│  • Orders & Subscriptions│                             │  • OpenAI, Anthropic,  │
│  • HMAC-SHA256 Webhooks  │                             │    Gemini, Ollama      │
└──────────────────────────┘                             └────────────────────────┘
```

---

## 2. Requirements Traceability Matrix (RTM)

| ID | Requirement Specification | Architecture Component | Implementation File / Target | Verification & Acceptance Proof |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | VS Code extension packaged & installable | Extension Host / Build | `skelion_vscode_extension` & `skelion-vscode-0.1.0.vsix` | Clean `code --install-extension` with no missing entrypoint errors. |
| **R2** | Side-panel Activity Bar UI (Codex/Copilot bar) | Webview View Provider | `src/views/SidebarProvider.ts` + Webview | Rendered sidebar across light/dark themes at 280px and 600px widths. |
| **R3** | Sign in with GitHub first screen | Auth UX Flow | Webview SignIn Screen + `AuthService.ts` | First install displays GitHub login; chat composer is inaccessible until authenticated. |
| **R4** | Auto profile creation on first login | Server Auth Route | `POST /v1/auth/github` in `skelion_agent/auth_routes.py` | New GitHub ID generates a new user/org record in DB; repeat login reuses record. |
| **R5** | Auto-assignment of Pilot (Free) plan | Entitlements Engine | `POST /v1/auth/github` + `plan_config.py` | New user record defaults to `plan='pilot'`, `credits_total=100`, `credits_used=0`. |
| **R6** | Agent chat with local tool execution | Streaming Gateway & AgentBridge | `POST /v1/chat` (SSE) + `src/agent/AgentBridge.ts` | Agent streams response, emits `tool_call`, extension executes file read/diff edit, user accepts. |
| **R7** | Model picker with plan gating | Model Router & Webview | `GET /v1/models` + UI Picker Dropdown | Free users see locked badge on advanced models; Pro/Enterprise unlocks full suite. |
| **R8** | Usage meter & credit display | Quota Enforcement | `GET /v1/me/usage` + UI Usage Bar + Status Bar | Realtime remaining credit counter decrements upon tool/chat runs. |
| **R9** | Subscription management panel | Billing Webview | Webview Billing Tab + `billing_routes.py` | Lists Pilot (₹0), Pro (₹3,999), Enterprise (₹9,999); shows active status and renewal dates. |
| **R10**| Secure payment verification & live upgrade | Razorpay Webhook & Signature | `POST /v1/billing/webhook` + HMAC-SHA256 | Valid webhook on `payment.captured` upgrades plan and refills credits instantly without editor restart. |
| **R11**| Reuse existing Razorpay & backend code | Backend Integration | `skelion_agent/billing_routes.py` & `razorpay_service.py` | Zero secret leaks in client; secrets read strictly via `os.getenv`. |
| **R12**| Monitor incidents, GossipMesh & logs | Telemetry & Observability | `skelion_agent/metrics_router.py` + Webview Tab | `/metrics` Prometheus counters and incident diagnostic reports displayed in UI. |
| **R13**| High resilience & fail-open guarantees | Edge Proxy & Key Pool | `skelion_edge/proxy.py` + `key_pool.py` | HTTP 429 from model providers triggers backoff; proxy fails open on exceptions. |

---

## 3. Plan Tiers & Entitlement Specifications

Derived from `BILLING_PLANS_AND_SUBSCRIPTION_MODEL.md` and `plan_config.py`:

```python
PLAN_DEFINITIONS = {
    "pilot": {
        "name": "Pilot (Free)",
        "price_inr": 0,
        "credit_quota": 100,
        "monthly_request_quota": 1000,
        "models": ["gpt-4o-mini", "gemini-1.5-flash"],
        "max_context_tokens": 32000,
        "agent_tools": ["read_file", "search_text", "get_diagnostics"],
        "history_retention_days": 7
    },
    "pro": {
        "name": "Pro",
        "price_inr": 3999,
        "credit_quota": 5000,
        "monthly_request_quota": 50000,
        "models": ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"],
        "max_context_tokens": 128000,
        "agent_tools": ["read_file", "edit_file", "create_file", "run_command", "search_text"],
        "history_retention_days": 90
    },
    "enterprise": {
        "name": "Enterprise",
        "price_inr": 9999,
        "credit_quota": 25000,
        "monthly_request_quota": 250000,
        "models": ["all"],
        "max_context_tokens": 200000,
        "agent_tools": ["all"],
        "history_retention_days": 365
    }
}
```

---

## 4. Phase-by-Phase Implementation Roadmap

### Phase 1: Backend Auth, Entitlements & Streaming Gateway Refinement
**Estimated Duration: 2 Days**
1. **GitHub OAuth Server Endpoint (`POST /v1/auth/github`)**:
   - Accept `access_token` from VS Code's `vscode.authentication.getSession('github', ...)`.
   - Query GitHub API (`https://api.github.com/user` & `/user/emails`) to verify identity.
   - Upsert `Organization` / user record by GitHub ID.
   - If newly created: automatically assign `plan="pilot"`, `credits_total=100`, `credits_used=0`.
   - Generate short-lived JWT (15 minutes) + rotating refresh token stored in DB/Redis.
2. **Quota & Usage Endpoint (`GET /v1/me/usage`)**:
   - Return `{ plan, credits_total, credits_used, credits_remaining, quota_remaining, reset_at }`.
   - Implement atomic Redis reserve-then-settle mechanism for active chat requests.
3. **SSE Chat Streaming Gateway (`POST /v1/chat`)**:
   - Accept user prompt, conversation history, and context (`@file`, selection).
   - Verify plan entitlement (check model access & credit balance).
   - Stream SSE events:
     - `event: delta` → text stream chunk
     - `event: tool_call` → `{ id, name, args }` (for file edits, commands)
     - `event: usage` → `{ credits_deducted, tokens_used }`
     - `event: done` → completion marker
4. **Tool Result Callback (`POST /v1/chat/tool-result`)**:
   - Accept local execution output from extension and resume agent loop.

### Phase 2: Razorpay Production Billing & Webhook Verifier
**Estimated Duration: 1.5 Days**
1. **Order & Subscription Creation (`POST /v1/billing/checkout`)**:
   - Validate plan against `PLAN_DEFINITIONS`.
   - Create Razorpay Order/Subscription with receipt `{org_id}:{plan}:{timestamp}`.
   - Return checkout details to launch external browser checkout.
2. **HMAC-SHA256 Raw Webhook Handler (`POST /v1/billing/webhook`)**:
   - Compute signature on raw bytes using `os.getenv("RAZORPAY_WEBHOOK_SECRET")`.
   - Idempotency guard: Record `X-Razorpay-Event-Id` into `webhook_events` table; ignore duplicates.
   - On `payment.captured` or `subscription.activated`:
     - Extract `org_id` and `plan` from receipt/notes.
     - Atomically update `Organization.plan = plan_name`, `credits_total = quota`, `credits_used = 0`.
     - Invalidate Redis subscription cache.
     - Emit SSE event to trigger instant live panel update.
3. **Reconciliation Job**:
   - Background worker task checking unconfirmed checkout sessions against Razorpay REST API every 15 minutes.

### Phase 3: VS Code Extension Core Architecture & Clean Packaging
**Estimated Duration: 1 Day**
1. **Fix Packaging & Entry Point Architecture**:
   - Structure `skelion_vscode_extension`:
     - Clean `package.json` with `"main": "./out/extension.js"`.
     - Output compilation directly to `./out/`.
     - `.vscodeignore` excluding source files, tests, and unnecessary metadata.
     - Verify packaging with `vsce package` producing valid VSIX archive.
2. **`AuthService.ts`**:
   - Implement `vscode.authentication.getSession('github', ['read:user', 'user:email'])`.
   - Store JWT in memory; persist refresh token in `context.secrets` (SecretStorage).
   - Automatic token refresh on 401 response.
3. **`ApiClient.ts`**:
   - Handle typed HTTP requests and SSE event streaming with exponential backoff.
4. **`AgentBridge.ts`**:
   - Local tool execution sandbox:
     - `read_file` (via `vscode.workspace.fs`)
     - `edit_file` / `create_file` (via `vscode.WorkspaceEdit` with side-by-side `vscode.diff` review)
     - `run_command` (in VS Code Integrated Terminal with explicit user confirmation)
     - Security bounds: prevent editing outside workspace or reading `.env` / secret files.

### Phase 4: Side-Panel Webview UI / UX Implementation
**Estimated Duration: 2.5 Days**
1. **Activity Bar & Sidebar Container**:
   - Native dark/light theme integration via `--vscode-*` CSS tokens.
2. **Screen 1: Sign-In Screen**:
   - Clean GitHub branding, value proposition bullets, and "Sign in with GitHub" CTA.
3. **Screen 2: Chat & Agent Operations**:
   - Streaming markdown message list with code block copy & apply actions.
   - Diff preview cards with Accept / Reject buttons.
   - Context chip attachments (`@file`, cursor selection).
   - Model picker dropdown with visual tier badges (Pilot vs Pro vs Enterprise).
4. **Screen 3: Usage & Limits Footer**:
   - Interactive usage meter bar showing credits used vs remaining.
   - Friendly upgrade prompt when credits dip below 10%.
5. **Screen 4: Billing & Subscription Tab**:
   - Plan comparison cards (Pilot ₹0, Pro ₹3,999, Enterprise ₹9,999).
   - "Upgrade Plan" button opening external checkout.
   - Realtime status transition: *Waiting for payment...* → *Confirming with bank...* → *Plan Active!*
6. **Screen 5: Incidents & GossipMesh Observability**:
   - Visual display of active edge incidents, synthetic replay test status, and Prometheus rate-limit savings.

### Phase 5: Verification, End-to-End Testing & Hardening
**Estimated Duration: 1.5 Days**
1. **End-to-End Flow Validation**:
   - Clean install of VSIX on VS Code.
   - GitHub Sign-in → Profile creation → Pilot 100 credits granted.
   - Prompt chat → Stream code → Propose file edit → Accept diff → Credits deducted.
   - Click Upgrade → Trigger Razorpay test payment → Webhook captures event → Plan switches to Pro in UI live without reload.
2. **Security & Secrets Audit**:
   - Verify zero secret exposure in VSIX, client logs, or webview bundle.
   - Webview CSP compliance (no inline scripts, strict nonce execution).
3. **Documentation & Release Artifacts**:
   - Write comprehensive user guide, release notes, and configuration documentation.

---

## 5. File Manifest & Key Responsibilities

| File Path | Responsibility |
| :--- | :--- |
| [`g:/My Drive/helios/BILLING_PLANS_AND_SUBSCRIPTION_MODEL.md`](file:///g:/My%20Drive/helios/BILLING_PLANS_AND_SUBSCRIPTION_MODEL.md) | Single-source-of-truth document for billing rates, credits, and gateway specs. |
| [`g:/My Drive/helios/skelion_agent/plan_config.py`](file:///g:/My%20Drive/helios/skelion_agent/plan_config.py) | Python definitions of plans, pricing, quotas, and model restrictions. |
| [`g:/My Drive/helios/skelion_agent/auth_routes.py`](file:///g:/My%20Drive/helios/skelion_agent/auth_routes.py) | GitHub OAuth verification, user creation, and JWT issuance. |
| [`g:/My Drive/helios/skelion_agent/billing_routes.py`](file:///g:/My%20Drive/helios/skelion_agent/billing_routes.py) | Razorpay checkout creation, HMAC webhook processing, and quota updates. |
| [`g:/My Drive/helios/skelion_agent/control_plane.py`](file:///g:/My%20Drive/helios/skelion_agent/control_plane.py) | Central FastAPI application hosting routers, middleware, and fail-open handlers. |
| `g:/My Drive/helios/skelion_vscode_extension/package.json` | Extension manifest, contribution points, commands, and packaging scripts. |
| `g:/My Drive/helios/skelion_vscode_extension/src/extension.ts` | Extension lifecycle, command registrations, and WebviewViewProvider setup. |
| `g:/My Drive/helios/skelion_vscode_extension/src/agent/AgentBridge.ts` | Local file reading, diff generation, and terminal command execution. |
| `g:/My Drive/helios/skelion_vscode_extension/src/views/panel.html` / webview | Multi-tab UI (Sign In, Chat, Billing, Incidents) styled with VS Code theme CSS. |

---

## 6. Definition of Done (DoD) Checklist

- [ ] **Packaging**: `npm run package` creates `skelion-vscode-0.1.0.vsix` cleanly without entrypoint errors.
- [ ] **Installation**: VSIX installs cleanly into VS Code via command line and GUI.
- [ ] **Authentication**: User signs in via GitHub; server creates profile with Pilot plan and 100 credits.
- [ ] **Chat & Tool Execution**: User prompts agent; streaming output renders; file edits display diff preview; terminal commands require explicit approval.
- [ ] **Billing Flow**: User triggers plan upgrade; Razorpay test order generates; webhook validates signature; plan updates to Pro in real-time.
- [ ] **Security**: Webview CSP enforced; secrets strictly located in environment variables; PII redacted from proxy logs.
- [ ] **Observability**: Prometheus metrics and edge incident summaries visible in telemetry.
