# VS Code Agent Extension — Master Build & Launch Plan

> **How to use this file:** Feed this entire file to your coding agent (Antigravity). Section 0 is the master prompt. Sections 1–16 are the specification. Section 17 is the phase-by-phase execution order with acceptance criteria. **Sections 21–26 (traceability, scale & reliability, agent-loop design, admin/notifications, Razorpay caveats, Definition of Done) are mandatory and override earlier sections where they conflict.** The agent must follow phases in order and not move on until a phase's acceptance criteria pass. Nothing in this file is "done" until the agent produces evidence for it (§26).

---

## 0. MASTER PROMPT (paste this first)

```
You are a senior full-stack engineer shipping a production VS Code extension.

GOAL
Turn my existing agent project into a commercial VS Code extension with:
1. A beautiful side-panel chat UI (quality bar: OpenAI Codex extension, GitHub Copilot Chat, Claude Code panel).
2. "Sign in with GitHub" as the first screen. First-time users get a new profile and the FREE plan automatically.
3. Chat with my agent (streaming, tool calls, file edits, terminal commands) with a model picker and visible usage limits.
4. A subscription management panel wired to my existing Razorpay billing. A paid plan is activated ONLY after my server verifies the payment (signature + webhook + amount + currency).
5. Production deployment of backend + publishing to VS Code Marketplace and Open VSX.

RULES
- FIRST inspect my existing repository. Reuse my existing agent, backend and Razorpay code. Do not rewrite what works. Summarize what exists and what is missing before writing code.
- Razorpay key_id / key_secret / webhook secret live ONLY in backend environment variables. Never in the extension bundle, webview, git, logs, or this prompt. Read them from process.env.
- Plan entitlements are enforced on the SERVER. The extension UI only displays state.
- Use TypeScript (strict) for extension + webview. Use the backend language already in my project; if none, use Node.js + Fastify + Postgres + Redis.
- Follow the phases in Section 17 in order. After each phase: run tests, show acceptance results, commit.
- Ask me only when blocked by a missing secret or an ambiguous product decision; otherwise pick the sensible default documented in this file and note it in DECISIONS.md.
- Keep a living file `PROGRESS.md` (done / in-progress / blocked) and `DECISIONS.md`.
- Build for real customers from day one: stateless services, queues for webhooks, atomic quota enforcement, provider failover, spend caps, kill switches, graceful shutdown (see §22). No in-memory state that breaks when a second server instance starts.
- Razorpay behavior must be verified against CURRENT official Razorpay docs and test mode before relying on anything in §8 or §25. If docs and this file disagree, the docs win; log it in DECISIONS.md.
- Do not claim anything is finished without evidence (test output, screenshots, load-test report). Finish by producing `FINAL_REPORT.md` and the evidence folder described in §26.

DELIVERABLES
Working extension (.vsix), deployed backend, CI/CD, docs, marketplace listing assets, launch checklist all green.
```

---

## 1. Product Overview

| Item | Decision |
|---|---|
| Surface | VS Code **side panel** (Activity Bar icon → Webview View). Also movable to the Secondary Side Bar (right side) by the user |
| Auth | GitHub (VS Code built-in auth provider → server verifies → server issues its own session) |
| Plans | Free (auto), Pro, Max/Team (names/prices editable in config) |
| Billing | Razorpay Subscriptions (recurring) + optional one-time top-ups/credits |
| Backend | Existing agent backend + new Auth, Entitlements, Billing, Usage modules |
| Distribution | VS Code Marketplace **and** Open VSX (needed for Antigravity, Cursor, VSCodium, Windsurf, etc.) |

### Core user journey
1. User installs extension → clicks icon in Activity Bar.
2. Sees **Sign in with GitHub** (logo, tagline, 3 value bullets, privacy link).
3. Clicks → GitHub consent in browser/VS Code dialog → back in editor.
4. Backend creates profile (if new) + assigns **Free plan** + returns session.
5. Chat screen opens with welcome state, suggested prompts, model picker, usage bar.
6. User chats; agent streams answers, proposes edits/commands, user approves.
7. Usage bar fills; at limit → friendly "Upgrade" card.
8. User opens **Subscription** tab → picks plan → browser opens hosted Razorpay checkout → pays.
9. Extension shows "Confirming payment…" → server verifies → plan flips live in the panel (no restart).
10. User can manage/cancel/see invoices from the same panel.

---

## 2. Architecture

```
┌────────────────────────── VS Code ──────────────────────────┐
│  Extension Host (Node, TypeScript)                          │
│   ├─ AuthService   (vscode.authentication + SecretStorage)  │
│   ├─ ApiClient     (fetch + auto-refresh + SSE streaming)   │
│   ├─ AgentBridge   (tool executor: read/edit files, terminal)│
│   ├─ SidebarProvider (WebviewViewProvider)                  │
│   └─ Commands / StatusBar / URI handler                     │
│        ▲  postMessage (typed protocol)  ▼                   │
│  Webview (React + Vite + Tailwind + codicons)               │
│   Screens: SignIn · Chat · History · Subscription · Settings│
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS (JWT access token)
┌──────────────────────────────▼──────────────────────────────┐
│ Backend API                                                 │
│  Auth · Users · Plans/Entitlements · Chat/Agent gateway     │
│  Usage metering · Billing (Razorpay) · Webhooks · Admin     │
│  Postgres · Redis (rate limit, sessions, pub/sub) · Queue   │
└──────────────────────────────┬──────────────────────────────┘
                               │
              Razorpay API + Webhooks · Model providers · GitHub API
```

### Key design decisions (with reasons)
- **Built-in GitHub auth provider** (`vscode.authentication.getSession('github', ...)`) instead of building raw OAuth: no client secret in the extension, users are often already signed in, fewer failure modes.
- **Server verifies the GitHub token** by calling `GET https://api.github.com/user` (+ `/user/emails` if email needed), then issues **its own short-lived JWT + rotating refresh token**. The GitHub token is never stored on the server unless you need repo access.
- **Payments happen in the external browser** on a hosted page (your website `/checkout`), not inside the webview. Razorpay Checkout needs popups/third-party scripts that clash with webview CSP; the browser is also more trusted by users and banks (3DS/UPI).
- **Webhook is the source of truth** for plan activation. The checkout redirect/handler is only a hint that triggers a fast re-check.
- **Server-side entitlements** so the plan cannot be spoofed by editing the extension.

---

## 3. Repository Layout (monorepo)

```
/apps
  /extension            # VS Code extension (TypeScript)
    src/extension.ts
    src/auth/AuthService.ts
    src/api/ApiClient.ts
    src/agent/AgentBridge.ts       # tool executors
    src/views/SidebarProvider.ts
    src/protocol.ts                # shared message types
    media/                         # icons, banner
    package.json                   # contributes, activationEvents
  /webview              # React UI (Vite)
    src/app/ screens/ components/ state/ styles/
  /server               # backend (or link to existing)
  /web                  # website: landing, /checkout, /billing, /privacy, /terms, /refund
/packages
  /shared               # zod schemas + TS types shared by extension/webview/server
  /ui-tokens
/.github/workflows      # ci.yml, release.yml
PROGRESS.md  DECISIONS.md
```

---

## 4. Authentication & Registration (GitHub)

### 4.1 Extension side
```ts
const session = await vscode.authentication.getSession(
  'github', ['read:user', 'user:email'], { createIfNone: true });
// POST /v1/auth/github { githubAccessToken: session.accessToken, deviceId, extVersion, vscodeVersion }
// -> { accessToken(15m), refreshToken, user, plan, isNewUser }
await context.secrets.store('auth.refresh', refreshToken);
```
- Store tokens **only** in `context.secrets` (SecretStorage). Never `globalState` or settings.
- Keep access token in memory; refresh on 401 once, then force re-login.
- Listen to `vscode.authentication.onDidChangeSessions` → if GitHub session removed, sign out locally.
- Commands: `agent.signIn`, `agent.signOut`, `agent.switchAccount`.
- Add `vscode://<publisher>.<ext>/auth` URI handler as a fallback (for forks lacking the GitHub provider): open `https://yourdomain/auth/github/start?state=...&redirect=vscode://...` → web OAuth → redirect back with a one-time code → exchange for session. Use `state` + PKCE-style one-time code exchange.

### 4.2 Server side `POST /v1/auth/github`
1. Validate body (zod). Rate-limit by IP + device.
2. Call GitHub `/user` with the token; reject if non-200. Confirm token is for a real user (and optionally check `X-OAuth-Scopes`).
3. Upsert user by `github_id` (immutable), update login/avatar/email.
4. **If new:** create `users` row, create `subscriptions` row on `free` plan, create `usage_period`, emit `user.created` (welcome analytics/email).
5. Create `sessions` row (device, refresh token **hash**), return JWT (15 min, `sub`, `plan`, `sid`) + refresh token (30 days, rotating, reuse detection → revoke family).
6. Endpoints: `POST /v1/auth/refresh`, `POST /v1/auth/logout`, `GET /v1/me`, `DELETE /v1/me` (account deletion/export).

### 4.3 Edge cases to handle
GitHub user with private/no email · user revokes GitHub access · multiple devices · offline start (show cached profile, disable chat) · clock skew · banned/suspended user (`403 account_suspended` UI state) · fork IDE without GitHub provider (URI fallback).

---

## 5. Database Schema (Postgres)

```sql
users(id uuid pk, github_id bigint unique, login text, name text, email text,
      avatar_url text, razorpay_customer_id text, status text default 'active',
      created_at, last_seen_at)

plans(id text pk,                -- 'free','pro','max'
      name, price_inr int, price_usd int, billing_period text,  -- monthly/yearly
      razorpay_plan_id_inr text, razorpay_plan_id_usd text,
      limits jsonb,              -- see §7
      models jsonb,              -- allowed model ids
      active bool)

subscriptions(id uuid pk, user_id fk, plan_id fk,
      status text,               -- free|created|authenticated|active|pending|halted|paused|cancelled|completed|expired
      razorpay_subscription_id text unique,
      current_period_start, current_period_end,
      cancel_at_period_end bool, pending_plan_id text,
      created_at, updated_at)

payments(id uuid pk, user_id fk, subscription_id fk,
      razorpay_payment_id text unique, razorpay_order_id text, razorpay_invoice_id text,
      amount int, currency text, status text, method text,
      captured_at, raw jsonb)

webhook_events(id text pk,       -- X-Razorpay-Event-Id (idempotency)
      type text, payload jsonb, processed_at, error text)

usage_periods(id, user_id fk, period_start, period_end,
      requests_used int, tokens_in bigint, tokens_out bigint, premium_requests_used int)

usage_events(id, user_id, ts, model, tokens_in, tokens_out, cost_usd, request_id)

conversations(id, user_id, title, model, created_at, updated_at)
messages(id, conversation_id, role, content jsonb, tool_calls jsonb, ts)

sessions(id, user_id, refresh_hash, device_id, ua, created_at, last_used_at, revoked_at)
audit_log(id, user_id, action, meta jsonb, ts)
```
Indexes: `subscriptions(user_id)`, `payments(razorpay_payment_id)`, `usage_periods(user_id, period_start)`, `messages(conversation_id, ts)`.

---

## 6. Plans & Pricing (editable config — defaults)

| | Free | Pro | Max |
|---|---|---|---|
| Price | ₹0 | ₹X / mo | ₹Y / mo |
| Requests | 30 / day | 1,000 / mo | 5,000 / mo |
| Models | 1–2 base | all standard | all + premium |
| Context | 32k | 128k | 200k+ |
| Agent actions (edit/terminal) | limited | yes | yes |
| History | 7 days | 90 days | unlimited |
| Priority queue | – | – | ✔ |

Put prices in the `plans` table/config, never hard-coded in UI. USD prices only if international payments are enabled on your Razorpay account. **Verify whether recurring subscriptions in USD / international cards are supported for your account (see §25); if not, launch INR-only recurring and offer international users one-time prepaid passes instead.**

---

## 7. Entitlements & Usage Metering

`plans.limits` example:
```json
{ "requests_per_day": 30, "requests_per_month": null, "premium_requests_per_month": 0,
  "max_context_tokens": 32000, "max_output_tokens": 4096,
  "concurrent_requests": 1, "agent_tools": ["read_file","search"], "history_days": 7 }
```
**Enforcement on every chat request (server):**
1. Auth → load subscription (cache in Redis, invalidate on webhook).
2. Check model allowed for plan.
3. Check quota (atomic Redis counters + DB reconciliation). If exceeded → `429 { code:"quota_exceeded", resetAt, upgradeUrl }`.
4. Stream response; on finish write `usage_events` and increment counters (include tokens actually used).
5. Rate limit per user (burst) + global circuit breaker.

`GET /v1/me/usage` → `{ plan, periods:{day:{used,limit,resetAt}, month:{...}}, premium:{...} }` for the usage bar.

---

## 8. Razorpay Billing — Implementation

> **Security:** Razorpay `key_id` is public-ish, `key_secret` and webhook secret are **server-only**. If any secret was pasted into chats/prompts/repos, **rotate it in the Razorpay dashboard** before launch.

### 8.1 Setup (one-time)
- Create Razorpay **Plans** (one per paid tier × period × currency) via API/dashboard; store IDs in `plans`.
- Configure webhook URL `https://api.yourdomain.com/v1/webhooks/razorpay` with a strong secret and these events:
  `subscription.authenticated, subscription.activated, subscription.charged, subscription.pending, subscription.halted, subscription.paused, subscription.resumed, subscription.cancelled, subscription.completed, payment.captured, payment.failed, refund.processed, invoice.paid`.
- Complete KYC/activation; enable international cards/UPI Autopay as needed.

### 8.2 Upgrade flow
```
Extension (Subscription tab) ──click "Upgrade to Pro"──►
POST /v1/billing/checkout { planId, period }   (JWT)
  server: ensure razorpay customer, create Razorpay subscription
          (plan_id, total_count, customer_notify, notes:{user_id, plan_id})
  returns { checkoutUrl: https://yourdomain/checkout?token=<signed one-time token> }
Extension: vscode.env.openExternal(checkoutUrl); UI → "Waiting for payment…" (poll/SSE)
Web /checkout: validates token → loads Razorpay Checkout.js with subscription_id → user pays
```
- Checkout token is single-use, expires in ~15 min, bound to user + plan.
- Show clear price, GST/tax lines, auto-renew notice, link to refund policy **before** payment.

### 8.3 Payment verification (the "credit check")
Three layers — all must be consistent before activating:

1. **Checkout handler signature** (fast hint): on success Razorpay returns `razorpay_payment_id`, `razorpay_subscription_id`, `razorpay_signature`. Server verifies  
   `HMAC_SHA256(razorpay_payment_id + "|" + subscription_id, key_secret) == razorpay_signature`.  
   Then **fetch the payment from Razorpay API** and confirm `status == "captured"`, `amount == plan.price`, `currency == plan.currency`, and subscription's `notes.user_id == current user`.
2. **Webhook (source of truth):** verify `X-Razorpay-Signature` = `HMAC_SHA256(raw_body, webhook_secret)` using the **raw request body** (do not parse first). Dedupe by `X-Razorpay-Event-Id` in `webhook_events`. Process inside a DB transaction. Return 200 quickly; do heavy work in a queue.
3. **Reconciliation job** (every 15 min): for subscriptions in `created/authenticated/pending`, call Razorpay API and fix drift; also daily check of `active` subscriptions vs Razorpay.

### 8.4 Event → state mapping
| Event | Action |
|---|---|
| `subscription.authenticated` | status=authenticated (no access yet unless charge captured) |
| `subscription.activated` / `subscription.charged` + `payment.captured` | verify amount → status=active, set `plan_id`, period start/end, store payment, invalidate cache, push realtime event to extension |
| `payment.failed` | store failure, notify user in panel, keep current plan |
| `subscription.pending` | grace banner "Payment retrying" (keep access for grace window, e.g., 3 days) |
| `subscription.halted` | downgrade to Free after grace, banner "Payment failed — update method" |
| `subscription.cancelled` | if `cancel_at_period_end` keep access to period end, then Free |
| `subscription.completed` | to Free |
| `refund.processed` | record refund; downgrade if full refund within policy |

### 8.5 Management features
- **Cancel:** `POST /v1/billing/cancel` → Razorpay cancel (at cycle end) → set `cancel_at_period_end`.
- **Upgrade/downgrade:** use subscription update (immediate vs next cycle; document proration behavior in `DECISIONS.md`).
- **Payment method update:** hosted page link.
- **Invoices/receipts:** `GET /v1/billing/invoices` (from your `payments` + Razorpay invoice URLs).
- **Coupons/trials (optional):** Razorpay offers / trial via `start_at`.
- **Idempotency:** every mutating billing endpoint accepts `Idempotency-Key`.
- **Taxes:** GST invoicing as required for India; store GSTIN optionally.

### 8.6 "Paid → live in panel" realtime
Server pushes `subscription.updated` via **SSE** (`GET /v1/me/events`) or fallback polling `GET /v1/me` every 3s (max 3 min) after checkout opens. Extension shows: *Waiting for payment → Confirming → ✅ Pro activated* with confetti-free subtle animation, and refreshes model list + limits instantly.

---

## 9. Extension Implementation Details

### 9.1 `package.json` essentials
```jsonc
{
  "name": "your-agent", "displayName": "Your Agent", "publisher": "<publisher>",
  "engines": { "vscode": "^1.90.0" },
  "categories": ["AI", "Chat", "Programming Languages"],
  "activationEvents": ["onStartupFinished", "onUri"],
  "main": "./dist/extension.js",
  "icon": "media/icon.png",
  "galleryBanner": { "color": "#0B0B0F", "theme": "dark" },
  "contributes": {
    "viewsContainers": { "activitybar": [{ "id": "agent", "title": "Your Agent", "icon": "media/activity.svg" }] },
    "views": { "agent": [{ "type": "webview", "id": "agent.sidebar", "name": "Chat" }] },
    "commands": [
      {"command":"agent.newChat","title":"Your Agent: New Chat","icon":"$(add)"},
      {"command":"agent.signIn","title":"Your Agent: Sign In"},
      {"command":"agent.signOut","title":"Your Agent: Sign Out"},
      {"command":"agent.manageSubscription","title":"Your Agent: Manage Subscription"},
      {"command":"agent.addSelectionToChat","title":"Your Agent: Add Selection to Chat"},
      {"command":"agent.explainSelection","title":"Your Agent: Explain This"}
    ],
    "menus": { "view/title": [{ "command":"agent.newChat","when":"view == agent.sidebar","group":"navigation" }],
               "editor/context": [{ "command":"agent.addSelectionToChat","when":"editorHasSelection" }] },
    "keybindings": [{ "command":"agent.focus","key":"ctrl+shift+a","mac":"cmd+shift+a" }],
    "configuration": { "title":"Your Agent", "properties": {
        "agent.apiBaseUrl": {"type":"string","default":"https://api.yourdomain.com","scope":"machine"},
        "agent.autoApprove": {"type":"string","enum":["never","reads","edits"],"default":"never"},
        "agent.telemetry": {"type":"boolean","default":true} } }
  },
  "capabilities": { "untrustedWorkspaces": { "supported": "limited" } }
}
```
(Do not expose `apiBaseUrl` as user-editable in production if you don't want it; keep it for dev builds only.)

### 9.2 Webview ↔ Extension typed protocol (`packages/shared`)
Messages (zod-validated both directions):
`ready · signIn · signOut · sendMessage{text,model,context[]} · stop · newChat · loadHistory · selectConversation · setModel · approveAction{id,decision} · openCheckout{planId,period} · cancelSubscription · refreshMe · openExternal{url} · attachFile · attachSelection`
Extension → webview: `authState · me · usage · models · streamDelta · toolCallProposed · toolCallResult · error · subscriptionUpdated · conversationList`.

### 9.3 Webview security
- `localResourceRoots` limited to `dist/webview`; strict **CSP with nonce**: `default-src 'none'; style-src ${cspSource} 'nonce-…'; script-src 'nonce-…'; img-src ${cspSource} https: data:; font-src ${cspSource};`
- Never `innerHTML` model output; render markdown with a sanitizing renderer (react-markdown + rehype-sanitize), syntax highlight with Shiki/highlight.js.
- `retainContextWhenHidden` off; persist UI state with `vscode.getState()` / `setState()`.
- Network calls go through the **extension host**, not the webview (keeps tokens out of the DOM).

### 9.4 Agent tool execution (AgentBridge)
Tools exposed to the agent (server sends tool call → extension executes locally → returns result):
- `read_file`, `list_dir`, `search_text` (use `vscode.workspace.fs`, `findFiles`, ripgrep)
- `edit_file` / `create_file` using `WorkspaceEdit` + **diff preview** (`vscode.diff`) with Accept/Reject
- `run_command` via integrated terminal (`window.createTerminal` + shell integration API when available) with **explicit approval**, timeout, output cap
- `get_diagnostics` (`languages.getDiagnostics`), `get_open_editors`, `get_selection`
Safety: path allow-list inside workspace, block `.env`/secrets patterns by default, command deny-list (`rm -rf /`, `curl | sh`…), approval modes (Ask / Auto-reads / Auto-edits), per-session checkpoint so user can **Undo all changes**, respect Workspace Trust.

### 9.5 Status bar & commands
Status bar item: `$(sparkle) Pro · 412/1000` (click → Subscription tab); turns warning color at 90%.

### 9.6 Telemetry & privacy
Respect `vscode.env.isTelemetryEnabled` and `agent.telemetry`. No code content in telemetry. Provide clear privacy policy of what code is sent to the server and retained.

---

## 10. UI / UX & Graphics Specification

### 10.1 Design principles
Native-feeling (inherit VS Code theme via `--vscode-*` CSS variables), fast, calm, keyboard-first, works in narrow widths (≥ 280px) and in light/dark/high-contrast themes.

**Do not use** the deprecated `@vscode/webview-ui-toolkit`. Build small components with Tailwind/Radix primitives styled by VS Code variables. Icons: **@vscode/codicons** + a few custom SVGs.

### 10.2 Design tokens
```css
:root{
  --radius: 10px; --radius-sm: 6px;
  --accent: var(--vscode-button-background);       /* adopt theme accent */
  --brand: #7C5CFF;                                /* your brand accent (gradients, badges) */
  --surface-1: var(--vscode-sideBar-background);
  --surface-2: var(--vscode-editorWidget-background);
  --border: var(--vscode-widget-border, var(--vscode-panel-border));
  --text: var(--vscode-foreground); --muted: var(--vscode-descriptionForeground);
  --font: var(--vscode-font-family); --mono: var(--vscode-editor-font-family);
}
```
Spacing scale 4/8/12/16/24. Type: 13px base, 12px meta, 11px caption. Motion: 120–180ms ease-out; respect `prefers-reduced-motion`.

### 10.3 Screens
1. **Sign-in:** brand mark, one-line promise, big **Continue with GitHub** button (GitHub mark), small "By continuing you agree to Terms & Privacy", expandable "What data do you collect?".
2. **First-run onboarding (once):** 3 quick cards (Ask · Edit · Run), pick approval mode, done. Skippable.
3. **Chat (main):**
   - **Header:** avatar menu (profile, plan badge, sign out), New chat (+), History (clock), overflow (…).
   - **Message list:** user bubble (subtle), assistant message (no bubble, full width), markdown, code blocks with *Copy / Insert at cursor / Apply to file*, collapsible **tool-call cards** (icon, title, status spinner/✔/✖, expandable output), **diff cards** with Accept/Reject, thinking/“Working…” shimmer, error banners with Retry.
   - **Composer:** auto-grow textarea, `@` file/symbol mentions, `/` slash commands (`/fix /explain /test /docs /clear`), attach current file/selection chips, **model picker dropdown**, mode toggle (Ask / Agent), Send ↔ Stop button, `Enter` send / `Shift+Enter` newline.
   - **Footer meter:** thin usage bar + `412 / 1000 requests · resets in 6d`; click → Subscription.
   - **Empty state:** greeting with GitHub name, 4 suggested prompts.
4. **Model picker:** grouped list (Fast / Balanced / Powerful), each with small description + cost badge (e.g., "1×", "3×"); locked models show 🔒 + "Pro" chip → opens upgrade sheet.
5. **Limit reached:** inline card in chat — “You’ve used today’s free requests. Resets at 12:00 AM. **Upgrade to Pro** · Remind me later”. Composer disabled with explanation, not an error.
6. **History:** searchable list grouped by Today/Yesterday/Earlier, rename, delete, export markdown.
7. **Subscription panel (tab or full-height sheet):**
   - Current plan card (name, status badge Active/Past due/Cancelling, renews on DATE, price).
   - Usage rings/bars (day, month, premium).
   - **Plan comparison cards** (Free / Pro / Max) with feature checklist, monthly/yearly toggle (+ “save X%”), CTA buttons: *Current plan / Upgrade / Downgrade*.
   - Actions: Manage payment method · View invoices · Cancel subscription (with confirm + “access until DATE”).
   - Payment status states: *Waiting for payment…*, *Confirming with bank…*, *✅ Activated*, *Payment failed — retry*.
8. **Settings:** approval mode, default model, telemetry toggle, keyboard shortcuts link, sign out, delete account/export data.
9. **System states:** offline, server down, session expired (silent refresh → else re-login card), update available, workspace-untrusted notice.

### 10.4 Graphics & assets checklist
| Asset | Spec |
|---|---|
| Marketplace icon | `icon.png` 128×128 (ideally 256×256 source), PNG, no transparency issues on dark/light |
| Activity bar icon | monochrome **SVG**, 24×24 viewBox, uses `currentColor` |
| Gallery banner | `galleryBanner.color` + theme (dark) |
| Screenshots | 5–7 PNG @ 1600×1000: sign-in, chat+diff, model picker, usage meter, subscription, light theme |
| Demo GIF/MP4 | 15–25s: sign in → ask → approve diff → upgrade |
| Logo variants | SVG light/dark, favicon, OG image 1200×630 for website |
| Empty-state illustrations | minimal SVG, theme-aware |
| README hero | banner + feature grid + GIF |
Brand: define 1 accent + 1 neutral gradient; keep UI mostly native colors.

### 10.5 Accessibility
Full keyboard navigation, focus rings (`--vscode-focusBorder`), ARIA roles (`log` for message list, `status` for streaming), contrast AA in all themes, screen-reader labels on icon buttons, no color-only status.

---

## 11. Backend API Contract (summary)

```
POST /v1/auth/github          POST /v1/auth/refresh       POST /v1/auth/logout
GET  /v1/me                   DELETE /v1/me               GET /v1/me/usage
GET  /v1/me/events (SSE)      GET /v1/models              GET /v1/plans
POST /v1/chat (SSE stream)    POST /v1/chat/tool-result   POST /v1/chat/stop
GET  /v1/conversations        GET/DELETE /v1/conversations/:id
POST /v1/billing/checkout     POST /v1/billing/cancel     POST /v1/billing/change-plan
GET  /v1/billing/subscription GET  /v1/billing/invoices
POST /v1/webhooks/razorpay    GET  /healthz  /readyz
```
Standard error shape: `{ error:{ code, message, details?, requestId } }` with codes `unauthorized, forbidden, quota_exceeded, model_not_allowed, payment_required, rate_limited, validation_error, server_error`.
Stream format: SSE events `delta`, `tool_call`, `usage`, `done`, `error`. Support cancel via aborted connection + `/stop`.
Version API (`/v1`), send `X-Ext-Version`; server can return `426` with min-version message to force update.

---

## 12. Security Checklist

- [ ] Secrets only in env/secret manager; `.env` git-ignored; rotate any key that was ever shared in plain text
- [ ] Webhook signature verified on raw body; replay/idempotency protected
- [ ] JWT short-lived; refresh tokens hashed, rotating, reuse-detected
- [ ] Per-user + per-IP rate limits; request size limits; input validation (zod)
- [ ] CORS locked down; HTTPS/HSTS only; secure headers (helmet)
- [ ] Webview CSP nonce; sanitized markdown; no remote scripts
- [ ] Tool execution sandboxed to workspace; approval gates; secret-file blocklist
- [ ] SQL injection safe (parametrized/ORM); least-privilege DB user
- [ ] Audit log for auth/billing events; PII minimal; backups + restore tested
- [ ] Dependency scanning (Dependabot/`npm audit`), lockfiles, signed releases
- [ ] Abuse controls: free-tier farming (device/GitHub account age checks), prompt abuse, concurrent request caps

## 13. Legal & Compliance (needed for Razorpay + Marketplace)
Privacy Policy (what code/data is sent, retention, subprocessors) · Terms of Service · **Refund & Cancellation Policy** · Contact/support page · Pricing page with taxes · India DPDP / GDPR basics (delete + export account) · Open-source licenses attribution (`THIRD_PARTY_NOTICES`) · Marketplace publisher verification.

## 14. Observability
Sentry (extension + server) · structured JSON logs w/ requestId · metrics (latency, tokens, quota hits, webhook lag, payment success rate) · alerts (webhook failures, 5xx spike, queue backlog, reconciliation drift) · status page · product analytics (sign-in funnel, free→paid conversion, activation, retention) with no code contents.

## 15. Testing Plan
- **Unit:** entitlement checks, quota math, signature verification, event→state mapper.
- **Integration:** auth flow with mocked GitHub; Razorpay **test mode** end-to-end (test cards/UPI), webhook replay, duplicate events, out-of-order events, amount mismatch → rejected.
- **Extension:** `@vscode/test-electron` (activation, commands, auth state, webview messaging).
- **UI:** Storybook/Vitest for components; Playwright for the web checkout page.
- **Load:** streaming chat with k6 (concurrency caps, quota under race).
- **Manual matrix:** Windows/macOS/Linux · VS Code stable/insiders · Antigravity/Cursor/VSCodium · light/dark/HC themes · narrow panel · offline · remote (SSH/WSL/Dev Containers) · Workspace Trust restricted.
- **Payment scenarios:** success, failure, user closes tab, pending UPI, retry, cancel, downgrade, refund, webhook delayed 5 min.

## 16. Deployment

### Backend
- Containerize (Dockerfile), run on Fly.io / Railway / Render / AWS (ECS/App Runner) / your VPS behind Cloudflare.
- Managed Postgres (daily backups, PITR) + managed Redis; migrations via Prisma/Drizzle/Alembic in CI; zero-downtime deploys (health checks).
- Environments: `dev` (Razorpay test keys) → `staging` (test keys) → `prod` (live keys). Separate DBs and secrets.
- Env vars: `DATABASE_URL, REDIS_URL, JWT_SECRET, REFRESH_SECRET, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET, GITHUB_API_BASE, MODEL_PROVIDER_KEYS…, SENTRY_DSN, PUBLIC_WEB_URL, MIN_EXT_VERSION`.

### Website (`/web`)
Landing (hero, features, pricing, FAQ), `/checkout`, `/billing` (also usable outside VS Code), legal pages, docs. Deploy on Vercel/Cloudflare Pages.

### Extension release
```
pnpm build → vsce package → test .vsix locally (Install from VSIX)
vsce publish  (Marketplace; needs publisher + Azure DevOps PAT with Marketplace Manage scope)
ovsx publish  (Open VSX; needs namespace + token)  ← required for Antigravity/Cursor/VSCodium users
```
- Create **publisher** at marketplace.visualstudio.com/manage; verify domain for the verified badge.
- Use **pre-release channel** first (`vsce publish --pre-release`) → beta users → stable.
- GitHub Actions `release.yml`: on tag `vX.Y.Z` → test → package → publish both registries → attach `.vsix` to GitHub Release → changelog.
- Keep `CHANGELOG.md`, semantic versioning, `.vscodeignore` to keep VSIX small (bundle with esbuild; < ~5 MB).
- Marketplace README: hero, feature list, GIF, pricing note, privacy summary, support link.

---

## 17. EXECUTION PHASES (agent must follow in order)

### Phase 0 — Audit & Setup (0.5 day)
- Inspect existing repo: agent core, API, Razorpay module, DB. Write `AUDIT.md` (what exists / gaps / reuse plan).
- Create monorepo structure, lint/format/tsc strict, CI skeleton.
- **Accept:** `AUDIT.md` committed; `pnpm build` and CI green.

### Phase 1 — Backend foundation (1–2 days)
- DB migrations (§5), seed `plans`, config loader, error format, request logging, health endpoints.
- Auth endpoints (`/auth/github`, refresh, logout, `/me`) incl. new-user creation + **Free plan auto-assign**.
- **Accept:** integration tests: new user → Free sub created; second login → no duplicate; refresh rotation + reuse detection works.

### Phase 2 — Entitlements, usage & chat gateway (1–2 days)
- Quota/rate limiting, `/models`, `/me/usage`, `/chat` SSE with tool-call round trips, usage events.
- **Accept:** Free user blocked from Pro model (403 `model_not_allowed`); quota exceeded returns 429 with resetAt; concurrent race test passes.

### Phase 3 — Billing (2 days)
- Razorpay plan sync, `/billing/checkout`, hosted `/checkout` page, signature verification, webhook handler (§8.4), idempotency, reconciliation job, cancel/change-plan, invoices, SSE `subscription.updated`.
- **Accept (test mode):** pay → webhook → plan active; wrong amount/currency → rejected; duplicate webhook → no double-apply; failed payment → banner state; cancel → access until period end; reconciliation fixes a dropped webhook.

### Phase 4 — Extension shell & auth (1 day)
- Activity bar view, `SidebarProvider`, SecretStorage, `AuthService`, `ApiClient` (refresh, SSE), typed protocol, status bar, commands, URI-handler fallback.
- **Accept:** sign-in from clean install creates profile; restart keeps session; sign-out wipes secrets; works in at least VS Code + one fork.

### Phase 5 — Webview UI (3–4 days)
- Design system + all screens in §10.3 (sign-in, onboarding, chat, model picker, limit card, history, subscription, settings, system states).
- Streaming markdown, code blocks with actions, tool-call & diff cards, composer with mentions/slash commands, usage footer.
- **Accept:** screenshots in light/dark/HC at 280px and 600px widths; keyboard-only walkthrough passes; Lighthouse-style a11y checks pass.

### Phase 6 — Agent tools & safety (2 days)
- AgentBridge tools (§9.4), approval modes, diff preview, command approval, checkpoints/undo, workspace-trust handling, secret blocklist.
- **Accept:** agent can read, edit (with diff accept/reject) and run a command with approval; undo restores files; blocked paths/commands refused.

### Phase 7 — Subscription panel integration (1 day)
- Wire plan cards → `/billing/checkout` → `openExternal` → waiting/confirming/activated states; cancel; invoices; live refresh of limits & model list.
- **Accept:** full upgrade in Razorpay test mode flips the panel to Pro **without restart** within seconds of webhook.

### Phase 8 — Hardening, legal, observability (1–2 days)
- Security checklist (§12), Sentry, metrics, alerts, legal pages (§13), account delete/export, abuse controls.
- Scale & reliability work from §22: worker/queue split, Redis-backed quota + run state, PgBouncer, partitioning, provider failover, spend caps, kill switches, graceful shutdown, autoscaling config, runbooks.
- Admin console + transactional emails (§24).
- Load and chaos tests (§22.10) with saved reports.
- **Accept:** all §12 boxes ticked; §22.10 pass criteria met; alert test fires; kill switches tested in staging.

### Phase 9 — Packaging, beta & launch (1–2 days)
- Assets (§10.4), README, CHANGELOG, `.vsix`, pre-release to Marketplace + Open VSX, closed beta (10–20 users), fix top issues, switch Razorpay to **live keys** on prod, make one real small payment + refund to verify, then stable release.
- **Accept:** launch checklist (§18) 100% done AND Definition of Done (§26) fully evidenced in `FINAL_REPORT.md`.

**Total realistic timeline:** ~2–3 weeks for a solid v1 with one engineer + agent.

---

## 18. Launch Checklist

- [ ] Razorpay live mode activated, live webhook configured, live keys in prod secrets, test keys removed from prod
- [ ] One real ₹ payment + refund end-to-end verified
- [ ] Webhook retries & reconciliation verified in prod
- [ ] Free-tier defaults confirmed; plan prices/limits final
- [ ] Privacy, Terms, Refund pages live and linked in extension + Marketplace
- [ ] Publisher verified; Marketplace + Open VSX listings published (pre-release → stable)
- [ ] Sentry/alerts/status page live; on-call contact set
- [ ] Support email + docs + FAQ; in-extension "Report issue" link
- [ ] Backups + restore drill done
- [ ] Rollback plan: ability to disable paid upgrades with a feature flag, force-update via `MIN_EXT_VERSION`
- [ ] Launch assets ready: demo video, GIF, screenshots, Product Hunt/X/Reddit/HN posts

## 19. Post-launch Roadmap (v1.1+)
Team plans & seats · usage-based top-ups/credits · annual plans & coupons · inline completions · MCP/tool marketplace · project memory/rules files · web dashboard · referral program · enterprise SSO.

---

## 20. Open Decisions (agent: pick defaults, log in DECISIONS.md)

1. Final plan names, prices (INR/USD), and limits — default to §6.
2. Immediate vs end-of-cycle upgrade proration — default: upgrades immediate, downgrades next cycle.
3. Grace period for failed renewals — default: 3 days.
4. Free-tier abuse policy (min GitHub account age, device limit) — default: 1 free account per GitHub ID, 3 devices.
5. Whether to require GitHub email — default: optional.
6. Product/extension name and publisher ID (permanent once published!).

---

## 21. Requirements Traceability Matrix (every original requirement → where it is built → how it is proven)

| # | Original requirement | Built in | Proof (must pass) |
|---|---|---|---|
| R1 | Proper VS Code extension, launched publicly | §3, §9, §16 | `.vsix` installs on fresh machine; listed on Marketplace + Open VSX |
| R2 | Side-panel UI like Codex / Copilot | §9.1, §10 | Screenshots at 280px/600px in light/dark/HC; keyboard walkthrough |
| R3 | User sees **Sign in with GitHub first** | §4, §10.3(1) | Clean install → first thing shown is sign-in; chat inaccessible until signed in |
| R4 | New user → **new profile created** | §4.2 step 3–4, §5 | Integration test: first login creates `users` row; second login creates none |
| R5 | New user → **free tier subscription** | §4.2, §5, §6 | Test: new user has `subscriptions.plan_id='free'` and `/me` returns Free limits |
| R6 | Chat section talking to **my agent** and performing operations | §9.4, §11, §23 | E2E: prompt → streamed answer → file edit with diff accept → command with approval |
| R7 | Change model in chat | §10.3(4), §7 | Model picker lists plan-allowed models; locked ones open upgrade; server rejects disallowed model |
| R8 | See limits / usage | §7, §10.3(3) footer, §9.5 status bar | Usage bar matches `/me/usage`; updates after each message |
| R9 | Subscription management panel connected to billing | §8, §10.3(7) | Upgrade, cancel, invoices, status states all work in Razorpay test mode |
| R10 | Payment → server confirms amount credited → allow that plan | §8.3, §8.4, §8.6 | Test: wrong amount/currency rejected; duplicate webhook harmless; plan flips live without restart |
| R11 | Razorpay already wired; keys/billing info already provided | §0 rules, §8, §12, §25 | Existing Razorpay module reused (AUDIT.md); no secret in repo (gitleaks clean) |
| R12 | Monitor everything with my other features | §14, §24 | Dashboards + alerts live; admin console shows users, usage, webhooks |
| R13 | User-friendly | §10, §10.5, onboarding, empty/limit/error states | Usability pass with 5 beta users; no dead ends in any error state |
| R14 | Graphics and design details | §10.2–§10.4 | All assets in §10.4 delivered in `/apps/extension/media` and `/marketing` |
| R15 | Ready to scale for real customers | §22 | Load + chaos reports meet §22.10 criteria |
| R16 | Full plan in a file for my agent | this file | Agent produces `FINAL_REPORT.md` mapping each row to evidence |

---

## 22. Production Scale & Reliability (mandatory)

### 22.1 Design targets (adjust to your real goals; architecture must grow ~10× by adding instances, not rewriting)
| Metric | Initial target |
|---|---|
| Registered users | 10k (design headroom to 100k) |
| Daily active users | 2k |
| Concurrent streaming chats | 500 |
| Non-chat API p95 latency | < 300 ms |
| Chat time-to-first-token (excluding model provider time) | < 500 ms overhead |
| Availability | 99.9% monthly |
| Webhook → plan active (p95) | < 5 s |
| RPO / RTO | ≤ 5 min / ≤ 1 h |

### 22.2 Stateless compute and streaming
- Separate processes: `api` (HTTP/SSE), `worker` (queues, webhooks, emails, reconciliation), `scheduler` (cron). All horizontally scalable; **no in-memory session, quota, or run state**.
- SSE: heartbeat every 15–20 s; load-balancer/proxy idle timeout must exceed the longest stream; disable proxy buffering; set per-stream max duration.
- Graceful shutdown on SIGTERM: stop accepting new streams, finish or checkpoint in-flight ones (grace window e.g. 60 s), then exit. Deploys must not cut users off mid-answer.
- Autoscale on CPU + open connections + queue depth. Minimum 2 instances across 2 availability zones in prod.

### 22.3 Database
- Connection pooling (PgBouncer or provider pooler); statement and idle-in-transaction timeouts.
- **Partition `usage_events` and `messages` by month**; retention jobs per plan (`history_days`); archive/delete old partitions.
- Read replica for admin analytics and heavy reports; never run analytics on the primary.
- Lock subscription rows (`SELECT … FOR UPDATE`) when applying billing events so concurrent webhooks and checkout returns cannot corrupt state.
- Migrations follow expand → migrate → contract; every migration backward compatible with the previous app version.

### 22.4 Queues and exactly-once-effect processing
- Webhook handler does only: verify signature on raw body → insert into `webhook_events` (unique on event id) → enqueue → return 200 fast. Workers process with retries, exponential backoff + jitter, and a dead-letter queue with alerting.
- **Outbox pattern** for side effects (realtime `subscription.updated` push, emails, analytics) so a crash between DB commit and notify loses nothing.
- Every handler idempotent; replaying any event any number of times yields the same final state.
- Queue tech: use what your stack already has (BullMQ/Redis, SQS, RabbitMQ, or Postgres-based queue); document in DECISIONS.md.

### 22.5 Quota & rate limiting at scale
- Use Redis atomic operations (Lua script or `INCRBY` with TTL) for per-user day/month counters; reconcile with `usage_events` nightly.
- **Reserve-then-settle:** reserve an estimated token/request budget before calling the model; settle to actual usage after. Prevents N parallel requests overshooting the limit.
- Redis outage policy (decide and document): free users fail-closed (temporary "try again" message); paid users fail-open with a conservative local cap and an alert.
- Layered limits: per-IP (pre-auth), per-user burst, per-plan concurrency (`concurrent_requests`), global circuit breaker.

### 22.6 Model-provider resilience and cost control
- Provider abstraction layer; per-provider timeouts, retries with jitter, circuit breakers, health checks.
- Fallback model/provider when primary is degraded (clearly tell the user when a fallback was used if quality differs).
- Handle provider 429s with queueing/backoff, not user-visible failures where possible.
- Hard caps: max input/output tokens per request, max agent steps per run, max tool-output size.
- **Spend guardrails:** per-user daily cost cap, per-plan cost cap, global daily budget with alert at 80% and automatic degrade-to-cheaper-model at 100%.
- Maintain a unit-economics sheet: cost per request per model vs plan price; alert on users/plans with negative margin.

### 22.7 Extension-side resilience
- API client: retry with backoff on network errors, single-flight token refresh, offline detection with clear UI.
- Chat stream: reconnect using last event id where the server supports it; otherwise show "Connection lost — Retry" without duplicating messages.
- Webview performance: virtualized message list, batch streaming deltas (~30–60 ms), lazy-load history, cap rendered output size, avoid re-rendering markdown on every token for finished messages.
- Survive extension-host restarts and window reloads (state in `vscode.getState` + server conversation).
- **Version compatibility:** server supports the current and previous two extension versions; `MIN_EXT_VERSION` forces update with a friendly message; additive-only API changes within `/v1`.
- **Remote config + feature flags** (fetched at startup, cached): kill switches without shipping a new extension.

### 22.8 Operations
- SLOs with error budgets; dashboards per SLO; paging only on user-impacting alerts.
- Health `/healthz` (process up) vs `/readyz` (DB/Redis/queue reachable); deployments gated on readiness.
- Deploy strategy: canary or blue-green with automatic rollback on error-rate/latency regression.
- Multi-AZ; managed Postgres with PITR; **restore drill performed and documented**; DR plan.
- **Kill switches (feature flags):** disable new signups · disable paid upgrades · disable agent file/terminal tools · force cheaper model · read-only mode · maintenance banner in panel.
- **Runbooks** in `/docs/runbooks`: webhook backlog, Razorpay outage, provider outage, DB failover, Redis outage, leaked secret rotation, mass-abuse event, bad release rollback, user paid-but-not-upgraded (manual reconcile).
- Status page + incident template + customer comms template.

### 22.9 Security at scale
- Cloudflare/WAF in front; bot protection and stricter limits on `/auth/*` and `/billing/*`.
- Free-tier abuse controls: 1 free profile per GitHub ID, optional minimum GitHub account age, device/IP velocity limits, anomaly alerts.
- Secrets in a secret manager with documented rotation; CI runs gitleaks, dependency audit, SAST; container image scan.
- Complete an OWASP ASVS-based self-review and fix findings before launch (external pen test recommended once revenue justifies it).
- Audit log for auth, billing, admin actions (append-only).

### 22.10 Required load & chaos tests (save reports in `/docs/launch-evidence`)
| Test | Pass criteria |
|---|---|
| 500 concurrent streaming chats for 30 min | error rate < 1%, no memory growth trend, overhead latency within §22.1 |
| Quota race: 50 parallel requests at limit−1 | exactly the allowed number succeed; rest get 429 |
| Webhook storm: 1,000 events incl. 30% duplicates, shuffled order | final DB state identical to ordered single-delivery; zero duplicate activations |
| Worker killed mid-job | job retried; effect applied exactly once |
| Redis down for 2 min | behavior matches §22.5 policy; recovery clean |
| DB failover / restart | API recovers without manual action; no lost paid activations |
| Provider outage (mock 100% 5xx) | fallback engages or clean error; no thread/connection leak |
| Rolling deploy under load | no dropped streams beyond grace window |
| Restore from backup | completed within RTO; data validated |

### 22.11 Support readiness
- In-panel **Help**: copy diagnostics (extension/VS Code version, requestId, plan, last error — never code), report issue link, docs link.
- Support inbox, macros for common cases (payment not reflected, can't sign in, limit questions), SLA stated on the site.

---

## 23. Agent Loop Architecture (how "chat with my agent and perform operations" actually works)

**Default (recommended): agent loop runs on the server; tools that touch the user's machine execute in the extension.**

```
Extension                         Server (agent)
 POST /v1/chat {conversationId, runId, message, context, model}
                                  → auth, entitlement, quota reserve
                                  ← SSE: delta… / tool_call {id,name,args} / usage / done
 execute tool locally (with approval)
 POST /v1/chat/tool-result {runId, toolCallId, result|error}
                                  → run state loaded from Redis (TTL ~30 min), loop resumes
                                  ← SSE continues…
```
- `runId` state (messages, pending tool call, step count, reserved budget) lives in Redis/DB, so any server instance can resume it.
- Limits: max steps/run (e.g., 25), max tool-output bytes (truncate with marker), per-tool timeout, overall run timeout; user **Stop** aborts run and releases reserved quota.
- Server-side tools (web search, retrieval) run on the server; client-side tools (files, terminal, diagnostics, diff) run in the extension. The server never gets filesystem access to the user's machine.
- Context building: explicit `@file` mentions, active selection, open editors, diagnostics; truncate/summarize long history; **redact** obvious secrets (`.env`, private keys, tokens) before anything leaves the machine; show the user which files were attached.
- If your existing agent currently runs locally or in a different shape, the agent must document the adaptation in `DECISIONS.md` rather than silently changing behavior.
- Persist each conversation turn and tool call for history/replay; apply plan-based retention (§7).

---

## 24. Admin Console, Notifications & Monitoring of "all other features"

### 24.1 Internal admin console (separate app, never shipped in the extension)
- Access: GitHub login + allowlist + 2FA; every action audit-logged.
- Features: user search/profile · current plan, subscription timeline, payments · manual plan override/grant credits (reason required) · suspend/unsuspend · webhook events viewer with **replay** · usage dashboards (per user/plan/model, cost) · feature-flag/kill-switch toggles · announcement banner editor · refund status viewer.
- Dashboards: signups, activation (first chat), free→paid conversion, churn, MRR, failed payments, provider cost vs revenue, error rates, top errors.

### 24.2 Transactional notifications (email provider such as SES/Resend/Postmark)
Welcome · payment receipt · payment failed / retry · renewal reminder (a few days before) · plan changed · cancellation confirmed (with access-until date) · account deleted. Plus in-panel banners for the same events. Include unsubscribe handling for non-essential mail.

### 24.3 Product analytics (privacy-safe, respects telemetry setting)
Events: `extension_activated, sign_in_started, sign_in_succeeded, first_message_sent, model_changed, limit_reached, upgrade_clicked, checkout_opened, payment_confirmed, subscription_cancelled, tool_approved/rejected`. Never include code or file contents.

---

## 25. Razorpay Caveats the Agent Must Verify in Current Docs (do not assume)

1. **Recurring in USD / international cards:** confirm whether Razorpay Subscriptions supports it for your account. If not, ship INR recurring and offer international users one-time prepaid passes.
2. **UPI AutoPay / e-mandate rules:** per-debit amount limits, pre-debit notification timing, and first-payment authentication differ by method; design plan prices and UX accordingly (show "authorizing mandate" states).
3. **Plan changes:** confirm what `update subscription` allows (immediate vs cycle-end, which payment methods support it). Fallback design: cancel at cycle end and create a new subscription, or create the new one and cancel the old after success; log the choice in DECISIONS.md.
4. **Plans are immutable** in Razorpay: price changes require new plan IDs; keep `plans.razorpay_plan_id_*` versioned so existing subscribers keep their price.
5. **`total_count`** is required on subscription creation; choose a large value for "until cancelled" and handle `subscription.completed`.
6. **Webhooks:** confirm delivery-retry window and timeout expectations; respond 200 quickly. Use `X-Razorpay-Event-Id` for dedupe. Separate webhook URL/secret per environment.
7. **Test vs live:** different keys, plans, customers, and webhooks. Never mix; CI guard that fails if live keys are present outside prod.
8. **Taxes/invoicing:** confirm GST handling, invoice generation, and what appears on receipts.
9. **Refunds & disputes:** implement `refund.processed` and dispute events; define policy in the Refund page.
10. **Clock/timezone:** store all timestamps UTC; display user-local.

If any item contradicts this file, current Razorpay documentation wins.

---

## 26. Definition of Done (the agent cannot declare completion until all are true)

**Functional**
- [ ] Every row of §21 passes with linked proof
- [ ] All phase acceptance criteria in §17 passed
- [ ] Upgrade works end-to-end in Razorpay **test mode** and with one small **live** payment + refund

**Scale & reliability**
- [ ] All tests in §22.10 pass with saved reports
- [ ] Two+ API instances and 2+ workers run simultaneously with no behavior difference
- [ ] Kill switches and rollback tested in staging
- [ ] Backup restore drill completed within RTO
- [ ] Runbooks written (§22.8)

**Security & compliance**
- [ ] §12 checklist fully ticked; gitleaks/dependency/SAST scans clean
- [ ] No secrets in repo history, extension bundle, webview, logs, or screenshots
- [ ] Privacy, Terms, Refund pages live; data export/delete works

**Product quality**
- [ ] Fresh-machine install of the `.vsix` tested on Windows, macOS, Linux
- [ ] Tested in VS Code stable + at least one fork (e.g., Antigravity) incl. auth fallback
- [ ] Light/dark/high-contrast + narrow panel verified
- [ ] 5-person beta feedback addressed; no dead-end states

**Delivery artifacts (in `/docs/launch-evidence` and repo root)**
`FINAL_REPORT.md` (maps R1–R16 to evidence) · `AUDIT.md` · `DECISIONS.md` · `PROGRESS.md` · test/load/chaos reports · screenshots · runbooks · architecture diagram · env var reference (names only, no values) · release notes.

---
**End of plan.** Start with Phase 0 and report back with `AUDIT.md` before writing feature code.
